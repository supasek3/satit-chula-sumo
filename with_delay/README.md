# with_delay: camera delay at Gate X1

Question: how much does the camera delay hurt the camera-controlled signal at Gate X1, if the cameras are connected by
**Ethernet** or by **Wi-Fi**?

Delays (team measurement, camera to screen, 6 Nov 2026): **Ethernet 0.3–0.5 s**, **Wi-Fi 0.6–1.5 s**.
Object-detection time on the computer is not included yet (`DETECT_DELAY`, default 0).

Time window: simulated **06:30–07:45** (hard stop), measured **07:15–07:45** (the peak). 06:30–07:15 builds the queue
and is not counted. In sumo-gui the clock counts seconds from 06:30: 2700 = 07:15, 4500 = 07:45.

## Where everything is

```
with_delay/
├── README.md                    this file
├── run_delay.sh                 runs all 10 cases (5 seeds each)
├── analyze_all.py               compares the cases -> compare_camera_delay.csv, all_versions.json
├── plot_distributions.py        histogram + bell curve per case
├── camera_delay.py              the camera delay function (a copy sits in every version folder)
├── 1_Baseline/
│   └── baseline_v7/             Baseline (human guard, no camera)
└── 2_Optimisations/
    ├── scenario_fluke_v7/       Fluke (Fluke's signal at X1)
    └── scenario_combined_v7/    Poom (best) AND Combo B - one folder, chosen with OPT_PRESET
```

**Poom has no folder of his own here.** He runs in `scenario_combined_v7` with `OPT_PRESET=best`: Poom's rules + Poom's
smart X1 control (the same `best` rules as his own folder `scenario_opt_v7`). `OPT_PRESET=combo_B` in the same folder
gives Poom's rules + Fluke's X1 signal. So one folder holds both, and only one copy of the delay code was needed.

## The 10 cases (5 seeds each)

| # | Version | Camera delay | Folder | Settings | Results folder |
|---|---|---|---|---|---|
| 1 | Baseline (human guard) | none (no camera) | `1_Baseline/baseline_v7` | `CAMERA_DELAY=none` | `results_nodelay` |
| 2 | Fluke | none | `2_Optimisations/scenario_fluke_v7` | `CAMERA_DELAY=none` | `results_nodelay` |
| 3 | Fluke | Ethernet 0.3–0.5 s | `2_Optimisations/scenario_fluke_v7_ethernet` * | `CAMERA_DELAY=ethernet` | `results_ethernet` |
| 4 | Fluke | Wi-Fi 0.6–1.5 s | `2_Optimisations/scenario_fluke_v7_wifi` * | `CAMERA_DELAY=wifi` | `results_wifi` |
| 5 | Poom (best) | none | `2_Optimisations/scenario_combined_v7` | `CAMERA_DELAY=none OPT_PRESET=best` | `results_poom_nodelay` |
| 6 | Poom (best) | Ethernet 0.3–0.5 s | `2_Optimisations/scenario_combined_v7` | `CAMERA_DELAY=ethernet OPT_PRESET=best` | `results_poom_ethernet` |
| 7 | Poom (best) | Wi-Fi 0.6–1.5 s | `2_Optimisations/scenario_combined_v7` | `CAMERA_DELAY=wifi OPT_PRESET=best` | `results_poom_wifi` |
| 8 | Combo B | none | `2_Optimisations/scenario_combined_v7` | `CAMERA_DELAY=none OPT_PRESET=combo_B` | `results_combo_B_nodelay` |
| 9 | Combo B | Ethernet 0.3–0.5 s | `2_Optimisations/scenario_combined_v7` | `CAMERA_DELAY=ethernet OPT_PRESET=combo_B` | `results_combo_B_ethernet` |
| 10 | Combo B | Wi-Fi 0.6–1.5 s | `2_Optimisations/scenario_combined_v7` | `CAMERA_DELAY=wifi OPT_PRESET=combo_B` | `results_combo_B_wifi` |

