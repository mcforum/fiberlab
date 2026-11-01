"""Composites English captions, labels and the live force chart onto the rendered frames.
Usage: python tensile_overlay.py START END"""
import sys, os, math
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from overlay_lib import *
BASE=os.environ.get('FIBERLAB_OUTPUT', os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','output'))
SRC=BASE+'/frames_tensile'; DST=BASE+'/composited_tensile'; os.makedirs(DST,exist_ok=True)
T=[0,4.2,4.4,4.55,4.75,5.0,5.25,5.55,5.8,6.0,6.5,7.0,7.1,7.3,7.5,7.9,8.0,8.25,8.5,8.75,9.0,9.25,9.5,9.75,10.0,10.25,10.5,10.75,11.0,11.25,11.5,11.75,12.0,12.25,12.5,12.75,13.0,13.25,13.35,13.4,13.5,14.0]
F=[0.014,0.015,0.023,0.038,0.054,0.060,0.024,0.067,0.034,0.023,0.017,0.017,0.029,0.023,0.015,0.022,0.041,0.039,0.048,0.045,0.068,0.079,0.065,0.072,0.071,0.082,0.094,0.128,0.172,0.209,0.216,0.270,0.305,0.312,0.341,0.345,0.370,0.379,0.393,0.042,0.019,0.017]
TS=[0,7.05,7.1,7.25,7.35,7.9,8.0,8.45,8.9,9.0,9.3,9.8,10.0,10.4,10.6,10.8,11.0,11.25,11.5,11.75,12.0,12.25,12.5,12.75,13.0,13.25,13.35,13.4,20]
S=[0,0,0.01,0.11,0.16,0.17,0.26,0.29,0.39,0.48,0.60,0.60,0.61,0.68,0.87,1.09,1.37,1.63,1.77,2.05,2.30,2.37,2.55,2.65,2.80,2.96,3.06,3.09,3.09]
F0=0.015
def interp(x,X,Y):
    if x<=X[0]: return Y[0]
    for i in range(len(X)-1):
        if x<=X[i+1]:
            u=(x-X[i])/(X[i+1]-X[i]); return Y[i]+u*(Y[i+1]-Y[i])
    return Y[-1]
def tmeas(f):
    if f<425: return 6.8
    if f<675: return 6.8+(f-425)/250*(13.35-6.8)
    return min(14.0,13.35+(f-675)/25*1.0)
def fz(t): return interp(t,T,F)-F0
def de(x,n=3): return ('%.*f'%(n,x))
def inset(base,f,al):
    if al<=0: return
    L=layer(); d=ImageDraw.Draw(L)
    x0,y0,x1,y1=1270,60,1860,470
    shadow_box(L,(x0,y0,x1,y1),16)
    d.text((x0+24,y0+18),'Force curve (measured example)',font=font(26,True),fill=INK)
    d.text((x0+24,y0+52),'Single polyester filament, own measurement',font=font(19),fill=MUTED)
    gx0,gy0,gx1,gy1=x0+78,y0+125,x1-26,y1-62
    tA,tB=6.8,14.0; fmax=0.45
    X=lambda t: gx0+(t-tA)/(tB-tA)*(gx1-gx0); Y=lambda v: gy1-v/fmax*(gy1-gy0)
    for v in (0,0.1,0.2,0.3,0.4):
        d.line([(gx0,Y(v)),(gx1,Y(v))],fill=(225,229,236,255),width=1)
        tw=d.textlength(de(v,1),font=font(17)); d.text((gx0-10-tw,Y(v)-10),de(v,1),font=font(17),fill=MUTED)
    for t in (7,8,9,10,11,12,13,14):
        d.text((X(t)-6,gy1+8),str(t),font=font(17),fill=MUTED)
    d.line([(gx0,gy0),(gx0,gy1),(gx1,gy1)],fill=INK,width=2)
    d.text((x0+22,y0+92),'F in N',font=font(17,True),fill=INK)
    d.text((gx1-60,gy1+30),'t in s',font=font(17,True),fill=INK)
    tc=tmeas(f)
    pts=[]; t=tA
    while t<=tc+1e-9:
        pts.append((X(t),Y(max(0,fz(t))))); t+=0.02
    pts.append((X(tc),Y(max(0,fz(tc)))))
    if len(pts)>1: d.line(pts,fill=ACC,width=4,joint='curve')
    d.ellipse((pts[-1][0]-7,pts[-1][1]-7,pts[-1][0]+7,pts[-1][1]+7),fill=ACC,outline='white',width=2)
    fv=max(0,fz(tc)); sv=interp(tc,TS,S)
    d.text((gx0+14,gy0+2),'F = %s N    s = %s cm'%(de(fv,3),de(sv,2)),font=font(20,True),fill=INK)
    if f>=675:
        px,py=X(13.35),Y(fz(13.35))
        d.line([(px-4,py+4),(px-70,py+40)],fill=INK,width=2)
        d.text((px-250,py+34),'Fmax ≈ %s N'%de(fz(13.35),2),font=font(20,True),fill=INK)
    alpha_paste(base,L,al)
def compose(f):
    src=f if not (150<=f<300) else 150
    im=frame(SRC+'/f%04d.png'%src)
    title_card(im,f,10,140,'Tensile test on single fibres and fibre bundles','3D reconstruction of the real setup, built and animated via the Fusion API','Spider silk vs. polyester, ceramic fibre and human hair')
    label(im,f,160,(868,328),(330,190),'Lab stand with cross clamp',b=296)
    label(im,f,180,(1063,360),(1330,190),'Force sensor','range ±50 N or ±1 N',b=296)
    label(im,f,200,(1063,492),(1330,350),'Hook = fibre anchor point',b=296)
    label(im,f,220,(1100,760),(1330,560),'Rotary motion sensor','pulley wheel measures elongation',b=296)
    label(im,f,240,(820,740),(120,850),'Sensor-CASSY 2','data acquisition',b=296)
    label(im,f,255,(640,520),(90,300),'Laptop running CASSY Lab 2',b=296)
    caption(im,f,365,440,1,'Attach the fibre to the hook and run it over the pulley','fixed with a knot or adhesive tape')
    inset(im,f,fade(f,420,890,15,20))
    caption(im,f,446,672,2,'Pull the fibre steadily by hand until it breaks','force and displacement logged every 0.05 s (shown in slow motion)')
    caption(im,f,680,800,3,'Break: the force drops instantly','evaluated: peak force Fmax after zero-offset correction')
    if f>=805:
        title_card(im,f,805,905,'Evaluation per sample','divide Fmax by the number of fibres → force per fibre','Note: for spider silk and ceramic fibres the pulley did not turn (no displacement data).')
    footer(im,'Simplified model · data: own measurement (CASSY Lab 2)')
    im.convert('RGB').save(DST+'/o%04d.jpg'%f,quality=93)
if __name__=='__main__':
    a,b=int(sys.argv[1]),int(sys.argv[2])
    for f in range(a,b): compose(f)
    print('done',a,b)
