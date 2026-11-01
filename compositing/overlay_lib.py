"""Pillow helpers for 2D overlays: background, title cards, captions, callout labels, panels."""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math, os
W,H=1920,1080
FD='/usr/share/fonts/truetype/dejavu/'
def font(sz,bold=False): return ImageFont.truetype(FD+('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'),sz)
INK=(28,38,56); MUTED=(92,104,122); ACC=(232,135,0); PANEL=(255,255,255)
_bg=None
def background():
    global _bg
    if _bg is None:
        g=Image.new('RGBA',(1,H)); 
        for y in range(H):
            u=y/H; c=tuple(int(a+(b-a)*u) for a,b in zip((242,244,247),(218,223,230)))
            g.putpixel((0,y),c+(255,))
        _bg=g.resize((W,H))
    return _bg.copy()
def ease(u): u=max(0.0,min(1.0,u)); return u*u*(3-2*u)
def fade(f,a,b,fi=12,fo=12):
    if f<a or f>b: return 0.0
    return min(ease((f-a)/fi) if fi else 1, ease((b-f)/fo) if fo else 1)
def layer(): return Image.new('RGBA',(W,H),(0,0,0,0))
def alpha_paste(base,lay,al):
    if al<=0: return
    if al<1:
        a=lay.getchannel('A').point(lambda v:int(v*al)); lay=lay.copy(); lay.putalpha(a)
    base.alpha_composite(lay)
def shadow_box(lay,box,r=14,fill=(255,255,255,235)):
    sh=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(sh)
    x0,y0,x1,y1=box; d.rounded_rectangle((x0,y0+6,x1,y1+6),r,fill=(20,30,50,50))
    sh=sh.filter(ImageFilter.GaussianBlur(10)); lay.alpha_composite(sh)
    ImageDraw.Draw(lay).rounded_rectangle(box,r,fill=fill)
def title_card(base,f,a,b,title,sub,small=None):
    al=fade(f,a,b,18,18)
    if al<=0: return
    L=layer(); d=ImageDraw.Draw(L)
    ft=font(58,True); fs=font(30)
    tw=d.textlength(title,font=ft)
    x=110; y=110
    shadow_box(L,(x-40,y-36,x+max(tw,d.textlength(sub,font=fs),d.textlength(small,font=font(22)) if small else 0)+50,y+150+(44 if small else 0)),18)
    d.rectangle((x-40,y-36,x-32,y+150+(44 if small else 0)),fill=ACC)
    d.text((x,y),title,font=ft,fill=INK)
    d.text((x,y+82),sub,font=fs,fill=MUTED)
    if small: d.text((x,y+130),small,font=font(22),fill=MUTED)
    alpha_paste(base,L,al)
def caption(base,f,a,b,num,text,sub=None):
    al=fade(f,a,b,15,15)
    if al<=0: return
    L=layer(); d=ImageDraw.Draw(L)
    ft=font(34,True); fs=font(24)
    tw=max(d.textlength(text,font=ft), d.textlength(sub,font=fs) if sub else 0)
    x0=90; y0=H-(190 if sub else 150); bw=tw+170
    shadow_box(L,(x0,y0,x0+bw,H-60),16)
    d.ellipse((x0+28,y0+24,x0+92,y0+88),fill=ACC)
    nw=d.textlength(str(num),font=font(36,True)); d.text((x0+60-nw/2,y0+33),str(num),font=font(36,True),fill='white')
    d.text((x0+120,y0+30),text,font=ft,fill=INK)
    if sub: d.text((x0+120,y0+82),sub,font=fs,fill=MUTED)
    alpha_paste(base,L,al)
def label(base,f,a,anchor,pos,text,sub=None,side='right',b=10**9):
    al=fade(f,a,b,12,12)
    if al<=0: return
    L=layer(); d=ImageDraw.Draw(L)
    ft=font(28,True); fs=font(21)
    tw=max(d.textlength(text,font=ft), d.textlength(sub,font=fs) if sub else 0)
    bh=86 if sub else 54
    x,y=pos
    box=(x,y,x+tw+36,y+bh)
    ax,ay=anchor
    cx=box[0] if ax<box[0] else box[2]
    cy=(box[1]+box[3])//2
    d.line([(ax,ay),(cx,cy)],fill=INK+(255,),width=3)
    d.ellipse((ax-8,ay-8,ax+8,ay+8),fill=ACC,outline='white',width=3)
    shadow_box(L,box,10)
    d.text((x+18,y+12),text,font=ft,fill=INK)
    if sub: d.text((x+18,y+52),sub,font=fs,fill=MUTED)
    alpha_paste(base,L,al)
def footer(base,text):
    d=ImageDraw.Draw(base); fs=font(18)
    tw=d.textlength(text,font=fs); d.text((W-tw-30,H-34),text,font=fs,fill=(110,120,135,255))
def frame(path):
    bg=background()
    if path and os.path.exists(path): bg.alpha_composite(Image.open(path).convert('RGBA'))
    return bg
