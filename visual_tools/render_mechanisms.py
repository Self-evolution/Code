#!/usr/bin/env python3
"""Render the three explanatory CAMPE mechanism animations.

These are conceptual scientific diagrams, not recorded experiments.
Parameters and causal relationships follow Sections IV-A--IV-D of the
supplied CAMPE manuscript. No simulated performance is synthesized here.

Run: python visual_tools/render_mechanisms.py
Requires: Pillow >= 10; Matplotlib provides portable fallback fonts.
"""
from pathlib import Path
import math
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
GIFS = ROOT / 'assets' / 'gifs'
STILLS = ROOT / 'assets' / 'stills'
W, H, SCALE = 1100, 620, 2
BG = '#F5F8FC'
INK = '#13233C'
MUTED = '#56677C'
LINE = '#D5DFEB'
CYAN = '#089FB6'
CYAN_LT = '#E8F7FA'
PURPLE = '#7C65D1'
PURPLE_LT = '#F1EEFB'
ORANGE = '#E79A38'
ORANGE_LT = '#FFF4E4'
WHITE = '#FFFFFF'


def resolve_fonts(system_dir=Path('/usr/share/fonts/truetype/dejavu')):
    """Use the original fonts when present, or Matplotlib's bundled fonts."""
    regular = system_dir / 'DejaVuSans.ttf'
    bold = system_dir / 'DejaVuSans-Bold.ttf'
    if regular.is_file() and bold.is_file():
        return regular, bold
    from matplotlib.font_manager import FontProperties, findfont
    return (
        Path(findfont(FontProperties(family='DejaVu Sans', weight='normal'))),
        Path(findfont(FontProperties(family='DejaVu Sans', weight='bold'))),
    )


FONT, BOLD = resolve_fonts()


def font(size=20, bold=False):
    return ImageFont.truetype(str(BOLD if bold else FONT), round(size * SCALE))


def xy(points):
    return tuple(round(v * SCALE) for v in points)


def new():
    im = Image.new('RGB', (W * SCALE, H * SCALE), BG)
    return im, ImageDraw.Draw(im)


def txt(d, pos, text, size=20, fill=INK, bold=False, anchor=None):
    d.text(xy(pos), text, font=font(size, bold), fill=fill, anchor=anchor)


def rect(d, box, fill=WHITE, outline=None, radius=18, width=1):
    d.rounded_rectangle(xy(box), radius=round(radius*SCALE), fill=fill,
                        outline=outline, width=round(width*SCALE))


def line(d, points, fill=LINE, width=2):
    d.line([xy(p) for p in points], fill=fill, width=round(width*SCALE), joint='curve')


def circle(d, cx, cy, radius, fill, outline=None, width=1):
    d.ellipse(xy((cx-radius,cy-radius,cx+radius,cy+radius)), fill=fill,
              outline=outline,width=round(width*SCALE))


def arrow(d, start, end, color=LINE, width=2, head=8):
    line(d,[start,end],color,width)
    angle=math.atan2(end[1]-start[1],end[0]-start[0])
    pts=[end,
         (end[0]-head*math.cos(angle-0.5),end[1]-head*math.sin(angle-0.5)),
         (end[0]-head*math.cos(angle+0.5),end[1]-head*math.sin(angle+0.5))]
    d.polygon([xy(p) for p in pts], fill=color)


def pill(d, box, text, color=CYAN, bg=CYAN_LT, size=18):
    rect(d,box,bg,radius=12)
    txt(d,((box[0]+box[2])/2,(box[1]+box[3])/2),text,size,color,True,'mm')


def base(d,kicker,title,subtitle):
    txt(d,(44,25),kicker,18,CYAN,True)
    txt(d,(44,60),title,35,INK,True)
    txt(d,(44,111),subtitle,20,MUTED)
    line(d,[(44,144),(1056,144)],LINE,1)
    txt(d,(44,593),'CAMPE',18,MUTED,True)
    txt(d,(1056,593),'Conceptual illustration',18,MUTED,False,'ra')


