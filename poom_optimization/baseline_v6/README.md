# baseline_v6 — v5 with all the no-student cars back (created 21 Oct 2026)

Copy of `../baseline_v5/` with **one change**: the cars with no student (purple in the GUI: through traffic,
parking IN/OUT, Soi 13) are no longer thinned out. v5 kept 20% of them; v6 keeps **100%**, as in v0.

- Changed: `make_baseline.py` → `NO_STUDENT_KEEP = 1.00` (was 0.20). User decision 2026-10-21.
- Everything else is identical to v5: network, 60 m / 8-car dynamic gate drop-off, "drop here or move closer" rule,
  6% to `bs_0` / `bs_5`, gate parents keep the left lane, guard controller at both crossings, pedestrians, the cars
  that carry a student, 35 s drop-off time, car colours.
- Seed 1 demand: 1,231 vehicles (v5: 698; the 533 removed cars are back), same 621 drop-offs and 1,111 pedestrians.
  Because the thinning uses its own random stream, every car with a student is exactly as in v5 for the same seed.
- Main-road volume is still unverified (HANDOFF §12); MOCK values unchanged.

**10-seed results (22 Oct 2026, `results/kpi_seeds.csv`, mean +- 95% CI):** vehicle delay 457 +- 63 s (cars with a student
751, no student 248), gate pedestrian wait 14.7 s (p95 44), X2 2.6 s, last car 29.7 min after 08:10, max queue outside the
entry 168, 0 collisions, 0.4 teleports. Raw per-seed outputs are not included. This is the reference for `../scenario_opt/`
(the best control package there gets 259 +- 35 s on the same demand).

The full description of the v5 rules is kept in `README_v5.md`.

## Run (from this folder; Windows: `py -3`)
```
python3 guard_control.py 1 --gui        # watch seed 1 (press ▶)
python3 run_seeds.py 10 --out results    # 10 seeds → results/kpi_seeds.csv
```
Do not open the GUI and a seed run in this folder at the same time (both rewrite `baseline.rou.xml`).
