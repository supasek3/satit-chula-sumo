# optimisation_f — chosen optimisation (combo F), on baseline_v7

Chosen by the team on 28 Oct 2026. Same code as `2_Optimisations/scenario_combined_v7`, with **combo F as the default**
(no environment variable needed). Demand is identical to baseline_v7; only lane choice, drop-off behaviour and crossing
control change.

## What combo F does
1. **Poom – lane + drop-off rules:** keep-right sign for cars with no Gate X1 left-lane drop-off (west / parking);
   no drop-off in the right lane at Gate X1 (bs_5 closed); bs_0 past the Gate X1 crossing 4 cars long, 85% of parents
   use it when the gate is full, still taking a gate bay that frees up beside them; parents stop at any free bay.
2. **Supasek – Z1 redirect (100%):** Gate X1-only drop-offs that turn left into Soi 11 drop off at Gate X2 Z1 instead
   (89–129 cars per seed).
3. **Fluke – demand-responsive signal at Gate X1 *and* Gate X2:** pedestrians served in a gap after ≥ 8 s vehicle green,
   or once the call is 25 s old; walk 4–10 s; clearance as the guard.
35 s mean drop-off kept.

## Results (10 seeds, vs baseline v7) — `results/kpi_seeds.csv`
| | Baseline v7 | Combo F |
|---|---|---|
| Vehicle delay | 374 s | **187 s (−50%)** |
| Journey time | 484 s | 297 s (−39%) |
| Gate X1 pedestrian wait mean / p95 | 14.1 / 41.6 s | **11.7 / 30.1 s** (p95 −28%) |
| Gate X2 pedestrian wait mean / p95 | 2.7 / 12.5 s | 6.6 / 26.5 s (about double) |
| Last car after 08:10 | 24.6 min | 10.8 min |
| Longest entry queue | 146 cars | 81 cars |
| Collisions / teleports | 0 / 0 | 0 / 0 |

Known trade-off: the 4-car Z1 bay overflows, parents stop just after the Gate X2 crossing and Gate X2 pedestrians wait
about twice as long (p95 still below today's Gate X1 p95). Combo D (50% redirect) halves this at a cost of ~27 s delay.

## Run (from this folder)
```
mkdir -p output
python3 guard_control.py 1 --gui                         # watch combo F, seed 1
python3 run_seeds.py 10 --out results_rerun --jobs 3     # 10 seeds (~12 min)
python3 ../../2_Optimisations/compare_v7.py results_rerun/kpi_seeds.csv   # vs baseline v7
```
Open items: 0.2 s timestep check; sign compliance (85%, lane rules) is assumed; main-road volume and 35 s dwell unverified.
Other switches still work (see `opt.py`, `README_combined.md`).
