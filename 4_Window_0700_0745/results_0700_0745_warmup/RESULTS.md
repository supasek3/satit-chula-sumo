# Results: 07:00–07:45 with the queue carried over from 06:30 (5 Nov 2026)

Simulated 06:30–07:45 (hard stop), measured only cars and students planned to depart 07:00–07:45 (≈ 688 cars,
637 students per seed). 5 seeds per version, paired with baseline_v7. Car delay = time lost on the road + time waiting
to enter, including cars still on the road or still waiting to enter at 07:45 (their delay so far).
Built with `../analyze_all.py --seeds 5`.

| Version | Car delay mean | median | 95% | X1 wait 95% | X2 wait 95% | Cars waiting at 07:45 |
|---|---|---|---|---|---|---|
| Baseline v7 | 185 s | 73 s | 646 s | 38 s | 12 s | 64 |
| Fluke | 167 (−10%) | 69 (−5%) | 599 (−7%) | **30 (−21%)** | 13 (+10%) | 61 (−5%) |
| Poom (best) | **122 (−34%)** | **43 (−40%)** | **442 (−32%)** | 42 (+12%) | 12 (0%) | **27 (−58%)** |
| **Combo B** | 142 (−24%) | 48 (−34%) | 540 (−16%) | **30 (−22%)** | 13 (+4%) | 41 (−36%) |

Within seed noise: Fluke's median/95% delay and cars waiting; Poom's X1 change; all X2 changes. No collisions or
teleports. Students waiting > 30 s at X1: baseline 12%, Fluke 4%, Poom 14%, Combo B 4%.

**Recommendation: Combo B** (Poom's rules + Fluke's signal at X1). B vs Poom on the same seeds: mean car delay
+20 ± 28 s and median +4 ± 8 s (within noise), X1 95th-percentile wait −12.7 ± 3.3 s.

The Z1 redirect cannot be implemented. Z1 and combos A, C, D, E, F: rerun pending (`ALL=1 ../run_5seeds_all.sh`).

Files: `compare_all_0700_0745.csv` (all KPIs, CIs, paired differences), `all_versions.json` (+ pooled values),
`charts/dist_<version>.png` (histogram + bell curve, baseline outline), each version's `results*_warm5/kpi_seeds.csv`.
Raw per-seed SUMO files are not in git (.gitignore). The earlier empty-start results (road empty at 07:00) were superseded and not kept.
