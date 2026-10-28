"""Builds the BASELINE demand and signal plans from baseline_inputs.csv.

    python3 make_baseline.py [seed]      ->  baseline.rou.xml, baseline_tls.add.xml

Time 0 = 06:30, end of demand 6000 s = 08:10. Logic follows the friend's AnyLogic model
(see CLAUDE.md 7b); every number below is labelled with its data class.
"""
import hashseed  # noqa: F401  v7: fixed PYTHONHASHSEED for repeatable runs
import csv, random, sys
from collections import defaultdict
import opt

ARGS = sys.argv[1:]
ROU = ARGS[ARGS.index("--rou") + 1] if "--rou" in ARGS else "baseline.rou.xml"      # scenario opt: per-run demand
TLS_FILE = ARGS[ARGS.index("--tls") + 1] if "--tls" in ARGS else "baseline_tls.add.xml"
SEED = int(ARGS[0]) if ARGS and ARGS[0].isdigit() else 1
rng = random.Random(SEED)

# ---- parameters -------------------------------------------------------------------------
# Main road volume: team decision = average of schedule 764.5 and field summary 420 (the 523 road-counter
# total was dropped to avoid double counting). Applied as a scale on the schedule's 15-min profile.
MAIN_TARGET = (764.5 + 420) / 2
# Team decision 2026-10-18: Soi 13 and both parking driveways (IN and OUT) carry only this share of their
# counts; the rest enters from the east on the main road and behaves like main-road cars
# (same drop-off rule, 70/30 west/south, Z1 eligible).
SIDE_SHARE = 0.10
PARK_SHARE = 0.10
P_DROP_L, DWELL_L = 0.83, (2.10, 6.71, 27.35)     # selectOutput1 / delay1 (MODEL shape)
P_DROP_R, DWELL_R = 0.0459, (1.40, 2.55, 7.68)    # selectOutput / delay (MODEL shape)
DWELL_Z1 = (2.10, 6.71, 27.35)                    # delay2 (MODEL shape)
# Team decision 2026-10-18: drop-offs average 35 s. Each fitted triangle is scaled so its mean is
# DWELL_MEAN_S (shape kept). Set DWELL_MEAN_S = None to use the original AnyLogic times.
DWELL_MEAN_S = opt.DWELL        # scenario opt: OPT_DWELL (v6: 35.0); same random draws, only scaled
if DWELL_MEAN_S:
    DWELL_L, DWELL_R, DWELL_Z1 = (tuple(round(x * DWELL_MEAN_S * 3 / sum(p), 2) for x in p)
                                  for p in (DWELL_L, DWELL_R, DWELL_Z1))
P_SOUTH = 0.30                                    # TURN_SOUTH 70/30 (MOCK)
# SCENARIO dynamic_dropoff, user decision 2026-10-19: "way too many purple cars" -> keep only this share of the cars
# with no student (no drop-off stop: through, parking IN/OUT, Soi 13). Own random stream, so every other car of the
# seed is exactly as in the baseline. Set to 1.0 for the baseline demand.
# v6, user decision 2026-10-21: add the removed 80% back -> all cars with no student (as in v0).
NO_STUDENT_KEEP = 1.00
P_SIDE_L_WEST = 0.10                              # side lane 1: 10% west, 90% south (MOCK, team decision)
VEH_GREEN = (2.00, 18.65, 66.55)                  # trafficLight vehicle phase (MODEL, fitted)
PED_GREEN = (0.20, 7.96, 22.68)                   # trafficLight pedestrian phase (MODEL, fitted)
YELLOW, ALL_RED = 3, 2                            # safety clearance added in SUMO (not in .alp)
TLS = {"X1": "10784747877", "X2": "J1"}
SIM_END = 14400                                   # signal plans cover demand + run-out

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

# ---- split Soi 13 / parking OUT counts: kept on their road vs moved to the main road ---------
kept, moved = {}, defaultdict(list)
for sid, share in (("SRC_SIDE_L", SIDE_SHARE), ("SRC_SIDE_R", SIDE_SHARE),
                   ("P1_OUT", PARK_SHARE), ("P2_OUT", PARK_SHARE)):
    for i, (_, _, c) in enumerate(B[sid]):
        k = n_of(int(c) * share)
        kept[sid, i] = k
        moved[i] += ["MOVED_" + sid] * (int(c) - k)

# ---- main road: L/R lanes, parking IN diverted out of it ------------------------------------
for i in range(len(B["SRC_MAIN_L"])):
    t0, t1, cL = B["SRC_MAIN_L"][i]
    cR = B["SRC_MAIN_R"][i][2]
    nL, nR = n_of(cL * scale), n_of(cR * scale)
    cars = [(1, "SRC_MAIN_L")] * nL + [(2, "SRC_MAIN_R")] * nR
    cars += [(1 if rng.random() < cL / (cL + cR) else 2, m) for m in moved[i]]
    rng.shuffle(cars)
    n_p1, n_p2 = n_of(int(B["P1_IN"][i][2]) * PARK_SHARE), n_of(int(B["P2_IN"][i][2]) * PARK_SHARE)
    roles = ["P1_IN"] * n_p1 + ["P2_IN"] * n_p2 + ["MAIN"] * max(0, len(cars) - n_p1 - n_p2)
    rng.shuffle(roles)
    for k, ((lane, label), role) in enumerate(zip(cars, roles)):
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
        v = dict(id=vid, frm=ENTRY, to=to, lane=lane, stops=stops, src=label)
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
        v["stops"] = [("bs_2", tri(DWELL_Z1))]   # v7 (Fluke fix 1): Z1 replaces any gate stop; one entrance per car

