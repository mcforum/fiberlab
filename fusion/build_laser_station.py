"""Assembles the laser-diffraction station from the original enclosure STL files, adds a camera
tripod, wall and graph paper at the measured distance L, and stores animation metadata as
attributes. Run inside Autodesk Fusion."""
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
    return tb.createBox(adsk.core.OrientedBoundingBox3D.create(P(cx,cy,cz),V(*ld),V(*wd),lx,ly,lz))
def cyl(p1,p2,r,r2=None): return tb.createCylinderOrCone(P(*p1),r,P(*p2),r if r2 is None else r2)
def sph(c,r): return tb.createSphere(P(*c),r)
def cut(a,b): tb.booleanOperation(a,b,adsk.fusion.BooleanTypes.DifferenceBooleanType); return a
def uni(a,b): tb.booleanOperation(a,b,adsk.fusion.BooleanTypes.UnionBooleanType); return a
def add(comp,tmp,ap,name=None):
    b=comp.bRepBodies.add(tmp); b.appearance=appear(ap) if isinstance(ap,str) else ap
    if name: b.name=name
    return b
def newcomp(name):
    occ=des().rootComponent.occurrences.addNewComponent(adsk.core.Matrix3D.create()); occ.component.name=name; return occ
def chain(pts,r):
    t=None
    for i in range(len(pts)-1):
        c=cyl(pts[i],pts[i+1],r); t=c if t is None else uni(t,c)
        if i>0: uni(t,sph(pts[i],r))
    return t
def smooth(pts,n=6):
    out=[]; ps=[pts[0]]+pts+[pts[-1]]
    for i in range(1,len(ps)-2):
        p0,p1,p2,p3=ps[i-1],ps[i],ps[i+1],ps[i+2]
        for k in range(n):
            t=k/n; out.append(tuple(0.5*((2*p1[j])+(-p0[j]+p2[j])*t+(2*p0[j]-5*p1[j]+4*p2[j]-p3[j])*t*t+(-p0[j]+3*p1[j]-3*p2[j]+p3[j])*t**3) for j in range(3)))
    out.append(pts[-1]); return out

H=110.0
G=(-4.5,-0.9,H-1.2)
STL=os.path.join(REPO,'hardware','stl')
def mat(t=(0,0,0),rx=0.0):
    m=adsk.core.Matrix3D.create()
    if rx: m.setToRotation(math.radians(rx),V(1,0,0),P(0,0,0))
    m2=adsk.core.Matrix3D.create(); m2.translation=V(t[0]+G[0],t[1]+G[1],t[2]+G[2])
    m.transformBy(m2); return m
def meshpart(name,fn,m,ap='Kunststoff - matt (Weiß)'):
    occ=des().rootComponent.occurrences.addNewComponent(adsk.core.Matrix3D.create()); occ.component.name=name
    mbs=occ.component.meshBodies.add(os.path.join(STL,fn),adsk.fusion.MeshUnits.MillimeterMeshUnit)
    for i in range(mbs.count):
        mb=mbs.item(i)
        try: mb.appearance=appear(ap)
        except: pass
    occ.transform2=m
    return occ
def addchain(comp,pts,r,ap,name):
    for i in range(len(pts)-1):
        b=add(comp,cyl(pts[i],pts[i+1],r),ap,name)
        if i>0: add(comp,sph(pts[i],r),ap,name)
