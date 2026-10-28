# HANDOFF — Satit Chula Drop-off & Pedestrian Crossing Simulation (SUMO)

**Last updated:** 18 Oct 2026 (Asia/Bangkok, UTC+7)
**Owner:** Supasek · **This package:** `SatitChula_SUMO_handoff/` (all paths below are relative to this folder)
**Tool:** Eclipse SUMO / netedit **1.28.0** · Python 3.12 (Anaconda `base`) · TraCI
**Companion log:** `reference/WORKING_LOG.md` (chronological working log; it refers to the original Mac paths and to
main-folder working files that are not in this package — `baseline/` is the reference copy of all of them)

---

## 0. TL;DR (read this first)

- **Goal:** replace the human guard who acts as a "manual traffic light" at the zebra crossing in front of the
  gate of Satit Chulalongkorn Demonstration School during the **morning peak (06:30–08:10)**.
  Phase 1 = SUMO simulation (baseline → scenarios → compare). Phase 2 = hardware prototype of the best strategy.
- **CURRENT BASELINE (19 Oct 2026): `baseline_v5/`** — team decision. Built from v0 below with a continuous
  60 m / 8-car dynamic gate drop-off, realistic parent stop / lane behaviour and 20% of the no-student traffic
  (decisions 18–23, full list in `baseline_v5/README.md`). The rest of this file describes **v0** (`baseline/`)
  unless it says v5; v0 is kept unchanged for history and comparison.
- **Status (v0):** Phase 1 baseline v0 is **finished and frozen** in `baseline/` (with 10-seed results).
  Two more versions exist and have 10-seed results:
  - `baseline_officer/`: a **traffic officer** instead of the guard at the gate crossing (less efficient).
  - `scenario_webster_soi11/`: **Webster adaptive signal** at the gate + **30% of gate drop-offs sent to Soi 11**
    (with two single-change variants inside `variants/`).
- **Headline finding:** the bottleneck is the **gate drop-off** (≈500 cars × 35 s each, 4+4 curb spots), not the
  crossing signal. Signal logic mostly decides *who waits* (cars vs pedestrians); moving drop-offs elsewhere is what
  cuts vehicle delay.

| 10 seeds, mean | Vehicle delay (s) | Gate ped wait mean / p95 (s) | Collisions |
|---|---|---|---|
| **Baseline (guard)** | 677 | 19.5 / 51 | 0 |
| Officer | 653 | 42.5 / 110 | 0 |
| Webster only | 1012 | 7.0 / 20 | 0 |
| Redirect 30% to Soi 11 only | **351** | 18.8 / 50 | 0 |
| Webster + redirect | 675 | **6.5 / 19** | 0 |

- **To watch the baseline:** `cd baseline && python3 guard_control.py 1 --gui`
- **To get KPIs:** `cd baseline && python3 run_seeds.py 10` (~15 min)

---

## 1. The site and the problem

- Road in front of the school: **two-lane, one-way, east → west**. **Thailand drives on the left**
  (network built with `lefthand="true"`). In SUMO, lane `_0` is the sidewalk (school side, south), lane `_1` the
  **left** vehicle lane (school side), lane `_2` the **right** vehicle lane (north side).
- School front wall ≈ **180 m**, gate in the middle, **zebra crossing** in front of the gate.
- Today a **guard** stops cars by hand so students can cross. Parents stop in the lanes to drop children off, which
  blocks traffic. This drop-off pattern is a big part of the problem.
- Roads in the model (OpenStreetMap names):
  - **Main road** (E→W) in front of the school: OSM way `31993796`.
  - **Soi Chulalongkorn 13** (ซอยจุฬาลงกรณ์ 13): comes from the north, merges into the main road west of the gate.
  - **Soi Chulalongkorn 11** (ซอยจุฬาลงกรณ์ 11): the north–south road at the west end; cars turn **left (south)** into it.
    It has a second drop-off (Z1) and a second zebra crossing (X2).
  - Two **parking driveways** on the north side: **P1** (ลานจอดรถ 1, north-mid) and **P2** (north-east).
- Map data: OpenStreetMap; the network coordinates are **UTM zone 47, real metres**
  (netOffset `-664897.52, -1519094.99`). Verified: the Soi 11 / main road corner node sits exactly on the OSM corner
  (lat 13.738291, lon 100.526651).

---

## 2. Environment and setup

| Item | Value |
|---|---|
| SUMO | 1.28.0, `/Library/Frameworks/EclipseSUMO.framework/Versions/1.28.0/EclipseSUMO/` |
| SUMO tools (TraCI, sumolib) | `…/EclipseSUMO/share/sumo/tools` (scripts add this path themselves; `SUMO_HOME` is **not** set) |
| Python | Anaconda `python3` (3.12). **`pyproj` installed** (needed for map tiles / lon-lat conversion) |
| PIL | available (used for overlay pictures) |

