"""Real-world driver choices, applied every step through TraCI (called from guard_control.run).

1. Lane choice: a car queued (halted) in the left lane (index 1) of the main road, with no drop-off coming up
   on that lane, moves to the right lane (index 2) when the right lane has clearly fewer halted cars.
2. Drop-off choice: a car about to drop off checks its zone when it is within DECIDE_M of it. If the zone is
   full (cars stopped there + cars already waiting for it >= its spots), it tries the alternatives in order:
       bs_1 (gate, left)  -> bs_5 (gate, right; only if the right lane is quieter) -> bs_0 (after the X1 crosswalk)
       bs_5 (gate, right) -> bs_1 (gate, left; only if the left lane is quieter)  -> bs_0
       bs_2 (Z1, Soi 11)  -> bs_4 (after the X2 crosswalk)
   and takes the first one with a free spot; otherwise it waits in line. Each car switches at most once and keeps
   its sampled drop-off time.
"""
import traci
from traci import constants as tc

CAPACITY = {"bs_0": 3, "bs_1": 4, "bs_5": 4, "bs_2": 4, "bs_4": 4}
GATE_EDGES = ["31993796#3_E", "31993796#3_M", "31993796#3", "31993796#4"]   # main road up to X1
ALTERNATIVES = {
    "bs_1": [("bs_5", "right_quieter"), ("bs_0", None)],
    "bs_5": [("bs_1", "left_quieter"), ("bs_0", None)],
    "bs_2": [("bs_4", None)],
}
# Allow switching to the drop-off on the other lane at the gate (bs_1 <-> bs_5). Both sit on the same 30 m, so when
# both are used the main road is blocked in both lanes. False = only the after-crosswalk spot is used as overflow.
ALLOW_OTHER_LANE_DROPOFF = True
DECIDE_M = 60.0          # start checking the zone this far before it
HALT_SPEED = 0.5         # m/s
QUIETER = 0.5            # other lane counts as quieter if its halted cars <= this share of this lane's (+1)


class Drivers:
    def __init__(self):
        self.watch = {}          # vehicle -> current drop-off stop id (only cars with a gate/Z1 drop-off ahead)
        self.switched = {}       # vehicle -> (from, to)
        self.lane_changes = 0
        self.lane_changed = set()

    # ---- helpers ------------------------------------------------------------------------------
    @staticmethod
    def halted(lane_index):
        return sum(traci.lane.getLastStepHaltingNumber(f"{e}_{lane_index}") for e in GATE_EDGES)

    def demand(self, bs, me):
        """Cars stopped at bs + cars halted while heading to it (excluding me)."""
        n = traci.busstop.getVehicleCount(bs)
        for v, target in self.watch.items():
            if v != me and target == bs and not traci.vehicle.isStopped(v) and traci.vehicle.getSpeed(v) < HALT_SPEED:
                n += 1
        return n

    def lane_ok(self, cond):
        if cond is None:
            return True
        left, right = self.halted(1), self.halted(2)
        if cond == "right_quieter":
            return right <= QUIETER * (left + 1)
        return left <= QUIETER * (right + 1)

    # ---- per step -----------------------------------------------------------------------------
    def step(self):
        for v in traci.simulation.getDepartedIDList():
            stops = traci.vehicle.getStops(v, 1)
            if stops and stops[0].stoppingPlaceID in ALTERNATIVES:
                self.watch[v] = stops[0].stoppingPlaceID
        for v in traci.simulation.getArrivedIDList():
            self.watch.pop(v, None)

        for v, bs in list(self.watch.items()):
            stops = traci.vehicle.getStops(v, 1)
            if not stops or stops[0].stoppingPlaceID != bs or traci.vehicle.isStopped(v):
                del self.watch[v]                      # reached its stop (or stop done)
                continue
            if v in self.switched:
                continue
            s = stops[0]
            dist = traci.vehicle.getDrivingDistance(v, s.lane.rsplit("_", 1)[0], s.startPos)
            if dist < 0 or dist > DECIDE_M:
                continue
            if self.demand(bs, v) < CAPACITY[bs]:
                continue                               # free spot: keep the plan
            for alt, cond in ALTERNATIVES[bs]:
                if cond and not ALLOW_OTHER_LANE_DROPOFF:
                    continue
                if self.demand(alt, v) < CAPACITY[alt] and self.lane_ok(cond):
                    try:
                        traci.vehicle.replaceStop(v, 0, alt, duration=s.duration, flags=tc.STOP_BUS_STOP)
                    except traci.TraCIException:
                        continue                       # e.g. too close to brake for it: try the next option
                    self.switched[v] = (bs, alt)
                    self.watch[v] = alt
                    break

        # through cars stuck in the left lane move right when the right lane is clearly quieter
        if self.halted(2) <= QUIETER * (self.halted(1) + 1):
            for e in GATE_EDGES:
                for v in traci.lane.getLastStepVehicleIDs(f"{e}_1"):
                    if v in self.lane_changed or v in self.watch or traci.vehicle.getSpeed(v) >= HALT_SPEED:
                        continue
                    if traci.vehicle.isStopped(v):
                        continue
                    traci.vehicle.changeLane(v, 2, 5.0)
                    self.lane_changed.add(v)
                    self.lane_changes += 1

    def stats(self):
        moves = {}
        for a, b in self.switched.values():
            moves[f"{a}->{b}"] = moves.get(f"{a}->{b}", 0) + 1
        return {"dropoff_switches": moves, "lane_changes": self.lane_changes}
