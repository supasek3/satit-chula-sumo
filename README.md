# Satit Chula SUMO project — handoff package

Everything needed to continue the Satit Chula drop-off / pedestrian-crossing simulation:
the frozen baseline, two further versions with results, the data, and full documentation.

## 1. Install (once)
1. **Eclipse SUMO 1.28** — https://eclipse.dev/sumo/ (make sure `sumo`, `sumo-gui`, `netconvert`, `netedit` work in a terminal).
2. **Python 3** with: `pip install pyproj pillow`
3. **Set `SUMO_HOME`** to your SUMO install folder if you are not on a Mac with the standard installer, e.g.
   - Linux: `export SUMO_HOME=/usr/share/sumo`
   - Windows: `setx SUMO_HOME "C:\Program Files (x86)\Eclipse\Sumo"`

## 2. Continue with Claude
- **Claude Code (recommended):** open this folder as the working directory (`cd SatitChula_SUMO_handoff` then `claude`,
  or open the folder in the Claude desktop app's Code tab). Claude automatically reads `CLAUDE.md`, which tells it
  to read `HANDOFF.md` first. Then just say what you want to do next.
- **Claude chat (claude.ai):** upload `CLAUDE.md`, `HANDOFF.md` and the files you want to change, and start with
  "Read CLAUDE.md and HANDOFF.md, then help me continue this project."

## 3. Quick check that it works
```
cd baseline
python3 guard_control.py 1 --gui
```
Press ▶ in the window. You should see the OpenStreetMap background, cars, and magenta pedestrians.

## 4. What is where
| Path | What |
|---|---|
| `CLAUDE.md` | Briefing and rules for Claude |
| `HANDOFF.md` | Full project handoff (network, data, controllers, results, decisions, next steps) |
| `baseline/` | Frozen baseline model + 10-seed results + `components/` (how it was built) |
| `baseline_officer/` | Variant: traffic officer at the gate crossing |
| `scenario_webster_soi11/` | Scenario: Webster signal + 30% of drop-offs sent to Soi 11 (+ `variants/`) |
| `reference/` | Working log, the AnyLogic Webster logic PDF, the AnyLogic data register and schema |

Map data © OpenStreetMap contributors.
