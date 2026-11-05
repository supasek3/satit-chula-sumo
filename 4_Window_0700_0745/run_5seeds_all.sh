#!/bin/bash
# 5 seeds (07:00-07:45) for every version + its distribution chart. Baseline uses its existing seeds 1-5.
# Usage:  cd ~/Desktop/SUMO_Project/4_Window_0700_0745 && ./run_5seeds_all.sh
# A version with all 5 seeds already done is skipped, so you can rerun after an interruption.
cd "$(dirname "$0")"; ROOT="$PWD"
EB=/Library/Frameworks/EclipseSUMO.framework/Versions/Current/EclipseSUMO
export SUMO_HOME="${SUMO_HOME:-$EB/share/sumo}"; export PATH="$EB/bin:$PATH"
AWAKE=""; command -v caffeinate >/dev/null && AWAKE="caffeinate -i"
run() {  # folder results-dir preset extra
  cd "$ROOT/$1" && mkdir -p output
  if [ -f "$2/seed_5/tripinfo.xml" ] && tail -c 20 "$2/seed_5/tripinfo.xml" | grep -q "</tripinfos>" && [ -f "$2/kpi_seeds.csv" -o "$2" = "results" ]; then
    echo "== $1 $3: 5 seeds already done"
  else
    echo "== $1 ${3:-} started $(date +%H:%M)"
    OPT_PRESET="$3" $AWAKE python3 run_seeds.py 5 --out "$2" $4 > "$2.log" 2>&1 || { echo "   FAILED, see $1/$2.log"; tail -5 "$2.log"; return; }
  fi
  python3 "$ROOT/plot_distributions.py" . --results "$2" --seeds 5 | tail -1
}
run 1_Baseline/baseline_v7 results ""
run 2_Optimisations/scenario_fluke_v7 results_5 ""
run 2_Optimisations/scenario_z1_dropoff_v7 results_5 ""
run 2_Optimisations/scenario_opt_v7 results_best5 best "--jobs 3"
for c in A B C D E F; do run 2_Optimisations/scenario_combined_v7 results_combo_${c}5 combo_$c "--jobs 3"; done
echo "ALL DONE $(date +%H:%M)"
