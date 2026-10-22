# SUMO review package — 22 October 2026

Start with **SUMO_REVIEW_2026-10-22.md**. It explains which data were verified, the two model corrections, the proposed method and the limits of the results.

- `baseline_v6_corrected/`: runnable corrected baseline and proposed controller. See its README for launch commands.
- `baseline_v6_audit/`: original v6 demand generator and input snapshot used for the regression comparison.
- `results_validated/`: development/selection comparisons on seeds 1–10.
- `results_holdout/`: selected method versus baseline on new seeds 11–20.
- `results_timestep_check/`: one-seed 0.2-second diagnostic, not a replicated validation set.
- `comparison.png`: paired uncertainty plot.
- `test_review.py`: four regression checks.

The 35-second mean drop-off remains a **provisional assumption**. One car now uses only one entrance. The original team project was not edited.

The proposed method reduces pedestrian waiting in the new-seed test. Reliable average vehicle improvement is still unproven, and timestep sensitivity and simulation warnings remain open. Keep it as an experimental candidate.

Batch runs use `experiment.py`. Use a fresh `--tag` for changed inputs, code or timesteps. Previously saved results are reused only if the recorded run signature matches; earlier review evidence without a signature is preserved and requires a fresh tag for a rerun.

The full reviewed model is stored in five numbered `.b64.txt` parts because GitHub rejected ZIP and TAR uploads. Run `python3 extract_SUMO_review_2026-10-22.py` beside those parts to reconstruct `review_2026-10-22/`. The package excludes the installed optional runtime and large raw XML output files. Standard Eclipse SUMO 1.28.0 with its TraCI Python tools is sufficient; optional `libsumo==1.28.0` speeds up headless comparisons.

The GitHub copy also keeps only the compact CSV/JSON result summaries. Re-run the experiment scripts to regenerate per-seed SUMO XML outputs.
