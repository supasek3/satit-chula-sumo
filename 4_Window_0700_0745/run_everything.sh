#!/bin/bash
# Runs all 10 versions (07:00-07:45, 10 seeds each) one after another, then writes the comparison tables.
# Usage:  cd ~/Desktop/SUMO_Project/4_Window_0700_0745 && ./run_everything.sh
# A finished version is skipped (delete its results folder to rerun it). Keep the Mac awake and plugged in.
cd "$(dirname "$0")"
EB=/Library/Frameworks/EclipseSUMO.framework/Versions/Current/EclipseSUMO
export SUMO_HOME="${SUMO_HOME:-$EB/share/sumo}"; export PATH="$EB/bin:$PATH"
AWAKE=""; command -v caffeinate >/dev/null && AWAKE="caffeinate -i"
ROOT="$PWD"
run() {  # folder  results-dir  preset  extra-args
  cd "$ROOT/$1" && mkdir -p output
  if [ -f "$2/kpi_seeds.csv" ]; then echo "== $1 $3: already done"; return; fi
  echo "== $1 ${3:-} ($(date +%H:%M))"
  OPT_PRESET="$3" $AWAKE python3 run_seeds.py 10 --out "$2" $4 > "$2.log" 2>&1 && echo "   done" || { echo "   FAILED, see $1/$2.log"; tail -5 "$2.log"; }
}
run 1_Baseline/baseline_v7 results ""
run 2_Optimisations/scenario_fluke_v7 results ""
run 2_Optimisations/scenario_z1_dropoff_v7 results ""
run 2_Optimisations/scenario_opt_v7 results_best best "--jobs 3"
for c in A B C D E F; do run 2_Optimisations/scenario_combined_v7 results_combo_$c combo_$c "--jobs 3"; done
cd "$ROOT/2_Optimisations"
FILES="scenario_fluke_v7/results/kpi_seeds.csv scenario_z1_dropoff_v7/results/kpi_seeds.csv scenario_opt_v7/results_best/kpi_seeds.csv $(ls scenario_combined_v7/results_combo_*/kpi_seeds.csv 2>/dev/null)"
{ echo "Satit Chula 07:00-07:45, 10 seeds, vs baseline_v7  ($(date))"; python3 compare_v7.py --summary $FILES; python3 compare_v7.py $FILES; } | tee "$ROOT/comparison_0700_0745.txt"
echo; echo "Saved: $ROOT/comparison_0700_0745.txt"
