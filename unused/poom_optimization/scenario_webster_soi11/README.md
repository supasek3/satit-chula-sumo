# Scenario: Webster signal at the gate + 30% of gate drop-offs sent to Soi 11

Built from `../baseline/` (same network, stops, data, driver logic). Two changes:

1. **Gate crossing X1 runs a Webster-based adaptive signal** (`webster_control.py`), following the team's AnyLogic
   PDF "Adaptive traffic signal control logic" with the agreed fixes:
   - Every 15 min: flows measured at X1 (cars crossing the stop line per lane, pedestrians entering the crosswalk)
     → y = q/s (s = 1,500 veh/h per lane, 6,000 ped/h) → C₀ = (1.5L + 5)/(1 − Y) with Y capped at 0.9, C in 30–120 s.
   - Green split uses the **uncapped** ratios (so greens never exceed C − L); cases A/B/C as in the PDF.
   - Min pedestrian green = ⌈4 + 6.4 m / 1.0 m/s⌉ = 11 s (real crossing length, child walking speed); min vehicle
     green 10 s; L = 8 s (yellow 3 + all-red 2 + pedestrian clearance 3, all-reds extended until the area is empty).
   - Real time: rest on vehicle green; once a pedestrian waits, cars keep green at most the Webster vehicle green
     counted **from the pedestrian's call**, or less on a > 3 s gap; pedestrians keep green while no car is waiting;
     when no car is near, the min green and the yellow are skipped.
   - Queue override: 25 halted cars in the left lane from X1 to the east entry → +15 s vehicle green, min pedestrian green.
   - X2 (Soi 11) keeps the guard controller.
2. **30% of the cars that would drop off at the gate turn left into Soi 11 and drop off at Z1** (`bs_2`) instead
   (`REDIRECT_TO_Z1` in `make_baseline.py`).

## Run (from this folder)
```
python3 guard_control.py 1 --gui      # watch seed 1
python3 run_seeds.py 10 --out results  # KPIs over 10 seeds
```
Switches (environment variables): `REDIRECT_TO_Z1=0` (no redirect), `X1_CONTROL=guard` (baseline guard at X1).
`variants/webster_only` (signal change only) and `variants/redirect_only` (redirect only) separate the two effects.

## Results (10 seeds each, mean ± 95% CI) — 2026-10-18
| KPI | Baseline | Webster only | Redirect only | Webster + redirect |
|---|---|---|---|---|
| Vehicle delay, all (s) | 677 ± 60 | 1012 ± 59 | **351 ± 28** | 675 ± 34 |
| Main-road delay (s) | 718 ± 64 | 1073 ± 62 | **371 ± 30** | 716 ± 37 |
| Ped wait X1 mean / p95 (s) | 19.5 / 51 | **7.0 / 20** | 18.8 / 50 | **6.5 / 19** |
| Ped wait X2 mean / p95 (s) | 2.6 / 12 | 2.1 / 10 | 7.4 / 34 | 5.2 / 26 |
| Max queue outside entry (veh) | 250 | 350 | **146** | 266 |
| Last car after 08:10 (min) | 32 | 42 | **16** | 27 |
| Overflow drop-offs after X2 (bs_4) | 15 | 21 | 149 | 159 |
| Collisions | 0 | 0 | 0 | 0 |
Webster picked the 30 s minimum cycle in every window (no oversaturated window): stop-line flows are capped by the
drop-off upstream. The signal mainly trades vehicle delay for pedestrian wait; the redirect to Soi 11 is what cuts
vehicle delay (but overloads Z1: ~150 cars drop off after X2 instead, and X2 pedestrians wait longer).
Files: `results/kpi_seeds.csv`, `variants/*/results/kpi_seeds.csv`.
