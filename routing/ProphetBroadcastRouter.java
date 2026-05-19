package routing;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import core.Connection;
import core.DTNHost;
import core.Message;
import core.Settings;
import core.SimClock;
import routing.util.RoutingInfo;
import util.Tuple;

public class ProphetBroadcastRouter extends ActiveRouter {

    public static final double P_ENC_MAX = 0.5;
    public static final double I_TYP = 1800.0;
    public static final double GAMMA = 0.999885791;
    public static final double DEFAULT_BETA = 0.9;
    public static final double DEFAULT_RELAY_THRESHOLD = 0.1;

    public static final String ROUTER_NS = "ProphetBroadcastRouter";
    public static final String SECONDS_IN_UNIT_S = "secondsInTimeUnit";
    public static final String BETA_S = "beta";
    public static final String THRESHOLD_S = "relayThreshold";

    private int secondsInTimeUnit;
    private double beta;
    private double relayThreshold;

    private Map<DTNHost, Double> preds;
    private Map<DTNHost, Double> lastEncounterTime;
    private double lastAgeUpdate;

    public ProphetBroadcastRouter(Settings s) {
        super(s);
        Settings rs = new Settings(ROUTER_NS);

        this.secondsInTimeUnit = rs.getInt(SECONDS_IN_UNIT_S);
        this.beta = rs.contains(BETA_S) ? rs.getDouble(BETA_S) : DEFAULT_BETA;
        this.relayThreshold = rs.contains(THRESHOLD_S)
                ? rs.getDouble(THRESHOLD_S)
                : DEFAULT_RELAY_THRESHOLD;

        initState();
    }

    protected ProphetBroadcastRouter(ProphetBroadcastRouter r) {
        super(r); // FIX: copy parent state properly
        this.secondsInTimeUnit = r.secondsInTimeUnit;
        this.beta = r.beta;
        this.relayThreshold = r.relayThreshold;
        initState();
    }

    private void initState() {
        this.preds = new HashMap<>();
        this.lastEncounterTime = new HashMap<>();
        this.lastAgeUpdate = 0;
    }

    @Override
    public void changedConnection(Connection con) {
        if (con.isUp()) {
            DTNHost other = con.getOtherNode(getHost());
            updateDeliveryPredFor(other);
            updateTransitivePreds(other);
        }
    }

    private void updateDeliveryPredFor(DTNHost host) {
        double now = SimClock.getTime();
        double lastEncTime = getEncTimeFor(host);
        double pEnc;

        if (lastEncTime == 0) {
            pEnc = P_ENC_MAX;
        } else {
            double interval = now - lastEncTime;
            pEnc = (interval < I_TYP)
                    ? P_ENC_MAX * (interval / I_TYP)
                    : P_ENC_MAX;
        }

        double oldP = getPredFor(host);
        preds.put(host, oldP + (1.0 - oldP) * pEnc);
        lastEncounterTime.put(host, now);
    }

    private void updateTransitivePreds(DTNHost host) {
        MessageRouter otherRouter = host.getRouter();
        Map<DTNHost, Double> otherPreds;

        if (otherRouter instanceof ProphetBroadcastRouter) {
            otherPreds = ((ProphetBroadcastRouter) otherRouter).getDeliveryPreds();
        } else if (otherRouter instanceof ProphetV2Router) {
            otherPreds = ((ProphetV2Router) otherRouter).getDeliveryPreds();
        } else {
            return;
        }

        double pAB = getPredFor(host);

        for (Map.Entry<DTNHost, Double> e : otherPreds.entrySet()) {
            if (e.getKey() == getHost()) continue;

            double pOld = getPredFor(e.getKey());
            double pNew = pAB * e.getValue() * beta;

            if (pNew > pOld) {
                preds.put(e.getKey(), pNew);
            }
        }
    }

    private void ageDeliveryPreds() {
        double timeDiff = (SimClock.getTime() - lastAgeUpdate) / secondsInTimeUnit;
        if (timeDiff == 0) return;

        double mult = Math.pow(GAMMA, timeDiff);

        for (Map.Entry<DTNHost, Double> e : preds.entrySet()) {
            e.setValue(e.getValue() * mult);
        }

        lastAgeUpdate = SimClock.getTime();
    }

    public double getPredFor(DTNHost host) {
        ageDeliveryPreds();
        return preds.getOrDefault(host, 0.0);
    }

    public double getEncTimeFor(DTNHost host) {
        return lastEncounterTime.getOrDefault(host, 0.0);
    }

    protected Map<DTNHost, Double> getDeliveryPreds() {
        ageDeliveryPreds();
        return preds;
    }

    private double getOtherPredFor(MessageRouter otherRouter, DTNHost dest) {
        if (otherRouter instanceof ProphetBroadcastRouter) {
            return ((ProphetBroadcastRouter) otherRouter).getPredFor(dest);
        }
        if (otherRouter instanceof ProphetV2Router) {
            return ((ProphetV2Router) otherRouter).getPredFor(dest);
        }
        if (otherRouter instanceof ProphetRouter) {
            return ((ProphetRouter) otherRouter).getPredFor(dest);
        }
        return 0.0;
    }

    @Override
    public void update() {
        super.update();

        if (!canStartTransfer() || isTransferring()) return;

        if (exchangeDeliverableMessages() != null) return;

        tryBroadcastMessages();
    }

    private void tryBroadcastMessages() {
        Collection<Message> msgs = getMessageCollection();
        if (msgs.isEmpty()) return;

        List<Tuple<Message, Connection>> transfers = new ArrayList<>();

        for (Connection con : getConnections()) {

            DTNHost other = con.getOtherNode(getHost());
            MessageRouter otherR = other.getRouter();

            if (otherR instanceof ActiveRouter &&
                ((ActiveRouter) otherR).isTransferring()) {
                continue;
            }

            for (Message m : msgs) {
                if (otherR.hasMessage(m.getId())) continue;

                double p = getOtherPredFor(otherR, m.getTo());

                if (p >= relayThreshold &&
                    p > getPredFor(m.getTo())) {

                    transfers.add(new Tuple<>(m, con));
                }
            }
        }

        if (transfers.isEmpty()) return;

        Collections.sort(transfers, new TupleComparator());
        tryMessagesForConnected(transfers);
    }

    private class TupleComparator implements Comparator<Tuple<Message, Connection>> {

        @Override
        public int compare(Tuple<Message, Connection> t1,
                           Tuple<Message, Connection> t2) {

            MessageRouter r1 = t1.getValue().getOtherNode(getHost()).getRouter();
            MessageRouter r2 = t2.getValue().getOtherNode(getHost()).getRouter();

            double p1 = getOtherPredFor(r1, t1.getKey().getTo());
            double p2 = getOtherPredFor(r2, t2.getKey().getTo());

            if (p2 > p1) return 1;
            if (p2 < p1) return -1;
            return compareByQueueMode(t1.getKey(), t2.getKey());
        }
    }

    @Override
    public RoutingInfo getRoutingInfo() {
        ageDeliveryPreds();

        RoutingInfo top = super.getRoutingInfo();
        RoutingInfo ri = new RoutingInfo(
                preds.size() + " delivery prediction(s)"
        );

        for (Map.Entry<DTNHost, Double> e : preds.entrySet()) {
            ri.addMoreInfo(new RoutingInfo(
                    e.getKey() + " : " + String.format("%.6f", e.getValue())
            ));
        }

        top.addMoreInfo(ri);
        return top;
    }

    @Override
    public MessageRouter replicate() {
        return new ProphetBroadcastRouter(this);
    }
}