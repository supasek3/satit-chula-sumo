"""v7: make every run repeatable.

Python randomises the order of sets between runs unless PYTHONHASHSEED is fixed, and the controllers loop over
sets of vehicle IDs, so the same seed could give slightly different results (Fluke's review, 22 Oct 2026).
Importing this module first restarts the script once with PYTHONHASHSEED=0 if it is not already set.
"""
import os, subprocess, sys

if os.environ.get("PYTHONHASHSEED") != "0" and sys.argv and sys.argv[0].endswith(".py"):
    os.environ["PYTHONHASHSEED"] = "0"
    sys.exit(subprocess.call([sys.executable] + sys.argv, env=os.environ))
