/*
 * Released under GPLv3. See LICENSE.txt for details.
 *
 * PriorityLoader
 * ==============
 * Reads every Group<N>.groupID + Group<N>.priority pair from the active
 * Settings and registers them with NodeGraphic so nodes are colored by
 * priority from the very first simulation frame.
 *
 * Called from DTNSim.main() immediately after initSettings() and once per
 * batch run after resetForNextRun(), so that run-index-dependent settings
 * are always respected.
 *
 * No other class needs to call this directly.
 */
package core;

import gui.playfield.NodeGraphic;

public class PriorityLoader {

    private PriorityLoader() {}   // utility class, no instances

    /**
     * Reads Scenario.nrofHostGroups, then for each Group&lt;N&gt; reads
     * groupID and priority (defaulting to 0 if absent) and forwards the
     * pair to {@link NodeGraphic#setGroupPriority(String, int)}.
     *
     * Safe to call in batch (headless) mode: NodeGraphic.setGroupPriority
     * simply populates a static Map and does nothing GUI-specific.
     */
    public static void load() {
        Settings s = new Settings();

        int nrofGroups;
        try {
            nrofGroups = s.getInt("Scenario.nrofHostGroups");
        } catch (Exception e) {
            return;  // no groups defined
        }

        for (int i = 1; i <= nrofGroups; i++) {
            Settings gs = new Settings("Group" + i);

            String groupID;
            try {
                groupID = gs.getSetting("groupID");
            } catch (Exception e) {
                continue;  // group has no ID — skip
            }

            int priority = 0;
            try {
                priority = gs.getInt("priority");
            } catch (Exception e) {
                // priority not specified — keep default 0 (GREEN)
            }

            NodeGraphic.setGroupPriority(groupID, priority);
        }
    }
}