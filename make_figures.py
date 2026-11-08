"""make_figures.py - PNG charts from passes.csv / holds.csv / summary.csv (run after run_pipeline.py)."""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np, pandas as pd
from scipy.stats import spearmanr

p, h, s = pd.read_csv("passes.csv"), pd.read_csv("holds.csv"), pd.read_csv("summary.csv")
INK, TEAL, BLUE, RED, GREY = "#14233A", "#0F8B8D", "#3D5A80", "#C1352F", "#9AA5B4"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": INK, "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK, "figure.dpi": 100})
short = lambda r: r.replace(" Grand Prix", "")
def save(fig, name): fig.tight_layout(); fig.savefig(f"figures/{name}.png", dpi=200); plt.close(fig)

# 1. pass vs hold points per race
r = p.groupby("Race").score.sum().to_frame("pass").join(h.groupby("Race").score.sum().rename("hold"))
r.index = [short(i) for i in r.index]; r = r.sort_values("hold", ascending=False)
fig, ax = plt.subplots(figsize=(8, 4.2)); x = np.arange(len(r)); w = .38
ax.bar(x - w/2, r["pass"], w, color=TEAL, label="Pass points"); ax.bar(x + w/2, r["hold"], w, color=BLUE, label="Defensive hold points")
for i, (a, b) in enumerate(zip(r["pass"], r["hold"])):
    ax.text(i - w/2, a + 2, f"{a:.0f}", ha="center", fontsize=8); ax.text(i + w/2, b + 2, f"{b:.0f}", ha="center", fontsize=8)
ax.set_xticks(x); ax.set_xticklabels(r.index); ax.set_ylabel("Points at default weights"); ax.legend(frameon=False)
ax.set_title("Defensive holds out-score passing in every race (Monaco: 9x)", loc="left", fontweight="bold", color=INK)
save(fig, "fig1_pass_vs_hold_by_race")

# 2. season leaderboard stacked
t = s.sort_values("TOE", ascending=False).head(15).iloc[::-1]
fig, ax = plt.subplots(figsize=(8, 5.4))
pp = t.PassPoints.clip(lower=0)
ax.barh(t.Driver, t.DefensePoints, color=BLUE, label="Defense points")
ax.barh(t.Driver, pp, left=t.DefensePoints, color=TEAL, label="Pass points")
for i, (d, a, b) in enumerate(zip(t.Driver, t.DefensePoints, t.PassPoints)): ax.text(a + pp.iloc[i] + .6, i, f"{a+b:.1f}", va="center", fontsize=8)
ax.set_xlabel("Season TOE (7 races, default weights)"); ax.legend(frameon=False, loc="lower right")
ax.set_title("Top 15 by TOE: most of the score is defending", loc="left", fontweight="bold", color=INK)
save(fig, "fig2_season_toe_top15")

# 3. TOE vs net passes
fig, ax = plt.subplots(figsize=(7, 5))
ax.scatter(s.NetPasses, s.TOE, color=TEAL, s=36, zorder=3)
for r_ in s.itertuples():
    if r_.TOE > 42 or abs(r_.NetPasses) > 15: ax.annotate(r_.Driver, (r_.NetPasses, r_.TOE), xytext=(4, 3), textcoords="offset points", fontsize=8)
rho = spearmanr(s.NetPasses, s.TOE)[0]
ax.axvline(0, color=GREY, lw=.8); ax.set_xlabel("Net passes (made minus times passed)"); ax.set_ylabel("Season TOE")
ax.set_title(f"TOE does not track net passes (Spearman {rho:.2f})", loc="left", fontweight="bold", color=INK)
save(fig, "fig3_toe_vs_net_passes")

# 4. pass value distribution
fig, ax = plt.subplots(figsize=(8, 4)); bins = np.arange(-1.2, 2.45, .1)
ax.hist([p[p.drs == 1].score, p[p.drs == 0].score], bins=bins, stacked=True, color=[BLUE, TEAL], label=["In range (within 1.0 s)", "Out of range"])
ax.axvline(0, color=RED, lw=1); ax.axvline(p.score.mean(), color=INK, ls="--", lw=1)
ax.text(p.score.mean() + .03, ax.get_ylim()[1] * .92, f"mean {p.score.mean():.2f}", fontsize=8)
ax.set_xlabel("Pass value (points)"); ax.set_ylabel("Passes"); ax.legend(frameon=False)
ax.set_title("302 clean passes: most are worth well under 1.0", loc="left", fontweight="bold", color=INK)
save(fig, "fig4_pass_value_distribution")

# 5. sensitivity: hold weight vs rank agreement with net passes
rows = []
for edge_only in (False, True):
    hh = h[h.tire_edge] if edge_only else h
    hold_n = hh.groupby("defender").size()
    for wgt in np.arange(0, 0.55, .05):
        toe = s.set_index("Driver").PassPoints + hold_n.reindex(s.Driver).fillna(0).values * wgt
        rows.append((edge_only, wgt, spearmanr(toe, s.set_index("Driver").NetPasses)[0]))
d = pd.DataFrame(rows, columns=["edge", "w", "rho"])
fig, ax = plt.subplots(figsize=(7, 4.2))
for e, c, lab in ((False, BLUE, "All holds"), (True, TEAL, "Tire-edge holds only")):
    q = d[d.edge == e]; ax.plot(q.w, q.rho, color=c, marker="o", ms=4, label=lab)
ax.set_xlabel("Defensive hold value (points per lap)"); ax.set_ylabel("Spearman: TOE vs net passes"); ax.legend(frameon=False)
ax.set_title("Lower hold values bring TOE back toward passing", loc="left", fontweight="bold", color=INK)
save(fig, "fig5_hold_weight_sensitivity")
print(d.pivot(index="w", columns="edge", values="rho").round(2).to_string())