\* `run_delay.sh` makes these two working copies of `scenario_fluke_v7` when it starts. Fluke writes its demand file
into its own folder, so the three Fluke cases need separate folders to run at the same time. Poom and Combo B write
their demand files into each results folder, so they can share `scenario_combined_v7`.

The baseline has only "none": the guard is a person watching the crossing, not a camera.

How to compare:
- **Effect of the camera** = a delay case against the same version without delay (3, 4 vs 2; 6, 7 vs 5; 9, 10 vs 8).
- **Still better than today?** = every case against the baseline (1).

## What changed compared with `4_Window_0700_0745`

1. **Measured 07:15–07:45 (peak, user decision 6 Nov 2026)**: results count only cars and students planned to depart
   07:15–07:45 (`MEASURE_BEGIN = 2700` in `run_seeds.py`, `BEGIN` in `analyze_all.py`).
2. **`camera_delay.py`**: the X1 controller sees the crossing as the camera saw it a moment ago. Every 0.1 s step the
   real view of X1 is stored as a frame; the controller gets the frame closest to *d* s old. *d* is drawn uniformly
   from the range and held about 1 s, so the lag drifts within the range; the picture never goes back in time (it
   freezes when the lag grows, jumps forward when it shrinks). Delayed together: cars approaching (30 m), cars inside
   the crossing, students waiting, students on the crossing, and for Poom also the number of waiting students, the
   longest wait and his own car check (can a car actually drive over the crossing?). X2 keeps the human guard, who sees
   in real time. Tested on its own: Ethernet lag 0.3–0.5 s (mean 0.40 s), Wi-Fi 0.6–1.5 s (mean 1.02 s).
3. **0.1 s simulation steps** (`step-length` in each `baseline.sumocfg`), so sub-second delays show. The no-delay cases
   also run at 0.1 s, so every comparison is at the same step. Queue and summary outputs stay at one line per second.
4. **Safety check** `x1_walk_with_car_inside_s`: seconds (07:15–07:45) in which X1 shows the walk signal while a car is
   really inside the crossing area, the risk a late "crossing clear" picture creates. Also `camera_delay_mean_s` and
   `camera_delay_max_s` (the lag the controller actually had).

## Run (on the Mac)

All 10 cases, four streams side by side (a finished case is skipped if you rerun after an interruption):
```
cd ~/Desktop/SUMO_Project/with_delay && ./run_delay.sh
python3 analyze_all.py --seeds 5
```
Keep the Mac plugged in and awake. 0.1 s steps make each run several times slower than the 1 s runs.

Watch one case in sumo-gui (change the folder and settings from the table above; seed 1):
```
export SUMO_HOME=/Library/Frameworks/EclipseSUMO.framework/Versions/Current/EclipseSUMO/share/sumo
export PATH=/Library/Frameworks/EclipseSUMO.framework/Versions/Current/EclipseSUMO/bin:$PATH
cd ~/Desktop/SUMO_Project/with_delay/2_Optimisations/scenario_combined_v7 && mkdir -p output
CAMERA_DELAY=wifi OPT_PRESET=best python3 guard_control.py 1 --gui        # Poom, Wi-Fi
CAMERA_DELAY=ethernet OPT_PRESET=combo_B python3 guard_control.py 1 --gui # Combo B, Ethernet
```
sumo-gui can take up to a minute to open ("Retrying in 1 seconds" while it starts); do not press Ctrl+C.
The GUI plays the 06:30–07:00 warm-up at full speed by itself and **pauses at 07:00** (clock 1800), with the queue
already built. Press play to watch from there; raise the toolbar Delay to slow it down. `GUI_START=2700` pauses at
07:15 (start of the measured peak) instead, `GUI_START=0` turns the pause off.

## Results

`compare_camera_delay.csv` gives every KPI per case, its change vs the baseline (`_diff`, `_pct`) and, for the delay
cases, its change vs the same version without delay (`_vsnd`, `_vsnd_pct`): that last one is the effect of the camera.
Results: not run yet.
