"""make_paper_pdf.py - builds TOE_paper.pdf (text matches the shared Doc) with figures from ./figures."""
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, KeepTogether, ListFlowable, ListItem

INK = colors.HexColor("#14233A")
B = ParagraphStyle("b", fontName="Times-Roman", fontSize=10.5, leading=14.5, spaceAfter=7)
T = ParagraphStyle("t", parent=B, fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=INK, spaceAfter=4)
N = ParagraphStyle("n", parent=B, fontName="Times-Italic", textColor=colors.HexColor("#5D6B80"), spaceAfter=10)
H1 = ParagraphStyle("h1", parent=B, fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=INK, spaceBefore=12, spaceAfter=5)
H2 = ParagraphStyle("h2", parent=H1, fontSize=11, spaceBefore=8)
F = ParagraphStyle("f", parent=B, fontName="Helvetica-Oblique", fontSize=8.5, leading=11, textColor=colors.HexColor("#5D6B80"), spaceAfter=10)
EQ = ParagraphStyle("eq", parent=B, fontName="Helvetica-Bold", fontSize=10, alignment=1, spaceBefore=4, spaceAfter=8)
P = lambda t, s=B: Paragraph(t, s)
def bl(items, kind="bullet"):
    return ListFlowable([ListItem(P(i), leftIndent=14) for i in items], bulletType=kind, leftIndent=14, bulletFontSize=9)
def fig(name, cap, w=5.6):
    from PIL import Image as PI
    iw, ih = PI.open(f"figures/{name}.png").size
    return KeepTogether([Image(f"figures/{name}.png", width=w*inch, height=w*inch*ih/iw), P(cap, F)])

S = []
S += [P("True Overtaking Efficiency: A Context-Weighted Passing Metric for Formula 1", T),
      P("Methods note. Empirical figures come from seven real 2026 Formula 1 races (FastF1 lap data). The DRS term uses a proxy, because 2026 cars have no DRS.", N)]
S += [P("Abstract", H1), P("Raw overtake counts reward cars that start out of position, drivers on fresher tires, and passes made with DRS open on a long straight. We propose True Overtaking Efficiency (TOE), a score that weights each clean on-track pass by DRS use, tire-age difference and tire-compound difference, and gives extra credit for defending against a car that holds an advantage. TOE can be computed entirely from free public data (FastF1 and OpenF1). We describe the metric, a reference implementation, and results on seven real 2026 races. Across 302 clean passes, the average pass was worth 0.57 points, and the defensive-hold term contributed 3.5 times as many points as passing. Season TOE rankings track defense points closely (Spearman 0.92) and are unrelated to net passes, so the hold rule, not passing, drives the ranking. We treat that as a design problem and list the calibration needed before TOE should be used to rank drivers.")]
S += [P("1. Motivation", H1),
      P("Overtaking is among the most visible driver skills and among the hardest to measure. A tally of positions gained conflates several things: the pace advantage of the car, the state of the tires, the aerodynamic help of DRS, and the starting position. A driver who passes five slower cars on old tires with DRS open has done something different from a driver who passes one equal car on equal tires without it, yet both tallies look like \"gains.\""),
      P("TOE is an attempt to put those contexts into one number using weights that are easy to state and easy to change. It is not a fitted model. It is a transparent scoring rule that makes the trade-offs explicit so they can be argued about and tuned.")]
S += [P("2. Data and pipeline", H1),
      P("The reference implementation uses lap-level data of the kind FastF1 provides: driver, lap number, end-of-lap position and session time, tire compound, tire age, pit-in and pit-out timestamps, track status, and a DRS flag derived from car telemetry (DRS channel value of 10 or higher is treated as open). The OpenF1 API exposes comparable positions, intervals and stints for a web-based implementation."),
      P("The scoring engine is deliberately independent of the data source. It takes a table of laps with a fixed set of columns, so the same code runs on FastF1 output or on simulated laps. The results below use a FastF1 lap export for the first seven 2026 rounds (Australia, China, Japan, Miami, Canada, Monaco and Barcelona), taken from a public GitHub repository (RACIM01/F1_Dashboard). We checked it against one official result: its Australian Grand Prix finishing order (Russell, Antonelli, Leclerc) matches the published classification. The export has no DRS, pit or track-status fields, so we derived them. Pit-in and pit-out laps come from stint changes. A lap counts as neutralised when the field's median lap time is more than 12% slower than the race norm. DRS is replaced by a proxy, because 2026 cars have no DRS: the attacker counts as in range if it was within 1.0 second of the car ahead at the end of the previous lap."),
      P("2.1 Detecting passes", H2),
      P("A pass is recorded on lap <i>N</i> when driver A was behind driver D at the end of lap <i>N-1</i> and ahead at the end of lap <i>N</i>. We then discard:"),
      bl(["Lap 1, where grid-slot chaos dominates.", "Any lap on which either car entered or left the pits.", "Any lap that was not fully green (yellow, safety car, virtual safety car, red flag).", "Any pair that was more than two positions apart on the previous lap, because such swaps are usually the product of other cars' pit stops."])]