# ---- combined: Supasek's Z1 redirect (OPT_Z1_REDIRECT). Gate X1-only drop-offs that turn left into Soi 11 drop off at
# Gate X2 Z1 instead. Same own random stream as scenario_z1_dropoff_v7, so the same cars are chosen.
redir_rng = random.Random(SEED * 37 + 11)
n_redirected = 0
if opt.Z1_REDIRECT > 0:
    for _, v in veh:
        if v["to"] == SOUTH and [b for b, _ in v["stops"]] == ["bs_1"] and redir_rng.random() < opt.Z1_REDIRECT:
            v["stops"] = [("bs_2", redir_rng.triangular(DWELL_Z1[0], DWELL_Z1[2], DWELL_Z1[1]))]
            n_redirected += 1

# ---- parking OUT and side road ------------------------------------------------------------
for sid, frm in (("P1_OUT", "P1_OUT"), ("P2_OUT", "P2_OUT")):
    for i, (t0, t1, c) in enumerate(B[sid]):
        for k in range(kept[sid, i]):
            to = SOUTH if rng.random() < P_SOUTH else WEST
            veh.append((rng.uniform(t0, t1), dict(id=f"{sid}_{i}_{k}", frm=frm, to=to, lane="best", stops=[], src=sid)))
for sid, lane in (("SRC_SIDE_L", 1), ("SRC_SIDE_R", 2)):
    for i, (t0, t1, c) in enumerate(B[sid]):
        for k in range(kept[sid, i]):
            to = WEST if (lane == 1 and rng.random() < P_SIDE_L_WEST) else SOUTH
            veh.append((rng.uniform(t0, t1), dict(id=f"{sid}_{i}_{k}", frm=SIDE, to=to, lane=lane, stops=[], src=sid)))

# ---- pedestrians: far-side pads -> school side --------------------------------------------
for sid, frm, to, apos in (("PED_MAIN", "walk_gate_N", "31993796#5", 1.0),
                           ("PED_SECOND", "walk_J1_W", "31973416#1", 27.0)):
    for i, (t0, t1, c) in enumerate(B[sid]):
        for k in range(int(c)):
            ped.append((rng.uniform(t0, t1), f'    <person id="{sid}_{i}_{k}" depart="{{d:.2f}}" type="student">\n'
                        f'        <walk from="{frm}" to="{to}" arrivalPos="{apos}"/>\n    </person>'))

# ---- scenario: thin out the cars with no student ------------------------------------------
keep_rng = random.Random(SEED * 31 + 7)
n_before = len(veh)
veh = [(d, v) for d, v in veh if v["stops"] or keep_rng.random() < NO_STUDENT_KEEP]

# ---- scenario opt: "keep right unless dropping off at the gate" sign upstream of the east entry ----------------
# Cars from the east entry with no left-lane gate drop-off (bs_1) that go west or into a parking driveway use the
# right lane. Only the lane changes, not how many cars come or where they go. OPT_KEEP_RIGHT=1: cars turning south
# into Soi 11 keep their lane (the left turn is from the left lane only); =2: they too start in the right lane and
# move left after the crossing (use with OPT_PASS_RIGHT=1, or SUMO moves them back left at once).
n_kept_right = 0
if opt.KEEP_RIGHT:
    for _, v in veh:
        if v["frm"] == ENTRY and v["lane"] == 1 and (v["to"] in (WEST, "P1_IN", "P2_IN") or opt.KEEP_RIGHT == 2) and \
                not any(b == "bs_1" for b, _ in v["stops"]):
            v["lane"] = 2
            n_kept_right += 1

# ---- write routes -------------------------------------------------------------------------
items = []
for dep, v in veh:
    s = "".join(f'\n        <stop busStop="{b}" duration="{d:.1f}" parking="false"/>' for b, d in v["stops"])
    items.append((dep, f'    <trip id="{v["id"]}" type="car" depart="{dep:.2f}" from="{v["frm"]}" to="{v["to"]}" '
                       f'departLane="{v["lane"]}"><param key="source" value="{v["src"]}"/>{s}\n    </trip>'))
for dep, x in ped:
    items.append((dep, x.format(d=dep)))
items.sort(key=lambda a: a[0])
with open(ROU, "w") as f:
    f.write(f'<?xml version="1.0" encoding="UTF-8"?>\n<!-- generated by make_baseline.py seed={SEED}; inputs: baseline_inputs.csv -->\n<routes>\n'
            '    <vType id="car" vClass="passenger" guiShape="passenger" accel="2.6" decel="4.5" sigma="0.5" length="5.0" minGap="2.5" maxSpeed="13.89"/>\n'
            '    <vType id="student" vClass="pedestrian" color="1,0,1"/>\n')
    f.write("\n".join(x for _, x in items))
    f.write("\n</routes>\n")

# ---- write guard-like signal plans (independent per crossing) -----------------------------
with open(TLS_FILE, "w") as f:
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
print("vehicles by source:", dict(cnt), "total", len(veh), f"(no-student cars kept {NO_STUDENT_KEEP:.0%}, removed {n_before - len(veh)})")
print("drop-offs:", dict(stops), "| pedestrians:", len(ped), f"| opt: {opt.describe()}, moved to right lane {n_kept_right}, Z1 redirected {n_redirected}")
for i, want, got in z1_short:
    print(f"  WARNING Z1 bin {i}: target {want} but only {got} main cars turn south")
