#!/usr/bin/env python3
"""
generate_configs.py
-------------------
Generates ONE simulator config files for a density vs delivery rate study.

- 13 node counts: 25, 50, 75, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000
- 5 priority groups, equal size, all pedestrians
- Host ranges, buffer sizes, and event generators scale with node count
- Message interval scales down slightly at higher densities to keep load proportional
- Output: configs/prophet_density_<N>_pedestrians.txt for each N
"""

import os
import math

# ─── Node counts to generate ──────────────────────────────────────────────────
NODE_COUNTS = [25, 50, 75, 100, 150, 200, 250, 300, 400, 500]

# ─── Fixed simulation parameters ──────────────────────────────────────────────
SIM_END_TIME   = 43200          # 12 hours
UPDATE_INTERVAL = 0.5
WARMUP         = 4000
TRANSMIT_SPEED = "250k"
TRANSMIT_RANGE = 10
SPEED_MIN      = 0.5
SPEED_MAX      = 1.5
WAIT_MIN       = 0
WAIT_MAX       = 120
MSG_TTL        = 300
MSG_SIZE_MIN   = "500k"
MSG_SIZE_MAX   = "1M"

# Message generation interval: slightly tighter at high density so
# total network load grows sub-linearly (avoids buffer saturation).
# Base interval for 25 nodes = 35-50s; scales by sqrt(N/25).
BASE_INTERVAL_MIN = 35
BASE_INTERVAL_MAX = 50

# Buffer sizes per priority (bytes), scale linearly with group size
# so per-node buffer stays constant.
BASE_BUFFERS = {5: "200M", 4: "180M", 3: "160M", 2: "140M", 1: "120M"}

# Priority → group index (1-based), router, group ID prefix
PRIORITIES = [
    (5, "ProphetBroadcastRouter", "p5"),
    (4, "ProphetV2Router",        "p4"),
    (3, "ProphetV2Router",        "p3"),
    (2, "ProphetV2Router",        "p2"),
    (1, "ProphetV2Router",        "p1"),
]

# Event prefix per priority
EVENT_PREFIXES = {5: "A", 4: "B", 3: "C", 2: "D", 1: "E"}

OUTPUT_DIR = "configs"

# ─── Template ─────────────────────────────────────────────────────────────────

