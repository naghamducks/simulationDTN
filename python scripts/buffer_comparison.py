"""
Enhanced Buffer Overhead — Routing Algorithm Comparison (Multi-Run)
===================================================================

Thesis-grade DTN routing analysis tool.

Features
--------
✓ Multi-run parsing
✓ Aggregate comparison dashboard
✓ Buffer size scalability analysis
✓ Confidence intervals
✓ Trendlines
✓ Statistical significance testing (optional SciPy)
✓ CSV export
✓ PDF + PNG export
✓ Thesis-quality 300 DPI figures

Usage
-----
python buffer_comparison.py prophet.txt epidemic.txt

python buffer_comparison.py \
    --labels "PRoPHET" "Epidemic" \
    prophet.txt epidemic.txt
"""

import re
import sys
import os
import csv
import argparse
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches

# ──────────────────────────────────────────────────────────────────────────────
# Optional SciPy
# ──────────────────────────────────────────────────────────────────────────────

try:
    from scipy.stats import ttest_ind
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

# ──────────────────────────────────────────────────────────────────────────────
# Style
# ──────────────────────────────────────────────────────────────────────────────

ALGO_STYLES = [
    {"color": "#1f77b4", "marker": "^", "linestyle": "-",  "linewidth": 2.0},
    {"color": "#ff7f0e", "marker": "o", "linestyle": "-",  "linewidth": 2.0},
    {"color": "#2ca02c", "marker": "s", "linestyle": "-",  "linewidth": 2.0},
    {"color": "#9467bd", "marker": "D", "linestyle": "--", "linewidth": 2.0},
]

PANEL_COLORS = [
    "#1565c0",
    "#b71c1c",
    "#2e7d32",
    "#6a1b9a"
]

# ──────────────────────────────────────────────────────────────────────────────
# Parser
# ──────────────────────────────────────────────────────────────────────────────

FIELD_PATTERNS = [
    (r"Sampling interval\s*:\s*([\d.]+)",      "sampling_interval_s", float),
    (r"Nodes sampled\s*:\s*([\d.]+)",          "nodes_sampled",       int),
    (r"Total samples\s*:\s*([\d.]+)",          "total_samples",       int),
    (r"Buffer size\s*:\s*(\S+)",               "buffer_size_raw",     str),
    (r"Router\s*:\s*(\S+)",                    "router",              str),
    (r"Average overhead %\s*:\s*([\d.]+)",     "avg_pct",             float),
    (r"Mean overhead %\s*:\s*([\d.]+)",        "mean_pct",            float),
    (r"SD overhead %\s*:\s*([\d.]+)",          "sd_pct",              float),
    (r"Min node overhead %\s*:\s*([\d.]+)",    "min_pct",             float),
    (r"Max node overhead %\s*:\s*([\d.]+)",    "max_pct",             float),
    (r"Mean of per-node SDs\s*:\s*([\d.]+)",   "mean_node_sd_pct",    float),
    (r"Global peak overhead\s*:\s*([\d.]+)",   "peak_pct",            float),
]


def parse_buffer_size_mb(raw):

    if not raw:
        return None

    raw = raw.upper().replace(" ", "")

    m = re.match(r"([\d.]+)(M|MB|G|GB|K|KB)?", raw)

    if not m:
        return None

    val = float(m.group(1))
    unit = m.group(2) or "M"

    if unit in ("G", "GB"):
        return val * 1024

    elif unit in ("K", "KB"):
        return val / 1024

    return val


def parse_one_block(block_text):

    result = {}

    for pattern, key, cast in FIELD_PATTERNS:

        m = re.search(pattern, block_text, re.IGNORECASE)

        result[key] = cast(m.group(1)) if m else None

    result["buffer_size_mb"] = parse_buffer_size_mb(
        result.get("buffer_size_raw", "")
    )

    return result


def parse_file(filepath):

    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()

    parts = re.split(
        r"(?=BUFFER OVERHEAD REPORT[\s\d]*[—\-])",
        text,
        flags=re.IGNORECASE
    )

    parts = [p.strip() for p in parts if p.strip()]

    runs = []

    for part in parts:

        block = parse_one_block(part)

        m = re.search(
            r"BUFFER OVERHEAD REPORT\s*(\d+)",
            part,
            re.IGNORECASE
        )

        block["run_index"] = int(m.group(1)) if m else 1

        block["filepath"] = filepath

        # Ignore invalid/incomplete blocks
        if (
            block.get("mean_pct") is not None and
            block.get("buffer_size_mb") is not None
        ):
            runs.append(block)

    runs.sort(
        key=lambda r: (r.get("buffer_size_mb") or 0)
    )

    return runs

