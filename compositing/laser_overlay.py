"""Composites English captions, labels and the live force chart onto the rendered frames.
Usage: python laser_overlay.py START END"""
import sys, os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from overlay_lib import *
BASE=os.environ.get('FIBERLAB_OUTPUT', os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','output'))
SRC=BASE+'/frames_laser'; DST=BASE+'/composited_laser'; os.makedirs(DST,exist_ok=True)
N=875
def srcframe(f):
    if 100<f<250: return 100
    if 600<=f<615: return 599
    if 615<=f<725: return 615
    if f>800: return 800
    return f
def panel(base,f,a,b,x0,y0,lines,title=None):
    al=fade(f,a,b,15,15)
    if al<=0: return
    L=layer(); d=ImageDraw.Draw(L)
    fts=[font(sz,bd) for (_,sz,bd) in lines]
    COL=500
    w=max((COL+d.textlength(t.split('\t')[1],font=ft)) if '\t' in t else d.textlength(t,font=ft) for (t,_,_),ft in zip(lines,fts))+60
    h=sum(sz+18 for (_,sz,_) in lines)+40
    shadow_box(L,(x0,y0,x0+w,y0+h),16)
    y=y0+22
    for (t,sz,bd),ft in zip(lines,fts):
        if '\t' in t:
            l_,r_=t.split('\t'); d.text((x0+30,y),l_,font=ft,fill=INK); d.text((x0+30+COL,y),r_,font=ft,fill=INK)
        else: d.text((x0+30,y),t,font=ft,fill=INK if bd else MUTED)
        y+=sz+18
    alpha_paste(base,L,al)
def lfooter(base,text):
    L=layer(); d=ImageDraw.Draw(L); fs=font(18); tw=d.textlength(text,font=fs)
    d.rounded_rectangle((W-tw-46,H-44,W-18,H-12),10,fill=(255,255,255,200)); d.text((W-tw-32,H-38),text,font=fs,fill=(90,100,115,255))
    base.alpha_composite(L)
def compose(f):
    im=frame(SRC+'/f%04d.png'%srcframe(f))
    title_card(im,f,8,95,'Laser diffraction: measuring fibre diameter','Self-built ESP32 measuring station – 3D reconstruction in Autodesk Fusion','Enclosure imported from the original 3D-print files')
    label(im,f,110,(600,330),(110,190),'3D-printed enclosure','ESP32 inside, controlled via Wi-Fi web interface',b=246)
    label(im,f,128,(950,390),(1230,190),'Ultrasonic sensor HC-SR04','measures distance L; DHT11 on the side for temperature',b=246)
    label(im,f,146,(968,625),(1250,800),'Laser module (λ = 650 nm)',b=246)
    label(im,f,164,(1075,665),(1290,560),'Fibre holder with clamped fibre','clamp plates top and bottom',b=246)
    label(im,f,182,(860,880),(110,860),'Camera tripod',b=246)
    caption(im,f,300,425,1,'Measure distance L from fibre to wall by ultrasound','echo time of flight, temperature-corrected: c = 331.3 m/s + 0.606 m/(s·°C) · ϑ  (≈ 343 m/s at 20 °C)')
    panel(im,f,400,520,1340,70,[('L = 39.9 cm',44,True),('Spider silk, sample 1 (run A04)',20,False)])
    caption(im,f,432,518,2,'The laser beam (λ = 650 nm) hits the clamped fibre','behind the fibre a diffraction pattern of bright maxima and dark minima appears')
    caption(im,f,530,722,3,'Measure the spacing a between minima of the same order','spider silk, sample 1: a = 14.2 cm at order m = 2 (graph paper)')
    if 615<=f<725:
        al=fade(f,618,722,10,15)
        if al>0:
            L=layer(); d=ImageDraw.Draw(L); t='a = 14.2 cm'; ft=font(30,True); tw=d.textlength(t,font=ft)
            shadow_box(L,(980-tw/2-16,676,980+tw/2+16,726),10); d.text((980-tw/2,684),t,font=ft,fill=INK); alpha_paste(im,L,al)
    panel(im,f,625,722,1270,60,[('Evaluation',30,True),('tan θ = (a/2) / L  →  θ = 10.1°',26,False),('d = m · λ / sin θ',30,True),('d = 2 · 650 nm / sin 10.1° ≈ 7.4 µm',26,False)])
    if f>=805:
        panel(im,f,805,890,110,90,[('Result: fibre diameter d (run A04)',34,True),('mean ± standard deviation, 4 samples each',20,False),
            ('Spider silk (dragline)\t7.33 ± 0.21 µm',28,True),('Ceramic fibre\t15.44 ± 0.19 µm',28,True),
            ('Polyester (single filament)\t17.53 ± 0.22 µm',28,True),('Human hair\t60.40 ± 0.76 µm',28,True)])
    lfooter(im,'Model: original enclosure print files · pattern computed from measured d and L (run A04)')
    im.convert('RGB').save(DST+'/o%04d.jpg'%f,quality=93)
if __name__=='__main__':
    a,b=int(sys.argv[1]),int(sys.argv[2])
    for f in range(a,b): compose(f)
    print('done',a,b)
