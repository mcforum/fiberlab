/*
  Laserbeugung – Messstation für den Schirmabstand L   (Version 2)
  ==================================================================
  Hardware: ESP32 DevKit, HC-SR04 (Echo über 1k/2k-Teiler), DHT11, Lasermodul 650 nm
  Verdrahtung: siehe Schaltplan (unverändert gegenüber Version 1).

  Was die Station kann:
    - misst den Abstand zur Wand per Ultraschall, temperaturkorrigiert (DHT11),
      abzüglich des kalibrierten Versatzes Sensor <-> Faser
    - speichert Messungen in "Aufnahmen" (Sitzungen) als JSON-Lines im Flash
      (/s/<id>.jsonl), inklusive aller 50 Einzelwerte jeder Messung
    - liefert die Weboberfläche (webseite.h): Faserauswahl, Maßband-Anzeige
      mit Zielzone, Auswertung mit Diagrammen, CSV/PNG/SVG-Export, PC-Empfang

  Netzwerk:
    - eigenes WLAN "Laserbeugung" (Passwort "spinnenseide") -> http://192.168.4.1
    - optional zusätzlich im Heim-/Schul-WLAN (in den Einstellungen eintragen)
      -> http://laserbeugung.local oder die angezeigte IP

  Bibliotheken: "DHT sensor library" (Adafruit) + "Adafruit Unified Sensor".
  Board: "ESP32 Dev Module", Boardpaket "esp32" von Espressif (2.x oder 3.x).
  Partition Scheme: Standard ("Default 4MB with spiffs") reicht.
*/

#include <WiFi.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include <LittleFS.h>
#include <Preferences.h>
#include <DHT.h>
#include "webseite.h"

// ---------------- Pins ----------------
#define PIN_TRIG 5
#define PIN_ECHO 18
#define PIN_DHT  4
#define DHTTYPE  DHT11

// ---------------- Netzwerk ----------------
const char* AP_SSID   = "Laserbeugung";
const char* AP_PASS   = "spinnenseide";      // mindestens 8 Zeichen
const char* MDNS_NAME = "laserbeugung";      // -> http://laserbeugung.local

// ---------------- Messparameter ----------------
const int  N_SERIE  = 50;                    // Pings pro gespeicherter Messung
const int  N_LIVE   = 5;                     // Pings pro Live-Wert
const int  PAUSE_MS = 60;                    // Datenblatt HC-SR04: >= 60 ms
const unsigned long ECHO_TIMEOUT_US = 30000; // ca. 5 m
const float T_ERSATZ = 20.0;                 // falls der DHT11 nicht antwortet

WebServer   server(80);
DHT         dht(PIN_DHT, DHTTYPE);
Preferences prefs;

float offsetCm    = 0.0;
float tempC       = NAN;
float feuchte     = NAN;
bool  tempGueltig = false;
unsigned long letzteDht = 0;

int   aktiveSession = -1;   // -1 = keine Aufnahme
int   naechsteId    = 1;
int   messNr        = 0;    // laufende Nummer in der aktiven Aufnahme
String wlanSsid, wlanPass;

float rohWerte[N_SERIE];    // Einzelwerte der letzten Serie (chronologisch)
float sortiert[N_SERIE];

struct Serie { float median, mittel, stdabw, minv, maxv; int gueltig; };

// ======================================================================
//  Messung
// ======================================================================

float aktuelleTemp()           { return tempGueltig ? tempC : T_ERSATZ; }
float schallgeschwindigkeit()  { return 331.3f + 0.606f * aktuelleTemp(); }   // m/s

unsigned long echoZeitUs() {
  digitalWrite(PIN_TRIG, LOW);  delayMicroseconds(4);
  digitalWrite(PIN_TRIG, HIGH); delayMicroseconds(10);
  digitalWrite(PIN_TRIG, LOW);
  return pulseIn(PIN_ECHO, HIGH, ECHO_TIMEOUT_US);   // 0 = kein Echo
}

