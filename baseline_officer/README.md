# Baseline variant: traffic officer at the gate crossing

Copy of `../baseline/` where the gate crossing **X1** is run by a traffic officer (`officer_control.py`), which is
less efficient than a signal. Everything else (network, drop-offs, demand, driver logic, Soi 11 crossing X2 with the
guard controller) is identical to the baseline.

## Officer rules (user, 2026-10-18)
- No car coming → pedestrians cross freely. No pedestrian waiting → cars keep going.
- Cars keep going while the **front car of the left lane** has already dropped off, drops off after the crossing,
  or is going straight / south. When the front car still has to drop off at the left-lane gate zone (`bs_1`), the
  officer stops traffic until that drop-off is finished **and** the pedestrians at the edge have crossed.
- Off-peak (left-lane queue ≤ 5 cars): pedestrians have priority. Peak (> 5): pedestrians cross during drop-off
  stops, and **no pedestrian waits more than 120 s**.
- Only the left lane is looked at; when the officer stops traffic both lanes stop.
- Human behaviour: 3 s reaction, at least 5 s per go / stop, no yellow, 3 s for cars to obey a stop signal;
  traffic restarts only once the crosswalk is empty. The officer gives up waiting for a car that has not started its
  drop-off within 60 s (prevents a deadlock seen in testing).

## Run (from this folder)
```
python3 guard_control.py 1 --gui        # watch seed 1
python3 run_seeds.py 10 --out results    # KPIs over 10 seeds
```

## Results (10 seeds, mean ± 95% CI) vs the baseline guard controller
| KPI | Baseline (guard) | Officer |
|---|---|---|
| Vehicle delay, all (s) | 677 ± 60 | 653 ± 38 |
| Main-road delay (s) | 718 ± 64 | 692 ± 41 |
| Parking OUT P1 / P2 (s) | 165 / 181 | 158 / 215 |
| Ped wait X1 mean / p95 (s) | **19.5 / 51** | **42.5 / 110** |
| Longest X1 ped wait per seed (s) | — | 116–128 (target 120; 3 seeds slightly over) |
| Ped wait X2 mean (s) | 2.6 | 2.7 |
| Max queue outside entry (veh) | 250 | 233 |
| Last car after 08:10 (min) | 32 | 32 |
| Collisions / teleports | 0 / 0.4 | 0 / 0.6 |
Officer stops per morning: 40 for drop-offs, 22 off-peak pedestrian priority, 23 for the 120 s maximum wait, 0 give-ups.
The officer is clearly worse for pedestrians (about double the wait); vehicle delay is about the same (difference
within the confidence range), because the gate drop-off, not the crossing, limits the cars.
