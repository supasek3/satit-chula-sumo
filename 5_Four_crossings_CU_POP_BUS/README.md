# Satit Chula — four zebra crossings and six pink CU POP BUS proxies

Separate version created 6 November 2026 from `window-0700-0745` at commit `77c443383c0c230552aeb27752fd0534732c886a`, using its latest `with_delay` models. The prior versions and GitHub branch were not edited.

## Open it in SUMO

Open a terminal in this folder and run:

```sh
python3 run_model.py --method combo_B --seed 1 --gui
```

For double-click launching after a GitHub download, first run `chmod +x Launch_Combo_B.command`, then double-click **Launch_Combo_B.command**. Browser uploads do not preserve the executable permission.

Other methods: `--method baseline`, `--method poom`, `--method fluke`. Camera choices: `--camera-delay none` (default), `ethernet`, `wifi`. The baseline always uses the no-camera case. `--drain` follows vehicles already scheduled before 07:45 until completion. Without it the run stops at 07:45, as in the source version. The source uses 0.1-second steps and measures its peak cohort from 07:15 to 07:45; the six bus replacements span the user-confirmed 07:00–07:45 window.

Each launch writes a fresh folder under `runs/` with demand, selected bus IDs, launch settings, controller statistics and unfiltered SUMO warnings. Opening a `.sumocfg` directly omits the Python controllers: use this launcher. Installed Eclipse SUMO 1.28.0 and its TraCI Python tools are needed. On this Mac the launcher automatically selects the existing Mesa-compatible GUI copy if available; that optional installation and the SUMO runtime are not included in the ZIP.

## Crossings

| ID | User's latitude | User's longitude | Implementation |
|---|---:|---:|---|
| X1 | Existing main gate | Existing | Existing controller retained |
| X2 | Existing second entrance | Existing | Existing controller retained |
| X3 | 13.737955 | 100.529222 | New zebra crossing, east approach |
| X4 | 13.738044 | 100.528696 | New zebra crossing, further west on east approach |

The pins are snapped longitudinally to the inherited road reference alignment, approximately **7.0 m at X3 and 5.7 m at X4** from the supplied pin coordinates. This avoids bending the road toward a map click. The precise supplied coordinates, projection and actual node coordinates are retained in `network/manifest.json`. The zebra geometry crosses the road at those longitudinal positions; this is not a surveyed geographic placement.

New X3/X4 rules are **unsignalized pedestrian priority**, with provisional 4 m crossing width and pedestrian waiting pads on both sides. These are explicit modeling assumptions pending site observation. Vehicles can yield to generated crossing pedestrians. Existing X1/X2 signals remain as in the selected method. Split entry edges were added to queue and lane-commitment logic. Other original lane counts and lengths are preserved within 0.05 m.

`new_crossing_arrivals.csv` intentionally contains only a header: X3/X4 demand is unknown, so default arrivals are zero. The zebra crossings are real network connections even with no pedestrians. Add one row per observed pedestrian:

```csv
crossing,depart_s,direction
X3,1800,N_to_S
X4,1810,S_to_N
```

Here 0 seconds is 06:30; 1800 is 07:00; 2700 is 07:15; 4500 is 07:45. `N`/`S` label the two waiting-pad sides; confirm these against field directions. Do not add the example rows as if they were observations. Alternatively launch with `--arrivals /absolute/path/to/observed_arrivals.csv`.

## CU POP BUS assumption

- Exactly **six existing through cars are replaced**, not six extra vehicles.
- Eligibility: main entry to west exit, no school drop-off or parking destination, scheduled 07:00–07:45.
- A deterministic selection distributes them across six equal time bands by choosing the nearest existing departure. Their IDs, exact departures, lane choices and routes remain unchanged.
- Pink colour `255,105,180`, type `cu_pop_bus`, bus icon. The display colour controller protects pink from the normal purple override.
- Purple still means other vehicles without a school drop-off, including through, parking and side-road traffic. Pink identifies the six CU POP BUS placeholders.
- **These are visual/service proxies with the original car physics:** 5 m length, 2.5 m gap, 2.6 m/s² acceleration, 4.5 m/s² deceleration, passenger lane permissions. The bus icon does not imply realistic bus dimensions or performance. No bus stop, dwell, passenger boarding, real route or observed timetable has been invented.
- Count, colour and proxy attributes are editable in `assumptions.json`. Replace the proxy settings with measured bus dimensions, movement and stopping behavior when available. The existing 35-second school drop-off assumption applies to parents, not these through proxies.

## Verification

`python3 test_scenario.py` runs four checks: four-crossing network and retained geometry; exact six-replacement demand conservation for seeds 1/2/21; pink protection; and actual traversal of both new zebra crossings in both directions.

A full Combo B seed-1 run at the source's 0.1-second step with clearance completed: 843 scheduled vehicles inserted, all vehicles and pedestrians cleared, all six proxies arrived, zero vehicle collisions or teleports. The retained log records one emergency brake, one emergency stop and three pedestrian-overlap warning messages at existing X1/P1-area geometry. This is a functionality check, not a new improvement or safety claim. Default X3/X4 demand is zero, so performance with their real pedestrian demand remains untested.

Additional full runs of baseline seed 2, Combo B seed 2 and Fluke seed 1 also cleared every vehicle, including all six proxies in each run, with zero vehicle collisions or teleports. Pedestrian-overlap warnings remain, and Fluke seed 1 recorded one emergency brake. `smoke_results.json` retains counts from all four runs.

## Files

- `baseline/`, `combined/`, `fluke/`: separate runnable source models with the new network and extension hook. `combined` supplies both Poom and Combo B presets.
- `run_model.py`: isolated GUI/headless launcher; use ordinary TraCI by default. `--backend libsumo` optionally uses the already installed local acceleration runtime.
- `scenario_extension.py`, `assumptions.json`: demand replacement rules and explicit provisional values.
- `new_crossing_arrivals.csv`: replace with observations when available.
- `network/`: compiled SUMO network, reproducible plain network source and coordinate manifest.
- `build_version.py`: rebuilds from the adjacent pinned source checkout; uses the repository’s with_delay folder (or the adjacent pinned source checkout) and libsumo for coordinate projection. The supplied compiled network does not need rebuilding to run.
- `test_results.log`: verification output. Raw local smoke outputs are under `runs/` and excluded from the shareable ZIP.
