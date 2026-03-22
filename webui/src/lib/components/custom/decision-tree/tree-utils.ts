/** Utilities for building d3-hierarchy from flat tree API response. */

import { hierarchy, type HierarchyNode } from "d3-hierarchy";
import type {
    TreeNodeResponse,
    SessionTreeResponse,
    TreeHierarchyDatum,
} from "./tree-types";

/**
 * Build a d3 HierarchyNode from the flat session tree response.
 *
 * If multiple roots exist, a virtual root is created to unify them.
 */
export function buildHierarchy(
    tree: SessionTreeResponse
): HierarchyNode<TreeHierarchyDatum> {
    const nodeMap = new Map<number, TreeNodeResponse>();
    for (const node of tree.nodes) {
        nodeMap.set(node.node_id, node);
    }

    // Build children lookup from edges
    const childrenMap = new Map<number, number[]>();
    for (const [parentId, childId] of tree.edges) {
        const children = childrenMap.get(parentId) ?? [];
        children.push(childId);
        childrenMap.set(parentId, children);
    }

    function buildDatum(nodeId: number): TreeHierarchyDatum {
        const node = nodeMap.get(nodeId)!;
        const childIds = childrenMap.get(nodeId) ?? [];
        return {
            id: nodeId,
            node,
            children: childIds
                .filter((cid) => nodeMap.has(cid))
                .map((cid) => buildDatum(cid)),
        };
    }

    if (tree.root_ids.length === 1) {
        return hierarchy(buildDatum(tree.root_ids[0]), (d) => d.children);
    }

    // Multiple roots: create virtual root
    const virtualRoot: TreeHierarchyDatum = {
        id: -1,
        node: {
            node_id: -1,
            parent_node_id: null,
            depth: -1,
            node_type: "step",
            current_iteration: null,
            iterations_left: null,
            selected_point: null,
            intermediate_points: null,
            closeness_measures: null,
            selected_point_index: null,
            selected_intermediate_point: null,
            final_solution_objectives: null,
        },
        children: tree.root_ids
            .filter((rid) => nodeMap.has(rid))
            .map((rid) => buildDatum(rid)),
    };

    return hierarchy(virtualRoot, (d) => d.children);
}

/** Get a color for a node based on its iteration progress (0..maxIter). */
export function nodeColor(
    node: TreeNodeResponse,
    maxIteration: number
): string {
    if (node.node_type === "final") {
        return "#10b981"; // emerald-500
    }

    if (maxIteration <= 0 || node.current_iteration == null) {
        return "#6b7280"; // gray-500
    }

    // Interpolate from blue (early) to orange (late)
    const t = node.current_iteration / maxIteration;
    const r = Math.round(59 + t * (234 - 59));
    const g = Math.round(130 + t * (88 - 130));
    const b = Math.round(246 + t * (12 - 246));
    return `rgb(${r}, ${g}, ${b})`;
}

/** Format objective values for display. */
export function formatPoint(
    point: Record<string, number> | null | undefined
): string {
    if (!point) return "—";
    return Object.entries(point)
        .map(([k, v]) => `${k}: ${v.toFixed(4)}`)
        .join(", ");
}

/** Trade-off analysis for one objective at a decision point. */
export interface ObjectiveTradeoff {
    /** Objective symbol (e.g. "f_1") */
    key: string;
    /** Value of this objective in the chosen point */
    chosenValue: number;
    /** Rank among the options (1 = best, N = worst). */
    rank: number;
    /** Total number of options */
    total: number;
    /** Normalized position: 0 = best among options, 1 = worst */
    normalizedRank: number;
    /** Best value among all options for this objective */
    bestValue: number;
    /** Worst value among all options for this objective */
    worstValue: number;
    /** Whether this objective is to be maximized */
    maximize: boolean;
}

/**
 * Analyze the trade-offs made in a decision.
 *
 * Compares the chosen intermediate point against all options that were shown.
 * For each objective, computes the rank of the chosen value among the options,
 * respecting whether each objective is to be minimized or maximized.
 *
 * @param options The intermediate points shown to the DM (parent node's intermediate_points)
 * @param chosenIdx The index of the option that was chosen
 * @param maximizeMap Optional map from objective key to whether it should be maximized.
 *                    Keys not present default to minimize (maximize=false).
 * @returns Per-objective trade-off analysis, or null if inputs are invalid
 */
export function analyzeTradeoffs(
    options: Record<string, number>[],
    chosenIdx: number,
    maximizeMap?: Record<string, boolean>
): ObjectiveTradeoff[] | null {
    if (!options || options.length < 2 || chosenIdx < 0 || chosenIdx >= options.length) {
        return null;
    }

    const chosen = options[chosenIdx];
    const keys = Object.keys(chosen);

    return keys.map((key) => {
        const maximize = maximizeMap?.[key] ?? false;
        const chosenValue = chosen[key];
        const allValues = options.map((opt) => opt[key]);

        // Sort ascending for minimize, descending for maximize
        // so that index 0 is always the "best"
        const sorted = maximize
            ? [...allValues].sort((a, b) => b - a)
            : [...allValues].sort((a, b) => a - b);

        const bestValue = sorted[0];
        const worstValue = sorted[sorted.length - 1];

        // Rank: 1-based, position in sorted-by-preference order
        const rank = sorted.indexOf(chosenValue) + 1;
        const total = options.length;
        const normalizedRank = total > 1 ? (rank - 1) / (total - 1) : 0;

        return { key, chosenValue, rank, total, normalizedRank, bestValue, worstValue, maximize };
    });
}
