"""Builds the tensile-test setup (stand, force sensor, rotary sensor with pulley, data logger,
laptop, cables, hand) as a direct-modeling design. Run inside Autodesk Fusion (Scripts and Add-Ins)."""
import adsk.core, adsk.fusion, math, os
# --- configuration -----------------------------------------------------------
# Absolute path of your local clone of this repository (edit before running in Fusion).
REPO = r"C:\path\to\fiberlab"
# -----------------------------------------------------------------------------

# Fusion ships localized appearance libraries. Names below are from the German UI;
# EN_NAMES maps them to the English UI. Missing appearances fall back to the default.
EN_NAMES = {
 'Kunststoff - matt (Weiß)':'Plastic - Matte (White)','Kunststoff - matt (Grau)':'Plastic - Matte (Gray)',
 'Kunststoff - matt (Schwarz)':'Plastic - Matte (Black)','Kunststoff - matt (Blau)':'Plastic - Matte (Blue)',
 'Kunststoff - matt (Gelb)':'Plastic - Matte (Yellow)','Kunststoff - glänzend (Schwarz)':'Plastic - Glossy (Black)',
 'Kunststoff - glänzend (Rot)':'Plastic - Glossy (Red)','Kunststoff - glänzend (Blau)':'Plastic - Glossy (Blue)',
 'Kunststoff - glänzend (Gelb)':'Plastic - Glossy (Yellow)','Kunststoff - glänzend (Grün)':'Plastic - Glossy (Green)',
 'Stahl - satiniert':'Steel - Satin','Edelstahl - satiniert':'Stainless Steel - Satin','Eisen - Guss':'Iron - Cast',
 'Farbe - Metallic (Blau)':'Paint - Metallic (Blue)','Aluminium - satiniert':'Aluminum - Satin','Chrom':'Chrome',
 'Papier (Weiß)':'Paper (White)','ABS (Weiß)':'ABS (White)','LED (Grün)':'LED (Green)','LED (Rot)':'LED (Red)',
 'Aluminium - eloxiert, rau (Grau)':'Aluminum - Anodized Rough (Gray)','Glas - dunkle Farbe':'Glass - Dark Color',
 'Paek (Beige)':'Paek (Beige)','Stoff (Grau)':'Fabric (Gray)','Gummi - weich':'Rubber - Soft','Messing - poliert':'Brass - Polished',
 'FR4':'FR4','Kiefer':'Pine'}
app=adsk.core.Application.get()
P=adsk.core.Point3D.create; V=adsk.core.Vector3D.create
tb=adsk.fusion.TemporaryBRepManager.get()
def des(): return adsk.fusion.Design.cast(app.activeProduct)
_lib=None
def appear(name):
    global _lib
    d=des(); a=d.appearances.itemByName(name)
    if a: return a
    if _lib is None:
        _lib=[l for l in app.materialLibraries if l.name in ('Fusion-Darstellungsbibliothek','Fusion Appearance Library')][0]
    for n in (name, EN_NAMES.get(name,'')):
        src=_lib.appearances.itemByName(n) if n else None
        if src: return d.appearances.addByCopy(src,name)
    return None
def add(comp,tmp,ap,name=None):
    b=comp.bRepBodies.add(tmp)
    a=appear(ap) if isinstance(ap,str) else ap
    if a: b.appearance=a
    if name: b.name=name
    return b
def box(cx,cy,cz,lx,ly,lz,ld=(1,0,0),wd=(0,1,0)):
    o=adsk.core.OrientedBoundingBox3D.create(P(cx,cy,cz),V(*ld),V(*wd),lx,ly,lz)
    return tb.createBox(o)
def cyl(p1,p2,r,r2=None):
    return tb.createCylinderOrCone(P(*p1),r,P(*p2),r if r2 is None else r2)
def sph(c,r): return tb.createSphere(P(*c),r)
def tor(c,ax,R,r): return tb.createTorus(P(*c),V(*ax),R,r)
def cut(a,b): tb.booleanOperation(a,b,adsk.fusion.BooleanTypes.DifferenceBooleanType); return a
def uni(a,b): tb.booleanOperation(a,b,adsk.fusion.BooleanTypes.UnionBooleanType); return a
def newcomp(name,tx=0,ty=0,tz=0):
    m=adsk.core.Matrix3D.create(); m.translation=V(tx,ty,tz)
    occ=des().rootComponent.occurrences.addNewComponent(m)
    occ.component.name=name
    return occ
def chain(pts,r):
    t=None
    for i in range(len(pts)-1):
        c=cyl(pts[i],pts[i+1],r)
        t=c if t is None else uni(t,c)
        if i>0: uni(t,sph(pts[i],r))
    return t
def smooth(pts,n=6):
    # Catmull-Rom
    out=[]
    ps=[pts[0]]+pts+[pts[-1]]
    for i in range(1,len(ps)-2):
        p0,p1,p2,p3=ps[i-1],ps[i],ps[i+1],ps[i+2]
        for k in range(n):
            t=k/n
            out.append(tuple(0.5*((2*p1[j])+(-p0[j]+p2[j])*t+(2*p0[j]-5*p1[j]+4*p2[j]-p3[j])*t*t+(-p0[j]+3*p1[j]-3*p2[j]+p3[j])*t**3) for j in range(3)))
    out.append(pts[-1]); return out
