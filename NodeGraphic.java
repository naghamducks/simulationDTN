/*
 * Copyright 2010 Aalto University, ComNet
 * Released under GPLv3. See LICENSE.txt for details.
 *
 * Modified: priority-based group coloring.
 * Group colors are determined by stripping the numeric suffix from the
 * node name (e.g. "p5" → "p", "t340" → "t", "t315" → "t3").
 * No changes to DTNHost are required.
 *
 * Register group priorities ONCE at startup (e.g. in your scenario loader):
 *   NodeGraphic.setGroupPriority("p",  1);  // cyan
 *   NodeGraphic.setGroupPriority("c",  2);  // blue
 *   NodeGraphic.setGroupPriority("w",  5);  // red  – distress
 *   NodeGraphic.setGroupPriority("t3", 3);  // yellow
 *   NodeGraphic.setGroupPriority("t4", 4);  // orange
 *   NodeGraphic.setGroupPriority("t10",0);  // green
 *
 * Priority → color:
 *   5 = RED    (highest / distress)
 *   4 = ORANGE
 *   3 = YELLOW
 *   2 = BLUE
 *   1 = CYAN
 *   0 = GREEN  (default / lowest)
 */
package gui.playfield;

import java.awt.Color;
import java.awt.Graphics2D;
import java.awt.geom.Ellipse2D;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import core.Connection;
import core.Coord;
import core.DTNHost;
import core.NetworkInterface;

/**
 * Visualization of a DTN Node
 */
public class NodeGraphic extends PlayFieldGraphic {
	private static boolean drawCoverage;
	private static boolean drawNodeName;
	private static boolean drawConnections;
	private static boolean drawBuffer;
	private static List<DTNHost> highlightedNodes;

	// ---------------------------------------------------------------
	// Priority color palette  (index = priority level 0..5)
	// ---------------------------------------------------------------
	private static final Color[] PRIORITY_COLORS = {
		new Color(0,   180,   0),   // 0 → GREEN   (lowest / default)
		new Color(0,   180, 220),   // 1 → CYAN
		new Color(30,  100, 255),   // 2 → BLUE
		new Color(220, 200,   0),   // 3 → YELLOW
		new Color(255, 140,   0),   // 4 → ORANGE
		new Color(220,   0,   0),   // 5 → RED     (highest / distress)
	};

	/**
	 * groupID prefix  →  priority (0-5).
	 * Populated via setGroupPriority().
	 * Any group not registered here defaults to priority 0 (GREEN).
	 */
	private static final Map<String, Integer> groupPriorities =
		new HashMap<String, Integer>();

	// Legacy colors kept for coverage rings, connection lines, and msg bars
	private static final Color rangeColor          = Color.GREEN;
	private static final Color conColor            = Color.BLACK;
	private static final Color msgColor1           = Color.BLUE;
	private static final Color msgColor2           = Color.GREEN;
	private static final Color msgColor3           = Color.RED;
	private static final Color highlightedNodeColor = Color.MAGENTA;

	private final DTNHost node;

	public NodeGraphic(DTNHost node) {
		this.node = node;
	}

	// ---------------------------------------------------------------
	// Public API – call once per group at simulation startup
	// ---------------------------------------------------------------

	/**
	 * Register the display priority for a group ID prefix.
	 *
	 * @param groupID  the group's ID prefix exactly as written in
	 *                 the settings file (e.g. "p", "c", "w", "t3", "t4", "t10")
	 * @param priority 0 (green/lowest) … 5 (red/highest); clamped automatically
	 */
	public static void setGroupPriority(String groupID, int priority) {
		groupPriorities.put(groupID, Math.max(0, Math.min(5, priority)));
	}

	// ---------------------------------------------------------------
	// Internal helpers
	// ---------------------------------------------------------------

	/**
	 * Extracts the alphabetic group prefix from a node name.
	 *
	 * Node names are formed as  groupID + address  (e.g. "p5", "c12",
	 * "w3", "t340").  For multi-character IDs like "t3", "t4", "t10"
	 * the address is purely numeric, so we strip all trailing digits to
	 * recover the prefix.
	 *
	 * Strategy: try the longest registered prefix that matches the start
	 * of the name before falling back to stripping trailing digits.
	 * This handles both "t3" (prefix) and "t" (prefix) correctly even
	 * when both are registered.
	 */
	private String extractGroupId() {
		String name = node.toString(); // e.g. "t340", "p5", "t3_1"

		// 1. Try every registered prefix, longest first – most specific wins
		String best = null;
		for (String prefix : groupPriorities.keySet()) {
			if (name.startsWith(prefix)) {
				if (best == null || prefix.length() > best.length()) {
					best = prefix;
				}
			}
		}
		if (best != null) {
			return best;
		}

		// 2. Fallback: strip trailing digits to reconstruct the prefix
		int i = name.length() - 1;
		while (i >= 0 && Character.isDigit(name.charAt(i))) {
			i--;
		}
		return (i >= 0) ? name.substring(0, i + 1) : name;
	}

