#!/bin/bash
# Camera delay at Gate X1, measured 07:15-07:45 (peak; simulated from 06:30), 0.1 s steps, 5 seeds per case:
#   baseline (guard, no camera) | Fluke, Poom (best), Combo B: each with no delay, Ethernet 0.3-0.5 s, Wi-Fi 0.6-1.5 s
# Usage:  cd ~/Desktop/SUMO_Project/with_delay && ./run_delay.sh      (10 cases)
# Four streams run side by side. A finished case is skipped, so you can rerun after an interruption.
# Keep the Mac awake and plugged in. Then:  python3 analyze_all.py --seeds 5
# Add object-detection time once measured:  DETECT_DELAY=0.1 ./run_delay.sh  (move the old results folders away first)
cd "$(dirname "$0")"; ROOT="$PWD"
EB=/Library/Frameworks/EclipseSUMO.framework/Versions/Current/EclipseSUMO
export SUMO_HOME="${SUMO_HOME:-$EB/share/sumo}"; export PATH="$EB/bin:$PATH"
AWAKE=""; command -v caffeinate >/dev/null && AWAKE="caffeinate -i"

run() {  # folder results-dir camera preset extra
  cd "$ROOT/$1" && mkdir -p output
  if [ -f "$2/kpi_seeds.csv" ]; then echo "== $1 $2: already done"; return; fi
  echo "== $1 $2 started $(date +%H:%M)"
  CAMERA_DELAY="$3" OPT_PRESET="$4" $AWAKE python3 run_seeds.py 5 --out "$2" $5 > "$2.log" 2>&1 \
    && echo "   $1 $2 done $(date +%H:%M)" || { echo "   $1 $2 FAILED, see $1/$2.log"; tail -5 "$2.log"; }
}
copy() {  # Fluke writes its demand file into its own folder: one working copy per case so cases can run side by side
  [ -d "$ROOT/$2" ] && return
  mkdir -p "$ROOT/$2" && cp -R "$ROOT/$1/." "$ROOT/$2/" && rm -rf "$ROOT/$2"/results_* "$ROOT/$2"/output
}
F=2_Optimisations/scenario_fluke_v7
copy $F ${F}_ethernet
copy $F ${F}_wifi

( run 1_Baseline/baseline_v7 results_nodelay none ""
  run $F results_nodelay none "" ) &
( run ${F}_ethernet results_ethernet ethernet ""
  run ${F}_wifi results_wifi wifi "" ) &
( for m in none ethernet wifi; do r=$m; [ $m = none ] && r=nodelay
    run 2_Optimisations/scenario_combined_v7 results_combo_B_$r $m combo_B "--jobs 2"; done ) &
( for m in none ethernet wifi; do r=$m; [ $m = none ] && r=nodelay   # Poom (best) = same folder, preset best
    run 2_Optimisations/scenario_combined_v7 results_poom_$r $m best "--jobs 2"; done ) &
wait
echo "ALL DONE $(date +%H:%M)"