S += [P("3. The metric", H1), P("For each clean pass, the value is:"),
      P("value = 1.0 - 0.4 x DRS + 0.05 x (age_att - age_def) + 0.3 x sign(hard_att - hard_def)", EQ),
      P("where DRS is 1 if the attacker had DRS open (for 2026 cars, which have no DRS: if it was within 1.0 second of the car ahead at the last detection) and 0 otherwise, ages are laps on the current set, and hardness is 1 for soft, 2 for medium and 3 for hard. The compound term is zero when the compounds match or when either car is on intermediates or wets. The intuition behind each term:"),
      bl(["<b>Base value (1.0).</b> Every clean pass counts.", "<b>DRS penalty (-0.4).</b> A DRS-assisted pass is easier, so it is discounted.", "<b>Tire age (+/-0.05 per lap).</b> Passing a car on fresher rubber while on older tires is harder and earns a bonus. Passing a car on older tires while on fresh ones is easier and is discounted.", "<b>Compound (+/-0.3).</b> Passing on a harder compound than the defender's is credited, and passing on a softer one is discounted."]),
      P("3.1 Defensive holds", H2),
      P("A driver earns 0.5 points for each lap in which they hold position and the car directly behind finishes the lap within 1.0 second while holding a tire or DRS advantage. A tire advantage means fresher tires or a softer compound. We treat any car within 1.0 second at the line as having a DRS advantage on the next lap."),
      P("A driver's TOE is the sum of their pass values plus their hold points. Net passes (passes made minus times passed) are reported alongside it.")]

rows = [["Race", "Clean passes", "Avg pass value", "Pass points", "Holds", "Hold points"],
 ["Australian", "41", "0.59", "24.15", "138", "69.0"], ["Chinese", "71", "0.43", "30.20", "158", "79.0"],
 ["Japanese", "45", "0.65", "29.20", "294", "147.0"], ["Miami", "57", "0.46", "26.45", "135", "67.5"],
 ["Canadian", "40", "0.73", "29.30", "120", "60.0"], ["Monaco", "8", "1.66", "13.30", "240", "120.0"],
 ["Barcelona", "40", "0.46", "18.55", "116", "58.0"], ["All races", "302", "0.57", "171.15", "1,201", "600.5"]]
tb = Table(rows, colWidths=[1.3*inch] + [1.05*inch]*5)
tb.setStyle(TableStyle([("FONT", (0,0), (-1,0), "Helvetica-Bold", 8.5), ("FONT", (0,1), (-1,-1), "Helvetica", 8.5),
    ("FONT", (0,-1), (-1,-1), "Helvetica-Bold", 8.5), ("BACKGROUND", (0,0), (-1,0), INK), ("TEXTCOLOR", (0,0), (-1,0), colors.white),
    ("ALIGN", (1,0), (-1,-1), "RIGHT"), ("LINEBELOW", (0,1), (-1,-2), .3, colors.HexColor("#D5DCE5")), ("LINEABOVE", (0,-1), (-1,-1), .8, INK),
    ("TOPPADDING", (0,0), (-1,-1), 3), ("BOTTOMPADDING", (0,0), (-1,-1), 3)]))
S += [P("4. Results on seven 2026 races", H1),
      P("Across seven 2026 races, the pipeline found 302 clean passes and 1,201 defensive holds. Pass points total 171.2 and hold points total 600.5, so holds are worth 3.5 times as much as passing."),
      tb, Spacer(1, 6), P("Table 1. Passes and holds by race at default weights.", F),
      fig("fig1_pass_vs_hold_by_race", "Figure 1. Pass points and hold points by race. Holds exceed passes in every race."),
      P("The main descriptive results, at default weights:"),
      bl(["<b>The average pass was worth 0.57 points.</b> 11% of passes scored below zero (Figure 4).",
          "<b>77% of passes were made in range.</b> In-range passes averaged 0.46 points. The 69 passes made out of range averaged 0.93.",
          "<b>Attackers were usually on fresher tires.</b> The tire-age term averaged -0.16 per pass, so it mostly acted as a discount. The compound term was non-zero in 34% of passes.",
          "<b>Verstappen led pass points (22.45) with 34 passes and a net gain of 24.</b> This fits his Australian Grand Prix, where he started 20th and finished sixth. Lap 1 is excluded by design, so his tally comes from later laps.",
          "<b>Defense decided the season ranking.</b> TOE correlates 0.92 (Spearman) with defense points, 0.29 with pass points and 0.00 with net passes. The top three by TOE (Gasly 56.75, Sainz 56.45, Lindblad 53.05) earned 48.0, 43.0 and 48.0 of those points from holds."]),
      fig("fig2_season_toe_top15", "Figure 2. Season TOE for the top 15 drivers, split into defense and pass points."),
      fig("fig3_toe_vs_net_passes", "Figure 3. Season TOE against net passes. The two are unrelated.", 4.8),
      P("One circuit shows the effect clearly. Monaco produced only 8 clean passes but 240 holds, so 120 of its points came from defending.")]
