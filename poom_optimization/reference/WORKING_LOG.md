# CLAUDE.md — Satit Chula Smart Drop-off + Pedestrian Crossing (SUMO)

Context handoff for Claude Code. Last updated 2026-10-18 (Asia/Bangkok, UTC+7).
Owner: Supasek (macOS, user `garnacho99`, project at `~/Desktop/SUMO_Project`, conda `(base)` shell).

---

## 1. Project in one paragraph
Automate the human security guard who currently acts as a "manual traffic light" at the
zebra crossing in front of the gate of **Satit Chulalongkorn Demonstration School** (Bangkok)
during the **morning peak**. Phase 1 = SUMO simulation: build a data-grounded *baseline* of
today's situation, then simulate and compare optimization scenarios. Phase 2 = hardware
prototype of the winning strategy (own CCTV + object detection, optional sensor fusion,
microcontroller signal controller, ped/vehicle signals), evaluated on site.

## 2. Site facts (from the project brief)
- Road in front of school: **two-lane, one-way**, traffic flows **east → west**.
- School front wall **180 m** long, **gate in the middle**, **zebra crossing directly in front of the gate**.
- **Thailand = left-hand traffic.** Network is built with `lefthand="true"` (verified).
- Current behaviour: parents drop students along the **left lane** (school side), between the
  **left (west) end of the wall and the zebra crossing**. Right lane and the whole stretch
  *behind/upstream of* the crossing are unused, yet traffic is heavy → the drop-off pattern
  itself is a big part of the problem.
- Layout sketch (project doc `gemini-code-…txt`):
  - **Inflows 1 & 2**: East entry of the 2-lane E→W main corridor.
  - **Inflows 3 & 4**: two **2-way driveways on the north side** (north-mid, north-east).
  - **Zones 2 & 3**: drop-off stops on the main corridor.
  - **West exit** at the west end; a **south turn** into the north–south road
    (Soi Chulalongkorn 11 / ซอยจุฬาลงกรณ์ 11), which has **Zone 1 (south drop-off)** and a **south exit**.
- Reference image (project file `Screenshot 2569-10-18 at 13.40.06.png`): satellite view with
  **two orange-hatched crossings** the user wants:
  1. **Main gate crossing** on the E–W road (with waiting pads on the north and south sides).
  2. **Lower-left crossing** on the N–S road (Soi Chula 11), further south.

## 3. Data, scope, metrics, controllers
- Real data: **~2 h manual counts, one Tuesday morning peak** (school CCTV angle unusable for counting).
  → Baseline scoped to AM peak only; small counts seed/calibrate SUMO (arrival rates, ped demand,
  queues); SUMO then generates the large synthetic data for optimization/RL. Representativeness
  and sim-to-real risk acknowledged → keep a deterministic rule-based fallback in Phase 2.
- **Measures (baseline vs each scenario):** vehicle delay, queue length, pedestrian waiting time,
  throughput, vehicle–pedestrian conflicts (surrogate, e.g. SSM device).
- **Controllers to test:**
  1. *Fixed algorithm first* (guaranteed feasible): **Webster** (cycle/splits) +
     **vehicle-actuated** gap-out/max-out + **PHB/HAWK** demand-actuated protected ped phase.
  2. *RL second, if time*: SUMO-RL / Berkeley Flow, trained on generated demand.
- Other hypotheses: organized drop-off scheme (use right lane / area upstream of crossing).
- Phase 1 loop: collect data → baseline → hypothesis → simulate → compare → repeat → pick best → hardware.

## 4. Environment notes
- User's Mac has **SUMO / netedit 1.28.0** (netconvert on PATH; otherwise use `$SUMO_HOME/bin`).
- Harmless warnings on every netconvert run: `Could not set locale to 'C'` and
  `pj_obj_create: Cannot find proj.db` (PROJ data path) — ignore.
