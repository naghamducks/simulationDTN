import os
import re
import pandas as pd
import matplotlib.pyplot as plt

# =========================================================
# CONFIGURATION
# =========================================================

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

# =========================================================
# BASIC METRIC PATTERNS
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

# =========================================================
# PRIORITY COUNT PATTERNS
# =========================================================

priority_patterns = {

    "P5": r"P5 .*?created:(\d+).*?delivered:(\d+).*?aborted:(\d+).*?relays:(\d+)",
    "P4": r"P4 .*?created:(\d+).*?delivered:(\d+).*?aborted:(\d+).*?relays:(\d+)",
    "P3": r"P3 .*?created:(\d+).*?delivered:(\d+).*?aborted:(\d+).*?relays:(\d+)",
    "P2": r"P2 .*?created:(\d+).*?delivered:(\d+).*?aborted:(\d+).*?relays:(\d+)",
    "P1": r"P1 .*?created:(\d+).*?delivered:(\d+).*?aborted:(\d+).*?relays:(\d+)"
}

# =========================================================
# ADVANCED PRIORITY METRICS
# =========================================================

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
# HELPER FUNCTION
# =========================================================

def extract_metric(content, pattern):

    match = re.search(pattern, content, re.DOTALL)

    if match:
        return float(match.group(1))

    return None

# =========================================================
# START DEBUG
# =========================================================

print("\n=================================================")
print("DTN PRIORITY ANALYSIS STARTED")
print("=================================================\n")

print("BASE DIRECTORY:")
print(BASE_DIR)

if not os.path.exists(BASE_DIR):

    print("\nERROR: BASE DIRECTORY DOES NOT EXIST")
    exit()

# =========================================================
# MAIN PARSING LOOP
# =========================================================

for protocol in protocols:

    print(f"\n=================================================")
    print(f"PROCESSING PROTOCOL: {protocol.upper()}")
    print("=================================================\n")

    protocol_path = os.path.join(BASE_DIR, protocol)

    if not os.path.exists(protocol_path):

        print("PROTOCOL FOLDER NOT FOUND")
        continue

    # -----------------------------------------------------
    # LOAD LOOP
    # -----------------------------------------------------

    for load in loads:

        print(f"\n---------------- LOAD: {load} ----------------\n")

        load_path = os.path.join(protocol_path, load)

        if not os.path.exists(load_path):

            print("LOAD FOLDER MISSING")
            continue

        run_folders = sorted(os.listdir(load_path))

        if len(run_folders) == 0:

            print("NO RUNS FOUND")
            continue

        # -------------------------------------------------
        # RUN LOOP
        # -------------------------------------------------

        for run_folder in run_folders:

            run_path = os.path.join(load_path, run_folder)

            if not os.path.isdir(run_path):
                continue

            files = os.listdir(run_path)

            stats_file = None

            # -------------------------------------------------
            # FIND REPORT FILE
            # -------------------------------------------------

            for file in files:

                if "MessageTransferReport" in file:

                    stats_file = os.path.join(run_path, file)
                    break

            if stats_file is None:

                print("NO MESSAGE TRANSFER REPORT FOUND")
                continue

            # -------------------------------------------------
            # READ FILE
            # -------------------------------------------------

            try:

                with open(stats_file, "r", encoding="utf-8") as f:

                    content = f.read()

            except Exception as e:

                print("FILE READ ERROR:")
                print(e)
                continue

            # -------------------------------------------------
            # CREATE ROW
            # -------------------------------------------------

            row = {

                "protocol": protocol,
                "load": load,
                "run": run_folder
            }

            # -------------------------------------------------
            # BASIC METRICS
            # -------------------------------------------------

            for metric, pattern in metrics_patterns.items():

                value = extract_metric(content, pattern)
                row[metric] = value

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

            # -------------------------------------------------
            # STORE ROW
            # -------------------------------------------------

            all_results.append(row)