def run(context):
    doc=app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    d=des(); d.designType=adsk.fusion.DesignTypes.DirectDesignType; root=d.rootComponent
    meshpart('Enclosure base','enclosure_base_with_laser_and_fibre_holder.stl',mat())
    meshpart('Sensor mount','ultrasonic_sensor_mount.stl',mat((-8.75,5.03,2.6)))
    meshpart('Enclosure cover','enclosure_cover.stl',mat((-8.98,19.26,7.2),180))
    meshpart('Clamp plate top','fibre_clamp_plate_1.stl',mat((-5.75,0.54,-13.1),90))
    meshpart('Clamp plate bottom','fibre_clamp_plate_2.stl',mat((-5.75,0.54,-16.7),90))
    o=newcomp('Visible electronics'); c=o.component
    gx,gy,gz=G
    def L(x,y,z): return (x/10+gx,y/10+gy,z/10+gz)
    for zz in (23,5):
        add(c,cyl(L(45,5.4,zz),L(45,1.6,zz),0.12),'Stahl - satiniert','Screw')
        add(c,cyl(L(45,1.6,zz),L(45,1.2,zz),0.3),'Chrom','Screw head')
    for hx_ in (32,58):
        add(c,cyl(L(hx_,62,53.5),L(hx_,43.3,53.5),0.8),'Aluminium - satiniert','Ultrasonic transducer')
        add(c,cyl(L(hx_,43.4,53.5),L(hx_,43.2,53.5),0.62),'Stoff (Grau)','Mesh')
    add(c,box(*L(88.5,72,40),0.55,1.25,1.6),'Kunststoff - matt (Blau)','DHT11')
    add(c,cyl(L(45,41,12),L(45,40.3,12),0.25),'LED (Rot)','Laser aperture')
    addchain(c,smooth([L(80,53.2,30),L(70,50,26),L(58,46,24),L(50,42.5,20)],3),0.05,'Kunststoff - glänzend (Rot)','Wire red')
    addchain(c,smooth([L(80.5,53.2,30.5),L(71,49,27.5),L(59,45,25),L(51,42.4,21)],3),0.05,'Kunststoff - glänzend (Blau)','Wire blue')
    o=newcomp('Camera tripod'); c=o.component
    cx,cy=0.0,(87-9)/10.0; zb=H-1.2
    add(c,box(cx,cy,zb-0.5,5,5,1),'Kunststoff - matt (Schwarz)','Quick-release plate')
    add(c,cyl((cx,cy,zb-1),(cx,cy,zb-4.5),2.6),'Kunststoff - matt (Schwarz)','Tripod head')
    add(c,cyl((cx-1,cy,zb-3),(cx-12,cy-9,zb-5),0.55),'Kunststoff - matt (Schwarz)','Pan handle')
    add(c,cyl((cx-9,cy-6.5,zb-4.5),(cx-12.5,cy-9.4,zb-5.1),0.85),'Gummi - weich','Grip')
    add(c,cyl((cx,cy,zb-4.5),(cx,cy,80),1.1),'Aluminium - eloxiert, rau (Grau)','Center column')
    add(c,cyl((cx,cy,83),(cx,cy,78),3.6),'Kunststoff - matt (Schwarz)','Leg hub')
    for k in range(3):
        a=math.radians(90+120*k); top=(cx+3*math.cos(a),cy+3*math.sin(a),79.5); foot=(cx+42*math.cos(a),cy+42*math.sin(a),0.6)
        mid=tuple(top[i]+(foot[i]-top[i])*0.5 for i in range(3))
        add(c,cyl(top,mid,1.05),'Aluminium - eloxiert, rau (Grau)','Upper leg tube')
        add(c,cyl(mid,foot,0.8),'Aluminium - eloxiert, rau (Grau)','Lower leg tube')
        cl=tuple(top[i]+(foot[i]-top[i])*0.5 for i in range(3))
        add(c,cyl(tuple(top[i]+(foot[i]-top[i])*0.47 for i in range(3)),tuple(top[i]+(foot[i]-top[i])*0.53 for i in range(3)),1.35),'Kunststoff - matt (Schwarz)','Leg clamp')
        add(c,sph(foot,1.0),'Gummi - weich','Foot')
    o=newcomp('Room'); c=o.component
    add(c,box(0,20,-0.5,220,160,1),'Kunststoff - matt (Grau)','Floor')
    add(c,box(0,-39.88-1.0,85,220,2,170),'Kunststoff - matt (Weiß)','Wall')
    add(c,box(0,-39.865,H,29.7,0.03,21),'Papier (Weiß)','Graph paper')
    root.isOriginFolderLightBulbOn=False
    a=root.attributes
    for k,vv in (('H',H),('L',39.88),('d_um',7.417),('src_y',(43.3-9)/10),('src_z',H+(53.5-12)/10),('ap_y',(40.5-9)/10)):
        a.add('anim',k,str(vv))
    exec(open(os.path.join(REPO,'fusion','common.py'),encoding='utf8').read(),globals())
    print('saved',save_as('Laser diffraction station','ESP32 laser diffraction station on a tripod (generated by script)'))
    setup_view()
    print('ok')
