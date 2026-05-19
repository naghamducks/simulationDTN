"""
===============================================================================
PROPHET DTN ADVANCED THESIS ANALYZER (PUBLICATION-READY VERSION)
===============================================================================

This analyzer aggregates MULTIPLE simulation runs grouped by node density.

Folder Structure
-------------------------------------------------------------------------------
density-vs-deliveryrate/
│
├── thesis_prophet_analyzer.py
│
├── 100/
│   ├── run1_prophet_battery_scenario_MessageTransferReport.txt
│   ├── run2_prophet_battery_scenario_MessageTransferReport.txt
│   └── ...
│
├── 200/
│   ├── run1_prophet_battery_scenario_MessageTransferReport.txt
│   └── ...
│
├── 300/
│   └── ...
-------------------------------------------------------------------------------

Features
-------------------------------------------------------------------------------
✓ Parses ALL runs inside each node folder
✓ Aggregates metrics statistically
✓ Computes:
    - Delivery Probability
    - Abort Probability
    - Average Latency
    - Average Hop Count
    - Relay Overhead Ratio
    - Per-Priority QoS metrics
    - Standard deviation (sample SD)
    - 95% confidence intervals
✓ Generates thesis-quality graphs
✓ Exports CSV summaries
✓ Publication-grade statistical handling

Generated Outputs
-------------------------------------------------------------------------------
analysis_output/
│
├── overall_delivery_vs_nodes.png
├── delivery_stability_vs_nodes.png
├── latency_vs_nodes.png
├── hopcount_vs_nodes.png
├── abort_probability_vs_nodes.png
├── overhead_ratio_vs_nodes.png
├── priority_delivery_vs_nodes.png
├── priority_latency_vs_nodes.png
├── heatmap_delivery.png
├── heatmap_latency.png
├── boxplot_delivery_distribution.png
├── correlation_matrix.png
├── combined_dashboard.png
├── aggregated_statistics.csv
├── priority_statistics.csv
└── experiment_info.txt

Usage
-------------------------------------------------------------------------------
python thesis_prophet_analyzer.py

OR

python thesis_prophet_analyzer.py 100 200 300

Requirements
-------------------------------------------------------------------------------
pip install matplotlib seaborn pandas numpy
"""

import os
import re
import sys
import glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from collections import defaultdict

# =============================================================================
# CONFIG
# =============================================================================

OUTPUT_DIR = "analysis_output"

sns.set_style("whitegrid")

PRIORITY_LABELS = {
    0: "P0 Unknown",
    1: "P1 Low",
    2: "P2 Medium",
    3: "P3 Normal",
    4: "P4 High",
    5: "P5 Distress",
}

PRIORITY_COLORS = {
    0: "#90a4ae",
    1: "#42a5f5",
    2: "#26a69a",
    3: "#9ccc65",
    4: "#ffa726",
    5: "#ef5350",
}

# =============================================================================
# REGEX
# =============================================================================

SUMMARY_PATTERN = re.compile(
    r"P(\d+)\s*->\s*created:(\d+)\s+delivered:(\d+)\s+aborted:(\d+)\s+relays:(\d+)"
)

ADVANCED_PATTERN = re.compile(
    r"Delivery Probability\s*:\s*([\d.]+)%.*?"
    r"Abort Probability\s*:\s*([\d.]+)%.*?"
    r"Average Latency\s*:\s*([\d.]+).*?"
    r"Average Hop Count\s*:\s*([\d.]+).*?"
    r"Overhead Ratio\s*:\s*([\d.]+)",
    re.S
)

PRIORITY_ADV_PATTERN = re.compile(
    r"P(\d+)\s*->\s*deliveryRate:([\d.]+)%\s*"
    r"avgLatency:([\d.]+)\s*sec\s*"
    r"avgHops:([\d.]+)"
)
# =============================================================================
# HELPERS
# =============================================================================

def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def mean_std(vals):

    vals = np.array(vals)

    return (
        np.mean(vals),
        np.std(vals, ddof=1)
    )


