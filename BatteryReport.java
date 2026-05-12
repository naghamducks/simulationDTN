package report;

import java.util.*;
import core.*;

/**
 * Reports battery statistics per node at end of simulation.
 * Add to config: Report.reportN = BatteryReport
 */
public class BatteryReport extends Report implements UpdateListener {

    private Map<DTNHost, Double> finalEnergy = new HashMap<>();

    @Override
    public void updated(List<DTNHost> hosts) {
        for (DTNHost h : hosts) {
            finalEnergy.put(h, h.getBattery().getEnergy());
        }
    }

    @Override
    public void done() {
        write("# Battery Life Report");
        write("# host   remaining_J   initial_J   pct_left   tx_J   rx_J   scan_J   dead");
        write("# -----------------------------------------------------------------------");

        int dead = 0;
        double totalRemaining = 0;
        double totalInitial   = 0;

        List<DTNHost> sorted = new ArrayList<>(finalEnergy.keySet());
        Collections.sort(sorted);

        for (DTNHost h : sorted) {
            BatteryModel b = h.getBattery();
            boolean isDead = b.isDead();
            if (isDead) dead++;
            totalRemaining += b.getEnergy();
            totalInitial   += b.getInitialEnergy();

            write(String.format("%s\t%.2f\t%.2f\t%.1f%%\t%.4f\t%.4f\t%.4f\t%s",
                h, b.getEnergy(), b.getInitialEnergy(),
                b.getRemainingFraction() * 100,
                b.getTotalTxEnergy(), b.getTotalRxEnergy(), b.getTotalScanEnergy(),
                isDead ? "DEAD" : "alive"));
        }

        write("");
        write("# Summary");
        write(String.format("Nodes dead: %d / %d", dead, finalEnergy.size()));
        write(String.format("Network avg remaining: %.1f%%",
            (totalRemaining / totalInitial) * 100));

        super.done();
    }
}