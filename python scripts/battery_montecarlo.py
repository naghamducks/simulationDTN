import re
import argparse
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from collections import defaultdict

# =========================================================
# CONFIG
# =========================================================

RUN_REGEX = re.compile(r"run(\d+)", re.IGNORECASE)

LINE_PATTERN = re.compile(
    r"^(\d+)\s+(\S+)\s+([\d.]+)\s+([\d.]+)\s+(alive|DEAD)"
)

FINAL_PATTERN = re.compile(
    r"^(\S+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)%\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+(alive|DEAD)"
)

# =========================================================
# HELPERS
# =========================================================

def get_run_id(name):
    m = RUN_REGEX.search(name)
    return int(m.group(1)) if m else None


def node_type(h):
    if h.startswith("p"):
        return "Pedestrian"

    if h.startswith("c"):
        return "Car"

    if h.startswith("w"):
        return "WiFi"

    if h.startswith("t"):
        return "Tram"

    return "Other"


# =========================================================
# FILE COLLECTION
# =========================================================

def collect_files(path):

    p = Path(path)

    if p.is_dir():
        files = list(p.glob("*BatteryReport*.txt"))
    else:
        files = list(Path().glob(path))

    grouped = {}

    for f in files:

        rid = get_run_id(f.name)

        if rid is not None:
            grouped[rid] = f

    return [grouped[k] for k in sorted(grouped.keys())]


# =========================================================
# PARSER
# =========================================================

def parse_file(fp):

    timeline = []
    final_nodes = []

    with open(fp, "r", encoding="utf-8", errors="ignore") as f:

        for line in f:

            line = line.strip()

            # ---------------------------------------------
            # TIMELINE DATA
            # ---------------------------------------------
            m = LINE_PATTERN.match(line)

            if m:

                timeline.append({
                    "time": int(m.group(1)),
                    "host": m.group(2),
                    "energy": float(m.group(3)),
                    "pct": float(m.group(4)),
                    "dead": m.group(5) == "DEAD"
                })

                continue

            # ---------------------------------------------
            # FINAL SUMMARY DATA
            # ---------------------------------------------
            m2 = FINAL_PATTERN.match(line)

            if m2:

                final_nodes.append({
                    "host": m2.group(1),
                    "remaining": float(m2.group(2)),
                    "initial": float(m2.group(3)),
                    "pct": float(m2.group(4)),
                    "tx": float(m2.group(5)),
                    "rx": float(m2.group(6)),
                    "scan": float(m2.group(7)),
                    "dead": m2.group(8) == "DEAD",
                    "type": node_type(m2.group(1))
                })

    return timeline, final_nodes


# =========================================================
# LOAD
# =========================================================

def load(path):

    files = collect_files(path)

    all_runs = []

    for f in files:

        timeline, final_nodes = parse_file(f)

        all_runs.append({
            "timeline": timeline,
            "final": final_nodes
        })

    return all_runs


# =========================================================
# STATIC METRICS
# =========================================================

def compute_static_metrics(all_runs):

    avg_remaining = []
    dead_counts = []

    type_loss = defaultdict(list)

    for run in all_runs:

        nodes = run["final"]

        if not nodes:
            continue

        avg_remaining.append(
            np.mean([n["pct"] for n in nodes])
        )

        dead_counts.append(
            sum(n["dead"] for n in nodes)
        )

        for n in nodes:

            loss = 100 - n["pct"]

            type_loss[n["type"]].append(loss)

    return avg_remaining, dead_counts, type_loss


# =========================================================
# SURVIVAL METRICS
# =========================================================

def compute_survival(all_runs):

    dead_probability = defaultdict(list)
    survival_probability = defaultdict(list)

    all_times = set()

    for run in all_runs:

        timeline = run["timeline"]

        times = sorted(set(x["time"] for x in timeline))

        all_times.update(times)

        for t in times:

            rows = [x for x in timeline if x["time"] == t]

            total = len(rows)

            if total == 0:
                continue

            dead = sum(r["dead"] for r in rows)

            p_dead = dead / total
            p_alive = 1 - p_dead

            dead_probability[t].append(p_dead)
            survival_probability[t].append(p_alive)

    final_times = sorted(all_times)

    dead_curve = []
    survival_curve = []

    for t in final_times:

        dead_curve.append(
            np.mean(dead_probability[t]) * 100
        )

        survival_curve.append(
            np.mean(survival_probability[t]) * 100
        )

    return final_times, dead_curve, survival_curve


