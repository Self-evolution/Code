"""Render the README's three data-based GIFs from the included data snapshots.

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

def signals():
    frames=[]
    times=TRACE.time_s.values
    panels=[("Formation score",[("score",TEAL,"Score")],(0,1.05)),
            ("Separate model drift from total drift",[("model_drift",PURPLE,"Model drift"),("drift",ORANGE,"Total drift")],(0,1.2)),
            ("Regulate the local update",[("update_weight",TEAL,"Update weight"),("kinematic_novelty",PURPLE,"Kinematic novelty")],(0,1.05)),
            ("Information age at the USV",[("aoi",ORANGE,"Mean AoI (s)")],(0,max(.8,TRACE.aoi.max()*1.08)))]
    for idx in np.linspace(0,len(TRACE)-1,91,dtype=int):
        t=times[idx];fig=plt.figure(figsize=(11,7.2),dpi=100,facecolor=BG)
        fig.text(.055,.95,"MEASURED ON THE SAME REPLAY",color=TEAL,size=12,weight="bold")
        fig.text(.055,.894,"Evidence, adaptation and information age",color=TEXT,size=22,weight="bold")
        fig.text(.945,.95,f"t = {t:5.1f} s",ha="right",color=MUTED,size=12,family="DejaVu Sans Mono")
        positions=[[.075,.555,.385,.255],[.565,.555,.385,.255],[.075,.205,.385,.255],[.565,.205,.385,.255]]
        for (title,series,ylim),pos in zip(panels,positions):
            ax=fig.add_axes(pos);style_axis(ax);ax.set_xlim(0,150);ax.set_ylim(*ylim)
            ax.set_xticks([0,30,60,90,120,150]);ax.set_title(title,loc="left",fontsize=13,pad=11,color=TEXT)
            for j,(a,b,_) in enumerate(PHASES):
                ax.axvspan(a,b,color=["#DCEEF1","#E4F1F3","#EAE5F3","#F5EBDD"][j],alpha=.3,zorder=0)
            for key,c,label in series:
                ax.plot(times[:idx+1],TRACE[key].values[:idx+1],c=c,lw=2,label=label)
                ax.plot(t,TRACE.iloc[idx][key],"o",c=c,ms=4)
            ax.axvline(t,c=MUTED,lw=.8,alpha=.6)
            ax.legend(loc="lower right" if title.startswith("Separate") else "lower left",fontsize=10.5,frameon=True,facecolor="white",edgecolor="none",framealpha=.9)
            if pos[1] < .4:
                ax.set_xlabel("Mission time (s)",fontsize=11)
        phase_bar(fig,t,.09)
        fig.text(.065,.039,"Joint shift  ·  seed 0  ·  raw, unsmoothed simulation signals  ·  no training curve is implied",color=MUTED,size=11)
        frames.append(frame(fig));plt.close(fig)
    save_gif(frames,"adaptation_signals",110)

def benchmarks():
    frames=[];g=SUMMARY["groups"]
    specs=[
        ("structured","Capture under structured shifts","4 regimes × 10 seeds = 40 episodes per method",["source_only","domain_randomization","direct_finetune","stdw","ctta","campe"],["Source Only","Source Robustness","Direct Fine-tune","STDW","CTTA","CAMPE"],"capture_percent",(0,115),"Medium-profile capture (%)",["100%","40 / 40 runs","CAMPE succeeds in every","tested structured-shift run."]),
        ("ood","Capture under additional OOD conditions","10 scenarios × 10 seeds = 100 episodes per method",["source_only","domain_randomization","ctta","campe"],["Source Only","Source Robustness","CTTA","CAMPE"],"capture_percent",(0,115),"Medium-profile capture (%)",["+9 pp","58% vs 49%","CAMPE versus CTTA across","the additional OOD suite."]),
        ("coordination","Fresher states under matched budgets","5 stress scenarios × 10 seeds = 50 episodes per planner",["fixed","fim","fim_mobility","dynamic_period","dual_plane","full_mpc"],["Fixed USV","FIM Only","FIM + Mobility","Dynamic Period","Dual Plane","Full MPC"],"aoi_s",(0,2.65),"Mean Age of Information (s) · lower is better",["38.4%","lower mean AoI","0.93 s versus 1.51 s","Full MPC versus FIM Only."])
    ]
    for slide,(group,title,sub,keys,labels,metric,xlim,xlabel,callout) in enumerate(specs):
        for tick in range(34):
            progress=min(1.,(tick+1)/20);p=1-(1-progress)**3
            fig=plt.figure(figsize=(11,6.2),dpi=100,facecolor=BG)
            fig.text(.055,.94,"RESULTS FROM THE RELEASED V3 CSVs",color=TEAL,size=12,weight="bold")
            fig.text(.055,.869,title,color=TEXT,size=22,weight="bold")
            fig.text(.055,.815,sub,color=MUTED,size=12)
            ax=fig.add_axes([.195,.24,.465,.49]);style_axis(ax)
            vals=[g[group][k][metric] for k in keys]
            colors=[TEAL if k in ["campe","full_mpc"] else PURPLE if k in ["ctta","fim"] else "#B8C5D7" for k in keys]
            y=np.arange(len(keys));ax.barh(y,np.array(vals)*p,color=colors,height=.58,zorder=3)
            ax.set_yticks(y,labels);ax.tick_params(axis="y",length=0,labelsize=12,colors=TEXT)
            ax.set_xlim(*xlim);ax.invert_yaxis();ax.grid(axis="y",visible=False);ax.set_xlabel(xlabel,fontsize=11)
            for j,v in enumerate(vals):
                label=f"{v:.0f}%" if metric=="capture_percent" else f"{v:.2f} s"
                ax.text(v*p+(1.5 if metric=="capture_percent" else .04),j,label,va="center",color=colors[j] if keys[j] in ["campe","full_mpc","ctta","fim"] else MUTED,fontsize=12,weight="bold")
            fig.patches.append(FancyBboxPatch((.71,.27),.24,.45,boxstyle="round,pad=.012,rounding_size=.014",transform=fig.transFigure,fc="#E3F2F4",ec="none"))
            fig.text(.735,.61,callout[0],color=TEAL,size=32,weight="bold")
            fig.text(.735,.55,callout[1],color=TEXT,size=15,weight="bold")
            fig.text(.735,.452,callout[2],color=MUTED,size=11.5)
            fig.text(.735,.411,callout[3],color=MUTED,size=11.5)
            fig.text(.055,.117,"Aggregate evidence  ·  observed proportions / means  ·  animated reveal, not a time series",color=MUTED,size=11)
            for k in range(3):
                fig.patches.append(Circle((.46+k*.04,.058),.006,transform=fig.transFigure,fc=TEAL if slide==k else "#CDD9E5",ec="none"))
            frames.append(frame(fig));plt.close(fig)
    # Add holds at the completed stage of each slide.
    durations=[90]*len(frames)
    for ix in [33,67,101]:durations[ix]=2300
    montage=Image.new("RGB",(1650,310))
    for k,i in enumerate([33,67,101]):montage.paste(frames[i].resize((550,310)),(550*k,0))
    pal=montage.quantize(colors=224)
    q=[f.quantize(palette=pal,dither=Image.Dither.NONE) for f in frames]
    q[0].save(GIFS/"benchmark_results.gif",save_all=True,append_images=q[1:],duration=durations,loop=0,optimize=True,disposal=1)
    static=Image.new("RGB",(1100,620*3),BG)
    for k,i in enumerate([33,67,101]):static.paste(frames[i],(0,620*k))
    static.save(STILLS/"benchmark_results.png",optimize=True)
    print("benchmark_results",len(frames),(GIFS/"benchmark_results.gif").stat().st_size,flush=True)

if __name__ == "__main__":
    replay()
    signals()
    benchmarks()
