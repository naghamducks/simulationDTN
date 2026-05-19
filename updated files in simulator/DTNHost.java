/*
 * Copyright 2010 Aalto University, ComNet
 * Released under GPLv3. See LICENSE.txt for details.
 *
 * Modified to include BatteryModel integration for battery life evaluation.
 * Modified to store groupId and priority for GUI color-coding.
 */
package core;

import java.util.ArrayList;
import java.util.Collection;
import java.util.List;

import movement.MovementModel;
import movement.Path;
import routing.MessageRouter;
import routing.util.RoutingInfo;

import static core.Constants.DEBUG;

/**
 * A DTN capable host.
 */
public class DTNHost implements Comparable<DTNHost> {
	private static int nextAddress = 0;
	private int address;

	private Coord location; 	// where is the host
	private Coord destination;	// where is it going

	private MessageRouter router;
	private MovementModel movement;
	private Path path;
	private double speed;
	private double nextTimeToMove;
	private String name;
	private List<MessageListener> msgListeners;
	private List<MovementListener> movListeners;
	private List<NetworkInterface> net;
	private ModuleCommunicationBus comBus;

	// -----------------------------------------------------------------------
	// Group identity – stored so the GUI can color-code nodes by group/priority
	// -----------------------------------------------------------------------
	/** The group ID prefix this host belongs to (e.g. "p", "c", "t", "d"). */
	private String groupId;

	/**
	 * Priority level for this host's group (0 = lowest/green … 5 = highest/red).
	 * Set via {@link #setPriority(int)} after construction, or read from config
	 * with Group&lt;n&gt;.priority in your settings file.
	 */
	private int priority;
	// -----------------------------------------------------------------------

	// -----------------------------------------------------------------------
	// Battery integration
	// -----------------------------------------------------------------------
	private BatteryModel battery;
	private double lastUpdateTime; // simulation time of the last update() call
	// -----------------------------------------------------------------------

	static {
		DTNSim.registerForReset(DTNHost.class.getCanonicalName());
		reset();
	}

	/**
	 * Creates a new DTNHost.
	 * @param msgLs Message listeners
	 * @param movLs Movement listeners
	 * @param groupId GroupID of this host
	 * @param interf List of NetworkInterfaces for the class
	 * @param comBus Module communication bus object
	 * @param mmProto Prototype of the movement model of this host
	 * @param mRouterProto Prototype of the message router of this host
	 */
	public DTNHost(List<MessageListener> msgLs,
			List<MovementListener> movLs,
			String groupId, List<NetworkInterface> interf,
			ModuleCommunicationBus comBus,
			MovementModel mmProto, MessageRouter mRouterProto) {
		this.comBus = comBus;
		this.location = new Coord(0,0);
		this.address = getNextAddress();
		this.name = groupId + address;
		this.net = new ArrayList<NetworkInterface>();

		this.groupId = groupId;
		this.priority = 0;

		for (NetworkInterface i : interf) {
			NetworkInterface ni = i.replicate();
			ni.setHost(this);
			net.add(ni);
		}

		this.msgListeners = msgLs;
		this.movListeners = movLs;

		// create instances by replicating the prototypes
		this.movement = mmProto.replicate();
		this.movement.setComBus(comBus);
		this.movement.setHost(this);
		setRouter(mRouterProto.replicate());

		this.location = movement.getInitialLocation();
		this.nextTimeToMove = movement.nextPathAvailable();
		this.path = null;

		if (movLs != null) {
			for (MovementListener l : movLs) {
				l.initialLocation(this, this.location);
			}
		}

		// Battery: read settings from the "Battery" namespace in the config file.
		this.battery = new BatteryModel(new Settings());
		this.lastUpdateTime = 0;
	}

	/**
	 * Returns a new network interface address and increments the address for
	 * subsequent calls.
	 * @return The next address.
	 */
	private synchronized static int getNextAddress() {
		return nextAddress++;
	}

	/**
	 * Reset the host and its interfaces
	 */
	public static void reset() {
		nextAddress = 0;
	}

	// =========================================================================
	// Group ID and Priority accessors
	// =========================================================================

	public String getGroupId() {
		return this.groupId;
	}

	public int getPriority() {
		return this.priority;
	}

	public void setPriority(int priority) {
		this.priority = Math.max(0, Math.min(5, priority));
		gui.playfield.NodeGraphic.setGroupPriority(this.groupId, this.priority);
	}

	// =========================================================================
	// Remainder of original DTNHost
	// =========================================================================

	public boolean isMovementActive() {
		return this.movement.isActive();
	}

	public boolean isRadioActive() {
		for (final NetworkInterface i : this.net) {
			if (i.isActive()) return true;
		}
		return false;
	}

