"""Histogram + fitted normal ("bell") curve for four baseline measures, 07:00-07:45.

    python3 plot_distributions.py                                  # baseline_v7, all seeds in results/
    python3 plot_distributions.py 2_Optimisations/scenario_fluke_v7 # any version folder
    python3 plot_distributions.py <folder> --results results_combo_F

Reads every <folder>/<results>/seed_*/tripinfo.xml (falls back to <folder>/output/tripinfo.xml, the last GUI run)
and writes <folder>/distributions_0700_0745.png plus distribution_stats.csv.
Measures use the same definitions as run_seeds.py:
  car delay   = timeLoss + departDelay   (time lost on the road + time queued before entering)
  journey     = duration + departDelay   (planned departure -> arrival, drop-off included)
  ped wait X1 / X2 = waitingTime of each student at the gate crossing / the Soi 11 crossing
Cars still on the road at 07:45 are included with their values up to 07:45.
"""
import csv, glob, math, os, re, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ARGS = sys.argv[1:]
RES = ARGS[ARGS.index("--results") + 1] if "--results" in ARGS else "results"
pos = [a for i, a in enumerate(ARGS) if not a.startswith("--") and (i == 0 or ARGS[i - 1] != "--results")]
HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = pos[0] if pos else os.path.join(HERE, "1_Baseline", "baseline_v7")
NAME = os.path.basename(os.path.normpath(FOLDER)) + ("" if RES == "results" else f" ({RES})")

files = sorted(glob.glob(os.path.join(FOLDER, RES, "seed_*", "tripinfo.xml")))
src = f"{len(files)} seeds ({RES}/)"
if not files:
    files = [os.path.join(FOLDER, "output", "tripinfo.xml")]
    src = "1 run (output/, last GUI run)"
    if not os.path.exists(files[0]):
        sys.exit(f"no tripinfo.xml found in {FOLDER}/{RES}/seed_*/ or {FOLDER}/output/")

A = lambda line, k: float(re.search(rf' {k}="([^"]*)"', line).group(1))
data = {"delay": [], "journey": [], "X1": [], "X2": []}
for f in files:                       # line-by-line: also works on a file still being written by an open GUI
    person = None
    for line in open(f):
        s = line.lstrip()
        if s.startswith("<tripinfo "):
            data["delay"].append(A(s, "timeLoss") + A(s, "departDelay"))
            data["journey"].append(A(s, "duration") + A(s, "departDelay"))
        elif s.startswith("<personinfo "):
            pid = re.search(r' id="([^"]*)"', s).group(1)
            person = "X1" if pid.startswith("PED_MAIN") else "X2" if pid.startswith("PED_SECOND") else None
        elif s.startswith("<walk ") and person and ' waitingTime="' in s:
            data[person].append(A(s, "waitingTime"))

PANELS = [("delay", "Car delay per car", "seconds lost per car"),
          ("journey", "Car journey time", "seconds from planned departure to arrival"),
          ("X1", "Pedestrian wait at Gate X1", "seconds each student waited"),
          ("X2", "Pedestrian wait at Gate X2 (Soi 11)", "seconds each student waited")]
BAR, CURVE, INK, INK2, GRID, SURF = "#86b6ef", "#1c5cab", "#0b0b0b", "#52514e", "#e6e5e1", "#fcfcfb"

plt.rcParams.update({"font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.titleweight": "bold", "axes.titlesize": 12})
fig, axes = plt.subplots(2, 2, figsize=(13, 9), facecolor=SURF)
rows = []
for ax, (key, title, xlabel) in zip(axes.flat, PANELS):
    x = np.array(data[key])
    ax.set_facecolor(SURF)
    if len(x) < 2:
        ax.text(0.5, 0.5, "no data", ha="center", va="center", transform=ax.transAxes, color=INK2)
        ax.set_title(title, loc="left", color=INK)
        continue
    mu, sd, med, p95 = x.mean(), x.std(ddof=1), np.median(x), np.percentile(x, 95)
    skew = float(((x - mu) ** 3).mean() / x.std() ** 3) if x.std() > 0 else 0.0
    zero = 100 * (x == 0).mean()
    hi = max(p95 * 1.6, mu + 3 * sd) if x.max() > p95 * 1.6 else x.max()
    bins = np.linspace(0, max(hi, 1), 31)
    ax.hist(np.clip(x, 0, bins[-1]), bins=bins, density=True, color=BAR, edgecolor=SURF, linewidth=1.5,
            label="simulated (histogram)")
    g = np.linspace(0, bins[-1], 400)
    if sd > 0:
        ax.plot(g, np.exp(-0.5 * ((g - mu) / sd) ** 2) / (sd * math.sqrt(2 * math.pi)), color=CURVE, lw=2,
                label=f"normal (bell) curve, mean {mu:.0f} s, SD {sd:.0f} s")
    for v, ls, lab in ((med, "--", f"median {med:.0f} s"), (p95, ":", f"95th percentile {p95:.0f} s")):
        ax.axvline(v, color=INK2, lw=1.2, ls=ls, label=lab)
    ax.set_title(title, loc="left", color=INK)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("probability density")
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    note = f"n = {len(x):,}   skew = {skew:+.1f}" + (f"   {zero:.0f}% waited 0 s" if key in ("X1", "X2") else "")
    ax.text(1.0, 1.02, note, transform=ax.transAxes, ha="right", va="bottom", fontsize=9, color=INK2)
    ax.legend(frameon=False, fontsize=9, loc="upper right", labelcolor=INK)
    rows.append(dict(measure=title, n=len(x), mean_s=round(mu, 1), sd_s=round(sd, 1), median_s=round(med, 1),
                     p95_s=round(p95, 1), min_s=round(x.min(), 1), max_s=round(x.max(), 1), skew=round(skew, 2),
                     pct_zero=round(zero, 1)))

fig.suptitle(f"{NAME}: distributions 07:00-07:45  ·  {src}", x=0.01, ha="left", fontsize=14, fontweight="bold", color=INK)
fig.text(0.01, 0.005, "Bars = simulated values. Curve = normal distribution with the same mean and SD; a long right tail "
         "(positive skew) means the bell curve under-states the long waits,\nso use the median and 95th percentile for "
         "those. Values beyond the x-axis are counted in the last bar.", fontsize=8.5, color=INK2)
fig.tight_layout(rect=(0, 0.04, 1, 0.96))
png = os.path.join(FOLDER, "distributions_0700_0745.png")
fig.savefig(png, dpi=150, facecolor=SURF)
with open(os.path.join(FOLDER, "distribution_stats.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader(); w.writerows(rows)
for r in rows:
    print(f"{r['measure']:38s} n={r['n']:5d} mean={r['mean_s']:7.1f} sd={r['sd_s']:7.1f} median={r['median_s']:7.1f} "
          f"p95={r['p95_s']:7.1f} skew={r['skew']:+.2f}")
print("saved", png)
