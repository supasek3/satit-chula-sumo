# baseline_v5 — CURRENT BASELINE (frozen 19 Oct 2026)

Team decision: v5 is the project's baseline (v0, the original handed-off `../baseline/`, also rests on many
assumptions because data are insufficient). **Do not modify this folder**; copy it for new scenarios.
Developed as `scenario_dynamic_dropoff/` (v1–v5 below), then renamed. Main-road volume is still unverified
(HANDOFF §12); values marked MOCK are assumptions, not site observations.

## Quick start (Windows: `py -3`, macOS/Linux: `python3`; needs SUMO 1.28, `pyproj`, `SUMO_HOME` set)
```
py -3 guard_control.py 1 --gui             # watch seed 1 (press ▶); colours: green child aboard, red dropping off,
                                            # yellow done, purple no student
py -3 run_seeds.py 10 --out results         # 10 seeds → results/kpi_seeds.csv (~15 min)
```
Do not open the GUI and a seed run in this folder at the same time (both rewrite `baseline.rou.xml`).

## What differs from v0 (`../baseline/`)
**Unchanged:** road network, crossings, buildings/map, pedestrian counts, the cars that carry a student, the 35 s
drop-off time, the 70/30 turn split, the guard controller at both crossings, the other drop-off zones.

1. **Gate drop-off (left lane):** 30 m / 4 cars → one continuous **60 m / 8 cars** (gate + P1 driveway stretch +
   `bs_1x` east of P1); open length grows with the queue (5 → 8 spots).
2. **Where parents stop:** halted in the zone, a parent drops off on the spot with chance 100% (front) → 15% (back
   of the queue), rising to 80% when the queue is twice the zone. (MOCK)
3. **When the zone is full:** only 6% use the spot past the crossing (`bs_0`), only 6% cross to the right-lane gate
   spot (`bs_5`); the rest wait in line. v0: everybody could. (MOCK)
4. **Lane changing:** gate parents keep the left lane until they drop off; the jam rule only moves cars with no
   drop-off ahead.
5. **Traffic:** cars with no student cut to **20%** (≈ 660 → 130 per morning). Cars with a student unchanged.
6. **GUI only:** car colours by drop-off status.
7. **KPIs:** delay with / without a student, drop-offs per stretch, zone statistics.

Files: changed `make_baseline.py`, `driver_logic.py`, `guard_control.py`, `dropoff.add.xml`, `run_seeds.py`;
new `dynamic_dropoff.py`, `car_colors.py`.

## Rules in the current version (v5)

### 1. One continuous gate drop-off: 4 → 8 cars (30 m → 60 m) (v5)
Measured back from the X1 stop line along the left lane:

| Stretch | Where | How a parent stops there |
|---|---|---|
| 0–30 m | `bs_1`, `31993796#4_1` 4.47–34.47 m (original gate zone) | SUMO stop |
| 30–48.9 m | last 4.5 m of `31993796#4` + the P1 driveway junction (14.5 m) | **held still** for its drop-off time (`setSpeed(0)`); SUMO cannot stop cars inside a junction |
| 48.9–60 m | `bs_1x`, `31993796#3_1` 20.70–31.77 m, east of P1 | SUMO stop |

- The junction stretch is painted like a drop-off band (`poly gate_dropoff_P1_stretch` in `dropoff.add.xml`).
  Left-lane cars standing there do not block P1: cars turn into and out of P1 from the right lane only.
- After a held drop-off, the car's leftover `bs_1` stop becomes a pass-through point (waypoint) at full speed, and
  the stop log marks it `state="waypoint"` (excluded from drop-off counts). Removing the stop through TraCI instead
  crashes SUMO 1.28.
- No road, junction, crossing or building was changed.
- v1–v4 had 6 spots (30 m at the gate + 15 m east of P1) with an unusable gap across the driveway.
- Right lane (`bs_5`) unchanged: an extension east of P1 would block cars turning into P1 from the right lane.

### 2. Dynamic length
"Queue" = gate drop-off cars only (dropping off in the zone + halted while waiting to drop off at the gate),
7.5 m per car.

| Queue | Open spots | Open length |
|---|---|---|
| ≤ 5 cars (≈ 2/3 of 60 m) | 1–5 | 37.5 m |
| 6 / 7 cars | 1–6 / 1–7 | 45 / 52.5 m |
| ≥ 8 cars | 1–8 | 60 m |

The "zone full → go elsewhere" check treats the gate zone as full only when the queue cannot open another spot
for the arriving car (8 or more drop-off cars already there).

### 3. Where a parent stops
A gate parent **halted on an open spot** drops off right there with probability

    p = 100% on the front spot (next to the crossing)
      → falls linearly to 15% at the back of the queue (rear bumper of the last drop-off car in the queue)

otherwise it waits to move closer and draws again at the next spot it halts on. A parent who is not held up drives
to the front of the free space (100%). Drop-off time unchanged (mean 35 s).

