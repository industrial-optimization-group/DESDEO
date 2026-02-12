/** Utilities for extracting the decision path and computing journey data. */

import type {
	ENautilusSessionTreeResponse,
	ENautilusTreeNodeResponse,
	ENautilusDecisionEventResponse,
	ProblemInfo,
} from "$lib/gen/models";
import { analyzeTradeoffs, type ObjectiveTradeoff } from "$lib/components/custom/decision-tree/tree-utils";

export interface AlternativeDelta {
	optionIdx: number;
	/** chosen[key] - alternative[key] for each objective */
	deltas: Record<string, number>;
	/** Percentage deltas: delta / |ideal - nadir| * 100 */
	pctDeltas: Record<string, number>;
}

export interface JourneyStep {
	iteration: number;
	nodeId: number;
	/** Normalized to [0, 1] preserving natural value direction:
	 *  0 = min(ideal, nadir), 1 = max(ideal, nadir).
	 *  For maximize objectives the line rises; for minimize it falls. */
	normalizedValues: Record<string, number>;
	/** Raw (un-normalized) objective values for tooltip display. */
	rawValues: Record<string, number>;
	tradeoffs: ObjectiveTradeoff[] | null; // null for root (no decision made)
	/** Per-alternative deltas: chosen minus each non-chosen option */
	alternativeDeltas: AlternativeDelta[] | null;
	/** The intermediate points shown at this decision step */
	intermediatePoints: Record<string, number>[] | null;
	/** Index of the chosen option among intermediatePoints */
	chosenOptionIdx: number | null;
}

export interface PreferenceProfileEntry {
	key: string; // objective symbol
	label: string; // human name
	preferenceScore: number; // 0..1
}

export interface PairwiseTradeoffEntry {
	/** Objective that was favored (chose better options for) */
	favoredKey: string;
	favoredLabel: string;
	/** Objective that was sacrificed (accepted worse options for) */
	sacrificedKey: string;
	sacrificedLabel: string;
	/** Average normalized sacrifice: 0 = no cost, 1 = worst option always chosen */
	avgSacrifice: number;
	/** Number of decision steps where this tradeoff was observed */
	count: number;
}

export interface JourneyData {
	steps: JourneyStep[];
	objectiveKeys: string[];
	objectiveLabels: string[];
	/** Per-objective: true = maximize, false = minimize. */
	objectiveMaximize: boolean[];
	preferenceProfile: PreferenceProfileEntry[];
	pairwiseTradeoffs: PairwiseTradeoffEntry[];
}

/**
 * Walk the parent_node_id chain from the leaf back to the root,
 * then reverse to get a root-first ordering.
 * NOTE: buggy, if multiple branches, should be polished.
 */
export function extractPathToLeaf(
	tree: ENautilusSessionTreeResponse,
	leafNodeId: number,
): ENautilusTreeNodeResponse[] {
	const nodes = tree.nodes ?? [];
	const nodeMap = new Map<number, ENautilusTreeNodeResponse>();
	for (const node of nodes) {
		nodeMap.set(node.node_id, node);
	}

	const path: ENautilusTreeNodeResponse[] = [];
	let current = nodeMap.get(leafNodeId);
	if (!current) return [];

	// Guard against infinite loops (circular parent chains)
	const visited = new Set<number>();
	while (current) {
		if (visited.has(current.node_id)) break;
		visited.add(current.node_id);
		path.push(current);
		if (current.parent_node_id == null) break;
		current = nodeMap.get(current.parent_node_id);
	}

	path.reverse();
	return path;
}

/**
 * Compute journey data from the decision path.
 *
 * Normalization preserves the natural value direction:
 *   normalized = (value - lowerBound) / (upperBound - lowerBound)
 * where lowerBound = min(ideal, nadir), upperBound = max(ideal, nadir).
 *
 * This means:
 * - Maximize objectives (ideal > nadir): line rises from nadir toward ideal
 * - Minimize objectives (ideal < nadir): line falls from nadir toward ideal
 */
