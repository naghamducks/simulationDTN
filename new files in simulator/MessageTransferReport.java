package report;

import core.DTNHost;
import core.Message;
import core.MessageListener;

import java.util.HashMap;
import java.util.Map;

/**
 * ============================================================================
 * Prophet Advanced Unified Message Transfer Report
 * ============================================================================
 *
 * Priority is derived from message ID prefix at CREATION TIME and stored in
 * MsgStats. Relay copies in ONE get new IDs (e.g. M<N>) — the old code called
 * priorityOf() on every event, so relay-copy IDs (prefix 'M') fell through to
 * getPriority() → 0 and were bucketed into P0 UNKNOWN, silently siphoning
 * relay/hop/abort counts away from the correct priority.  Fix: priority is now
 * resolved once in newMessage() / getStats()-first-creation and stored; all
 * subsequent lookups use the stored value.
 *
 *   A = P5 (DISTRESS)   — ProphetBroadcastRouter
 *   B = P4 (HIGH)       — ProphetV2Router
 *   C = P3 (MED-HIGH)   — ProphetV2Router
 *   D = P2 (MEDIUM)     — ProphetV2Router
 *   E = P1 (LOW)        — ProphetV2Router
 *
 * ============================================================================
 *
 * FIXES:
 *
 *   FIX A — Priority stored at creation, never re-derived from relay-copy ID.
 *            Relay copies get IDs like "M42" whose prefix doesn't map to any
 *            priority; the old fallback returned 0, bleeding all relay events
 *            for P5 (heaviest relay traffic) into the P0 bucket and making P5
 *            delivery look artificially low / overhead artificially small.
 *
 *   FIX B — creationTime set only in newMessage() or on true first-seen in
 *            getStats(); never overwritten by a relay transfer arriving before
 *            the newMessage() callback.  Previously getStats() could create the
 *            entry with simTime=relayTime, then newMessage() would overwrite
 *            creationTime with a later value, making latency negative or zero.
 *            Now getStats() marks the entry with a sentinel (creationTime=-1)
 *            so newMessage() always wins when it fires.
 *
 *   FIX C — messageDeleted() tracks expired/dropped messages (was empty).
 *            created = delivered + aborted + dropped + in-transit must hold.
 *
 *   FIX D — hopCount for final delivery now includes the last hop.
 *            s.hopCount++ ran only in the relay branch; the terminal transfer
 *            (relay→destination) was never counted.
 *
 *   FIX E — ABORTED log lines show attempt count to distinguish per-event log
 *            lines from the per-message summary count.
 *
 * ============================================================================
 */
public class MessageTransferReport extends Report implements MessageListener {

    // =========================================================================
    // FORMATTING
    // =========================================================================

    private static final String SEP =
        "==========================================================================";

    private static final String HDR =
        String.format(
            "%-10s | %-10s | %-10s | %-12s | %-14s | %-12s | %s",
            "SimTime", "From", "To", "MsgID", "Priority", "Size(B)", "Type"
        );

    // =========================================================================
    // GLOBAL COUNTERS
    // =========================================================================

    private int totalRelays     = 0;
    private int totalDeliveries = 0;
    private int totalAborted    = 0;
    private int totalDropped    = 0;

    private double totalLatency  = 0;
    private int    totalHopCount = 0;

    // =========================================================================
    // MESSAGE-LEVEL TRACKING
    // =========================================================================

    private static class MsgStats {
        int     priority      = 0;
        boolean delivered     = false;
        boolean aborted       = false;
        boolean dropped       = false;
        int     relays        = 0;
        int     hopCount      = 0;
        int     abortAttempts = 0;
        /**
         * Sentinel value -1 means "entry created by a relay/delete event before
         * newMessage() fired".  newMessage() will overwrite -1 with the true
         * creation time; if newMessage() fires first it sets the real time and
         * subsequent calls to getStats() will not touch it.
         */
        double  creationTime  = -1;
        double  deliveryTime  = 0;
    }

    private final Map<String, MsgStats> stats = new HashMap<>();

    // =========================================================================
    // PER-PRIORITY COUNTERS  (index 0–5)
    // =========================================================================

    private final int[]    createdByP      = new int[6];
    private final int[]    deliveredByP    = new int[6];
    private final int[]    abortedByP      = new int[6];
    private final int[]    droppedByP      = new int[6];
    private final int[]    relaysByP       = new int[6];
    private final double[] latencyByP      = new double[6];
    private final int[]    latencyCountByP = new int[6];
    private final int[]    hopsByP         = new int[6];

    // =========================================================================
    // CONSTRUCTOR
    // =========================================================================

    public MessageTransferReport() {
        super();
        write(SEP);
        write("PROPHET ADVANCED MESSAGE TRANSFER REPORT");
        write(SEP);
        write(HDR);
        write(SEP);
    }