**When the queue is longer than the drop-off area (v4)** parents get keener to stop where they are: the
back-of-queue chance ramps evenly with the drop-off queue length.

| Drop-off queue | Chance front → back |
|---|---|
| ≤ 60 m (≤ 8 cars, fits in the zone) | 100% → 15% |
| 90 m (12 cars) | 100% → 47.5% |
| ≥ 120 m (≥ 16 cars, 2 × the zone) | 100% → 80% |

(v4 used the 45 m zone: 45 m → 90 m.)

`P_BACK`, `P_BACK_LONG`, `RAMP_FROM`, `RAMP_TO` in `dynamic_dropoff.py`.

### 4. Where parents go when the gate zone is full
Drawn once per car:
- **6%** see the spot past the crossing (`bs_0`) as a drop-off area (`P_ACCEPT_AFTER_X1`).
- **6%** of left-lane parents would cross to the right-lane gate spot `bs_5` if that lane is quieter (`P_SWITCH_RIGHT`).
- Everyone else waits in line for the left-lane gate zone.

### 5. Lane changing
- A parent in the left lane heading for the gate drop-off **does not change lanes**: it waits behind a car that is
  dropping off instead of overtaking on the right (`LC_KEEP_LANE`).
- After dropping off (yellow) cars change lanes normally; a halted car in the left lane with **no drop-off ahead**
  (yellow / purple) moves to the right lane when that lane is clearly emptier (jam rule).
- Cars heading for Soi 11 (`bs_2`), `bs_0` or `bs_5` and cars with no student use SUMO's normal lane changing.

### 6. Fewer cars with no student: 20% kept
Cars with no drop-off (purple: through traffic, parking IN/OUT, Soi 13) are thinned to **20%** of the baseline
demand (≈ 660 → 130 per seed). Cars with a student are exactly the baseline's. `NO_STUDENT_KEEP` in
`make_baseline.py`. **This changes the demand**, so the fair comparison is the baseline logic with the same reduced
traffic (reference run below). Small groups (P2 parking, Soi 13 lane 1) can be empty in a seed → their delay is
`nan` (skipped in the summary).

### Car colours in sumo-gui (`car_colors.py`, display only, `--gui` runs)
green = still has a child to drop off · red = dropping off now · yellow = finished · purple = no student.
Pedestrians stay magenta.

Code: `dynamic_dropoff.py` (zone + where to stop), `driver_logic.py` (zone full, 6% rules, lane changing),
`car_colors.py`, hooks in `guard_control.py`, `make_baseline.py` (no-student thinning), `run_seeds.py` (KPIs).

## How to run (Windows: `py -3`, macOS/Linux: `python3`)
```
py -3 guard_control.py 1 --gui            # watch seed 1 (press ▶); the extension is the stop drawn east of P1
py -3 run_seeds.py 10 --out results        # 10 seeds → results/kpi_seeds.csv (~20 min)
```

## Extra KPIs in `results/kpi_seeds.csv`
| KPI | Meaning |
|---|---|
| `veh_with_student`, `veh_no_student`, `delay_with_student_s`, `delay_no_student_s` | cars with / without a drop-off |
| `dropoffs_bs_1`, `dropoffs_bs_1x`, `dropoffs_gate_left_total` | drop-offs on the gate stretch / extension / both |
| `switch_<from>-><to>` | cars that gave up their zone because it was full |
| `zone_open4/5/6_share` | share of 06:30–08:10 with 4 / 5 / 6 spots open |
| `zone_early_spot1..6` | parents who stopped where they were halted, by spot (1 = next to the crossing) |
| `zone_draws`, `zone_early_total` | "drop here?" decisions made / answered yes |
| `zone_gate_cars`, `zone_gate_cars_accept_bs0/bs5` | gate parents / of those willing to use `bs_0` / `bs_5` |

## Checks
- v3 diagnostic, seed 1: green cars standing ≥ 5 s with free road ahead **8** per morning (v2: 102; user: real life
  6–7), longest 16 s. Parents crossing left → right before dropping off: 39 (only the 6% + 6%; v2: ~340).
- Every 10-seed run: collisions (junction check on) and teleports reported in the results.
- v1, seed 1: peak occupancy gate stretch 4 (max 4), extension 2 (max 2); every lane stop inside its stretch.

## Results v5 (current, `results/`), v4 (`results_v4/`), v3 (`results_v3/`)
10 seeds, mean ± 95% CI, 0 collisions and 0 teleports in every v3–v5 seed. Main-road volume still unverified.
v0 = `baseline/` (full traffic); reference = v0 logic with the same 20% no-student traffic.

