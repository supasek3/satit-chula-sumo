# scenario_opt_v7 — Poom's optimisation, moved onto baseline_v7 (28 Oct 2026)

Copy of `poom_optimization/scenario_opt/` (code only; old v6 results and screening runs stay in the original folder).
Changes, all identical to `baseline_v7`:
1. `make_baseline.py`: one entrance per car (Fluke fix 1).
2. `driver_logic.py`: left-lane commitment kept through junction links (Fluke fix 2), merged into Poom's version.
3. `hashseed.py` + imports: repeatable runs (PYTHONHASHSEED=0).
4. `run_seeds.py`: adds `veh_journey_all_s`; student cars counted from each seed's demand file.

Checked: with no OPT_* switches this folder generates exactly the baseline_v7 demand (seeds 1–10). With `OPT_PRESET=best`
the demand is the same apart from the keep-right lane choice (67–98 cars per seed start in the right lane).

Run (from this folder):
```
mkdir -p output
OPT_PRESET=best python3 run_seeds.py 10 --out results_best --jobs 3
```
Compare against `../../1_Baseline/baseline_v7/results/kpi_seeds.csv` (or run `python3 ../compare_v7.py`).
See `README.md` for every switch and the original v6 screening results.
