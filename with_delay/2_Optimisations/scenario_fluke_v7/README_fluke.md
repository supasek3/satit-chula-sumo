# scenario_fluke_v7 — Fluke's proposed method on baseline_v7 (28 Oct 2026)

From Fluke's review package (branch `Fluke`, `review_2026-10-22/baseline_v6_corrected/proposed_control.py` and the
`balanced` method of `experiment.py`). Fluke's corrected baseline = baseline_v7, so the method is unchanged; only the
run scripts are the team's (`run_seeds.py`, same KPIs as baseline_v7 and the other scenarios).

**Method (FLUKE_METHOD=balanced, the default):**
- Organized drop-off at Gate X1: all 8 positions of the existing 60 m zone always open; a halted parent drops off at
  any free position (100% compliance, ideal case). Same dwell (35 s), no extra road space, no rerouting.
- Demand-responsive Gate X1 signal: pedestrians served in a natural gap after >= 8 s vehicle green, or once the oldest
  call is 25 s old; walk admission >= 4 s and <= 10 s while cars wait; clearance as in the baseline.
- Gate X2 keeps the baseline guard.

Other values of FLUKE_METHOD: `combined` (20 s trigger), `organized` (drop-off only), `adaptive` (signal only, 20 s),
`baseline` (= baseline_v7).

Run (from this folder):
```
mkdir -p output
python3 run_seeds.py 10 --out results                 # balanced, ~20 min
FLUKE_METHOD=organized python3 run_seeds.py 10 --out results_organized   # optional parts
python3 guard_control.py 1 --gui                      # watch seed 1
```
Check: Fluke's own run of `balanced` on seeds 1–10 gave journey time 449.6 s, raw vehicle delay 340.5 s,
X1 pedestrian wait 11.81 s. With the same code this run should reproduce them.