// misst n Pings; gültige Abstände (cm, bereits minus Versatz) landen in rohWerte[]
Serie messeSerie(int n) {
  if (n > N_SERIE) n = N_SERIE;
  float c = schallgeschwindigkeit();
  int k = 0;
  for (int i = 0; i < n; i++) {
    unsigned long t = echoZeitUs();
    if (t > 0) rohWerte[k++] = t * c / 20000.0f - offsetCm;  // µs·m/s -> cm, halber Weg
    delay(PAUSE_MS);
  }
  Serie s = {NAN, NAN, NAN, NAN, NAN, k};
  if (k == 0) return s;

  for (int i = 0; i < k; i++) sortiert[i] = rohWerte[i];
  for (int i = 1; i < k; i++) {                       // Insertion-Sort
    float v = sortiert[i]; int j = i - 1;
    while (j >= 0 && sortiert[j] > v) { sortiert[j + 1] = sortiert[j]; j--; }
    sortiert[j + 1] = v;
  }
  s.median = (k % 2) ? sortiert[k / 2] : (sortiert[k / 2 - 1] + sortiert[k / 2]) / 2.0f;
  s.minv = sortiert[0];
  s.maxv = sortiert[k - 1];
  float summe = 0;
  for (int i = 0; i < k; i++) summe += rohWerte[i];
  s.mittel = summe / k;
  float q = 0;
  for (int i = 0; i < k; i++) q += (rohWerte[i] - s.mittel) * (rohWerte[i] - s.mittel);
  s.stdabw = (k > 1) ? sqrtf(q / (k - 1)) : 0;
  return s;
}

void dhtAktualisieren() {
  if (letzteDht != 0 && millis() - letzteDht < 2500) return;   // DHT11: max. 1 Hz
  letzteDht = millis();
  float t = dht.readTemperature();
  float h = dht.readHumidity();
  if (!isnan(t)) { tempC = t; tempGueltig = true; }
  if (!isnan(h)) feuchte = h;
}

// ======================================================================
//  Hilfsfunktionen
// ======================================================================

String jZahl(float v, int stellen) { return isnan(v) ? String("null") : String(v, stellen); }

String jText(String s) {                       // String -> JSON-String mit Escaping
  if (s.length() > 160) s = s.substring(0, 160);
  String o = "\"";
  for (unsigned int i = 0; i < s.length(); i++) {
    char ch = s[i];
    if (ch == '"' || ch == '\\') { o += '\\'; o += ch; }
    else if ((uint8_t)ch < 0x20) o += ' ';
    else o += ch;
  }
  return o + "\"";
}

float argZahl(const char* name) {              // akzeptiert 41,5 und 41.5
  String s = server.arg(name);
  s.trim();
  if (s.length() == 0) return NAN;
  s.replace(",", ".");
  return s.toFloat();
}

String sessionPfad(int id) { return "/s/" + String(id) + ".jsonl"; }

bool zeileAnhaengen(int id, const String& zeile) {
  File f = LittleFS.open(sessionPfad(id), "a");
  if (!f) return false;
  f.print(zeile);
  f.print('\n');
  f.close();
  return true;
}

void jsonSenden(const String& j)   { server.send(200, "application/json", j); }
void fehlerSenden(const String& t) { jsonSenden("{\"fehler\":" + jText(t) + "}"); }

// ======================================================================
//  HTTP-Handler
// ======================================================================

void seite() { server.send_P(200, "text/html; charset=utf-8", SEITE); }

void apiStatus() {
  String j = "{\"aktiv\":" + (aktiveSession >= 0 ? String(aktiveSession) : String("null"));
  j += ",\"messNr\":" + String(messNr);
  j += ",\"offset\":" + jZahl(offsetCm, 2);
  j += ",\"ap_ip\":" + jText(WiFi.softAPIP().toString());
  j += ",\"sta_ip\":" + (WiFi.status() == WL_CONNECTED ? jText(WiFi.localIP().toString()) : String("null"));
  j += ",\"ssid\":" + jText(wlanSsid);
  j += ",\"mdns\":" + jText(String(MDNS_NAME) + ".local");
  j += ",\"belegt_kb\":" + String((unsigned long)(LittleFS.usedBytes() / 1024));
  j += ",\"gesamt_kb\":" + String((unsigned long)(LittleFS.totalBytes() / 1024));
  j += "}";
  jsonSenden(j);
}

