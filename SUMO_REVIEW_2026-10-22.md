# SUMO baseline review and proposed method

Satit Chula · 22 October 2026 · 06:30–08:10 demand window

## Decision

**The SUMO baseline is runnable, but it was not ready to freeze as a validated baseline.** The review found and corrected duplicate drop-off assignments and a lane-control defect. The count tables are internally consistent with the available register, and the main pedestrian bins match the raw timestamps. Major vehicle-volume and behavioral assumptions remain provisional.

The best candidate investigated is **organized use of the existing drop-off space plus a demand-responsive crossing with a 25-second call trigger**. New-seed testing supports a reduction in main-gate pedestrian waiting. The average vehicle improvement is promising but statistically uncertain, and simulation warnings and timestep sensitivity remain unresolved. Keep the corrected baseline and candidate separate. Do not replace the baseline with the proposed method or claim that both objectives are conclusively improved.

The original project folders were not edited. Source-file hashes were checked. The changes are in `baseline_v6_corrected/` in this review package.

## 1. What was checked

The latest local model is `baseline_v6`, dated 21 October 2026. It restores 100% of the non-student traffic, unlike v5's 20%. The top-level handoff still identifies v5 as current, so that documentation is stale. Old officer/Webster/redirect scenarios were built on v0 and are not valid direct comparators for v6.

| Item | Finding | Status |
|---|---|---|
| Main pedestrians | Raw timestamps reproduce 31, 82, 129, 183, 198, 251, 15; total 889 | Verified against the local raw workbook |
| Second pedestrians | 8, 20, 32, 46, 49, 63, 4; total 222 | Accepted MOCK value; implemented correctly |
| Second drop-offs | 4, 10, 15, 22, 23, 29, 2; total 105 | Accepted MOCK value; maintained after the correction |
| Side-road register | 172 + 351 = 523 | Matches the register; original counter CSV was not available in the inspected project data |
| Parking register | P1 IN/OUT = 151/88; P2 IN/OUT = 46/27 | Matches the register; original parking count CSV was not available |
| Main-road schedule | 764.5 vehicles if the schedule unit is vehicles/hour | Source and intended units remain unverified |
| Main-road target | (764.5 + 420) / 2 = 592.25 before moved traffic | Team assumption; averaging conflicting totals is not calibration |
| Traffic reassignment | 90% of side-road and parking-OUT demand is moved to the main entrance; parking-IN demand is reduced to 10% | Documented team scenario assumption, not observed geography |
| Mean drop-off dwell | 35 seconds | User reconfirmed as a provisional assumption in this review |
| Turn split | 70% west / 30% south for main-road traffic | MOCK; unchanged |
| Demand generation | Approximately 1,230 vehicles plus 1,111 pedestrians | Internally consistent with transformed inputs; not a direct field replay |
| Road and crossings | X1=`10784747877`, X2=`J1`; pedestrian-only sidewalks and crossing connections present | Simulation structure checked; physical survey not independently performed |

All nine FIELD/MOCK count series were checked bin by bin against the register. Rate × duration agrees with count within CSV rounding tolerance. Every series covers 100 minutes, with a final 10-minute bin. The generator uses **count** and row order; changing only `rate_per_min` does not change generated demand.

Seed 1 originally has 1,231 vehicles: 1,164 from the main entry, 54 from Soi 13, 9 from P1 OUT and 4 from P2 OUT. Parking IN diverts existing main-road cars rather than adding a new vehicle source. Those entry totals differ from the raw register because of the documented transformations.

The two raw drop-off files contain 348 and 17 records overall. Restricting starts to 06:30–08:10 leaves **345 records averaging 12.22 seconds** and **15 averaging 4.99 seconds**. These measure door-open-to-move time. Lane coverage and whether maneuvering is included must be established before replacing the 35-second scenario assumption. The user chose to keep 35 seconds for now.

The raw workbook also records 156 signal intervals. The corrected guard baseline produces 176.4 X1 pedestrian-admission cycles on selection seeds and 180.0 on new seeds. Counts alone do not establish calibration, and the physical meaning of the recorded signal intervals needs confirmation.

## 2. Corrections made

### One entrance per drop-off vehicle

The old generator first assigned a main-gate stop and then appended a second-entrance stop to sampled southbound cars. This caused **42–64 vehicles per seed** to stop at both entrances in seeds 1–10; seed 1 had 52.