def obj(name):
    r=des().rootComponent
    for o in r.allOccurrences:
        if o.component.name==name: return o
def setcam(eye,target,up=(0,0,1),fov=None):
    vp=app.activeViewport; c=vp.camera
    c.isSmoothTransition=False
    c.cameraType=adsk.core.CameraTypes.PerspectiveCameraType
    c.eye=P(*eye); c.target=P(*target); c.upVector=V(*up)
    if fov: c.perspectiveAngle=math.radians(fov)
    c.isFitView=False
    vp.camera=c

def run(context):
    doc=app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    d=des(); d.designType=adsk.fusion.DesignTypes.DirectDesignType
    root=d.rootComponent
    # bench
    o=newcomp('Lab bench'); c=o.component
    add(c,box(0,8,-1.5,130,70,3),'Kunststoff - matt (Weiß)','Table top')
    for x in (-62,62):
        for y in (-24,40):
            add(c,box(x,y,-39,4,4,72),'Stahl - satiniert','Leg')
    # stand A
    o=newcomp('Stand with force sensor mount'); c=o.component
    add(c,box(0,1,1,16,9,2),'Eisen - Guss','Stand base')
    add(c,cyl((0,0,2),(0,0,4.5),1.6),'Eisen - Guss','Base hub')
    add(c,cyl((1.5,0,3.5),(3.2,0,3.5),0.3),'Stahl - satiniert')
    add(c,box(3.4,0,3.5,0.4,1.8,1.3),'Stahl - satiniert','Wing screw')
    add(c,cyl((0,0,2),(0,0,55),0.6),'Edelstahl - satiniert','Stand rod')
    add(c,box(0,-1.4,40,3.2,6,3.2),'Farbe - Metallic (Blau)','Cross clamp')
    add(c,cyl((1.6,0.9,40),(5.0,0.9,40),0.3),'Stahl - satiniert')
    add(c,cyl((5.0,0.9,38.6),(5.0,0.9,41.4),0.35),'Stahl - satiniert')
    add(c,cyl((-0.9,-2.75,41.6),(-0.9,-2.75,44.5),0.3),'Stahl - satiniert')
    add(c,cyl((-0.9,-4.0,44.5),(-0.9,-1.5,44.5),0.35),'Stahl - satiniert')
    add(c,cyl((-7,-2.75,40),(25,-2.75,40),0.5),'Edelstahl - satiniert','Cross bar')
    # Kraftsensor S
    o=newcomp('Force sensor'); c=o.component
    b=box(14.5,-2.75,37.5,2.6,2.6,8)
    cut(b,box(14.5,-2.75,36.0,0.5,3,2.2))
    add(c,b,'Aluminium - satiniert','Sensor body')
    add(c,cyl((14.5,-2.75,41.5),(14.5,-2.75,42.3),0.3),'Stahl - satiniert')
    kn=cyl((14.5,-2.75,42.3),(14.5,-2.75,44.6),0.75)
    for i in range(8):
        a=i*math.pi/4; cut(kn,cyl((14.5+0.85*math.cos(a),-2.75+0.85*math.sin(a),42.2),(14.5+0.85*math.cos(a),-2.75+0.85*math.sin(a),44.7),0.18))
    add(c,kn,'Kunststoff - glänzend (Schwarz)','Clamp knob')
    add(c,cyl((14.5,-2.75,31.8),(14.5,-2.75,33.6),0.24),'Chrom','Hook shank')
    h=tor((14.5,-2.75,30.8),(0,1,0),1.0,0.22)
    cut(h,box(16.0,-2.75,31.8,3.0,1,2.0))
    add(c,h,'Chrom','Hook')
    add(c,cyl((14.5,-1.45,35),(14.5,-0.6,35),0.45),'Kunststoff - matt (Grau)','Cable gland')
    # Drehbewegungssensor
    o=newcomp('Rotary motion sensor'); c=o.component
    add(c,box(17,1.5,1,16,9,2),'Eisen - Guss','Stand base')
    add(c,cyl((17,0.5,2),(17,0.5,4.5),1.6),'Eisen - Guss')
    add(c,cyl((17,0.5,2),(17,0.5,9),0.5),'Edelstahl - satiniert','Rod')
    hb=box(17,-0.5,12,6,3,6)
    add(c,hb,'Kunststoff - matt (Schwarz)','Housing')
    add(c,box(17,-0.5,15.03,4,1.8,0.06),'Papier (Weiß)','Label')
    # pulley wheel (own component, origin = rotation axis)
    o=newcomp('Pulley wheel',17,-2.75,12); c=o.component
    w=cyl((0,0.25,0),(0,0.75,0),2.9); uni(w,cyl((0,-0.25,0),(0,0.25,0),2.5)); uni(w,cyl((0,-0.75,0),(0,-0.25,0),2.9))
    for i in range(3):
        a=i*2*math.pi/3+0.5; cut(w,cyl((1.5*math.cos(a),-0.9,1.5*math.sin(a)),(1.5*math.cos(a),0.9,1.5*math.sin(a)),0.45))
    add(c,w,'Kunststoff - glänzend (Schwarz)','Step pulley')
    add(c,cyl((0,-0.85,0),(0,0.8,0),0.45),'Chrom','Axle')
    add(c,box(0,-0.78,2.3,0.35,0.08,1.0),'Kunststoff - matt (Weiß)','Marker')
    # Sensor-CASSY 2
    o=newcomp('Data logger'); c=o.component
    add(c,box(-8,22,3,24,15,6),'ABS (Weiß)','Housing')
    add(c,box(-8,22,6.02,22,13,0.04),'Kunststoff - matt (Grau)','Front panel')
    for i,x in enumerate((-14,-11.5,-9)):
        add(c,cyl((x,17.5,6),(x,17.5,6.6),0.45),'Kunststoff - glänzend (Rot)' if i<2 else 'Kunststoff - glänzend (Blau)')
    for x,col in ((-1,'Kunststoff - glänzend (Rot)'),(1.5,'Kunststoff - glänzend (Blau)')):
        add(c,cyl((x,17.5,6),(x,17.5,6.6),0.45),col)
    add(c,box(-13,25,8.5,4.5,4,5),'ABS (Weiß)','Sensor box A')
    add(c,box(-3,25,8.5,4.5,4,5),'ABS (Weiß)','Sensor box B')
    add(c,box(-8,15.6,0.6,20,0.4,0.3),'LED (Grün)','LED')
    # Laptop
    o=newcomp('Laptop'); c=o.component
    add(c,box(-44,22,0.8,32,22,1.6),'Aluminium - eloxiert, rau (Grau)','Base')
    add(c,box(-44,19,1.62,28,10,0.05),'Kunststoff - matt (Schwarz)','Keyboard')
    s15,c15=math.sin(math.radians(15)),math.cos(math.radians(15))
    up=(0,s15,c15); hinge=(-44,33,1.6)
    ctr=tuple(hinge[i]+10.5*up[i] for i in range(3))
    add(c,box(*ctr,32,21,0.7,ld=(1,0,0),wd=up),'Aluminium - eloxiert, rau (Grau)','Lid')
    n=(0,-c15,s15); ctr2=tuple(ctr[i]+0.36*n[i] for i in range(3))
    add(c,box(*ctr2,30,19,0.03,ld=(1,0,0),wd=up),'Glas - dunkle Farbe','Screen')
    # cables
    o=newcomp('Cables'); c=o.component
    add(c,chain(smooth([(14.5,-0.6,35),(15,3,33),(19,7,22),(17,11,6),(10,16,0.3),(-6,19,0.3),(-13,26,4),(-13,25,10),(-13,25,11.2)]),0.22),'Kunststoff - matt (Grau)','Force sensor cable')
    add(c,chain(smooth([(17,1,12),(17,4,10),(14,9,3),(6,15,0.3),(-1,18,0.3),(-3,26,4),(-3,25,10),(-3,25,11.2)]),0.22),'Kunststoff - matt (Schwarz)','Rotary sensor cable')
    add(c,chain(smooth([(-20,24,3),(-24,25,1),(-27,25,0.3),(-28,24,0.3)]),0.25),'Kunststoff - matt (Grau)','USB')
    # hand (origin = grip point)
    o=newcomp('Hand',40,-2.75,9.5); c=o.component
    sk='Paek (Beige)'
    hand=chain([(0.2,0,0.35),(3.0,0.3,1.4),(5.6,0.8,2.6)],0.6)
    uni(hand,chain([(0.2,0,-0.35),(2.6,-0.5,-1.2),(4.6,-0.4,-2.4)],0.7))
    uni(hand,box(8.0,0.6,0.4,5.4,2.6,5.6))
    for dz,dx in ((1.6,0),(0,0.6),(-1.4,1.2)):
        uni(hand,chain([(5.4,0.6,0.9+dz),(3.8+dx,0.2,0.6+dz),(3.9+dx,-0.9,-0.4+dz)],0.55))
    uni(hand,cyl((10.6,0.6,0.4),(16,0.6,0.4),2.4))
    add(c,hand,sk,'Hand')
    add(c,cyl((12,0.6,0.4),(20,0.6,0.4),2.6),'Stoff (Grau)','Sleeve')
    root.isOriginFolderLightBulbOn=False
    vp=app.activeViewport; vp.visualStyle=adsk.core.VisualStyles.ShadedVisualStyle
    setcam((40,-80,45),(5,5,18),fov=30)
    print('ok', root.allOccurrences.count)

    exec(open(os.path.join(REPO,'fusion','common.py'),encoding='utf8').read(),globals())
    setup_view()
    print('saved',save_as('Tensile test setup','Reconstruction of a hand-pulled tensile test (generated by script)'))
