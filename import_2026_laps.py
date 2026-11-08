"""
import_2026_laps.py - build laps.csv from REAL 2026 race data (7 rounds) without needing the F1 servers.

Source: RACIM01/F1_Dashboard on GitHub (FastF1 lap export; semicolon CSV with comma decimals).
That export has no DRS, pit or track-status columns, so they are derived here:
  * PitOut  = first lap of a new stint; PitIn = last lap before a stint change.
  * TrackStatus '4' (neutralised) = lap whose field-median lap time is >12% slower than the race's
    typical lap (safety car / VSC / red-flag laps). Heuristic; check the printed lap list.
  * DRSOpen = "in range": car was within 1.0 s of the car ahead at the end of the previous lap.
    2026 cars have no DRS (active aero + electrical override instead), so this proxy stands in for
    the DRS term. Replace with real telemetry if you have it (see fetch_real_race.py).
Usage: python import_2026_laps.py [path/to/Data]   (downloads the repo zip if no path is given)
"""
import io, json, sys, urllib.request, zipfile
import numpy as np
import pandas as pd

if len(sys.argv) > 1:
    race_csv, races_csv = f"{sys.argv[1]}/Race.csv", f"{sys.argv[1]}/Races.csv"
else:
    url = "https://codeload.github.com/RACIM01/F1_Dashboard/zip/refs/heads/main"
    z = zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(url, timeout=60).read()))
    z.extractall("src_2026"); race_csv = "src_2026/F1_Dashboard-main/Data/Race.csv"
    races_csv = "src_2026/F1_Dashboard-main/Data/Races.csv"

R = pd.read_csv(race_csv, sep=";", decimal=",")
names = pd.read_csv(races_csv, sep=";")
names = names[names.Session == "Race"].set_index("Race_id")["RaceName"]
R = R[R.Race_id.isin(names.index)].copy()
R["Time"] = pd.to_timedelta(R["Time"]).dt.total_seconds()

out = []
for rid, g in R.groupby("Race_id"):
    g = g.sort_values(["Driver", "LapNumber"]).copy()
    nxt = g.groupby("Driver")["Stint"].shift(-1); prv = g.groupby("Driver")["Stint"].shift(1)
    g["PitIn"] = nxt.notna() & (nxt != g["Stint"])
    g["PitOut"] = prv.notna() & (prv != g["Stint"])
    med = g.groupby("LapNumber")["LapTimeSec"].median()
    ref = med.iloc[1:].median()
    slow = set(med.index[(med > 1.12 * ref) & (med.index > 1)])
    g["TrackStatus"] = np.where(g.LapNumber.isin(slow), "4", "1")
    g = g.sort_values(["LapNumber", "Position"])
    g["GapAhead"] = g.groupby("LapNumber")["Time"].diff().fillna(99.0).round(3)
    g = g.sort_values(["Driver", "LapNumber"])
    prev_gap = g.groupby("Driver")["GapAhead"].shift(1)
    g["DRSOpen"] = ((prev_gap < 1.0) & (g.LapNumber >= 3) & (g.TrackStatus == "1")
                    & ~g.PitIn & ~g.PitOut)
    g["Race"] = names[rid]
    print(f"{names[rid]}: {int(g.LapNumber.max())} laps, {g.Driver.nunique()} drivers, neutralised laps {sorted(int(x) for x in slow)}")
    out.append(g)

L = pd.concat(out)
laps = pd.DataFrame({
    "Race": L.Race, "Driver": L.Driver, "Team": L.Team, "LapNumber": L.LapNumber.astype(int),
    "Position": L.Position.astype(int), "Time": L.Time.round(3), "LapTime": L.LapTimeSec,
    "Compound": L.Compound.fillna("UNKNOWN").str.upper(), "TyreLife": L.TyreLife.fillna(1).astype(int),
    "PitIn": L.PitIn, "PitOut": L.PitOut, "TrackStatus": L.TrackStatus, "DRSOpen": L.DRSOpen, "GapAhead": L.GapAhead,
}).sort_values(["Race", "LapNumber", "Position"])
laps.to_csv("laps.csv", index=False)
json.dump({"label": "2026 season, rounds 1-7 (real FastF1 data)", "synthetic": False, "proxy_drs": True}, open("meta.json", "w"))
print("Wrote laps.csv:", len(laps), "rows")