Harmless warnings you will see on every run (ignore): `Could not set locale to 'C'`,
`pj_obj_create: Cannot find proj.db`, `Environment variable SUMO_HOME is not set…`, `Fontconfig error…` (GUI).

**Gotchas**
- In **netedit**, open a network with `-s` (not `-n`): `netedit -s network_crossings.net.xml -a dropoff.add.xml`.
  `-n` means "node file" in netedit and gives `Error: No nodes loaded`.
- When closing netedit, answer **No** to "save network?" unless you mean it. A netedit save at 15:19 once overwrote
  the resized stops and moved a crossing. Always reload `dropoff.add.xml` before saving additionals.
- **Never run `make_crossings.sh` in the main folder**: it rebuilds from the original master and undoes every later
  network change (see §4.6 for the correct rebuild procedure).
- Plain `sumo-gui -c baseline.sumocfg` runs **without** the crossing controller and driver logic (it falls back to a
  fixed signal plan). Always launch through `guard_control.py` (see §10).
- `run_seeds.py` and `guard_control.py` regenerate `baseline.rou.xml` in their folder. **Do not open the GUI in a
  folder while a seed run is going in that folder**; use a separate demand copy (`view_seed1.rou.xml`, §10).
- All three model folders use the same file names (`baseline.sumocfg`, scheme `satit_baseline`), so the sumo-gui
  window says "baseline" even in the officer / Webster folders. The controller code is what differs.
  (Renaming the config files was offered, not done yet.)

---

## 3. Folder map

```
SatitChula_SUMO_handoff/
├── CLAUDE.md                   ← instructions Claude Code reads automatically (start here, Claude)
├── README.md                   ← for the person: setup + how to hand this to Claude
├── HANDOFF.md                  ← this file
├── reference/                  ← working log, AnyLogic Webster PDF, friend's data register + schema
├── baseline/                   ← ★ FROZEN BASELINE (read-only). Runs on its own.
│   ├── README.md
│   ├── network_crossings.net.xml, dropoff.add.xml, baseline.sumocfg, baseline.gui.xml, background/ (map tiles)
│   ├── baseline_inputs.csv     ← count data (edit here)
│   ├── make_baseline.py        ← CSV → baseline.rou.xml (+ baseline_tls.add.xml)
│   ├── guard_control.py        ← runs SUMO via TraCI; guard controller at both crossings
│   ├── driver_logic.py         ← lane changes + choosing another drop-off when full
│   ├── run_seeds.py            ← multi-seed KPI runner
│   ├── results/                ← kpi_seeds.csv (10 seeds), run_summary.txt
│   └── components/             ← everything used to BUILD it (network steps, history, data, old results, docs)
├── baseline_officer/           ← baseline variant: traffic officer at the gate crossing (officer_control.py)
│   └── results/kpi_seeds.csv   ← 10 seeds
└── scenario_webster_soi11/     ← scenario: Webster signal at gate + 30% drop-offs redirected to Soi 11
    ├── webster_control.py
    ├── results/kpi_seeds.csv   ← 10 seeds (both changes)
    └── variants/webster_only/, variants/redirect_only/   ← each change alone (results/kpi_seeds.csv)
└── baseline_v5/                ← ★ CURRENT BASELINE (frozen). Dynamic 60 m gate drop-off (dynamic_dropoff.py), parent
                                  behaviour rules, 20% no-student traffic, car colours. results/ = v5;
                                  results_v1..v4/ = earlier versions. Was scenario_dynamic_dropoff/.
```
Raw per-seed SUMO outputs (`output/`, `results/seed_*`) are not included (hundreds of MB); `run_seeds.py` regenerates them.

The original project's main folder (on Supasek's Mac) also held working copies and patch files; everything needed is
in `baseline/` and `baseline/components/`. Treat `baseline/` as the reference copy.

