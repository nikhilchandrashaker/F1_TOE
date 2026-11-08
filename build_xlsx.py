"""Builds toe_dataset.xlsx (live formulas) from laps/passes/holds/summary CSVs. Multi-race aware."""
import json, os
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

META = json.load(open("meta.json")) if os.path.exists("meta.json") else {"label": "Synthetic race", "synthetic": True}
laps, passes, holds, summ = (pd.read_csv(f) for f in ("laps.csv", "passes.csv", "holds.csv", "summary.csv"))
if "Race" not in laps: laps.insert(0, "Race", "Race")
races = list(dict.fromkeys(laps.Race))
F, FB = Font(name="Arial", size=10), Font(name="Arial", size=10, bold=True)
BLUE = Font(name="Arial", size=10, color="0000FF")
HDR = PatternFill("solid", fgColor="14233A"); HF = Font(name="Arial", size=10, bold=True, color="FFFFFF")
YEL = PatternFill("solid", fgColor="FFFF00")
wb = Workbook()

def header(ws, cols, widths=None):
    ws.append(cols)
    for c in ws[1]:
        c.font, c.fill, c.alignment = HF, HDR, Alignment(horizontal="center", wrap_text=True)
    ws.freeze_panes = "A2"
    for i in range(1, len(cols) + 1):
        ws.column_dimensions[get_column_letter(i)].width = (widths or {}).get(i, 13)

def fmt(ws, nrows, ncols, bold=()):
    for row in ws.iter_rows(min_row=2, max_row=nrows, max_col=ncols):
        for c in row: c.font = FB if c.column in bold else F

# ---- Notes
n = wb.active; n.title = "Notes"
src = ("DATA SOURCE: synthetic (simulate_race.py). Fictional drivers and teams. Not real F1 results." if META["synthetic"]
       else f"DATA SOURCE: real FastF1 lap data - {META['label']}. Source export: RACIM01/F1_Dashboard on GitHub (import_2026_laps.py).")
lines = [["True Overtaking Efficiency (TOE) dataset"], [src],
 ["Edit the yellow cells on the Weights sheet; Season, Races, Passes and Holds recalculate."],
 ["Pass value = Base - DRS penalty (if in range) + age weight x (attacker tire age - defender tire age) + compound weight x sign(attacker hardness - defender hardness)."],
 ["Hardness: SOFT=1, MEDIUM=2, HARD=3. Harder attacker on softer defender = bonus; softer on harder = penalty."],
 ["Defensive hold: defender keeps position with the attacker within the hold window at the line; credited per lap."],
 ["Excluded: Lap 1, any lap with a pit-in or pit-out, neutralised laps, passes between cars more than 2 grid slots apart on the prior lap."]]
if META.get("proxy_drs"):
    lines += [["DRS PROXY: 2026 cars have no DRS. 'In range' = within 1.0 s of the car ahead at the end of the previous lap (detection-style proxy)."],
              ["DERIVED FIELDS: pit-in/out inferred from stint changes; neutralised laps inferred from field median lap time >12% over the race norm. Both are heuristics."]]
lines += [["Limitation: passes come from end-of-lap order, so within-lap swaps are invisible."]]
for r in lines: n.append(r)
n["A1"].font = Font(name="Arial", size=14, bold=True)
for r in range(2, len(lines) + 1): n.cell(r, 1).font = F
n.column_dimensions["A"].width = 160

# ---- Weights
w = wb.create_sheet("Weights")
header(w, ["Parameter", "Value", "Meaning"], {1: 26, 2: 10, 3: 70})
for r in [["Base value", 1.0, "Points per clean on-track pass"], ["DRS / in-range penalty", 0.4, "Subtracted when attacker was in range"],
          ["Tire age per lap", 0.05, "Per lap attacker's tires are older than defender's (negative if fresher)"],
          ["Compound softness", 0.3, "Bonus passing on a harder compound, penalty on a softer one"],
          ["Defensive hold value", 0.5, "Points per lap a hold is counted"], ["Hold window (s)", 1.0, "Max gap at the line for a hold to count"],
          ["Tire edge only (1/0)", 0, "1 = count holds only when the attacker has a tire edge"]]:
    w.append(r)
for r in range(2, 9):
    w.cell(r, 1).font = F; w.cell(r, 3).font = F; w.cell(r, 2).font = BLUE; w.cell(r, 2).fill = YEL
w["A10"] = "Blue on yellow = editable inputs. Defaults come from the TOE specification."; w["A10"].font = F

# ---- Passes (A Race, B Lap, C Att, D Def, E InRange, F AttComp, G DefComp, H AttAge, I DefAge, J Base ... P Value)
p = wb.create_sheet("Passes")
header(p, ["Race", "Lap", "Attacker", "Defender", "In range (1/0)", "Att compound", "Def compound", "Att tire age", "Def tire age",
           "Base", "Range adj", "Age adj", "Att hardness", "Def hardness", "Compound adj", "Pass value"], {1: 22, 6: 14, 7: 14})
