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
 * This report provides:
 *
 * 1. Message-level transfer tracking
 * 2. Delivery statistics
 * 3. Abort statistics
 * 4. Relay overhead analysis
 * 5. Average latency analysis
 * 6. Hop count analysis
 * 7. Priority-aware QoS metrics
 * 8. Thesis-ready summary statistics
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
            "SimTime",
            "From",
            "To",
            "MsgID",
            "Priority",
            "Size(B)",
            "Type"
        );

    // =========================================================================
    // GLOBAL METRICS
    // =========================================================================

    private int totalRelays = 0;
    private int totalDeliveries = 0;
    private int totalAborted = 0;

    private double totalLatency = 0;
    private int totalHopCount = 0;

    // =========================================================================
    // MESSAGE-LEVEL TRACKING
    // =========================================================================

    private static class MsgStats {

        int priority = 0;

        boolean delivered = false;
        boolean aborted = false;

        int relays = 0;
        int hopCount = 0;

        double creationTime = 0;
        double deliveryTime = 0;
    }

    private Map<String, MsgStats> stats = new HashMap<>();

    // =========================================================================
    // PER-PRIORITY COUNTERS
    // =========================================================================

    private int[] createdByP = new int[6];
    private int[] deliveredByP = new int[6];
    private int[] abortedByP = new int[6];
    private int[] relaysByP = new int[6];

    // =========================================================================
    // PER-PRIORITY LATENCY/HOPS
    // =========================================================================

    private double[] latencyByP = new double[6];
    private int[] latencyCountByP = new int[6];

    private int[] hopsByP = new int[6];

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

    private int priorityOf(Message m) {

        try {
            return m.getPriority();
        }
        catch (Exception e) {
            return 0;
        }
    }

    private String priorityLabel(int p) {

        switch (p) {

            case 5:
                return p + " DISTRESS";

            case 4:
                return p + " HIGH";

            case 3:
                return p + " MED-HIGH";

            case 2:
                return p + " MEDIUM";

            case 1:
                return p + " LOW";

            default:
                return p + " NORMAL";
        }
    }

    // =========================================================================
    // GET OR CREATE MESSAGE STATS
    // =========================================================================

    private MsgStats getStats(Message m) {

        MsgStats s = stats.get(m.getId());

        if (s == null) {

            s = new MsgStats();

            s.priority = priorityOf(m);

            s.creationTime = getSimTime();

            stats.put(m.getId(), s);

            createdByP[s.priority]++;
        }

        return s;
    }

    // =========================================================================
    // LOGGING
    // =========================================================================

    private void log(
        Message m,
        DTNHost from,
        DTNHost to,
        String type
    ) {

        write(String.format(
            "%-10.1f | %-10s | %-10s | %-12s | %-14s | %-12d | %s",

            getSimTime(),

            from.toString(),
            to.toString(),

            m.getId(),

            priorityLabel(priorityOf(m)),

            m.getSize(),

            type
        ));
    }

    // =========================================================================
    // MESSAGE TRANSFERRED
    // =========================================================================

    @Override
    public void messageTransferred(
        Message m,
        DTNHost from,
        DTNHost to,
        boolean firstDelivery
    ) {

        MsgStats s = getStats(m);

        // =====================================================================
        // FINAL DELIVERY
        // =====================================================================

        if (firstDelivery) {

            if (!s.delivered) {

                s.delivered = true;

                s.deliveryTime = getSimTime();

                double latency =
                    s.deliveryTime - s.creationTime;

                totalLatency += latency;

                latencyByP[s.priority] += latency;

                latencyCountByP[s.priority]++;

                totalHopCount += s.hopCount;

                hopsByP[s.priority] += s.hopCount;

                deliveredByP[s.priority]++;

                totalDeliveries++;
            }

            log(
                m,
                from,
                to,
                "FINAL DELIVERY"
            );
        }

        // =====================================================================
        // RELAY
        // =====================================================================

        else {

            s.relays++;

            s.hopCount++;

            relaysByP[s.priority]++;

            totalRelays++;

            log(
                m,
                from,
                to,
                "RELAY"
            );
        }
    }

    // =========================================================================
    // ABORTED
    // =========================================================================

    @Override
    public void messageTransferAborted(
        Message m,
        DTNHost from,
        DTNHost to
    ) {

        MsgStats s = getStats(m);

        if (!s.aborted) {

            s.aborted = true;

            abortedByP[s.priority]++;

            totalAborted++;
        }

        log(
            m,
            from,
            to,
            "ABORTED"
        );
    }

    // =========================================================================
    // TRANSFER STARTED
    // =========================================================================

    @Override
    public void messageTransferStarted(
        Message m,
        DTNHost from,
        DTNHost to
    ) {
    }

    // =========================================================================
    // NEW MESSAGE
    // =========================================================================

    @Override
    public void newMessage(Message m) {

        getStats(m);
    }

    // =========================================================================
    // MESSAGE DELETED
    // =========================================================================

    @Override
    public void messageDeleted(
        Message m,
        DTNHost where,
        boolean dropped
    ) {
    }

    // =========================================================================
    // FINAL SUMMARY
    // =========================================================================

    @Override
    public void done() {

        // =====================================================================
        // BASIC SUMMARY
        // =====================================================================

        write(SEP);
        write("SUMMARY (MESSAGE-LEVEL BY PRIORITY)");
        write(SEP);

        for (int p = 5; p >= 0; p--) {

            write(String.format(
                "P%d -> created:%d delivered:%d aborted:%d relays:%d",

                p,

                createdByP[p],

                deliveredByP[p],

                abortedByP[p],

                relaysByP[p]
            ));
        }

        // =====================================================================
        // TOTALS
        // =====================================================================

        write(SEP);

        write(String.format(
            "TOTAL created   : %d",
            stats.size()
        ));

        write(String.format(
            "TOTAL delivered : %d",
            totalDeliveries
        ));

        write(String.format(
            "TOTAL relays    : %d",
            totalRelays
        ));

        write(String.format(
            "TOTAL aborted   : %d",
            totalAborted
        ));

        // =====================================================================
        // ADVANCED METRICS
        // =====================================================================

        double deliveryProbability =
            stats.size() > 0
                ? ((double) totalDeliveries / stats.size()) * 100
                : 0;

        double abortProbability =
            stats.size() > 0
                ? ((double) totalAborted / stats.size()) * 100
                : 0;

        double averageLatency =
            totalDeliveries > 0
                ? totalLatency / totalDeliveries
                : 0;

        double averageHopCount =
            totalDeliveries > 0
                ? (double) totalHopCount / totalDeliveries
                : 0;

        double overheadRatio =
            totalDeliveries > 0
                ? (double) totalRelays / totalDeliveries
                : 0;

        write(SEP);
        write("ADVANCED METRICS");
        write(SEP);

        write(String.format(
            "Delivery Probability : %.2f%%",
            deliveryProbability
        ));

        write(String.format(
            "Abort Probability    : %.2f%%",
            abortProbability
        ));

        write(String.format(
            "Average Latency      : %.2f sec",
            averageLatency
        ));

        write(String.format(
            "Average Hop Count    : %.2f",
            averageHopCount
        ));

        write(String.format(
            "Overhead Ratio       : %.2f",
            overheadRatio
        ));

        // =====================================================================
        // PRIORITY ADVANCED METRICS
        // =====================================================================

        write(SEP);
        write("PER PRIORITY ADVANCED METRICS");
        write(SEP);

        for (int p = 5; p >= 0; p--) {

            double avgLatency =
                latencyCountByP[p] > 0
                    ? latencyByP[p] / latencyCountByP[p]
                    : 0;

            double avgHops =
                deliveredByP[p] > 0
                    ? (double) hopsByP[p] / deliveredByP[p]
                    : 0;

            double deliveryRate =
                createdByP[p] > 0
                    ? ((double) deliveredByP[p] / createdByP[p]) * 100
                    : 0;

            write(String.format(
                "P%d -> deliveryRate:%.2f%% avgLatency:%.2f avgHops:%.2f",

                p,

                deliveryRate,

                avgLatency,

                avgHops
            ));
        }

        // =====================================================================
        // END
        // =====================================================================

        write(SEP);

        super.done();
    }
}