export function computeJourneyData(
	pathNodes: ENautilusTreeNodeResponse[],
	decisionEvents: ENautilusDecisionEventResponse[],
	problem: ProblemInfo,
	finalSolutionPoint?: Record<string, number> | null,
): JourneyData {
	const objectives = problem.objectives;
	const objectiveKeys = objectives.map((o) => o.symbol);
	const objectiveLabels = objectives.map((o) => o.name);
	const objectiveMaximize = objectives.map((o) => !!o.maximize);

	// Build a maximize map for analyzeTradeoffs
	const maximizeMap: Record<string, boolean> = {};
	for (const obj of objectives) {
		maximizeMap[obj.symbol] = !!obj.maximize;
	}

	// Build ideal map from the problem definition.
	const idealMap: Record<string, number> = {};
	for (const obj of objectives) {
		if (obj.ideal != null) {
			idealMap[obj.symbol] = obj.ideal;
		}
	}

	// Extract the root node's selected_point as the actual nadir baseline.
	// The problem's stored nadir may differ from the E-NAUTILUS starting point
	// (which is computed from representative solutions), so we use the root's
	// actual values to ensure the chart starts at exactly 0 (max) or 1 (min).
	const nadirMap: Record<string, number> = {};
	if (pathNodes.length > 0) {
		const rootPoint = pathNodes[0].selected_point as Record<string, number> | null;
		if (rootPoint) {
			for (const key of objectiveKeys) {
				if (rootPoint[key] != null) {
					nadirMap[key] = rootPoint[key];
				}
			}
		}
	}
	// Fallback: use problem nadir if root data is missing
	for (const obj of objectives) {
		if (nadirMap[obj.symbol] == null && obj.nadir != null) {
			nadirMap[obj.symbol] = obj.nadir;
		}
	}

	// Index decision events by (parent, child) pair for correct lookup
	// when the tree has branches from the same parent.
	const eventMap = new Map<string, ENautilusDecisionEventResponse>();
	const safeEvents = decisionEvents ?? [];
	for (const evt of safeEvents) {
		eventMap.set(`${evt.parent_node_id}-${evt.child_node_id}`, evt);
	}

	const steps: JourneyStep[] = [];
	const allTradeoffs: ObjectiveTradeoff[][] = [];

	for (let i = 0; i < pathNodes.length; i++) {
		const node = pathNodes[i];
		const iteration = node.current_iteration ?? i;

		// For the root node, use its selected_point if available
		// For subsequent nodes, use the decision event's chosen_point
		let pointValues: Record<string, number> | null = null;
		let tradeoffs: ObjectiveTradeoff[] | null = null;
		let alternativeDeltas: AlternativeDelta[] | null = null;
		let intermediatePoints: Record<string, number>[] | null = null;
		let chosenOptionIdx: number | null = null;

		if (i === 0) {
			// Root: use the node's selected_point (the nadir / starting position)
			pointValues = node.selected_point as Record<string, number> | null;
		} else {
			const parentNode = pathNodes[i - 1];
			const event = eventMap.get(`${parentNode.node_id}-${node.node_id}`);
			if (event) {
				pointValues = event.chosen_point as Record<string, number> | null;

				// Compute trade-offs from the parent's intermediate_points
				const options = parentNode.intermediate_points as Record<string, number>[] | null;
				if (options && event.chosen_option_idx != null) {
					intermediatePoints = options;
					chosenOptionIdx = event.chosen_option_idx;
					tradeoffs = analyzeTradeoffs(
						options,
						event.chosen_option_idx,
						maximizeMap,
					);
					if (tradeoffs) {
						allTradeoffs.push(tradeoffs);
					}

					// Compute per-alternative deltas (chosen - each other option)
					const chosen = options[event.chosen_option_idx];
					if (chosen) {
						alternativeDeltas = [];
						for (let oi = 0; oi < options.length; oi++) {
							if (oi === event.chosen_option_idx) continue;
							const deltas: Record<string, number> = {};
							const pctDeltas: Record<string, number> = {};
							for (const key of objectiveKeys) {
								const d = (chosen[key] ?? 0) - (options[oi][key] ?? 0);
								deltas[key] = d;
								const range = Math.abs((idealMap[key] ?? 0) - (nadirMap[key] ?? 0));
								pctDeltas[key] = range > 0 ? (d / range) * 100 : 0;
							}
							alternativeDeltas.push({ optionIdx: oi, deltas, pctDeltas });
						}
					}
				}
			}

			// Fallback: if no event found or chosen_point was null,
			// use the node's own selected_point.
			if (!pointValues) {
				pointValues = node.selected_point as Record<string, number> | null;
			}
		}

		// For the last node, override with the projected final solution if provided.
		// The tree only stores intermediate points; the actual Pareto-optimal solution
		// is fetched separately (representative solutions) and may differ.
		if (i === pathNodes.length - 1 && finalSolutionPoint) {
			pointValues = finalSolutionPoint;
		}

		// Normalize using actual nadir (root values) and problem ideal.
		// lo = min(ideal, nadir), hi = max(ideal, nadir).
		// Maximize (ideal > nadir): nadir→0, ideal→1 (line goes UP)
		// Minimize (ideal < nadir): nadir→1, ideal→0 (line goes DOWN)
		const normalizedValues: Record<string, number> = {};
		const rawValues: Record<string, number> = {};
		if (pointValues) {
			for (const key of objectiveKeys) {
				const value = pointValues[key];
				if (value == null) continue;

				rawValues[key] = value;

				const ideal = idealMap[key];
				const nadir = nadirMap[key];
				if (ideal != null && nadir != null && ideal !== nadir) {
					const lo = Math.min(ideal, nadir);
					const hi = Math.max(ideal, nadir);
					normalizedValues[key] = (value - lo) / (hi - lo);
				} else {
					normalizedValues[key] = 0.5;
				}
			}
		}

		steps.push({ iteration, nodeId: node.node_id, normalizedValues, rawValues, tradeoffs, alternativeDeltas, intermediatePoints, chosenOptionIdx });
	}

	// Compute preference profile:
	// For each objective, average (1 - normalizedRank) across all decision steps.
	const preferenceProfile: PreferenceProfileEntry[] = objectiveKeys.map(
		(key, idx) => {
			if (allTradeoffs.length === 0) {
				return { key, label: objectiveLabels[idx], preferenceScore: 0.5 };
			}

			let sum = 0;
			let count = 0;
			for (const tradeoffSet of allTradeoffs) {
				const entry = tradeoffSet.find((t) => t.key === key);
				if (entry) {
					sum += 1 - entry.normalizedRank;
					count++;
				}
			}

			const preferenceScore = count > 0 ? sum / count : 0.5;
			return { key, label: objectiveLabels[idx], preferenceScore };
		},
	);

	// Normalize preference scores to sum to 1 (relative shares)
	const totalScore = preferenceProfile.reduce((s, p) => s + p.preferenceScore, 0);
	if (totalScore > 0) {
		for (const p of preferenceProfile) {
			p.preferenceScore /= totalScore;
		}
	}

	// Compute pairwise tradeoffs: when A was favored over B, how much was B sacrificed?
	const pairwiseMap = new Map<string, { sacrificeSum: number; count: number }>();
	for (const tradeoffSet of allTradeoffs) {
		for (let a = 0; a < tradeoffSet.length; a++) {
			for (let b = 0; b < tradeoffSet.length; b++) {
				if (a === b) continue;
				const tA = tradeoffSet[a];
				const tB = tradeoffSet[b];
				// A was favored over B if A got a better rank (lower normalizedRank)
				if (tA.normalizedRank < tB.normalizedRank) {
					const pk = `${tA.key}\0${tB.key}`;
					const e = pairwiseMap.get(pk) ?? { sacrificeSum: 0, count: 0 };
					e.sacrificeSum += tB.normalizedRank;
					e.count += 1;
					pairwiseMap.set(pk, e);
				}
			}
		}
	}

	const pairwiseTradeoffs: PairwiseTradeoffEntry[] = [];
	for (const [pk, data] of pairwiseMap) {
		const [fk, sk] = pk.split('\0');
		const fi = objectiveKeys.indexOf(fk);
		const si = objectiveKeys.indexOf(sk);
		pairwiseTradeoffs.push({
			favoredKey: fk,
			favoredLabel: objectiveLabels[fi] ?? fk,
			sacrificedKey: sk,
			sacrificedLabel: objectiveLabels[si] ?? sk,
			avgSacrifice: data.sacrificeSum / data.count,
			count: data.count,
		});
	}
	pairwiseTradeoffs.sort((a, b) => b.count - a.count || b.avgSacrifice - a.avgSacrifice);

	return { steps, objectiveKeys, objectiveLabels, objectiveMaximize, preferenceProfile, pairwiseTradeoffs };
}