for i, r in enumerate(passes.itertuples(), 2):
    p.append([r.Race, r.lap, r.attacker, r.defender, int(r.drs), r.att_comp, r.def_comp, r.att_age, r.def_age,
              "=Weights!$B$2", f"=-E{i}*Weights!$B$3", f"=Weights!$B$4*(H{i}-I{i})",
              f'=IF(F{i}="SOFT",1,IF(F{i}="MEDIUM",2,IF(F{i}="HARD",3,0)))',
              f'=IF(G{i}="SOFT",1,IF(G{i}="MEDIUM",2,IF(G{i}="HARD",3,0)))',
              f"=IF(OR(M{i}=0,N{i}=0),0,Weights!$B$5*SIGN(M{i}-N{i}))", f"=J{i}+K{i}+L{i}+O{i}"])
NP = len(passes) + 1; fmt(p, NP, 16, bold=(16,))

# ---- Holds (A Race, B Lap, C Def, D Att, E Gap, F Edge, G Counted, H Points)
h = wb.create_sheet("Holds")
header(h, ["Race", "Lap", "Defender", "Attacker", "Gap at line (s)", "Tire edge (1/0)", "Counted (1/0)", "Hold points"], {1: 22})
for i, r in enumerate(holds.itertuples(), 2):
    h.append([r.Race, r.lap, r.defender, r.attacker, r.gap_s, int(r.tire_edge),
              f"=IF(AND(E{i}<=Weights!$B$7,OR(Weights!$B$8=0,F{i}=1)),1,0)", f"=G{i}*Weights!$B$6"])
NH = len(holds) + 1; fmt(h, NH, 8)

# ---- Season
s = wb.create_sheet("Season", 1)
header(s, ["Driver", "Team", "Passes made", "Times passed", "Net passes", "Pass points", "Defense points", "TOE", "Avg pass value", "Rank"], {2: 16})
nd = len(summ)
for i, r in enumerate(summ.itertuples(), 2):
    d = r.Driver
    s.append([d, r.Team, f"=COUNTIF(Passes!$C$2:$C${NP},A{i})", f"=COUNTIF(Passes!$D$2:$D${NP},A{i})", f"=C{i}-D{i}",
              f"=SUMIF(Passes!$C$2:$C${NP},A{i},Passes!$P$2:$P${NP})", f"=SUMIF(Holds!$C$2:$C${NH},A{i},Holds!$H$2:$H${NH})",
              f"=F{i}+G{i}", f"=IF(C{i}=0,0,F{i}/C{i})", f"=RANK(H{i},$H$2:$H${nd+1})"])
fmt(s, nd + 1, 10, bold=(1, 8))
for row in s.iter_rows(min_row=2, max_row=nd + 1, min_col=6, max_col=9):
    for c in row: c.number_format = "0.00;[Red]-0.00;0.00"
s.cell(nd + 3, 1, "Season totals across all races loaded. Rows ordered by TOE at default weights; Rank updates with the weights.").font = F

# ---- Races
rc = wb.create_sheet("Races", 2)
header(rc, ["Race", "Passes", "Avg pass value", "Pass points", "Holds counted", "Hold points", "Hold points / pass points", "Passes in range (%)", "Negative-value passes (%)"], {1: 24})
for i, rn in enumerate(races, 2):
    rc.append([rn, f"=COUNTIF(Passes!$A$2:$A${NP},A{i})", f"=IF(B{i}=0,0,D{i}/B{i})",
               f"=SUMIF(Passes!$A$2:$A${NP},A{i},Passes!$P$2:$P${NP})", f"=SUMIF(Holds!$A$2:$A${NH},A{i},Holds!$G$2:$G${NH})",
               f"=SUMIF(Holds!$A$2:$A${NH},A{i},Holds!$H$2:$H${NH})", f"=IF(D{i}<=0,0,F{i}/D{i})",
               f"=IF(B{i}=0,0,SUMIF(Passes!$A$2:$A${NP},A{i},Passes!$E$2:$E${NP})/B{i})",
               f"=IF(B{i}=0,0,COUNTIFS(Passes!$A$2:$A${NP},A{i},Passes!$P$2:$P${NP},\"<0\")/B{i})"])
fmt(rc, len(races) + 1, 9, bold=(1,))
for row in rc.iter_rows(min_row=2, max_row=len(races) + 1):
    for c in row[2:4] + row[5:7]: c.number_format = "0.00"
    for c in row[7:9]: c.number_format = "0%"
t = len(races) + 2
rc.cell(t, 1, "All races").font = FB
for c, col in ((2, "B"), (4, "D"), (5, "E"), (6, "F")):
    rc.cell(t, c, f"=SUM({col}2:{col}{t-1})").font = FB
rc.cell(t, 3, f"=IF(B{t}=0,0,D{t}/B{t})").font = FB
rc.cell(t, 7, f"=IF(D{t}<=0,0,F{t}/D{t})").font = FB
for c in (3, 4, 6, 7): rc.cell(t, c).number_format = "0.00"

# ---- Laps
l = wb.create_sheet("Laps")
cols = [c for c in ["Race", "Driver", "Team", "LapNumber", "Position", "Time", "LapTime", "Compound", "TyreLife", "PitIn", "PitOut", "TrackStatus", "DRSOpen", "GapAhead"] if c in laps]
header(l, cols, {1: 22})
for r in laps[cols].itertuples(index=False):
    l.append([x.item() if hasattr(x, "item") else x for x in r])
fmt(l, len(laps) + 1, len(cols))
wb.save("toe_dataset.xlsx")
