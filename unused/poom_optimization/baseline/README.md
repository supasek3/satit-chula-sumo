# Satit Chula drop-off: BASELINE (frozen 2026-10-18)

Self-contained copy of the agreed baseline. Run everything from inside this folder.

## Run

Watch one morning (seed 1) in the GUI, then press ▶:
```
python3 guard_control.py 1 --gui
```

Ten mornings with KPIs (about 15 min), written to `output/kpi_seeds.csv`:
```
python3 run_seeds.py 10
```

Time 0 = 06:30, demand ends at 6000 s (08:10), and the run continues until the last car is through.
Plain `sumo-gui -c baseline.sumocfg` runs **without** the crossing controller and driver logic, so use the commands above.

## Files

| File | Role |
|---|---|
| `network_crossings.net.xml` | Network: gate crossing X1 on the OSM zebra (node `10784747877`), Soi 11 crossing X2 (`J1`), driveways P1/P2, Soi 13 merge |
| `dropoff.add.xml` | Drop-off zones: bs_1 / bs_5 gate left/right (4 cars each), bs_0 after X1 (3), bs_2 Z1 Soi 11 (4), bs_4 after X2 (4) |
| `baseline_inputs.csv` | Count data (15-min bins, data class FIELD / MODEL / MOCK). Edit numbers here. |
| `make_baseline.py [seed]` | CSV → `baseline.rou.xml` (cars + pedestrians) and `baseline_tls.add.xml` |
| `guard_control.py` | Runs the simulation and controls both crossings like the guard (pedestrians cross when no car is coming, and vice versa) |
| `driver_logic.py` | Drivers change lane when the left lane is jammed, and pick another drop-off spot when theirs is full |
| `run_seeds.py` | Multi-seed runner and KPI table |
| `baseline.sumocfg`, `baseline.gui.xml`, `background/` | Config, GUI view (car shapes, large pedestrians), OpenStreetMap background (© OpenStreetMap contributors) |
| `results/` | KPIs of the 10-seed run of this baseline |
| `components/` | Everything used to build it: network build steps (verified to rebuild this exact network), network history, original files, the friend's data files, earlier versions and results, full project log. See `components/README.md`. |

## Main assumptions
- Main road: average of schedule 764.5 and field summary 420 vehicles (100 min). Soi 13 and both parking
  driveways carry 10% of their counts; the other 90% enter from the east and behave like main-road cars.
- Drop-off: left lane 83%, right lane 4.59% (AnyLogic), average 35 s (team figure); 70/30 west/south; Z1 105 (MOCK).
- Pedestrians: X1 889 (FIELD, 18 Aug 2026), X2 222 (MOCK).
- Crossing max times from the friend's fitted AnyLogic timings; yellow 3 s and all-red clearance added for safety.
- Full details: `CLAUDE.md` in the main project folder.
