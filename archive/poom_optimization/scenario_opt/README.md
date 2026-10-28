# scenario_opt — finding the best control package on top of baseline_v6 (22 Oct 2026)

Copy of `../baseline_v6/` with **optimisation switches** (`opt.py`). With no switch set it runs exactly v6 (checked:
seed 1 gives the identical tripinfo, mean delay 340.42 s in both folders).

**Rules kept (user, 2026-10-22):** the demand is not touched — same cars, same counts per 15 min, same routes, same
cars carrying a student. Only the behaviour/control logic changes: the crossing controller ("officer"), lane
changing, and drop-off behaviour. Main-road volume is still unverified (HANDOFF §12); MOCK values unchanged.

## Result (10 seeds, mean ± 95% CI; 0 collisions and 0 teleports in every seed of the three packages)

| KPI | v6 baseline | Sign 85% only (flex) | **BEST** | BEST + organised drop-off 30 s |
|---|---|---|---|---|
| Vehicle delay, all (s) | 457 ± 63 | 383 ± 41 (−16%) | **259 ± 35 (−43%)** | 192 ± 28 (−58%) |
| Delay, cars with a student (s) | 751 ± 96 | 634 ± 64 | **469 ± 66** | 339 ± 49 |
| Delay, cars with no student (s) | 248 ± 38 | 215 ± 23 | **119 ± 13** | 92 ± 11 |
| Ped wait X1 mean / p95 (s) | 14.7 / 44 | 15.4 / 45 | **13.7 / 42** | 14.0 / 43 |
| Ped wait X2 mean (s) | 2.6 | 2.6 | 2.6 | 2.8 |
| Max queue outside the entry (veh) | 168 | 152 | **109** | 85 |
| Last car done after 08:10 (min) | 29.7 | 24.7 | **18.3** | 12.8 |
| Drop-offs past the crossing `bs_0` | 25 | 73 | 108 | 101 |
| Drop-offs gate left / right lane `bs_5` | 453 / 53 | 407 / 52 | 423 / 0 | 430 / 0 |

BEST is better than v6 in **every one of the 10 seeds** (−119 to −296 s). Soi 13 cars lose ~3 s more (27 → 30 s)
because more cars now pass the merge; parking exits gain 10–24 s.
Files: `results_best/`, `results_best_dwell30/`, `results_sign85_flex/` (each `kpi_seeds.csv`, `settings.json`),
v6 in `../baseline_v6/results/`. Side-by-side table: `results_summary.txt`.

## The BEST package (`OPT_PRESET=best`)
1. **Sign: "Gate full? Drop off after the crossing" (85% follow it)** — `OPT_BS0_ACCEPT=0.85` (v6 6%).
   **Only works with rule 2.** Alone it makes delay *worse* (+34%, see screening).
2. **"Flex": the sign is an option, not a commitment** — `OPT_BS0_FLEX=1`. A parent who chose `bs_0` but is
   halted next to a free gate bay still drops off there. Without it, parents who chose `bs_0` stay in the gate queue
   while bays open up next to them, the 8-bay gate zone empties, and everyone queues for 3 bays past the crossing.
3. **Drop-off past the crossing marked for 4 cars** (whole stretch to the Soi 13 merge, 1–31 m) — `OPT_BS0_SPOTS=4`
   (v6 3 cars, 1–23.5 m). Kerb marking only; `dropoff_bs0x4.add.xml`, no road change.
4. **"No drop-off in the right lane" at the gate** — `OPT_NO_BS5=1`. The right lane is the only through lane in front
   of the gate; a parent stopping there blocks it. Those parents (≈ 50/morning) use the spot past the crossing.
5. **"Not dropping off at the gate? Keep right" (upstream of the east entry)** — `OPT_KEEP_RIGHT=1`. Cars with no
   left-lane gate drop-off that go west or into P1/P2 start in the right lane (≈ 70–85/morning), so they no longer wait
   in the drop-off queue. Cars turning south into Soi 11 stay left (the turn is from the left lane only).
6. **"Stop at any free bay" (kiss & go marking)** — `OPT_P_BACK=1.0`: a parent halted on an open bay drops off there
   (v6: 100% at the front falling to 15% at the back, so most waited to reach the front → one-at-a-time drop-off).
7. **Smart gate crossing control** (camera + microcontroller, `OPT_GUARD=smart`, X1 only; X2 keeps the guard):
   - a car that is stuck behind a parent who is dropping off cannot use a green, so it does **not** hold pedestrians
     → pedestrians cross while the lane is blocked anyway, at no cost to traffic;
   - while cars can flow, pedestrians cross **in groups**: green once **12** are waiting or the first has waited
     **45 s** (`OPT_PED_MIN_BATCH=12`, `OPT_PED_MAXWAIT=45`);
   - unchanged safety rules: yellow 3 s, all-red until the junction is empty, cars go only once the crossing is empty.