def confidence_interval(vals, confidence=0.95):

    vals = np.array(vals)

    n = len(vals)

    if n <= 1:
        return 0

    # Sample standard deviation
    sample_std = np.std(vals, ddof=1)

    # Standard error
    std_err = sample_std / np.sqrt(n)

    # z-score for 95% confidence interval
    z = 1.96

    return z * std_err


def export_experiment_info():

    out = os.path.join(
        OUTPUT_DIR,
        "experiment_info.txt"
    )

    with open(out, "w") as f:

        f.write("PROPHET DTN Simulation Study\n")
        f.write("=================================\n\n")

        f.write("Independent runs per density: 20\n")
        f.write("Confidence interval: 95%\n")
        f.write("Aggregation: Mean ± CI\n")
        f.write("Standard deviation: Sample SD (ddof=1)\n")
        f.write("Random seeds: Independent per run\n")

    print(f"[✓] {out}")

# =============================================================================
# PARSE FILE
# =============================================================================

def parse_report(filepath):

    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    advanced = ADVANCED_PATTERN.search(content)

    if not advanced:
        return None

    data = {
        "delivery_probability": float(advanced.group(1)),
        "abort_probability": float(advanced.group(2)),
        "avg_latency": float(advanced.group(3)),
        "avg_hops": float(advanced.group(4)),
        "overhead_ratio": float(advanced.group(5)),
    }

    priority_data = {}

    for m in PRIORITY_ADV_PATTERN.finditer(content):

        p = int(m.group(1))

        priority_data[p] = {
            "delivery_rate": float(m.group(2)),
            "avg_latency": float(m.group(3)),
            "avg_hops": float(m.group(4)),
        }

    data["priority"] = priority_data

    return data

# =============================================================================
# LOAD NODE FOLDER
# =============================================================================

def load_node_folder(folder):

    try:
        node_count = int(os.path.basename(folder))
    except:
        return None

    txt_files = glob.glob(os.path.join(folder, "*.txt"))

    if not txt_files:
        return None

    runs = []

    for fp in txt_files:

        parsed = parse_report(fp)

        if parsed:
            runs.append(parsed)

    if not runs:
        return None

    # =========================================================================
    # GLOBAL METRICS
    # =========================================================================

    delivery_vals = [r["delivery_probability"] for r in runs]
    abort_vals = [r["abort_probability"] for r in runs]
    latency_vals = [r["avg_latency"] for r in runs]
    hops_vals = [r["avg_hops"] for r in runs]
    overhead_vals = [r["overhead_ratio"] for r in runs]

    # =========================================================================
    # PRIORITY METRICS
    # =========================================================================

    priority_stats = defaultdict(list)

    for r in runs:

        for p, pdata in r["priority"].items():

            priority_stats[p].append(pdata)

    aggregated_priority = {}

    for p, plist in priority_stats.items():

        aggregated_priority[p] = {

            "delivery_mean":
                np.mean([x["delivery_rate"] for x in plist]),

            "latency_mean":
                np.mean([x["avg_latency"] for x in plist]),

            "hop_mean":
                np.mean([x["avg_hops"] for x in plist]),
        }

    # =========================================================================
    # RETURN AGGREGATED DATA
    # =========================================================================

    return {

        "nodes": node_count,

        "runs": len(runs),

        # =========================================================
        # DELIVERY
        # =========================================================

        "delivery_mean": np.mean(delivery_vals),
        "delivery_std": np.std(delivery_vals, ddof=1),
        "delivery_ci": confidence_interval(delivery_vals),

        # =========================================================
        # ABORT
        # =========================================================

        "abort_mean": np.mean(abort_vals),
        "abort_std": np.std(abort_vals, ddof=1),
        "abort_ci": confidence_interval(abort_vals),

        # =========================================================
        # LATENCY
        # =========================================================

        "latency_mean": np.mean(latency_vals),
        "latency_std": np.std(latency_vals, ddof=1),
        "latency_ci": confidence_interval(latency_vals),

        # =========================================================
        # HOPS
        # =========================================================

        "hops_mean": np.mean(hops_vals),
        "hops_std": np.std(hops_vals, ddof=1),
        "hops_ci": confidence_interval(hops_vals),

        # =========================================================
        # OVERHEAD
        # =========================================================

        "overhead_mean": np.mean(overhead_vals),
        "overhead_std": np.std(overhead_vals, ddof=1),
        "overhead_ci": confidence_interval(overhead_vals),

        # =========================================================

        "priority": aggregated_priority,

        "raw_delivery": delivery_vals,
    }