The user confirmed that each car should use only one entrance. The correction retains the selected 105 second-entrance vehicles and replaces any main-gate stop for those cars. It preserves vehicle IDs, departure times, origins, destinations, pedestrian IDs/times and the random dwell draws for the retained stop. Main-gate stop totals necessarily fall. Seed 1 changes from 621 stop events on 569 vehicles to **569 stop events on 569 vehicles**, including exactly 105 at the second entrance.

### Left-lane commitment across driveway junctions

The driver logic previously restored normal lane changes whenever a car entered an internal junction lane. A traced car left the P1 internal link in the right lane despite still requiring a left-lane gate stop, became stuck, teleported and skipped its stop. The correction preserves its left-lane commitment across internal links while the same gate stop remains assigned. It still releases the commitment if the destination stop changes.

The corrected baseline and all candidate variants use this identical fix. The final selection and new-seed runs recorded no vehicle teleports, skipped stops or unfinished trips. A further reconciliation of all 70 final selection/new-seed runs confirmed that every assigned drop-off vehicle completed exactly one service, using ordinary stop records plus the separately recorded manual holds.

### Measurements and reproducibility

- Vehicle categories now come from assigned demand. `stopTime > 0` was unreliable because manually held junction drop-offs could have zero recorded scheduled stop time.
- The review records delay accrued during manually held dwell and removes it from the delay diagnostic, making it more consistent with SUMO's exclusion of ordinary scheduled stops.
- **Total vehicle journey time from scheduled departure to arrival** is the primary vehicle measure. It includes the entry queue and drop-off time, avoids silently ignoring held vehicles, and is paired on identical demand. Raw delay and the adjusted diagnostic are retained separately. Waypoint handling can affect the interpretation of SUMO stop/time-loss fields; the adjusted diagnostic should not be treated as a fully calibrated pure congestion measure.
- Both vehicle and pedestrian completion are checked. Demand hashes must match across methods within each seed. Pedestrian mean, p95 and maximum waits are kept separately for both crossings.
- X1 cycles count actual entries into the pedestrian-admission phase, rather than all signal-state changes.
- `PYTHONHASHSEED=0` makes Python set iteration repeatable in addition to the SUMO/controller seeds. The old scripts did not fix this source of variation.
- Four regression checks cover input windows/units, preservation of the demand while removing duplicate stops, lane commitment across a junction, and equivalence/clearance behavior of the shipped proposed controller.

An instrumented libsumo 1.28.0 run reproduced the original normal SUMO/TraCI seed-1 raw vehicle-delay and pedestrian-wait results exactly before the model corrections. This was checked before using libsumo to accelerate replications.

## 3. Proposed method and why it could help

**Organized drop-off + demand-responsive pedestrian service.** Use an attendant, markings or instructions to allocate available space along the modeled zone, so parents do not keep queuing for a position nearer the gate. Then serve pedestrian requests at natural vehicle gaps, with a waiting-call trigger to prevent prolonged deferral.

The tested organized case opens all eight already modeled positions in the existing 60 m zone and assumes 100% acceptance when a driver is halted at a usable position. It adds no road space, removes no traffic, reroutes no vehicles to the second entrance, and retains the same 35-second dwell distribution. This is an **ideal-compliance intervention assumption**, not an observed behavior.

| X1 setting | Candidate value |
|---|---:|
| Minimum vehicle green before optional gap service | 8 s |
| Waiting-call age that initiates switching | 25 s |
| Minimum pedestrian admission time | 4 s |
| Maximum pedestrian admission time while cars wait | 10 s |
| Yellow when vehicles are near | 3 s |
| Vehicle-to-pedestrian clearance | Wait until conflicting junction vehicles have cleared |
| Pedestrian-to-vehicle clearance | At least 2 s and crossing must be empty |
| X2 controller | Existing guard logic |

The admission timer governs entry to the crossing. It does not require a pedestrian to finish crossing in 4 seconds; the clearance phase waits for the crossing to become empty. The 25-second trigger is not a maximum completed pedestrian wait. All these are experimental simulation values, not approved physical-road timings.

The zone includes the P1 driveway stretch in the inherited model. Its physical suitability, usable capacity and realistic compliance remain prerequisites for an operational proposal. Pedestrian sources are independently generated; drop-off passengers are not explicitly alighted into the pedestrian model. Avoid claiming that changing drop-off locations automatically predicts the resulting pedestrian routes.

## 4. Selection experiments: seeds 1–10

Five variants used identical corrected demand for each seed and unchanged road geometry, 35-second dwell and all other accepted input assumptions. Each table entry is the mean of ten runs.