void apiLive() {
  dhtAktualisieren();
  Serie s = messeSerie(N_LIVE);
  String j = "{\"L\":" + jZahl(s.median, 2);
  j += ",\"roh\":" + jZahl(s.median + offsetCm, 2);
  j += ",\"gueltig\":" + String(s.gueltig);
  j += ",\"offset\":" + jZahl(offsetCm, 2);
  j += ",\"T\":" + jZahl(aktuelleTemp(), 1);
  j += ",\"T_sensor\":" + String(tempGueltig ? "true" : "false");
  j += ",\"rh\":" + jZahl(feuchte, 0);
  j += ",\"c\":" + jZahl(schallgeschwindigkeit(), 1);
  j += ",\"aktiv\":" + (aktiveSession >= 0 ? String(aktiveSession) : String("null"));
  j += "}";
  jsonSenden(j);
}

void sessionBeenden(const String& zeit) {
  if (aktiveSession < 0) return;
  zeileAnhaengen(aktiveSession, "{\"typ\":\"ende\",\"zeit\":" + jText(zeit) + "}");
  aktiveSession = -1;
  prefs.putInt("aktiv", -1);
}

void apiSessionStart() {
  sessionBeenden(server.arg("zeit"));          // laufende Aufnahme sauber abschließen
  int id = naechsteId++;
  prefs.putInt("sid", naechsteId);
  String meta = "{\"typ\":\"meta\",\"id\":" + String(id) +
                ",\"name\":" + jText(server.arg("name")) +
                ",\"start\":" + jText(server.arg("zeit")) +
                ",\"offset\":" + jZahl(offsetCm, 2) +
                ",\"version\":2}";
  if (!zeileAnhaengen(id, meta)) { fehlerSenden("Flash-Speicher nicht beschreibbar."); return; }
  aktiveSession = id;
  messNr = 0;
  prefs.putInt("aktiv", id);
  prefs.putInt("nr", 0);
  jsonSenden("{\"id\":" + String(id) + "}");
}

void apiSessionEnde() {
  if (aktiveSession < 0) { fehlerSenden("Es läuft keine Aufnahme."); return; }
  int id = aktiveSession;
  sessionBeenden(server.arg("zeit"));
  jsonSenden("{\"id\":" + String(id) + "}");
}

void apiMessen() {
  if (aktiveSession < 0) { fehlerSenden("Bitte zuerst eine Aufnahme starten."); return; }
  dhtAktualisieren();
  Serie s = messeSerie(N_SERIE);
  if (s.gueltig < N_SERIE / 2) {
    fehlerSenden("Nur " + String(s.gueltig) + " von 50 Echos gültig. Sensor gerade auf die Wand richten, Schallkegel frei halten.");
    return;
  }
  messNr++;
  prefs.putInt("nr", messNr);

  String z = "{\"typ\":\"messung\",\"nr\":" + String(messNr);
  z += ",\"zeit\":"   + jText(server.arg("zeit"));
  z += ",\"faser\":"  + jText(server.arg("faser"));
  z += ",\"probe\":"  + jText(server.arg("probe"));
  z += ",\"soll\":"   + jZahl(argZahl("soll"), 1);
  z += ",\"L\":"      + jZahl(s.median, 2);
  z += ",\"mittel\":" + jZahl(s.mittel, 2);
  z += ",\"sd\":"     + jZahl(s.stdabw, 3);
  z += ",\"min\":"    + jZahl(s.minv, 2);
  z += ",\"max\":"    + jZahl(s.maxv, 2);
  z += ",\"n\":"      + String(s.gueltig);
  z += ",\"lref\":"   + jZahl(argZahl("lref"), 1);
  z += ",\"T\":"      + jZahl(aktuelleTemp(), 1);
  z += ",\"Tsensor\":" + String(tempGueltig ? "true" : "false");
  z += ",\"rh\":"     + jZahl(feuchte, 0);
  z += ",\"c\":"      + jZahl(schallgeschwindigkeit(), 1);
  z += ",\"off\":"    + jZahl(offsetCm, 2);
  z += ",\"notiz\":"  + jText(server.arg("notiz"));
  z += ",\"werte\":[";
  for (int i = 0; i < s.gueltig; i++) { if (i) z += ","; z += String(rohWerte[i], 2); }
  z += "]}";

  if (!zeileAnhaengen(aktiveSession, z)) { fehlerSenden("Speichern fehlgeschlagen (Flash voll?)."); return; }
  jsonSenden(z);
}

