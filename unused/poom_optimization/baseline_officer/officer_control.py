"""Traffic officer at the gate crossing X1 (variant "baseline_officer"); less efficient than a signal.

User's rules (2026-10-18):
  - No car coming -> pedestrians cross freely; no pedestrian waiting -> cars keep going.
  - Cars keep going while the FRONT car of the LEFT lane (the gate drop-off lane) is a car that has already dropped
    off, will drop off after the crossing, or is going straight through / south. As soon as the front car is one that
    still has to drop off IN FRONT of the crossing (next stop bs_1 or bs_5), the officer stops traffic until that car
    has finished its drop-off AND the pedestrians waiting at the edge have crossed.
  - Off-peak (left-lane queue <= 5 cars): pedestrians have priority (officer stops cars whenever someone waits).
    Peak (left-lane queue > 5): pedestrians only cross during the drop-off stops.
  - No pedestrian waits more than 120 s: when the longest-waiting pedestrian gets close (allowing for the reaction
    and stop clearance), the officer stops traffic for them even at peak.
  - Only the left lane is looked at; when the officer stops traffic both lanes stop (pedestrians cross both).
  - Human behaviour: 3 s reaction before any switch, at least 5 s per go / stop, no yellow (hand signals).
    Safety as in the other controllers: cars stop only once nobody is left in the junction, and go again only once
    the crosswalk is empty.
States: GO (GGr) -> VCLEAR (rrr, until no car in the junction) -> STOP (rrG, pedestrians cross) -> PCLEAR (rrr,
until the crosswalk is empty) -> GO.
"""
import traci

REACTION = 3.0        # s, officer notices and signals
MIN_GO = 5.0          # s
MIN_STOP = 5.0        # s
VCLEAR_MIN = 3.0      # s, cars need time to obey the stop signal (no yellow with an officer)
PCLEAR_MIN = 2.0      # s
MAX_PED_WAIT = 120.0  # s, user rule: no pedestrian waits longer (officer stops traffic for them at peak too)
MAX_WAIT_MARGIN = 6.0 # s, extra lead time for a stop clearance that has to wait for the junction to empty
PEAK_QUEUE = 5        # left-lane queue (halted cars, drop-off dwellers excluded) above this = peak
GATE_STOPS = ("bs_1",)                # left-lane gate drop-off only ("prioritize left lane only")
GIVE_UP = 60.0        # s, officer releases traffic if the awaited car has not started its drop-off by then
LEFT_GATE_LANE = "31993796#4_1"                                  # left lane in front of X1 (gate drop-off zone)
LEFT_QUEUE_LANES = ("31993796#4_1", "31993796#3_1", "31993796#3_M_1", "31993796#3_E_1")

STATE = {"GO": "GGr", "VCLEAR": "rrr", "STOP": "rrG", "PCLEAR": "rrr"}


class Officer:
    def __init__(self, name, tls, crossing, wait_edges):
        self.name, self.tls, self.crossing, self.wait_edges = name, tls, crossing, wait_edges
        self.phase, self.since = "GO", 0.0
        self.want_since = None          # when the reason to switch first appeared (reaction timer)
        self.hold_car = None            # drop-off car the officer is waiting for
        self.gave_up = 0
        self.switches = 0
        self.dropoff_stops = 0
        self.ped_priority_stops = 0
        self.max_wait_stops = 0

    def set(self, phase, now):
        phase = "GO" if phase == "VEH" else phase          # guard_control starts every crossing with "VEH"
        self.phase, self.since, self.want_since = phase, now, None
        traci.trafficlight.setRedYellowGreenState(self.tls, STATE[phase])
        self.switches += 1

    def react(self, want, now):
        """True once the reason to switch has lasted the officer's reaction time."""
        if not want:
            self.want_since = None
            return False
        if self.want_since is None:
            self.want_since = now
        return now - self.want_since >= REACTION

    @staticmethod
    def next_gate_stop(v):
        stops = traci.vehicle.getStops(v, 1)
        return bool(stops) and stops[0].stoppingPlaceID in GATE_STOPS

    def front_dropoff_car(self):
        """Front car of the left lane in front of X1, if it still has to drop off before the crossing."""
        cars = traci.lane.getLastStepVehicleIDs(LEFT_GATE_LANE)
        if not cars:
            return None
        front = max(cars, key=traci.vehicle.getLanePosition)        # closest to the stop line
        return front if self.next_gate_stop(front) else None

    def longest_ped_wait(self):
        w = 0.0
        for p in traci.person.getIDList():
            if traci.person.getRoadID(p) in self.wait_edges and traci.person.getNextEdge(p) == self.crossing:
                w = max(w, traci.person.getWaitingTime(p))
        return w

    @staticmethod
    def left_queue():
        n = 0
        for lane in LEFT_QUEUE_LANES:
            for v in traci.lane.getLastStepVehicleIDs(lane):
                if traci.vehicle.getSpeed(v) < 0.5 and not traci.vehicle.isStopped(v):
                    n += 1
        return n

    def step(self, now, cars_near, cars_inside, peds_waiting, peds_on_crossing):
        t = now - self.since
        if self.phase == "GO":
            maxwait = peds_waiting and \
                self.longest_ped_wait() >= MAX_PED_WAIT - REACTION - VCLEAR_MIN - MAX_WAIT_MARGIN
            if t < MIN_GO and cars_near and not maxwait:
                return
            front = self.front_dropoff_car()
            peak = self.left_queue() > PEAK_QUEUE
            reason = None
            if front:
                reason = "dropoff"
            elif peds_waiting and (not cars_near or not peak):
                reason = "peds"
            elif maxwait:
                reason = "maxwait"
            if self.react(reason is not None, now):
                self.hold_car = front
                if reason == "dropoff":
                    self.dropoff_stops += 1
                elif reason == "maxwait":
                    self.max_wait_stops += 1
                else:
                    self.ped_priority_stops += 1
                self.set("VCLEAR", now)
        elif self.phase == "VCLEAR":
            if t >= VCLEAR_MIN and not cars_inside:
                self.set("STOP", now)
        elif self.phase == "STOP":
            if t < MIN_STOP:
                return
            car_done = self.hold_car is None or self.hold_car not in traci.vehicle.getIDList() \
                or not self.next_gate_stop(self.hold_car)
            if not car_done and not traci.vehicle.isStopped(self.hold_car) and t >= GIVE_UP:
                car_done = True                                   # awaited car is stuck: officer gives up
                self.gave_up += 1
            if not cars_near:                                     # no car waiting: pedestrians keep crossing
                done = not peds_waiting and not peds_on_crossing and car_done
            else:
                done = car_done and not peds_waiting
            if self.react(done, now):
                self.hold_car = None
                self.set("PCLEAR", now)
        elif self.phase == "PCLEAR":
            if t >= PCLEAR_MIN and not peds_on_crossing:
                self.set("GO", now)

    def stats(self):
        return {"X1_switches": self.switches, "officer_dropoff_stops": self.dropoff_stops,
                "officer_ped_priority_stops": self.ped_priority_stops, "officer_max_wait_stops": self.max_wait_stops, "officer_gave_up": self.gave_up}
