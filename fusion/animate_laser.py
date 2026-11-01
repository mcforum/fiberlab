"""Animates the laser-diffraction measurement: ultrasonic pulses (time of flight), laser beam,
and the far-field single-slit/Babinet intensity pattern I = (sin b / b)^2 computed from the
measured fibre diameter d and distance L. Saves transparent PNG frames."""
import adsk.core, adsk.fusion, math, os, time
# --- configuration -----------------------------------------------------------
# Absolute path of your local clone of this repository (edit before running in Fusion).
REPO = r"C:\path\to\fiberlab"
# -----------------------------------------------------------------------------
app=adsk.core.Application.get()
P=adsk.core.Point3D.create; V=adsk.core.Vector3D.create
OUT=os.path.join(REPO,'output','frames_laser')
LAM=650e-9
def ease(u): u=max(0,min(1,u)); return u*u*(3-2*u)
def lerp(a,b,u): return tuple(a[i]+(b[i]-a[i])*u for i in range(len(a)))
G={}
def geo():
    r=adsk.fusion.Design.cast(app.activeProduct).rootComponent
    for k in ('H','L','d_um','src_y','src_z','ap_y'): G[k]=float(r.attributes.itemByName('anim',k).value)
def cams():
    H=G['H']; C=(0,3.5,H+1.5)
    def orb(a,R=30,h=7):
        a=math.radians(a); return ((C[0]+R*math.cos(a),C[1]+R*math.sin(a),H+h),C,34)
    return {'o0':orb(-40),'o1':orb(-122),'wide':((-62,30,H+22),(0,-16,H-4),40),
            'wall':((-9,-14,H+4),(0,-G['L'],H),48)}
def camfor(f):
    K=cams(); H=G['H']
    def mix(a,b,u):
        A,B=K[a],K[b]; return (lerp(A[0],B[0],u),lerp(A[1],B[1],u),A[2]+(B[2]-A[2])*u)
    if f<100:
        a=math.radians(-40-82*ease(f/100)); C=(0,3.5,H+1.5)
        return ((30*math.cos(a),3.5+30*math.sin(a),H+7),C,34)
    if f<250: return K['o1']
    if f<300: return mix('o1','wide',ease((f-250)/50))
    if f<520: return K['wide']
    if f<600: return mix('wide','wall',ease((f-520)/80))
    if f<725: return K['wall']
    if f<800: return mix('wall','wide',ease((f-725)/75))
    return K['wide']
def arc(c,r,a0,a1,plane,n=24):
    pts=[]
    for k in range(n+1):
        a=a0+(a1-a0)*k/n
        if plane=='xy': pts.append((c[0]+r*math.sin(a),c[1]-r*math.cos(a),c[2]))
        else: pts.append((c[0],c[1]-r*math.cos(a),c[2]+r*math.sin(a)))
    return pts
def intensity(x):
    th=math.atan(x/G['L']); b=math.pi*G['d_um']*1e-6*math.sin(th)/LAM
    return 1.0 if abs(b)<1e-6 else (math.sin(b)/b)**2