// nachträgliche Auswertung des Beugungsbilds (Abstand der Minima, Ordnung, Wellenlänge)
void apiAuswertung() {
  int id = server.arg("id").toInt();
  if (!LittleFS.exists(sessionPfad(id))) { fehlerSenden("Aufnahme nicht gefunden."); return; }
  String z = "{\"typ\":\"auswertung\",\"nr\":" + String((int)server.arg("nr").toInt());
  z += ",\"abst\":"   + jZahl(argZahl("abst"), 2);
  z += ",\"m\":"      + jZahl(argZahl("m"), 0);
  z += ",\"lambda\":" + jZahl(argZahl("lambda"), 1);
  z += "}";
  zeileAnhaengen(id, z);
  jsonSenden("{\"ok\":true}");
}

void apiKalibrieren() {
  float lref = argZahl("lref");
  if (isnan(lref) || lref <= 0) { fehlerSenden("Bitte den Zollstock-Wert in cm eintragen."); return; }
  dhtAktualisieren();
  float alt = offsetCm;
  offsetCm = 0;                                   // Rohabstand messen
  Serie s = messeSerie(N_SERIE);
  if (s.gueltig < N_SERIE / 2) { offsetCm = alt; fehlerSenden("Zu wenige gültige Echos – Kalibrierung abgebrochen."); return; }
  offsetCm = s.median - lref;
  prefs.putFloat("offset", offsetCm);
  jsonSenden("{\"offset\":" + jZahl(offsetCm, 2) + ",\"sd\":" + jZahl(s.stdabw, 3) + "}");
}

void apiSessions() {
  String j = "[";
  bool erster = true;
  File dir = LittleFS.open("/s");
  if (dir && dir.isDirectory()) {
    File f = dir.openNextFile();
    while (f) {
      String name = f.name();                     // "12.jsonl" (je nach Core auch mit Pfad)
      int slash = name.lastIndexOf('/');
      if (slash >= 0) name = name.substring(slash + 1);
      int id = name.toInt();
      String meta = f.readStringUntil('\n');
      int anzahl = 0; bool ende = false;
      while (f.available()) {
        String zeile = f.readStringUntil('\n');
        if (zeile.indexOf("\"typ\":\"messung\"") >= 0) anzahl++;
        else if (zeile.indexOf("\"typ\":\"ende\"") >= 0) ende = true;
      }
      if (id > 0 && meta.startsWith("{")) {
        if (!erster) j += ",";
        erster = false;
        j += "{\"id\":" + String(id) + ",\"n\":" + String(anzahl) +
             ",\"ende\":" + String(ende ? "true" : "false") +
             ",\"aktiv\":" + String(id == aktiveSession ? "true" : "false") +
             ",\"bytes\":" + String((unsigned long)f.size()) +
             ",\"meta\":" + meta + "}";
      }
      f.close();
      f = dir.openNextFile();
    }
  }
  j += "]";
  jsonSenden(j);
}

void apiSession() {
  int id = server.arg("id").toInt();
  File f = LittleFS.open(sessionPfad(id), "r");
  if (!f) { server.send(404, "text/plain", "Aufnahme nicht gefunden"); return; }
  server.streamFile(f, "text/plain; charset=utf-8");
  f.close();
}

void apiSessionLoeschen() {
  int id = server.arg("id").toInt();
  if (id == aktiveSession) { aktiveSession = -1; prefs.putInt("aktiv", -1); }
  LittleFS.remove(sessionPfad(id));
  jsonSenden("{\"ok\":true}");
}

void apiFasernLesen() {
  File f = LittleFS.open("/fasern.json", "r");
  if (!f) { jsonSenden("null"); return; }
  server.streamFile(f, "application/json");
  f.close();
}

