# scenario_z1_dropoff_v7 — Supasek's left-turn optimisation on baseline_v7 (28 Oct 2026)

**Idea:** cars that would drop off only at Gate X1 left (`bs_1`) and then turn left into Soi 11 drop off at
Gate X2 Z1 (`bs_2`) instead. Demand-only change: same cars, departure times, routes and pedestrians; only the
drop-off place of those cars changes (Z1 dwell distribution, own random stream).
Originally on branch `left-turn-optimization` (`scenario_z1_dropoff/`, built on v6).

This folder = `baseline_v7` + the redirect in `make_baseline.py` (`REDIRECT_LEFT_TURNERS`, default 1.0 = all of them).
Checked (seeds 1–10): identical to baseline_v7 demand except the 89–129 redirected cars per seed — the same cars as
in the v6 version.

Run (from this folder):
```
mkdir -p output
python3 run_seeds.py 10 --out results
REDIRECT_LEFT_TURNERS=0.5 python3 run_seeds.py 10 --out results_half    # optional: only half comply
```
Compare against `../baseline_v7/results/kpi_seeds.csv` (or run `python3 ../compare_v7.py`).

---
(baseline_v7 README follows)

