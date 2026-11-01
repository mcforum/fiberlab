# ESP32 laser-diffraction station

Measures the distance **L** between a clamped fibre and a screen by ultrasound and evaluates the diffraction pattern of a 650 nm laser to obtain the fibre diameter **d**.

## Hardware
| Part | Purpose |
|---|---|
| ESP32 DevKit | measurement, storage (LittleFS), Wi-Fi web server |
| HC-SR04 (echo via 1 kΩ/2 kΩ divider) | time-of-flight distance to the wall |
| DHT11 | air temperature → speed of sound |
| 650 nm laser module (3.3 V) | light source |
| 3D-printed enclosure | see `../../hardware/stl` |

Pins: `TRIG 5`, `ECHO 18`, `DHT 4`.

## Measurement principle
- **Distance:** 50 pings per measurement (≥ 60 ms apart), median used; `c = 331.3 + 0.606·ϑ` m/s; a calibrated sensor↔fibre offset (measured once with a folding rule) is subtracted.
- **Diameter:** the user enters the spacing **a** between the left and right minimum of order **m** read off graph paper:
  `θ = atan((a/2)/L)`, `d = m·λ / sin θ` (small-angle check: `d ≈ 2·m·λ·L / a`).
- The station suggests a target distance per fibre so that the first minima fall a few cm from the centre (e.g. spider silk 40 cm, hair 200 cm).

## Features
- Own access point (`Laserbeugung`, default password in the sketch — change it) or joins an existing Wi-Fi (`laserbeugung.local`).
- Live distance gauge with target zone, measurement sessions stored as JSON lines incl. all 50 raw pings.
- In-browser evaluation with charts; CSV / PNG / SVG export.

## Build
Arduino IDE, board package *esp32* (Espressif, 2.x or 3.x), board *ESP32 Dev Module*, libraries *DHT sensor library* + *Adafruit Unified Sensor*. `webseite.h` embeds `index.html` as a raw string literal (edit `index.html`, then paste it between `R"HTML(` and `)HTML"`).

> UI text and most code comments are in German.