def xmin(m): return G['L']*math.tan(math.asin(m*LAM/(G['d_um']*1e-6)))
def scene(f):
    H=G['H']; L=G['L']; WY=-L+0.15
    lines=[]; meshes=[]
    lines.append(([(0,0,H-1.2),(0,0,H+1.4)],(232,135,0),3))
    src=(0,G['src_y'],G['src_z']); D=G['src_y']+L; spd=D/25.0
    for p0 in (305,350,395):
        t=f-p0
        if 0<=t<=50:
            r=t*spd
            for k in range(3):
                rr=r-k*1.2
                if rr<=0.3: continue
                if rr<=D:
                    for pl in ('xy','yz'): lines.append((arc(src,rr,-0.35,0.35,pl),(40,120,220),3-k))
                elif rr<2*D:
                    m=(0,-2*L-G['src_y'],src[2])
                    for pl in ('xy','yz'): lines.append((arc(m,rr,math.pi-0.35,math.pi+0.35,pl),(20,170,160),3-k))
    if f>=425:
        ap=(0,G['ap_y'],H); fb=(0,0,H)
        u1=ease((f-425)/20); u2=ease((f-445)/14)
        if u1>0: lines.append(([ap,lerp(ap,fb,u1)],(235,20,20),4))
        if u2>0: lines.append(([fb,lerp(fb,(0,WY,H),u2)],(235,20,20),4))
        k=ease((f-459)/40)
        if k>0:
            for kk in (1.43,2.46,3.47):
                xx=L*math.tan(math.asin(kk*LAM/(G['d_um']*1e-6)))
                for sgn in (-1,1):
                    c=tuple(int(255-(255-v)*0.55*k) for v in (235,60,60))
                    lines.append(([fb,(sgn*xx,WY,H)],c,1))
            levels={}; w=0.08; x=-14.0
            while x<14.0:
                I=intensity(x+w/2); a=min(1.0,k*(I**0.3)*1.3)
                if I>0.004 and a>0.06: levels.setdefault(int(a*14),[]).append((x,x+w))
                x+=w
            for q,strips in levels.items():
                a=q/14.0; rgb=tuple(int(c0+(t-c0)*a) for c0,t in zip((250,200,200),(225,15,20))); hh=0.25+0.12*a
                meshes.append(([(s0,WY,H-hh,s1,WY,H+hh) for s0,s1 in strips],rgb))
            meshes.append(([(-0.2,WY+0.005,H-0.2,0.2,WY+0.005,H+0.2)],tuple(int(c0+(t-c0)*k) for c0,t in zip((252,215,215),(255,90,90)))))
    if 615<=f<725:
        zz=H-2.2; xa,xb=-xmin(2),xmin(2); c=(28,38,56)
        lines.append(([(xa,WY+0.01,zz),(xb,WY+0.01,zz)],c,2))
        for xv in (xa,xb): lines.append(([(xv,WY+0.01,zz-0.6),(xv,WY+0.01,H-0.4)],c,2))
    return lines,meshes
def apply(f):
    root=adsk.fusion.Design.cast(app.activeProduct).rootComponent
    for g in list(root.customGraphicsGroups): g.deleteMe()
    lines,meshes=scene(f); g=root.customGraphicsGroups.add()
    for pl,rgb,wt in lines:
        co=adsk.fusion.CustomGraphicsCoordinates.create([c for p in pl for c in p]); idx=[]
        for i in range(len(pl)-1): idx+=[i,i+1]
        l=g.addLines(co,idx,False); l.weight=wt
        l.color=adsk.fusion.CustomGraphicsSolidColorEffect.create(adsk.core.Color.create(*rgb,255))
    for quads,rgb in meshes:
        cs=[]; ti=[]
        for (x0,y,z0,x1,_,z1) in quads:
            b=len(cs)//3; cs+=[x0,y,z0, x1,y,z0, x1,y,z1, x0,y,z1]; ti+=[b,b+2,b+1,b,b+3,b+2]
        nrm=[0.0,1.0,0.0]*(len(cs)//3)
        m=g.addMesh(adsk.fusion.CustomGraphicsCoordinates.create(cs),ti,nrm,ti)
        C=adsk.core.Color.create(*rgb,255)
        m.color=adsk.fusion.CustomGraphicsSolidColorEffect.create(C)
    eye,tgt,fov=camfor(f)
    vp=app.activeViewport; c=vp.camera; c.isSmoothTransition=False
    c.cameraType=adsk.core.CameraTypes.PerspectiveCameraType
    c.eye=P(*eye); c.target=P(*tgt); c.upVector=V(0,0,1); c.perspectiveAngle=math.radians(fov); c.isFitView=False
    vp.camera=c
def render(frames,w=1920,h=1080,sub=''):
    geo(); os.makedirs(OUT+sub,exist_ok=True)
    vp=app.activeViewport; t0=time.time()
    for f in frames:
        apply(f); adsk.doEvents(); vp.refresh()
        o=adsk.core.SaveImageFileOptions.create(os.path.join(OUT+sub,'f%04d.png'%f))
        o.width=w; o.height=h; o.isBackgroundTransparent=True; o.isAntiAliased=True
        vp.saveAsImageFileWithOptions(o)
    return time.time()-t0
FRAMES=list(range(0,101))+list(range(250,600))+[615]+list(range(725,801))