def three_rate(t):
    im,d=new()
    base(d,'SYSTEM OVERVIEW / THREE-RATE COLLABORATION',
         'One closed loop. Three time scales.',
         'AUV motion, state freshness, and policy evolution continually inform one another.')
    phase=min(2,int(t*3))
    xs=[44,388,732]
    colors=[CYAN,PURPLE,ORANGE]
    bgs=[CYAN_LT,PURPLE_LT,ORANGE_LT]
    labels=['FAST AUV CONTROL','USV COORDINATION','SLOW POLICY EVOLUTION']
    metrics=['Every 0.5 s','Every 2.5 s','20-step window']
    lines=[['Sense and choose a safe action.','Execute on each AUV.'],
           ['Predict follower motion.','Gate planning with confidence.'],
           ['Filter evidence of change.','Tune the 16-weight adapter.']]
    for i,x in enumerate(xs):
        rect(d,(x,165,x+324,374),WHITE,colors[i] if phase==i else LINE,width=2 if phase==i else 1)
        pill(d,(x+20,184,x+304,216),labels[i],colors[i],bgs[i],18)
        txt(d,(x+20,239),metrics[i],23 if i<2 else 21,INK,True)
        txt(d,(x+20,282),lines[i][0],18,MUTED)
        txt(d,(x+20,311),lines[i][1],18,MUTED)
        for j in range(3):
            circle(d,x+22+j*13,349,3.5,colors[i] if j<=int((t*9)%3) else LINE)
    arrow(d,(369,265),(387,265),CYAN,2,6)
    arrow(d,(713,265),(731,265),PURPLE,2,6)
    # An explicit return arrow closes the information-motion loop.
    line(d,[(894,376),(894,389),(205,389),(205,376)],ORANGE,2)
    arrow(d,(205,389),(205,376),ORANGE,2,6)
    rect(d,(44,411,1056,550),WHITE,LINE)
    txt(d,(66,417),'TIMING OVER 10 s',18,MUTED,True)
    start,end=340,1024
    yvals=[454,491,528]
    lefts=['AUV actions','USV replanning','Evidence accumulates']
    progress=min(t*1.08,1.0)
    for i,y in enumerate(yvals):
        txt(d,(66,y),lefts[i],18,MUTED,False,'lm')
        line(d,[(start,y),(end,y)],LINE,3)
    for k in range(21):
        x=start+(end-start)*k/20
        circle(d,x,yvals[0],4,CYAN if k/20<=progress else LINE)
    for k in range(5):
        x=start+(end-start)*k/4
        rect(d,(x-5,yvals[1]-5,x+5,yvals[1]+5),PURPLE if k/4<=progress else LINE,radius=2)
    line(d,[(start,yvals[2]),(start+(end-start)*min(progress,1),yvals[2])],ORANGE,8)
    circle(d,start+(end-start)*min(progress,1),yvals[2],7,ORANGE)
    txt(d,(550,570),'A 20-step window smooths evidence; local micro-updates may occur at each step.',18,MUTED,False,'mm')
    return im


