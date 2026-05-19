package core;


/**
 * Simple battery model for ONE simulator nodes.
 * Energy is consumed by: transmitting, receiving, scanning (idle radio), and moving.
 */
public class BatteryModel {

    // Default energy costs (Joules per second or per byte)
    public static final String BATTERY_NS = "Battery";
    public static final String INIT_ENERGY_S   = "initialEnergy";   // Joules
    public static final String TX_ENERGY_S     = "txEnergy";        // J/byte
    public static final String RX_ENERGY_S     = "rxEnergy";        // J/byte
    public static final String SCAN_ENERGY_S   = "scanEnergy";      // J/s (idle radio)
    public static final String MOVE_ENERGY_S   = "moveEnergy";      // J/s (moving)

    private double energy;
    private final double initialEnergy;
    private final double txEnergyPerByte;
    private final double rxEnergyPerByte;
    private final double scanEnergyPerSec;
    private final double moveEnergyPerSec;

    private double totalTxEnergy  = 0;
    private double totalRxEnergy  = 0;
    private double totalScanEnergy = 0;
    private double totalMoveEnergy = 0;

    public BatteryModel(Settings s) {
        Settings bs = new Settings(BATTERY_NS);
        this.initialEnergy    = bs.getDouble(INIT_ENERGY_S, 10800); // ~3Wh default
        this.energy           = initialEnergy;
        this.txEnergyPerByte  = bs.getDouble(TX_ENERGY_S,   0.000005);
        this.rxEnergyPerByte  = bs.getDouble(RX_ENERGY_S,   0.000003);
        this.scanEnergyPerSec = bs.getDouble(SCAN_ENERGY_S, 0.005);
        this.moveEnergyPerSec = bs.getDouble(MOVE_ENERGY_S, 0.0005);
    }

    /** Copy constructor for DTNHost prototype pattern */
    public BatteryModel(BatteryModel proto) {
        this.initialEnergy    = proto.initialEnergy;
        this.energy           = proto.initialEnergy; // fresh battery
        this.txEnergyPerByte  = proto.txEnergyPerByte;
        this.rxEnergyPerByte  = proto.rxEnergyPerByte;
        this.scanEnergyPerSec = proto.scanEnergyPerSec;
        this.moveEnergyPerSec = proto.moveEnergyPerSec;
    }

    public void consumeTx(long bytes) {
        double cost = bytes * txEnergyPerByte;
        energy = Math.max(0, energy - cost);
        totalTxEnergy += cost;
    }

    public void consumeRx(long bytes) {
        double cost = bytes * rxEnergyPerByte;
        energy = Math.max(0, energy - cost);
        totalRxEnergy += cost;
    }

    public void consumeScan(double seconds) {
        double cost = seconds * scanEnergyPerSec;
        energy = Math.max(0, energy - cost);
        totalScanEnergy += cost;
    }

    public void consumeMove(double seconds) {
        double cost = seconds * moveEnergyPerSec;
        energy = Math.max(0, energy - cost);
        totalMoveEnergy += cost;
    }

    public boolean isDead()            { return energy <= 0; }
    public double getEnergy()          { return energy; }
    public double getInitialEnergy()   { return initialEnergy; }
    public double getRemainingFraction(){ return energy / initialEnergy; }

    public double getTotalTxEnergy()   { return totalTxEnergy; }
    public double getTotalRxEnergy()   { return totalRxEnergy; }
    public double getTotalScanEnergy() { return totalScanEnergy; }
    public double getTotalMoveEnergy() { return totalMoveEnergy; }

    @Override
    public String toString() {
        return String.format("Battery[%.1f/%.1fJ = %.1f%%]",
            energy, initialEnergy, getRemainingFraction() * 100);
    }
}