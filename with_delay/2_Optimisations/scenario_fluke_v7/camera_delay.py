"""Camera delay at Gate X1: the signal controller sees the crossing as the camera saw it a moment ago.

Choose with the environment variable CAMERA_DELAY:
    none      no delay (the controller sees the crossing in real time)            default
    ethernet  every camera on a LAN cable: camera-to-screen delay 0.3-0.5 s
    wifi      every camera on Wi-Fi:       camera-to-screen delay 0.6-1.5 s
Delays are the team's camera-to-screen measurements (6 Nov 2026). DETECT_DELAY (s, default 0) adds the object-detection
time on the computer, which those numbers do not include; set it once it is measured.

How it works: every simulation step (0.1 s) the real view of X1 is stored as a "frame". The controller then gets the
frame closest to d seconds old (never newer than d minus half a step). d is drawn uniformly from the range above and held for HOLD_S (1 s)
before the next draw, so the lag drifts within the measured range as a real stream does. Frames never go backwards in
time (a video stream arrives in order): when the lag grows, the picture freezes until it is d old; when it shrinks,
the picture jumps forward. Only X1 is delayed: it is the camera-controlled signal. X2 keeps the human guard,
who sees in real time.

What is delayed: all four inputs of the X1 controller - cars approaching (30 m), cars inside the crossing, students
waiting, students on the crossing (and, for Poom's smart control, the count and longest wait of waiting students).

Safety check: x1_walk_with_car_inside_s counts the seconds in which X1 shows the walk signal while a car is really
inside the crossing area, the risk a late "crossing clear" picture creates.
"""
import copy
import os
import random
from collections import deque

MODE = os.environ.get("CAMERA_DELAY", "none")
RANGES = {"none": None, "ethernet": (0.3, 0.5), "wifi": (0.6, 1.5)}
DETECT = float(os.environ.get("DETECT_DELAY", "0"))
HOLD_S = 1.0     # s, how long one lag value lasts before the next is drawn
assert MODE in RANGES, f"CAMERA_DELAY must be one of {list(RANGES)}, got {MODE!r}"


class CameraDelay:
    def __init__(self, keys, seed):
        """keys: the ids that identify X1 in the controller's input dicts (its tls id and its crossing id)."""
        self.keys = set(keys)
        self.rng = random.Random(seed * 6151 + 29)        # own random stream: nothing else in the run changes
        self.frames = deque()                              # (time, {key: value}) oldest first
        self.shown = float("-inf")
        self.delays = []
        self.unsafe = 0.0
        self.last = None
        self.d, self.next_draw = 0.0, float("-inf")

    def __call__(self, now, inputs):
        """inputs: tuple of dicts (near, inside, waiting, on[, queue]); returns the same tuple with X1 delayed."""
        if RANGES[MODE] is None:
            return inputs
        self.frames.append((now, [{k: copy.copy(d[k]) for k in self.keys if k in d} for d in inputs]))
        if now >= self.next_draw:                          # the stream's lag drifts: a new value about every second
            lo, hi = RANGES[MODE]
            self.d = self.rng.uniform(lo, hi) + DETECT
            self.next_draw = now + HOLD_S
        half = (now - self.frames[-2][0]) / 2 if len(self.frames) > 1 else 0.0
        target = max(self.shown, now - self.d + half)        # nearest frame (half a step), not always the older one
        while len(self.frames) > 1 and self.frames[1][0] <= target:
            self.frames.popleft()                          # keep the newest frame not newer than the target
        t, frame = self.frames[0]
        self.shown = t
        self.delays.append(now - t)
        out = []
        for real, seen in zip(inputs, frame):
            real = dict(real)
            real.update(seen)
            out.append(real)
        return tuple(out)

    def check(self, now, phase, car_really_inside):
        """Accumulate seconds of walk signal at X1 while a car is really inside the crossing."""
        if self.last is not None and phase == "PED" and car_really_inside:
            self.unsafe += now - self.last
        self.last = now

    def stats(self):
        ds = sorted(self.delays) or [0.0]
        return {"camera_mode": MODE, "camera_detect_s": DETECT,
                "camera_delay_mean_s": round(sum(ds) / len(ds), 3),
                "camera_delay_max_s": round(ds[-1], 3),
                "x1_walk_with_car_inside_s": round(self.unsafe, 1)}
