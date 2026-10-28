"""Builds the BASELINE demand and signal plans from baseline_inputs.csv.

    python3 make_baseline.py [seed]      ->  baseline.rou.xml, baseline_tls.add.xml

Time 0 = 06:30, end of demand 6000 s = 08:10. Logic follows the friend's AnyLogic model
(see CLAUDE.md 7b); every number below is labelled with its data class.
"""
import csv, random, sys
from collections import defaultdict

SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 1
rng = random.Random(SEED)

# ---- parameters -------------------------------------------------------------------------
# Main road volume: team decision = average of the three totals (schedule 764.5, field summary 420,
# road counter 523). Applied as a scale on the schedule's 15-min profile.
MAIN_TARGET = (764.5 + 420 + 523) / 3
P_DROP_L, DWELL_L = 0.83, (2.10, 6.71, 27.35)     # selectOutput1 / delay1 (MODEL shape)
P_DROP_R, DWELL_R = 0.0459, (1.40, 2.55, 7.68)    # selectOutput / delay (MODEL shape)
DWELL_Z1 = (2.10, 6.71, 27.35)                    # delay2 (MODEL shape)
# Team decision 2026-10-18: drop-offs average 35 s. Each fitted triangle is scaled so its mean is
# DWELL_MEAN_S (shape kept). Set DWELL_MEAN_S = None to use the original AnyLogic times.
DWELL_MEAN_S = 35.0
if DWELL_MEAN_S:
    DWELL_L, DWELL_R, DWELL_Z1 = (tuple(round(x * DWELL_MEAN_S * 3 / sum(p), 2) for x in p)
                                  for p in (DWELL_L, DWELL_R, DWELL_Z1))
P_SOUTH = 0.30                                    # TURN_SOUTH 70/30 (MOCK)
P_SIDE_L_WEST = 0.10                              # side lane 1: 10% west, 90% south (MOCK, team decision)
VEH_GREEN = (2.00, 18.65, 66.55)                  # trafficLight vehicle phase (MODEL, fitted)
PED_GREEN = (0.20, 7.96, 22.68)                   # trafficLight pedestrian phase (MODEL, fitted)
YELLOW, ALL_RED = 3, 2                            # safety clearance added in SUMO (not in .alp)
TLS = {"X1": "10072794956", "X2": "J1"}
SIM_END = 7200                                    # signal plans cover demand + run-out

ENTRY = "31993796#3_E"
WEST, SOUTH = "31993793", "31973416#1.32"
SIDE = "31973404#0"


def tri(p):                       # (low, mode, high) -> sample
    return rng.triangular(p[0], p[2], p[1])


def bins_of(rows):
    t, out = 0, []
    for r in rows:
        d = int(r["duration_min"]) * 60
        out.append((t, t + d, float(r["count"])))
        t += d
    return out


def n_of(x):                      # stochastic rounding keeps totals unbiased
    return int(x) + (rng.random() < x - int(x))


src = defaultdict(list)
with open("baseline_inputs.csv") as f:
    for r in csv.DictReader(f):
        src[r["source_id"]].append(r)
B = {k: bins_of(v) for k, v in src.items()}

main_raw = sum(c for k in ("SRC_MAIN_L", "SRC_MAIN_R") for _, _, c in B[k])
scale = MAIN_TARGET / main_raw

veh, ped = [], []                  # (depart, xml)
south_main = defaultdict(list)     # bin index -> main-road vehicles turning south (Z1 candidates)

# ---- main road: L/R lanes, parking IN diverted out of it ------------------------------------
for i in range(len(B["SRC_MAIN_L"])):
    t0, t1, cL = B["SRC_MAIN_L"][i]
    cR = B["SRC_MAIN_R"][i][2]
    nL, nR = n_of(cL * scale), n_of(cR * scale)
    lanes = [1] * nL + [2] * nR
    rng.shuffle(lanes)
    n_p1, n_p2 = int(B["P1_IN"][i][2]), int(B["P2_IN"][i][2])
    roles = ["P1_IN"] * n_p1 + ["P2_IN"] * n_p2 + ["MAIN"] * max(0, len(lanes) - n_p1 - n_p2)
    rng.shuffle(roles)
    for k, (lane, role) in enumerate(zip(lanes, roles)):
        vid = f"main_{i}_{k}"
        dep = rng.uniform(t0, t1)
        if role != "MAIN":
            veh.append((dep, dict(id=vid, frm=ENTRY, to=role, lane=lane, stops=[], src=role)))
            continue
        stops = []
        if lane == 1 and rng.random() < P_DROP_L:
            stops.append(("bs_1", tri(DWELL_L)))
        elif lane == 2 and rng.random() < P_DROP_R:
            stops.append(("bs_5", tri(DWELL_R)))
        to = SOUTH if rng.random() < P_SOUTH else WEST
        v = dict(id=vid, frm=ENTRY, to=to, lane=lane, stops=stops, src="SRC_MAIN_" + "LR"[lane - 1])
        veh.append((dep, v))
        if to == SOUTH:
            south_main[i].append(v)