# ──────────────────────────────────────────────────────────────────────────────
# Statistics
# ──────────────────────────────────────────────────────────────────────────────


def confidence_interval(sd, n, z=1.96):

    if n is None or n <= 1:
        return 0

    return z * (sd / np.sqrt(n))


def scalability_slope(runs):

    xs = [
        r["buffer_size_mb"]
        for r in runs
        if r.get("buffer_size_mb") is not None
    ]

    ys = [
        r["mean_pct"]
        for r in runs
        if r.get("mean_pct") is not None
    ]

    if len(xs) < 2:
        return None

    return np.polyfit(xs, ys, 1)[0]


def aggregate_runs(runs):

    def safe_mean(key):

        vals = [
            r[key]
            for r in runs
            if r.get(key) is not None
        ]

        return float(np.mean(vals)) if vals else None

    return {
        "mean_pct":         safe_mean("mean_pct"),
        "sd_pct":           safe_mean("sd_pct"),
        "min_pct":          min((r["min_pct"] for r in runs if r.get("min_pct") is not None), default=None),
        "max_pct":          max((r["max_pct"] for r in runs if r.get("max_pct") is not None), default=None),
        "peak_pct":         max((r["peak_pct"] for r in runs if r.get("peak_pct") is not None), default=None),
        "mean_node_sd_pct": safe_mean("mean_node_sd_pct"),
        "nodes_sampled":    runs[0].get("nodes_sampled"),
        "buffer_size_raw":  "Multiple" if len(runs) > 1 else runs[0].get("buffer_size_raw"),
        "router":           runs[0].get("router"),
    }

# ──────────────────────────────────────────────────────────────────────────────
# CSV Export
# ──────────────────────────────────────────────────────────────────────────────


def export_csv(all_file_runs, labels, output_path):

    with open(output_path, "w", newline="") as f:

        writer = csv.writer(f)

        writer.writerow([
            "Algorithm",
            "Buffer_MB",
            "Mean_Overhead",
            "SD_Overhead",
            "Peak_Overhead"
        ])

        for label, runs in zip(labels, all_file_runs):

            for r in runs:

                writer.writerow([
                    label,
                    r.get("buffer_size_mb"),
                    r.get("mean_pct"),
                    r.get("sd_pct"),
                    r.get("peak_pct")
                ])

    print(f"[OK] CSV exported -> {output_path}")

# ──────────────────────────────────────────────────────────────────────────────
# Console Table
# ──────────────────────────────────────────────────────────────────────────────


def print_table(agg_reports, labels):

    fields = [
        ("Mean overhead %",     "mean_pct"),
        ("SD overhead %",       "sd_pct"),
        ("Min node overhead %", "min_pct"),
        ("Max node overhead %", "max_pct"),
        ("Mean per-node SD %",  "mean_node_sd_pct"),
        ("Global peak %",       "peak_pct"),
    ]

    col = 18

    header = f"{'Metric':<28}" + "".join(
        f"{l:>{col}}" for l in labels
    )

    sep = "=" * len(header)

    print("\n" + sep)
    print(header)
    print(sep)

    for fname, fkey in fields:

        row = f"{fname:<28}"

        for r in agg_reports:

            val = r.get(fkey)

            row += f"{f'{val:.4f}%' if val is not None else 'N/A':>{col}}"

        print(row)

    print(sep)

# ──────────────────────────────────────────────────────────────────────────────
# Aggregate Dashboard
# ──────────────────────────────────────────────────────────────────────────────