# =========================================================
# FINAL DEBUG
# =========================================================

print("\n=================================================")
print("FINAL DEBUG")
print("=================================================\n")

print("TOTAL ROWS PARSED:")
print(len(all_results))

if len(all_results) == 0:

    print("\nERROR: NO DATA PARSED")
    exit()

# =========================================================
# CREATE DATAFRAME
# =========================================================

df = pd.DataFrame(all_results)

print("\n=================================================")
print("RAW DATAFRAME")
print("=================================================\n")

print(df.head())

# =========================================================
# SAVE RAW RESULTS
# =========================================================

df.to_csv("priority_network_results.csv", index=False)

print("\nSaved: priority_network_results.csv")

# =========================================================
# SUMMARY STATISTICS
# =========================================================

summary = df.groupby(["protocol", "load"]).mean(numeric_only=True).reset_index()

summary.to_csv("priority_summary_statistics.csv", index=False)

print("\nSaved: priority_summary_statistics.csv")

# =========================================================
# TABLE GENERATION FUNCTION
# =========================================================

def generate_metric_table(metric, ylabel, filename):

    table_df = summary.pivot(
        index="load",
        columns="protocol",
        values=metric
    )

    table_df = table_df.reindex(loads)

    table_df.index = [
        load_labels[x]
        for x in table_df.index
    ]

    table_df = table_df.round(2)

    fig, ax = plt.subplots(figsize=(8, 3))

    ax.axis('off')

    table = ax.table(
        cellText=table_df.values,
        rowLabels=table_df.index,
        colLabels=table_df.columns,
        loc='center'
    )

    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 1.8)

    plt.title(ylabel)

    plt.savefig(filename, dpi=300, bbox_inches='tight')

    plt.close()

    print(f"Generated Table: {filename}")

# =========================================================
# PLOT GENERATION FUNCTION
# =========================================================

def generate_line_plot(metric, ylabel, filename):

    plt.figure(figsize=(8,5))

    for protocol in protocols:

        subset = summary[summary["protocol"] == protocol]

        subset = subset.set_index("load")

        available_loads = [

            l for l in loads
            if l in subset.index
        ]

        subset = subset.loc[available_loads].reset_index()

        x_labels = [
            load_labels[x]
            for x in subset["load"]
        ]

        plt.plot(
            x_labels,
            subset[metric],
            marker='o',
            linewidth=2,
            label=protocol
        )

    plt.title(ylabel)

    plt.xlabel("Network Load")

    plt.ylabel(ylabel)

    plt.grid(True)

    plt.legend()

    plt.savefig(filename, dpi=300, bbox_inches='tight')

    plt.close()

    print(f"Generated Plot: {filename}")

# =========================================================
# STANDARD METRICS
# =========================================================

standard_metrics = {

    "delivery_prob": "Delivery Probability (%)",
    "abort_prob": "Abort Probability (%)",
    "latency_avg": "Average Latency (sec)",
    "hopcount_avg": "Average Hop Count",
    "overhead_ratio": "Overhead Ratio"
}

# =========================================================
# GENERATE STANDARD PLOTS + TABLES
# =========================================================

for metric, ylabel in standard_metrics.items():

    generate_line_plot(
        metric,
        ylabel,
        f"{metric}_comparison.png"
    )

    generate_metric_table(
        metric,
        ylabel,
        f"{metric}_table.png"
    )

# =========================================================
# PRIORITY DELIVERY RATE TABLES + PLOTS
# =========================================================

priority_levels = ["P5", "P4", "P3", "P2", "P1"]

for priority in priority_levels:

    metric = f"{priority}_deliveryRate"

    generate_line_plot(
        metric,
        f"{priority} Delivery Rate (%)",
        f"{priority}_deliveryRate_comparison.png"
    )

    generate_metric_table(
        metric,
        f"{priority} Delivery Rate (%)",
        f"{priority}_deliveryRate_table.png"
    )

