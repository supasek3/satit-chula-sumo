"""Compare all versions, 07:15-07:45 (peak; simulated from 06:30), from their seed results (tripinfo.xml + statistics.xml).

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
BEGIN = 2700.0   # with_delay: measure only cars/students planned to depart 07:15-07:45 (peak); 06:30-07:15 = warm-up
T95 = {2: 12.71, 3: 4.30, 4: 3.18, 5: 2.78, 6: 2.57, 7: 2.45, 8: 2.36, 9: 2.31, 10: 2.26}

VERSIONS = [  # key, label, folder, results dir, OPT_PRESET   (with_delay: camera delay at X1)
    ("baseline", "Baseline v7 (guard)", "1_Baseline/baseline_v7", "results_nodelay", ""),
    ("fluke_none", "Fluke, no delay", "2_Optimisations/scenario_fluke_v7", "results_nodelay", ""),
    ("fluke_eth", "Fluke, Ethernet", "2_Optimisations/scenario_fluke_v7_ethernet", "results_ethernet", ""),
    ("fluke_wifi", "Fluke, Wi-Fi", "2_Optimisations/scenario_fluke_v7_wifi", "results_wifi", ""),
    ("b_none", "Combo B, no delay", "2_Optimisations/scenario_combined_v7", "results_combo_B_nodelay", "combo_B"),
    ("b_eth", "Combo B, Ethernet", "2_Optimisations/scenario_combined_v7", "results_combo_B_ethernet", "combo_B"),
    ("b_wifi", "Combo B, Wi-Fi", "2_Optimisations/scenario_combined_v7", "results_combo_B_wifi", "combo_B"),
]

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
    kp = os.path.join(ROOT, folder, res, "kpi_seeds.csv")      # with_delay: camera stats + walk-with-car-inside
    if os.path.exists(kp):
        import csv as _csv
        for row in _csv.DictReader(open(kp)):
            if str(row.get("seed")) == str(seed):
                for c in ("x1_walk_with_car_inside_s", "camera_delay_mean_s", "camera_delay_max_s"):
                    k[c] = float(row.get(c) or 0)
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

base = res["baseline"]["per_seed"]   # with_delay: also see the per-version no-delay rows
KPI = ["delay_mean", "delay_median", "delay_p95", "journey_mean", "journey_median", "journey_p95", "X1_mean", "X1_median",
       "X1_p95", "X2_mean", "X2_median", "X2_p95", "delay_over_300", "delay_over_600", "X1_over_30", "cars", "finished",
       "on_road", "not_entered", "collisions", "teleports", "x1_walk_with_car_inside_s", "camera_delay_mean_s"]
rows = []
for key, r in res.items():
    row = dict(version=r["label"], key=key)
    for k in KPI:
        v = [p.get(k, 0.0) for p in r["per_seed"]]
        row[k], row[k + "_ci"] = float(np.mean(v)), ci(v)
        if key != "baseline":
            dif = [a.get(k, 0.0) - b.get(k, 0.0) for a, b in zip(r["per_seed"], base)]
            bm = np.mean([b.get(k, 0.0) for b in base])
            row[k + "_diff"], row[k + "_diff_ci"] = float(np.mean(dif)), ci(dif)
            row[k + "_pct"] = 100 * np.mean(dif) / bm if bm else float("nan")
        ref = {"fluke_eth": "fluke_none", "fluke_wifi": "fluke_none", "b_eth": "b_none", "b_wifi": "b_none"}.get(key)
        if ref in res:   # with_delay: the effect of the camera delay = same version, same seeds, without delay
            nd = res[ref]["per_seed"]
            dif = [a.get(k, 0.0) - b.get(k, 0.0) for a, b in zip(r["per_seed"], nd)]
            bm = np.mean([b.get(k, 0.0) for b in nd])
            row[k + "_vsnd"], row[k + "_vsnd_ci"] = float(np.mean(dif)), ci(dif)
            row[k + "_vsnd_pct"] = 100 * np.mean(dif) / bm if bm else float("nan")
    rows.append(row)

import csv
with open(os.path.join(OUT, "compare_camera_delay.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(dict.fromkeys(k for r in rows for k in r)), extrasaction="ignore")
    w.writeheader(); w.writerows(rows)
json.dump(dict(rows=rows, pooled={k: {m: [round(x, 2) for x in v] for m, v in p.items()} for k, p in pooled.items()}),
          open(os.path.join(OUT, "all_versions.json"), "w"))
print(f"\n{'version':14s} {'delay med':>10s} {'delay p95':>10s} {'delay mean':>11s} {'X1 p95':>8s} {'X2 p95':>8s} {'not in':>7s} {'coll':>5s}")
for r in rows:
    print(f"{r['version']:14s} {r['delay_median']:10.1f} {r['delay_p95']:10.1f} {r['delay_mean']:11.1f} {r['X1_p95']:8.1f} "
          f"{r['X2_p95']:8.1f} {r['not_entered']:7.1f} {r['collisions']:5.1f}")
