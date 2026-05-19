package input;

import java.util.Random;

import core.Settings;
import core.SettingsError;

public class MessageEventGenerator implements EventQueue {

    public static final String MESSAGE_SIZE_S = "size";
    public static final String MESSAGE_INTERVAL_S = "interval";
    public static final String HOST_RANGE_S = "hosts";
    public static final String TO_HOST_RANGE_S = "tohosts";
    public static final String MESSAGE_ID_PREFIX_S = "prefix";
    public static final String MESSAGE_TIME_S = "time";

    protected double nextEventsTime = 0;
    protected int[] hostRange = {0, 0};
    protected int[] toHostRange = null;
    private int id = 0;
    protected String idPrefix;
    private int[] sizeRange;
    private int[] msgInterval;
    protected double[] msgTime;

    protected Random rng;

    public MessageEventGenerator(Settings s) {

        this.sizeRange = s.getCsvInts(MESSAGE_SIZE_S);
        this.msgInterval = s.getCsvInts(MESSAGE_INTERVAL_S);
        this.hostRange = s.getCsvInts(HOST_RANGE_S, 2);
        this.idPrefix = s.getSetting(MESSAGE_ID_PREFIX_S);

        if (s.contains(MESSAGE_TIME_S)) {
            this.msgTime = s.getCsvDoubles(MESSAGE_TIME_S, 2);
        } else {
            this.msgTime = null;
        }

        if (s.contains(TO_HOST_RANGE_S)) {
            this.toHostRange = s.getCsvInts(TO_HOST_RANGE_S, 2);
        } else {
            this.toHostRange = null;
        }

        this.rng = new Random(idPrefix.hashCode());

        if (this.sizeRange.length == 1) {
            this.sizeRange = new int[] {this.sizeRange[0], this.sizeRange[0]};
        } else {
            s.assertValidRange(this.sizeRange, MESSAGE_SIZE_S);
        }

        if (this.msgInterval.length == 1) {
            this.msgInterval = new int[] {this.msgInterval[0], this.msgInterval[0]};
        } else {
            s.assertValidRange(this.msgInterval, MESSAGE_INTERVAL_S);
        }

        s.assertValidRange(this.hostRange, HOST_RANGE_S);

        this.nextEventsTime = (this.msgTime != null ? this.msgTime[0] : 0)
                + msgInterval[0]
                + (msgInterval[0] == msgInterval[1] ? 0 :
                rng.nextInt(msgInterval[1] - msgInterval[0]));
    }

    // ─────────────────────────────────────────────
    // PRIORITY LOGIC (NEW)
    // ─────────────────────────────────────────────

    private int derivePriority(int from) {

        // matches your scenario groups:
        if (from >= 80 && from <= 119) return 5; // distress (RED)
        if (from >= 120 && from <= 121) return 3; // bus A
        if (from >= 122 && from <= 123) return 4; // bus B
        if (from >= 124 && from <= 125) return 0; // bus C
        if (from >= 40 && from <= 79) return 2;   // cars
        if (from >= 0 && from <= 39) return 1;    // pedestrians

        return 0;
    }

    // ─────────────────────────────────────────────

    protected int drawHostAddress(int hostRange[]) {
        if (hostRange[1] == hostRange[0]) return hostRange[0];
        return hostRange[0] + rng.nextInt(hostRange[1] - hostRange[0]);
    }

    protected int drawMessageSize() {
        int sizeDiff = sizeRange[0] == sizeRange[1] ? 0 :
                rng.nextInt(sizeRange[1] - sizeRange[0]);
        return sizeRange[0] + sizeDiff;
    }

    protected int drawNextEventTimeDiff() {
        int timeDiff = msgInterval[0] == msgInterval[1] ? 0 :
                rng.nextInt(msgInterval[1] - msgInterval[0]);
        return msgInterval[0] + timeDiff;
    }

    protected int drawToAddress(int hostRange[], int from) {
        int to;
        do {
            to = this.toHostRange != null
                    ? drawHostAddress(this.toHostRange)
                    : drawHostAddress(this.hostRange);
        } while (from == to);

        return to;
    }

    @Override
    public ExternalEvent nextEvent() {

        int responseSize = 0;

        int from = drawHostAddress(this.hostRange);
        int to = drawToAddress(hostRange, from);

        int msgSize = drawMessageSize();
        int interval = drawNextEventTimeDiff();

        // 🔥 NEW: priority per message
        int priority = derivePriority(from);

       
        MessageCreateEvent mce = new MessageCreateEvent(
                from,
                to,
                this.getID(),
                msgSize,
                responseSize,
                this.nextEventsTime,
                priority
        );
        this.nextEventsTime += interval;

        if (this.msgTime != null && this.nextEventsTime > this.msgTime[1]) {
            this.nextEventsTime = Double.MAX_VALUE;
        }

        return mce;
    }

    @Override
    public double nextEventsTime() {
        return this.nextEventsTime;
    }

    protected String getID() {
        this.id++;
        return idPrefix + this.id;
    }
}