| Method | Vehicle delay diagnostic (s) | X1 wait (s) | X2 wait (s) |
|---|---:|---:|---:|
| Corrected guard baseline | 370.8 | 14.06 | 2.67 |
| Organized drop-off only | 323.0 | 14.48 | 3.10 |
| 20 s adaptive call trigger only | 405.5 | 10.10 | 2.77 |
| Organized + 20 s call trigger | 354.0 | 10.17 | 2.89 |
| Organized + 25 s call trigger (selected) | 336.6 | 11.81 | 2.84 |

Signal-only control clearly shifts waiting toward vehicles. Organized drop-off alone improves vehicle performance without establishing a pedestrian benefit. The 25-second combined variant had favorable paired intervals for both vehicle journey time and X1 pedestrian waiting in this **selection** set, so it was chosen for new-seed evaluation. These exploratory comparisons are not independent proof of the selected method.

One person-to-person collision warning occurred in the organized-only selection runs. All selection variants had zero reported vehicle collisions, teleports and unfinished trips. Warnings were retained rather than suppressed.

## 5. New-seed evaluation: seeds 11–20

The selected settings were held fixed, and ten previously unused seeds were compared against the corrected baseline. The demand file hash matches for every pair. Confidence intervals use the paired seed differences with Student's t, 9 degrees of freedom. Runs with unfavorable outcomes were not excluded.

| Metric | Baseline mean ± 95% CI | Proposed mean ± 95% CI | Paired change [95% CI] |
|---|---:|---:|---:|
| Vehicle journey time, including entry queue and drop-off (s) | 487.63 ± 40.48 | 467.92 ± 26.57 | -19.71 [-50.47, +11.05] |
| Vehicle delay diagnostic, excluding manually held dwell (s) | 374.74 ± 40.30 | 355.11 ± 26.41 | -19.63 [-50.39, +11.13] |
| Vehicles completing by 08:10 | 1064.50 ± 15.77 | 1069.00 ± 15.07 | +4.50 [-6.19, +15.19] |
| Main-gate pedestrian wait, mean (s) | 13.63 ± 0.73 | 11.68 ± 0.27 | -1.95 [-2.67, -1.22] |
| Main-gate pedestrian wait, mean of per-run p95 (s) | 40.70 ± 1.72 | 29.90 ± 0.53 | -10.80 [-12.67, -8.93] |
| Second-entrance pedestrian wait, mean (s) | 2.77 ± 0.34 | 2.68 ± 0.20 | -0.09 [-0.54, +0.36] |
| Second-entrance pedestrian wait, mean of per-run p95 (s) | 12.00 ± 1.58 | 12.50 ± 1.52 | +0.50 [-2.18, +3.18] |
| Pedestrian wait, both crossings weighted by person count (s) | 11.46 ± 0.61 | 9.88 ± 0.20 | -1.58 [-2.19, -0.96] |
| Time until last vehicle finishes after 08:10 (min) | 24.31 ± 2.33 | 22.76 ± 2.14 | -1.55 [-3.07, -0.03] |

**Interpretation:** X1 pedestrian mean waiting falls by about 14%, and the mean per-run p95 falls from 40.7 to 29.9 seconds. The average vehicle delay diagnostic falls by about 5%, but its paired interval crosses zero; a reliable average vehicle benefit has not been established. The last vehicle clears about 1.55 minutes earlier on average, with a narrow interval just below zero. Throughput by 08:10 and X2 waiting changes remain uncertain. Do not describe X2 as demonstrably improved or guaranteed not to worsen.

![Paired changes with confidence intervals](comparison.png)

In all 20 new-seed runs, every vehicle and pedestrian completed, with zero vehicle collisions, teleports or skipped stops. **The proposed runs nevertheless emitted five person-to-person collision/overlap warnings across seeds 13 and 20.** These are log messages, including repeated pairs, not five independently established real-world collisions. They are not included in SUMO's `safety collisions` total. Consequently, reporting only “zero collisions” would be misleading. Zero simulated vehicle collisions would not itself establish road safety.

## 6. Timestep check

Both seed-20 cases were also run at 0.2 seconds instead of 1 second, without changing the controller settings or demand. At 0.2 s, the baseline/proposed vehicle journey means were **415.87 / 287.05 s**, compared with **432.45 / 477.96 s** at 1 s. X1 waits at 0.2 s were **12.27 / 11.02 s**. This reversal in the vehicle comparison shows material numerical/behavioral sensitivity.

The pedestrian overlap warnings disappeared in this single smaller-step run, but the proposed case reported **two emergency-braking events and one emergency-stop event**. Both runs completed without vehicle collisions or teleports. This is a diagnostic result, not a validated fix or evidence that one timestep is correct. No final numerical performance claim should be made until the controller and driver model have passed a replicated timestep/convergence check.

