import os
import re
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# =========================================================
# THESIS-QUALITY DTN ANALYSIS SCRIPT
# =========================================================

# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

BASE_DIR = r"C:\Users\User\Desktop\Network Load\results"

protocols = [
    "prophet",
    "epidemic",
    "sprayAndWait"
]

loads = [
    "low_load",
    "high_load",
    "extreme_load"
]

load_labels = {
    "low_load": "Low",
    "high_load": "High",
    "extreme_load": "Extreme"
}

priority_levels = ["P5", "P4", "P3", "P2", "P1"]

# ---------------------------------------------------------
# THESIS STYLE
# ---------------------------------------------------------

plt.style.use('default')
sns.set_theme(style="whitegrid")

FIG_DPI = 600
TITLE_SIZE = 18
LABEL_SIZE = 14
TICK_SIZE = 12
LEGEND_SIZE = 11

PROTOCOL_LABELS = {
    "prophet": "PRoPHET",
    "epidemic": "Epidemic",
    "sprayAndWait": "Spray-and-Wait"
}

PROTOCOL_COLORS = {
    "prophet": "#1f77b4",
    "epidemic": "#ff7f0e",
    "sprayAndWait": "#2ca02c"
}

# =========================================================
# REGEX PATTERNS
# =========================================================

metrics_patterns = {

    "delivery_prob": r"Delivery Probability\s*:\s*([\d.]+)",
    "abort_prob": r"Abort Probability\s*:\s*([\d.]+)",
    "latency_avg": r"Average Latency\s*:\s*([\d.]+)",
    "hopcount_avg": r"Average Hop Count\s*:\s*([\d.]+)",
    "overhead_ratio": r"Overhead Ratio\s*:\s*([\d.]+)",

    "total_created": r"TOTAL created\s*:\s*(\d+)",
    "total_delivered": r"TOTAL delivered\s*:\s*(\d+)",
    "total_relays": r"TOTAL relays\s*:\s*(\d+)",
    "total_aborted": r"TOTAL aborted\s*:\s*(\d+)"
}

priority_patterns = {

    "P5": r"P5 .*?created:(\d+).*?delivered:(\d+).*?aborted:(\d+).*?relays:(\d+)",
    "P4": r"P4 .*?created:(\d+).*?delivered:(\d+).*?aborted:(\d+).*?relays:(\d+)",
    "P3": r"P3 .*?created:(\d+).*?delivered:(\d+).*?aborted:(\d+).*?relays:(\d+)",
    "P2": r"P2 .*?created:(\d+).*?delivered:(\d+).*?aborted:(\d+).*?relays:(\d+)",
    "P1": r"P1 .*?created:(\d+).*?delivered:(\d+).*?aborted:(\d+).*?relays:(\d+)"
}

advanced_priority_patterns = {

    "P5": r"P5 -> deliveryRate:([\d.]+)%.*?avgLatency:([\d.]+).*?avgHops:([\d.]+)",
    "P4": r"P4 -> deliveryRate:([\d.]+)%.*?avgLatency:([\d.]+).*?avgHops:([\d.]+)",
    "P3": r"P3 -> deliveryRate:([\d.]+)%.*?avgLatency:([\d.]+).*?avgHops:([\d.]+)",
    "P2": r"P2 -> deliveryRate:([\d.]+)%.*?avgLatency:([\d.]+).*?avgHops:([\d.]+)",
    "P1": r"P1 -> deliveryRate:([\d.]+)%.*?avgLatency:([\d.]+).*?avgHops:([\d.]+)"
}

# =========================================================
# STORAGE
# =========================================================

all_results = []

# =========================================================
# HELPERS
# =========================================================

def extract_metric(content, pattern):

    match = re.search(pattern, content, re.DOTALL)

    if match:
        return float(match.group(1))

    return None

def save_figure(filename):

    plt.tight_layout()

    plt.savefig(
        filename,
        dpi=FIG_DPI,
        bbox_inches='tight'
    )

    plt.close()

    print(f"Saved: {filename}")

# =========================================================
# START
# =========================================================

print("\n=================================================")
print("DTN THESIS ANALYSIS STARTED")
print("=================================================\n")

if not os.path.exists(BASE_DIR):

    print("ERROR: BASE DIRECTORY NOT FOUND")
    exit()

# =========================================================
# MAIN PARSING LOOP
# =========================================================

