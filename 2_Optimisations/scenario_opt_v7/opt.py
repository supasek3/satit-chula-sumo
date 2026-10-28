"""SCENARIO opt (v7): optimisation switches on top of baseline_v7. Every switch defaults to the baseline value, so with no
environment variables set this folder runs exactly baseline_v7.

Set a switch with an environment variable of the same name, e.g.
    OPT_BS0_ACCEPT=0.85 OPT_KEEP_RIGHT=1 python3 run_seeds.py 10 --out results_x
or pick a named package with OPT_PRESET (see PRESETS below; single variables still override the preset).

Demand (flow rates, lanes, routes, who carries a student) is never changed by these switches.
"""
import os

DEFAULTS = dict(                 # v6 values
    OPT_BS0_ACCEPT=0.06,         # share of gate parents who use the drop-off past the crossing (bs_0) when the gate is full
    OPT_BS0_SPOTS=3,             # bs_0 length in cars (3 = 22.5 m; 4 = 30 m, the whole edge up to the Soi 13 merge)
    OPT_BS0_FIRST=0.0,           # share of gate parents who aim for bs_0 FIRST (sign "drop off past the crossing")
    OPT_BS0_FLEX=0,              # 1 = a parent heading for bs_0 still takes a gate spot that opens next to it
    OPT_NO_BS5=0,                # 1 = no drop-off in the right lane at the gate (sign): bs_5 parents use bs_0 instead
    OPT_PASS_RIGHT=0,            # 1 = every car with no left-lane gate drop-off passes the gate queue in the right lane
    OPT_KEEP_RIGHT=0,            # 1 = cars with no gate drop-off ahead that go west keep to the right lane (sign)
    OPT_P_BACK=0.15,             # chance a halted parent drops off at the back of the queue (1.0 = "stop at any bay")
    OPT_MIN_SPOTS=5,             # gate zone spots always open (8 = whole 60 m zone always marked)
    OPT_DWELL=35.0,              # mean drop-off time, s (organised "kiss & go" drop-off = shorter)
    OPT_GUARD="base",            # X1 crossing control: base (v6 guard) | smart (camera-aware guard, see guard_control.py)
    OPT_PED_MAXWAIT=30.0,        # smart guard: a pedestrian never waits longer than this while cars can flow, s
    OPT_PED_MIN_BATCH=8,         # smart guard: while cars can flow, start pedestrian green once this many are waiting
)

BEST = dict(                     # best package found (see README): signs + lane rules + smart guard, 35 s drop-off kept
    OPT_BS0_ACCEPT=0.85, OPT_BS0_FLEX=1, OPT_BS0_SPOTS=4, OPT_NO_BS5=1, OPT_KEEP_RIGHT=1, OPT_P_BACK=1.0,
    OPT_GUARD="smart", OPT_PED_MAXWAIT=45.0, OPT_PED_MIN_BATCH=12)
PRESETS = {
    "v6": {},
    "sign85": dict(OPT_BS0_ACCEPT=0.85),                       # the 85% sign alone (makes things worse)
    "sign85_flex": dict(OPT_BS0_ACCEPT=0.85, OPT_BS0_FLEX=1),  # the 85% sign, parents still take a gate spot
    "best": BEST,
    "best_dwell30": dict(BEST, OPT_DWELL=30.0),                # + organised drop-off, 30 s mean (assumption change)
    "best_dwell25": dict(BEST, OPT_DWELL=25.0),                # + organised drop-off, 25 s mean (assumption change)
}


def _load():
    vals = dict(DEFAULTS)
    vals.update(PRESETS[os.environ.get("OPT_PRESET", "v6")])
    for k, v in DEFAULTS.items():
        if k in os.environ:
            vals[k] = type(v)(os.environ[k])
    return vals


O = _load()
BS0_ACCEPT, BS0_SPOTS, BS0_FIRST = O["OPT_BS0_ACCEPT"], O["OPT_BS0_SPOTS"], O["OPT_BS0_FIRST"]
NO_BS5, PASS_RIGHT, BS0_FLEX = O["OPT_NO_BS5"], O["OPT_PASS_RIGHT"], O["OPT_BS0_FLEX"]
KEEP_RIGHT, P_BACK, MIN_SPOTS, DWELL = O["OPT_KEEP_RIGHT"], O["OPT_P_BACK"], O["OPT_MIN_SPOTS"], O["OPT_DWELL"]
GUARD, PED_MAXWAIT, PED_MIN_BATCH = O["OPT_GUARD"], O["OPT_PED_MAXWAIT"], O["OPT_PED_MIN_BATCH"]


def describe():
    return {k: v for k, v in O.items() if v != DEFAULTS[k]} or "v6 (no change)"