# ---- Z1 second drop-off: pick exactly the MOCK target among south-turning main cars -------
z1_short = []
for i, (_, _, target) in enumerate(B["DROPOFF_SECOND"]):
    cand = south_main[i]
    k = min(int(target), len(cand))
    if k < target:
        z1_short.append((i, int(target), len(cand)))
    for v in rng.sample(cand, k):
        v["stops"].append(("bs_2", tri(DWELL_Z1)))

# ---- parking OUT and side road ------------------------------------------------------------
for sid, frm in (("P1_OUT", "P1_OUT"), ("P2_OUT", "P2_OUT")):
    for i, (t0, t1, c) in enumerate(B[sid]):
        for k in range(int(c)):
            to = SOUTH if rng.random() < P_SOUTH else WEST
            veh.append((rng.uniform(t0, t1), dict(id=f"{sid}_{i}_{k}", frm=frm, to=to, lane="best", stops=[], src=sid)))
for sid, lane in (("SRC_SIDE_L", 1), ("SRC_SIDE_R", 2)):
    for i, (t0, t1, c) in enumerate(B[sid]):
        for k in range(int(c)):
            to = WEST if (lane == 1 and rng.random() < P_SIDE_L_WEST) else SOUTH
            veh.append((rng.uniform(t0, t1), dict(id=f"{sid}_{i}_{k}", frm=SIDE, to=to, lane=lane, stops=[], src=sid)))

# ---- pedestrians: far-side pads -> school side --------------------------------------------
for sid, frm, to, apos in (("PED_MAIN", "walk_gate_N", "31993796#4", 1.0),
                           ("PED_SECOND", "walk_J1_W", "31973416#1", 27.0)):
    for i, (t0, t1, c) in enumerate(B[sid]):
        for k in range(int(c)):
            ped.append((rng.uniform(t0, t1), f'    <person id="{sid}_{i}_{k}" depart="{{d:.2f}}" type="student">\n'
                        f'        <walk from="{frm}" to="{to}" arrivalPos="{apos}"/>\n    </person>'))

# ---- write routes -------------------------------------------------------------------------
items = []
for dep, v in veh:
    s = "".join(f'\n        <stop busStop="{b}" duration="{d:.1f}" parking="false"/>' for b, d in v["stops"])
    items.append((dep, f'    <trip id="{v["id"]}" type="car" depart="{dep:.2f}" from="{v["frm"]}" to="{v["to"]}" '
                       f'departLane="{v["lane"]}"><param key="source" value="{v["src"]}"/>{s}\n    </trip>'))
for dep, x in ped:
    items.append((dep, x.format(d=dep)))
items.sort(key=lambda a: a[0])
with open("baseline.rou.xml", "w") as f:
    f.write(f'<?xml version="1.0" encoding="UTF-8"?>\n<!-- generated by make_baseline.py seed={SEED}; inputs: baseline_inputs.csv -->\n<routes>\n'
            '    <vType id="car" vClass="passenger" guiShape="passenger" accel="2.6" decel="4.5" sigma="0.5" length="5.0" minGap="2.5" maxSpeed="13.89"/>\n'
            '    <vType id="student" vClass="pedestrian" color="1,0,1"/>\n')
    f.write("\n".join(x for _, x in items))
    f.write("\n</routes>\n")

# ---- write guard-like signal plans (independent per crossing) -----------------------------
with open("baseline_tls.add.xml", "w") as f:
    f.write(f'<?xml version="1.0" encoding="UTF-8"?>\n<!-- generated by make_baseline.py seed={SEED}: guard-like plans, '
            f'vehicle G~tri{VEH_GREEN}, ped G~tri{PED_GREEN}, yellow {YELLOW}s, all-red {ALL_RED}s -->\n<additional>\n')
    for name, tid in TLS.items():
        f.write(f'    <tlLogic id="{tid}" type="static" programID="baseline" offset="0">  <!-- {name} -->\n')
        t = 0
        while t < SIM_END:
            g, p = max(1, round(tri(VEH_GREEN))), max(1, round(tri(PED_GREEN)))
            for dur, st in ((g, "GGr"), (YELLOW, "yyr"), (p, "rrG"), (ALL_RED, "rrr")):
                f.write(f'        <phase duration="{dur}" state="{st}"/>\n')
                t += dur
        f.write("    </tlLogic>\n")
    f.write("</additional>\n")

# ---- summary ------------------------------------------------------------------------------
cnt = defaultdict(int)
for _, v in veh:
    cnt[v["src"]] += 1
stops = defaultdict(int)
for _, v in veh:
    for b, _ in v["stops"]:
        stops[b] += 1
print(f"seed {SEED}: main scale {scale:.4f} (raw {main_raw:.1f} -> target {MAIN_TARGET:.1f})")
print("vehicles by source:", dict(cnt), "total", len(veh))
print("drop-offs:", dict(stops), "| pedestrians:", len(ped))
for i, want, got in z1_short:
    print(f"  WARNING Z1 bin {i}: target {want} but only {got} main cars turn south")
