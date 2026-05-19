import re
import sys
import os
import argparse
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# ─────────────────────────────────────────────
# CONFIG DETECTION
# ─────────────────────────────────────────────
RUN_REGEX = re.compile(r"run(\d+)", re.IGNORECASE)

def get_run_id(name):
    m = RUN_REGEX.search(name)
    return int(m.group(1)) if m else None


def node_type(h):
    if h.startswith("p"): return "Pedestrian"
    if h.startswith("c"): return "Car"
    if h.startswith("w"): return "WiFi"
    if h.startswith("t"): return "Tram"
    return "Other"


# ─────────────────────────────────────────────
# FILE COLLECTION
# ─────────────────────────────────────────────
def collect_files(path):
    p = Path(path)
    files = list(p.glob("*BatteryReport*.txt")) if p.is_dir() else list(Path().glob(path))

    grouped = {}
    for f in files:
        rid = get_run_id(f.name)
        if rid is not None:
            grouped[rid] = f

    return [grouped[k] for k in sorted(grouped.keys())]


# ─────────────────────────────────────────────
# PARSER
# ─────────────────────────────────────────────
def parse_file(fp):
    nodes = []

    pattern = re.compile(
        r"^(\S+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)%\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+(\w+)"
    )

    with open(fp, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = pattern.match(line.strip())
            if not m:
                continue

            nodes.append({
                "host": m.group(1),
                "initial": float(m.group(3)),
                "remaining": float(m.group(2)),
                "pct": float(m.group(4)),
                "rx": float(m.group(6)),
                "scan": float(m.group(7)),
                "dead": m.group(8).lower() == "dead",
                "type": node_type(m.group(1))
            })

    return nodes


# ─────────────────────────────────────────────
# LOAD ALL RUNS
# ─────────────────────────────────────────────
def load(path):
    files = collect_files(path)

    all_data = {}
    for f in files:
        rid = get_run_id(f.name)
        all_data[rid] = parse_file(f)

    return all_data


# ─────────────────────────────────────────────
# METRICS
# ─────────────────────────────────────────────
def compute(all_data):
    runs = sorted(all_data.keys())

    avg_remaining = []
    dead_counts = []

    type_loss = {}

    for r in runs:
        nodes = all_data[r]

        avg_remaining.append(
            np.mean([n["pct"] for n in nodes])
        )

        dead_counts.append(
            sum(n["dead"] for n in nodes)
        )

        for n in nodes:
            t = n["type"]
            loss = 100 - n["pct"]

            if t not in type_loss:
                type_loss[t] = []
            type_loss[t].append(loss)

    return runs, avg_remaining, dead_counts, type_loss


# ─────────────────────────────────────────────
# PLOTS (THESIS QUALITY)
# ─────────────────────────────────────────────
def plot(runs, avg, dead, type_loss):

    fig = plt.figure(figsize=(18, 12))

    # ── 1. Histogram ─────────────────────────
    ax1 = plt.subplot(2, 2, 1)
    ax1.hist(avg, bins=20, color="steelblue", edgecolor="black")
    ax1.set_title("Battery Remaining Distribution")
    ax1.set_xlabel("Avg Remaining %")
    ax1.set_ylabel("Frequency")

    # ── 2. Trend line ─────────────────────────
    ax2 = plt.subplot(2, 2, 2)
    ax2.plot(runs, avg, marker="o", color="green")
    ax2.set_title("Battery Trend Across Runs")
    ax2.set_xlabel("Run ID")
    ax2.set_ylabel("Avg Remaining %")
    ax2.grid(True)

    # ── 3. Dead nodes trend ───────────────────
    ax3 = plt.subplot(2, 2, 3)
    ax3.plot(runs, dead, marker="x", color="red")
    ax3.set_title("Dead Nodes Across Runs")
    ax3.set_xlabel("Run ID")
    ax3.set_ylabel("Dead Nodes")
    ax3.grid(True)

    # ── 4. Type loss bar chart ────────────────
    ax4 = plt.subplot(2, 2, 4)

    labels = list(type_loss.keys())
    means = [np.mean(type_loss[t]) for t in labels]
    stds = [np.std(type_loss[t]) for t in labels]

    ax4.bar(labels, means, yerr=stds, capsize=5)
    ax4.set_title("Battery Loss per Node Type")
    ax4.set_ylabel("Loss %")

    plt.tight_layout()
    plt.savefig("battery_thesis_analysis.png", dpi=200)
    plt.show()


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    args = parser.parse_args()

    data = load(args.path)

    print(f"[+] Loaded {len(data)} runs")

    runs, avg, dead, type_loss = compute(data)

    plot(runs, avg, dead, type_loss)

    print("[✓] Saved: battery_thesis_analysis.png")