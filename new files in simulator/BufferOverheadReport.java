/*
 * BufferOverheadReport.java
 * Place in: the-one/src/report/
 *
 * Samples buffer occupancy across all nodes at regular intervals and
 * reports GLOBAL AGGREGATE statistics only at the end of the simulation.
 *
 * Metrics reported:
 *   - Nodes sampled
 *   - Total samples collected
 *   - Average overhead %
 *   - Mean overhead %
 *   - SD overhead %
 *   - Min node overhead %
 *   - Max node overhead %
 *   - Mean of per-node SDs
 *   - Global peak overhead %
 *
 * Settings:
 *   Report.reportN                = BufferOverheadReport
 *   BufferOverheadReport.interval = 60
 */

package report;

import core.DTNHost;
import core.Message;
import core.MessageListener;
import core.Settings;
import core.UpdateListener;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class BufferOverheadReport extends Report
        implements UpdateListener, MessageListener {

    public static final String INTERVAL_S = "interval";
    public static final double DEFAULT_INTERVAL = 60.0;

    private double interval;
    private double lastSampleTime = Double.MIN_VALUE;

    /** Per-node occupancy samples */
    private final Map<Integer, List<Long>> samples = new HashMap<>();

    /** Per-node buffer sizes */
    private final Map<Integer, Long> bufferSizes = new HashMap<>();

    // =========================================================
    // CONSTRUCTOR
    // =========================================================

    public BufferOverheadReport() {

        super();

        Settings s = getSettings();

        interval = s.contains(INTERVAL_S)
                ? s.getDouble(INTERVAL_S)
                : DEFAULT_INTERVAL;
    }

    // =========================================================
    // PERIODIC SAMPLING ONLY
    // =========================================================

    @Override
    public void updated(List<DTNHost> hosts) {

        if (getSimTime() - lastSampleTime < interval) {
            return;
        }

        lastSampleTime = getSimTime();

        for (DTNHost h : hosts) {
            sampleHost(h);
        }
    }

    // =========================================================
    // DISABLED EVENT-BASED SAMPLING
    // (kept for interface compatibility)
    // =========================================================

    @Override
    public void messageTransferred(Message m,
                                   DTNHost from,
                                   DTNHost to,
                                   boolean firstDelivery) {
        // intentionally disabled
    }

    @Override
    public void messageDeleted(Message m,
                               DTNHost where,
                               boolean dropped) {
        // intentionally disabled
    }

    @Override
    public void messageTransferStarted(Message m,
                                       DTNHost from,
                                       DTNHost to) {
    }

    @Override
    public void messageTransferAborted(Message m,
                                       DTNHost from,
                                       DTNHost to) {
    }

    @Override
    public void newMessage(Message m) {
    }

    // =========================================================
    // SAMPLING
    // =========================================================

    private void sampleHost(DTNHost h) {

        int addr = h.getAddress();

        if (!samples.containsKey(addr)) {

            samples.put(addr, new ArrayList<>());

            bufferSizes.put(
                    addr,
                    h.getRouter().getBufferSize()
            );
        }

        long buf = h.getRouter().getBufferSize();

        long free = h.getRouter().getFreeBufferSize();

        // Clamp occupancy safely between 0 and buffer size
        long occ = Math.max(
                0,
                Math.min(buf, buf - free)
        );

        samples.get(addr).add(occ);
    }

    // =========================================================
    // HELPERS
    // =========================================================

    private double mean(List<Long> vals) {

        if (vals.isEmpty()) {
            return 0.0;
        }

        double sum = 0;

        for (long v : vals) {
            sum += v;
        }

        return sum / vals.size();
    }

    private double sd(List<Long> vals, double mean) {

        if (vals.size() < 2) {
            return 0.0;
        }

        double sq = 0;

        for (long v : vals) {

            double d = v - mean;

            sq += d * d;
        }

        return Math.sqrt(sq / (vals.size() - 1));
    }

    // =========================================================
    // FINAL REPORT
    // =========================================================

    @Override
    public void done() {

        String sep = "=".repeat(60);

        List<Double> meanPcts = new ArrayList<>();
        List<Double> sdPcts = new ArrayList<>();

        double globalPeakPct = 0.0;

        int totalSamples = 0;

        for (int addr : samples.keySet()) {

            List<Long> s = samples.get(addr);

            long bufSize = bufferSizes.get(addr);

            if (s.isEmpty()
                    || bufSize <= 0
                    || bufSize == Integer.MAX_VALUE) {
                continue;
            }

            totalSamples += s.size();

            double meanOcc = mean(s);

            double sdOcc = sd(s, meanOcc);

            long peak = s.stream()
                    .mapToLong(Long::longValue)
                    .max()
                    .orElse(0);

            double bufD = (double) bufSize;

            double meanPct = (meanOcc / bufD) * 100.0;

            double sdPct = (sdOcc / bufD) * 100.0;

            double peakPct = (peak / bufD) * 100.0;

            meanPcts.add(meanPct);

            sdPcts.add(sdPct);

            globalPeakPct = Math.max(
                    globalPeakPct,
                    peakPct
            );
        }

        write(sep);
        write("BUFFER OVERHEAD REPORT — GLOBAL AGGREGATE");
        write(sep);

        write(String.format(
                "  Sampling interval    : %.0f s",
                interval
        ));

        write(String.format(
                "  Nodes sampled        : %d",
                meanPcts.size()
        ));

        write(String.format(
                "  Total samples        : %d",
                totalSamples
        ));

        write(String.format(
                "  Buffer size\t       : 30M"
        ));

        write(String.format(
                "  Router\t       : Prophet"
        ));

        write(sep);

        if (!meanPcts.isEmpty()) {

            double avg = meanPcts.stream()
                    .mapToDouble(Double::doubleValue)
                    .average()
                    .orElse(0);

            double sqSum = 0;

            for (double v : meanPcts) {

                double d = v - avg;

                sqSum += d * d;
            }

            double globalSd =
                    meanPcts.size() > 1
                            ? Math.sqrt(
                                    sqSum / (meanPcts.size() - 1)
                            )
                            : 0.0;

            double minPct = meanPcts.stream()
                    .mapToDouble(Double::doubleValue)
                    .min()
                    .orElse(0);

            double maxPct = meanPcts.stream()
                    .mapToDouble(Double::doubleValue)
                    .max()
                    .orElse(0);

            double meanOfSds = sdPcts.stream()
                    .mapToDouble(Double::doubleValue)
                    .average()
                    .orElse(0);

            write(String.format(
                    "  Average overhead %%   : %.4f %%",
                    avg
            ));

            write(String.format(
                    "  Mean overhead %%      : %.4f %%",
                    avg
            ));

            write(String.format(
                    "  SD overhead %%        : %.4f %%",
                    globalSd
            ));

            write(String.format(
                    "  Min node overhead %%  : %.4f %%",
                    minPct
            ));

            write(String.format(
                    "  Max node overhead %%  : %.4f %%",
                    maxPct
            ));

            write(String.format(
                    "  Mean of per-node SDs : %.4f %%",
                    meanOfSds
            ));

            write(String.format(
                    "  Global peak overhead : %.4f %%",
                    globalPeakPct
            ));
        }
        else {

            write("  No finite-buffer nodes found.");
        }

        write(sep);

        super.done();
    }
}