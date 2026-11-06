# with_delay: camera delay at Gate X1

Question: how much does the camera delay hurt the camera-controlled signal at Gate X1, if the cameras are connected by
**Ethernet** or by **Wi-Fi**?

Delays (team measurement, camera to screen, 6 Nov 2026): **Ethernet 0.3–0.5 s**, **Wi-Fi 0.6–1.5 s**.
Object-detection time on the computer is not included yet (`DETECT_DELAY`, default 0).

## Cases (5 seeds each, measured 07:15–07:45 = peak, simulated from 06:30, hard stop 07:45)

| Version | No delay | Ethernet | Wi-Fi |
|---|---|---|---|
| Baseline v7 (human guard, no camera) | ✓ | – | – |
| Fluke (Fluke's signal at X1) | ✓ | ✓ | ✓ |
| Poom (best: Poom's rules + smart X1 control) | ✓ | ✓ | ✓ |
| Combo B (Poom's rules + Fluke's signal at X1) | ✓ | ✓ | ✓ |

Poom runs in `scenario_combined_v7` with `OPT_PRESET=best` (same rules as `scenario_opt_v7`). His smart control also
uses its own car check (can a car actually drive over the crossing?); that check is delayed with the other inputs.

The folders are copies of `4_Window_0700_0745` (06:30 warm-up). Changes:
0. **Measured 07:15–07:45 (peak, user decision 6 Nov 2026)**: results count only cars and students planned to depart
   07:15–07:45 (`MEASURE_BEGIN = 2700` in `run_seeds.py`, `BEGIN` in `analyze_all.py`); 06:30–07:15 builds the queue.
1. **`camera_delay.py`** (copied into each version folder): the X1 controller sees the crossing as the camera saw it a
   moment ago. Every step the real view of X1 is stored as a frame; the controller gets the frame closest to *d* s old.
   *d* is drawn uniformly from the range and held about 1 s, so the lag drifts within the range; the picture never goes
   back in time (it freezes when the lag grows, jumps forward when it shrinks). All four X1 inputs are delayed together:
   cars approaching (30 m), cars inside the crossing, students waiting, students on the crossing. X2 keeps the human
   guard, who sees in real time. Choose with `CAMERA_DELAY=none|ethernet|wifi`.
   Tested on its own: Ethernet lag 0.3–0.5 s (mean 0.40 s), Wi-Fi 0.6–1.5 s (mean 1.02 s).
2. **0.1 s simulation steps** (`step-length` in `baseline.sumocfg`), so sub-second delays show. The no-delay cases are
   rerun at 0.1 s too, so every comparison is at the same step. Queue and summary outputs stay at 1 per second.
3. **Safety check** `x1_walk_with_car_inside_s`: seconds in which X1 shows the walk signal while a car is really inside
   the crossing area, the risk a late "crossing clear" picture creates. Also `camera_delay_mean_s`, `camera_delay_max_s`.

## Run (on the Mac)
```
cd ~/Desktop/SUMO_Project/with_delay && ./run_delay.sh      # 10 cases × 5 seeds, four streams side by side
python3 analyze_all.py --seeds 5                             # -> compare_camera_delay.csv, all_versions.json
```
`run_delay.sh` makes working copies `scenario_fluke_v7_ethernet` and `scenario_fluke_v7_wifi` (Fluke writes its demand
file into its own folder, so cases need separate folders to run side by side). A finished case is skipped on rerun.

Watch one case in the GUI, e.g. Combo B on Wi-Fi:
```
cd 2_Optimisations/scenario_combined_v7 && mkdir -p output && CAMERA_DELAY=wifi OPT_PRESET=combo_B python3 guard_control.py 1 --gui
```

`compare_camera_delay.csv` gives every KPI per case, its change vs the baseline (`_diff`, `_pct`) and, for the delay
cases, its change vs the same version without delay (`_vsnd`, `_vsnd_pct`): that last one is the effect of the camera.
