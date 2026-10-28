"""VARIANT baseline_officer: X1 uses officer_control.Officer; X2 uses Guard below.

Demand-responsive control of the two zebra crossings (X1 gate, X2 Soi 11), emulating the guard.

Rules per crossing, checked every simulation step:
  - Rest in vehicle green while no pedestrian is waiting.
  - Pedestrian waiting and no car approaching (moving car within APPROACH_M of the stop line)
    -> pedestrians get green at once (yellow is skipped when no car is near).
  - Both waiting -> they take turns: the side holding green keeps it at most a sampled max time,
    counted from when the other side started waiting (vehicle max ~ tri(2, 18.65, 66.55) s,
    pedestrian max ~ tri(0.2, 7.96, 22.68) s: the friend's fitted AnyLogic timings).
  - Pedestrian green ends when nobody is waiting (or its max is reached while cars wait);
    cars get green only after the crossing is empty (all-red at least ALL_RED s).
  - Pedestrians get green only once no car is inside the junction (all-red after yellow until it is empty).
Cars stopped at a drop-off do not count as approaching.
Driver choices (lane change, switching drop-off zone when full) come from driver_logic.py.

Use as a module (run_seeds.py) or directly:
    python3 guard_control.py [seed] [--gui]
"""
import os, random, sys

TOOLS = "/Library/Frameworks/EclipseSUMO.framework/Versions/1.28.0/EclipseSUMO/share/sumo/tools"
if "SUMO_HOME" in os.environ:
    TOOLS = os.path.join(os.environ["SUMO_HOME"], "tools")
sys.path.append(TOOLS)
import traci  # noqa: E402
from driver_logic import Drivers  # noqa: E402
from officer_control import Officer  # noqa: E402

VEH_MAX = (2.00, 18.65, 66.55)   # (low, mode, high) s, fitted vehicle phase (MODEL)
PED_MAX = (0.20, 7.96, 22.68)    # (low, mode, high) s, fitted pedestrian phase (MODEL)
YELLOW, ALL_RED = 3.0, 2.0       # s
VEH_MIN_GREEN = 2.0              # s, low end of the fitted vehicle phase
PED_MIN_GREEN = 1.0              # s
APPROACH_M = 30.0                # a moving car this close to the stop line holds pedestrians
SIM_END = 14400

CROSSINGS = {
    "X1": dict(tls="10784747877", crossing=":10784747877_c0", wait_edges={"walk_gate_N", ":10784747877_w0", ":10784747877_w1"}),
    "X2": dict(tls="J1", crossing=":J1_c0", wait_edges={"walk_J1_W", ":J1_w0", ":J1_w1"}),
}
STATE = {"VEH": "GGr", "YELLOW": "yyr", "VCLEAR": "rrr", "PED": "rrG", "CLEAR": "rrr"}


class Guard:
    def __init__(self, name, tls, crossing, wait_edges, rng):
        self.name, self.tls, self.crossing, self.wait_edges, self.rng = name, tls, crossing, wait_edges, rng
        self.phase, self.since, self.conflict_since, self.limit = "VEH", 0.0, None, None
        self.switches = 0

    def tri(self, p):
        return self.rng.triangular(p[0], p[2], p[1])

    def set(self, phase, now):
        self.phase, self.since, self.conflict_since, self.limit = phase, now, None, None
        traci.trafficlight.setRedYellowGreenState(self.tls, STATE[phase])
        self.switches += 1

    def step(self, now, cars_near, cars_inside, peds_waiting, peds_on_crossing):
        t = now - self.since
        if self.phase == "VEH":
            if not peds_waiting:
                self.conflict_since = None
                return
            if self.conflict_since is None:
                self.conflict_since, self.limit = now, self.tri(VEH_MAX)
            if t >= VEH_MIN_GREEN and (not cars_near or now - self.conflict_since >= self.limit):
                self.set("YELLOW" if cars_near else "VCLEAR", now)
        elif self.phase == "YELLOW":
            if t >= YELLOW:
                self.set("VCLEAR", now)
        elif self.phase == "VCLEAR":                # all-red until no car is left in the junction
            if not cars_inside:
                self.set("PED", now)
        elif self.phase == "PED":
            if not cars_near:
                self.conflict_since = None
                if not peds_waiting and not peds_on_crossing and t >= PED_MIN_GREEN:
                    self.set("CLEAR", now)          # nobody left: go back to rest (vehicle green)
                return
            if self.conflict_since is None:
                self.conflict_since, self.limit = now, self.tri(PED_MAX)
            if t >= PED_MIN_GREEN and (not peds_waiting or now - self.conflict_since >= self.limit):
                self.set("CLEAR", now)
        elif self.phase == "CLEAR":
            if t >= ALL_RED and not peds_on_crossing:
                self.set("VEH", now)


def sense():
    """Per crossing: cars approaching, pedestrians waiting, pedestrians on the crossing."""
    near = {g["tls"]: False for g in CROSSINGS.values()}
    inside = {g["tls"]: False for g in CROSSINGS.values()}
    for v in traci.vehicle.getIDList():
        road = traci.vehicle.getRoadID(v)
        if road.startswith(":"):
            tls = road[1:].rsplit("_", 1)[0]
            if tls in inside:
                inside[tls] = True
            continue
        if traci.vehicle.isStopped(v):
            continue
        for tls, _, dist, _ in traci.vehicle.getNextTLS(v)[:1]:
            if tls in near and dist <= APPROACH_M:
                near[tls] = True
    waiting = {g["crossing"]: False for g in CROSSINGS.values()}
    on = {g["crossing"]: False for g in CROSSINGS.values()}
    for p in traci.person.getIDList():
        road = traci.person.getRoadID(p)
        for g in CROSSINGS.values():
            if road == g["crossing"]:
                on[g["crossing"]] = True
            elif road in g["wait_edges"] and traci.person.getNextEdge(p) == g["crossing"]:
                waiting[g["crossing"]] = True
    return near, inside, waiting, on


def run(sumo_cmd, seed, drivers=True):
    rng = random.Random(seed * 7919 + 17)
    traci.start(sumo_cmd)
    drv = Drivers() if drivers else None
    # variant baseline_officer: X1 (gate) is run by a traffic officer, X2 (Soi 11) keeps the guard controller
    guards = [Officer(n, **g) if n == "X1" else Guard(n, rng=rng, **g) for n, g in CROSSINGS.items()]
    for g in guards:
        g.set("VEH", 0.0)
    while traci.simulation.getMinExpectedNumber() > 0 and traci.simulation.getTime() < SIM_END:
        traci.simulationStep()
        now = traci.simulation.getTime()
        near, inside, waiting, on = sense()
        for g in guards:
            g.step(now, near[g.tls], inside[g.tls], waiting[g.crossing], on[g.crossing])
        if drv:
            drv.step()
    traci.close()
    out = {g.name: g.switches for g in guards}
    for g in guards:
        if isinstance(g, Officer):
            out.update(g.stats())
    if drv:
        out.update(drv.stats())
    return out


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--gui"]
    seed = int(args[0]) if args else 1
    import subprocess
    subprocess.run([sys.executable, "make_baseline.py", str(seed)], check=True)
    binary = "sumo-gui" if "--gui" in sys.argv else "sumo"
    print(run([binary, "-c", "baseline.sumocfg", "--seed", str(seed)], seed))
