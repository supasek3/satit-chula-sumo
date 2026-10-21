"""Runs the BASELINE over several seeds and collects KPIs.

    python3 run_seeds.py [n_seeds] [--net NET.net.xml] [--out DIR]
        ->  DIR/seed_<n>/..., DIR/kpi_seeds.csv, printed summary   (defaults: baseline net, DIR=output)

Each seed regenerates demand (make_baseline.py <seed>) and runs sumo with the same seed, with both crossings
driven by the demand-responsive guard controller (guard_control.py). Pedestrian-vehicle collisions are checked.
Vehicle delay = timeLoss + departDelay (time queued before entering); runs until every vehicle has finished.
At the end baseline.rou.xml / baseline_tls.add.xml are regenerated with seed 1 (the default files).
"""
import csv, os, re, statistics, subprocess, sys
import xml.etree.ElementTree as ET
import guard_control
from collections import defaultdict

ARGS = sys.argv[1:]
NET = ARGS[ARGS.index("--net") + 1] if "--net" in ARGS else None
OUT = ARGS[ARGS.index("--out") + 1] if "--out" in ARGS else "output"
N = int(ARGS[0]) if ARGS and ARGS[0].isdigit() else 10
DEMAND_END = 6000
QUEUE_LANES = {  # KPI name -> lane id prefix
    "queue_side_road_m": "31973404#0_",
    "queue_main_before_X1_m": "31993796#4_",
    "queue_main_P2_to_P1_m": "31993796#3_",
    "queue_main_mid_m": "31993796#3_M_",
    "queue_main_entry_m": "31993796#3_E_",
    "queue_soi11_before_X2_m": "31973416#1_",
}
TTC_LIMIT = 1.5  # s, vehicle-vehicle conflict threshold


def group(t):
    vid = t.get("id")
    if vid.startswith("main_"):
        lane = t.get("arrivalLane", "")
        return "P1_IN" if lane.startswith("P1_IN") else "P2_IN" if lane.startswith("P2_IN") else "MAIN"
    return re.sub(r"_\d+_\d+$", "", vid)


