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
   SCENARIO dynamic_dropoff: the gate left zone (bs_1) is the dynamic 4-6 spot zone of dynamic_dropoff.py; it counts
   as full only when the queue could not open another spot for this car (GateZone.full_for).
   Only 6% of gate drop-off parents (P_ACCEPT_AFTER_X1) consider bs_0 (past the crosswalk); the rest only use the
   area before the crossing (bs_1 / bs_5) and wait in line.
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
# SCENARIO dynamic_dropoff, user decision 2026-10-19: only this share of the parents heading for the gate drop-off
# see the spot past the crosswalk (bs_0) as a drop-off area; everyone else only counts the area before the crossing
# (gate left / gate right) and waits in line when it is full. Drawn once per car when it departs.
P_ACCEPT_AFTER_X1 = 0.06
GATE_STOPS = ("bs_1", "bs_5")
# SCENARIO v3, user decision 2026-10-19: parents do not cross to the right lane just to drop off closer; only this
# share of left-lane gate parents (own draw per car) may switch bs_1 -> bs_5. A parent in the left lane heading for
# the gate drop-off (bs_1 or a spot it chose in the zone) does not change lanes at all: it waits behind a car that is
# dropping off instead of pulling out to the right (SUMO would otherwise overtake and then get stuck merging back).
# Everyone else (after drop-off, other zones, no student) uses SUMO's normal lane changing, and only cars with no
# drop-off ahead use the jam rule below.
P_SWITCH_RIGHT = 0.06
LC_KEEP_LANE = 0b011000000000    # no own lane changes
LC_DEFAULT = 0b011001010101      # SUMO default (1621)
GATE_LEFT_LANES = ("31993796#3_E_1", "31993796#3_M_1", "31993796#3_1", "31993796#4_1")


class Drivers:
    def __init__(self, zone=None, rng=None):
        self.zone = zone         # dynamic_dropoff.GateZone (scenario) or None (fixed bs_1 capacity)
        self.rng = rng           # scenario: draws who accepts bs_0 (None = everybody, as in the baseline)
        self.after_ok = set()    # gate drop-off cars that would use bs_0
        self.right_ok = set()    # left-lane gate cars that would cross to the right-lane gate spot bs_5
        self.with_child = set()  # cars still carrying a child
        self.lane_kept = set()   # of those: gate parents in the left lane, own lane changes off
        self.n_gate = self.n_accept = self.n_right = 0
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

    def full(self, bs, me):
        if bs == "bs_1" and self.zone:
            return self.zone.full_for(me)
        return self.demand(bs, me) >= CAPACITY[bs]

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
                if stops[0].stoppingPlaceID in GATE_STOPS:
                    self.n_gate += 1
                    if self.rng is None or self.rng.random() < P_ACCEPT_AFTER_X1:
                        self.after_ok.add(v)
                        self.n_accept += 1
                if stops[0].stoppingPlaceID == "bs_1" and (self.rng is None or self.rng.random() < P_SWITCH_RIGHT):
                    self.right_ok.add(v)
                    self.n_right += 1
            if stops and self.rng is not None:
                self.with_child.add(v)
        for v in traci.simulation.getArrivedIDList():
            self.watch.pop(v, None)
            self.after_ok.discard(v)
            self.right_ok.discard(v)
            self.with_child.discard(v)
            self.lane_kept.discard(v)
        for v in list(self.with_child):
            stops = traci.vehicle.getStops(v, 1)
            if not stops and not traci.vehicle.isStopped(v):
                self.with_child.discard(v)             # dropped off
            s = stops[0] if stops else None
            # v7 (Fluke fix 2): retain the left-lane commitment through internal junction links.
            # Releasing it at P1 let SUMO overtake into the right lane before this
            # controller ran again, stranding a car with a left-lane drop-off.
            on_gate_lane = traci.vehicle.getLaneID(v) in GATE_LEFT_LANES or \
                (v in self.lane_kept and traci.vehicle.getRoadID(v).startswith(":"))
            keep = s is not None and on_gate_lane and \
                (s.stoppingPlaceID == "bs_1" or (s.stoppingPlaceID == "" and s.lane in GATE_LEFT_LANES))
            if keep != (v in self.lane_kept):
                traci.vehicle.setLaneChangeMode(v, LC_KEEP_LANE if keep else LC_DEFAULT)
                (self.lane_kept.add if keep else self.lane_kept.discard)(v)

        for v, bs in list(self.watch.items()):
            stops = traci.vehicle.getStops(v, 1)
            if not stops or stops[0].stoppingPlaceID != bs or traci.vehicle.isStopped(v):
                del self.watch[v]                      # reached its stop (or stop done)
                continue
            if v in self.switched or (self.zone and (v in self.zone.held or v in self.zone.done)):
                continue                               # dropping off / dropped off in the P1 junction stretch
            s = stops[0]
            dist = traci.vehicle.getDrivingDistance(v, s.lane.rsplit("_", 1)[0], s.startPos)
            if dist < 0 or dist > DECIDE_M:
                continue
            if not self.full(bs, v):
                continue                               # free spot: keep the plan
            for alt, cond in ALTERNATIVES[bs]:
                if cond and not ALLOW_OTHER_LANE_DROPOFF:
                    continue
                if alt == "bs_0" and v not in self.after_ok:
                    continue                           # does not see past the crossing as a drop-off area
                if bs == "bs_1" and alt == "bs_5" and v not in self.right_ok:
                    continue                           # does not cross to the right lane just to drop off
                if not self.full(alt, v) and self.lane_ok(cond):
                    try:
                        traci.vehicle.replaceStop(v, 0, alt, duration=s.duration, flags=tc.STOP_BUS_STOP)
                    except traci.TraCIException:
                        continue                       # e.g. too close to brake for it: try the next option
                    self.switched[v] = (bs, alt)
                    self.watch[v] = alt
                    if alt == "bs_1" and self.zone:
                        self.zone.add(v)
                    break

        # through cars stuck in the left lane move right when the right lane is clearly quieter
        # (scenario: only cars with no drop-off ahead = purple / yellow)
        if self.halted(2) <= QUIETER * (self.halted(1) + 1):
            for e in GATE_EDGES:
                for v in traci.lane.getLastStepVehicleIDs(f"{e}_1"):
                    if v in self.lane_changed or v in self.watch or traci.vehicle.getSpeed(v) >= HALT_SPEED:
                        continue
                    if traci.vehicle.isStopped(v) or traci.vehicle.getStops(v, 1):
                        continue
                    traci.vehicle.changeLane(v, 2, 5.0)
                    self.lane_changed.add(v)
                    self.lane_changes += 1

    def stats(self):
        moves = {}
        for a, b in self.switched.values():
            moves[f"{a}->{b}"] = moves.get(f"{a}->{b}", 0) + 1
        return {"dropoff_switches": moves, "lane_changes": self.lane_changes,
                "zone_gate_cars": self.n_gate, "zone_gate_cars_accept_bs0": self.n_accept,
                "zone_gate_cars_accept_bs5": self.n_right}