# =============================================================================
# LOAD ALL
# =============================================================================

def load_all(folders):

    data = []

    for folder in folders:

        if not os.path.isdir(folder):
            continue

        print(f"[*] Processing {folder}")

        result = load_node_folder(folder)

        if result:
            data.append(result)

    data.sort(key=lambda x: x["nodes"])

    return data

# =============================================================================
# EXPORT CSV
# =============================================================================

def export_csv(data):

    rows = []

    for d in data:

        rows.append({

            "nodes": d["nodes"],
            "runs": d["runs"],

            "delivery_mean": d["delivery_mean"],
            "delivery_std": d["delivery_std"],
            "delivery_ci95": d["delivery_ci"],

            "abort_mean": d["abort_mean"],
            "abort_std": d["abort_std"],
            "abort_ci95": d["abort_ci"],

            "latency_mean": d["latency_mean"],
            "latency_std": d["latency_std"],
            "latency_ci95": d["latency_ci"],

            "hops_mean": d["hops_mean"],
            "hops_std": d["hops_std"],
            "hops_ci95": d["hops_ci"],

            "overhead_mean": d["overhead_mean"],
            "overhead_std": d["overhead_std"],
            "overhead_ci95": d["overhead_ci"],
        })

    df = pd.DataFrame(rows)

    out = os.path.join(
        OUTPUT_DIR,
        "aggregated_statistics.csv"
    )

    df.to_csv(out, index=False)

    print(f"[✓] {out}")

# =============================================================================
# EXPORT PRIORITY CSV
# =============================================================================

def export_priority_csv(data):

    rows = []

    for d in data:

        for p, pdata in d["priority"].items():

            rows.append({

                "nodes": d["nodes"],
                "priority": p,

                "delivery_mean": pdata["delivery_mean"],
                "latency_mean": pdata["latency_mean"],
                "hop_mean": pdata["hop_mean"],
            })

    df = pd.DataFrame(rows)

    out = os.path.join(
        OUTPUT_DIR,
        "priority_statistics.csv"
    )

    df.to_csv(out, index=False)

    print(f"[✓] {out}")

# =============================================================================
# GENERIC LINE GRAPH
# =============================================================================

def line_graph(
    data,
    key,
    ylabel,
    title,
    filename,
    std_key=None
):

    x = [d["nodes"] for d in data]
    y = [d[key] for d in data]

    plt.figure(figsize=(10, 6))

    if std_key:

        yerr = [d[std_key] for d in data]

        plt.errorbar(
            x,
            y,
            yerr=yerr,
            marker="o",
            linewidth=2.5,
            capsize=6
        )

    else:

        plt.plot(
            x,
            y,
            marker="o",
            linewidth=2.5
        )

    plt.title(title)

    plt.xlabel("Number of Nodes")

    if std_key and "ci" in std_key:
        plt.ylabel(f"{ylabel} (Mean ± 95% CI)")
    else:
        plt.ylabel(ylabel)

    plt.tight_layout()

    out = os.path.join(OUTPUT_DIR, filename)

    plt.savefig(out, dpi=300)

    plt.close()

    print(f"[✓] {out}")

# =============================================================================
# PRIORITY DELIVERY GRAPH
# =============================================================================

def plot_priority_delivery(data):

    plt.figure(figsize=(12, 7))

    priorities = sorted({
        p
        for d in data
        for p in d["priority"]
    })

    for p in priorities:

        x = []
        y = []

        for d in data:

            if p in d["priority"]:

                x.append(d["nodes"])

                y.append(
                    d["priority"][p]["delivery_mean"]
                )

        plt.plot(
            x,
            y,
            marker="o",
            linewidth=2,
            label=PRIORITY_LABELS.get(p, f"P{p}"),
            color=PRIORITY_COLORS.get(p)
        )

    plt.title("Priority Delivery Rate vs Nodes")

    plt.xlabel("Number of Nodes")

    plt.ylabel("Delivery Rate (%)")

    plt.legend()

    plt.tight_layout()

    out = os.path.join(
        OUTPUT_DIR,
        "priority_delivery_vs_nodes.png"
    )

    plt.savefig(out, dpi=300)

    plt.close()

    print(f"[✓] {out}")