	private void setRouter(MessageRouter router) {
		router.init(this, msgListeners);
		this.router = router;
	}

	public MessageRouter getRouter() {
		return this.router;
	}

	public int getAddress() {
		return this.address;
	}

	public ModuleCommunicationBus getComBus() {
		return this.comBus;
	}

	public void connectionUp(Connection con) {
		this.router.changedConnection(con);
	}

	public void connectionDown(Connection con) {
		this.router.changedConnection(con);
	}

	public List<Connection> getConnections() {
		List<Connection> lc = new ArrayList<Connection>();
		for (NetworkInterface i : net) {
			lc.addAll(i.getConnections());
		}
		return lc;
	}

	public Coord getLocation() {
		return this.location;
	}

	public Path getPath() {
		return this.path;
	}

	public void setLocation(Coord location) {
		this.location = location.clone();
	}

	public void setName(String name) {
		this.name = name;
	}

	public Collection<Message> getMessageCollection() {
		return this.router.getMessageCollection();
	}

	public int getNrofMessages() {
		return this.router.getNrofMessages();
	}

	public double getBufferOccupancy() {
		long bSize = router.getBufferSize();
		long freeBuffer = router.getFreeBufferSize();
		return 100*((bSize-freeBuffer)/(bSize * 1.0));
	}

	public RoutingInfo getRoutingInfo() {
		return this.router.getRoutingInfo();
	}

	public List<NetworkInterface> getInterfaces() {
		return net;
	}

	public NetworkInterface getInterface(int interfaceNo) {
		NetworkInterface ni = null;
		try {
			ni = net.get(interfaceNo-1);
		} catch (IndexOutOfBoundsException ex) {
			throw new SimError("No such interface: "+interfaceNo +
					" at " + this);
		}
		return ni;
	}

	protected NetworkInterface getInterface(String interfacetype) {
		for (NetworkInterface ni : net) {
			if (ni.getInterfaceType().equals(interfacetype)) {
				return ni;
			}
		}
		return null;
	}

	public void forceConnection(DTNHost anotherHost, String interfaceId,
			boolean up) {
		NetworkInterface ni;
		NetworkInterface no;

		if (interfaceId != null) {
			ni = getInterface(interfaceId);
			no = anotherHost.getInterface(interfaceId);
			assert (ni != null) : "Tried to use a nonexisting interfacetype "+interfaceId;
			assert (no != null) : "Tried to use a nonexisting interfacetype "+interfaceId;
		} else {
			ni = getInterface(1);
			no = anotherHost.getInterface(1);
			assert (ni.getInterfaceType().equals(no.getInterfaceType())) :
				"Interface types do not match.  Please specify interface type explicitly";
		}

		if (up) {
			ni.createConnection(no);
		} else {
			ni.destroyConnection(no);
		}
	}

	public void connect(DTNHost h) {
		if (DEBUG) Debug.p("WARNING: using deprecated DTNHost.connect" +
			"(DTNHost) Use DTNHost.forceConnection(DTNHost,null,true) instead");
		forceConnection(h,null,true);
	}

	// =========================================================================
	// Battery accessors
	// =========================================================================

	/**
	 * Returns the {@link BatteryModel} of this host.
	 * @return the battery model – never null
	 */
	public BatteryModel getBattery() {
		return this.battery;
	}

	/**
	 * Convenience method: returns true when the node's battery is fully depleted.
	 */
	public boolean isBatteryDead() {
		return this.battery.isDead();
	}

	// =========================================================================
	// Core simulation loop
	// =========================================================================

	/**
	 * Updates node's network layer and router.
	 *
	 * Scan energy is charged here — but ONLY when the radio is actually active
	 * and the battery is not dead. This ensures per-node scan drain reflects
	 * real radio-on time, producing meaningful variation across nodes and runs.
	 *
	 * TX energy is charged in Connection.finalizeTransfer() on the sender.
	 * RX energy is charged in receiveMessage() on the receiver.
	 *
	 * @param simulateConnections Should network layer be updated too
	 */
	public void update(boolean simulateConnections) {
		double now = SimClock.getTime();
		double elapsed = now - lastUpdateTime;
		lastUpdateTime = now;

		// -------------------------------------------------------------------
		// Charge scan energy only when the radio is on and node is alive.
		// Dead nodes and inactive radios do not scan.
		// -------------------------------------------------------------------
		if (elapsed > 0 && isRadioActive() && !battery.isDead()) {
			battery.consumeScan(elapsed);
		}

		if (!isRadioActive() || battery.isDead()) {
			tearDownAllConnections();
			return;
		}

		if (simulateConnections) {
			for (NetworkInterface i : net) {
				i.update();
			}
		}
		this.router.update();
	}

