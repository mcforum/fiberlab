"""Animates the tensile test frame by frame and saves transparent PNGs via
Viewport.saveAsImageFileWithOptions. Force/displacement come from a real measurement
(single polyester filament). Call render(list_of_frames) from a Fusion script; batches of
~150 frames avoid add-in timeouts."""
import adsk.core, adsk.fusion, math, os, time
# --- configuration -----------------------------------------------------------
# Absolute path of your local clone of this repository (edit before running in Fusion).
REPO = r"C:\path\to\fiberlab"
# -----------------------------------------------------------------------------
app=adsk.core.Application.get()
P=adsk.core.Point3D.create; V=adsk.core.Vector3D.create
OUT=os.path.join(REPO,'output','frames_tensile')
T=[0,4.2,4.4,4.55,4.75,5.0,5.25,5.55,5.8,6.0,6.5,7.0,7.1,7.3,7.5,7.9,8.0,8.25,8.5,8.75,9.0,9.25,9.5,9.75,10.0,10.25,10.5,10.75,11.0,11.25,11.5,11.75,12.0,12.25,12.5,12.75,13.0,13.25,13.35,13.4,13.5,14.0]
F=[0.014,0.015,0.023,0.038,0.054,0.060,0.024,0.067,0.034,0.023,0.017,0.017,0.029,0.023,0.015,0.022,0.041,0.039,0.048,0.045,0.068,0.079,0.065,0.072,0.071,0.082,0.094,0.128,0.172,0.209,0.216,0.270,0.305,0.312,0.341,0.345,0.370,0.379,0.393,0.042,0.019,0.017]
TS=[0,7.05,7.1,7.25,7.35,7.9,8.0,8.45,8.9,9.0,9.3,9.8,10.0,10.4,10.6,10.8,11.0,11.25,11.5,11.75,12.0,12.25,12.5,12.75,13.0,13.25,13.35,13.4,20]
S=[0,0,0.01,0.11,0.16,0.17,0.26,0.29,0.39,0.48,0.60,0.60,0.61,0.68,0.87,1.09,1.37,1.63,1.77,2.05,2.30,2.37,2.55,2.65,2.80,2.96,3.06,3.09,3.09]
def interp(x,X,Y):
    if x<=X[0]: return Y[0]
    for i in range(len(X)-1):
        if x<=X[i+1]:
            u=(x-X[i])/(X[i+1]-X[i]); return Y[i]+u*(Y[i+1]-Y[i])
    return Y[-1]
def ease(u): u=max(0,min(1,u)); return u*u*(3-2*u)
def lerp(a,b,u): return tuple(a[i]+(b[i]-a[i])*u for i in range(len(a)))
R=2.5; WX,WY,WZ=17,-2.75,12; HX,HZ=14.5,29.8; HAND0=40; FY=-2.75
CAM={'far':((80,-125,72),(0,8,16),30),'wide':((62,-118,60),(3,6,24),30),'close':((37.2,-108.9,29.6),(28,-2.75,21.5),27),'pull':((53.5,-105.4,36.4),(27,-2.75,22),27)}
def camfor(f):
    def mix(a,b,u):
        A,B=CAM[a],CAM[b]; return (lerp(A[0],B[0],u),lerp(A[1],B[1],u),A[2]+(B[2]-A[2])*u)
    if f<150: return mix('far','wide',ease(f/150))
    if f<300: return CAM['wide']
    if f<360: return mix('wide','close',ease((f-300)/60))
    if f<425: return CAM['close']
    if f<775: return mix('close','pull',ease((f-425)/350))
    return mix('pull','wide',ease((f-775)/90))
# measurement time during the pulling phase
def tmeas(f):
    if f<425: return 6.8
    if f<675: return 6.8+(f-425)/250*(13.35-6.8)
    return 13.35+(f-675)/25*1.0
def path_full(s):
    pts=[(HX,FY,HZ),(HX,FY,WZ)]
    for k in range(1,17):
        th=math.pi+k*(math.pi/2)/16; pts.append((WX+R*math.cos(th),FY,WZ+R*math.sin(th)))
    pts.append((HAND0+s,FY,WZ-R)); return pts
