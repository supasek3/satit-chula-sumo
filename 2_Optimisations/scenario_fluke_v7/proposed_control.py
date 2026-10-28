"""Fluke's proposed method (review 22 Oct 2026), moved onto baseline_v7 on 28 Oct 2026.

"Organized drop-off + demand-responsive pedestrian service" at Gate X1:
  - organized: all 8 modelled positions of the existing 60 m Gate X1 zone are always open and a halted parent
    drops off at any free position (100% compliance, ideal case). Same zone, same 35 s dwell, no extra road space.
  - adaptive X1 signal: serve pedestrians in a natural vehicle gap after >= 8 s vehicle green, or switch once the
    oldest pedestrian call is 25 s old; pedestrian admission >= 4 s, <= 10 s while cars wait; clearance as baseline.
Gate X2 keeps the baseline guard. Simulation design values, not approved field timings.

Choose with the environment variable FLUKE_METHOD (default "balanced" = Fluke's selected package):
    balanced   organized + adaptive X1 with 25 s trigger   (selected)
    combined   organized + adaptive X1 with 20 s trigger
    organized  organized drop-off only
    adaptive   adaptive X1 only (20 s trigger)
    baseline   nothing changed (= baseline_v7)
"""
import os
import guard_control as base
import dynamic_dropoff as zone

METHOD = os.environ.get("FLUKE_METHOD", "balanced")
TRIGGER = 25 if METHOD == "balanced" else 20
MIN_VEH_GREEN, MIN_WALK, MAX_WALK_CARS_WAITING = 8, 4, 10


class ProposedGuard(base.Guard):
    def step(self, now, cars_near, cars_inside, waiting, on):
        elapsed = now - self.since
        if self.phase == "VEH":
            if not waiting:
                self.conflict_since = None
                return
            if self.conflict_since is None:
                self.conflict_since = now
            if (elapsed >= MIN_VEH_GREEN and not cars_near) or now - self.conflict_since >= TRIGGER:
                self.set("YELLOW" if cars_near else "VCLEAR", now)
        elif self.phase == "YELLOW":
            if elapsed >= base.YELLOW:
                self.set("VCLEAR", now)
        elif self.phase == "VCLEAR":
            if not cars_inside:
                self.set("PED", now)
        elif self.phase == "PED":
            if elapsed >= MIN_WALK and (not waiting or (cars_near and elapsed >= MAX_WALK_CARS_WAITING)):
                self.set("CLEAR", now)
        elif self.phase == "CLEAR":
            if elapsed >= base.ALL_RED and not on:
                self.set("VEH", now)


def install():
    assert METHOD in ("balanced", "combined", "organized", "adaptive", "baseline"), METHOD
    if METHOD in ("balanced", "combined", "adaptive"):
        original = base.Guard

        def factory(name, **kwargs):
            return (ProposedGuard if name == "X1" else original)(name, **kwargs)
        base.Guard = factory
    if METHOD in ("balanced", "combined", "organized"):
        zone.MIN_SPOTS = zone.MAX_SPOTS
        zone.P_BACK = zone.P_BACK_LONG = 1.0
    return METHOD
