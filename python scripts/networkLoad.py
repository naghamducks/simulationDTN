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
# DEBUG START
# =========================================================

print("\n=================================================")
print("DTN PRIORITY ANALYSIS STARTED")
print("=================================================\n")

print("BASE DIRECTORY:")
print(BASE_DIR)

if not os.path.exists(BASE_DIR):

    print("\nERROR: BASE DIRECTORY DOES NOT EXIST")
    exit()

print("\nAVAILABLE PROTOCOLS:")

for item in os.listdir(BASE_DIR):

    print(" -", item)

# =========================================================
# MAIN PARSING LOOP
# =========================================================

for protocol in protocols:

    print(f"\n=================================================")
    print(f"PROCESSING PROTOCOL: {protocol.upper()}")
    print("=================================================\n")

    protocol_path = os.path.join(BASE_DIR, protocol)

    if not os.path.exists(protocol_path):

        print("PROTOCOL FOLDER NOT FOUND:")
        print(protocol_path)
        continue

    # -----------------------------------------------------
    # LOAD LOOP
    # -----------------------------------------------------

    for load in loads:

        print(f"\n---------------- LOAD: {load} ----------------\n")

        load_path = os.path.join(protocol_path, load)

        print("LOAD PATH:")
        print(load_path)

        if not os.path.exists(load_path):

            print("LOAD FOLDER MISSING")
            continue

        run_folders = sorted(os.listdir(load_path))

        print("RUNS FOUND:")
        print(run_folders)

        if len(run_folders) == 0:

            print("NO RUNS FOUND")
            continue

        # -------------------------------------------------
        # RUN LOOP
        # -------------------------------------------------

        for run_folder in run_folders:

            run_path = os.path.join(load_path, run_folder)

            print("\nRUN PATH:")
            print(run_path)

            if not os.path.isdir(run_path):

                print("NOT A DIRECTORY")
                continue

            files = os.listdir(run_path)

            print("FILES:")
            print(files)

            stats_file = None

            # -------------------------------------------------
            # FIND REPORT FILE
            # -------------------------------------------------

            for file in files:

                if "MessageTransferReport" in file:

                    stats_file = os.path.join(run_path, file)

                    print("FOUND REPORT:")
                    print(stats_file)

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

                print("FILE READ SUCCESS")

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

            print("\nBASIC METRICS:")

            for metric, pattern in metrics_patterns.items():

                value = extract_metric(content, pattern)

                row[metric] = value

                print(f"{metric}: {value}")

            # -------------------------------------------------
            # PRIORITY COUNTS
            # -------------------------------------------------

            print("\nPRIORITY COUNTS:")

            for priority, pattern in priority_patterns.items():

                match = re.search(pattern, content, re.DOTALL)

                if match:

                    row[f"{priority}_created"] = int(match.group(1))
                    row[f"{priority}_delivered"] = int(match.group(2))
                    row[f"{priority}_aborted"] = int(match.group(3))
                    row[f"{priority}_relays"] = int(match.group(4))

                    print(f"{priority} parsed successfully")

                else:

                    row[f"{priority}_created"] = 0
                    row[f"{priority}_delivered"] = 0
                    row[f"{priority}_aborted"] = 0
                    row[f"{priority}_relays"] = 0

                    print(f"{priority} NOT FOUND")

            # -------------------------------------------------
            # ADVANCED PRIORITY METRICS
            # -------------------------------------------------

            print("\nADVANCED PRIORITY METRICS:")

            for priority, pattern in advanced_priority_patterns.items():

                match = re.search(pattern, content, re.DOTALL)

                if match:

                    row[f"{priority}_deliveryRate"] = float(match.group(1))
                    row[f"{priority}_avgLatency"] = float(match.group(2))
                    row[f"{priority}_avgHops"] = float(match.group(3))

                    print(f"{priority} advanced metrics parsed")

                else:

                    row[f"{priority}_deliveryRate"] = 0
                    row[f"{priority}_avgLatency"] = 0
                    row[f"{priority}_avgHops"] = 0

                    print(f"{priority} advanced metrics missing")

            # -------------------------------------------------
            # STORE ROW
            # -------------------------------------------------

            all_results.append(row)

            print("\nROW ADDED SUCCESSFULLY")

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

print("\nFIRST RESULT SAMPLE:\n")

print(all_results[0])

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

summary = df.groupby(["protocol", "load"]).mean().reset_index()

print("\n=================================================")
print("SUMMARY STATISTICS")
print("=================================================\n")

print(summary)

summary.to_csv("priority_summary_statistics.csv", index=False)

print("\nSaved: priority_summary_statistics.csv")

# =========================================================
# PLOT SETTINGS
# =========================================================

load_order = [
    "low_load",
    "high_load",
    "extreme_load"
]

# =========================================================
# STANDARD METRIC PLOTS
# =========================================================

plot_metrics = [

    "delivery_prob",
    "abort_prob",
    "latency_avg",
    "hopcount_avg",
    "overhead_ratio"

]

for metric in plot_metrics:

    plt.figure(figsize=(8,5))

    for protocol in protocols:

        subset = summary[summary["protocol"] == protocol]

        subset = subset.set_index("load")

        available_loads = [

            l for l in load_order
            if l in subset.index

        ]

        subset = subset.loc[available_loads].reset_index()

        plt.plot(

            subset["load"],
            subset[metric],
            marker='o',
            linewidth=2,
            label=protocol

        )

    plt.title(f"{metric} vs Network Load")

    plt.xlabel("Network Load")

    plt.ylabel(metric)

    plt.grid(True)

    plt.legend()

    filename = f"{metric}_comparison.png"

    plt.savefig(filename, dpi=300, bbox_inches='tight')

    plt.close()

    print(f"Generated: {filename}")

