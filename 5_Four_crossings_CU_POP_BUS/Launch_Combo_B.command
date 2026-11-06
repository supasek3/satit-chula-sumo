#!/bin/zsh
SCENARIO_DIR="${0:A:h}"
cd -- "$SCENARIO_DIR"
exec /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 run_model.py --method combo_B --gui "$@"