	/**
	 * Tears down all connections for this host.
	 */
	private void tearDownAllConnections() {
		for (NetworkInterface i : net) {
			List<Connection> conns = i.getConnections();
			if (conns.size() == 0) continue;

			List<NetworkInterface> removeList =
				new ArrayList<NetworkInterface>(conns.size());
			for (Connection con : conns) {
				removeList.add(con.getOtherInterface(i));
			}
			for (NetworkInterface inf : removeList) {
				i.destroyConnection(inf);
			}
		}
	}

	/**
	 * Moves the node towards the next waypoint or waits if it is
	 * not time to move yet.
	 * @param timeIncrement How long time the node moves
	 */
	public void move(double timeIncrement) {
		double possibleMovement;
		double distance;
		double dx, dy;

		if (battery.isDead()) {
			return;
		}

		if (!isMovementActive() || SimClock.getTime() < this.nextTimeToMove) {
			return;
		}
		if (this.destination == null) {
			if (!setNextWaypoint()) {
				return;
			}
		}

		possibleMovement = timeIncrement * speed;
		distance = this.location.distance(this.destination);

		double movingTime = 0;

		while (possibleMovement >= distance) {
			this.location.setLocation(this.destination);
			if (speed > 0) movingTime += distance / speed;
			possibleMovement -= distance;
			if (!setNextWaypoint()) {
				this.destination = null;
				return;
			}
			distance = this.location.distance(this.destination);
		}

		dx = (possibleMovement/distance) * (this.destination.getX() -
				this.location.getX());
		dy = (possibleMovement/distance) * (this.destination.getY() -
				this.location.getY());
		this.location.translate(dx, dy);
		if (speed > 0) movingTime += possibleMovement / speed;

		if (movingTime > 0) {
			battery.consumeMove(movingTime);
		}
	}

	/**
	 * Sets the next destination and speed to correspond the next waypoint
	 * on the path.
	 */
	private boolean setNextWaypoint() {
		if (path == null) {
			path = movement.getPath();
		}

		if (path == null || !path.hasNext()) {
			this.nextTimeToMove = movement.nextPathAvailable();
			this.path = null;
			return false;
		}

		this.destination = path.getNextWaypoint();
		this.speed = path.getSpeed();

		if (this.movListeners != null) {
			for (MovementListener l : this.movListeners) {
				l.newDestination(this, this.destination, this.speed);
			}
		}

		return true;
	}

	/**
	 * Sends a message from this host to another host
	 */
	public void sendMessage(String id, DTNHost to) {
		this.router.sendMessage(id, to);
	}

	/**
	 * Start receiving a message from another host.
	 * RX energy is charged here on the receiving node.
	 */
	public int receiveMessage(Message m, DTNHost from) {
		if (battery.isDead()) {
			return MessageRouter.DENIED_UNSPECIFIED;
		}
		// Charge RX energy on this node (the receiver).
		battery.consumeRx(m.getSize());

		int retVal = this.router.receiveMessage(m, from);

		if (retVal == MessageRouter.RCV_OK) {
			m.addNodeOnPath(this);
		}

		return retVal;
	}

	/**
	 * Requests for deliverable message from this host to be sent trough a
	 * connection.
	 */
	public boolean requestDeliverableMessages(Connection con) {
		return this.router.requestDeliverableMessages(con);
	}

	/**
	 * Informs the host that a message was successfully transferred.
	 *
	 * NOTE: TX energy is NOT charged here. It is charged on the sender in
	 * Connection.finalizeTransfer(), which is the only place where both the
	 * sender identity (msgFromNode) and message size are known with certainty.
	 * Charging TX here would bill the wrong node (the receiver).
	 */
	public void messageTransferred(String id, DTNHost from) {
		this.router.messageTransferred(id, from);
	}

	/**
	 * Informs the host that a message transfer was aborted.
	 */
	public void messageAborted(String id, DTNHost from, int bytesRemaining) {
		this.router.messageAborted(id, from, bytesRemaining);
	}

	/**
	 * Creates a new message to this host's router
	 */
	public void createNewMessage(Message m) {
		this.router.createNewMessage(m);
	}

	/**
	 * Deletes a message from this host
	 */
	public void deleteMessage(String id, boolean drop) {
		this.router.deleteMessage(id, drop);
	}

	/**
	 * Returns a string presentation of the host.
	 */
	public String toString() {
		return name;
	}

	/**
	 * Checks if a host is the same as this host by comparing the object reference
	 */
	public boolean equals(DTNHost otherHost) {
		return this == otherHost;
	}

	/**
	 * Compares two DTNHosts by their addresses.
	 */
	public int compareTo(DTNHost h) {
		return this.getAddress() - h.getAddress();
	}

}