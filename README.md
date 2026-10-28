# Satit Chula SUMO — smart drop-off and pedestrian crossing

Morning peak 06:30–08:10 at the gate of Satit Chulalongkorn Demonstration School. Gate X1 = main gate crossing,
Gate X2 = Soi 11 crossing. Thailand drives on the left; the main road is one-way east → west.

| Folder | What it is |
|---|---|
| `1_Baseline/baseline_v7/` | **Baseline**: v6 + Fluke's two bug fixes (one entrance per car; left lane kept through junctions) + repeatable runs. 10-seed results: vehicle delay 374 s, Gate X1 pedestrian p95 41.6 s, 0 collisions/teleports. |
| `2_Optimisations/` | **All optimisations**, each on baseline_v7: `scenario_opt_v7` (Poom, −42%), `scenario_z1_dropoff_v7` (Supasek Z1 left-turn, −33%), `scenario_fluke_v7` (Fluke, −9%, Gate X1 ped p95 −28%), `scenario_combined_v7` (combos A–F) and `compare_v7.py`. |
| `3_Chosen_optimisation/optimisation_f/` | **Chosen optimisation: combo F** = Poom's lane + drop-off rules + 100% Z1 redirect + Fluke's signal at Gate X1 and X2. Delay 374 → 187 s (−50%), Gate X1 pedestrian p95 41.6 → 30.1 s, 0 collisions; Gate X2 pedestrian waits about double. |
| `archive/` | Earlier work: baselines v0, v5, v6, older scenarios (officer, Webster), Poom's original v6 package, reference data and working log, unused files. |

All runs: same demand (same cars, pedestrians, departure times), 10 seeds, compared seed by seed against baseline_v7.
Caveats: main-road volume unverified; 35 s mean drop-off assumed; sign compliance assumed.

Run anything from inside its folder (macOS; on Windows use `py -3`):
```
mkdir -p output
python3 guard_control.py 1 --gui                 # watch seed 1 (combo F in optimisation_f; OPT_PRESET=... elsewhere)
python3 run_seeds.py 10 --out results            # 10 seeds -> results/kpi_seeds.csv
```
If `sumo` is not found: `export PATH=/Library/Frameworks/EclipseSUMO.framework/Versions/1.28.0/EclipseSUMO/bin:$PATH`.