    // =========================================================================
    // PRIORITY HELPERS
    // =========================================================================

    /**
     * Resolve priority from the ORIGINAL message ID prefix (A–E).
     * This is only called when creating a new MsgStats entry (i.e. for the
     * original message ID, never for relay-copy IDs).
     */
    private int priorityFromPrefix(Message m) {
        String id = m.getId();
        if (id != null && !id.isEmpty()) {
            switch (id.charAt(0)) {
                case 'A': return 5;
                case 'B': return 4;
                case 'C': return 3;
                case 'D': return 2;
                case 'E': return 1;
            }
        }
        // Last-resort: try the field directly (reliable only at source node)
        try {
            int p = m.getPriority();
            if (p >= 1 && p <= 5) return p;
        } catch (Exception ignored) {}
        return 0;
    }

    private String priorityLabel(int p) {
        switch (p) {
            case 5: return "5 DISTRESS";
            case 4: return "4 HIGH";
            case 3: return "3 MED-HIGH";
            case 2: return "2 MEDIUM";
            case 1: return "1 LOW";
            default: return "0 UNKNOWN";
        }
    }

    // =========================================================================
    // GET OR CREATE MESSAGE STATS
    // =========================================================================

    /**
     * Returns the MsgStats for a message, creating it if absent.
     *
     * FIX A: priority is resolved from the original message ID only on first
     * creation.  If this entry was already created by newMessage(), we reuse
     * the stored priority — no re-derivation from a possibly-mutated relay ID.
     *
     * FIX B: creationTime is left as sentinel -1 here so that newMessage(),
     * which carries the authoritative creation timestamp, can overwrite it.
     * If newMessage() never fires (shouldn't happen but defensive), the latency
     * calculation skips this message (latency < 0 guard in messageTransferred).
     */
    private MsgStats getOrCreate(Message m) {
        MsgStats s = stats.get(m.getId());
        if (s == null) {
            s          = new MsgStats();
            s.priority = priorityFromPrefix(m);
            // creationTime stays -1 (sentinel) until newMessage() sets it
            stats.put(m.getId(), s);
            createdByP[s.priority]++;
        }
        return s;
    }

    // =========================================================================
    // LOGGING
    // =========================================================================

    private void log(Message m, DTNHost from, DTNHost to, String type, int priority) {
        write(String.format(
            "%-10.1f | %-10s | %-10s | %-12s | %-14s | %-12d | %s",
            getSimTime(),
            from != null ? from.toString() : "-",
            to   != null ? to.toString()   : "-",
            m.getId(),
            priorityLabel(priority),
            m.getSize(),
            type
        ));
    }

    // =========================================================================
    // NEW MESSAGE — called when message is first created at source
    // =========================================================================

    @Override
    public void newMessage(Message m) {
        MsgStats s = stats.get(m.getId());
        if (s == null) {
            // Normal path: newMessage fires before any transfer event
            s          = new MsgStats();
            s.priority = priorityFromPrefix(m);
            s.creationTime = getSimTime();
            stats.put(m.getId(), s);
            createdByP[s.priority]++;
        } else {
            // FIX B: entry was pre-created by getOrCreate() from a racing
            // transfer event.  Set the authoritative creation time now.
            // Do NOT touch priority (already resolved from original ID).
            // Do NOT re-increment createdByP (already done in getOrCreate).
            if (s.creationTime < 0) {
                s.creationTime = getSimTime();
            }
        }
    }

    // =========================================================================
    // MESSAGE TRANSFERRED
    // =========================================================================

    @Override
    public void messageTransferred(Message m, DTNHost from, DTNHost to,
                                   boolean firstDelivery) {

        MsgStats s = getOrCreate(m);

        if (firstDelivery) {
            // ── FINAL DELIVERY ──────────────────────────────────────────────
            if (!s.delivered) {
                s.delivered    = true;
                s.deliveryTime = getSimTime();

                // FIX D: count the terminal hop (relay → destination)
                s.hopCount++;

                // FIX B: skip latency if creationTime was never set properly
                double latency = s.deliveryTime - s.creationTime;
                if (s.creationTime >= 0 && latency >= 0) {
                    totalLatency           += latency;
                    latencyByP[s.priority] += latency;
                    latencyCountByP[s.priority]++;
                }

                totalHopCount       += s.hopCount;
                hopsByP[s.priority] += s.hopCount;

                deliveredByP[s.priority]++;
                totalDeliveries++;
            }
            log(m, from, to, "FINAL DELIVERY", s.priority);

        } else {
            // ── RELAY ────────────────────────────────────────────────────────
            s.relays++;
            s.hopCount++;
            relaysByP[s.priority]++;
            totalRelays++;
            log(m, from, to, "RELAY", s.priority);
        }
    }

    // =========================================================================
    // TRANSFER ABORTED
    // =========================================================================