for protocol in protocols:

    print(f"\nProcessing Protocol: {protocol}")

    protocol_path = os.path.join(BASE_DIR, protocol)

    if not os.path.exists(protocol_path):
        continue

    for load in loads:

        load_path = os.path.join(protocol_path, load)

        if not os.path.exists(load_path):
            continue

        run_folders = sorted(os.listdir(load_path))

        for run_folder in run_folders:

            run_path = os.path.join(load_path, run_folder)

            if not os.path.isdir(run_path):
                continue

            stats_file = None

            for file in os.listdir(run_path):

                if "MessageTransferReport" in file:

                    stats_file = os.path.join(run_path, file)
                    break

            if stats_file is None:
                continue

            try:

                with open(stats_file, "r", encoding="utf-8") as f:
                    content = f.read()

            except Exception as e:

                print(e)
                continue

            row = {

                "protocol": protocol,
                "load": load,
                "run": run_folder
            }

            # -------------------------------------------------
            # BASIC METRICS
            # -------------------------------------------------

            for metric, pattern in metrics_patterns.items():

                row[metric] = extract_metric(
                    content,
                    pattern
                )

            # -------------------------------------------------
            # PRIORITY COUNTS
            # -------------------------------------------------

            for priority, pattern in priority_patterns.items():

                match = re.search(pattern, content, re.DOTALL)

                if match:

                    row[f"{priority}_created"] = int(match.group(1))
                    row[f"{priority}_delivered"] = int(match.group(2))
                    row[f"{priority}_aborted"] = int(match.group(3))
                    row[f"{priority}_relays"] = int(match.group(4))

                else:

                    row[f"{priority}_created"] = 0
                    row[f"{priority}_delivered"] = 0
                    row[f"{priority}_aborted"] = 0
                    row[f"{priority}_relays"] = 0

            # -------------------------------------------------
            # ADVANCED PRIORITY METRICS
            # -------------------------------------------------

            for priority, pattern in advanced_priority_patterns.items():

                match = re.search(pattern, content, re.DOTALL)

                if match:

                    row[f"{priority}_deliveryRate"] = float(match.group(1))
                    row[f"{priority}_avgLatency"] = float(match.group(2))
                    row[f"{priority}_avgHops"] = float(match.group(3))

                else:

                    row[f"{priority}_deliveryRate"] = 0
                    row[f"{priority}_avgLatency"] = 0
                    row[f"{priority}_avgHops"] = 0

            all_results.append(row)

# =========================================================
# DATAFRAME
# =========================================================

df = pd.DataFrame(all_results)

if len(df) == 0:

    print("NO DATA PARSED")
    exit()

df.to_csv("priority_network_results.csv", index=False)

summary = df.groupby(
    ["protocol", "load"]
).mean(
    numeric_only=True
).reset_index()

summary.to_csv(
    "priority_summary_statistics.csv",
    index=False
)

# =========================================================
# CLEAN LINE PLOTS
# =========================================================

def generate_clean_line_plot(metric, ylabel, filename):

    plt.figure(figsize=(8, 5))

    for protocol in protocols:

        subset = summary[
            summary["protocol"] == protocol
        ].copy()

        subset = subset.set_index("load")
        subset = subset.loc[loads].reset_index()

        x_labels = [
            load_labels[x]
            for x in subset["load"]
        ]

        plt.plot(
            x_labels,
            subset[metric],
            marker='o',
            linewidth=2.5,
            markersize=8,
            label=PROTOCOL_LABELS[protocol],
            color=PROTOCOL_COLORS[protocol]
        )

    plt.title(ylabel, fontsize=TITLE_SIZE)

    plt.xlabel(
        "Network Load",
        fontsize=LABEL_SIZE
    )

    plt.ylabel(
        ylabel,
        fontsize=LABEL_SIZE
    )

    plt.xticks(fontsize=TICK_SIZE)
    plt.yticks(fontsize=TICK_SIZE)

    plt.legend(fontsize=LEGEND_SIZE)

    plt.grid(True, linestyle='--', alpha=0.5)

    save_figure(filename)

# =========================================================
# GROUPED BAR CHARTS
# =========================================================

def generate_grouped_bar_chart(metric, ylabel, filename):

    chart_df = summary.copy()

    chart_df["Load"] = chart_df["load"].map(load_labels)

    chart_df["Protocol"] = chart_df["protocol"].map(
        PROTOCOL_LABELS
    )

    plt.figure(figsize=(9, 5))

    sns.barplot(
        data=chart_df,
        x="Load",
        y=metric,
        hue="Protocol"
    )

    plt.title(ylabel, fontsize=TITLE_SIZE)

    plt.xlabel(
        "Network Load",
        fontsize=LABEL_SIZE
    )

    plt.ylabel(
        ylabel,
        fontsize=LABEL_SIZE
    )

    plt.xticks(fontsize=TICK_SIZE)
    plt.yticks(fontsize=TICK_SIZE)

    plt.legend(fontsize=LEGEND_SIZE)

    save_figure(filename)

# =========================================================
# PRIORITY HEATMAPS
# =========================================================

def generate_priority_heatmaps():

    for protocol in protocols:

        heatmap_data = []

        for load in loads:

            subset = summary[
                (summary["protocol"] == protocol)
                &
                (summary["load"] == load)
            ]

            row = []

            for priority in priority_levels:

                value = subset.iloc[0][
                    f"{priority}_deliveryRate"
                ]

                row.append(round(value, 2))

            heatmap_data.append(row)

        heatmap_df = pd.DataFrame(
            heatmap_data,
            index=[load_labels[x] for x in loads],
            columns=priority_levels
        )

        plt.figure(figsize=(7, 4))

        sns.heatmap(
            heatmap_df,
            annot=True,
            fmt='.2f',
            linewidths=0.5,
            cmap='YlGnBu',
            cbar_kws={
                'label': 'Delivery Ratio (%)'
            }
        )

        plt.title(
            f"{PROTOCOL_LABELS[protocol]} Priority Delivery Ratios",
            fontsize=TITLE_SIZE
        )

        plt.xlabel(
            "Priority Level",
            fontsize=LABEL_SIZE
        )

        plt.ylabel(
            "Network Load",
            fontsize=LABEL_SIZE
        )

        save_figure(
            f"{protocol}_priority_heatmap.png"
        )

