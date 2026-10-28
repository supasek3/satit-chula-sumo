"""Side-by-side KPI table of several result folders (each with kpi_seeds.csv), mean ± 95% CI over their seeds.

    python3 compare.py ../baseline_v6/results results_best screen/*
"""
import csv, glob, json, os, statistics, sys

KPIS = [("veh_delay_all_s", "delay all"), ("delay_with_student_s", "delay student"),
        ("delay_no_student_s", "delay no-stud"), ("ped_wait_X1_mean_s", "ped X1 mean"),
        ("ped_wait_X1_p95_s", "ped X1 p95"), ("ped_wait_X2_mean_s", "ped X2 mean"),
        ("max_queue_outside_entry_veh", "queue entry"), ("last_vehicle_done_min_after_0810", "last car min"),
        ("dropoffs_bs_0", "bs_0"), ("dropoffs_gate_left_total", "gate L"), ("dropoffs_bs_5", "bs_5"),
        ("collisions", "coll"), ("teleports", "telep")]
T = {2: 12.706, 3: 4.303, 4: 3.182, 5: 2.776, 6: 2.571, 7: 2.447, 8: 2.365, 9: 2.306, 10: 2.262}


def load(d):
    with open(os.path.join(d, "kpi_seeds.csv")) as f:
        return list(csv.DictReader(f))


def cell(rows, k):
    v = [float(r[k]) for r in rows if r.get(k) not in (None, "", "nan")]
    if not v:
        return "-"
    m = statistics.mean(v)
    if len(v) < 2:
        return f"{m:.1f}"
    return f"{m:.1f}±{T.get(len(v), 1.96) * statistics.stdev(v) / len(v) ** 0.5:.0f}"


dirs = [d for a in sys.argv[1:] for d in sorted(glob.glob(a)) if os.path.exists(os.path.join(d, "kpi_seeds.csv"))]
name_w = max(len(os.path.basename(d.rstrip("/"))) for d in dirs) + 2
print("folder".ljust(name_w) + "n  " + "".join(lbl.rjust(15) for _, lbl in KPIS))
for d in dirs:
    rows = load(d)
    print(os.path.basename(d.rstrip("/")).ljust(name_w) + f"{len(rows):<3d}" + "".join(cell(rows, k).rjust(15) for k, _ in KPIS))
    s = os.path.join(d, "settings.json")
    if os.path.exists(s) and "-v" in sys.argv:
        print("    ", json.load(open(s)))
