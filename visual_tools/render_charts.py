"""Build five evidence-based README animations from the included CSV snapshots.

Usage:
    python visual_tools/render_charts.py
    python visual_tools/render_charts.py --only evolution_heatmap

Requires numpy, pandas, matplotlib and Pillow. No inference or network access.
Each chart has its own figure. Defaults supply all chart colors and colormaps.
Raw data are never modified or smoothed. Animation timing is presentation only.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DATA, GIFS, STILLS = (ROOT / "assets" / s for s in ("data", "gifs", "stills"))
METHODS = ["source_only", "ctta", "campe"]
NAMES = {"source_only": "Source Only", "domain_randomization": "Source Robustness",
         "direct_finetune": "Direct Fine-tune", "stdw": "STDW", "ctta": "CTTA", "campe": "CAMPE"}
PLANNERS = ["fixed", "fim", "dual_plane", "full_mpc"]
PLANNER_NAMES = {"fixed": "Fixed USV", "fim": "FIM Only", "dual_plane": "Dual-Plane", "full_mpc": "Full MPC (CAMPE)"}
REGIMES = ["gradual", "sudden", "joint", "recurrent"]
OOD = ["strong_current", "direction_switch", "long_burst_loss", "random_target",
       "deceptive_target", "sensor_anomaly", "severe_thruster", "adversarial_mix",
       "blackout_chase", "recurrent_shift"]
PHASES = [(0., 30., "Nominal"), (30., 63., "Mild"), (63., 99., "Moderate"), (99., 150., "Severe")]
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "axes.titleweight": "bold", "axes.linewidth": .8})


def read_csv(path: Path, required: Sequence[str]) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Missing included data snapshot: {path}")
    frame = pd.read_csv(path)
    missing = set(required) - set(frame.columns)
    if missing:
        raise ValueError(f"{path.name} is missing columns: {sorted(missing)}")
    return frame


def traces() -> dict[str, pd.DataFrame]:
    out = {m: read_csv(DATA / f"{m}_joint_seed0_trace.csv", ["step", "time_s", "radius_error"])
           for m in METHODS}
    for name, d in out.items():
        if len(d) != 301 or not np.array_equal(d.step.to_numpy(), np.arange(-1, 300)):
            raise ValueError(f"Unexpected time/row convention in {name}")
        if not np.allclose(d.time_s, np.arange(301) * .5):
            raise ValueError(f"Unexpected time spacing in {name}")
    return out


def benchmark(name: str) -> pd.DataFrame:
    return read_csv(DATA / "benchmarks" / f"{name}_raw.csv", ["scenario", "seed", "capture_success_medium"])


def header(eyebrow: str, title: str, subtitle: str):
    fig = plt.figure(figsize=(11, 6.6), dpi=100)
    fig.text(.06, .955, f"CAMPE  /  {eyebrow}", fontsize=10.5, fontweight="bold", va="center")
    fig.text(.06, .895, title, fontsize=22, fontweight="bold")
    fig.text(.06, .851, subtitle, fontsize=11)
    return fig


def axis_style(ax):
    ax.grid(True, linewidth=.65, alpha=.35)
    ax.set_axisbelow(True)
    ax.tick_params(labelsize=11)


def phases(ax):
    for left, right, name in PHASES:
        if left > 0:
            ax.axvline(left, linestyle=":", linewidth=1.0, alpha=.45)
        ax.text((left + right) / 2, 1.025, name, transform=ax.get_xaxis_transform(),
                ha="center", va="bottom", fontsize=10)


def pixels(fig) -> Image.Image:
    fig.canvas.draw()
    return Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[:, :, :3].copy())


def save_animation(frames: list[Image.Image], stem: str,
                   duration: int | list[int] = 110, still: Image.Image | None = None) -> None:
    if not frames:
        raise ValueError("Cannot save an animation without frames")
    GIFS.mkdir(parents=True, exist_ok=True)
    STILLS.mkdir(parents=True, exist_ok=True)
    indices = np.linspace(0, len(frames) - 1, min(6, len(frames)), dtype=int)
    montage = Image.new("RGB", (330 * len(indices), 198))
    for k, idx in enumerate(indices):
        montage.paste(frames[idx].resize((330, 198)), (330 * k, 0))
    palette = montage.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    indexed = [im.quantize(palette=palette, dither=Image.Dither.NONE) for im in frames]
    if isinstance(duration, int):
        durations = [duration] * len(frames)
        durations[0], durations[-1] = 650, 2400
    else:
        durations = duration
    if len(durations) != len(frames):
        raise ValueError("One duration is required per frame")
    indexed[0].save(GIFS / f"{stem}.gif", save_all=True, append_images=indexed[1:],
                    duration=durations, loop=0, optimize=True, disposal=1)
    (still if still is not None else frames[-1]).save(STILLS / f"{stem}.png", optimize=True)
    print(f"{stem}: {len(frames)} frames, {(GIFS / (stem + '.gif')).stat().st_size / 1e6:.2f} MB", flush=True)


def tracking_comparison() -> None:
    data = traces()
    fig = header("MATCHED MISSION REPLAY", "Can the formation withstand changing conditions?",
                 "Three controllers, the same Joint shift, seed 0 and Full MPC planner. Lower radial error is better.")
    ax = fig.add_axes([.10, .23, .845, .50])
    axis_style(ax)
    ymax = np.ceil(max(d.radius_error.max() for d in data.values())) + 1
    ax.set(xlim=(0, 150), ylim=(0, ymax), xlabel="Mission time (s)",
           ylabel="Mean absolute radial error (m)")
    phases(ax)
    lines = []
    for m, ls, lw in zip(METHODS, ["--", "-.", "-"], [1.8, 2., 2.7]):
        line, = ax.plot([], [], linestyle=ls, linewidth=lw, marker="o", markersize=4,
                        markevery=[-1], label=NAMES[m])
        lines.append(line)
    ax.legend(loc="lower center", bbox_to_anchor=(.5, 1.095), ncol=3, frameon=False)
    ax.axhline(3.5, linestyle=":", linewidth=1.1, alpha=.55)
    ax.text(149, 3.5 + .12, "3.5 m radial tolerance", ha="right", fontsize=9)
    clock = fig.text(.945, .955, "", ha="right", va="center", fontsize=10.5)
    means = {m: float(d.loc[d.step >= 0, "radius_error"].mean()) for m, d in data.items()}
    fig.text(.06, .105, "Episode means: " + "   |   ".join(f"{NAMES[m]} {means[m]:.2f} m" for m in METHODS), fontsize=10.5)
    fig.text(.06, .062, "Raw simulation traces, not multi-seed averages. Capture also requires angular, containment, safety and stability conditions.", fontsize=9.1)
    frames = []
    for n in np.unique(np.linspace(1, 301, 101, dtype=int)):
        for line, m in zip(lines, METHODS):
            d = data[m].iloc[:n]
            line.set_data(d.time_s, d.radius_error)
        clock.set_text(f"{(n - 1) * .5:05.1f} / 150.0 s")
        frames.append(pixels(fig))
    save_animation(frames, "tracking_comparison", 90)
    plt.close(fig)


def evolution_heatmap() -> None:
    raw = traces()["campe"]
    d = raw.loc[raw.step >= 0].reset_index(drop=True)
    target_speed = np.linalg.norm(np.diff(raw[["target_x", "target_y"]].to_numpy(), axis=0), axis=1) / .5
    auv_speed = np.stack([np.linalg.norm(np.diff(raw[[f"auv{i}_x", f"auv{i}_y"]].to_numpy(), axis=0), axis=1) / .5
                          for i in range(4)]).mean(axis=0)
    specs = [("Model drift", d.model_drift.to_numpy()),
             ("Total discrepancy", d.drift.to_numpy()),
             ("Kinematic novelty", d.kinematic_novelty.to_numpy()),
             ("Packet-error estimate", d.per.to_numpy()),
             ("Mean AoI", d.aoi.to_numpy()),
             ("Update strength", d.update_weight.to_numpy()),
             ("Control reservation", d.control_ratio.to_numpy()),
             ("Target speed", target_speed),
             ("Mean AUV speed", auv_speed),
             ("Formation score", d.score.to_numpy())]
    vals = np.vstack([v for _, v in specs])
    mins, maxs = vals.min(axis=1), vals.max(axis=1)
    scaled = (vals - mins[:, None]) / np.where(maxs > mins, maxs - mins, 1)[:, None]
    fig = header("OBSERVATIONS → ADAPTATION → BEHAVIOR", "Watch the adaptation signals evolve together",
                 "One CAMPE mission: environmental evidence, communication status, update strength and formation quality.")
    ax = fig.add_axes([.22, .24, .65, .51])
    im = ax.imshow(np.ma.masked_all_like(scaled), aspect="auto", interpolation="nearest",
                   origin="upper", extent=(0, 150, len(specs)-.5, -.5), vmin=0, vmax=1)
    ax.set_yticks(range(len(specs)), [n for n, _ in specs], fontsize=10.5)
    ax.set_xticks(np.arange(0, 151, 30))
    ax.set_xlabel("Mission time (s)")
    ax.tick_params(axis="y", length=0, pad=8)
    phases(ax)
    cax = fig.add_axes([.895, .24, .018, .51])
    cb = fig.colorbar(im, cax=cax)
    cb.set_label("Row-normalized intensity", fontsize=10)
    clock = fig.text(.945, .955, "", ha="right", fontsize=10.5, va="center")
    values = fig.text(.06, .117, "", fontsize=10.5)
    fig.text(.06, .073, "Each row is min-max scaled over this episode. Read changes within a row; colors do not compare physical magnitudes across rows.", fontsize=9)
    fig.text(.06, .040, "300 post-step records · 0.5 s per step · no smoothing · Joint / seed 0 · speeds derived from logged positions", fontsize=9)
    frames = []
    for n in np.unique(np.linspace(1, 300, 91, dtype=int)):
        mask = np.arange(300)[None, :] >= n
        im.set_data(np.ma.array(scaled, mask=np.broadcast_to(mask, scaled.shape)))
        row = d.iloc[n-1]
        clock.set_text(f"{row.time_s:05.1f} / 150.0 s")
        values.set_text(f"At this step:   model drift {row.model_drift:.2f}   |   update weight {row.update_weight:.2f}   |   mean AoI {row.aoi:.2f} s   |   formation {row.score:.2f}")
        frames.append(pixels(fig))
    save_animation(frames, "evolution_heatmap", 95)
    plt.close(fig)
    (DATA / "heatmap_normalization.json").write_text(json.dumps({
        "scope": "300 CAMPE post-step records from Joint / seed 0", "normalization": "(x-row_min)/(row_max-row_min); no smoothing",
        "rows": [{"name": n, "min": float(a), "max": float(b)} for (n, _), a, b in zip(specs, mins, maxs)]}, indent=2))


def radial_error_histogram() -> None:
    df = benchmark("adaptation")
    grouped = {m: df.loc[df.method == m].sort_values(["seed", "scenario"]).reset_index(drop=True) for m in METHODS}
    keys = grouped[METHODS[0]][["seed", "scenario"]]
    if any(len(d) != 40 or not d[["seed", "scenario"]].equals(keys) for d in grouped.values()):
        raise ValueError("Histogram requires the same 40 scenario-seed observations per method")
    bins = np.arange(0, 4.0001, .25)
    for d in grouped.values():
        if not d.radius_error.between(bins[0], bins[-1], inclusive="both").all():
            raise ValueError("Histogram bounds would omit observations")
    ymax = max(np.histogram(d.radius_error, bins=bins)[0].max() for d in grouped.values()) + 2
    fig = header("DISTRIBUTION ACROSS RECORDED EPISODES", "Is the tracking improvement consistent across runs?",
                 "True histograms of episode-mean radial error. Fixed bins and common axes; all 40 runs per method are included.")
    ax = fig.add_axes([.10, .23, .845, .50])
    tally = fig.text(.945, .955, "", ha="right", va="center", fontsize=10.5)
    fig.text(.06, .103, "4 structured regimes × 10 seeds per method. One observation is an episode mean, not an individual control step.", fontsize=10)
    fig.text(.06, .061, "Animation adds matched seed-scenario records; it does not represent training or mission time. Final frame shows all observations.", fontsize=9.1)
    frames = []
    for n in range(1, 41):
        ax.clear()
        axis_style(ax)
        vals = [grouped[m].radius_error.iloc[:n].to_numpy() for m in METHODS]
        labels = [f"{NAMES[m]}  (mean {v.mean():.2f} m)" for m, v in zip(METHODS, vals)]
        ax.hist(vals, bins=bins, histtype="step", linewidth=2.4, label=labels)
        ax.set(xlim=(0, 4), ylim=(0, ymax), xlabel="Episode-mean radial error (m) — lower is better",
               ylabel="Number of recorded episodes")
        ax.set_xticks(np.arange(0, 4.01, .5))
        ax.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
        ax.legend(loc="lower center", bbox_to_anchor=(.5, 1.06), ncol=3, frameon=False, fontsize=10)
        tally.set_text(f"{n:02d} / 40 episodes per method")
        frames.append(pixels(fig))
    save_animation(frames, "radial_error_histogram", 200)
    plt.close(fig)


def benchmark_heatmap() -> None:
    structured, ood = benchmark("adaptation"), benchmark("robustness")
    configs = [
        (structured, ["source_only", "domain_randomization", "direct_finetune", "stdw", "ctta", "campe"], REGIMES,
         ["Gradual", "Sudden", "Joint", "Recurrent"], "STRUCTURED SHIFTS  /  1 OF 2",
         "Which structured changes can each method handle?", "4 regimes × 10 seeds per method · medium-profile capture success · 6 methods",
         "Structured total: CAMPE 40/40 (100%); CTTA 16/40 (40%). These are observed finite-sample proportions.", "structured"),
        (ood, ["source_only", "domain_randomization", "ctta", "campe"], OOD,
         ["Strong\ncurrent", "Direction\nswitch", "Long burst\nloss", "Random\ntarget", "Deceptive\ntarget", "Sensor\nanomaly", "Severe\nthruster", "Adversarial\nmix", "Blackout\nchase", "Recurrent\nshift"],
         "ADDITIONAL OOD CONDITIONS  /  2 OF 2", "Where does generalization remain difficult?",
         "10 additional scenarios × 10 seeds per method · same fixed configuration · 4 evaluated methods",
         "OOD total: CAMPE 58/100 (58%); CTTA 49/100 (49%). The per-scenario view also exposes failures and trade-offs.", "ood")]
    frames, durations = [], []
    for df, methods, scenarios, labels, eyebrow, title, subtitle, foot, suffix in configs:
        counts = df.groupby(["method", "scenario"]).size().unstack().reindex(index=methods, columns=scenarios)
        if not (counts == 10).all().all():
            raise ValueError("Each heatmap cell must represent exactly ten episodes")
        values = 100 * df.groupby(["method", "scenario"]).capture_success_medium.mean().unstack().reindex(index=methods, columns=scenarios).to_numpy()
        fig = header(eyebrow, title, subtitle)
        ax = fig.add_axes([.19, .27, .70, .49])
        im = ax.imshow(np.ma.masked_all_like(values), vmin=0, vmax=100, alpha=.55,
                       aspect="auto", interpolation="nearest")
        ax.set_xticks(range(len(scenarios)), labels, fontsize=10 if len(scenarios) > 4 else 12)
        ax.set_yticks(range(len(methods)), [NAMES[m] for m in methods], fontsize=11)
        ax.tick_params(axis="both", length=0, pad=9)
        ax.set_xticks(np.arange(len(scenarios)+1)-.5, minor=True)
        ax.set_yticks(np.arange(len(methods)+1)-.5, minor=True)
        ax.tick_params(which="minor", length=0)
        ax.grid(which="minor", linewidth=.8, alpha=.30)
        cax = fig.add_axes([.915, .27, .016, .49])
        cb = fig.colorbar(im, cax=cax)
        cb.set_label("Capture success (%)", fontsize=10)
        texts = [[ax.text(j, i, "", ha="center", va="center", fontsize=15 if len(scenarios)>4 else 19,
                          fontweight="bold" if methods[i]=="campe" else "normal")
                  for j in range(len(scenarios))] for i in range(len(methods))]
        fig.text(.06, .125, foot, fontsize=9.8)
        fig.text(.06, .077, "Each cell is based on 10 seeds; both panels use a fixed 0–100% scale. Columns reveal final statistics, not training progress.", fontsize=9.2)
        fig.text(.06, .041, "Source: released adaptation_raw.csv / robustness_raw.csv. No interpolation between measured percentages.", fontsize=9)
        for n in range(1, len(scenarios)+1):
            mask = np.broadcast_to(np.arange(len(scenarios))[None, :] >= n, values.shape)
            im.set_data(np.ma.array(values, mask=mask))
            for i, row in enumerate(texts):
                for j, text in enumerate(row):
                    text.set_text(f"{values[i,j]:.0f}" if j < n else "")
            frames.append(pixels(fig))
            durations.append(450 if n < len(scenarios) else 4000)
        STILLS.mkdir(parents=True, exist_ok=True)
        frames[-1].save(STILLS / f"benchmark_heatmap_{suffix}.png", optimize=True)
        plt.close(fig)
    save_animation(frames, "benchmark_heatmap", durations)


def aoi_distribution() -> None:
    df = benchmark("control_plane")
    data = {p: np.sort(df.loc[df.planner==p, "aoi"].to_numpy()) for p in PLANNERS}
    if any(len(v)!=50 for v in data.values()):
        raise ValueError("AoI plot requires 50 episodes per selected planner")
    xmax = float(np.ceil(max(v.max() for v in data.values())))
    fig = header("MATCHED-RESOURCE COORDINATION", "How fresh is the information reaching the USV?",
                 "Empirical cumulative distributions of episode-mean AoI. Higher and farther left means fresher information.")
    ax = fig.add_axes([.10, .23, .845, .49])
    axis_style(ax)
    ax.set(xlim=(0, xmax), ylim=(0, 102), xlabel="Episode-mean Age of Information (s)",
           ylabel="Episodes at or below threshold (%)")
    ax.set_yticks(np.arange(0, 101, 20))
    lines, curves = [], []
    for p, ls in zip(PLANNERS, [":", "--", "-.", "-"]):
        v = data[p]
        x = np.r_[0, v, xmax]
        y = np.r_[0, np.arange(1, 51)*2, 100]
        curves.append((x,y))
        line, = ax.plot([],[], drawstyle="steps-post", linestyle=ls,
                        linewidth=2.6 if p=="full_mpc" else 1.9,
                        label=f"{PLANNER_NAMES[p]}  (mean {v.mean():.2f} s)")
        lines.append(line)
    ax.legend(loc="lower center", bbox_to_anchor=(.5, 1.065), ncol=2, frameon=False, fontsize=10)
    scan = fig.text(.945, .955, "", ha="right", fontsize=10.5, va="center")
    fig.text(.06, .107, "50 episodes per planner · fixed CAMPE follower · common bandwidth, speed limit and movement cap for movable USVs", fontsize=9.8)
    fig.text(.06, .063, "Four selected planners from Table IV; Fixed USV is stationary. The animation scans the AoI threshold, not mission or training time.", fontsize=9.1)
    frames = []
    for cut in np.linspace(0, xmax, 81):
        for line, (x, y) in zip(lines, curves):
            sel = x <= cut
            xx, yy = x[sel], y[sel]
            line.set_data(np.r_[xx, cut], np.r_[yy, yy[-1]])
        scan.set_text(f"AoI threshold: {cut:.1f} s")
        frames.append(pixels(fig))
    save_animation(frames, "aoi_distribution", 100)
    plt.close(fig)


RENDERERS = {f.__name__: f for f in [tracking_comparison, evolution_heatmap, radial_error_histogram,
                                    benchmark_heatmap, aoi_distribution]}

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", choices=list(RENDERERS), help="Render just one of the five charts")
    args = parser.parse_args()
    for name in ([args.only] if args.only else RENDERERS):
        RENDERERS[name]()

if __name__ == "__main__":
    main()
