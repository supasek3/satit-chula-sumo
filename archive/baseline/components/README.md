# Components: everything behind the baseline

The files in `baseline/` are enough to run the baseline. This folder holds everything used to **build** it,
plus earlier versions and results, so the work can be traced and rebuilt.

## network_build/: how `network_crossings.net.xml` was made, in order
Run the commands in a working folder containing these files. netconvert is SUMO 1.28. Never overwrite `network.net.xml`.

| Step | Files | What it does |
|---|---|---|
| 0 | `network.net.xml` | Master network drawn in netedit from OSM (UTM 47, left-hand traffic). Untouched. |
| 1 | `fix_sidewalks.py`, `make_crossings.sh`, `crossings.nod/edg/con.xml` → `network_base.net.xml` | Removes extra sidewalk lanes, adds pedestrian pads and the two signalised crossings |
| 2 | (manual, netedit, 15:19) → `../network_history/network_crossings.netedit_1519.net.xml` | User moved the Soi 11 crossing (J1) and its pad ~20 m north. **Start rebuilding from this file.** |
| 3 | `soi11.nod/edg.xml` | Slides the Soi 11 pass-through node north, so the Z1 lane fits 4 cars |
| 4 | `driveways.nod/edg/con.xml` + `--remove-edges.explicit E0,E1,E2,E3` | Splits the main road and connects parking driveways P1/P2 |
| 5 | `merge.nod/edg.xml` | Soi 13 merge = priority junction, side road gives way |
| 6 | `driveways_swap.edg.xml` | Driveway IN lane on the east side, OUT lane on the west side |
| 7 | `driveways_keepclear.con.xml` | Main road left lane may queue across driveway mouths; parking exits into the right lane only |
| 8a | `move_X1_stepA.nod/con.xml` + `--remove-edges.explicit P1_IN,P1_OUT,walk_gate_N --tls.unset 10072794956` | Removes the old gate signal and crossing |
| 8b | `move_X1_stepB.nod/edg/con.xml` | Gate crossing X1 onto the OSM zebra node `10784747877`; P1 onto the old X1 node; P2 moved west |
| 8c | `move_X1_stepC.nod/edg.xml` | P1 onto the second OSM parking connection (x 288.1), so the gate drop-offs fit 4 cars |

Each step: `netconvert -s <previous>.net.xml --node-files … --edge-files … --connection-files … -o <next>.net.xml`.
`network_history/` holds the network after each step, for checking.

## network_history/
Network before each change: `netedit_1519` (after step 2), `before_driveways` (before 4), `before_merge` (before 5),
`before_swap` (before 6), `before_keepclear` (before 7), `before_move_X1` (before 8).

## original_files/
The project's first files: `satit.net.xml`, `satit.rou.xml`, `satit.sumocfg`, and the OSM screenshot.

## data_sources/
The friend's AnyLogic data register (`…Register_with_Map_Schema.xlsx`) and network schema (`…Network_Data_Schema.txt`).
`baseline_inputs.csv` (one folder up) was made from them.

## previous_versions/
Earlier `dropoff.add.xml` versions (`.bak` = oldest … `.bak5` = before the X1 move) and `make_baseline.before_move.py`
(before 90% of Soi 13 and parking traffic moved to the main road).

## earlier_results/: 10-seed KPI tables from earlier states (not comparable with the final baseline)
| File | State |
|---|---|
| `kpi_seeds_fixedplan.csv` | Fixed signal plan, ~12 s drop-off, original side-road and parking flows |
| `kpi_seeds_dwell12s.csv` | Guard controller, ~12 s drop-off |
| `kpi_seeds_before_move.csv` | Guard controller, 35 s drop-off, original side-road and parking flows |
| `kpi_seeds_no_driver_logic.csv` | 90% of Soi 13 and parking traffic moved to the main road, no driver logic, old crossing position; delay includes time queued before entering |
Delays in the first three tables exclude time queued before entering the network.

## docs/
`HANDOFF_CLAUDE.md`: full working log and decisions at freeze time (also in `reference/WORKING_LOG.md` of the handoff package).