- Net projection: UTM zone 47, netOffset `-664897.52,-1519094.99`.
- Rule: **never overwrite `network.net.xml`** (the user's netedit master). All generated nets go to new files.

## 5. File inventory (`~/Desktop/SUMO_Project`)
| File | Role / status |
|---|---|
| `network.net.xml` | **Master network** saved from netedit 1.28 (12:24). Untouched by scripts. |
| `satit.net.xml` | Older network (10:24), backup, not referenced. |
| `dropoff.add.xml` | 5 `busStop`s used as drop-off zones (see §7). |
| `satit.rou.xml` | vTypes + 2 flows (see §8). Needs work. |
| `satit.sumocfg` | `net-file=network.net.xml`, `route-files=satit.rou.xml`, `additional-files=dropoff.add.xml`. |
| `fix_sidewalks.py` | Generates `network_base.net.xml` from master (see §9). |
| `crossings.nod.xml` | 2 new pad nodes for the far-side footpaths. |
| `crossings.edg.xml` | 2 new pedestrian-only footpath edges. |
| `crossings.con.xml` | The 2 `<crossing>` definitions. |
| `make_crossings.sh` | Runs fix_sidewalks.py then netconvert → `network_crossings.net.xml`. |
| `network_base.net.xml` | Generated intermediate (cleaned master). |
| `network_crossings.net.xml` | Generated output — valid, 2 signalized crossings (Attempt 3, see §9). |
| `Screenshot 2569-10-18 at 12.40.45.png` | OSM map of Chula campus area (context only). |

## 6. Network topology (master `network.net.xml`)
Coordinates in SUMO net metres. Every road edge originally had **4 lanes**:
`_0` sidewalk (`allow="pedestrian"`, 2.0 m), `_1` and `_2` vehicle lanes, `_3` second sidewalk.
In this left-hand net, **lane `_0` is the school side** on both roads.

| Edge | From → To | Notes |
|---|---|---|
| `31993796#3` | `cluster_10068082487_10072794948_10784747883` (526,155) → `10072794956` (279.6,199.1) | Main corridor, E→W, 250 m, upstream of gate |
| `31993796#4` | `10072794956` → `10784747877` (241.4,204.6) | Main corridor downstream of gate, 39 m |
| `31993796#5` | `10784747877` → `358217462` (202.3,211.5) | 34 m |
| `1085984275#0` | `358217462` → `cluster10784747874_358216946_J0` (169,210.2) | 8 m |
| `31993793` | `cluster10784747874_358216946_J0` → `2106360898` (21.4,238.6) | West exit |
| `31973404#0` | `280758819` (228,342) → `358217462` | Road from north (Soi Chula 13) |
| `31973416#0` | `cluster10784747874_358216946_J0` → `cluster_10784747894_9950744948` (159.6,165.6) | Soi Chula 11 southbound |
| `31973416#1` | `cluster_10784747894_9950744948` → `J1` (157,127.4) | Soi Chula 11, 33 m |
| `31973416#1.32` | `J1` → `358227907` (132.5,−21.5) | Soi Chula 11 south of J1, 151 m, south exit |
| `E0` (J2→J3), `E1` (J4→J5) | around x≈316–328, y 190–211 | **North driveway pair (Inflow 3)**, 2 lanes (`_0` ped, `_1` veh). **Not connected** to main road (dead ends). |
| `E2` (J6→J7), `E3` (J8→J9) | around x≈435–448, y 172–195 | **North driveway pair (Inflow 4)**, same, **not connected**. |

Signalized junctions (both `traffic_light`, mid-block, 1 in-edge + 1 out-edge):
- **`10072794956` = MAIN GATE crossing** on the E–W corridor (between `31993796#3` and `#4`).
  Original tlLogic: `GG 82s / yy 3s / rr 5s` (vehicle links only, lanes 1–2).
- **`J1` = Soi Chula 11 crossing** (lower-left orange box).
  Original tlLogic: `GGGG 10s / yyyy 3s / rrrr 5s` (4 links incl. sidewalk lanes 0 and 3 — wrong).
- Neither had any `<crossing>` before today.

## 7. Drop-off zones (`dropoff.add.xml`)
Resized 2026-10-18 to hold a set number of cars (7.5 m per car = 5.0 m length + 2.5 m minGap).
Positions use `network_crossings.net.xml` lane lengths; the network and crossings are unchanged.
Verified in sumo: the peak number of cars stopped equals the capacity; extra cars queue behind and are served later.
| id | lane | pos | cars | Data zone |
|---|---|---|---|---|
| `bs_0` | `31993796#4_1` | 4.33–26.83 | 3 | west (downstream) of X1, left lane |
| `bs_1` | `31993796#3_1` | 4.87–34.87 | 4 | Z2+Z3 left (`curbSpots_L`), east of X1 |
| `bs_5` | `31993796#3_2` | 4.87–34.87 | 4 | Z2+Z3 right (`curbSpots_R`) |
| `bs_2` | `31973416#1_1` | 0.15–28.15 | 4 | Z1 (`curbSpots2_L`), before X2 |
| `bs_4` | `31973416#1.32_1` | 4.66–34.66 | 4 | after X2, no counterpart in the data |
Each busStop carries `name=` with the friend's AnyLogic zone (Z2Z3_L, Z2Z3_R, Z1); bs_0 and bs_4 are SUMO-only zones
kept by the user's decision (positions and capacities final). Previous version: `dropoff.add.xml.bak`. (`.bak2` = before names.)

**Netedit edit + lane extension (2026-10-18 15:19 onward):** the user moved J1 (X2) and `pad_J1_W` about 20 m north in
netedit (J1 now at 160.24,148.34) and saved `network_crossings.net.xml` (backup: `network_crossings.netedit_1519.net.xml`).
That left `31973416#1` at 22.06 m (3 cars). To fit 4 cars without moving X2, the pass-through node
`cluster_10784747894_9950744948` (only #0→#1) was slid ~6 m north along the road with `soi11.nod.xml` + `soi11.edg.xml`
(`netconvert -s network_crossings.net.xml --node-files soi11.nod.xml --edge-files soi11.edg.xml`). Now `#1` = 28.15 m,
`#0` = 19.31 m. Crossings, TLS, J1 and pads are unchanged (verified, pedestrians cross both).
**⚠ `make_crossings.sh` rebuilds from the master net and would undo both the J1 move and the node move**; treat the
current `network_crossings.net.xml` as the working network and patch it, or bake both edits into the scripts first.

## 7b. Team decisions (2026-10-18)
- **SUMO is the team's model of record**; the friend's AnyLogic model is unfinished and used only as a data/logic source.
- Drop-off: positions and capacities in `dropoff.add.xml` are final. Baseline uses bs_1 (Z2Z3_L), bs_5 (Z2Z3_R), bs_2 (Z1);
  bs_0 and bs_4 are kept but unused in the baseline. Main drop-off is upstream of X1, both lanes; Z1 left lane only.
- X2 pedestrians: `PED_SECOND` 222/100 min (MOCK, 15-min bins), `walk_J1_W` → school side, same control rule as X1
  but independent timing; ped wait KPI reported per crossing.
- Side road = SUMO `31973404#0` (Soi Chula 13), as in the current network.
- SecondDropoff 105, SecondPed 222, 70/30 straight/south: accepted MOCK. Main-road 152–344 treated provisionally as veh/h/lane
  (UNIT_FIX_REQUIRED / RAW_SOURCE_UNVERIFIED; field summary 420 cars and counter 523 vehicles do not reconcile).
- Count data from 18 Aug (Tue), 16 Sep (Wed), 25 Sep (Fri) 2026; window 06:30–08:10 = 6000 s.

## 7c. Driveways + BASELINE build (2026-10-18)
**Driveways connected** (`driveways.nod.xml/.edg.xml/.con.xml`, applied with netconvert to the working net;
backup `network_crossings.before_driveways.net.xml`): old stubs E0–E3 removed; main road split into
`31993796#3_E` (east entry → P2) → `31993796#3_M` (P2 → P1) → `31993796#3` (P1 → X1, 34.87 m; keeps its id).
New edges `P1_IN/P1_OUT` (P1_node ↔ P1_lot, north-mid) and `P2_IN/P2_OUT` (P2_node ↔ P2_lot, north-east);
IN turns from lane 2 (north/right lane), OUT merges into lanes 1–2. bs_1/bs_5 re-anchored to 4.87–34.87 (same place, ending at X1).
**Driveway sides swapped (user request):** IN lane on the east side, OUT lane on the west side of both driveways
(`driveways_swap.edg.xml`, spreadType center, ±1.6 m; backup `network_crossings.before_swap.net.xml`). Turn-in and
exit paths no longer cross, and crossing-type SSM conflicts dropped from ~5 to 0 per run.
**Entry edge for main-road traffic is now `31993796#3_E`.**

**Baseline files:**
| File | Role |
|---|---|
| `baseline_inputs.csv` | Data register in the friend's STANDARD INPUT TABLE format (source_id, bins, count, data_class…). Edit numbers here. |
| `make_baseline.py [seed]` | CSV → `baseline.rou.xml` (cars + persons) and `baseline_tls.add.xml` (guard-like signal plans). |
| `baseline.gui.xml` | sumo-gui view settings (loaded by baseline.sumocfg): car shapes (vType guiShape=passenger), people 4× size, magenta, delay 100 ms. |
| `baseline.sumocfg` | Net + routes + dropoff + baseline TLS; outputs to `output/` (tripinfo, summary, stops, queue, statistics). SSM via `--device.ssm.probability 1 --device.ssm.file output/ssm.xml`. |
Logic: main road = schedule profile scaled to the team's average (764.5+420+523)/3 = 569 veh; parking IN diverted
out of it (P1_IN 151, P2_IN 46); left lane 83% stop at bs_1 dwell tri(2.10,6.71,27.35); right lane 4.59% stop at bs_5
dwell tri(1.40,2.55,7.68); 70/30 west/south; Z1 (bs_2) = exact MOCK target picked among south-turning main cars, dwell
tri(2.10,6.71,27.35); parking OUT 88/27 join before X1 then 70/30; side road L 10% west/90% south, R 100% south,
no drop-off; PED_MAIN 889 walk_gate_N → school side via X1, PED_SECOND 222 walk_J1_W → school side via X2.
Signals: programID `baseline`, X1 and X2 independent, cycle = veh G tri(2,18.65,66.55) / yellow 3 / ped G
tri(0.2,7.96,22.68) / all-red 2 (yellow and all-red are SUMO safety additions, not in the .alp), whole seconds.

**Seed-1 results:** 1209 vehicles, 1111 persons, 0 teleports, 0 collisions. All source counts match the register per bin.
Mean delay main 23.5 s; side road 56–73 s (max ~420 s, queue 129 m = whole side edge); ped wait X1 15.3 s, X2 14.4 s.
**Open issues:** (1) Z1 target 105 not reachable: only 96 south-turning main cars exist after the volume averaging
(bins 2–5 short). (2) Side-road merge `358217462` (Soi Chula 13 joining the main road, friend's J2): **team confirmed Soi 13 waits for
a gap** in main-road traffic. Made explicit as a `priority` junction with `31973404#0` priority 3 (`merge.nod.xml/.edg.xml`;
backup `network_crossings.before_merge.net.xml`); results identical to before. Side-road delay (~50–68 s, queue fills
the 129 m road) is therefore a real baseline finding. Zipper alternative tested: ~20 s.
(3) The averaged 523 is the side-road counter
total, mixed into main-road volume by team decision. (4) Only one seed run so far; use several seeds for results.
**Do not run `make_crossings.sh`** (would rebuild from the master and lose J1 move, Soi 11 node move and driveways).

## 7d. Baseline KPIs, 10 seeds (2026-10-18, after driveway swap)
`python3 run_seeds.py 10` → `output/seed_<n>/` + `output/kpi_seeds.csv` (~30 s; default files regenerated with seed 1).
All seeds: 0 teleports, 0 collisions, all 1205–1210 vehicles and 1111 persons finish. Mean ± 95% CI:
- Vehicle delay (timeLoss): all 34.0 ±2.0 s; main road 23.0 ±0.5; parking OUT 25–27; parking IN 3–6;
  **side road (Soi 13) L 72.0 ±7.9, R 45.9 ±4.1, p95 199 s**; queue fills the whole 129 m side road every seed.
- Ped wait: X1 15.0 ±0.6 s (p95 44), X2 15.1 ±1.1 s (p95 44).
- Max queues: main entry 75 m, main mid 39 m (very variable), before X1 37 m (≈ full edge), before X2 31 m.
- Drop-offs: bs_1 160, bs_5 8, bs_2 96 (Z1 MOCK target 105 not reachable, see 7c).
- SSM (TTC < 1.5 s, unique encounters): crossing 0, junction 0, merge 0, rear-end ~650. Rear-end counts mostly
  reflect SUMO car-following gaps in queues, so do not use them as a safety KPI without calibration. SSM does not
  measure vehicle–pedestrian conflicts.

## 7e. Demand-responsive crossings, "guard controller" (2026-10-18) — CURRENT BASELINE CONTROL
User rule: at both crossings, if no car is coming pedestrians can cross, and vice versa. `guard_control.py` (TraCI)
now drives X1 and X2 every step and overrides `baseline_tls.add.xml` (that fixed plan is only used when sumo runs
without the controller). Logic: rest in vehicle green; a pedestrian waiting with no moving car within 30 m → ped green
(yellow 3 s only if a car is near, then all-red until no car is inside the junction); both waiting → take turns, each
side's max counted from when the other side started waiting: vehicle tri(2,18.65,66.55), ped tri(0.2,7.96,22.68)
(friend's fitted timings); ped green ends when nobody waits/crosses; cars get green only after the crosswalk is empty
(all-red ≥ 2 s). Cars stopped at a drop-off are ignored. Tests: peds only → max wait 1 s; cars only → 0 s.
**Safety finding:** with `--collision.check-junctions` the old fixed plan had 1 car–pedestrian collision (yellow went
straight to ped green). The controller's all-red clearance gives 0 across all seeds. Collision check is now always on in
`run_seeds.py`.
Run: `python3 guard_control.py [seed] [--gui]` (plain `sumo-gui -c baseline.sumocfg` would show the OLD fixed plan).
10-seed KPIs (vs fixed plan in `output/kpi_seeds_fixedplan.csv`): ped wait X1 5.5 s (was 15.0), X2 6.0 s (15.1);
main delay 19.4 s (23.0); parking OUT 19.5/22.5 s (25/27); all vehicles 34.8 s (34.0); side road L 82.4 / R 49.1 s
(72.0/45.9) — main traffic now flows more evenly, leaving Soi 13 fewer gaps; collisions 0 (was 1 when checked).

## 7f. Drop-off time = 35 s average (2026-10-18, user decision) — CURRENT
`make_baseline.py`: `DWELL_MEAN_S = 35.0` scales each fitted AnyLogic triangle so its mean is 35 s (shape kept):
bs_1 / bs_2 tri(6.10, 19.48, 79.42), bs_5 tri(12.64, 23.02, 69.34). Set `DWELL_MEAN_S = None` for the original times
(avg ≈12 s left/Z1, ≈4 s right). Measured over 10 seeds: bs_1 35.4 s, bs_2 35.3 s, bs_5 35.7 s.
KPIs, 10 seeds, guard controller (previous run with ~12 s dwell in `output/kpi_seeds_dwell12s.csv`): all vehicles
39.5 s (34.8), main road 28.9 s (19.4), P1_OUT 36.0 s (19.5), P2_OUT 27.2 s (22.5), side road L 85.1 / R 49.3 s,
queue between the driveways 74 m (39), ped wait X1 5.9 s, X2 5.6 s; 0 collisions, 0 teleports.
Data class of the 35 s: USER/TEAM ASSUMPTION (not field-measured yet).

## 7g. Traffic moved from Soi 13 / driveways to the main road (2026-10-18, user decision) — CURRENT
User: Soi 13 and both parking driveways actually carry ~10% of their counted cars; the rest uses the main road.
`make_baseline.py`: `SIDE_SHARE = PARK_SHARE = 0.10` (Soi 13 L/R, P1/P2 IN and OUT); moved cars (90% of Soi 13 and of
parking OUT) enter at `31993796#3_E` as main-road cars: same drop-off rule (L 83% at bs_1, R 4.59% at bs_5, 35 s),
70/30 west/south, Z1 eligible. Parking IN reduced to 10% (the rest stay on the main road). Main-road base volume
re-averaged WITHOUT the 523 counter total: (764.5 + 420) / 2 = 592 (avoid double counting). Previous generator:
`make_baseline.before_move.py`; previous KPIs `output/kpi_seeds_before_move.csv` (old delay metric).
**KPI method fix:** vehicle delay is now timeLoss + departDelay (time queued before entering), and runs continue until
every vehicle is done (end 14400 s); new KPIs `veh_unfinished`, `max_queue_outside_entry_veh`,
`last_vehicle_done_min_after_0810`. Earlier sections' delays exclude departDelay (small then: ~8 s).
**Result (10 seeds): the main road is over capacity.** ~1,231 vehicles; ~505 drop-offs at bs_1 (4 spots × 35 s).
From ~07:15 cars queue outside the east entry, up to 237 vehicles; last car done ~59 min after 08:10.
Mean delay: all 786 s, main road 834 s (~14 min), P1_OUT 119 s, P2_OUT 129 s, Soi 13 ~25 s; ped wait X1 14.9 s
(cars almost always near, so turns alternate by max time), X2 2.4 s; 0 collisions, ~0.1 teleports/seed.
Likely more severe than reality → sensitivity checks suggested: moved cars not dropping off, lower left-lane drop-off
share, shorter dwell, more drop-off spots.
**User confirmed (2026-10-18): keep as is — moved cars DO drop off at the gate. This is the frozen baseline.**

## 7h. Driver logic: lane change + drop-off zone choice (2026-10-18, user request) — CURRENT
`driver_logic.py` (called each step from `guard_control.run`, so only active when running through guard_control /
run_seeds). (1) Through cars halted in the main road's left lane (#3_E/#3_M/#3, lane 1) move to lane 2 when lane 2
has clearly fewer halted cars (≤ 0.5×(left+1)). (2) A car within 60 m of its drop-off zone checks it; if full (stopped +
already-waiting cars ≥ spots) it switches once, keeping its dwell time: bs_1 → bs_5 (only if right lane quieter)
→ bs_0 (after X1); bs_5 → bs_1 (if left quieter) → bs_0; bs_2 → bs_4 (after X2). `ALLOW_OTHER_LANE_DROPOFF`
(default True) turns the bs_1↔bs_5 switch on/off. Each seed now takes ~1.5 min.
Seed 1 diagnostics: 0 collisions, 0 teleports; switches bs_1→bs_5 166, bs_1→bs_0 224, bs_2→bs_4 12; 268 lane changes;
mean delay 694 s (was 786 s without driver logic). Bottleneck = the 30 m in front of the gate: bs_1 and bs_5 sit side by
side, so when both are used both lanes are blocked. With `ALLOW_OTHER_LANE_DROPOFF = False` it is worse (1074 s): cars
queue for the 3 after-crosswalk spots inside the X1 area. Previous KPIs: `output/kpi_seeds_no_driver_logic.csv`.

## 7i. Main road left lane queues across driveway mouths (2026-10-18, user request) — CURRENT NET
User: the east→west left lane does not give way at the two driveway junctions. Checked: main lanes were already major
(`M`, never yield); the visible stops were SUMO's "keep the junction clear" rule. `driveways_keepclear.con.xml`
(applied to `network_crossings.before_keepclear.net.xml` → `network_crossings.net.xml`): keepClear=false for the main
road's LEFT lane (lane 1) at P2_node and P1_node; the right lane still keeps the mouths clear; parking exits now turn
into the right lane only (P_OUT→lane 1 connections deleted). Doing both lanes trapped parking-exit cars (10 teleports);
left-lane only + right-lane exits gives ~1 teleport in seed 1. Exits still yield to lane 1 because the junction shapes
overlap. `run_seeds.py` gained `--net` and `--out` options; 10-seed comparison: `output/cmp_keepclear_on/` (old net)
vs `output/` (current).

## 7j. Georeferenced map background (2026-10-18)
User saw the roads misaligned with a hand-placed screenshot background. Checked: the network is OSM-derived in UTM
metres and correct (Soi 11/main corner node = OSM corner at lat 13.738291, lon 100.526651; corner→gate 111 m).
Installed `pyproj` (pip, needed by sumolib/tileGet) and ran SUMO's `tileGet.py -n network_crossings.net.xml
-u https://tile.openstreetmap.org --zoom 19 -d background -f 100` → 48 OSM tiles in `background/` (628 KB) +
`background/decals.xml`; the 48 decals are also embedded in `baseline.gui.xml` (layer -1), so the map loads with
the simulation. In netedit: View → Edit Visualization → Background → load `background/decals.xml`. Overlay check:
all roads sit on the OSM roads. P2 driveway stub sits near อาคารจามจุรี 5 where OSM shows no clear entrance: verify.
Map data © OpenStreetMap contributors (credit it in the report).

## 7k. Gate crossing X1 and both driveways moved west (2026-10-18, user request, matched to OSM) — CURRENT NET
User marked on the OSM overlay: X1 + pad ~35 m west, P1 to where X1 was, P2 ~65 m west. OSM data (API 0.6 map call)
confirmed: zebra `crossing=uncontrolled` at node **10784747877** (x 241.4) and the ลานจอดรถ 1 parking aisles join the
main road at old X1 (x 279.5) and x 288.1. New layout (backup `network_crossings.before_move_X1.net.xml`):
- **X1 = junction `10784747877`** (TLS + crossing `:10784747877_c0` over `31993796#5`; pad `pad_gate_N` at
  244.18,224.39; `walk_gate_N` 17.5 m). Old X1 node `10072794956` is now a plain priority junction.
- **P1 = junction `10072794956`, moved to x 288.10, y 197.58** (second OSM parking connection, gives room for 4 cars);
  P1_IN/P1_OUT (15.7 m, IN east side, OUT west side), P1_OUT → right lane only; left-lane keepClear=false there.
  Old `P1_node` (x 326.5) is now just a pass-through split between `31993796#3_M` and `31993796#3`.
- **P2 = `P2_node` moved to 375.00,181.46** (user's arrow; OSM has no connected lot entrance there).
- Main lanes now: #3_E 146.4 m, #3_M 42.0, #3 31.8 (P1_node→P1), #4 34.5 (P1→X1), #5 34.5 (X1→side merge).
- Stops: bs_1 / bs_5 on `31993796#4_1/_2` 4.47–34.47 (4 cars, end at X1); bs_0 on `31993796#5_1` 1.00–23.50 (3 cars).
  Capacities re-tested (4/4/3).
- Patch files: `move_X1_stepA.nod/.con.xml` (unset old TLS/crossing, applied with `--remove-edges.explicit
  P1_IN,P1_OUT,walk_gate_N --tls.unset 10072794956`), `move_X1_stepB.nod/.edg/.con.xml`, `move_X1_stepC.nod/.edg.xml`.
- Code updated: guard_control X1 ids, make_baseline PED_MAIN → `31993796#5` + TLS id, driver_logic GATE_EDGES + #4,
  run_seeds queue lanes (before X1 = #4, P2→P1 = #3).
Checks: peds-only max wait 1 s, cars-only 0 s, all driveway/side trips OK; seed 1: 0 collisions, 0 teleports, mean delay
581 s, X1 ped wait 19.6 s, max queue outside 220, last car 27 min after 08:10 (vs ~59 before the move).

## 7l. Frozen baseline folder (2026-10-18, user: "this is perfect")
`baseline/` = self-contained copy of the agreed baseline (network after the X1/P1/P2 move, stops, map background,
data CSV, make_baseline/guard_control/driver_logic/run_seeds, config, GUI settings, README.md). Run from inside it:
`python3 guard_control.py 1 --gui`, `python3 run_seeds.py 10`. Its seed-1 demand equals `view_seed1.rou.xml`, the
morning the user watched. 10-seed KPIs go to `baseline/results/`. Treat `baseline/` as read-only; build scenarios
in the main folder or in copies.

## 9b. SCENARIO webster_soi11 (2026-10-18) — folder `scenario_webster_soi11/` (see its README.md)
User: Webster-based signal at X1 (from the team's AnyLogic PDF, with Claude's assessed fixes) + encourage 30% of gate
drop-off cars to turn left into Soi 11 and drop off at Z1. Built as a copy of `baseline/`; `baseline/` untouched.
`webster_control.py` (X1 only; X2 keeps the guard). Fixes vs PDF: uncapped ratios in the split; s = 1500 veh/h both
lanes; flows measured at X1 each 15 min; max-out timer from the ped call; ped rest when no car waits; min ped green
11 s (6.4 m crossing, 1.0 m/s); min green + yellow skipped when no car is near; spillback trigger = 25 halted cars in the
left lane X1→east entry. `make_baseline.py`: REDIRECT_TO_Z1 = 0.30 (env override); `guard_control.py`: X1_CONTROL env.
Seed-1 finding: measured stop-line flows stay 84–464 veh/h (the drop-off upstream caps discharge), so Y_raw ≤ 0.43 and
Webster always picks the 30 s minimum cycle (case A, 11 s / 11 s); the actuation does the work. X1 ped wait 6.7 s
(baseline seed 1: 19.6 s); mean vehicle delay 661 s (baseline seed 1: 581 s); Z1 overloaded (160 overflow to bs_4).
10-seed runs: scenario (both changes) + `variants/webster_only` (REDIRECT_TO_Z1=0) + `variants/redirect_only`
(X1_CONTROL=guard), to separate the two effects.
**10-seed results** (see scenario README table): baseline 677 s / X1 ped 19.5 s; Webster only 1012 s / 7.0 s;
redirect only 351 s / 18.8 s; both 675 s / 6.5 s. Webster always 30 s cycle. Redirect = the vehicle-delay win;
Webster = the pedestrian win at a vehicle cost. Z1 overloaded under redirect (~150 overflow to bs_4).

## 7m. Baseline variant: traffic officer at X1 (2026-10-18) — folder `baseline_officer/` (see its README.md)
User: simulate officer control (less efficient) at X1 only; X2 keeps the guard. `officer_control.py`: cars go while the
front LEFT-lane car is not a bs_1 drop-off car; when it is, stop (both lanes) until its drop-off is done and waiting
pedestrians crossed; off-peak (left queue ≤ 5) pedestrian priority; peak: pedestrians wait max 120 s (trigger allows for
reaction + clearance + 6 s margin); 3 s reaction, ≥ 5 s per go/stop, no yellow, 3 s stop clearance (was 1 s → caused a
car–pedestrian collision), give up after 60 s if the awaited car never starts its drop-off. bs_5 was removed from the
trigger: a left-lane car bound for bs_5 could not change lanes while the officer held traffic (deadlock, 11 teleports).
Without the 120 s rule, peak pedestrians waited ~213 s on average (max ~13 min). Seeds 1–3 after fixes: 0 collisions,
0–2 teleports, delay 642–756 s, X1 ped wait 40–44 s, max ~120 s. 10-seed results in `baseline_officer/results/`.
**10 seeds:** delay 653 ± 38 s (baseline 677 ± 60), X1 ped wait 42.5 s / p95 110 s (baseline 19.5 / 51), longest
ped wait 116–128 s per seed, 0 collisions, 0.6 teleports. Officer ≈ same for cars, much worse for pedestrians.

## 8. Demand (`satit.rou.xml`) — current
```xml
<vType id="car" accel="2.6" decel="4.5" sigma="0.5" length="5.0" minGap="2.5" maxSpeed="13.89"/>
<vType id="bus" accel="1.2" decel="4.0" sigma="0.5" length="12.0" minGap="3.0" maxSpeed="10.00" vClass="bus"/>
<vType id="pedestrian" vClass="pedestrian"/>
<flow id="f_car" type="car" begin="0" end="3600" number="80" from="31973416#0" to="31973416#1"/>
<flow id="f_bus" type="bus" begin="0" end="3600" number="10" from="31973416#0" to="31973416#1"/>
```
Problems: flows only cover a 2-edge stretch of Soi Chula 11; **no `<stop>`s**, so nobody uses the
drop-offs; the main corridor (east entry → gate → west exit / south turn) has no demand;
no pedestrians/persons; numbers are placeholders, not the calibrated Tuesday counts.

## 9. Today's crossing work (history — important)
Goal: add signalized crossings at `10072794956` (gate) and `J1`.

**Attempt 1** — `crossings.con.xml` + `netconvert -s network.net.xml --connection-files … --walkingareas --tls.rebuild`:
- `Ignoring additional sidewalk lane 3 on edge …` → **SUMO supports only one sidewalk per edge, at lane `_0`.** Lane `_3` sidewalks are ignored.
- `crossing ':10072794956_c0' across [31993796#4] has no target` → far side had no usable sidewalk.
- `Discarding invalid crossing ':J1_c0' … (no vehicle lanes to cross)` → lanes `_1/_2` of `31973416#1` and `#1.32` did **not** disallow pedestrian (unlike all other edges).
- Result: 0 crossings.

**Fix design** (current scripts):
1. `fix_sidewalks.py` → `network_base.net.xml`:
   - delete lane `_3` from all 9 four-lane road edges (keeps `_0` sidewalk + `_1/_2` vehicle);
   - add `pedestrian` to `disallow` on lanes 1–2 of `31973416#1`, `31973416#1.32`;
   - drop all internal/walkingarea/crossing edges, internal junctions, connections from/to `:` edges,
     connections using lane 3, **sidewalk connections (fromLane 0)**; strip `via/tl/linkIndex`
     on connections; strip `intLanes/incLanes` and `<request>` children on junctions;
     remove all `tlLogic` (rebuilt);
   - **keeps E0–E3** (driveways).
2. Far-side sidewalks modelled as **separate pedestrian-only stub edges** into each crossing node
   (`crossings.nod.xml` / `crossings.edg.xml`, 4 m wide, `allow="pedestrian"`):
   - `walk_gate_N`: `pad_gate_N` (282.45, 218.94) → `10072794956` — north (parking-lot) side, ~20 m perpendicular.
   - `walk_J1_W`: `pad_J1_W` (137.00, 128.80) → `J1` — west side.
   Positions computed from road heading, **not visually verified** — check/drag in netedit.
3. `crossings.con.xml`:
   ```xml
   <crossing node="10072794956" edges="31993796#4" width="4.0"/>
   <crossing node="J1" edges="31973416#1.32" width="4.0"/>
   ```
4. `make_crossings.sh`: `python3 fix_sidewalks.py` then
   `netconvert -s network_base.net.xml --node-files crossings.nod.xml --edge-files crossings.edg.xml --connection-files crossings.con.xml --walkingareas --tls.rebuild -o network_crossings.net.xml`,
   prints crossing count (expect **2**) and the tlLogics.

**Attempt 2** failed: `Unknown edge ':…_w0' given in connection` (connections *to* old walkingareas
were kept). Fixed (now strips connections to `:` edges, sidewalk links, junction intLanes/request).
Cleaned base verified: 0 `:` refs, 16 vehicle connections, no dangling edges/nodes.

**Attempt 3** (run by Claude Code on the Mac, 2026-10-18) → "Success" but 0 crossings, 0 tlLogics:
- netconvert auto-enables `no-internal-links` when the input net has no internal edges (which
  fix_sidewalks.py strips) → crossings silently dropped. Fix: `--no-internal-links false`.
- junctions still typed `traffic_light` with no tlLogic → no program built. Fix: fix_sidewalks.py
  now resets them to `priority`, and make_crossings.sh passes `--tls.set 10072794956,J1`.

**STATUS: DONE — `network_crossings.net.xml` valid, 2 crossings built.** Both tlLogics (default
netconvert timings, to be replaced in TODO 3): `GGr 77 / yyr 3 / rrG 5 / rrr 5` (link 2 = crossing).
Verified in sumo: test persons `walk_gate_N → 31993796#4` and `walk_J1_W → 31973416#1` both cross
(~62 s wait for ped green). Pad positions still not visually checked in netedit.
Note: Claude's cloud workspace and the device VM have no internet → cannot install/run SUMO;
the user runs netconvert/sumo on the Mac and pastes output. If you (Claude Code) run on the Mac
directly, you can run netconvert yourself.

## 10. Design decisions & cautions
- **Baseline vs scenario:** today there is *no signal*, only a zebra + guard. Baseline should be an
  **unsignalized priority crossing** (`<crossing … priority="true"/>` on a `priority` / non-TLS node, or
  approximate the guard), with drop-offs only in the **left lane between the west end of the wall
  and the crossing**. Signalized (`traffic_light`) crossings belong to the optimized scenarios.
  Keep separate net/config variants (e.g. `baseline.sumocfg`, `scenario_*.sumocfg`).
- In TLS states use **`G` (capital)** for crossing links during the ped phase; lowercase `g` = yield.
- Ped phase must alternate safely with vehicle green (include yellow + all-red clearance).
- Drop-off modelling: `<stop busStop="bs_x" duration="…" parking="false"/>` blocks the lane — this is
  the congestion mechanism to reproduce. Consider modelling students as `<person>`s riding then
  walking to the crossing to couple vehicle and ped demand.
- Use `vClass="passenger"` for cars (currently unset → default passenger, OK).
- Write netconvert output to a **different** filename than its input.

## 11. TODO (in order)
1. Run `make_crossings.sh`; resolve any errors; verify crossings + pads in netedit.
2. Connect north driveways E0–E3 to the main corridor (split `31993796#3` at driveway positions,
   2-way connection) or delete if not needed for the baseline.
3. Set real TLS timings (netedit TLS mode `T`, or a `.tll.xml`): vehicle G / y / all-red / ped G.
4. Point `satit.sumocfg` at the chosen net (`network_crossings.net.xml`).
5. Rewrite `satit.rou.xml`: routes for east entry → gate → west exit / south turn, north driveway
   inflows, Soi Chula 11; stops at the drop-off busStops; pedestrian flows / persons across both
   crossings; calibrate rates from the Tuesday counts (AM peak, ~2 h → `end=7200`).
6. Add outputs: `--tripinfo-output`, `--summary-output`, queue output, `--device.ssm` for conflicts;
   lane-area detectors (E2) on approaches.
7. Run `sumo-gui -c satit.sumocfg` end to end; check stops and signal obedience.
8. Build baseline (unsignalized) variant; then fixed-algorithm controller (actuated + PHB); then RL if time.

## 12. Original AI project instructions (summary)
Phases: (1) network & sidewalks (`spreadType="roadCenter"`, no `unknown` values; outer lanes
sidewalks, inner lanes `disallow="pedestrian"`; netconvert `--walkingareas`); (2) signalized
crossroads & zebra crossings (junction `traffic_light`, crossings with `tl`, TLS phases alternating
ped/vehicle); (3) drop-off busStops in `dropoff.add.xml`, only on vehicle lanes; (4) vTypes/flows
in `satit.rou.xml`, all inputs grouped in `satit.sumocfg`; (5) debug XML errors, verify in sumo-gui.
NB: "sidewalks on both sides as outer lanes" is **not possible on one edge in SUMO** — far side
must be a separate pedestrian edge (done via stub edges above).