S += [P("5. Design critique", H1),
      P("<b>Defensive holds dominate under the specified rule.</b> Hold points exceed pass points in every race, from 2.0 times in Canada to 9.0 times in Monaco. Counting a hold only when the attacker has a real tire edge removes 825 of the 1,201 holds, leaving 188 points. That is close to the 171 points from passing, so a tire-edge rule or a lower hold value would restore balance (Figure 5)."),
      fig("fig5_hold_weight_sensitivity", "Figure 5. Rank agreement between TOE and net passes as the hold value falls from 0.5 to 0.", 4.8),
      P("<b>The range proxy is mostly a flat discount.</b> With 77% of passes in range, the DRS-style penalty separates few passes from the rest. On circuits and eras with real DRS the share will differ."),
      fig("fig4_pass_value_distribution", "Figure 4. Distribution of pass values, split by whether the attacker was in range.", 5.0),
      P("<b>Fresher tires are the norm for attackers.</b> The tire-age term averaged -0.16 per pass, so it usually lowers a pass's value instead of rewarding the hard ones."),
      P("<b>Opposite adjustments can cancel.</b> A hard-on-soft pass on old tires scores a compound bonus and an age bonus, while the same pass on fresh tires scores a compound bonus and an age discount. Whether additive weights are the right structure is an open question."),
      P("<b>The weights are not estimated.</b> The values 0.4, 0.05, 0.3 and 0.5 come from the specification. Nothing here shows they reflect real difficulty.")]
S += [P("6. Limitations", H1),
      bl(["<b>Lap-granularity detection.</b> Passes are inferred from end-of-lap order. A pass and repass within one lap is invisible, and a pass is dated to the lap in which it was completed.",
          "<b>Proxy for DRS.</b> The flag records whether the attacker started the lap within 1.0 second of the car ahead, not whether any assist was actually used.",
          "<b>Derived fields.</b> Pit laps come from stint changes and neutralised laps from a lap-time heuristic. Both can misclassify laps, for example under a virtual safety car or in changing weather.",
          "<b>Light verification.</b> We checked one race's finishing order against the published result. The other six races and all lap-by-lap values come from the source export unaudited.",
          "<b>Small sample.</b> Seven races from one season, with one circuit (Monaco) contributing 20% of all hold points.",
          "<b>Pit-cycle contamination.</b> The two-position filter reduces but does not eliminate positions gained through other cars' stops."], "1"),
      P("7. Future work", H1),
      bl(["<b>Calibration.</b> Fit pass-success probability against DRS, age delta, compound delta and pace gap, and derive weights from the coefficients.",
          "<b>Opportunity normalization.</b> Divide by laps spent within 1.0 second of a car ahead, so drivers are not rewarded or penalized for how often they get the chance.",
          "<b>Finer detection.</b> Use the distance-based telemetry channels to locate passes on track and to match DRS use to the pass zone.",
          "<b>Multi-race validation.</b> Extend beyond seven rounds and check whether TOE is stable from race to race, and whether it separates drivers beyond what team pace explains."]),
      P("8. Reproducibility", H1),
      P("The reference code, a seven-race 2026 dataset, an interactive dashboard and an Excel workbook with live formulas accompany this note. The workbook recalculates every pass value, hold and driver total from a Weights sheet, so any reader can change the weights and see the effect without running code."),
      P("Data sources", H1),
      bl(["FastF1, an open-source Python library for Formula 1 timing and telemetry data.", "OpenF1, a free API of historical and live Formula 1 data.", "RACIM01/F1_Dashboard on GitHub, the FastF1 lap export used for the 2026 results."])]

def foot(c, d):
    c.saveState(); c.setFont("Helvetica", 8); c.setFillColor(colors.HexColor("#5D6B80"))
    c.drawCentredString(letter[0]/2, 0.5*inch, f"True Overtaking Efficiency  |  {d.page}"); c.restoreState()
SimpleDocTemplate("TOE_paper.pdf", pagesize=letter, leftMargin=1*inch, rightMargin=1*inch, topMargin=.9*inch, bottomMargin=.9*inch,
                  title="True Overtaking Efficiency", author="").build(S, onFirstPage=foot, onLaterPages=foot)