def run(seed):
    out = f"{OUT}/seed_{seed}"
    os.makedirs(out, exist_ok=True)
    subprocess.run([sys.executable, "make_baseline.py", str(seed)], check=True, capture_output=True)
    guard_control.run(["sumo", "-c", "baseline.sumocfg", "--seed", str(seed),
                    "--tripinfo-output", f"{out}/tripinfo.xml", "--summary-output", f"{out}/summary.xml",
                    "--person-summary-output", f"{out}/person_summary.xml", "--stop-output", f"{out}/stops.xml",
                    "--queue-output", f"{out}/queue.xml", "--statistic-output", f"{out}/statistics.xml",
                    "--device.ssm.probability", "1", "--device.ssm.file", f"{out}/ssm.xml",
                    "--device.ssm.measures", "TTC PET", "--collision.check-junctions", "true",
                    "--collision.action", "warn", "--no-warnings"] + (["--net-file", NET] if NET else []), seed)
    k = {"seed": seed}
    st = ET.parse(f"{out}/statistics.xml").getroot()
    k["teleports"] = int(st.find("teleports").get("total"))
    v = st.find("vehicles")
    k["veh_unfinished"] = int(v.get("running")) + int(v.get("waiting"))
    summ = ET.parse(f"{out}/summary.xml").getroot()
    k["max_queue_outside_entry_veh"] = max(int(x.get("waiting")) for x in summ)
    k["last_vehicle_done_min_after_0810"] = (max(float(x.get("time")) for x in summ if int(x.get("running")) + int(x.get("waiting")) > 0) - DEMAND_END) / 60
    k["collisions"] = int(st.find("safety").get("collisions"))

    loss, wait = defaultdict(list), defaultdict(list)
    arrived_by_end = 0
    ti = ET.parse(f"{out}/tripinfo.xml").getroot()
    for t in ti.findall("tripinfo"):   # delay = time lost on the road + time queued before entering the network
        loss[group(t)].append(float(t.get("timeLoss")) + float(t.get("departDelay")))
        arrived_by_end += float(t.get("arrival")) <= DEMAND_END
    for p in ti.findall("personinfo"):
        g = re.sub(r"_\d+_\d+$", "", p.get("id"))
        wait[g] += [float(w.get("waitingTime")) for w in p.findall("walk")]
    every = [x for v in loss.values() for x in v]
    k["veh_delay_all_s"] = statistics.mean(every)
    for g in ("MAIN", "P1_IN", "P2_IN", "P1_OUT", "P2_OUT", "SRC_SIDE_L", "SRC_SIDE_R"):
        k[f"delay_{g}_s"] = statistics.mean(loss[g])
    k["delay_SIDE_p95_s"] = sorted(loss["SRC_SIDE_L"] + loss["SRC_SIDE_R"])[int(0.95 * (len(loss["SRC_SIDE_L"]) + len(loss["SRC_SIDE_R"])))]
    for g, name in (("PED_MAIN", "X1"), ("PED_SECOND", "X2")):
        k[f"ped_wait_{name}_mean_s"] = statistics.mean(wait[g])
        k[f"ped_wait_{name}_p95_s"] = sorted(wait[g])[int(0.95 * len(wait[g]))]
    k["veh_arrived"] = len(every)
    k["veh_arrived_by_0810"] = arrived_by_end
    k["persons_arrived"] = sum(len(v) for v in wait.values())

    mq = defaultdict(float)
    for ts in ET.parse(f"{out}/queue.xml").getroot():
        for l in ts.iter("lane"):
            for name, pre in QUEUE_LANES.items():
                if l.get("id").startswith(pre) and l.get("id")[len(pre):].isdigit():
                    mq[name] = max(mq[name], float(l.get("queueing_length")))
    for name in QUEUE_LANES:
        k[name] = mq[name]

    stops = defaultdict(int)
    for s in ET.parse(f"{out}/stops.xml").getroot():
        stops[s.get("busStop")] += 1
    for b in ("bs_1", "bs_5", "bs_0", "bs_2", "bs_4"):
        k[f"dropoffs_{b}"] = stops[b]

    # SSM encounter types: 1-3 following (rear-end), 4-8 adjacent/merging, 9-11 crossing, 12-14 in junction egress.
    # Each encounter appears once per vehicle, so count unordered ego/foe pairs once.
    seen, conf = set(), defaultdict(int)
    for c in ET.parse(f"{out}/ssm.xml").getroot().iter("conflict"):
        m = c.find("minTTC")
        if m is None or m.get("value") in (None, "NA") or float(m.get("value")) >= TTC_LIMIT:
            continue
        pair = (frozenset((c.get("ego"), c.get("foe"))), c.get("begin"))
        if pair in seen:
            continue
        seen.add(pair)
        t = int(m.get("type"))
        conf["rear_end" if t <= 3 else "merge" if t <= 8 else "crossing" if t <= 11 else "junction"] += 1
    for cat in ("rear_end", "merge", "crossing", "junction"):
        k[f"conflicts_{cat}_TTC<{TTC_LIMIT}s"] = conf[cat]
    return k


rows = []
for s in range(1, N + 1):
    rows.append(run(s))
    print(f"seed {s} done", flush=True)
subprocess.run([sys.executable, "make_baseline.py", "1"], check=True, capture_output=True)

keys = list(rows[0])
with open(f"{OUT}/kpi_seeds.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=keys)
    w.writeheader()
    w.writerows(rows)

print(f"\nKPI over {N} seeds: mean  sd  min  max   (95% CI half-width)")
for key in keys[1:]:
    v = [r[key] for r in rows]
    m, sd = statistics.mean(v), (statistics.stdev(v) if N > 1 else 0.0)
    print(f"{key:30s} {m:9.1f} {sd:7.1f} {min(v):8.1f} {max(v):8.1f}   ±{2.262 * sd / N ** 0.5 if N == 10 else 1.96 * sd / N ** 0.5:.1f}")