def make_config(n_total):
    n_per_group = n_total // 5          # integer division; always exact for our counts
    remainder   = n_total % 5           # distribute remainder to first groups if needed

    # Build group host ranges
    groups = []
    cursor = 0
    for i, (priority, router, gid) in enumerate(PRIORITIES):
        size = n_per_group + (1 if i < remainder else 0)
        start = cursor
        end   = cursor + size - 1
        groups.append({
            "index":    i + 1,
            "priority": priority,
            "router":   router,
            "gid":      gid,
            "size":     size,
            "start":    start,
            "end":      end,
            "buffer":   BASE_BUFFERS[priority],
        })
        cursor = end + 1

    # Scale message interval: sqrt scaling keeps per-link load roughly constant
    scale = math.sqrt(n_total / 25)
    interval_min = max(5,  int(BASE_INTERVAL_MIN / scale))
    interval_max = max(10, int(BASE_INTERVAL_MAX / scale))

    lines = []

    # ── Header comment ─────────────────────────────────────────────────────────
    lines += [
        f"#",
        f"# prophet_density_{n_total}_pedestrians.txt",
        f"# PRoPHET routing — Density vs Delivery Rate study",
        f"# Beirut map — {n_total} nodes, all pedestrians, 5 priority groups",
        f"#",
        f"# Node count breakdown (total = {n_total}):",
    ]
    for g in groups:
        lines.append(
            f"#   Group{g['index']} (p{g['priority']}) = {g['size']:4d}  "
            f"priority {g['priority']}  buffer {g['buffer']}  "
            f"hosts {g['start']}-{g['end']}"
        )
    lines += [f"#                     ---", f"#                     {n_total}", f""]

    # ── Scenario ───────────────────────────────────────────────────────────────
    lines += [
        f"Scenario.name = prophet_battery_scenario",
        f"Scenario.simulateConnections = true",
        f"Scenario.updateInterval = {UPDATE_INTERVAL}",
        f"Scenario.endTime = {SIM_END_TIME}",
        f"",
    ]

    # ── Interface ──────────────────────────────────────────────────────────────
    lines += [
        f"btInterface.type = SimpleBroadcastInterface",
        f"btInterface.transmitSpeed = {TRANSMIT_SPEED}",
        f"btInterface.transmitRange = {TRANSMIT_RANGE}",
        f"",
        f"Scenario.nrofHostGroups = 5",
        f"",
        f"# --- Global defaults ---",
        f"Group.movementModel = ShortestPathMapBasedMovement",
        f"Group.router = ProphetV2Router",
        f"Group.waitTime = {WAIT_MIN}, {WAIT_MAX}",
        f"Group.nrofInterfaces = 1",
        f"Group.interface1 = btInterface",
        f"Group.speed = {SPEED_MIN}, {SPEED_MAX}",
        f"Group.msgTtl = {MSG_TTL}",
        f"Group.nrofHosts = 1",
        f"",
    ]

    # ── Groups ─────────────────────────────────────────────────────────────────
    for g in groups:
        p_label = {5:"P5", 4:"P4", 3:"P3", 2:"P2", 1:"P1"}[g["priority"]]
        lines += [
            f"# --- Group {g['index']}: Pedestrians {p_label} ---",
            f"Group{g['index']}.groupID = {g['gid']}",
            f"Group{g['index']}.nrofHosts = {g['size']}",
            f"Group{g['index']}.movementModel = ShortestPathMapBasedMovement",
            f"Group{g['index']}.router = {g['router']}",
            f"Group{g['index']}.bufferSize = {g['buffer']}",
            f"Group{g['index']}.waitTime = {WAIT_MIN}, {WAIT_MAX}",
            f"Group{g['index']}.speed = {SPEED_MIN}, {SPEED_MAX}",
            f"Group{g['index']}.msgTtl = {MSG_TTL}",
            f"Group{g['index']}.nrofInterfaces = 1",
            f"Group{g['index']}.interface1 = btInterface",
            f"Group{g['index']}.priority = {g['priority']}",
            f"",
        ]

    # ── Events ─────────────────────────────────────────────────────────────────
    lines += [
        f"# --- Message generation (one generator per priority group) ---",
        f"Events.nrof = 5",
        f"",
    ]
    for idx, g in enumerate(groups, start=1):
        prefix = EVENT_PREFIXES[g["priority"]]
        lines += [
            f"Events{idx}.class = MessageEventGenerator",
            f"Events{idx}.interval = {interval_min}, {interval_max}",
            f"Events{idx}.size = {MSG_SIZE_MIN}, {MSG_SIZE_MAX}",
            f"Events{idx}.hosts = {g['start']}, {g['end']}",
            f"Events{idx}.tohosts = 0, {n_total - 1}",
            f"Events{idx}.prefix = {prefix}",
            f"Events{idx}.priority = {g['priority']}",
            f"",
        ]

    # ── Movement model ─────────────────────────────────────────────────────────
    lines += [
        f"# --- Movement model ---",
        f"MovementModel.rngSeed = 1",
        f"MovementModel.worldSize = 11300, 3645",
        f"MovementModel.warmup = {WARMUP}",
        f"",
        f"# --- Map files ---",
        f"MapBasedMovement.nrofMapFiles = 4",
        f"MapBasedMovement.mapFile1 = data/roads.wkt",
        f"MapBasedMovement.mapFile2 = data/main_roads.wkt",
        f"MapBasedMovement.mapFile3 = data/pedestrian_paths.wkt",
        f"MapBasedMovement.mapFile4 = data/shops.wkt",
        f"",
        f"# --- Reports ---",
        f"Report.nrofReports = 1",
        f"Report.warmup = {WARMUP}",
        f"Report.reportDir = reports/",
        f"Report.report1 = MessageTransferReport",
        f"",
        f"# --- Router settings ---",
        f"ProphetV2Router.secondsInTimeUnit = 30",
        f"",
        f"ProphetBroadcastRouter.secondsInTimeUnit = 30",
        f"ProphetBroadcastRouter.beta = 0.9",
        f"ProphetBroadcastRouter.relayThreshold = 0.05",
        f"",
        f"# --- Optimizations ---",
        f"Optimization.cellSizeMult = 5",
        f"Optimization.randomizeUpdateOrder = false",
        f"",
        f"# --- GUI ---",
        f"GUI.UnderlayImage.fileName = data/beirut_underlay.png",
        f"GUI.UnderlayImage.offset = 0, 452",
        f"GUI.UnderlayImage.scale = 0.2011",
        f"GUI.UnderlayImage.rotate = 0",
        f"",
        f"GUI.EventLogPanel.nrofEvents = 100",
    ]

    return "\n".join(lines)


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for n in NODE_COUNTS:
        filename = os.path.join(OUTPUT_DIR, f"prophet_density_{n}_pedestrians.txt")
        content  = make_config(n)
        with open(filename, "w") as f:
            f.write(content)
        print(f"  wrote {filename}")

    print(f"\nDone — {len(NODE_COUNTS)} configs in ./{OUTPUT_DIR}/")
    print("\nHost range summary:")
    print(f"{'N':>6}  {'G1(p5)':>10}  {'G2(p4)':>10}  {'G3(p3)':>10}  {'G4(p2)':>10}  {'G5(p1)':>10}  {'interval':>10}")
    print("-" * 76)
    for n in NODE_COUNTS:
        npg = n // 5
        rem = n % 5
        ranges = []
        cur = 0
        for i in range(5):
            sz = npg + (1 if i < rem else 0)
            ranges.append(f"{cur}-{cur+sz-1}")
            cur += sz
        scale = math.sqrt(n / 25)
        imin = max(5,  int(BASE_INTERVAL_MIN / scale))
        imax = max(10, int(BASE_INTERVAL_MAX / scale))
        row = f"{n:>6}  " + "  ".join(f"{r:>10}" for r in ranges) + f"  {imin}-{imax}s"
        print(row)


if __name__ == "__main__":
    main()
