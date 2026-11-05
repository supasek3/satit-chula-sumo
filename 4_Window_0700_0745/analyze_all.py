"""Compare all versions, 07:00-07:45, from their seed results (tripinfo.xml + statistics.xml).

    python3 analyze_all.py [--seeds 5] [--root <folder with the results tree>]

Per seed and version: car delay / journey (incl. cars still on the road at 07:45, and cars still WAITING TO ENTER at
07:45, whose delay so far = 07:45 - planned departure, journey the same), pedestrian waits at X1/X2.
Every statistic is computed per seed, then averaged over seeds (+- 95% CI); "vs baseline" is the paired difference.
Writes compare_all_0700_0745.csv and all_versions.json next to this script (or --out).
"""
import json, math, os, re, subprocess, sys, tempfile, shutil, statistics as st
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
A = sys.argv[1:]
NS = int(A[A.index("--seeds") + 1]) if "--seeds" in A else 5
ROOT = A[A.index("--root") + 1] if "--root" in A else HERE
OUT = A[A.index("--out") + 1] if "--out" in A else HERE
END = 4500.0
BEGIN = 1800.0   # measure only cars/students planned to depart 07:00-07:45 (06:30-07:00 = warm-up)
T95 = {2: 12.71, 3: 4.30, 4: 3.18, 5: 2.78, 6: 2.57, 7: 2.45, 8: 2.36, 9: 2.31, 10: 2.26}

VERSIONS = [  # key, label, folder, results dir, OPT_PRESET
    ("baseline", "Baseline v7", "1_Baseline/baseline_v7", "results_warm5", ""),
    ("fluke", "Fluke", "2_Optimisations/scenario_fluke_v7", "results_warm5", ""),
    ("z1", "Z1 left-turn", "2_Optimisations/scenario_z1_dropoff_v7", "results_warm5", ""),
    ("poom", "Poom (best)", "2_Optimisations/scenario_opt_v7", "results_best_warm5", "best"),
] + [(f"combo_{c}", f"Combo {c}", "2_Optimisations/scenario_combined_v7", f"results_combo_{c}_warm5", f"combo_{c}") for c in "ABCDEF"]

GEN = {}  # (folder, preset, seed) -> {trip id: planned depart}


def planned(folder, preset, seed):
    """Regenerate the seed's demand (make_baseline.py is deterministic) in a temp copy; return trip departures."""
    k = (folder, preset, seed)
    if k not in GEN:
        src = os.path.join(HERE, folder)
        tmp = tempfile.mkdtemp()
        for f in os.listdir(src):
            if f.endswith(".py") or f.endswith(".csv"):
                shutil.copy(os.path.join(src, f), tmp)
        env = dict(os.environ, OPT_PRESET=preset) if preset else {k2: v for k2, v in os.environ.items() if k2 != "OPT_PRESET"}
        subprocess.run([sys.executable, "make_baseline.py", str(seed)], cwd=tmp, env=env, check=True, capture_output=True)
        GEN[k] = {m.group(1): float(m.group(2)) for m in
                  re.finditer(r'<trip id="([^"]+)" type="car" depart="([\d.]+)"', open(os.path.join(tmp, "baseline.rou.xml")).read())}
        shutil.rmtree(tmp)
    return GEN[k]


def attr(s, k):
    return float(re.search(rf' {k}="([^"]*)"', s).group(1))