def plot_aggregate(agg_reports, labels, output_path):

    n = len(agg_reports)

    colors = PANEL_COLORS[:n]

    x = np.arange(n)

    means = [r["mean_pct"] for r in agg_reports]
    sds = [r["sd_pct"] for r in agg_reports]
    peaks = [r["peak_pct"] for r in agg_reports]
    nd_sds = [r["mean_node_sd_pct"] for r in agg_reports]

    fig = plt.figure(figsize=(15, 11))

    fig.suptitle(
        "Buffer Overhead Analysis — Routing Algorithm Comparison",
        fontsize=15,
        fontweight="bold"
    )

    gs = gridspec.GridSpec(2, 2, figure=fig)

    # Panel 1
    ax1 = fig.add_subplot(gs[0, 0])

    ax1.bar(
        x,
        means,
        color=colors,
        yerr=sds,
        capsize=8,
        alpha=0.85
    )

    ax1.set_xticks(x)
    ax1.set_xticklabels(labels)

    ax1.set_ylabel("Overhead (%)")

    ax1.set_title("Mean Overhead ± SD")

    ax1.grid(True, linestyle="--", alpha=0.4)

    # Panel 2
    ax2 = fig.add_subplot(gs[0, 1])

    ax2.bar(
        x,
        peaks,
        color=colors,
        alpha=0.85
    )

    ax2.set_xticks(x)
    ax2.set_xticklabels(labels)

    ax2.set_ylabel("Peak Overhead (%)")

    ax2.set_title("Global Peak Overhead")

    ax2.grid(True, linestyle="--", alpha=0.4)

    # Panel 3
    ax3 = fig.add_subplot(gs[1, 0])

    ax3.bar(
        x,
        nd_sds,
        color=colors,
        alpha=0.85
    )

    ax3.set_xticks(x)
    ax3.set_xticklabels(labels)

    ax3.set_ylabel("Per-node SD (%)")

    ax3.set_title("Node-Level Variability")

    ax3.grid(True, linestyle="--", alpha=0.4)

    # Panel 4 — Radar
    ax4 = fig.add_subplot(gs[1, 1], polar=True)

    metrics = [
        "Mean",
        "SD",
        "Peak",
        "Node SD"
    ]

    raw_vals = [
        [
            r["mean_pct"],
            r["sd_pct"],
            r["peak_pct"],
            r["mean_node_sd_pct"]
        ]
        for r in agg_reports
    ]

    all_v = np.array(raw_vals)

    ranges = np.where(
        all_v.max(0) - all_v.min(0) == 0,
        1,
        all_v.max(0) - all_v.min(0)
    )

    norm_v = (all_v - all_v.min(0)) / ranges

    angles = np.linspace(
        0,
        2 * np.pi,
        len(metrics),
        endpoint=False
    ).tolist()

    angles += angles[:1]

    for norm, color, label in zip(norm_v, colors, labels):

        vals = norm.tolist() + norm[:1].tolist()

        ax4.plot(
            angles,
            vals,
            color=color,
            linewidth=2.2,
            label=label
        )

        ax4.fill(
            angles,
            vals,
            color=color,
            alpha=0.12
        )

    ax4.set_xticks(angles[:-1])
    ax4.set_xticklabels(metrics)

    ax4.set_yticklabels([])

    ax4.set_title("Normalised Overhead Profile")

    ax4.legend(loc="upper right")

    plt.tight_layout()

    plt.savefig(output_path, dpi=300, bbox_inches="tight")

    plt.savefig(
        output_path.replace(".png", ".pdf"),
        bbox_inches="tight"
    )

    print(f"[OK] Aggregate chart saved -> {output_path}")

    plt.close()

# ──────────────────────────────────────────────────────────────────────────────
# Buffer Size Scalability Plot
# ──────────────────────────────────────────────────────────────────────────────


