"""Render the retained mission-replay GIF from its included trace snapshot.

Run from anywhere: python visual_tools/render_data_visuals.py
Dependencies: numpy, pandas, matplotlib, Pillow.
No model inference or external assets are used by this renderer.
"""
from pathlib import Path
import json
import math
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle, FancyBboxPatch
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "assets" / "data"
GIFS = ROOT / "assets" / "gifs"
STILLS = ROOT / "assets" / "stills"
GIFS.mkdir(parents=True, exist_ok=True)
STILLS.mkdir(parents=True, exist_ok=True)
TRACE = pd.read_csv(DATA / "campe_joint_seed0_trace.csv")
SUMMARY = json.loads((DATA / "benchmark_summary.json").read_text())
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 12,
                     "axes.titleweight": "bold", "axes.spines.top": False,
                     "axes.spines.right": False, "axes.linewidth": .8})
BG, TEXT, MUTED, GRID = "#F5F8FC", "#13233C", "#5D7089", "#DFE7F0"
TEAL, PURPLE, ORANGE, GREEN = "#089FB6", "#7C65D1", "#E79A38", "#249C7F"
NAVY, PANEL, WHITE = "#081829", "#11273D", "#ECF3FC"
AUV_COLORS = ["#58D9EA", "#B59AFF", "#6FE4B5", "#FFD280"]
PHASES = [(0,30,"Nominal"),(30,63,"Mild"),(63,99,"Moderate"),(99,150,"Severe")]

def frame(fig):
    fig.canvas.draw()
    return Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[:, :, :3].copy())

def save_gif(frames, stem, duration=100, still_index=-1):
    # A shared palette keeps colors stable from frame to frame.
    montage = Image.new("RGB", (550*4,330))
    for k, i in enumerate(np.linspace(0,len(frames)-1,4,dtype=int)):
        montage.paste(frames[i].resize((550,330)), (550*k,0))
    pal = montage.quantize(colors=224, method=Image.Quantize.MEDIANCUT)
    indexed=[f.quantize(palette=pal,dither=Image.Dither.NONE) for f in frames]
    durations=[duration]*len(frames)
    durations[0]=700; durations[-1]=1800
    indexed[0].save(GIFS/f"{stem}.gif",save_all=True,append_images=indexed[1:],
                    duration=durations,loop=0,optimize=True,disposal=1)
    frames[still_index].save(STILLS/f"{stem}.png",optimize=True)
    print(stem, len(frames), (GIFS/f"{stem}.gif").stat().st_size,flush=True)

def style_axis(ax, dark=False):
    fg = WHITE if dark else TEXT
    ax.set_facecolor(PANEL if dark else "#FFFFFF")
    ax.tick_params(colors="#9FB3CD" if dark else MUTED,labelsize=11)
    for s in ax.spines.values(): s.set_color("#34506C" if dark else GRID)
    ax.xaxis.label.set_color(fg); ax.yaxis.label.set_color(fg)
    ax.grid(True,color="#294059" if dark else GRID,lw=.6,alpha=.7)
    ax.set_axisbelow(True)

def phase_bar(fig, t, y=.075, dark=False):
    colors=["#226278","#2D7691","#7663A6","#B87942"] if dark else ["#DCEEF1","#C9E5EB","#E6DFF3","#F5E4CD"]
    ax=fig.add_axes([.065,y,.87,.048]);ax.set_xlim(0,150);ax.set_ylim(0,1);ax.axis("off")
    for (a,b,label),c in zip(PHASES,colors):
        ax.add_patch(Rectangle((a,0),b-a,1,fc=c,ec=NAVY if dark else BG,lw=2))
        ax.text((a+b)/2,.5,label,ha="center",va="center",color=WHITE if dark else TEXT,fontsize=11.5)
    ax.plot([t,t],[0,1],color=WHITE if dark else TEXT,lw=2.5)
    ax.plot(t,1.07,"v",color=WHITE if dark else TEXT,ms=7,clip_on=False)
    return ax