def one_seed(folder, res, preset, seed):
    d = os.path.join(ROOT, folder, res, f"seed_{seed}")
    delay, journey, ped = [], [], {"X1": [], "X2": []}
    seen, person, finished = set(), None, 0
    for line in open(os.path.join(d, "tripinfo.xml")):
        s = line.lstrip()
        if s.startswith("<tripinfo "):
            seen.add(re.search(r' id="([^"]*)"', s).group(1))
            if attr(s, "depart") - attr(s, "departDelay") < BEGIN:
                continue
            delay.append(attr(s, "timeLoss") + attr(s, "departDelay"))
            journey.append(attr(s, "duration") + attr(s, "departDelay"))
            finished += attr(s, "arrival") >= 0
        elif s.startswith("<personinfo "):
            pid = re.search(r' id="([^"]*)"', s).group(1)
            person = "X1" if pid.startswith("PED_MAIN") else "X2" if pid.startswith("PED_SECOND") else None
            if attr(s, "depart") < BEGIN:
                person = None
        elif s.startswith("<walk ") and person and ' waitingTime="' in s:
            ped[person].append(attr(s, "waitingTime"))
    plan = planned(folder, preset, seed)
    not_in = [END - t for i, t in plan.items() if i not in seen and BEGIN <= t < END]   # still waiting to enter at 07:45
    delay += not_in
    journey += not_in
    stat = open(os.path.join(d, "statistics.xml")).read()
    v = re.search(r"<vehicles [^>]*>", stat).group(0)
    k = dict(cars=len(delay), finished=finished, on_road=int(attr(v, "running")), not_entered=len(not_in),
             collisions=int(attr(re.search(r"<safety [^>]*>", stat).group(0), "collisions")),
             teleports=int(attr(re.search(r"<teleports [^>]*>", stat).group(0), "total")))
    for name, x in (("delay", delay), ("journey", journey), ("X1", ped["X1"]), ("X2", ped["X2"])):
        x = np.array(x)
        k[f"{name}_mean"], k[f"{name}_median"], k[f"{name}_p95"] = x.mean(), np.median(x), np.percentile(x, 95)
    k["delay_over_300"] = 100 * (np.array(delay) > 300).mean()
    k["delay_over_600"] = 100 * (np.array(delay) > 600).mean()
    k["X1_over_30"] = 100 * (np.array(ped["X1"]) > 30).mean()
    return k, dict(delay=delay, journey=journey, X1=ped["X1"], X2=ped["X2"])


def ci(v):
    return T95.get(len(v), 1.96) * st.stdev(v) / math.sqrt(len(v)) if len(v) > 1 else 0.0


res, pooled = {}, {}
for key, label, folder, rdir, preset in VERSIONS:
    seeds = [s for s in range(1, NS + 1) if os.path.exists(os.path.join(ROOT, folder, rdir, f"seed_{s}", "statistics.xml"))]
    if len(seeds) < NS:
        print(f"skip {label}: only {len(seeds)} of {NS} seeds")
        continue
    per = [one_seed(folder, rdir, preset, s) for s in seeds]
    res[key] = dict(label=label, seeds=seeds, per_seed=[p for p, _ in per])
    pooled[key] = {m: sum((q[m] for _, q in per), []) for m in ("delay", "journey", "X1", "X2")}
    print("done", label)

base = res["baseline"]["per_seed"]
KPI = ["delay_mean", "delay_median", "delay_p95", "journey_mean", "journey_median", "journey_p95", "X1_mean", "X1_median",
       "X1_p95", "X2_mean", "X2_median", "X2_p95", "delay_over_300", "delay_over_600", "X1_over_30", "cars", "finished",
       "on_road", "not_entered", "collisions", "teleports"]
rows = []
for key, r in res.items():
    row = dict(version=r["label"], key=key)
    for k in KPI:
        v = [p[k] for p in r["per_seed"]]
        row[k], row[k + "_ci"] = float(np.mean(v)), ci(v)
        if key != "baseline":
            dif = [a[k] - b[k] for a, b in zip(r["per_seed"], base)]
            bm = np.mean([b[k] for b in base])
            row[k + "_diff"], row[k + "_diff_ci"] = float(np.mean(dif)), ci(dif)
            row[k + "_pct"] = 100 * np.mean(dif) / bm if bm else float("nan")
    rows.append(row)

import csv
with open(os.path.join(OUT, "compare_all_0700_0745.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[1].keys()) if len(rows) > 1 else list(rows[0].keys()), extrasaction="ignore")
    w.writeheader(); w.writerows(rows)
json.dump(dict(rows=rows, pooled={k: {m: [round(x, 2) for x in v] for m, v in p.items()} for k, p in pooled.items()}),
          open(os.path.join(OUT, "all_versions.json"), "w"))
print(f"\n{'version':14s} {'delay med':>10s} {'delay p95':>10s} {'delay mean':>11s} {'X1 p95':>8s} {'X2 p95':>8s} {'not in':>7s} {'coll':>5s}")
for r in rows:
    print(f"{r['version']:14s} {r['delay_median']:10.1f} {r['delay_p95']:10.1f} {r['delay_mean']:11.1f} {r['X1_p95']:8.1f} "
          f"{r['X2_p95']:8.1f} {r['not_entered']:7.1f} {r['collisions']:5.1f}")