	/**
	 * Returns the display color for this node based on its group's priority.
	 */
	private Color getNodeColor() {
		String groupId = extractGroupId();
		int priority   = groupPriorities.containsKey(groupId)
		                 ? groupPriorities.get(groupId) : 0;
		return PRIORITY_COLORS[priority];
	}

	// ---------------------------------------------------------------
	// Drawing
	// ---------------------------------------------------------------

	@Override
	public void draw(Graphics2D g2) {
		drawHost(g2);
		if (drawBuffer) {
			drawMessages(g2);
		}
	}

	private boolean isHighlighted() {
		return highlightedNodes != null && highlightedNodes.contains(node);
	}

	private void drawHost(Graphics2D g2) {
		Coord loc = node.getLocation();

		// Radio coverage circles
		if (drawCoverage && node.isRadioActive()) {
			ArrayList<NetworkInterface> interfaces =
				new ArrayList<NetworkInterface>(node.getInterfaces());
			for (NetworkInterface ni : interfaces) {
				double range = ni.getTransmitRange();
				Ellipse2D.Double coverage = new Ellipse2D.Double(
					scale(loc.getX() - range), scale(loc.getY() - range),
					scale(range * 2),          scale(range * 2));
				g2.setColor(rangeColor);
				g2.draw(coverage);
			}
		}

		// Connection lines
		if (drawConnections) {
			g2.setColor(conColor);
			Coord c1 = node.getLocation();
			ArrayList<Connection> conList =
				new ArrayList<Connection>(node.getConnections());
			for (Connection c : conList) {
				DTNHost otherNode = c.getOtherNode(node);
				if (otherNode == null) continue;
				Coord c2 = otherNode.getLocation();
				g2.drawLine(scale(c1.getX()), scale(c1.getY()),
				            scale(c2.getX()), scale(c2.getY()));
			}
		}

		// Node rectangle – colored by priority
		Color nodeColor = getNodeColor();
		g2.setColor(nodeColor);
		g2.drawRect(scale(loc.getX() - 1), scale(loc.getY() - 1),
		            scale(2), scale(2));

		// Highlighted node (filled magenta square)
		if (isHighlighted()) {
			g2.setColor(highlightedNodeColor);
			g2.fillRect(scale(loc.getX()) - 3, scale(loc.getY()) - 3, 6, 6);
		}

		// Node name label
		if (drawNodeName) {
			g2.setColor(nodeColor);
			g2.drawString(node.toString(), scale(loc.getX()), scale(loc.getY()));
		}
	}

	// ---------------------------------------------------------------
	// Static setters
	// ---------------------------------------------------------------

	public static void setDrawCoverage(boolean draw)    { drawCoverage    = draw; }
	public static void setDrawNodeName(boolean draw)    { drawNodeName    = draw; }
	public static void setDrawConnections(boolean draw) { drawConnections = draw; }
	public static void setDrawBuffer(boolean draw)      { drawBuffer      = draw; }
	public static void setHighlightedNodes(List<DTNHost> nodes) {
		highlightedNodes = nodes;
	}

	// ---------------------------------------------------------------
	// Message buffer bars (unchanged)
	// ---------------------------------------------------------------

	private void drawMessages(Graphics2D g2) {
		int nrofMessages = node.getNrofMessages();
		Coord loc = node.getLocation();
		drawBar(g2, loc, nrofMessages % 10, 1);
		drawBar(g2, loc, nrofMessages / 10, 2);
	}

	private void drawBar(Graphics2D g2, Coord loc, int nrof, int col) {
		final int BAR_HEIGHT      = 5;
		final int BAR_WIDTH       = 5;
		final int BAR_DISPLACEMENT = 2;

		for (int i = 1; i <= nrof; i++) {
			if (i % 2 == 0) {
				g2.setColor(msgColor1);
			} else {
				g2.setColor(col > 1 ? msgColor3 : msgColor2);
			}
			g2.fillRect(
				scale(loc.getX() - BAR_DISPLACEMENT - (BAR_WIDTH * col)),
				scale(loc.getY() - BAR_DISPLACEMENT - i * BAR_HEIGHT),
				scale(BAR_WIDTH),
				scale(BAR_HEIGHT));
		}
	}
}