def plot_vs_buffersize(all_file_runs, labels, output_path):

    fig, ax = plt.subplots(figsize=(8, 5.5))

    for file_runs, label, style in zip(
        all_file_runs,
        labels,
        ALGO_STYLES
    ):

        xs = [
            r["buffer_size_mb"]
            for r in file_runs
        ]

        ys = [
            r["mean_pct"]
            for r in file_runs
        ]

        es = [
            confidence_interval(
                r["sd_pct"],
                r.get("nodes_sampled", 1)
            )
            for r in file_runs
        ]

        ax.plot(
            xs,
            ys,
            color=style["color"],
            marker=style["marker"],
            linestyle=style["linestyle"],
            linewidth=style["linewidth"],
            markersize=7,
            label=label
        )

        ax.fill_between(
            xs,
            np.array(ys) - np.array(es),
            np.array(ys) + np.array(es),
            color=style["color"],
            alpha=0.12
        )

        # Trendline
        if len(xs) >= 2:

            z = np.polyfit(xs, ys, 1)

            p = np.poly1d(z)

            ax.plot(
                xs,
                p(xs),
                linestyle=":",
                linewidth=1.5,
                color=style["color"],
                alpha=0.8
            )

    ax.axhline(
        100,
        color="#c62828",
        linestyle="--",
        linewidth=1.2,
        label="100% Buffer Full"
    )

    ax.set_xlabel("Buffer Size (MB)", fontsize=11)

    ax.set_ylabel("Mean Overhead %", fontsize=11)

    ax.set_title(
        "Impact of Buffer Capacity on Routing Overhead",
        fontsize=13,
        fontweight="bold"
    )

    ax.grid(True, linestyle="--", alpha=0.5)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax.legend()

    # Improvement annotation
    if len(all_file_runs) == 2:

        try:

            first = all_file_runs[0][-1]["mean_pct"]

            second = all_file_runs[1][-1]["mean_pct"]

            improvement = ((second - first) / second) * 100

            ax.text(
                0.02,
                0.95,
                f"Improvement: {improvement:.2f}%",
                transform=ax.transAxes,
                fontsize=10,
                fontweight="bold",
                bbox=dict(
                    boxstyle="round",
                    facecolor="#f5f5f5",
                    edgecolor="#999"
                )
            )

        except:
            pass

    plt.tight_layout()

    plt.savefig(output_path, dpi=300, bbox_inches="tight")

    plt.savefig(
        output_path.replace(".png", ".pdf"),
        bbox_inches="tight"
    )

    print(f"[OK] Scalability chart saved -> {output_path}")

    plt.close()

# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Enhanced DTN Buffer Overhead Analysis"
    )

    parser.add_argument(
        "files",
        nargs="+",
        help="Input report files"
    )

    parser.add_argument(
        "--labels",
        nargs="+",
        default=None
    )

    args = parser.parse_args()

    if len(args.files) > 4:

        print("[!] Maximum 4 files supported.")

        sys.exit(1)

    all_file_runs = []

    for fp in args.files:

        if not os.path.isfile(fp):

            print(f"[X] File not found: {fp}")

            sys.exit(1)

        print(f"[*] Parsing: {fp}")

        runs = parse_file(fp)

        if not runs:

            print(f"[X] No valid data found in {fp}")

            sys.exit(1)

        print(
            f"    -> {len(runs)} run(s): "
            f"{[r.get('buffer_size_raw') for r in runs]}"
        )

        all_file_runs.append(runs)

    # Labels
    labels = []

    for i, (fp, runs) in enumerate(zip(args.files, all_file_runs)):

        if args.labels and i < len(args.labels):

            labels.append(args.labels[i])

        else:

            labels.append(
                runs[0].get("router")
                or os.path.splitext(os.path.basename(fp))[0]
            )

    agg_reports = [
        aggregate_runs(runs)
        for runs in all_file_runs
    ]

    print_table(agg_reports, labels)

    # Statistical significance
    if len(all_file_runs) == 2 and SCIPY_AVAILABLE:

        a = [
            r["mean_pct"]
            for r in all_file_runs[0]
            if r.get("mean_pct") is not None
        ]

        b = [
            r["mean_pct"]
            for r in all_file_runs[1]
            if r.get("mean_pct") is not None
        ]

        if len(a) > 1 and len(b) > 1:

            t, p = ttest_ind(a, b, equal_var=False)

            print(f"\nT-test p-value: {p:.6f}")

            if p < 0.05:
                print("Difference is statistically significant.")
            else:
                print("Difference is NOT statistically significant.")

    elif len(all_file_runs) == 2:

        print("\n[i] SciPy not installed — t-test skipped.")

    # Scalability analysis
    print("\nScalability Analysis:")

    for label, runs in zip(labels, all_file_runs):

        slope = scalability_slope(runs)

        if slope is not None:

            print(
                f"  {label}: slope = {slope:.4f}"
            )

    cwd = os.getcwd()

    export_csv(
        all_file_runs,
        labels,
        os.path.join(cwd, "buffer_overhead_results.csv")
    )

    plot_aggregate(
        agg_reports,
        labels,
        os.path.join(cwd, "buffer_overhead_comparison.png")
    )

    max_runs = max(len(runs) for runs in all_file_runs)

    if max_runs > 1:

        plot_vs_buffersize(
            all_file_runs,
            labels,
            os.path.join(cwd, "buffer_overhead_vs_buffersize.png")
        )

    else:

        print(
            "[i] Single run per file — scalability plot skipped."
        )