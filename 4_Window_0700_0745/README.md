# 4_Window_0700_0745 — all versions, simulated 07:00–07:45 only

Clones of the `Optimisation` branch folders (5 Nov 2026), changed **only** in their time window:

| Folder | Version |
|---|---|
| `1_Baseline/baseline_v7/` | Baseline v7 |
| `2_Optimisations/scenario_opt_v7/` | Poom (`OPT_PRESET=best`) |
| `2_Optimisations/scenario_z1_dropoff_v7/` | Left-turn optimisation (gate left-turners drop off at Z1) |
| `2_Optimisations/scenario_fluke_v7/` | Fluke (proposed signal controller) |
| `2_Optimisations/scenario_combined_v7/` | Combos A–F (`OPT_PRESET=combo_A` … `combo_F`) |
| `2_Optimisations/compare_v7.py` | Compares against `1_Baseline/baseline_v7` **in this folder** |

Old full-morning results were not copied, so nothing here can be mixed up with 06:30–08:10 numbers.

## What changed (same in every folder)
1. `make_baseline.py` — the full morning is still generated exactly as in v7 (same random draws), then only cars and
   pedestrians **departing 07:00–07:45** (t = 1800–4500 s) are written. Checked for seed 1 in all 10 versions: the
   kept 1,325 items (688 cars, 637 pedestrians) are identical to v7's cars in that window. Edit
   `WINDOW_BEGIN, WINDOW_END` to change the window.
2. `baseline.sumocfg` — `begin` = 1800 (the clock starts at 07:00; t = 0 is still 06:30).
3. `run_seeds.py` — `DEMAND_END` = 4500. KPI names now say 0745: `last_vehicle_done_min_after_0745`,
   `veh_arrived_by_0745` (same in `compare*.py`).
4. `dynamic_dropoff.py` — drop-off zone statistics collected up to 07:45.

The run still continues after 07:45 until the last car has finished, so every car's delay counts.

**Caveat:** the road starts **empty** at 07:00. In the full-morning runs the 06:30–07:00 traffic has already built a
queue by 07:00, so delays here will be lower than the 07:00–07:45 part of the full run. Compare these folders only
with each other.

## Run (inside a folder; Windows: `py -3`)
```
mkdir -p output
python3 guard_control.py 1 --gui                                   # watch seed 1 (baseline / z1 / fluke)
OPT_PRESET=best python3 guard_control.py 1 --gui                   # Poom
OPT_PRESET=combo_F python3 guard_control.py 1 --gui                # a combo
python3 run_seeds.py 10 --out results                              # baseline_v7, z1, fluke
OPT_PRESET=best python3 run_seeds.py 10 --out results_best --jobs 3   # Poom
./run_all.sh                                                       # combos A–F (in scenario_combined_v7)
```
Run the baseline first; `compare_v7.py` and `run_all.sh` read `1_Baseline/baseline_v7/results/kpi_seeds.csv`.
