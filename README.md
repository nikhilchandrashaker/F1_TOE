# True Overtaking Efficiency (TOE)

A passing stat for Formula 1 that asks not just *how many* overtakes a driver made, but *how hard they were*. Each clean on-track pass is weighted by DRS, tire age and tire compound, and drivers earn extra credit for defending against cars with an advantage.

Built on free public data ([FastF1](https://docs.fastf1.dev) or the [OpenF1 API](https://openf1.org)). No proprietary team data needed.

> **Data.** The bundled results use **real FastF1 lap data for the first seven 2026 races** (Australia, China, Japan, Miami, Canada, Monaco, Barcelona), imported from a public GitHub export by `import_2026_laps.py`. That export has no DRS, pit or track-status fields, so the importer derives them (see Known limitations). 2026 cars have no DRS, so the DRS term uses a proxy: the attacker was within 1.0 s of the car ahead at the end of the previous lap. One race's finishing order (Australia) was checked against the official result; the rest is unaudited.

## The formula

For every clean pass:

| Term | Value | Condition |
|---|---|---|
| Base | +1.0 | Any clean on-track pass |
| DRS penalty | −0.4 | Attacker had DRS open |
| Tire age | ±0.05 per lap | + per lap the attacker's tires are *older* than the defender's, − per lap if *fresher* |
| Compound | ±0.3 | + for a harder compound passing a softer one, − for softer passing harder |

For every lap a driver keeps position with a car within 1.0 s that holds a tire or DRS advantage: **+0.5**.

```
pass_value = 1.0 − 0.4·[DRS] + 0.05·(att_age − def_age) + 0.3·sign(att_hardness − def_hardness)
TOE        = Σ pass_value (passes made) + 0.5 · (defensive holds)
```

Hardness: SOFT = 1, MEDIUM = 2, HARD = 3. Intermediates and wets get no compound adjustment.

**Excluded:** Lap 1, any lap with a pit-in or pit-out for either car, any non-green lap (yellow, SC, VSC, red), and "passes" between cars more than two grid slots apart on the previous lap (usually pit-cycle reshuffles).

## What's in the box

| File | What it is |
|---|---|
| `import_2026_laps.py` | Builds `laps.csv` for the seven real 2026 races from the public export. No F1 servers needed. |
| `fetch_real_race.py` | Pulls any other race with FastF1 (real DRS from telemetry) and writes `laps.csv` and `meta.json`. |
| `run_pipeline.py` | Turns `laps.csv` (real or synthetic) into the CSVs, `toe_dashboard.html` and `toe_dataset.xlsx`. |
| `dashboard_template.html` | Dashboard shell that `run_pipeline.py` fills with data. |
| `true_overtaking_efficiency.py` | Standalone one-file version for a quick terminal table on a real session. |
| `toe_engine.py` | The same scoring logic as a pure-pandas engine (no FastF1 dependency). |
| `simulate_race.py` | Synthetic 57-lap race that writes `laps.csv`, `passes.csv`, `holds.csv`, `summary.csv`, `dashboard_data.json`. |
| `build_xlsx.py` | Builds `toe_dataset.xlsx` from those CSVs. |
| `toe_dashboard.html` | Interactive dashboard: leaderboard, lap-by-lap race replay, pass log, live weight sliders. |
| `toe_dataset.xlsx` | Workbook with live formulas. Edit the yellow cells on **Weights** and everything recalculates. |
| `TOE_paper` | Short methods paper (shared as a document). |

## Quick start

```bash
pip install pandas openpyxl

# The seven real 2026 races (downloads the public export)
python import_2026_laps.py
python run_pipeline.py        # CSVs, toe_dashboard.html (race picker), toe_dataset.xlsx

# Any other race, with real DRS telemetry (needs fastf1)
pip install fastf1
python fetch_real_race.py 2024 Monza R
python run_pipeline.py

# Synthetic demo (no network)
python simulate_race.py && python run_pipeline.py
```

Open `toe_dashboard.html` in a browser. The workbook has Season, Races, Passes, Holds and Laps sheets, all driven by the Weights sheet.

## Known limitations

1. **Lap-granularity detection.** Passes come from end-of-lap order, so a pass-and-repass inside one lap is invisible and a pass can land on the lap it finished rather than where it happened. For sharper detection use `Distance`/`RelativeDistance` telemetry or OpenF1 `position` and `intervals`.
2. **DRS is a proxy on 2026 data** (no DRS exists on 2026 cars): within 1.0 s of the car ahead at the last detection. With FastF1 telemetry it is "DRS open anywhere on the attacker's lap," not strictly in the pass zone.
   - **Derived fields in the 2026 import:** pit-in/out laps come from stint changes, and neutralised laps from a field-median lap time more than 12% over the race norm. Both are heuristics; the importer prints the flagged laps for review.
3. **Defensive holds dominate.** On the seven real races, hold points (600.5) are 3.5 times pass points (171.2), and season TOE correlates 0.92 with defense points but 0.00 with net passes (Spearman). Counting only holds with a tire edge cuts hold points to 188. Treat the hold weight as a tuning parameter before ranking drivers.
4. **Weights are specified, not fitted.** The 0.4 / 0.05 / 0.3 / 0.5 values come from the original spec. Nothing here validates them against real outcomes.
5. **Tire age** uses FastF1's `TyreLife`, which can include laps from used sets, not strictly laps in the current stint.

## Ideas for next steps

- Calibrate weights from real data (for example, regress pass success probability on DRS, age delta and compound delta).
- Normalise TOE by opportunity (laps spent within 1.0 s of a car ahead).
- Compare across circuits, since DRS-heavy tracks inflate raw pass counts.
