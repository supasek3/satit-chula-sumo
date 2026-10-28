#!/bin/bash
# Runs every combination over 10 seeds (3 in parallel) and prints the comparison with baseline_v7.
# Usage (from this folder):  ./run_all.sh            all six
#                            ./run_all.sh combo_C    only the ones named
# caffeinate keeps the Mac awake (macOS). Each combination takes ~10-12 min.
cd "$(dirname "$0")"
mkdir -p output
PRESETS="${@:-combo_A combo_B combo_C combo_D combo_E combo_F}"
KEEP_AWAKE=""; command -v caffeinate >/dev/null && KEEP_AWAKE="caffeinate -i"
for p in $PRESETS; do
  if [ -f "results_$p/kpi_seeds.csv" ]; then echo "== $p: already done (delete results_$p to rerun)"; continue; fi
  echo "== $p  ($(date +%H:%M))"
  OPT_PRESET=$p $KEEP_AWAKE python3 run_seeds.py 10 --out "results_$p" --jobs 3 > "results_$p.log" 2>&1 \
    && echo "   done ($(date +%H:%M))" || { echo "   FAILED - see results_$p.log"; tail -5 "results_$p.log"; }
done
python3 ../compare_v7.py --summary ../scenario_opt_v7/results_best/kpi_seeds.csv ../scenario_z1_dropoff_v7/results/kpi_seeds.csv \
  ../scenario_fluke_v7/results/kpi_seeds.csv results_combo_*/kpi_seeds.csv