### Optional extra: organised drop-off (changes an assumption — team decision needed)
The 35 s drop-off time is the biggest single lever. If staff open doors and children are ready with their bags, the
mean drop-off time falls. 30 s → 192 s delay (−58% vs v6); 25 s (6 seeds) → 130 s. The 35 s itself was never timed on
site (HANDOFF §12), so time real drop-offs before relying on this. Presets `best_dwell30`, `best_dwell25`.

## What was found (bottlenecks in v6)
1. **One left lane does everything.** Gate parents, Soi 11 drivers and through cars that entered on the left all
   share a single-file queue behind parents who are dropping off. Left-lane entries wait 400–500 s just to enter
   the road; right-lane entries ~40 s. → rules 4, 5.
2. **One-at-a-time drop-off.** Parents wait to reach the front bay instead of using a free bay behind → rule 6.
3. **The spot past the crossing is unused (6%)** — but it is also where right-lane cars must merge left to turn
   into Soi 11, and parents who commit to it stay in the gate queue. Raising use to 85% only helps with flex (rule 2)
   and a longer marking (rule 3).
4. **The guard stops for halted cars that could not move anyway**, and gives way to single pedestrians while cars
   flow → rule 7 (shorter pedestrian waits *and* less car delay).
5. **Drop-off time** (35 s) dominates whatever is left → optional organised drop-off.

## Screening (6 seeds each, seeds 1–6; `screen/`, table in `screen/screening_summary.txt`)

| Run | Change vs v6 | Delay all (s) | Ped X1 mean (s) |
|---|---|---|---|
| s0 | v6 | 428 | 14.3 |
| s1 | sign 85% only (no flex) | **576 (worse)** | 19.0 |
| s2 | sign 85% + bs_0 4 cars | 501 (worse) | 18.1 |
| s3 | keep right | 395 | 14.3 |
| s4 | stop at any free bay | 396 | 15.0 |
| s5 | all 8 bays always open | 456 (no gain → not used) | 14.3 |
| s6 | smart guard (8 peds / 30 s) | 435 | **8.2** |
| s7 | drop-off 25 s | 240 | 13.8 |
| s8 | every non-gate car passes the queue on the right | 426 (no gain → not used) | 17.7 |
| c1 | sign 85% + pass on the right | **1080 (much worse)** | 23.5 |
| s9 | no right-lane drop-off | 411 | 12.2 |
| f1 | sign 85% + flex | 378 | 15.4 |
| f2 | sign 85% + flex + bs_0 4 cars | 359 | 15.2 |
| k1 | keep right + any bay + smart guard | 376 | 9.2 |
| k2 | k1 + sign 85% flex | 322 | 9.8 |
| k3 | k2 + no right-lane drop-off | 315 | 10.7 |
| k4 | k3 + bs_0 4 cars (guard 8 / 30 s) | 294 | 10.3 |
| k6 | k4, guard 5 / 20 s | 352 | 7.6 |
| **k5** | **k4, guard 12 / 45 s = BEST** | **249** | **13.8** |
| k8 | k4, guard 16 / 60 s | 248 | 16.7 |
| k7 | k4 with "any bay" chance 50% | 312 | 9.8 |
| d30 / d25 | BEST + drop-off 30 / 25 s | 185 / 130 | 14.2 / 14.1 |

The guard's group size is a dial between cars and pedestrians (k6 → k4 → k5); 12 / 45 s is where car delay stops
improving (k8 gives no more) while pedestrians still wait less than with today's guard. If the school prefers
shorter pedestrian waits, 8 / 30 s still cuts car delay by 31% with 10 s pedestrian waits.

## How to run (from this folder; Windows `py -3`, needs SUMO on PATH / `SUMO_HOME`)
```
OPT_PRESET=best python3 guard_control.py 1 --gui                    # watch the best package, seed 1
OPT_PRESET=best python3 run_seeds.py 10 --jobs 8 --out results_best  # 10 seeds in parallel (~8 min on 8 cores)
python3 compare.py ../baseline_v6/results results_best              # side-by-side KPI table
OPT_PRESET=best OPT_PED_MAXWAIT=30 OPT_PED_MIN_BATCH=8 python3 run_seeds.py 10 --jobs 8 --out results_x   # tweak one switch
```
Windows (cmd): `set OPT_PRESET=best` then the command. All switches and their v6 defaults: `opt.py`.

## Files changed vs v6
`opt.py` (new, switches), `compare.py` (new), `dropoff_bs0x4.add.xml` (new, 4-car bs_0), `make_baseline.py`
(keep-right lane choice, drop-off time switch, `--rou/--tls` output paths), `driver_logic.py` (85% / flex / no bs_5 /
pass-right), `dynamic_dropoff.py` (any-bay chance, min open bays, flex parents), `guard_control.py` (`SmartGuard`,
pedestrian counts), `run_seeds.py` (parallel seeds, per-seed demand files, settings.json).

## Limits
- Same model limits as v6: main-road volume unverified, MOCK values, 35 s drop-off time not timed on site.
- "85% follow the sign", "parents keep right / stop at any free bay" are assumed compliance rates, not observed.
- The smart guard assumes a camera can tell a parent who is dropping off from a car that can drive on.
- Vehicle–pedestrian conflicts are not measured (only collisions, 0 everywhere).