# =========================================================
# PRIORITY DELIVERY RATE PLOTS
# =========================================================

priority_levels = ["P5", "P4", "P3", "P2", "P1"]

for priority in priority_levels:

    plt.figure(figsize=(8,5))

    for protocol in protocols:

        subset = summary[summary["protocol"] == protocol]

        subset = subset.set_index("load")

        available_loads = [

            l for l in load_order
            if l in subset.index

        ]

        subset = subset.loc[available_loads].reset_index()

        plt.plot(

            subset["load"],
            subset[f"{priority}_deliveryRate"],
            marker='o',
            linewidth=2,
            label=protocol

        )

    plt.title(f"{priority} Delivery Rate vs Network Load")

    plt.xlabel("Network Load")

    plt.ylabel("Delivery Rate (%)")

    plt.grid(True)

    plt.legend()

    filename = f"{priority}_deliveryRate_comparison.png"

    plt.savefig(filename, dpi=300, bbox_inches='tight')

    plt.close()

    print(f"Generated: {filename}")

# =========================================================
# INTERPRETATION OUTPUT
# =========================================================
# =========================================================
# INTERPRETATION OUTPUT
# =========================================================

print("\n=================================================")
print("INTERPRETATION")
print("=================================================\n")

# ---------------------------------------------------------
# PER PROTOCOL ANALYSIS
# ---------------------------------------------------------

for protocol in protocols:

    print(f"\n#################################################")
    print(f"############ {protocol.upper()} ############")
    print("#################################################\n")

    proto_data = summary[summary["protocol"] == protocol]

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

================ PRIORITY LATENCIES ================

P5 Latency : {row['P5_avgLatency']:.2f} sec
P4 Latency : {row['P4_avgLatency']:.2f} sec
P3 Latency : {row['P3_avgLatency']:.2f} sec
P2 Latency : {row['P2_avgLatency']:.2f} sec
P1 Latency : {row['P1_avgLatency']:.2f} sec

================ PRIORITY HOP COUNTS ================

P5 Hops : {row['P5_avgHops']:.2f}
P4 Hops : {row['P4_avgHops']:.2f}
P3 Hops : {row['P3_avgHops']:.2f}
P2 Hops : {row['P2_avgHops']:.2f}
P1 Hops : {row['P1_avgHops']:.2f}
""")

# ---------------------------------------------------------
# COMPARATIVE ANALYSIS
# ---------------------------------------------------------

print("\n=================================================")
print("CROSS-PROTOCOL COMPARISON")
print("=================================================\n")

for load in load_order:

    print(f"\n#################################################")
    print(f"############ LOAD: {load.upper()} ############")
    print("#################################################\n")

    load_data = summary[summary["load"] == load]

    # -----------------------------------------------------
    # DELIVERY RANKING
    # -----------------------------------------------------

    best_delivery = load_data.sort_values(
        by="delivery_prob",
        ascending=False
    )

    print("DELIVERY PROBABILITY RANKING:")

    for i, (_, row) in enumerate(best_delivery.iterrows(), start=1):

        print(
            f"{i}. {row['protocol']} "
            f"-> {row['delivery_prob']:.2f}%"
        )

    # -----------------------------------------------------
    # OVERHEAD RANKING
    # -----------------------------------------------------

    best_overhead = load_data.sort_values(
        by="overhead_ratio",
        ascending=True
    )

    print("\nLOWEST OVERHEAD RANKING:")

    for i, (_, row) in enumerate(best_overhead.iterrows(), start=1):

        print(
            f"{i}. {row['protocol']} "
            f"-> {row['overhead_ratio']:.2f}"
        )

    # -----------------------------------------------------
    # LATENCY RANKING
    # -----------------------------------------------------

    best_latency = load_data.sort_values(
        by="latency_avg",
        ascending=True
    )

    print("\nLOWEST LATENCY RANKING:")

    for i, (_, row) in enumerate(best_latency.iterrows(), start=1):

        print(
            f"{i}. {row['protocol']} "
            f"-> {row['latency_avg']:.2f} sec"
        )

    # -----------------------------------------------------
    # DISTRESS MESSAGE ANALYSIS
    # -----------------------------------------------------

    distress_best = load_data.sort_values(
        by="P5_deliveryRate",
        ascending=False
    )

    print("\nDISTRESS MESSAGE PRESERVATION (P5):")

    for i, (_, row) in enumerate(distress_best.iterrows(), start=1):

        print(
            f"{i}. {row['protocol']} "
            f"-> {row['P5_deliveryRate']:.2f}%"
        )

    # -----------------------------------------------------
    # CONGESTION INTERPRETATION
    # -----------------------------------------------------

    print("\nCONGESTION ANALYSIS:")

    for _, row in load_data.iterrows():

        protocol_name = row['protocol']

        overhead = row['overhead_ratio']

        delivery = row['delivery_prob']

        if overhead > 10:

            congestion = "EXTREME FLOODING"

        elif overhead > 5:

            congestion = "HIGH CONGESTION"

        elif overhead > 2:

            congestion = "MODERATE CONGESTION"

        else:

            congestion = "LOW CONGESTION"

        print(
            f"{protocol_name}: "
            f"{congestion} "
            f"(Overhead={overhead:.2f}, "
            f"Delivery={delivery:.2f}%)"
        )

# ---------------------------------------------------------
# FINAL CONCLUSIONS
# ---------------------------------------------------------

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