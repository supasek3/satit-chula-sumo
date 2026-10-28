"""Webster-based adaptive signal for the gate crossing X1 (scenario "webster_soi11").

Follows the team's "Adaptive traffic signal control logic" (AnyLogic PDF) with the fixes agreed on 2026-10-18:
  1. Green split uses the UNCAPPED flow ratios (Y is capped at 0.9 only for the cycle length), so the greens never
     add up to more than the available green; windows with y_v + y_p >= 0.9 are logged as oversaturated.
  2. Both lanes use a stop-line saturation flow of 1500 veh/h (drop-off friction is modelled by the simulation itself).
  3. Flows come from what the controller measures at X1 in the previous 15 minutes (no hard-coded inputs).
  4. Queue override triggers on 25 halted cars in the left lane between X1 and the east entry (cars parked at a
     drop-off are not counted).
  Plus: the max-out timer starts when the pedestrian call is registered; pedestrians keep green while no car is
  waiting; the minimum pedestrian green uses the real crossing length (6.4 m) and a child walking speed of 1.0 m/s;
  cars get green only after the crosswalk is empty; when no car is near, the min vehicle green and the yellow are
  skipped (pedestrians are served at once, as the user's "no car -> pedestrians cross" rule requires).

Phases: VEH (GGr) -> YELLOW (yyr, 3 s) -> VCLEAR (rrr, >= 2 s, until no car in the junction) -> PED (rrG)
        -> PCLEAR (rrr, >= 3 s, until the crosswalk is empty) -> VEH.   Lost time L = 3 + 2 + 3 = 8 s.
"""
import math
import traci

S_LEFT = S_RIGHT = 1500.0      # veh/h/lane at the stop line (fix 2)
S_PED = 6000.0                 # peds/h (PDF)
L_LOST = 8.0                   # s per cycle (PDF): yellow 3 + all-red 2 + pedestrian clearance 3
YELLOW, VCLEAR_MIN, PCLEAR_MIN = 3.0, 2.0, 3.0
C_MIN, C_MAX = 30.0, 120.0     # s (PDF)
G_V_MIN = 10.0                 # s (PDF)
T_STARTUP, V_WALK = 4.0, 1.0   # s, m/s (child speed; PDF had 1.2)
GAP_OUT = 3.0                  # s (PDF)
WINDOW = 900.0                 # s, re-plan every 15 min (PDF)
Y_CAP = 0.90
N_QUEUE_OVERRIDE = 25          # halted cars in the left lane (PDF)
OVERRIDE_EXTRA = 15.0          # s (PDF)
APPROACH_M = 30.0              # a car this close to the stop line (or halted there) is a vehicle call

STATE = {"VEH": "GGr", "YELLOW": "yyr", "VCLEAR": "rrr", "PED": "rrG", "PCLEAR": "rrr"}