void apiFasernSchreiben() {
  String d = server.arg("daten");
  if (d.length() < 2 || d.length() > 6000 || d[0] != '[') { fehlerSenden("Ungültige Faserliste."); return; }
  File f = LittleFS.open("/fasern.json", "w");
  if (!f) { fehlerSenden("Speichern fehlgeschlagen."); return; }
  f.print(d);
  f.close();
  jsonSenden("{\"ok\":true}");
}

void apiWlan() {
  wlanSsid = server.arg("ssid");
  wlanPass = server.arg("pass");
  prefs.putString("ssid", wlanSsid);
  prefs.putString("pass", wlanPass);
  jsonSenden("{\"ok\":true}");
  delay(500);
  ESP.restart();
}

// ======================================================================
//  Setup / Loop
// ======================================================================

void wlanStarten() {
  WiFi.mode(WIFI_AP_STA);
  WiFi.softAP(AP_SSID, AP_PASS);
  if (wlanSsid.length() > 0) {
    WiFi.begin(wlanSsid.c_str(), wlanPass.c_str());
    Serial.print("Verbinde mit "); Serial.print(wlanSsid);
    unsigned long t0 = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - t0 < 12000) { delay(250); Serial.print("."); }
    Serial.println();
    if (WiFi.status() == WL_CONNECTED) {
      Serial.print("Im WLAN: http://"); Serial.println(WiFi.localIP());
    } else {
      // Network not reachable: access point only, otherwise scan attempts interfere
      Serial.println("WLAN nicht erreichbar – nur Access Point.");
      WiFi.disconnect(true);
      WiFi.mode(WIFI_AP);
      WiFi.softAP(AP_SSID, AP_PASS);
    }
  } else {
    WiFi.mode(WIFI_AP);
    WiFi.softAP(AP_SSID, AP_PASS);
  }
  Serial.print("Access Point "); Serial.print(AP_SSID);
  Serial.print(": http://"); Serial.println(WiFi.softAPIP());
  if (MDNS.begin(MDNS_NAME)) MDNS.addService("http", "tcp", 80);
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_TRIG, OUTPUT);
  pinMode(PIN_ECHO, INPUT);
  digitalWrite(PIN_TRIG, LOW);
  dht.begin();

  prefs.begin("laser", false);
  offsetCm      = prefs.getFloat("offset", 0.0);
  naechsteId    = prefs.getInt("sid", 1);
  aktiveSession = prefs.getInt("aktiv", -1);
  messNr        = prefs.getInt("nr", 0);
  wlanSsid      = prefs.getString("ssid", "");
  wlanPass      = prefs.getString("pass", "");

  if (!LittleFS.begin(true)) Serial.println("LittleFS-Fehler");
  if (!LittleFS.exists("/s")) LittleFS.mkdir("/s");
  if (aktiveSession >= 0 && !LittleFS.exists(sessionPfad(aktiveSession))) aktiveSession = -1;

  wlanStarten();

  server.on("/",                    HTTP_GET,  seite);
  server.on("/api/status",          HTTP_GET,  apiStatus);
  server.on("/api/live",            HTTP_GET,  apiLive);
  server.on("/api/session/start",   HTTP_POST, apiSessionStart);
  server.on("/api/session/ende",    HTTP_POST, apiSessionEnde);
  server.on("/api/session/loeschen",HTTP_POST, apiSessionLoeschen);
  server.on("/api/session",         HTTP_GET,  apiSession);
  server.on("/api/sessions",        HTTP_GET,  apiSessions);
  server.on("/api/messen",          HTTP_POST, apiMessen);
  server.on("/api/auswertung",      HTTP_POST, apiAuswertung);
  server.on("/api/kalibrieren",     HTTP_POST, apiKalibrieren);
  server.on("/api/fasern",          HTTP_GET,  apiFasernLesen);
  server.on("/api/fasern",          HTTP_POST, apiFasernSchreiben);
  server.on("/api/wlan",            HTTP_POST, apiWlan);
  server.onNotFound([]() { server.send(404, "text/plain", "Nicht gefunden"); });
  server.begin();
}

void loop() {
  server.handleClient();
  dhtAktualisieren();
}
