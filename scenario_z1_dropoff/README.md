# scenario_z1_dropoff — Left-turn optimization (Supasek, 22 Oct 2026)

Copy of `../baseline_v6/` (v5 with all no-student cars back). **One change, in the demand generator only — no network,
signal, driver-logic or crossing change; the structure stays as it is.**

## The rule
A car is moved if (1) its only planned drop-off is the left-lane gate spot (`bs_1`) **and** (2) it turns left into
Soi 11 (so it crosses X2). It drops off at **Z1 (`bs_2`)** instead, with a new dwell drawn from the Z1 distribution
(mean 35 s). Fixed: all such cars, all day (`REDIRECT_LEFT_TURNERS = 1.0`).

- Code: `make_baseline.py` — the setting `REDIRECT_LEFT_TURNERS` (env override; `0` = baseline_v6 demand, `0.5` = half),
  and a block after the Z1 second-drop-off pick. Own random stream (`SEED*37+11`): every other car of a seed is
  exactly as in v6.
- Not moved: cars with two drop-offs (`bs_1` + `bs_2`, 50 in seed 1), right-lane gate spot (`bs_5`), west-bound gate
  drop-offs (353), cars with no student.
- Seed 1: 90 cars moved; `bs_1` 493 → 403, `bs_2` 105 → 195.
- At run time the v6 driver logic is unchanged (if Z1 is full a car can overflow to `bs_4` after X2).

## Results (10 seeds, mean ± 95% CI; vs `../baseline_v6/results/kpi_seeds.csv`)
| | baseline_v6 | this scenario | change |
|---|---|---|---|
| Average vehicle delay (s) | 451 ± 65 | 313 ± 33 | −139 (−31%) |
| Delay, cars with a student (s) | 739 ± 99 | 515 ± 54 | −30% |
| Delay, cars with no student (s) | 248 ± 39 | 157 ± 15 | −37% |
| Last car done, min after 08:10 | 29.8 ± 3.1 | 20.1 ± 2.4 | −9.7 |
| Longest queue outside entry (cars) | 168 ± 20 | 130 ± 13 | −23% |
| X1 pedestrian wait, mean / slowest 5% (s) | 14.9 / 44.3 | 14.8 / 43.6 | no change |
| X2 pedestrian wait, mean / slowest 5% (s) | 2.5 / 10.5 | 4.8 / 22.6 | +2.3 / +12.1 |
| Drop-offs: left-lane gate / Z1 / after X2 (`bs_4`) | 453 / 102 / 3 | 362 / 140 / 70 | overflow past X2 |

0 collisions, 0 unfinished cars. (Team agreed an X2 mean wait up to ≈7.4 s is acceptable.)

## Caveats
- **Main-road volume is unverified** (HANDOFF §12); MOCK values unchanged.
- Assumes **100% of those parents follow the redirect** (MOCK), all day, even when the gate is quiet.
- Z1 (4 spots) overflows: about 70 cars/morning drop off after X2. Slowest-5% X2 pedestrian wait doubles.
- Compare with `../baseline_v6`, not with v0 or v5 numbers (different demand).

## Run (from this folder; Windows: `py -3`)
```
python3 guard_control.py 1 --gui                              # watch seed 1 (press ▶)
REDIRECT_LEFT_TURNERS=0.5 python3 guard_control.py 1 --gui    # only half of them
python3 run_seeds.py 10 --out results
```