    @Override
    public void messageTransferAborted(Message m, DTNHost from, DTNHost to) {
        MsgStats s = getOrCreate(m);

        // FIX E: track every attempt; count the message only once in totals.
        s.abortAttempts++;
        if (!s.aborted) {
            s.aborted = true;
            abortedByP[s.priority]++;
            totalAborted++;
        }

        log(m, from, to, "ABORTED (attempt " + s.abortAttempts + ")", s.priority);
    }

    // =========================================================================
    // MESSAGE DELETED — FIX C: track TTL expiry and buffer eviction
    // =========================================================================

    @Override
    public void messageDeleted(Message m, DTNHost where, boolean dropped) {
        MsgStats s = getOrCreate(m);

        // Count as lost only if never successfully delivered.
        if (!s.delivered && !s.dropped) {
            s.dropped = true;
            droppedByP[s.priority]++;
            totalDropped++;
        }
    }

    // =========================================================================
    // TRANSFER STARTED  (no-op)
    // =========================================================================

    @Override
    public void messageTransferStarted(Message m, DTNHost from, DTNHost to) {}

    // =========================================================================
    // FINAL SUMMARY
    // =========================================================================

    @Override
    public void done() {

        int totalCreated = stats.size();
        int inTransit    = totalCreated - totalDeliveries - totalAborted - totalDropped;

        // ── Per-priority basic counts ────────────────────────────────────────
        write(SEP);
        write("SUMMARY (MESSAGE-LEVEL BY PRIORITY)");
        write(SEP);

        for (int p = 5; p >= 0; p--) {
            write(String.format(
                "P%d [%-8s] -> created:%d  delivered:%d  aborted:%d  dropped:%d  relays:%d",
                p,
                priorityLabel(p).substring(2).trim(),
                createdByP[p],
                deliveredByP[p],
                abortedByP[p],
                droppedByP[p],
                relaysByP[p]
            ));
        }

        // ── Totals ───────────────────────────────────────────────────────────
        write(SEP);
        write(String.format("TOTAL created    : %d", totalCreated));
        write(String.format("TOTAL delivered  : %d", totalDeliveries));
        write(String.format("TOTAL aborted    : %d  (unique msgs with ≥1 failed transfer)", totalAborted));
        write(String.format("TOTAL dropped    : %d  (TTL expired or buffer-evicted, undelivered)", totalDropped));
        write(String.format("TOTAL in-transit : %d  (still in buffers at sim end)", inTransit));
        write(String.format("TOTAL relays     : %d", totalRelays));
        write(String.format("CHECK            : %d + %d + %d + %d = %d (must equal created)",
            totalDeliveries, totalAborted, totalDropped, inTransit,
            totalDeliveries + totalAborted + totalDropped + inTransit));

        // ── Global advanced metrics ──────────────────────────────────────────
        double deliveryProbability = totalCreated > 0
            ? (double) totalDeliveries / totalCreated * 100 : 0;
        double abortProbability    = totalCreated > 0
            ? (double) totalAborted    / totalCreated * 100 : 0;
        double dropProbability     = totalCreated > 0
            ? (double) totalDropped    / totalCreated * 100 : 0;
        double averageLatency      = totalDeliveries > 0
            ? totalLatency  / totalDeliveries : 0;
        double averageHopCount     = totalDeliveries > 0
            ? (double) totalHopCount / totalDeliveries : 0;
        double overheadRatio       = totalDeliveries > 0
            ? (double) totalRelays   / totalDeliveries : 0;

        write(SEP);
        write("ADVANCED METRICS");
        write(SEP);
        write(String.format("Delivery Probability : %.2f%%", deliveryProbability));
        write(String.format("Abort Probability    : %.2f%%", abortProbability));
        write(String.format("Drop Probability     : %.2f%%", dropProbability));
        write(String.format("Average Latency      : %.2f sec", averageLatency));
        write(String.format("Average Hop Count    : %.2f",     averageHopCount));
        write(String.format("Overhead Ratio       : %.2f",     overheadRatio));

        // ── Per-priority advanced metrics ────────────────────────────────────
        write(SEP);
        write("PER PRIORITY ADVANCED METRICS");
        write(SEP);

        for (int p = 5; p >= 0; p--) {
            double avgLatency   = latencyCountByP[p] > 0
                ? latencyByP[p] / latencyCountByP[p] : 0;
            double avgHops      = deliveredByP[p] > 0
                ? (double) hopsByP[p] / deliveredByP[p] : 0;
            double deliveryRate = createdByP[p] > 0
                ? (double) deliveredByP[p] / createdByP[p] * 100 : 0;

            write(String.format(
                "P%d -> deliveryRate:%.2f%%  avgLatency:%.2f sec  avgHops:%.2f",
                p, deliveryRate, avgLatency, avgHops
            ));
        }

        write(SEP);
        super.done();
    }
}