## 7. What is ready and what remains

Ready for continued simulation development: the corrected one-entrance baseline, the fixed lane-holding behavior, isolated repeatable comparison runs, detailed completion/warning accounting, and the runnable proposed controller.

Before freezing a research baseline or claiming improvement in both objectives:

1. **Establish effective traffic inputs.** Verify the main-road count location/time/unit, whether 420 and 764.5 describe the same population, and whether the 90% relocation and 10% parking-IN scaling should remain as mock scenario choices. Keep raw FIELD counts separate from effective simulated entries.
2. **Validate crossing and driver behavior.** Reconcile the 156 recorded intervals with simulated guard operation, identify realistic initial queues at 06:30, explicitly choose pedestrian speed parameters, and verify the 60 m zone/driveway geometry. The present `student` vehicle type uses SUMO pedestrian defaults rather than explicitly implementing the older AnyLogic 1.0–1.2 m/s assumption.
3. **Resolve numerical and safety warnings.** Repeat smaller-step tests, inspect the emergency-stop trajectories and person overlap events, and verify detection/clearance under slow pedestrians and late vehicles. Do not hide warnings or change geometry merely to remove them.
4. **Test practical sensitivity.** After the preceding corrections, predefine comparisons for main-road demand, 35-second dwell uncertainty, 50/75/100% bay compliance, second-gate demand and arrival bursts. The raw pedestrian timestamps can support a replay case. Keep the baseline and candidate matched within each scenario.
5. **Confirm benefit on a new evaluation set.** Predefine a sufficient seed count and the acceptance rule. Require lower vehicle journey time/delay and pedestrian waiting, no lost or teleported demand, and acceptable second-gate tails and safety diagnostics. A development result that fails these criteria stays a candidate.

No empirical mock parameters were silently replaced during this review. The two user decisions were: retain 35 seconds provisionally, and allow each car to drop off at only one entrance. Repairs and candidate intervention settings are documented separately.

## 8. Files and reproduction

- `baseline_v6_corrected/README.md`: model details and GUI/batch commands.
- `baseline_v6_corrected/run_model.py`: launch corrected baseline or proposed controller.
- `experiment.py`: all comparison variants with isolated per-seed model/output folders.
- `results_validated/comparison.csv`: selection comparisons, seeds 1–10.
- `results_holdout/comparison.csv`: independent new-seed comparisons, seeds 11–20.
- `input_audit.json` and `corrected_demand_checks.json`: count reconciliation and per-seed demand checks.
- `test_review.py`: regression checks.

Full raw outputs remain in the local review folder. The shareable ZIP includes source models, summaries, per-seed metrics and warning logs, but excludes the large runtime and XML trajectory/output files. Installing the optional pinned `libsumo==1.28.0` package accelerates headless runs; standard SUMO/TraCI remains supported. Map tiles are © OpenStreetMap contributors.

## Sources

Local project: `satit-chula-sumo-main/baseline_v6/`, its README, v5 README, `HANDOFF.md` and the original input/code/result files. These describe the scenario decisions; they are not independent field validation.

Raw pedestrian and signal records: :codex-file-citation{path="/Users/ittipol.f/Documents/Year 4/Final Project/Data/school-crossing-data-2026-08-18 3.xlsx" purpose="source" artifact_kind="workbook"}

Raw drop-off records: :codex-file-citation{path="/Users/ittipol.f/Documents/Year 4/Final Project/Data/school-crossing-data-2026-08-18.xlsx" purpose="source" artifact_kind="workbook"}

Count register: :codex-file-citation{path="/Users/ittipol.f/Documents/Year 4/Final Project/Data/Satit_Chula_Simulation_Input_Register.xlsx" purpose="source" artifact_kind="workbook" sheet="FIELD_MOCK" range="A4:H67"}

SUMO documentation supports the metric definitions, actuation API and runtime mechanics, rather than proving this site's assumed parameters: [TripInfo](https://sumo.dlr.de/docs/Simulation/Output/TripInfo.html), [pedestrian-actuated crossing tutorial](https://sumo.dlr.de/docs/Tutorials/TraCIPedCrossing.html), [pedestrian modeling](https://sumo.dlr.de/docs/Simulation/Pedestrians.html), [randomness and seeds](https://sumo.dlr.de/docs/Simulation/Randomness.html), [libsumo](https://sumo.dlr.de/docs/Libsumo.html), [waypoints](https://sumo.dlr.de/docs/Definition_of_Vehicles%2C_Vehicle_Types%2C_and_Routes.html#waypoints).