def partial(pts,frac):
    L=[0]
    for i in range(len(pts)-1): L.append(L[-1]+math.dist(pts[i],pts[i+1]))
    tgt=L[-1]*frac; out=[pts[0]]
    for i in range(len(pts)-1):
        if L[i+1]<=tgt: out.append(pts[i+1])
        else:
            u=(tgt-L[i])/(L[i+1]-L[i]); out.append(lerp(pts[i],pts[i+1],u)); break
    return out
def state(f):
    tm=tmeas(f)
    s=interp(tm,TS,S)
    lines=[]
    if f<360: pass
    elif f<425:
        lines.append(partial(path_full(0),ease((f-360)/62)))
    elif f<675:
        lines.append(path_full(s))
    else:
        u=(f-675)/25.0  # seconds after break
        BZ=21.5
        # upper piece: recoils and swings
        Lu=HZ-BZ; Lu2=Lu*(0.55+0.45*math.exp(-3*u))
        sw=1.6*math.exp(-1.2*u)*math.sin(6*u)
        up=[]
        for k in range(13):
            v=k/12; z=HZ-v*Lu2; x=HX+sw*v*v+0.5*(1-math.exp(-2*u))*math.sin(v*4)*v
            up.append((x,FY,z))
        lines.append(up)
        # lower piece: falls off the pulley
        Ll=BZ-WZ; ang=(1-math.exp(-2.5*u))*math.pi*0.85+0.15*math.exp(-1.5*u)*math.sin(7*u)
        lo=[(HX,FY,WZ)]; x,z=HX,WZ
        for k in range(12):
            a=ang*(0.45+0.55*k/11); x-=Ll/12*math.sin(a); z+=Ll/12*math.cos(a); lo.append((x,FY,max(z,0.1)))
        lines.append(lo)
        s=s+1.2*(1-math.exp(-4*u))
        lines.append(path_full(s)[1:])
    phi=-s/R
    return lines,s,phi
def apply(f):
    d=adsk.fusion.Design.cast(app.activeProduct); root=d.rootComponent
    lines,s,phi=state(f)
    for o in root.occurrences:
        n=o.component.name
        if n=='Pulley wheel':
            m=adsk.core.Matrix3D.create(); m.setToRotation(phi,V(0,1,0),P(0,0,0)); m.translation=V(WX,WY,WZ); o.transform2=m
        elif n=='Hand':
            m=adsk.core.Matrix3D.create(); m.translation=V(HAND0+s,FY,WZ-R); o.transform2=m
            vis=f>=340
            for b in o.component.bRepBodies:
                if b.isLightBulbOn!=vis: b.isLightBulbOn=vis
    for g in list(root.customGraphicsGroups): g.deleteMe()
    if lines:
        g=root.customGraphicsGroups.add()
        col=adsk.fusion.CustomGraphicsSolidColorEffect.create(adsk.core.Color.create(232,135,0,255))
        for pl in lines:
            if len(pl)<2: continue
            co=adsk.fusion.CustomGraphicsCoordinates.create([c for p in pl for c in p])
            idx=[]
            for i in range(len(pl)-1): idx+=[i,i+1]
            l=g.addLines(co,idx,False); l.weight=6; l.color=col
    eye,tgt,fov=camfor(f)
    vp=app.activeViewport; c=vp.camera; c.isSmoothTransition=False
    c.cameraType=adsk.core.CameraTypes.PerspectiveCameraType
    c.eye=P(*eye); c.target=P(*tgt); c.upVector=V(0,0,1); c.perspectiveAngle=math.radians(fov); c.isFitView=False
    vp.camera=c
def render(frames,w=1920,h=1080,sub=''):
    os.makedirs(OUT+sub,exist_ok=True)
    vp=app.activeViewport; t0=time.time()
    for f in frames:
        apply(f); adsk.doEvents(); vp.refresh()
        o=adsk.core.SaveImageFileOptions.create(os.path.join(OUT+sub,'f%04d.png'%f))
        o.width=w; o.height=h; o.isBackgroundTransparent=True; o.isAntiAliased=True
        vp.saveAsImageFileWithOptions(o)
    return time.time()-t0
