"""Compare scenario results against baseline_v7 (same seeds, paired).

    python3 compare_v7.py                       # default set of result folders
    python3 compare_v7.py path/to/kpi_seeds.csv ...
"""
import csv, math, os, statistics as st, sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "baseline_v7/results/kpi_seeds.csv")
DEFAULT = ["scenario_opt_v7/results_best/kpi_seeds.csv", "scenario_z1_dropoff_v7/results/kpi_seeds.csv",
           "scenario_fluke_v7/results/kpi_seeds.csv"]
KPIS = [("veh_delay_all_s", "Vehicle delay (s)"), ("veh_journey_all_s", "Journey time (s)"),
        ("delay_with_student_s", "Delay, student cars (s)"), ("delay_no_student_s", "Delay, no-student cars (s)"),
        ("ped_wait_X1_mean_s", "Gate X1 ped wait, mean (s)"), ("ped_wait_X1_p95_s", "Gate X1 ped wait, p95 (s)"),
        ("ped_wait_X2_mean_s", "Gate X2 ped wait, mean (s)"), ("ped_wait_X2_p95_s", "Gate X2 ped wait, p95 (s)"),
        ("max_queue_outside_entry_veh", "Longest entry queue (cars)"), ("last_vehicle_done_min_after_0810", "Last car after 08:10 (min)"),
        ("veh_arrived_by_0810", "Cars finished by 08:10"), ("teleports", "Teleports"), ("collisions", "Collisions")]
T9 = 2.262  # t(0.05, 9)


def load(p):
    return {r["seed"]: r for r in csv.DictReader(open(p))}


def ci(v):
    return T9 * st.stdev(v) / math.sqrt(len(v)) if len(v) > 1 else 0.0


base = load(BASE)
files = sys.argv[1:] or [os.path.join(HERE, f) for f in DEFAULT]
for f in files:
    if not os.path.exists(f):
        print(f"\n(missing: {f})")
        continue
    sc = load(f)
    seeds = sorted(set(base) & set(sc), key=int)
    print(f"\n=== {os.path.relpath(f, HERE)}  vs baseline_v7  (seeds {','.join(seeds)})")
    print(f"{'KPI':32s} {'baseline_v7':>16s} {'scenario':>16s} {'change [95% CI]':>28s}")
    for k, name in KPIS:
        if k not in sc[seeds[0]]:
            continue
        b = [float(base[s][k]) for s in seeds]; x = [float(sc[s][k]) for s in seeds]; d = [a - c for a, c in zip(x, b)]
        md = st.mean(d); h = ci(d); mb = st.mean(b)
        pct = f" ({100 * md / mb:+.0f}%)" if mb else ""
        print(f"{name:32s} {st.mean(b):9.1f} ±{ci(b):5.1f} {st.mean(x):9.1f} ±{ci(x):5.1f} {md:+8.1f} [{md - h:+.1f}, {md + h:+.1f}]{pct}")
    k = "veh_delay_all_s"
    better = sum(float(sc[s][k]) < float(base[s][k]) for s in seeds)
    print(f"vehicle delay lower than baseline in {better}/{len(seeds)} seeds")