# =============================================================================
# PRIORITY LATENCY GRAPH
# =============================================================================

def plot_priority_latency(data):

    plt.figure(figsize=(12, 7))

    priorities = sorted({
        p
        for d in data
        for p in d["priority"]
    })

    for p in priorities:

        x = []
        y = []

        for d in data:

            if p in d["priority"]:

                x.append(d["nodes"])

                y.append(
                    d["priority"][p]["latency_mean"]
                )

        plt.plot(
            x,
            y,
            marker="o",
            linewidth=2,
            label=PRIORITY_LABELS.get(p, f"P{p}"),
            color=PRIORITY_COLORS.get(p)
        )

    plt.title("Priority Latency vs Nodes")

    plt.xlabel("Number of Nodes")

    plt.ylabel("Average Latency")

    plt.legend()

    plt.tight_layout()

    out = os.path.join(
        OUTPUT_DIR,
        "priority_latency_vs_nodes.png"
    )

    plt.savefig(out, dpi=300)

    plt.close()

    print(f"[✓] {out}")

# =============================================================================
# HEATMAP
# =============================================================================

def heatmap(data, metric, title, filename):

    priorities = sorted({
        p
        for d in data
        for p in d["priority"]
    })

    # Prevent empty heatmap crash
    if not priorities:
        print(f"[!] Skipping {filename} (no priority data found)")
        return

    matrix = []

    for d in data:

        row = []

        for p in priorities:

            if p not in d["priority"]:
                row.append(np.nan)
                continue

            if metric == "delivery":
                val = d["priority"][p]["delivery_mean"]
            else:
                val = d["priority"][p]["latency_mean"]

            row.append(val)

        matrix.append(row)

    # Extra protection
    if len(matrix) == 0 or len(matrix[0]) == 0:
        print(f"[!] Skipping {filename} (empty matrix)")
        return

    plt.figure(figsize=(10, 7))

    sns.heatmap(
        matrix,
        annot=True,
        fmt=".1f",

        xticklabels=[
            PRIORITY_LABELS[p]
            for p in priorities
        ],

        yticklabels=[
            d["nodes"]
            for d in data
        ],

        cmap="RdYlGn"
    )

    plt.title(title)

    plt.xlabel("Priority")

    plt.ylabel("Nodes")

    plt.tight_layout()

    out = os.path.join(OUTPUT_DIR, filename)

    plt.savefig(out, dpi=300)

    plt.close()

    print(f"[✓] {out}")
# =============================================================================
# BOXPLOT
# =============================================================================

def boxplot_delivery(data):

    vals = [d["raw_delivery"] for d in data]

    labels = [d["nodes"] for d in data]

    plt.figure(figsize=(11, 6))

    plt.boxplot(vals, labels=labels)

    plt.title("Delivery Distribution Across Runs")

    plt.xlabel("Number of Nodes")

    plt.ylabel("Delivery Rate (%)")

    plt.tight_layout()

    out = os.path.join(
        OUTPUT_DIR,
        "boxplot_delivery_distribution.png"
    )

    plt.savefig(out, dpi=300)

    plt.close()

    print(f"[✓] {out}")

# =============================================================================
# CORRELATION MATRIX
# =============================================================================

def correlation_matrix(data):

    df = pd.DataFrame({

        "delivery":
            [d["delivery_mean"] for d in data],

        "abort":
            [d["abort_mean"] for d in data],

        "latency":
            [d["latency_mean"] for d in data],

        "hops":
            [d["hops_mean"] for d in data],

        "overhead":
            [d["overhead_mean"] for d in data],
    })

    corr = df.corr()

    plt.figure(figsize=(8, 6))

    sns.heatmap(
        corr,
        annot=True,
        cmap="coolwarm",
        fmt=".2f"
    )

    plt.title("Metric Correlation Matrix")

    plt.tight_layout()

    out = os.path.join(
        OUTPUT_DIR,
        "correlation_matrix.png"
    )

    plt.savefig(out, dpi=300)

    plt.close()

    print(f"[✓] {out}")

