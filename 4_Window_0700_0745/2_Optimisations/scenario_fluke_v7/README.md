# baseline_v7 — common baseline for combining the optimisations

Created 28 Oct 2026. **v7 = baseline_v6 + the two bug fixes from Fluke's review (22 Oct 2026) + repeatable runs.**
Everything else (inputs, network, drop-off stops, guard controller, dwell 35 s, all MOCK values) is unchanged from v6.
All optimisations (Poom's `scenario_opt`, Supasek's `scenario_z1_dropoff`, Fluke's proposed controller) are to be
re-run on top of this folder and compared against its results.

## What changed vs baseline_v6
| # | Change | File | Effect |
|---|---|---|---|
| 1 | **One entrance per car.** v6 gave some southbound cars a gate stop *and then* a Z1 (`bs_2`) stop. Now the Z1 stop replaces the gate stop. | `make_baseline.py` (1 line) | 42–64 fewer double drop-offs per seed (seed 1: 621 → 569 stops). Same cars, pedestrians, departure times, and 105 Z1 drop-offs. Random draws unchanged. |
| 2 | **Left-lane commitment kept through junction links.** In v6 a car needing the left-lane gate stop could drift to the right lane inside the P1 driveway junction, get stuck, teleport and skip its stop. | `driver_logic.py` (9 lines, Fluke's fix) | Should remove those teleports / skipped stops. |
| 3 | **Repeatable runs.** The controllers loop over Python sets whose order changed between runs, so the same seed could give different results (Poom's and Supasek's v6 runs: 457 vs 451 s). | `hashseed.py` (new), imported first by `run_seeds.py`, `guard_control.py`, `make_baseline.py` | Same seed → same result. Scripts restart themselves once with `PYTHONHASHSEED=0`. |
| 4 | **KPI script.** Same columns as v6, plus `veh_journey_all_s` (Fluke's main measure: planned departure → arrival, incl. entry queue and drop-off). "With student" cars now come from the demand file instead of `stopTime > 0` (which missed manually held drop-offs). | `run_seeds.py` | v6 columns stay comparable. `delay_with_student_s` / `delay_no_student_s` are defined slightly differently from v6. |

Verified (28 Oct, seeds 1–10): demand identical to v6 except the double-stop cars, which keep only their Z1 stop.
Not yet verified: a SUMO run (no results in this folder yet).

## Run it (from inside this folder)
```
mkdir -p output results
python3 guard_control.py 1 --gui          # watch seed 1 (press ▶ in sumo-gui)
python3 run_seeds.py 10 --out results     # 10 seeds, ~15–25 min -> results/kpi_seeds.csv
```
macOS: if `sumo` is not found, `export PATH=/Library/Frameworks/EclipseSUMO.framework/Versions/1.28.0/EclipseSUMO/bin:$PATH`.
Windows: use `py -3` instead of `python3`.

## Rules for comparisons
- Compare scenarios only against `baseline_v7/results/kpi_seeds.csv`, on the same seeds (1–10).
- Report 10-seed means with 95% CI; check 0 collisions, teleports, unfinished vehicles.
- Main-road volume is still unverified and the 35 s dwell is still an assumption — say so with every result.
- Fluke also found results can change at a 0.2 s step; check the final combined package at `--step-length 0.2`.
