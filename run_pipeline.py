"""
run_pipeline.py - laps.csv (one or many races; real or synthetic) -> CSVs, dashboard, Excel.
    python run_pipeline.py
"""
import json, os, subprocess, sys
import pandas as pd
from toe_engine import Weights, compute_toe, summarise

laps = pd.read_csv("laps.csv")
if "Race" not in laps: laps["Race"] = "Race"
for c in ("PitIn", "PitOut", "DRSOpen"):
    laps[c] = laps[c].astype(bool)
laps["TrackStatus"] = laps["TrackStatus"].astype(str)
meta = json.load(open("meta.json")) if os.path.exists("meta.json") else {"label": "Synthetic race", "synthetic": True}
w = Weights()

P, H, ALL, order = [], [], [], list(dict.fromkeys(laps.Race))
for race in order:
    lg = laps[laps.Race == race]
    p, h = compute_toe(lg.drop(columns="Race"), w)
    p.insert(0, "Race", race); h.insert(0, "Race", race); P.append(p); H.append(h)
    sc = sorted(int(n) for n, g in lg.groupby("LapNumber") if g.TrackStatus.ne("1").mean() > 0.5)
    drv = lg.drop_duplicates("Driver")[["Driver", "Team"]]
    ALL.append(dict(
        label=race, nLaps=int(lg.LapNumber.max()), scLaps=sc,
        drivers=[dict(code=a, team=b) for a, b in drv.itertuples(index=False)],
        laps=[[r.Driver, int(r.LapNumber), int(r.Position), str(r.Compound)[0], int(r.TyreLife), int(r.PitIn),
               int(r.PitOut), int(r.DRSOpen), round(float(r.GapAhead), 2)] for r in lg.itertuples()],
        passes=p[["lap", "attacker", "defender", "drs", "att_comp", "def_comp", "att_age", "def_age"]]
            .assign(drs=lambda x: x.drs.astype(int)).values.tolist(),
        holds=h[["lap", "defender", "attacker", "gap_s", "tire_edge"]]
            .assign(tire_edge=lambda x: x.tire_edge.astype(int)).values.tolist()))
passes, holds = pd.concat(P), pd.concat(H)
passes.to_csv("passes.csv", index=False); holds.to_csv("holds.csv", index=False)
season = summarise(passes, holds)
team = laps.drop_duplicates("Driver", keep="last").set_index("Driver")["Team"]
season.insert(1, "Team", season.Driver.map(team))
season.to_csv("summary.csv", index=False)

if meta["synthetic"]:
    note = "Synthetic race with fictional drivers, not real F1 data."
else:
    note = f"Real data: {meta['label']}."
    if meta.get("proxy_drs"):
        note += " 2026 cars have no DRS, so the DRS term applies when the attacker was within 1.0 s of the car ahead at the last detection."
html = (open("dashboard_template.html").read()
        .replace("__DATA__", json.dumps(ALL, separators=(",", ":"))).replace("__NOTE__", note))
open("toe_dashboard.html", "w").write(html)
subprocess.run([sys.executable, "build_xlsx.py"], check=True)
print(season.head(12).to_string(index=False))
print(f"\n{len(passes)} passes, {len(holds)} holds across {len(order)} race(s).")