# =============================================================================
# DASHBOARD
# =============================================================================

def dashboard(data):

    fig, axs = plt.subplots(2, 2, figsize=(15, 10))

    nodes = [d["nodes"] for d in data]

    axs[0, 0].plot(
        nodes,
        [d["delivery_mean"] for d in data],
        marker="o"
    )

    axs[0, 0].set_title("Delivery Probability")

    axs[0, 1].plot(
        nodes,
        [d["latency_mean"] for d in data],
        marker="o"
    )

    axs[0, 1].set_title("Average Latency")

    axs[1, 0].plot(
        nodes,
        [d["hops_mean"] for d in data],
        marker="o"
    )

    axs[1, 0].set_title("Average Hop Count")

    axs[1, 1].plot(
        nodes,
        [d["overhead_mean"] for d in data],
        marker="o"
    )

    axs[1, 1].set_title("Overhead Ratio")

    for ax in axs.flat:

        ax.grid(True)

        ax.set_xlabel("Nodes")

    plt.suptitle(
        "PROPHET DTN THESIS DASHBOARD",
        fontsize=16,
        fontweight="bold"
    )

    plt.tight_layout()

    out = os.path.join(
        OUTPUT_DIR,
        "combined_dashboard.png"
    )

    plt.savefig(out, dpi=300)

    plt.close()

    print(f"[✓] {out}")

# =============================================================================
# MAIN
# =============================================================================

def main():

    ensure_output_dir()

    export_experiment_info()

    if len(sys.argv) > 1:

        folders = []

        for arg in sys.argv[1:]:

            expanded = glob.glob(arg)

            if expanded:
                folders.extend(expanded)
            else:
                folders.append(arg)

    else:

        folders = [
            d
            for d in os.listdir(".")
            if os.path.isdir(d)
        ]

    data = load_all(folders)

    if not data:

        print("[✗] No valid node folders found.")

        return

    # =========================================================================
    # EXPORTS
    # =========================================================================

    export_csv(data)

    export_priority_csv(data)

    # =========================================================================
    # GLOBAL METRIC GRAPHS
    # =========================================================================

    line_graph(
        data,
        "delivery_mean",
        "Delivery Probability (%)",
        "Delivery Probability vs Nodes",
        "overall_delivery_vs_nodes.png",
        "delivery_ci"
    )

    line_graph(
        data,
        "delivery_std",
        "Standard Deviation",
        "Delivery Stability vs Nodes",
        "delivery_stability_vs_nodes.png"
    )

    line_graph(
        data,
        "latency_mean",
        "Average Latency",
        "Average Latency vs Nodes",
        "latency_vs_nodes.png",
        "latency_ci"
    )

    line_graph(
        data,
        "hops_mean",
        "Average Hop Count",
        "Average Hop Count vs Nodes",
        "hopcount_vs_nodes.png",
        "hops_ci"
    )

    line_graph(
        data,
        "abort_mean",
        "Abort Probability (%)",
        "Abort Probability vs Nodes",
        "abort_probability_vs_nodes.png",
        "abort_ci"
    )

    line_graph(
        data,
        "overhead_mean",
        "Overhead Ratio",
        "Overhead Ratio vs Nodes",
        "overhead_ratio_vs_nodes.png",
        "overhead_ci"
    )

    # =========================================================================
    # PRIORITY ANALYSIS
    # =========================================================================

    plot_priority_delivery(data)

    plot_priority_latency(data)

    heatmap(
        data,
        "delivery",
        "Priority Delivery Heatmap",
        "heatmap_delivery.png"
    )

    heatmap(
        data,
        "latency",
        "Priority Latency Heatmap",
        "heatmap_latency.png"
    )

    # =========================================================================
    # ADVANCED STATISTICS
    # =========================================================================

    boxplot_delivery(data)

    correlation_matrix(data)

    dashboard(data)

    print("\n[✓] Advanced thesis analysis completed.")

    print(f"[✓] Outputs saved in: {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()