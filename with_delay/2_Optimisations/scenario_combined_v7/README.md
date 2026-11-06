# scenario_combined_v7 — best parts of Poom, Supasek (Z1) and Fluke, on baseline_v7 (28 Oct 2026)

Built from `scenario_opt_v7` (Poom's switch system, see `README_poom.md`) plus two new switches. Demand is never
changed: only lane choice, drop-off behaviour and crossing control.

| Switch | From | Meaning |
|---|---|---|
| `OPT_Z1_REDIRECT` | Supasek | share of Gate X1-only drop-offs turning into Soi 11 that drop off at Gate X2 Z1 instead (same cars as `scenario_z1_dropoff_v7`) |
| `OPT_GUARD=fluke` | Fluke | Gate X1 signal: pedestrians served in a gap after 8 s vehicle green or once the call is `OPT_FLUKE_TRIGGER` (25) s old; walk 4–10 s |
| `OPT_X2_GUARD=fluke` | Fluke | the same signal at Gate X2 |
| `OPT_MIN_SPOTS=8` (+ `OPT_P_BACK=1`) | Fluke | all 8 Gate X1 bays always open (organized drop-off) |
| all other `OPT_*` | Poom | lane rules, bs_0 sign/flex, no bs_5, stop at any free bay, smart guard (see `opt.py`) |

Combinations (every one keeps Poom's lane + drop-off rules: keep-right, no bs_5, bs_0 4 cars with 85% flex, stop at any bay):

| Preset | X1 signal | Z1 redirect | Extra |
|---|---|---|---|
| `combo_A` | Poom smart guard | 100% | – |
| `combo_B` | Fluke | – | – |
| `combo_C` | Fluke | 100% | – (the "best of all three" candidate) |
| `combo_D` | Fluke | 50% | – |
| `combo_E` | Fluke | 100% | all 8 Gate X1 bays open |
| `combo_F` | Fluke | 100% | Fluke signal at Gate X2 too |

Checked (28 Oct): with no switches = baseline_v7 demand; Z1 redirect picks the same cars as the Z1 run; FlukeGuard gives
identical phase sequences to Fluke's `proposed_control.py`.

Run all (about 1 h 10 min, 3 seeds in parallel, keeps the Mac awake), then a summary table is printed:
```
./run_all.sh
OPT_PRESET=combo_C python3 guard_control.py 1 --gui      # watch one
```
