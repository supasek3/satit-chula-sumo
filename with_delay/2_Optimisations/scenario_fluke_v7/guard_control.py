"""SCENARIO dynamic_dropoff: as the baseline, plus the dynamic 4-6 spot gate drop-off zone (dynamic_dropoff.py).

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
import hashseed  # noqa: F401  v7: fixed PYTHONHASHSEED for repeatable runs
import os, random, sys

TOOLS = "/Library/Frameworks/EclipseSUMO.framework/Versions/1.28.0/EclipseSUMO/share/sumo/tools"
if "SUMO_HOME" in os.environ:
    TOOLS = os.path.join(os.environ["SUMO_HOME"], "tools")
sys.path.append(TOOLS)
import traci  # noqa: E402
from driver_logic import Drivers  # noqa: E402
from dynamic_dropoff import GateZone  # noqa: E402
from car_colors import CarColors  # noqa: E402
from camera_delay import CameraDelay  # noqa: E402  with_delay: camera delay at X1

VEH_MAX = (2.00, 18.65, 66.55)   # (low, mode, high) s, fitted vehicle phase (MODEL)
PED_MAX = (0.20, 7.96, 22.68)    # (low, mode, high) s, fitted pedestrian phase (MODEL)
YELLOW, ALL_RED = 3.0, 2.0       # s
VEH_MIN_GREEN = 2.0              # s, low end of the fitted vehicle phase
PED_MIN_GREEN = 1.0              # s
APPROACH_M = 30.0                # a moving car this close to the stop line holds pedestrians
SIM_END = 4500   # WINDOW: hard stop at 07:45 (was 14400)

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


def run(sumo_cmd, seed, drivers=True, colors=False):
    rng = random.Random(seed * 7919 + 17)
    traci.start(sumo_cmd)
    zone = GateZone(random.Random(seed * 104729 + 3))   # own random stream: guard timings stay as in the baseline
    drv = Drivers(zone, rng=random.Random(seed * 15485863 + 11)) if drivers else None   # 6% accept bs_0
    paint = CarColors(zone) if colors else None         # display only (sumo-gui)
    guards = [Guard(n, rng=rng, **g) for n, g in CROSSINGS.items()]
    x1 = CROSSINGS["X1"]
    cam = CameraDelay({x1["tls"], x1["crossing"]}, seed)
    g_x1 = [g for g in guards if g.name == "X1"][0]
    for g in guards:
        g.set("VEH", 0.0)
    while traci.simulation.getMinExpectedNumber() > 0 and traci.simulation.getTime() < SIM_END:
        traci.simulationStep()
        now = traci.simulation.getTime()
        real = sense()
        near, inside, waiting, on = cam(now, real)   # with_delay: X1 controller sees the camera's (late) view
        for g in guards:
            g.step(now, near[g.tls], inside[g.tls], waiting[g.crossing], on[g.crossing])
        cam.check(now, g_x1.phase, real[1][x1["tls"]])   # with_delay: walk shown while a car is really inside X1
        zone.step(now)
        if drv:
            drv.step()
        if paint:
            paint.step()
    traci.close()
    out = {g.name: g.switches for g in guards}
    out.update(cam.stats())
    if drv:
        out.update(drv.stats())
    out.update(zone.stats())
    return out


if __name__ == "__main__":
    import proposed_control  # scenario fluke: GUI runs use the same method as run_seeds.py
    print("FLUKE_METHOD =", proposed_control.install())
    Guard = proposed_control.base.Guard   # this script is __main__; the patched class lives in the imported guard_control
    args = [a for a in sys.argv[1:] if a != "--gui"]
    seed = int(args[0]) if args else 1
    import subprocess
    subprocess.run([sys.executable, "make_baseline.py", str(seed)], check=True)
    binary = "sumo-gui" if "--gui" in sys.argv else "sumo"
    # with_delay: in the GUI the 06:30 warm-up plays at full speed and pauses at GUI_START (default 1800 s = 07:00);
    # press play to watch from there (raise the toolbar Delay to slow it down). GUI_START=2700 pauses at 07:15.
    gui_start = os.environ.get("GUI_START", "1800")
    gui_opts = ["-S", "--delay", "0", "--breakpoints", gui_start] if "--gui" in sys.argv and gui_start != "0" else []
    print(run([binary, *gui_opts, "-c", "baseline.sumocfg", "--seed", str(seed)], seed, colors="--gui" in sys.argv))