# =========================================================
# PLOTS
# =========================================================

def plot(
    avg_remaining,
    dead_counts,
    type_loss,
    times,
    dead_curve,
    survival_curve
):

    fig = plt.figure(figsize=(20, 18))

    # =====================================================
    # 1. Battery Remaining Histogram
    # =====================================================

    ax1 = plt.subplot(3, 2, 1)

    ax1.hist(
        avg_remaining,
        bins=15,
        edgecolor="black"
    )

    ax1.set_title("Battery Remaining Distribution")
    ax1.set_xlabel("Average Remaining Battery (%)")
    ax1.set_ylabel("Frequency")

    # =====================================================
    # 2. Avg Battery Trend
    # =====================================================

    ax2 = plt.subplot(3, 2, 2)

    ax2.plot(
        range(1, len(avg_remaining) + 1),
        avg_remaining,
        marker='o'
    )

    ax2.set_title("Average Remaining Battery Across Runs")
    ax2.set_xlabel("Run")
    ax2.set_ylabel("Remaining Battery (%)")

    ax2.grid(True)

    # =====================================================
    # 3. Dead Nodes Trend
    # =====================================================

    ax3 = plt.subplot(3, 2, 3)

    ax3.plot(
        range(1, len(dead_counts) + 1),
        dead_counts,
        marker='x'
    )

    ax3.set_title("Dead Nodes Across Runs")
    ax3.set_xlabel("Run")
    ax3.set_ylabel("Dead Nodes")

    ax3.grid(True)

    # =====================================================
    # 4. Battery Loss by Node Type
    # =====================================================

    ax4 = plt.subplot(3, 2, 4)

    labels = list(type_loss.keys())

    means = [
        np.mean(type_loss[t])
        for t in labels
    ]

    stds = [
        np.std(type_loss[t])
        for t in labels
    ]

    ax4.bar(
        labels,
        means,
        yerr=stds,
        capsize=5
    )

    ax4.set_title("Battery Loss per Node Type")
    ax4.set_ylabel("Battery Loss (%)")

    # =====================================================
    # 5. Death Probability Over Time
    # =====================================================

    ax5 = plt.subplot(3, 2, 5)

    ax5.plot(
        times,
        dead_curve,
        linewidth=2,
        marker='o'
    )

    ax5.set_title(
        "Probability of Node Battery Death Over Time"
    )

    ax5.set_xlabel("Simulation Time (s)")
    ax5.set_ylabel("Dead Node Probability (%)")

    ax5.grid(True)

    # =====================================================
    # 6. Survival Probability Over Time
    # =====================================================

    ax6 = plt.subplot(3, 2, 6)

    ax6.plot(
        times,
        survival_curve,
        linewidth=2,
        marker='o'
    )

    ax6.set_title(
        "Node Survival Probability Over Time"
    )

    ax6.set_xlabel("Simulation Time (s)")
    ax6.set_ylabel("Survival Probability (%)")

    ax6.grid(True)

    # =====================================================

    plt.tight_layout()

    plt.savefig(
        "battery_complete_analysis.png",
        dpi=300,
        bbox_inches="tight"
    )

    plt.show()


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument("path")

    args = parser.parse_args()

    all_runs = load(args.path)

    print(f"[+] Loaded {len(all_runs)} runs")

    avg_remaining, dead_counts, type_loss = compute_static_metrics(all_runs)

    times, dead_curve, survival_curve = compute_survival(all_runs)

    plot(
        avg_remaining,
        dead_counts,
        type_loss,
        times,
        dead_curve,
        survival_curve
    )

    print("[✓] Saved: battery_complete_analysis.png")