def replay():
    frames=[]
    coords=[]
    for prefix in ["target","usv"]+[f"auv{k}" for k in range(4)]:
        coords.append(TRACE[[f"{prefix}_x",f"{prefix}_y"]].values)
    allxy=np.vstack(coords)
    lo=np.floor((allxy.min(axis=0)-8)/10)*10; hi=np.ceil((allxy.max(axis=0)+8)/10)*10
    # Equal geometric scale is used in both views.
    for idx in np.linspace(0,len(TRACE)-1,101,dtype=int):
        row=TRACE.iloc[idx]; t=row.time_s
        fig=plt.figure(figsize=(11,7.2),dpi=100,facecolor=NAVY)
        fig.text(.055,.95,"CAMPE  /  SIMULATION REPLAY",color=AUV_COLORS[0],weight="bold",size=12)
        fig.text(.055,.889,"Coordinating around a moving target",color=WHITE,weight="bold",size=23)
        fig.text(.945,.95,f"{t:05.1f} / 150 s",ha="right",color=WHITE,size=13,family="DejaVu Sans Mono")
        ax=fig.add_axes([.065,.285,.505,.51]);style_axis(ax,True)
        ax.set_xlim(lo[0],hi[0]);ax.set_ylim(lo[1],hi[1]);ax.set_aspect("equal",adjustable="box")
        ax.set_xlabel("World x (m)",fontsize=12);ax.set_ylabel("World y (m)",fontsize=12)
        current=np.array([[row[f"auv{k}_x"],row[f"auv{k}_y"]] for k in range(4)])
        tx,ty=row.target_x,row.target_y
        for k,c in enumerate(AUV_COLORS):
            p=coords[k+2][:idx+1];ax.plot(p[:,0],p[:,1],color=c,lw=1.8,alpha=.7)
            ax.plot(current[k,0],current[k,1],"o",mec=NAVY,mew=1.3,ms=10,color=c,zorder=7)
        order=np.argsort(np.arctan2(current[:,1]-ty,current[:,0]-tx))
        ring=current[np.r_[order,order[0]]]
        ax.fill(ring[:,0],ring[:,1],color=AUV_COLORS[0],alpha=.045,zorder=1)
        ax.plot(ring[:,0],ring[:,1],color="#5299B2",alpha=.5,lw=1,zorder=2)
        ax.add_patch(Circle((tx,ty),18,fill=False,ec="#7692AB",lw=1.1,ls=(0,(4,4)),zorder=1))
        for prefix,c,mark in [("target","#FF8C9F","*"),("usv","#FFFFFF","D")]:
            p=TRACE.iloc[:idx+1];ax.plot(p[f"{prefix}_x"],p[f"{prefix}_y"],color=c,lw=2,alpha=.8)
            ax.plot(row[f"{prefix}_x"],row[f"{prefix}_y"],mark,color=c,ms=15 if prefix=="target" else 9,mec=NAVY,mew=1,zorder=8)
        ax.text(.02,.96,"WORLD VIEW",transform=ax.transAxes,color="#9FB3CD",size=10.5,va="top",weight="bold")
        rel=fig.add_axes([.65,.445,.295,.35]);style_axis(rel,True)
        rel.set_xlim(-37,37);rel.set_ylim(-37,37);rel.set_aspect("equal")
        rel.set_xticks([-30,0,30]);rel.set_yticks([-30,0,30])
        rel.add_patch(Circle((0,0),18,fill=False,ec="#7692AB",lw=1.3,ls=(0,(4,4))))
        for k,c in enumerate(AUV_COLORS):
            start=max(0,idx-22)
            pts=coords[k+2][start:idx+1]-coords[0][start:idx+1]
            rel.plot(pts[:,0],pts[:,1],c=c,lw=2,alpha=.65)
            rel.plot(current[k,0]-tx,current[k,1]-ty,"o",c=c,ms=10,mec=NAVY,mew=1.2)
        rel.plot(0,0,"*",c="#FF8C9F",ms=15)
        rel.set_xlabel("Relative x (m)",fontsize=11.5)
        rel.set_ylabel("Relative y (m)",fontsize=11.5)
        fig.text(.65,.824,"TARGET-CENTERED VIEW",color="#9FB3CD",weight="bold",size=10.5)
        fig.text(.65,.325,"RADIAL ERROR",color="#9FB3CD",size=10.5)
        fig.text(.65,.28,f"{row.radius_error:.2f} m",color=WHITE,size=23,weight="bold")
        fig.text(.825,.325,"MEAN AoI",color="#9FB3CD",size=10.5)
        fig.text(.825,.28,f"{row.aoi:.2f} s",color=WHITE,size=23,weight="bold")
        fig.text(.065,.174,"● AUV team     ◆ USV     ★ Moving target     - -  Desired 18 m ring",color="#BDCEE2",size=11)
        phase_bar(fig,t,.085,True)
        fig.text(.065,.036,"Joint domain shift  ·  seed 0  ·  current-code CPU rollout  ·  accelerated replay",color="#9FB3CD",size=11)
        frames.append(frame(fig));plt.close(fig)
    save_gif(frames,"mission_replay",100,still_index=70)


if __name__ == "__main__":
    replay()
