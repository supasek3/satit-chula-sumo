"""SCENARIO dynamic_dropoff: a longer, dynamic gate drop-off zone (left lane) + "the closer to the gate, the more
likely a parent drops off here" (user rules, 2026-10-19). Called every step from guard_control.run.

Zone (left lane, school side): ONE continuous 60 m stretch = 8 spots of 7.5 m (was 4), measured back from the X1
stop line (v5; v1-v4 had 6 spots with a gap at the P1 driveway):
    0 - 30 m      bs_1   31993796#4_1 4.47-34.47   the original gate zone (SUMO bus stop / lane stops)
    30 - 48.9 m   gap    31993796#4_1 0-4.47 + the P1 junction (:10072794956_0_0, 14.46 m). SUMO cannot stop cars
                         inside a junction, so a parent dropping off here is HELD still with setSpeed(0) for its
                         drop-off time; the stretch is painted like a drop-off zone (poly in dropoff.add.xml).
    48.9 - 60 m   bs_1x  31993796#3_1 20.70-31.77  east of the P1 driveway mouth (lane stops)
    No road, junction or crossing was changed.
Dynamic length: queue = gate drop-off cars (dropping off now + halted while waiting to drop off at the gate),
    7.5 m each. Queue <= 2/3 of the zone (<= 5 cars, 37.5 m) -> spots 1-5; then one more spot per car, all 8 at
    8 or more cars.
Where a parent stops: a gate drop-off car that is halted on an open spot drops off right there with probability
    p = 1 on the front spot, falling linearly to p_back at the back of the queue (the rear bumper of the last
    drop-off car in the queue); otherwise it waits to move closer and draws again at the next spot it halts on.
    p_back = 15%, rising evenly to 80% while the drop-off queue grows from 60 m (the whole zone) to 120 m (v4/v5).
    A car that is not held up drives to the front of the free space (SUMO bus stop bs_1) and stops there.
Each car keeps its sampled drop-off time.
"""
import traci
import opt

SPOT = 7.5               # m per car (5 m car + 2.5 m gap)
CAR = 5.0                # m
MIN_SPOTS, MAX_SPOTS = opt.MIN_SPOTS, 8     # 2/3 of 60 m ~ 5 spots; whole zone 8 spots (v5); scenario opt: OPT_MIN_SPOTS
ZONE_LEN = MAX_SPOTS * SPOT                 # 60 m
P_BACK = opt.P_BACK      # scenario opt: OPT_P_BACK (v6 0.15). Drop-off chance at the back of the queue (user: 0.40 in v1/v2, 0.15 from v3)
# v4 (user): once the drop-off queue is longer than the whole zone, parents are keener to stop where they are:
# the back-of-queue chance ramps evenly from P_BACK (queue = zone) to P_BACK_LONG (queue = 2 x zone) and stays there.
P_BACK_LONG = max(0.80, P_BACK)
RAMP_FROM, RAMP_TO = ZONE_LEN, 2 * ZONE_LEN  # 60 m -> 120 m of drop-off queue
HALT_SPEED = 0.5         # m/s
GATE_STOP = "bs_1"
X1_EDGE, X1_POS = "31993796#4", 34.47           # stop line of the gate crossing (left lane end)
ZONE_LANES = ("31993796#4_1", ":10072794956_0_0", "31993796#3_1")
GATE_LANE, EAST_LANE = "31993796#4_1", "31993796#3_1"   # lane stops possible here (outside the junction)
WAYPOINT_SPEED = 13.89   # m/s, the car's max speed: passing its old bs_1 stop costs no slow-down