`baseline/components/` (see its README):
- `network_build/`: master network + every script/patch file in order (rebuild verified identical, §4.6).
- `network_history/`: the network before each change.
- `original_files/`: first `satit.*` files and the OSM screenshot.
- `data_sources/`: friend's `Satit_Chula_Simulation_Register_with_Map_Schema.xlsx` and `Satit_Chula_Network_Data_Schema.txt`.
- `previous_versions/`: older `dropoff.add.xml` versions, `make_baseline.before_move.py`.
- `earlier_results/`: 10-seed KPI tables from earlier model states (not comparable with the final baseline).
- `docs/HANDOFF_CLAUDE.md`: the working log at freeze time (same as `reference/WORKING_LOG.md`; not this package's `CLAUDE.md`).

---

## 4. Network (final, `baseline/network_crossings.net.xml`)

### 4.1 Main road, west → east (vehicle lanes `_1` left / `_2` right, sidewalk `_0`)

| Piece | From → to | Lane length | What is on it |
|---|---|---|---|
| `31993793` | west corner → west exit | – | West exit (70% of main-road cars) |
| `1085984275#0` | Soi 13 merge → west corner `cluster10784747874_358216946_J0` | 13 m | Left turn into Soi 11 happens at the corner (from lane 1) |
| `31993796#5` | **X1** `10784747877` → Soi 13 merge `358217462` | 34.5 m | `bs_0` drop-off after the crossing |
| `31993796#4` | **P1** `10072794956` → **X1** | 34.5 m | Gate drop-offs `bs_1` (left), `bs_5` (right), both end at X1 |
| `31993796#3` | `P1_node` (pass-through) → P1 | 31.8 m | |
| `31993796#3_M` | **P2** `P2_node` → `P1_node` | 42.0 m | |
| `31993796#3_E` | east entry `cluster_10068082487_…` → P2 | 146.4 m | **All main-road demand enters here** |

### 4.2 Junctions and crossings

| Name | SUMO junction | Type | Notes |
|---|---|---|---|
| **X1 gate crossing** | `10784747877` | traffic_light + crossing `:10784747877_c0` over `31993796#5` | On the **OSM-mapped zebra** (`crossing=uncontrolled`). Crossing 6.4 m long, 4 m wide. North pad `pad_gate_N` via `walk_gate_N` (17.5 m). Links: 0 = left lane, 1 = right lane, 2 = crossing. States `GGr` (cars) / `rrG` (peds). |
| **X2 Soi 11 crossing** | `J1` | traffic_light + crossing `:J1_c0` over `31973416#1.32` | West pad `pad_J1_W` via `walk_J1_W`. Moved ~20 m north by the user in netedit (J1 at 160.24, 148.34). |
| **P1 driveway** | `10072794956` | priority | Moved to x 288.10, y 197.58 (second OSM parking connection of ลานจอดรถ 1). Old X1 position. |
| **P2 driveway** | `P2_node` | priority | x 375.00, y 181.46 (user's choice; OSM has no connected entrance there). |
| **Soi 13 merge** | `358217462` | priority, Soi 13 (`31973404#0`, priority 3) **gives way** | Team confirmed: Soi 13 cars wait for a gap. |
| West corner | `cluster10784747874_358216946_J0` | priority | Straight (west) or left (south into Soi 11). |
| Soi 11 pass-through | `cluster_10784747894_9950744948` | priority | Slid ~6 m north so Z1 fits 4 cars. |

### 4.3 Driveways
- `P1_IN` / `P1_OUT` (15.7 m) and `P2_IN` / `P2_OUT` (21.2 m), one lane each, `disallow="pedestrian"`, 20 km/h.
- **IN lane on the east side, OUT lane on the west side** (user request; paths no longer cross → crossing conflicts 0).
- Cars turn **in from the right lane (lane 2)** only; parking exits turn **into the right lane only**.
- **Main road left lane may queue across both driveway mouths** (`keepClear=false`, user: "left lane does not give
  way there"); the right lane keeps the mouths clear so parking cars can get out.

### 4.4 Soi 11 (`31973416#0` → `#1` → `J1`/X2 → `#1.32` → south exit `358227907`)
- `#1` = 28.15 m (Z1 `bs_2`), `#1.32` = 170.6 m (`bs_4` after X2).

### 4.5 Drop-off zones (`dropoff.add.xml`) — 7.5 m per car (5 m car + 2.5 m gap)

| Stop | Friend's zone | Lane | Position (m) | Cars | Used in baseline |
|---|---|---|---|---|---|
| `bs_1` | Z2Z3_L (`curbSpots_L`) | `31993796#4_1` | 4.47–34.47 | 4 | yes (primary gate drop-off) |
| `bs_5` | Z2Z3_R (`curbSpots_R`) | `31993796#4_2` | 4.47–34.47 | 4 | yes |
| `bs_0` | SUMO-only, after X1 | `31993796#5_1` | 1.00–23.50 | 3 | overflow (driver logic) |
| `bs_2` | Z1 (`curbSpots2_L`) | `31973416#1_1` | 0.15–28.15 | 4 | yes |
| `bs_4` | SUMO-only, after X2 | `31973416#1.32_1` | 4.66–34.66 | 4 | overflow (driver logic) |

Capacities verified in SUMO (peak occupancy = capacity; extra cars queue behind).

### 4.6 How the network was built (and how to rebuild it)
Files in `baseline/components/network_build/`; run each step with
`netconvert -s <previous>.net.xml [--node-files …] [--edge-files …] [--connection-files …] -o <next>.net.xml`.

| Step | Files / options | Change |
|---|---|---|
| 0 | `network.net.xml` | Master drawn in netedit from OSM (never overwritten) |
| 1 | `fix_sidewalks.py` + `make_crossings.sh` + `crossings.*` | Removed extra sidewalk lane `_3`; added pads + 2 crossings. Needed `--no-internal-links false` and `--tls.set` (netconvert silently drops crossings when the input has no internal edges). |
| 2 | manual netedit (15:19) → `network_history/network_crossings.netedit_1519.net.xml` | J1 + pad moved north. **Start a rebuild from this file.** |
| 3 | `soi11.nod/edg.xml` | Soi 11 pass-through node slid north (Z1 = 4 cars) |
| 4 | `driveways.nod/edg/con.xml` + `--remove-edges.explicit E0,E1,E2,E3` | Main road split, driveways connected |
| 5 | `merge.nod/edg.xml` | Soi 13 merge = priority junction |
| 6 | `driveways_swap.edg.xml` | Driveway IN east / OUT west |
| 7 | `driveways_keepclear.con.xml` | Left lane keepClear=false; exits to right lane only |
| 8a | `move_X1_stepA.nod/con.xml` + `--remove-edges.explicit P1_IN,P1_OUT,walk_gate_N --tls.unset 10072794956` | Old gate signal/crossing removed |
| 8b | `move_X1_stepB.nod/edg/con.xml` | X1 onto OSM zebra node `10784747877`; P1 onto old X1 node; P2 moved |
| 8c | `move_X1_stepC.nod/edg.xml` | P1 onto x 288.1 (room for 4 cars in front of the gate) |

Rebuilding steps 3→8c from the netedit file reproduces the current network **exactly** (lanes, nodes, connections,
crossings, signals — verified). Network backups: `network_crossings.before_*.net.xml`.

---

## 5. Data and demand

### 5.1 Sources
- Friend's AnyLogic model register (`data_sources/…Register_with_Map_Schema.xlsx`) and schema text.
- Counting days: **pedestrians 18 Aug 2026 (Tue)**, **parking 16 Sep 2026 (Wed)**, **side road 25 Sep 2026 (Fri)**.
  Window **06:30–08:10 (100 min)** in 15-min bins (last bin 10 min). Note in reports: three different days.
- Data classes kept distinct: **FIELD** (counted), **MODEL** (from the .alp), **MOCK** (assumption), plus team/user decisions.
- Team decision: **SUMO is the team's model of record**; the AnyLogic model is unfinished and only a data/logic source.

### 5.2 `baseline_inputs.csv` (friend's STANDARD INPUT TABLE format)
Columns: `source_id, time_start, time_end, duration_min, count, rate_per_min, data_class, movement, lane_id, scenario_id`.

| source_id | Total / 100 min | Class | Notes |
|---|---|---|---|
| `SRC_MAIN_L` / `SRC_MAIN_R` | 409.3 / 355.2 (raw schedule, veh/h ÷ 60 × min) | MODEL (unit unverified) | Scaled, see §5.3 |
| `SRC_SIDE_L` / `SRC_SIDE_R` | 172 / 351 | FIELD | Soi 13 |
| `P1_IN` / `P1_OUT` | 151 / 88 | FIELD | |
| `P2_IN` / `P2_OUT` | 46 / 27 | FIELD | |
| `PED_MAIN` | 889 | FIELD | X1 (peak 251 in 07:45–08:00 ≈ 1,004/h) |
| `PED_SECOND` | 222 | MOCK | X2, ~25% of main |
| `DROPOFF_SECOND` | 105 | MOCK | Z1 drop-offs among south-turning main cars |

### 5.3 Demand generation (`make_baseline.py [seed]`) — final baseline settings

| Parameter | Value | Source |
|---|---|---|
| Main-road total | (764.5 + 420) / 2 = **592** veh, 15-min profile of the schedule | Team decision (523 counter total removed to avoid double counting) |
| `SIDE_SHARE`, `PARK_SHARE` | **0.10** | User: Soi 13 and both driveways (IN and OUT) carry only 10% of their counts |
| Moved traffic | 90% of Soi 13 and of parking OUT enter at the **east entry** as normal main-road cars (drop off, 70/30, Z1-eligible) | User decision |
| Parking IN | 10% of counts, taken from main-road cars | |
| Lane choice | left/right by the schedule's L/R share per bin | |
| Gate drop-off | left lane **83%** → `bs_1`; right lane **4.59%** → `bs_5` | MODEL (selectOutput1 / selectOutput) |
| Drop-off time | triangle scaled to **mean 35 s**: bs_1/bs_2 tri(6.10, 19.48, 79.42), bs_5 tri(12.64, 23.02, 69.34) | User/team figure (`DWELL_MEAN_S = 35`; `None` = original AnyLogic ≈12 s / 4 s) |
| Turn at the west corner | 70% west / **30% south** | MOCK |
| Z1 (`bs_2`) | exactly the MOCK target per bin among south-turning main cars | MOCK |
| Soi 13 kept cars | lane 1: 10% west / 90% south; lane 2: 100% south; no drop-off | MOCK (team) |
| Vehicle type | car 5.0 m, minGap 2.5, accel 2.6, decel 4.5, sigma 0.5, `guiShape=passenger` | |
| Pedestrians | `PED_MAIN`: `walk_gate_N` → `31993796#5` (across X1); `PED_SECOND`: `walk_J1_W` → `31973416#1` (across X2); magenta | |
| Time | 0 = 06:30, demand ends 6000 s (08:10); runs continue until every car is done (end 14400 s) | |

Per seed ≈ **1,231 vehicles** and **1,111 pedestrians**.

### 5.4 Friend's names ↔ SUMO
| Friend (AnyLogic / map code) | SUMO |
|---|---|
| INFLOW 1&2 (`CarLeft/RightPhayathai`) | `31993796#3_E` lanes 1/2 |
| X1 main zebra | junction `10784747877` |
| J2 side merge / INFLOW 5 (`MergeRoad`) | `358217462` / `31973404#0` (Soi 13) |
| J1 left/straight split (**not** SUMO's `J1`!) | `cluster10784747874_358216946_J0` |
| WEST EXIT (`Chula9Road`) / SOUTH EXIT | `31993793` / `358227907` |
| Z2+Z3 (`curbSpots_L` / `_R`) | `bs_1` / `bs_5` |
| Z1 (`curbSpots2_L`) | `bs_2` |
| X2 second zebra | SUMO junction **`J1`** |
| P1 / P2 parking | `P1_IN/OUT` at `10072794956` / `P2_IN/OUT` at `P2_node` |

---

## 6. Crossing controllers (all run through TraCI from `guard_control.py`)

Common safety rules in every controller: cars stop only once no car is left inside the junction (all-red), and get
green again only once the crosswalk is empty. Collisions are checked with `--collision.check-junctions true`.

### 6.1 Guard controller (BASELINE, both crossings) — `guard_control.py`
Emulates today's guard ("if no car, pedestrians cross; and vice versa"):
- Rest on vehicle green. A waiting pedestrian with **no moving car within 30 m** → pedestrians go (yellow only if a car is near).
- Both waiting → take turns; each side's max is sampled from the friend's fitted AnyLogic timings, counted from when
  the other side started waiting: vehicle **tri(2, 18.65, 66.55) s**, pedestrian **tri(0.2, 7.96, 22.68) s**.
- Yellow 3 s; all-red until the junction is empty; pedestrian green ends when nobody waits/crosses.
- Cars parked at a drop-off are ignored.
- Found while building it: the earlier *fixed* signal plan went yellow → pedestrian green with no all-red and
  produced a car–pedestrian collision; the guard's clearance rules give 0.

### 6.2 Officer controller (`baseline_officer/officer_control.py`, X1 only; X2 keeps the guard)
User's rules:
- No car → pedestrians cross; no pedestrian → cars go.
- Cars keep going while the **front car of the left lane** has dropped off, drops off after the crossing, or goes
  straight/south. When it still has to drop off at **`bs_1`**, the officer stops **both lanes** until that drop-off
  is finished **and** the pedestrians at the edge have crossed.
- Off-peak (left-lane queue ≤ 5 halted cars): pedestrian priority. Peak (> 5): pedestrians cross during drop-off
  stops, and **no pedestrian waits more than 120 s** (trigger at 120 − 3 − 3 − 6 s margin).
- Human behaviour: **3 s reaction**, ≥ 5 s per go/stop, no yellow, **3 s** for cars to obey a stop
  (1 s caused a collision), gives up after **60 s** if the awaited car never starts its drop-off.
- `bs_5` was taken out of the trigger: a left-lane car bound for `bs_5` could not change lanes while traffic was
  held → deadlock (11 teleports).

### 6.3 Webster controller (`scenario_webster_soi11/webster_control.py`, X1 only; X2 keeps the guard)
Based on the team's AnyLogic PDF "Adaptive Traffic Signal Control Logic & Mathematical Derivation"
(`reference/AnyLogic_Traffic_Light_Logic.pdf`), with these agreed fixes:
1. Green split uses the **uncapped** ratios (PDF capped Y at 0.9 but split with it → greens could exceed C − L).
2. Saturation **1,500 veh/h for both lanes** (PDF's 700 for the left lane double-counted drop-off friction).
3. Flows **measured at X1** in the previous 15 min (cars crossing the stop line per lane, pedestrians entering the crosswalk).
4. Queue override: 25 halted left-lane cars from X1 to the east entry (drop-off dwellers excluded) → +15 s vehicle green.
Plus: max-out timer starts at the pedestrian call; pedestrians keep green while no car waits; min pedestrian green
⌈4 + 6.4 m / 1.0 m/s⌉ = **11 s**; min vehicle green 10 s and yellow skipped when no car is near; L = 8 s
(yellow 3 + all-red 2 + ped clearance 3); C in 30–120 s; gap-out 3 s.
Formulas: y = q/s, Y_raw = max(y_left, y_right) + q_p/6000, C₀ = (1.5L + 5)/(1 − min(0.9, Y_raw)),
C = max(max(30, L + g_v,min + g_p,min), min(120, C₀)), cases A/B/C as in the PDF.
**Finding:** stop-line flows never exceed ~460 veh/h/lane (the drop-off upstream caps discharge), so Webster always
selects the 30 s minimum cycle; the real-time actuation does the work.

---

## 7. Driver logic (`driver_logic.py`, active whenever runs go through `guard_control.py`)
- **Lane change:** a car halted in the main road's left lane (`#3_E`, `#3_M`, `#3`, `#4`), with no drop-off ahead,
  moves to the right lane when it has clearly fewer halted cars (≤ 0.5 × (left + 1)).
- **Drop-off choice:** within 60 m of its zone, a car checks whether it is full (stopped + already-waiting cars ≥ spots)
  and switches once, keeping its drop-off time:
  `bs_1 → bs_5` (if the right lane is quieter) → `bs_0` (after X1); `bs_5 → bs_1` → `bs_0`; `bs_2 → bs_4` (after X2).
- `ALLOW_OTHER_LANE_DROPOFF = True` (turning it off was worse: 1,074 s vs 694 s delay in seed 1).

---

## 8. KPI method (`run_seeds.py`)
```
python3 run_seeds.py [n_seeds] [--net NET.net.xml] [--out DIR]    # defaults: 10, folder net, DIR = output
```
For each seed: `make_baseline.py <seed>` → SUMO via `guard_control.run` with the same seed → KPIs → `DIR/kpi_seeds.csv`,
summary printed as mean, sd, min, max, 95% CI half-width (t = 2.262 for 10 seeds). Raw files in `DIR/seed_<n>/`.

| KPI | Definition |
|---|---|
| `veh_delay_*_s` | **timeLoss + departDelay** (time lost on the road + time queued before entering), per source group |
| `ped_wait_X1/X2_mean_s`, `_p95_s` | pedestrian waiting time per crossing |
| `max_queue_outside_entry_veh` | most cars waiting to enter the network |
| `last_vehicle_done_min_after_0810` | when the last car finished |
| `queue_*_m` | max queue length per approach (from `--queue-output`) |
| `dropoffs_bs_*` | drop-offs served per zone |
| `conflicts_*_TTC<1.5s` | SSM unique encounters by type. **Rear-end counts reflect SUMO car-following gaps — do not use as a safety KPI.** SSM does not measure vehicle–pedestrian conflicts. |
| `collisions`, `teleports`, `veh_unfinished` | sanity checks (collisions include car–pedestrian, junction check on) |

Earlier result tables (before §5.3's final settings) excluded `departDelay`; they are in `components/earlier_results/`.

---

## 9. Results (10 seeds each, mean ± 95% CI)

| KPI | Baseline (guard) | Officer | Webster only | Redirect only | Webster + redirect |
|---|---|---|---|---|---|
| Vehicle delay, all (s) | 677 ± 60 | 653 ± 38 | 1012 ± 59 | **351 ± 28** | 675 ± 34 |
| Main-road delay (s) | 718 ± 64 | 692 ± 41 | 1073 ± 62 | **371 ± 30** | 716 ± 37 |
| Parking OUT P1 / P2 (s) | 165 / 181 | 158 / 215 | 163 / 197 | 145 / 132 | 177 / 194 |
| Soi 13 L / R (s) | 27 / 27 | 30 / 29 | 20 / 20 | 33 / 34 | 21 / 23 |
| Ped wait X1 mean / p95 (s) | 19.5 / 51 | 42.5 / 110 | 7.0 / 20 | 18.8 / 50 | **6.5 / 19** |
| Ped wait X2 mean / p95 (s) | 2.6 / 12 | 2.7 / 13 | 2.1 / 10 | 7.4 / 34 | 5.2 / 26 |
| Max queue outside entry (veh) | 250 | 233 | 350 | **146** | 266 |
| Last car after 08:10 (min) | 32 | 32 | 42 | **16** | 27 |
| Drop-offs after X2 (`bs_4`) | 15 | 17 | 21 | 149 | 159 |
| Collisions / teleports | 0 / 0.4 | 0 / 0.6 | 0 / 0.4 | 0 / 0 | 0 / 0.7 |

Files: `baseline/results/kpi_seeds.csv`, `baseline_officer/results/kpi_seeds.csv`,
`scenario_webster_soi11/results/kpi_seeds.csv`, `scenario_webster_soi11/variants/*/results/kpi_seeds.csv`.
Officer: longest gate pedestrian wait per seed 116–128 s (3 seeds slightly over 120 because of 1 s steps/clearance).

### Key findings
1. **The gate drop-off is the bottleneck** (≈500 drop-offs at 35 s on 4+4 curb spots). From ~07:15 cars queue
   outside the east entry (≈250 cars); the last car clears ~30 min after 08:10.
2. **Signal logic redistributes waiting.** Webster cuts gate pedestrian waits from 19.5 s to ~7 s but raises vehicle
   delay by ~50% when used alone. The officer roughly doubles pedestrian waits with about the same vehicle delay.
3. **Moving drop-offs away from the gate is the big vehicle win:** redirecting 30% to Soi 11 halves vehicle delay,
   but Z1 (4 spots) overloads (~150 cars drop off after X2) and X2 pedestrian waits rise.
4. Webster always picked its 30 s minimum cycle (no oversaturated window) because measured stop-line flows are capped
   by the drop-off; a stop-line-count Webster cannot "see" the real demand at this site.

---

## 10. How to run things

All commands from the folder you want (`baseline`, `baseline_officer`, `scenario_webster_soi11`):

```bash
cd baseline && python3 guard_control.py 1 --gui
```
Watch seed 1 (press ▶; Delay box = speed; *Edit → Breakpoints* `4500` jumps to 07:45). People are magenta and 4× size,
cars have car shapes, the OSM map is the background (`baseline.gui.xml`).

```bash
cd baseline && python3 run_seeds.py 10
```
KPIs over 10 seeds (~15–25 min). Use `--out results` to write into `results/`.

```bash
cd baseline && python3 make_baseline.py 3
```
Regenerate demand for seed 3 after editing `baseline_inputs.csv` or parameters.

Watch while a seed run is going in the same folder (uses a separate demand copy):
```bash
cd baseline_officer && python3 -c "import guard_control as g; print(g.run(['sumo-gui','-c','baseline.sumocfg','-r','view_seed1.rou.xml','--output-prefix','view_'],1))"
```

Scenario switches (environment variables in `scenario_webster_soi11/`):
```bash
cd scenario_webster_soi11 && REDIRECT_TO_Z1=0 X1_CONTROL=guard python3 run_seeds.py 10
```
(`REDIRECT_TO_Z1` = share of gate drop-offs sent to Soi 11; `X1_CONTROL` = `webster` or `guard`.)

Open the network only (no cars), with the map:
```bash
cd baseline && sumo-gui -n network_crossings.net.xml -a dropoff.add.xml --gui-settings-file baseline.gui.xml
```
Edit in netedit (save additionals only, answer No to saving the network):
```bash
cd baseline && netedit -s network_crossings.net.xml -a dropoff.add.xml
```
In netedit, load the map via *View → Edit Visualization → Background → Load decals* → `background/decals.xml`.

Re-download map tiles (needs internet + pyproj):
```bash
cd baseline && PYTHONPATH=/Library/Frameworks/EclipseSUMO.framework/Versions/1.28.0/EclipseSUMO/share/sumo/tools python3 /Library/Frameworks/EclipseSUMO.framework/Versions/1.28.0/EclipseSUMO/share/sumo/tools/tileGet.py -n network_crossings.net.xml -u https://tile.openstreetmap.org -a "SatitChulaSUMO/1.0" --zoom 19 -d background -s decals.xml -l -1 -f 100
```

---

## 11. Decision log (18 Oct 2026, in order)
1. Crossings built at the gate and Soi 11 (fixed netconvert flags; sidewalk lane `_3` removed).
2. Drop-off stops resized by car count (3/4/4/4/4) and named after the friend's zones.
3. Friend's data mapped to SUMO; SUMO chosen as model of record; MOCK values accepted (SecondPed 222, SecondDropoff 105, 70/30).
4. Driveways P1/P2 connected; baseline signals from fitted guard timings; first demand file and KPI runner.
5. Soi 13 merge: side road waits for a gap (made explicit as a priority junction).
6. Driveway IN/OUT sides swapped (IN east, OUT west).
7. Guard controller: "no car → pedestrians cross, and vice versa" (fixed plan had a car–pedestrian collision).
8. Drop-off time set to average **35 s**.
9. Main-road volume = average of 764.5 and 420 (523 removed); **90% of Soi 13 and parking traffic moved to the main road**; moved cars drop off like main cars (user confirmed).
10. Delay KPI now includes time queued before entering; runs continue until all cars finish.
11. Driver logic: lane change when left lane is jammed; switch drop-off zone when full.
12. Left lane queues across driveway mouths; exits into the right lane only.
13. Georeferenced OSM background (pyproj installed, 48 tiles).
14. Gate crossing X1 moved onto the OSM zebra; P1 and P2 moved west (user's map markup + OSM data).
15. **Baseline frozen** in `baseline/` with `components/` (rebuild verified) and 10-seed results.
16. Webster PDF assessed; scenario built with fixes + 30% of gate drop-offs redirected to Soi 11 (left turn).
17. Officer variant built (X1 only); 120 s maximum pedestrian wait added; deadlock and collision fixed.
18. (19 Oct 2026) `scenario_dynamic_dropoff/`: left-lane gate drop-off +50% (4 → 6 spots; extra 2 spots `bs_1x`
    east of the P1 driveway, no network change); open length follows the drop-off queue (≤ 4 cars → 4 spots, 5 → 5,
    ≥ 6 → 6); a halted parent drops off on the spot with chance 100% at the front → 40% at the back of the queue
    (MOCK, user). Details and log in its README.
19. (19 Oct 2026) `scenario_dynamic_dropoff/` v2: only 6% of gate drop-off parents use `bs_0` past the crossing
    (MOCK, user); cars with no student cut to 20% of baseline demand (user). Car colours by drop-off status in the GUI.
    v1 results in `results_v1/`.
20. (19 Oct 2026) `scenario_dynamic_dropoff/` v3: back-of-queue stop chance 15%; only 6% of left-lane gate parents
    may switch to `bs_5`; gate parents keep the left lane until they drop off, jam-rule lane changes only for cars
    with no drop-off ahead (fixed green cars standing in line while waiting to change lanes: 102 → 8 per morning).
    v2 results in `results_v2/`.
21. (19 Oct 2026) `scenario_dynamic_dropoff/` v4: when the drop-off queue is longer than the 45 m zone, the
    back-of-queue stop chance ramps 15% → 80% (at a 90 m queue). MOCK, user. v3 results in `results_v3/`.
22. (19 Oct 2026) `scenario_dynamic_dropoff/` v5: gap across the P1 driveway filled → one continuous 60 m / 8-car
    left-lane drop-off (parents in the junction stretch held still via TraCI, stretch painted; no network change);
    dynamic 5 → 8 spots; ramp over 60 → 120 m. Note: `traci.vehicle.replaceStop(v, i, "")` (stop removal) crashes
    SUMO 1.28 — use a waypoint (`setStopParameter(..., "speed", ...)`) instead.
23. (19 Oct 2026) **v5 adopted as the team's baseline** ("v0 also rests on many assumptions because data are
    insufficient"). `scenario_dynamic_dropoff/` renamed `baseline_v5/` and frozen; `baseline/` kept as v0.
    New scenarios start from `baseline_v5/`.

---

## 12. Known issues and limitations
- **Main-road volume is unverified** (schedule 764.5 vs field 420 vs counter 523; the units of the schedule are
  assumed veh/h). Status: UNIT_FIX_REQUIRED / RAW_SOURCE_UNVERIFIED.
- **MOCK values:** SecondPed 222, SecondDropoff 105, 70/30 turn split, Soi 13 branch split, 35 s drop-off time
  (team figure, not timed on site). Run sensitivity checks before drawing conclusions.
- **Z1 target 105** is fully reached only when enough cars turn south (was short before the 90% move).
- **Counts from three different days.**
- **Right-lane drop-off share (4.59%) and its original dwell (~4 s avg)** look low; now 35 s like the others.
- **SSM rear-end conflicts** are a model artefact; **vehicle–pedestrian conflicts are not measured** (only collisions).
- SUMO runs with **1 s steps** (PDF specifies 0.1 s evaluation).
- **P2 position** follows the user's markup; OSM shows no connected entrance there.
- The sumo-gui window title says "baseline" in every folder (same file names).
- The user's last screenshot of sumo-gui showed only the map with no roads visible; not confirmed whether that was a
  crop or a drawing-order problem (decals use layer −1). Check if roads are missing in the GUI.
- `__pycache__/`, `output/` (219 MB) and `view_seed1.rou.xml` files are regenerable working files.

## 13. Open items / suggested next steps
1. Confirm main-road counts and units with the friend (biggest uncertainty).
2. Time real drop-offs on site (replace the 35 s assumption).
3. Drop-off scenarios (likely the biggest gains): more curb space, use upstream stretch, organised/staffed drop-off
   with shorter dwell, spreading drop-offs between the gate and Soi 11 with Z1 capacity increased.
4. Webster variant that uses **upstream demand** (counts at the east entry) instead of stop-line flow, so the cycle
   responds to real demand.
5. Sensitivity runs on MOCK values; several more seeds for final numbers.
6. Phase 2 hardware: the guard/Webster controllers are simple state machines that can be ported to a microcontroller;
   keep a deterministic fallback.
7. Optional: rename config files per folder so the GUI shows the version (offered, waiting for a yes).