# =========================================================
# PRIORITY LATENCY TABLES + PLOTS
# =========================================================

for priority in priority_levels:

    metric = f"{priority}_avgLatency"

    generate_line_plot(
        metric,
        f"{priority} Average Latency (sec)",
        f"{priority}_avgLatency_comparison.png"
    )

    generate_metric_table(
        metric,
        f"{priority} Average Latency (sec)",
        f"{priority}_avgLatency_table.png"
    )

# =========================================================
# PRIORITY HOPS TABLES + PLOTS
# =========================================================

for priority in priority_levels:

    metric = f"{priority}_avgHops"

    generate_line_plot(
        metric,
        f"{priority} Average Hop Count",
        f"{priority}_avgHops_comparison.png"
    )

    generate_metric_table(
        metric,
        f"{priority} Average Hop Count",
        f"{priority}_avgHops_table.png"
    )

# =========================================================
# COMBINED SUMMARY TABLE
# =========================================================

combined_metrics = [

    "delivery_prob",
    "abort_prob",
    "latency_avg",
    "hopcount_avg",
    "overhead_ratio"

]

combined_table = summary[[
    "protocol",
    "load"
] + combined_metrics]

combined_table["load"] = combined_table["load"].map(load_labels)

combined_table = combined_table.round(2)

combined_table.to_csv(
    "combined_summary_table.csv",
    index=False
)

print("\nGenerated: combined_summary_table.csv")

# =========================================================
# INTERPRETATION OUTPUT
# =========================================================

print("\n=================================================")
print("INTERPRETATION")
print("=================================================\n")

for protocol in protocols:

    print(f"\n#################################################")
    print(f"############ {protocol.upper()} ############")
    print("#################################################\n")

    proto_data = summary[
        summary["protocol"] == protocol
    ]

    for _, row in proto_data.iterrows():

        print(f"""
LOAD: {row['load']}

================ BASIC METRICS ================

Delivery Probability : {row['delivery_prob']:.2f}%
Abort Probability    : {row['abort_prob']:.2f}%
Average Latency      : {row['latency_avg']:.2f} sec
Average Hop Count    : {row['hopcount_avg']:.2f}
Overhead Ratio       : {row['overhead_ratio']:.2f}

================ PRIORITY DELIVERY RATES ================

P5 DISTRESS  : {row['P5_deliveryRate']:.2f}%
P4 HIGH      : {row['P4_deliveryRate']:.2f}%
P3 MED-HIGH  : {row['P3_deliveryRate']:.2f}%
P2 MEDIUM    : {row['P2_deliveryRate']:.2f}%
P1 LOW       : {row['P1_deliveryRate']:.2f}%
""")

# =========================================================
# FINAL CONCLUSIONS
# =========================================================

print("\n=================================================")
print("FINAL AUTOMATED CONCLUSIONS")
print("=================================================\n")

overall_delivery = summary.groupby(
    "protocol"
)["delivery_prob"].mean().sort_values(
    ascending=False
)

overall_overhead = summary.groupby(
    "protocol"
)["overhead_ratio"].mean().sort_values()

overall_distress = summary.groupby(
    "protocol"
)["P5_deliveryRate"].mean().sort_values(
    ascending=False
)

print("BEST OVERALL DELIVERY PERFORMANCE:")

print(
    f"{overall_delivery.index[0]} "
    f"({overall_delivery.iloc[0]:.2f}%)"
)

print("\nLOWEST OVERALL OVERHEAD:")

print(
    f"{overall_overhead.index[0]} "
    f"({overall_overhead.iloc[0]:.2f})"
)

print("\nBEST DISTRESS MESSAGE PRESERVATION:")

print(
    f"{overall_distress.index[0]} "
    f"({overall_distress.iloc[0]:.2f}%)"
)

print("\n=================================================")
print("ANALYSIS COMPLETED")
print("=================================================\n")