| KPI | v0 | Reference | v3 | v4 | **v5** |
|---|---|---|---|---|---|
| Vehicle delay, all (s) | 677 ± 60 | 321 ± 43 | 452 ± 64 | 428 ± 57 | **407 ± 50** |
| Delay, cars with a student (s) | – | 358 ± 49 | 532 ± 73 | 503 ± 64 | **449 ± 49** |
| Delay, cars with no student (s) | – | 150 ± 9 | 84 ± 17 | 83 ± 17 | **297 ± 51** |
| Ped wait X1 mean / p95 (s) | 19.5 / 51 | 18.0 / 49 | 10.0 / 35 | 10.1 / 36 | **7.6 / 28** |
| Max queue outside entry (veh) | 250 | 74 | 103 | 100 | **96** |
| Last car after 08:10 (min) | 32 | 14 | 22 | 21 | **19** |
| Gate-left drop-offs: gate / P1 stretch / east of P1 | 89 / – / – | 117 / – / – | 335 / – / 118 | 325 / – / 127 | **243 / 134 / 77** |
| Drop-offs `bs_5` / `bs_0` | 197 / 245 | 228 / 186 | 53 / 26 | 52 / 26 | **53 / 25** |

- v5 gives the shortest delay for cars with a student and the shortest gate pedestrian waits of all versions.
- **Cars with no student wait much longer in v5 (297 s vs 83 s in v4).** Likely cause: a parent held still in the
  P1 junction stretch blocks the left lane inside the junction, where cars behind cannot change lanes, so through
  cars queue behind it. Check before using no-student delay as a KPI.
- All v3–v5 versions are slower for cars than the reference mainly because of the 6% rules (parents wait in line
  instead of using `bs_0` / `bs_5`).

## Results v2 (`results_v2/`): rules 1–4 with 40% back-of-queue chance, any parent may switch to `bs_5`
10 seeds, mean ± 95% CI. Reference = baseline logic with the same 20% no-student demand
(run from a scratch copy of `baseline/` + this folder's `make_baseline.py`; not kept in the package).

| KPI | Baseline (full demand) | Reference (20% purple) | v2 |
|---|---|---|---|
| Vehicle delay, all (s) | 677 ± 60 | 321 ± 43 | 525 ± 95 |
| Delay cars with student (s) | – | 358 ± 49 | 587 ± 110 |
| Ped wait X1 mean (s) | 19.5 | 18.0 | 14.6 |
| Max queue outside entry (veh) | 250 | 74 | 107 |
| Last car after 08:10 (min) | 32.3 | 13.8 | 23.8 |
| Drop-offs `bs_1` / `bs_1x` / `bs_5` / `bs_0` | 89 / – / 197 / 245 | 117 / – / 228 / 186 | 176 / 47 / 283 / 25 |
| Collisions / teleports | 0 / 0.4 | 0 / 0.2 | 0 / 0 |

v2 is slower than the reference mainly because of the 6% rule: drop-offs past the crossing fall from 186 to 25,
so those parents wait in line at the gate instead.

## Results v1 (`results_v1/`): rules 1–3 only, full baseline demand
| KPI | Baseline | v1 |
|---|---|---|
| Vehicle delay, all (s) | 677 ± 60 | 637 ± 47 (−6%, CIs overlap) |
| Ped wait X1 mean (s) | 19.5 | 20.1 |
| Last car after 08:10 (min) | 32.3 | 29.7 |
| Drop-offs gate left (`bs_1` + `bs_1x`) / `bs_5` / `bs_0` | 89 / 197 / 245 | 133 / 168 / 230 |

## Decision log (all 2026-10-19, user decisions; MOCK = not observed on site)
- v1: Left lane only. Extension east of P1 because P1 and X1 must not move (no street / crossing changes).
- v1: Queue for the dynamic length = gate drop-off cars only.
- v1: Stop-here chance 100% at the front, 40% at the rear bumper of the last drop-off car in the queue. **MOCK**.
- v1: Overflow rule keeps the baseline's counting; zone full = 6 cars (dynamic maximum).
- Car colours by drop-off status in the GUI; display only.
- v2: Only 6% of gate parents see `bs_0` (past the crossing) as a drop-off area. **MOCK**.
- v2: Cars with no student cut to 20% ("way too many purple cars"; read as the number of cars, not their drawn size).
- v3: Back-of-queue chance 40% → **15%**. **MOCK**.
- v3: Only 6% of left-lane gate parents may switch to the right-lane gate spot `bs_5` (was: anyone, when the right
  lane is quieter). **MOCK**.
- v3: Gate parents in the left lane keep their lane until they drop off; cars change lanes (jam rule) only once they
  have no drop-off ahead. Fixes green cars standing in line "for no reason" (they were waiting for a gap to change
  lanes).
- v4: When the drop-off queue is longer than the 45 m zone, the back-of-queue chance ramps evenly 15% → 80%
  (reached at a 90 m queue); gradual rather than a jump. **MOCK**.
- v5: The gap across the P1 driveway is filled: one continuous 60 m / 8-car drop-off from the crossing to the far end
  east of P1 (`bs_1x` trimmed to 20.70–31.77 m). Dynamic length 5 → 8 spots; the v4 ramp now runs over a 60 → 120 m
  queue. Parents in the driveway stretch are held still (SUMO cannot stop cars in a junction); no road changes.