class GateZone:
    def __init__(self, rng):
        self.rng = rng
        self.bound = set()       # cars whose next stop is the gate drop-off (bs_1), not yet stopped
        self.early = {}          # car -> [spot, has stood still], cars that stopped where they were halted
        self.held = {}           # car -> release time, cars dropping off in the junction stretch (held still)
        self.done = set()        # cars that dropped off in the junction stretch (bs_1 left as a waypoint)
        self.tried = {}          # car -> spots already drawn on
        self.flex = set()        # scenario opt (OPT_BS0_FLEX): gate parents now heading for bs_0 who still take a gate
                                 # spot they are halted on (same draw as everyone else)
        self.dwellers, self.waiting = set(), set()
        self.n_open, self.tail = MIN_SPOTS, 0.0
        self.open_steps = {n: 0 for n in range(MIN_SPOTS, MAX_SPOTS + 1)}
        self.early_by_spot = {s: 0 for s in range(1, MAX_SPOTS + 1)}
        self.draws = self.hits = self.gap_drops = 0
        self.p_back = P_BACK
        self.p_back_sum = self.long_steps = 0

    # ---- helpers ------------------------------------------------------------------------------
    @staticmethod
    def next_stop(v):
        stops = traci.vehicle.getStops(v, 1)
        return stops[0] if stops else None

    @staticmethod
    def front_dist(v):
        """Distance from the car's front bumper to the X1 stop line (None once past X1)."""
        d = traci.vehicle.getDrivingDistance(v, X1_EDGE, X1_POS)
        return None if d < -1.0 else max(0.0, d)

    def rear_dist(self, v):
        d = self.front_dist(v)
        return None if d is None else d + traci.vehicle.getLength(v)

    def spot_of(self, v):
        """Spot (1 = next to the crossing) the halted car stands on, or None if it is not inside the zone."""
        if traci.vehicle.getLaneID(v) not in ZONE_LANES:
            return None
        d = self.front_dist(v)
        if d is None or d + CAR > ZONE_LEN + SPOT / 3:
            return None
        return min(MAX_SPOTS, int(d / SPOT) + 1)

    def add(self, v):
        self.bound.add(v)

    def add_flex(self, v):
        """scenario opt: v (a gate parent) now heads for bs_0 past the crossing but may still drop off in the zone."""
        self.flex.add(v)
        self.bound.add(v)

    def full_for(self, v):
        """Used by driver_logic: is the gate zone full for car v? If v joins, the queue opens the zone up to
        min(queue, MAX_SPOTS) spots, so it is full once MAX_SPOTS other drop-off cars are already there or waiting."""
        others = len((self.dwellers | self.waiting) - {v})
        return others >= max(MIN_SPOTS, min(MAX_SPOTS, others + 1))

    def p_here(self, spot, rear):
        if spot == 1 or self.tail <= SPOT:
            return 1.0
        x = min(1.0, max(0.0, (rear - SPOT) / (self.tail - SPOT)))
        return 1.0 - (1.0 - self.p_back) * x

    def start_dropoff(self, v, now):
        """Stop the halted car where it stands for its drop-off time. False if SUMO refused."""
        lane, f, dur = traci.vehicle.getLaneID(v), traci.vehicle.getLanePosition(v), self.next_stop(v).duration
        try:
            if lane == EAST_LANE or (lane == GATE_LANE and f >= CAR):
                traci.vehicle.replaceStop(v, 0, lane.rsplit("_", 1)[0], pos=min(f + 0.5, traci.lane.getLength(lane)),
                                          laneIndex=int(lane.rsplit("_", 1)[1]), duration=dur,
                                          startPos=max(0.0, f - 1.0))
                return "stop"
            traci.vehicle.setSpeed(v, 0.0)       # junction stretch: hold still; bs_1 stays as its next stop
            self.held[v] = now + dur
            self.gap_drops += 1
            return "held"
        except traci.TraCIException:
            return None

    # ---- per step -----------------------------------------------------------------------------
    def step(self, now):
        for v in traci.simulation.getDepartedIDList():
            s = self.next_stop(v)
            if s and s.stoppingPlaceID == GATE_STOP:
                self.bound.add(v)
        for v in traci.simulation.getArrivedIDList():
            self.bound.discard(v)
            self.early.pop(v, None)
            self.held.pop(v, None)
            self.done.discard(v)
            self.tried.pop(v, None)
            self.flex.discard(v)

        # parents held in the junction stretch whose drop-off time is over drive on. Their pending bs_1 stop becomes a
        # waypoint (passed without stopping); removing it via TraCI (replaceStop with "") crashes SUMO 1.28 later.
        for v, until in list(self.held.items()):
            if now >= until:
                try:
                    traci.vehicle.setStopParameter(v, 0, "speed", str(WAYPOINT_SPEED))
                except traci.TraCIException:
                    traci.vehicle.setStopParameter(v, 0, "duration", "0")
                traci.vehicle.setSpeed(v, -1)
                del self.held[v]
                self.done.add(v)

        # who is in the drop-off queue now
        self.dwellers = set(traci.busstop.getVehicleIDs(GATE_STOP)) | set(self.held)
        for v, rec in list(self.early.items()):
            if traci.vehicle.isStopped(v):
                rec[1] = True
                self.dwellers.add(v)
            elif rec[1]:
                del self.early[v]                # drop-off finished, driving on
            else:
                self.dwellers.add(v)             # stop just assigned, about to stand still
        self.waiting, rear = set(), {}
        for v in list(self.bound):
            s = self.next_stop(v)
            target = s.stoppingPlaceID if s else None
            if not s or (target != GATE_STOP and not (target == "bs_0" and v in self.flex)) \
                    or traci.vehicle.isStopped(v) or v in self.held:
                self.bound.discard(v)            # switched zone, stopped at bs_1, early lane stop or held
                continue
            r = self.rear_dist(v)
            if r is not None and traci.vehicle.getSpeed(v) < HALT_SPEED:
                self.waiting.add(v)
                rear[v] = r
        queue = self.dwellers | self.waiting
        self.n_open = max(MIN_SPOTS, min(MAX_SPOTS, len(queue)))
        ramp = min(1.0, max(0.0, (len(queue) * SPOT - RAMP_FROM) / (RAMP_TO - RAMP_FROM)))
        self.p_back = P_BACK + (P_BACK_LONG - P_BACK) * ramp
        rears = list(rear.values()) + [r for r in map(self.rear_dist, self.dwellers) if r is not None]
        self.tail = max(rears, default=0.0)
        if now <= 6000:
            self.open_steps[self.n_open] += 1
            self.p_back_sum += self.p_back
            self.long_steps += ramp > 0

        # halted drop-off cars on an open spot: drop off here, or wait to move closer?
        for v in self.waiting:
            spot = self.spot_of(v)
            if spot is None or spot > self.n_open or spot in self.tried.setdefault(v, set()):
                continue
            self.tried[v].add(spot)
            self.draws += 1
            if self.rng.random() >= self.p_here(spot, rear[v]):
                continue                         # waits to get closer to the gate
            how = self.start_dropoff(v, now)
            if how is None:
                continue
            self.hits += 1
            if how == "stop":
                self.early[v] = [spot, False]
            self.early_by_spot[spot] += 1
            self.bound.discard(v)

    def stats(self):
        total = sum(self.open_steps.values()) or 1
        out = {f"zone_open{n}_share": self.open_steps[n] / total for n in self.open_steps}
        out.update({f"zone_early_spot{s}": c for s, c in self.early_by_spot.items()})
        out.update(zone_draws=self.draws, zone_early_total=self.hits, zone_gap_dropoffs=self.gap_drops,
                   zone_p_back_mean=self.p_back_sum / total, zone_queue_longer_than_zone_share=self.long_steps / total)
        return out
