"""Colours cars by drop-off status in sumo-gui (user request, 2026-10-19). Display only: no effect on the model.

    green   still has a child to drop off (a drop-off stop is still ahead)
    red     dropping off right now (standing at its drop-off)
    yellow  finished dropping off
    purple  no student: through traffic, parking and Soi 13 cars
Pedestrians stay magenta (set in the route file).
"""
import traci

GREEN, RED, YELLOW, PURPLE = (0, 200, 0, 255), (230, 0, 0, 255), (255, 215, 0, 255), (120, 40, 200, 255)


class CarColors:
    def __init__(self, zone=None):
        self.zone = zone         # dynamic_dropoff.GateZone: cars held still while dropping off in the P1 junction
        self.state = {}          # car with a child -> current colour

    def step(self):
        for v in traci.simulation.getDepartedIDList():
            if traci.vehicle.getStops(v):
                self.state[v] = None
            else:
                traci.vehicle.setColor(v, PURPLE)
        for v in traci.simulation.getArrivedIDList():
            self.state.pop(v, None)
        for v, old in self.state.items():
            z = self.zone
            dropping = traci.vehicle.isStopped(v) or (z is not None and v in z.held)
            finished = z is not None and v in z.done                   # bs_1 left over as a pass-through point
            new = RED if dropping else YELLOW if finished else GREEN if traci.vehicle.getStops(v) else YELLOW
            if new != old:
                traci.vehicle.setColor(v, new)
                self.state[v] = new