class Webster:
    def __init__(self, name, tls, crossing, wait_edges, crossing_length,
                 links=(":10784747877_0_0", ":10784747877_0_1"),
                 queue_lanes=("31993796#4_1", "31993796#3_1", "31993796#3_M_1", "31993796#3_E_1")):
        self.name, self.tls, self.crossing, self.wait_edges = name, tls, crossing, wait_edges
        self.links, self.queue_lanes = links, queue_lanes
        self.g_p_min = math.ceil(T_STARTUP + crossing_length / V_WALK)
        self.c_min_safe = L_LOST + G_V_MIN + self.g_p_min
        self.phase, self.since, self.call_since = "VEH", 0.0, None
        self.seen_link = [set(), set()]
        self.seen_ped = set()
        self.count = [0, 0, 0]          # left, right, peds in the current window
        self.last_pass = -1e9
        self.window_start = 0.0
        self.plans = []                 # (time, q_left, q_right, q_ped, Y_raw, C, g_v, g_p, case)
        self.overrides = 0
        self.switches = 0
        self.plan(0.0, 0, 0, 0)

    # ---- macro: Webster plan from the last window's counts --------------------------------------
    def plan(self, now, n_left, n_right, n_ped):
        f = 3600.0 / WINDOW
        q_l, q_r, q_p = n_left * f, n_right * f, n_ped * f
        y_v = max(q_l / S_LEFT, q_r / S_RIGHT)
        y_p = q_p / S_PED
        y_raw = y_v + y_p
        Y = min(Y_CAP, y_raw)
        c_o = (1.5 * L_LOST + 5.0) / (1.0 - Y)
        C = max(max(C_MIN, self.c_min_safe), min(C_MAX, c_o))
        G = C - L_LOST
        if y_raw <= 0:
            g_v, g_p, case = G - self.g_p_min, self.g_p_min, "empty"
        else:
            gv_raw, gp_raw = G * y_v / y_raw, G * y_p / y_raw          # fix 1: uncapped ratios
            if gp_raw < self.g_p_min:
                g_v, g_p, case = G - self.g_p_min, self.g_p_min, "A"
            elif gv_raw < G_V_MIN:
                g_v, g_p, case = G_V_MIN, G - G_V_MIN, "B"
            else:
                g_v, g_p, case = round(gv_raw), round(gp_raw), "C"
        self.g_v, self.g_p, self.C = g_v, g_p, C
        self.plans.append((now, q_l, q_r, q_p, round(y_raw, 3), round(C, 1), g_v, g_p, case))

    # ---- helpers ----------------------------------------------------------------------------------
    def set(self, phase, now):
        self.phase, self.since = phase, now
        if phase != "VEH" and phase != "PED":
            self.call_since = None
        traci.trafficlight.setRedYellowGreenState(self.tls, STATE[phase])
        self.switches += 1

    def measure(self, now):
        for i, lane in enumerate(self.links):
            ids = set(traci.lane.getLastStepVehicleIDs(lane))
            new = ids - self.seen_link[i]
            if new:
                self.count[i] += len(new)
                self.last_pass = now
            self.seen_link[i] = ids
        on = set(traci.edge.getLastStepPersonIDs(self.crossing))
        self.count[2] += len(on - self.seen_ped)
        self.seen_ped = on
        if now - self.window_start >= WINDOW:
            self.plan(now, *self.count)
            self.count = [0, 0, 0]
            self.window_start = now

    def left_queue(self):
        n = 0
        for lane in self.queue_lanes:
            for v in traci.lane.getLastStepVehicleIDs(lane):
                if traci.vehicle.getSpeed(v) < 0.5 and not traci.vehicle.isStopped(v):
                    n += 1
        return n

    # ---- micro: actuation, same signature as Guard.step -----------------------------------------
    def step(self, now, cars_near, cars_inside, peds_waiting, peds_on_crossing):
        self.measure(now)
        t = now - self.since
        if self.phase == "VEH":
            if not peds_waiting:
                self.call_since = None                                  # rest on vehicle green
                return
            if self.call_since is None:
                self.call_since = now                                   # max-out timer starts at the call
            g_v_limit = self.g_v
            if self.left_queue() >= N_QUEUE_OVERRIDE:                   # fix 4: spillback override
                g_v_limit = min(self.g_v + OVERRIDE_EXTRA, C_MAX - L_LOST - self.g_p_min)
                self.overrides += 1
            gap = now - self.last_pass
            if not cars_near:                                           # no car coming: no min green, no yellow
                self.set("VCLEAR", now)
            elif t >= G_V_MIN and (gap > GAP_OUT or now - self.call_since >= g_v_limit):
                self.set("YELLOW", now)
        elif self.phase == "YELLOW":
            if t >= YELLOW:
                self.set("VCLEAR", now)
        elif self.phase == "VCLEAR":
            if t >= VCLEAR_MIN and not cars_inside:
                self.set("PED", now)
        elif self.phase == "PED":
            if t < self.g_p_min:
                return
            if not cars_near:                                           # no car waiting: pedestrians keep green
                self.call_since = None
                if not peds_waiting and not peds_on_crossing:
                    self.set("PCLEAR", now)                             # nobody left: back to vehicle rest
                return
            if self.call_since is None:
                self.call_since = now
            g_p_limit = self.g_p_min if self.left_queue() >= N_QUEUE_OVERRIDE else self.g_p
            if not peds_waiting or now - self.call_since >= g_p_limit or t >= self.g_p:
                self.set("PCLEAR", now)
        elif self.phase == "PCLEAR":
            if t >= PCLEAR_MIN and not peds_on_crossing:
                self.set("VEH", now)

    def stats(self):
        cyc = [p[5] for p in self.plans[1:]]
        return {"webster_plans": self.plans, "webster_mean_cycle_s": sum(cyc) / len(cyc) if cyc else self.C,
                "webster_oversat_windows": sum(1 for p in self.plans[1:] if p[4] >= Y_CAP),
                "webster_override_steps": self.overrides, "X1_switches": self.switches}