def policy_evolution(t):
    im,d=new()
    base(d,'POLICY EVOLUTION / CAUSAL ONBOARD ADAPTATION',
         'Adapt 16 weights. Keep the backbone frozen.',
         'Separate physical mismatch from communication degradation before trusting an update.')
    phase=min(3,int(t*4))
    for box,c,bg in [((44,164,537,280),CYAN,CYAN_LT),((563,164,1056,280),PURPLE,PURPLE_LT)]:
        rect(d,box,WHITE,c if phase==0 else LINE,width=2 if phase==0 else 1)
    txt(d,(66,184),'Physical / model evidence',23,CYAN,True)
    txt(d,(66,221),'Residuals, action effectiveness, motion novelty',18,MUTED)
    txt(d,(66,248),'Observable formation and escape risk',18,MUTED)
    txt(d,(585,184),'Communication evidence',23,PURPLE,True)
    txt(d,(585,221),'Age of Information (AoI) and packet loss',18,MUTED)
    txt(d,(585,248),'Freshness regulates confidence in experience',18,MUTED)
    arrow(d,(291,281),(291,303),CYAN,2)
    arrow(d,(810,281),(810,303),PURPLE,2)
    # A common bracket routes observed evidence to selection and adaptation.
    line(d,[(291,303),(810,303)],LINE,2)
    arrow(d,(448,303),(448,320),CYAN,2,6)
    arrow(d,(825,303),(825,320),PURPLE,2,6)
    boxes=[(44,321,284,520),(310,321,584,520),(610,321,1056,520)]
    colors=[CYAN,PURPLE,ORANGE]
    for j,b in enumerate(boxes):
        active=(phase==1 and j in [0,2]) or (phase in [2,3] and j==1)
        rect(d,b,WHITE,colors[j] if active else LINE,width=2 if active else 1)
    txt(d,(64,340),'Frozen source actor',19,INK,True)
    txt(d,(64,370),'Weights stay fixed',18,MUTED)
    # Tiny schematic neural network, fixed for every frame.
    for x1,x2,ny1,ny2 in [(86,158,3,4),(158,232,4,2)]:
        for a in range(ny1):
            for b in range(ny2):
                line(d,[(x1,431+(a-(ny1-1)/2)*21),(x2,431+(b-(ny2-1)/2)*21)],LINE,1)
    for x,n in [(86,3),(158,4),(232,2)]:
        for k in range(n):circle(d,x,431+(k-(n-1)/2)*21,7,CYAN)
    txt(d,(164,492),'Source behavior kept',18,MUTED,False,'mm')
    txt(d,(330,340),'Residual adapter',20,INK,True)
    txt(d,(330,370),'8 inputs × 2 outputs',18,MUTED)
    for r in range(8):
        for c in range(2):
            x=341+r*27;y=407+c*28
            pulse=phase==2 and (r+c+int(t*40))%5==0
            color=ORANGE if pulse else (PURPLE if phase!=0 else '#CFC5F0')
            rect(d,(x,y,x+20,y+20),color,radius=4)
    pill(d,(337,471,557,504),'16 trainable weights',PURPLE,PURPLE_LT,18)
    arrow(d,(285,418),(308,418),CYAN,2,6)
    arrow(d,(585,418),(608,418),PURPLE,2,6)
    txt(d,(630,340),'Choose from 18 safe candidates',20,INK,True)
    txt(d,(630,370),'Utility + priors − uncertainty',18,MUTED)
    selected=min(17,max(0,int((t-.25)*72))) if phase==1 else (9 if phase>=2 else -1)
    for j in range(18):
        x=655+(j%9)*43;y=417+(j//9)*32
        color=ORANGE if j==selected else '#DCE6F1'
        circle(d,x,y,8,color)
        if j==selected:circle(d,x,y,12,None,ORANGE,2)
    txt(d,(630,480),'Project geometry → execute safe action',18,MUTED)
    captions=[
        '01  Separate drift signals; risk and freshness regulate adaptation strength.',
        '02  Source and residual proposals enter conservative, safety-filtered action selection.',
        '03  Executed actions provide causal targets for a lightweight local micro-update.',
        '04  A consolidated low-drift anchor and trust regions restrain unnecessary change.',
    ]
    rect(d,(44,539,1056,579),[CYAN_LT,ORANGE_LT,PURPLE_LT,PURPLE_LT][phase],radius=12)
    txt(d,(550,559),captions[phase],18,INK,False,'mm')
    return im


def dual_plane(t):
    im,d=new()
    base(d,'COMMUNICATION / WORK-CONSERVING DUAL PLANE',
         'Protect state refresh. Reuse spare capacity.',
         'Control packets and adaptation-status telemetry share one acoustic resource.')
    phase=min(3,int(t*4))
    rect(d,(44,165,1056,283),WHITE,LINE)
    txt(d,(66,182),'SHARED SLOT CAPACITY',18,INK,True)
    txt(d,(1034,182),'Control reservation: 80–94%',18,CYAN,True,'ra')
    x0,x1,y0,y1=66,1034,224,254
    # Widths illustrate the allocation mechanism, not an experimental trace.
    reserved=.86
    actual=.58
    status=.28
    rect(d,(x0,y0,x1,y1),'#E7ECF4',radius=8)
    split=x0+(x1-x0)*reserved
    if phase==0:
        rect(d,(x0,y0,split,y1),CYAN,radius=8)
        rect(d,(split+3,y0,x1,y1),PURPLE,radius=8)
    elif phase==1:
        used=x0+(x1-x0)*actual
        rect(d,(x0,y0,used,y1),CYAN,radius=8)
        rect(d,(used+3,y0,split,y1),'#B9E6ED',radius=8)
        rect(d,(split+3,y0,x1,y1),PURPLE,radius=8)
    elif phase==2:
        used=x0+(x1-x0)*actual
        rect(d,(x0,y0,used,y1),CYAN,radius=8)
        rect(d,(used+3,y0,x1,y1),ORANGE_LT,ORANGE,radius=8,width=1)
        for k in range(3):
            cx=used+50+k*100+20*math.sin(t*math.pi*8)
            arrow(d,(cx,239),(cx+30,239),ORANGE,2,6)
    else:
        used=x0+(x1-x0)*actual; final=used+(x1-x0)*status
        rect(d,(x0,y0,used,y1),CYAN,radius=8)
        rect(d,(used+3,y0,final,y1),PURPLE,radius=8)
    # Control and telemetry lanes expose their differing purposes.
    rect(d,(44,305,537,443),WHITE,CYAN if phase in [0,1] else LINE,width=2 if phase in [0,1] else 1)
    rect(d,(563,305,1056,443),WHITE,PURPLE if phase==3 else LINE,width=2 if phase==3 else 1)
    pill(d,(64,324,517,357),'CONTROL PLANE',CYAN,CYAN_LT,18)
    pill(d,(583,324,1036,357),'ADAPTATION-STATUS PLANE',PURPLE,PURPLE_LT,18)
    txt(d,(66,375),'512 B packets · task-critical state refresh',19,INK)
    txt(d,(66,405),'Retry priority uses link state and geometry.',18,MUTED)
    txt(d,(585,375),'2048 B message · surface monitoring',19,INK)
    txt(d,(585,405),'Served only when residual capacity permits.',18,MUTED)
    # This independent lane makes the central causal distinction explicit.
    rect(d,(44,464,1056,515),CYAN_LT,radius=12)
    circle(d,70,490,6,CYAN)
    txt(d,(88,489),'Onboard adapter updates continue from local history; status delivery is not an update gate.',19,INK,False,'lm')
    captions=[
        '01  Reserve control capacity using observable risk, AoI, and packet loss.',
        '02  Transmit control packets; only actual attempts consume bytes.',
        '03  Return unused control and retransmission capacity to the same slot.',
        '04  Use residual capacity for status traffic: the realized split is flexible.',
    ]
    txt(d,(550,543),captions[phase],19,INK,False,'mm')
    txt(d,(550,571),'Bar widths are illustrative; the reservation is not a rigid split of realized traffic.',18,MUTED,False,'mm')
    return im


def render_one(name, fn, frames=80):
    full=[]
    for i in range(frames):
        im=fn(i/(frames-1)).resize((W,H),Image.Resampling.LANCZOS)
        full.append(im)
    # Use one shared palette to keep thin lines and lettering steady.
    palette_sheet=Image.new('RGB',(W*2,H*2),BG)
    selected=[0,frames//3,2*frames//3,frames-1]
    for j,k in enumerate(selected):palette_sheet.paste(full[k],((j%2)*W,(j//2)*H))
    palette=palette_sheet.quantize(colors=128)
    indexed=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in full]
    duration=[100]*frames
    duration[0]=800;duration[-1]=1400
    indexed[0].save(GIFS/f'{name}.gif',save_all=True,append_images=indexed[1:],
                    duration=duration,loop=0,optimize=True,disposal=1)
    full[-1].save(STILLS/f'{name}.png',optimize=True)
    print(name,(GIFS/f'{name}.gif').stat().st_size,'bytes',flush=True)


def main():
    for p in [GIFS,STILLS]:p.mkdir(parents=True,exist_ok=True)
    render_one('policy_evolution',policy_evolution)
    # The v2 homepage uses static architecture and allocation references.
    for name, fn in [('three_rate_loop', three_rate), ('dual_plane', dual_plane)]:
        fn(1.0).resize((W, H), Image.Resampling.LANCZOS).save(STILLS/f'{name}.png', optimize=True)


if __name__=='__main__':main()
