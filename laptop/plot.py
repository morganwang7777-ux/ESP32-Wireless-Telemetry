"""Graphs for the range test. Reads results/telemetry.db, saves 3 PNGs into results/."""
import re
import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt

OPEN = "#2a78d6"     # line of sight
DOOR = "#eb6834"     # behind the door
TEXT = "#0b0b0b"
GREY = "#52514e"
GRID = "#e1e0d9"
BG = "#fcfcfb"

plt.rcParams.update({
    "figure.facecolor": BG, "axes.facecolor": BG,
    "axes.edgecolor": "#c3c2b7", "axes.labelcolor": TEXT,
    "xtick.color": GREY, "ytick.color": GREY,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.axisbelow": True, "font.size": 11,
})

RESULTS = Path(__file__).resolve().parent.parent / "results"
db = sqlite3.connect(RESULTS / "telemetry.db")

# one row per run: received, expected (from seq numbers), average rssi
runs = db.execute("""
    SELECT r.id, r.note,
           COUNT(s.seq)                AS received,
           MAX(s.seq) - MIN(s.seq) + 1 AS expected,
           AVG(s.rssi)                 AS avg_rssi
    FROM runs r JOIN samples s ON s.run_id = r.id
    GROUP BY r.id
""").fetchall()

# group repeats together: "10m_door_b" -> "10m_door"
tests = {}
for run_id, note, received, expected, avg_rssi in runs:
    test = re.sub(r"_[a-z]\d*$", "", note)
    loss = 100 * (expected - received) / expected
    tests.setdefault(test, []).append((loss, avg_rssi, received, expected, run_id))

order = ["2m", "5m", "10m", "15m", "5m_door", "10m_door"]
order = [t for t in order if t in tests]


def label(test):
    return test.replace("_door", "\n+ door")


def is_door(test):
    return "door" in test


# graph 1: average loss per test, with a line from best to worst run
fig, ax = plt.subplots(figsize=(8, 4.5))
for i, t in enumerate(order):
    tries = tests[t]
    avg = 100 * sum(e - r for _, _, r, e, _ in tries) / sum(e for _, _, _, e, _ in tries)
    lo = min(x[0] for x in tries)
    hi = max(x[0] for x in tries)
    ax.bar(i, avg, width=0.6, color=DOOR if is_door(t) else OPEN)
    ax.plot([i, i], [lo, hi], color=TEXT, linewidth=1.5)           # best-to-worst range
    ax.plot([i - 0.08, i + 0.08], [hi, hi], color=TEXT, linewidth=1.5)
    ax.plot([i - 0.08, i + 0.08], [lo, lo], color=TEXT, linewidth=1.5)
    ax.annotate(f"{avg:.1f}%", (i, hi), xytext=(0, 6), textcoords="offset points",
                ha="center", color=TEXT, fontsize=10)
ax.set_ylim(0, max(max(x[0] for x in tests[t]) for t in order) * 1.15)
ax.set_xticks(range(len(order)), [label(t) for t in order])
ax.set_ylabel("Packets lost (%)")
ax.set_title("Packet loss by distance (average of 3 runs, line = best to worst)",
             loc="left", color=TEXT, fontsize=12)
ax.bar(0, 0, color=OPEN, label="Line of sight")
ax.bar(0, 0, color=DOOR, label="Behind closed door")
ax.legend(frameon=False, loc="upper left")
fig.tight_layout()
fig.savefig(RESULTS / "graph1_loss_by_distance.png", dpi=200)
plt.close(fig)

# graph 2: loss vs signal, one dot per run
fig, ax = plt.subplots(figsize=(8, 4.5))
for t in order:
    xs = [x[1] for x in tests[t]]
    ys = [x[0] for x in tests[t]]
    ax.scatter(xs, ys, s=70, color=DOOR if is_door(t) else OPEN,
               edgecolors=BG, linewidths=1.5, zorder=3)
ax.axvline(-80, color=GREY, linestyle="--", linewidth=1)
ax.annotate("loss rises sharply\nbelow -80 dBm", (-80, 55), xytext=(8, 0),
            textcoords="offset points", ha="left", color=GREY, fontsize=10)
ax.set_xlabel("Average signal strength, RSSI (dBm)  -  stronger to the right")
ax.set_ylabel("Packets lost (%)")
ax.set_title("Weaker signal, more loss (each dot is one 30 s run)",
             loc="left", color=TEXT, fontsize=12)
ax.scatter([], [], s=70, color=OPEN, label="Line of sight")
ax.scatter([], [], s=70, color=DOOR, label="Behind closed door")
ax.legend(frameon=False, loc="upper right")
fig.tight_layout()
fig.savefig(RESULTS / "graph2_loss_vs_signal.png", dpi=200)
plt.close(fig)

# graph 3: packets per second in the worst run, to show the dropouts
worst = max(runs, key=lambda r: (r[3] - r[2]) / r[3])
worst_id, worst_note = worst[0], worst[1]
seqs = [row[0] for row in db.execute(
    "SELECT seq FROM samples WHERE run_id = ? ORDER BY seq", (worst_id,))]
t_ms = [row[0] for row in db.execute(
    "SELECT t_ms FROM samples WHERE run_id = ? ORDER BY seq", (worst_id,))]
start = t_ms[0]
seconds = int((t_ms[-1] - start) / 1000) + 1
per_second = [0] * seconds
for t in t_ms:
    per_second[int((t - start) / 1000)] += 1
send_rate = (seqs[-1] - seqs[0]) / ((t_ms[-1] - start) / 1000)

fig, ax = plt.subplots(figsize=(8, 4.5))
ax.bar(range(seconds), per_second, width=0.8, color=DOOR)
ax.axhline(send_rate, color=TEXT, linestyle="--", linewidth=1)
ax.annotate(f"sent: {send_rate:.1f} per second", (seconds - 0.5, send_rate),
            xytext=(0, 5), textcoords="offset points", ha="right", color=TEXT, fontsize=10)
ax.set_xlabel("Time into run (s)")
ax.set_ylabel("Packets received per second")
ax.set_title(f"Worst run ({worst_note}): losses come in bursts, not evenly",
             loc="left", color=TEXT, fontsize=12)
fig.tight_layout()
fig.savefig(RESULTS / "graph3_dropouts_worst_run.png", dpi=200)
plt.close(fig)

print("Saved graph1_loss_by_distance.png, graph2_loss_vs_signal.png, graph3_dropouts_worst_run.png")