# =========================================================
# PRIORITY BAR CHARTS
# =========================================================

def generate_priority_comparison_charts():

    for load in loads:

        rows = []

        for protocol in protocols:

            subset = summary[
                (summary["protocol"] == protocol)
                &
                (summary["load"] == load)
            ]

            for priority in priority_levels:

                rows.append({

                    "Protocol": PROTOCOL_LABELS[protocol],
                    "Priority": priority,
                    "Delivery": subset.iloc[0][
                        f"{priority}_deliveryRate"
                    ]
                })

        chart_df = pd.DataFrame(rows)

        plt.figure(figsize=(9, 5))

        sns.barplot(
            data=chart_df,
            x="Priority",
            y="Delivery",
            hue="Protocol"
        )

        plt.title(
            f"Priority Delivery Ratios ({load_labels[load]} Load)",
            fontsize=TITLE_SIZE
        )

        plt.xlabel(
            "Priority Level",
            fontsize=LABEL_SIZE
        )

        plt.ylabel(
            "Delivery Ratio (%)",
            fontsize=LABEL_SIZE
        )

        plt.xticks(fontsize=TICK_SIZE)
        plt.yticks(fontsize=TICK_SIZE)

        plt.legend(fontsize=LEGEND_SIZE)

        save_figure(
            f"priority_delivery_{load}.png"
        )

# =========================================================
# THESIS SUMMARY TABLE
# =========================================================

def generate_thesis_summary_table():

    display_df = summary[[

        "protocol",
        "load",
        "delivery_prob",
        "abort_prob",
        "latency_avg",
        "hopcount_avg",
        "overhead_ratio"

    ]].copy()

    display_df["protocol"] = display_df[
        "protocol"
    ].map(PROTOCOL_LABELS)

    display_df["load"] = display_df[
        "load"
    ].map(load_labels)

    display_df.columns = [

        "Protocol",
        "Load",
        "Delivery",
        "Abort",
        "Latency",
        "Hop Count",
        "Overhead"
    ]

    display_df = display_df.round(2)

    fig, ax = plt.subplots(
        figsize=(12, 3.5)
    )

    ax.axis('off')

    table = ax.table(
        cellText=display_df.values,
        colLabels=display_df.columns,
        loc='center'
    )

    table.auto_set_font_size(False)

    table.set_fontsize(10)

    table.scale(1.15, 1.7)

    for (row, col), cell in table.get_celld().items():

        if row == 0:

            cell.set_text_props(weight='bold')
            cell.set_facecolor('#d9e6f2')

    plt.title(
        "Overall DTN Protocol Performance Summary",
        fontsize=16,
        weight='bold'
    )

    save_figure(
        "thesis_summary_table.png"
    )

# =========================================================
# STANDARD METRICS
# =========================================================

standard_metrics = {

    "delivery_prob": "Delivery Ratio",
    "abort_prob": "Abort Probability",
    "latency_avg": "Average Latency (sec)",
    "hopcount_avg": "Average Hop Count",
    "overhead_ratio": "Overhead Ratio"
}

# =========================================================
# GENERATE FIGURES
# =========================================================

for metric, ylabel in standard_metrics.items():

    generate_clean_line_plot(
        metric,
        ylabel,
        f"{metric}_line.png"
    )

    generate_grouped_bar_chart(
        metric,
        ylabel,
        f"{metric}_bar.png"
    )

generate_priority_heatmaps()

generate_priority_comparison_charts()

generate_thesis_summary_table()

# =========================================================
# FINAL REPORT
# =========================================================

print("\n=================================================")
print("ALL THESIS-QUALITY FIGURES GENERATED")
print("=================================================\n")

print("Generated Files:\n")

generated_files = [

    "delivery_prob_line.png",
    "delivery_prob_bar.png",

    "abort_prob_line.png",
    "abort_prob_bar.png",

    "latency_avg_line.png",
    "latency_avg_bar.png",

    "hopcount_avg_line.png",
    "hopcount_avg_bar.png",

    "overhead_ratio_line.png",
    "overhead_ratio_bar.png",

    "prophet_priority_heatmap.png",
    "epidemic_priority_heatmap.png",
    "sprayAndWait_priority_heatmap.png",

    "priority_delivery_low_load.png",
    "priority_delivery_high_load.png",
    "priority_delivery_extreme_load.png",

    "thesis_summary_table.png"
]

for file in generated_files:

    print(file)

print("\nDONE.\n")