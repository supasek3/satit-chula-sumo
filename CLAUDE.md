# CLAUDE.md — Satit Chula SUMO project (handoff package)

You are continuing a SUMO traffic-simulation project started by Supasek with Claude. This file is your briefing.
**Read `HANDOFF.md` before doing any work** — it has every detail (network, data, controllers, results, decisions).
`reference/WORKING_LOG.md` is the chronological log of how everything was built and why.

## What the project is
Replace the human guard who acts as a "manual traffic light" at the zebra crossing in front of the gate of
**Satit Chulalongkorn Demonstration School** (Bangkok) during the **morning peak, 06:30–08:10**.
Phase 1 (current): SUMO simulation — a data-grounded baseline, then optimisation scenarios compared on KPIs.
Phase 2 (later): hardware prototype (camera detection + microcontroller signal) of the best strategy.

## Current state
- `baseline_v5/` — **the current baseline** (team decision 19 Oct 2026), frozen with 10-seed results. **Do not
  modify it.** Copy it to build anything new. Compared with v0: continuous 60 m / 8-car dynamic gate drop-off
  (across the P1 driveway), "drop here or move closer" rule, only 6% use `bs_0` / switch to `bs_5`, gate parents
  keep the left lane, cars with no student cut to 20%, car colours in the GUI. Full list + decision log: its README.
- `baseline/` — **v0, the original handed-off baseline**. Kept unchanged for history and comparison; do not modify.
- `baseline_officer/`, `scenario_webster_soi11/` — scenarios built on **v0** (not v5); their results compare with
  `baseline/`, not `baseline_v5/`.
- Headline result (v0): the **gate drop-off** (≈500 drop-offs × 35 s on 4+4 curb spots) is the bottleneck, not the
  signal. Signal logic trades car delay against pedestrian wait; moving drop-offs away cuts car delay.

## Key facts you must keep straight
- **Left-hand traffic** (Thailand). Main road is **one-way east → west**, two lanes. In SUMO: lane `_0` = sidewalk
  (school side), `_1` = **left** lane (school side, main drop-off lane), `_2` = **right** lane.
- **X1** = gate crossing = SUMO junction **`10784747877`** (TLS + crossing `:10784747877_c0`).
  **X2** = Soi 11 crossing = SUMO junction **`J1`**. The friend's AnyLogic "J1" is a different place
  (the west corner `cluster10784747874_358216946_J0`) — do not mix them up.
- Drop-off stops (`dropoff.add.xml`): `bs_1` gate left (4 cars), `bs_5` gate right (4), `bs_0` after X1 (3),
  `bs_2` Soi 11 Z1 (4), `bs_4` after X2 (4). 7.5 m per car. Their positions/capacities are user-confirmed final.
- Time 0 = 06:30; demand ends at 6000 s (08:10); runs continue until every car is done.
- Data classes stay distinct: FIELD (counted), MODEL (friend's AnyLogic), MOCK (assumed), team/user decisions.
  The main-road volume is **unverified** — say so whenever you report results.

## How to run (from inside a model folder; on Windows use `py -3` instead of `python3`)
A model folder needs an `output/` subfolder for GUI runs (SUMO does not create it).
```
python3 guard_control.py 1 --gui        # watch seed 1 (press ▶ in sumo-gui)
python3 run_seeds.py 10 --out results    # KPIs over 10 seeds (~15–25 min) → results/kpi_seeds.csv
python3 make_baseline.py <seed>          # regenerate demand after editing baseline_inputs.csv / parameters
```
- Always run through `guard_control.py`/`run_seeds.py`: they drive the crossing controllers and the driver logic via
  TraCI. Plain `sumo-gui -c baseline.sumocfg` falls back to a fixed signal plan (not the model).
- Both scripts regenerate `baseline.rou.xml` in their folder — never run a GUI and a seed run in the same folder at
  the same time (use a separate demand copy with `-r`, see HANDOFF §10).
- Run long seed runs in the background; each seed takes ~1.5 min.

## Environment (check first on a new machine)
- Needs **Eclipse SUMO 1.28** (`sumo`, `sumo-gui`, `netconvert`, `netedit` on PATH) and Python 3 with **`pyproj`**
  (and Pillow if you draw map overlays).
- The scripts find TraCI via `SUMO_HOME` if it is set, otherwise via the macOS path
  `/Library/Frameworks/EclipseSUMO.framework/Versions/1.28.0/EclipseSUMO/share/sumo/tools`.
  **On any other machine set `SUMO_HOME`** (e.g. `export SUMO_HOME=/usr/share/sumo` on Linux,
  `C:\Program Files (x86)\Eclipse\Sumo` on Windows) or edit `TOOLS` at the top of each `guard_control.py`.
- Harmless warnings: `Could not set locale to 'C'`, `Cannot find proj.db`, `SUMO_HOME is not set`, `Fontconfig`.

## Rules for working on this project
1. **Never modify `baseline_v5/` or `baseline/`.** New ideas = new folder copied from `baseline_v5/`
   (e.g. `scenario_<name>/`), with a README.
2. Network changes: write node/edge/connection patch files and apply with
   `netconvert -s <in>.net.xml … -o <out>.net.xml` to a **new** file; keep the previous network as a backup.
   Never overwrite a net with netconvert in place. In netedit open with `-s` (not `-n`); answer **No** to saving
   the network unless intended. Never use `components/network_build/make_crossings.sh` on its own — it rebuilds
   from the original master and loses all later changes (rebuild procedure: HANDOFF §4.6).
3. After any network change, re-check: drop-off capacities (peak occupancy test), pedestrians crossing both
   crossings, driveway trips, a full seed with `--collision.check-junctions true` (0 collisions), teleports.
4. Report results as **10-seed means with 95% CI**; compare against `baseline_v5/results/kpi_seeds.csv`
   (v5 demand has only 20% of the no-student cars, so do not compare v5-based scenarios with v0 numbers directly).
   Vehicle delay = timeLoss + departDelay. Don't use SSM rear-end conflict counts as a safety KPI.
5. Ask the user before changing assumptions (volumes, shares, dwell times, MOCK values); record every decision
   (append to HANDOFF.md's decision log or a log in the scenario folder).
6. The user is a student team member, not a SUMO expert: explain in plain language, give copy-paste commands.

## Suggested next steps (from HANDOFF §13)
1. Verify the main-road counts/units with the data owner (largest uncertainty).
2. Drop-off scenarios (most promising): more curb space / upstream stretch, organised drop-off with shorter dwell,
   spreading drop-offs between the gate and Soi 11 with more Z1 capacity.
3. A Webster variant fed by upstream demand (east-entry counts) instead of stop-line flow.
4. Sensitivity runs on MOCK values and the 35 s dwell; more seeds for final numbers.
