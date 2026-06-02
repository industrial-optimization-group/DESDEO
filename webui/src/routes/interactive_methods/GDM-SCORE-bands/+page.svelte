<script lang="ts">
	/**
	 * +page.svelte (GDM-SCORE-bands method)
	 *
	 * @author Stina (Functionality) <palomakistina@gmail.com>
	 * @author Giomara Larraga (Base structure) <glarragw@jyu.fi>
	 * @created December 2025
	 *
	 * @description
	 * Group decision making interface using SCORE-bands method.
	 * Handles consensus phase (band voting) and decision phase (solution voting).
	 *
	 * @props
	 * @property {Object} data - Contains authentication token, group info, and problem data.
	 * @property {string} data.refreshToken - JWT refresh token for authentication.
	 * @property {GroupPublic} data.group - Group information including members and owner.
	 * @property {ProblemInfo} data.problem - Optimization problem definition and metadata.
	 *
	 * @features
	 * - Real-time collaboration via WebSocket
	 * - Two-phase process: consensus reaching and decision phase
	 * - SCORE-bands visualization for voting in consensus reaching phase
	 * - Parallel coordinates visualization for solution voting in decision phase
	 * - Configuration panel for method parameters (number of solutions, clusters, etc.) (group owner only)
	 * - History browser with possibility to revert to chosen iteration (group owner only)
	 * - Role-based access control (group owner vs decision makers)
	 * - Cluster visibility controls with solution count display
	 * - Agreement calculation and consensus indicators (axis colors)
	 * - Voted bands visible in bar chart visualization
	 * - Solution table with detailed objective and decision variable values for decision phase
	 *
	 * @dependencies
	 * - ScoreBands: Main visualization component for SCORE-bands method
	 * - ParallelCoordinates: Visualization for solution comparison
	 * - ScoreBandsSolutionTable: Table component for displaying solution details
	 * - HistoryBrowser: Component for browsing iteration history
	 * - ConfigPanel: Configuration interface for method parameters
	 * - WebSocketService: Real-time communication service for collaboration
	 * - Button: UI component for actions and controls
	 * - Alert: For displaying error messages and notifications
	 * - createObjectiveDimensions: Helper for visualization data transformation
	 * - Helper functions: drawVotesChart, calculateAxisAgreement, generate_axis_options, etc.
	 *
	 * @notes
	 * - WebSocket connection is established automatically when component mounts
	 * - User roles are determined from group membership and ownership
	 * - State is managed using Svelte's reactive $state and $derived declarations
	 * - Real-time updates are handled through WebSocket message processing
	 * - Consensus is calculated based on agreement thresholds and vote patterns
	 *
	 * @phases
	 * 1. Band Voting Phase (CRP):
	 *    - Decision makers vote on preferred objective value bands
	 *    - SCORE-bands visualization shows clusters and voting interface
	 *    - Real-time consensus tracking with agreement indicators
	 *    - Configuration panel allows adjusting method parameters
	 *
	 * 2. Solution Voting Phase (Decision phase):
	 *    - Activated after API returns different data without bands, meaning there are under 10 solutions
	 *    - Parallel coordinates show solutions within agreed bands
	 *    - Decision makers vote on specific solutions
	 *    - Final solution selected based on voting results
	 */

	import { Button } from '$lib/components/ui/button';
	import ScoreBands from '$lib/components/visualizations/score-bands/score-bands.svelte';
	import ParallelCoordinates from '$lib/components/visualizations/parallel-coordinates/parallel-coordinates.svelte';
	import ScoreBandsSolutionTable from './score-bands-solution-table.svelte';
	import ClusterBandTable from '$lib/components/custom/score-bands-table/solution-table.svelte';
	import HistoryBrowser from './history-browser.svelte';
	import ConfigPanel from './config-panel.svelte';
	import { onMount, onDestroy } from 'svelte';
	import type { GroupPublic, ProblemInfo, GDMSCOREBandsResponse, GDMSCOREBandsDecisionResponse, SCOREBandsResult, SCOREBandsConfig, GDMSCOREBandFinalSelection, SCOREBandsGDMConfig } from '$lib/gen/endpoints/DESDEOFastAPI';
	import { auth } from '../../../stores/auth';
	import { errorMessage } from '../../../stores/uiState';
	import Alert from '$lib/components/custom/notifications/alert.svelte';
	import { createObjectiveDimensions } from '$lib/helpers/visualization-data-transform';

	import { WebSocketService } from './websocket-store';

	import {
		drawVotesChart,
		calculateAxisAgreement,
		generate_axis_options,
		generate_cluster_colors,
		calculateScales
	} from './helper-functions';
	import { json } from 'd3';

	type LearningNote = {
		id: string;
		targetType: 'band' | 'sub-band' | 'solution';
		targetId: string;
		text: string;
		createdAt: string;
	};

	type LearningSubBand = {
		id: string;
		parentClusterId: number;
		label: string;
		solutionIndices: number[];
		color: string;
	};

	let learningState = $state({
		selectedBand: null as number | null,
		savedBands: [] as number[],
		comparedBands: [] as number[],
		notes: [] as LearningNote[],
		zoomedBand: null as number | null,
		subBands: [] as LearningSubBand[]
	});

	const { data } = $props<{
		data: {
			refreshToken: string;
			group: GroupPublic;
			problem: ProblemInfo;
		};
	}>();

	// User authentication
	let userId = $auth.user?.id;
	let isOwner = $state(false);
	let isDecisionMaker = $state(false);

	// Initialize user roles
	$effect(() => {
		isOwner = userId === data.group.owner_id;
		isDecisionMaker = data.group.user_ids.includes(userId);
	});

	// WebSocket service for real-time updates
	let wsService: WebSocketService | null = $state(null);

	//
	let data_loaded = $state(false);
	let loading_error: string | null = $state(null);

	// State of votes, confirms, and related data
	let vote_confirmed = $state(false);
	let votes_and_confirms = $state({
		confirms: [] as number[],
		votes: {} as Record<number, number>
	});
	// If user has voted, usersVote is the id they voted for. If not, null.
	let usersVote: number | null = $derived.by(() => {
		if (userId && votes_and_confirms.votes.hasOwnProperty(userId)) {
			return votes_and_confirms.votes[userId];
		}
		return null;
	});
	const totalVoters = $derived(data.group.user_ids.length);
	let have_all_voted = $derived.by(() => {
		return totalVoters === Object.keys(votes_and_confirms.votes || {}).length;
	});

	$effect(() => {
		if (userId) {
			vote_confirmed = votes_and_confirms.confirms.includes(userId);
		} else {
			vote_confirmed = false;
		}
	});

	let votes_per_cluster: Record<number, number> = $derived.by(() => {
		const counts: Record<number, number> = {};
		Object.values(votes_and_confirms.votes).forEach((bandId) => {
			if (!(bandId in counts)) {
				counts[bandId] = 0;
			}
			counts[bandId] += 1;
		});
		return counts;
	});

	function getClusterVoteCount(clusterId: number): number {
	return votes_per_cluster[clusterId] ?? 0;
}

function getClusterVotePercent(clusterId: number): number {
	if (totalVoters === 0) return 0;
	return Math.round((getClusterVoteCount(clusterId) / totalVoters) * 100);
}

function getConsensusLabel(axisName: string): string {
	const status = axis_agreement?.[axisName];

	if (status === 'agreement') return 'Agreement';
	if (status === 'disagreement') return 'Disagreement';
	return 'Neutral';
}

function getConsensusClasses(axisName: string): string {
	const status = axis_agreement?.[axisName];

	if (status === 'agreement') return 'text-green-700';
	if (status === 'disagreement') return 'text-red-700';
	return 'text-muted-foreground';
}

	// Calculate axis agreement when everyone has voted
	let axis_agreement = $derived.by(() => {
		// Only calculate if we're in consensus phase and have the necessary data
		if (!isConsensusPhase || !SCOREBands.medians || !SCOREBands.scales) {
			return {};
		}

		const votesCount = Object.keys(votes_and_confirms.votes || {}).length;

		// Calculate when everyone has voted
		if (votesCount === totalVoters) {
			return calculateAxisAgreement(
				votes_and_confirms,
				SCOREBands.medians,
				SCOREBands.scales,
				0.1, // agreement threshold
				0.9 // disagreement threshold
			);
		}

		return {}; // Return empty object when conditions aren't met
	});

	// Iteration info: history, current iteration, phase, etc.
	let history: (
		| GDMSCOREBandsResponse
		| GDMSCOREBandsDecisionResponse
	)[] = $state([]);
	//let phase = $state('Consensus Reaching Phase'); // 'Consensus reaching phase' or 'Decision phase'
	let phase = $state('Learning Phase');

	let isLearningPhase = $derived(phase === 'Learning Phase');
	let isDecisionPhase = $derived(phase === 'Decision Phase');
	let isConsensusPhase = $derived(phase === 'Consensus Reaching Phase');

	
	let iteration_id = $state(0); // for header and fetch_score_bands
	// current iteration data for consensus reaching phase, when bands exist
	let scoreBandsResult: SCOREBandsResult | null = $state(null);

	// Configuration and latestIteration are used in initialization and configPanel
	let latestIteration: number | null = $state(null);
	let scoreBandsConfig: SCOREBandsConfig = $state({
		clustering_algorithm: {
			name: 'KMeans',
			n_clusters: 5
		},
		distance_formula: 1,
		distance_parameter: 0.05,
		use_absolute_correlations: false,
		include_solutions: false,
		include_medians: true,
		interval_size: 0.25
	});
	// Current iteration data for decision phase, when solutions exist and not bands
	let decisionResult: GDMSCOREBandFinalSelection | null = $state(null);

	// Derived state to determine which phase we're in, for conditional component rendering
	//let isDecisionPhase = $derived(phase === 'Decision Phase');
	//let isConsensusPhase = $derived(phase === 'Consensus Reaching Phase');

	// Map raw objective keys to display labels for SCORE-bands axes.
	// Prefer objective.name for readability, but keep robust fallbacks.
	let objectiveDisplayMap = $derived.by(() => {
		const map: Record<string, string> = {};
		(data.problem.objectives || []).forEach((objective: any) => {
			const displayLabel = objective.name || objective.symbol;
			if (!displayLabel) return;

			if (objective.name) {
				map[objective.name] = displayLabel;
			}
			if (objective.symbol) {
				map[objective.symbol] = displayLabel;
			}
		});
		return map;
	});

	// Data from scoreBandsResult stored in format that is actually used in UI
	let SCOREBands = $derived.by(() => {
		if (!scoreBandsResult || scoreBandsResult === null) {
			return {
				axisNames: [] as string[],
				clusterIds: [] as number[],
				axisPositions: [] as number[],
				axisSigns: [] as number[],
				data: [] as number[][],
				bands: {},
				medians: {},
				scales: undefined,
				solutions_per_cluster: {} as Record<string, number>
			};
		}

		const rawAxisNames = scoreBandsResult.ordered_dimensions;
		const displayAxisNames = rawAxisNames.map(
			(axisName) => objectiveDisplayMap[axisName] || axisName
		);

		const remapAxisKeyedObject = <T,>(
			obj: Record<string, Record<string, T>>
		): Record<string, Record<string, T>> => {
			return Object.fromEntries(
				Object.entries(obj).map(([clusterId, axisValues]) => [
					clusterId,
					Object.fromEntries(
						Object.entries(axisValues).map(([axisName, value]) => [
							objectiveDisplayMap[axisName] || axisName,
							value
						])
					)
				])
			);
		};

		const rawScales = calculateScales(data.problem, scoreBandsResult);
		const remappedScales = displayAxisNames.reduce(
			(acc, displayAxisName, index) => {
				const rawAxisName = rawAxisNames[index];
				acc[displayAxisName] =
					rawScales[rawAxisName] || rawScales[displayAxisName] || [0, 1];
				return acc;
			},
			{} as Record<string, [number, number]>
		);

		const derivedData = {
			axisNames: displayAxisNames,
			clusterIds: Object.keys(scoreBandsResult.bands)
				.sort((a, b) => parseInt(a) - parseInt(b))
				.map((id) => Number(id)),
			// Convert axis_positions dict to ordered array
			axisPositions: rawAxisNames.map(
				(objName) => scoreBandsResult?.axis_positions[objName]
			) as number[],

			// TODO: Visualization used axisSigns, but is the info from backend or user in UI? "Flip axes" -checkbox?
			axisSigns: new Array(rawAxisNames.length).fill(1),
			data: [], // TODO: This could be filled with solution data, if it will be a thing later. Visualization might not work: copy-paste from old function, not tested.
			bands: remapAxisKeyedObject(scoreBandsResult.bands),
			medians: remapAxisKeyedObject(scoreBandsResult.medians),
			scales: remappedScales,
			solutions_per_cluster: scoreBandsResult.cardinalities
		};
		return derivedData;
	});

	// Visualization options with checkboxes
	let show_bands = $state(true);
	let show_solutions = $state(false); // Disabled and hidden for now - no individual solutions
	let show_medians = $state(false); // Hide medians by default

	// Helper functions to prevent deselecting all visualization options
	function canToggleBands() {
		// Can toggle bands off only if medians would remain on
		return !show_bands || show_medians || show_solutions;
	}

	function canToggleMedians() {
		// Can toggle medians off only if bands would remain on
		return !show_medians || show_bands || show_solutions;
	}

	// options for drawing score bands
	let options = $derived.by(() => {
		return {
			bands: show_bands,
			solutions: show_solutions,
			medians: show_medians
		};
	});

	// Cluster visibility controls
	let cluster_visibility_map: Record<number, boolean> = $state({});

	// Helper function to initialize all clusters as visible
	function clusters_to_visible() {
		if (SCOREBands && SCOREBands.clusterIds.length > 0) {
			SCOREBands.clusterIds.forEach((clusterId) => {
				cluster_visibility_map[clusterId] = true;
			});
		}
	}

	// Update cluster visibility when groups data changes
	$effect(() => {
		if (SCOREBands && SCOREBands.clusterIds.length > 0) {
			// Initialize all clusters as visible if not already set
			SCOREBands.clusterIds.forEach((clusterId) => {
				if (!(clusterId in cluster_visibility_map)) {
					cluster_visibility_map[clusterId] = true;
				}
			});
			// Remove clusters that no longer exist in the data
			Object.keys(cluster_visibility_map).forEach((clusterId) => {
				if (!SCOREBands.clusterIds.includes(Number(clusterId))) {
					delete cluster_visibility_map[Number(clusterId)];
				}
			});
		}
	});

	// Axis order control
	// TODO: not used now. Remove if unnecessary, use if needed
	let custom_axis_order: number[] = $state([]);
	let use_custom_order = $state(false);

	// For SCORE bands, the axisNames from the result are already in optimal order,
	// so we use the default sequential order [0, 1, 2, ...] unless custom order is specified
	let effective_axis_order = $derived.by(() => {
		const axisCount = SCOREBands.axisNames.length;
		if (use_custom_order && custom_axis_order.length === axisCount) {
			return custom_axis_order;
		}
		// Default sequential order [0, 1, 2, ...] is counted in component, no need here
		return [];
	});

	// visualization options not decided by user
	let cluster_colors = $derived(
		SCOREBands.clusterIds.length > 0 ? generate_cluster_colors(SCOREBands.clusterIds) : {}
	);

	let clusterBandRows = $derived.by(() => {
		if (
			!(isLearningPhase || isConsensusPhase) ||
			!SCOREBands.clusterIds.length ||
			!SCOREBands.scales ||
			!SCOREBands.bands ||
			!SCOREBands.medians
		) {
			return [];
		}

		const axisNames = SCOREBands.axisNames;

		return Object.keys(SCOREBands.bands).map((clusterId) => {
			const objectiveRanges: Record<string, any> = {};

			axisNames.forEach((axisName) => {
				const bandRange = SCOREBands.bands[clusterId]?.[axisName];
				const median = SCOREBands.medians[clusterId]?.[axisName];
				const axisScale = SCOREBands.scales?.[axisName];

				if (!bandRange || median === undefined) return;
				if (!axisScale || axisScale.length !== 2) return;

				const scaleMin = Math.min(axisScale[0], axisScale[1]);
				const scaleMax = Math.max(axisScale[0], axisScale[1]);

				objectiveRanges[axisName] = {
					min: Math.min(bandRange[0], bandRange[1]),
					max: Math.max(bandRange[0], bandRange[1]),
					median,
					scaleMin,
					scaleMax
				};
			});

			return {
				id: Number(clusterId),
				label: `Cluster ${clusterId} band`,
				color: cluster_colors[Number(clusterId)] || '#64748b',
				numSolutions: SCOREBands.solutions_per_cluster[clusterId] ?? 0,
				objectiveRanges
			};
		});
	});

	let axis_options = $derived(
		SCOREBands.axisNames.length > 0
			? generate_axis_options(SCOREBands.axisNames, axis_agreement)
			: []
	);

	// Selection state
	let selected_band: number | null = $state(null);
	let selected_axis: number | null = $state(null); // not used, axis selection commented out
	let selected_solution: number | null = $state(null); // for decision phase

	// Selection handlers
	function selectLearningBand(clusterId: number | null) {
		learningState.selectedBand = clusterId;
	}

	function toggleSavedBand(clusterId: number) {
		learningState.savedBands = learningState.savedBands.includes(clusterId)
			? learningState.savedBands.filter((id) => id !== clusterId)
			: [...learningState.savedBands, clusterId];
	}

	function toggleCompareBand(clusterId: number) {
		if (learningState.comparedBands.includes(clusterId)) {
			learningState.comparedBands = learningState.comparedBands.filter((id) => id !== clusterId);
			return;
		}

		if (learningState.comparedBands.length >= 3) return;

		learningState.comparedBands = [...learningState.comparedBands, clusterId];
	}

	function zoomIntoBand(clusterId: number) {
		learningState.zoomedBand = clusterId;
		learningState.selectedBand = clusterId;
	}

	function exitBandZoom() {
		learningState.zoomedBand = null;
		learningState.subBands = [];
	}

	function createPersonalSubBands(numberOfSubBands = 3) {
		if (learningState.zoomedBand === null || !scoreBandsResult) return;

		const visibleIndices = scoreBandsResult.clusters
			.map((clusterId, index) => ({ clusterId, index }))
			.filter((item) => item.clusterId === learningState.zoomedBand)
			.map((item) => item.index);

		const chunkSize = Math.ceil(visibleIndices.length / numberOfSubBands);
		const colors = ['#8b5cf6', '#06b6d4', '#f97316', '#22c55e'];

		learningState.subBands = Array.from({ length: numberOfSubBands }, (_, i) => ({
			id: `${learningState.zoomedBand}-${i + 1}`,
			parentClusterId: learningState.zoomedBand!,
			label: `Sub-band ${learningState.zoomedBand}.${i + 1}`,
			solutionIndices: visibleIndices.slice(i * chunkSize, (i + 1) * chunkSize),
			color: colors[i % colors.length]
		}));
	}
	function handle_band_select(clusterId: number | null) {
		selected_band = clusterId;
	}

	function handle_axis_select(axisIndex: number | null) {
		// TODO: Waiting until there is need to select an axis. Should happen if user will be able to move axes later.
		// selected_axis = axisIndex;
	}

	function handle_solution_select(index: number | null) {
		selected_solution = index;
	}

	// Check if group decision is reached
	let isGroupDecisionReached = $derived.by(() => {
		return (
			decisionResult?.winner_solution_objectives &&
			Object.keys(decisionResult.winner_solution_objectives).length > 0
		);
	});

	// Get the index of the winning solution
	let winnerSolutionIndex = $derived.by(() => {
		if (
			!isGroupDecisionReached ||
			!decisionResult?.solution_objectives ||
			!decisionResult?.winner_solution_objectives
		) {
			return null;
		}

		// Find which solution matches the winner objectives
		const objectives = decisionResult.solution_objectives;
		const winnerObjectives = decisionResult.winner_solution_objectives;
		const numSolutions = Object.values(objectives)[0]?.length || 0;

		for (let i = 0; i < numSolutions; i++) {
			let matches = true;
			for (const [objName, winnerValue] of Object.entries(winnerObjectives)) {
				if (objectives[objName] && objectives[objName][i] !== winnerValue) {
					matches = false;
					break;
				}
			}
			if (matches) return i;
		}
		return 0; // fallback to first solution if no exact match found
	});

	// Transform solution data for parallel coordinates visualization in decision phase
	let decisionSolutions = $derived.by(() => {
		if (!decisionResult || !decisionResult.solution_objectives) {
			return [];
		}

		const objectives = decisionResult.solution_objectives;
		const numSolutions = Object.values(objectives)[0]?.length || 0;

		return Array.from({ length: numSolutions }, (_, index) => {
			const solution: { [key: string]: number } = {};
			Object.entries(objectives).forEach(([objectiveName, values]) => {
				solution[objectiveName] = values[index];
			});
			return solution;
		});
	});

	// Votes chart container
	let votesChartContainer: HTMLDivElement | undefined = $state();
	let waitingRefreshTimer: ReturnType<typeof setInterval> | null = null;
	let consensusVotesSyncTimer: ReturnType<typeof setInterval> | null = null;
	let isConsensusVoteSyncing = $state(false);
	let isConsensusIterationSyncing = $state(false);

	// Update votes chart when votes change
	$effect(() => {
		if (votesChartContainer) {
			drawVotesChart(votesChartContainer, votes_per_cluster, totalVoters, cluster_colors);
		}
	});

	$effect(() => {
		const shouldSyncVotes =
			isConsensusPhase || (isDecisionPhase && !isGroupDecisionReached);

		if (!shouldSyncVotes) {
			if (consensusVotesSyncTimer) {
				clearInterval(consensusVotesSyncTimer);
				consensusVotesSyncTimer = null;
			}
			return;
		}

		if (!consensusVotesSyncTimer) {
			// Keep vote counts and "all voted" state in sync for every user
			// in active voting phases, even if websocket vote updates are missed.
			consensusVotesSyncTimer = setInterval(() => {
				if (isConsensusVoteSyncing) {
					return;
				}

				isConsensusVoteSyncing = true;
				fetch_votes_and_confirms().finally(() => {
					isConsensusVoteSyncing = false;
				});
			}, 2000);
		}

		return () => {
			if (consensusVotesSyncTimer) {
				clearInterval(consensusVotesSyncTimer);
				consensusVotesSyncTimer = null;
			}
			isConsensusVoteSyncing = false;
		};
	});

	$effect(() => {
		const shouldPollForNextIteration = isConsensusPhase;

		if (!shouldPollForNextIteration) {
			if (waitingRefreshTimer) {
				clearInterval(waitingRefreshTimer);
				waitingRefreshTimer = null;
			}
			isConsensusIterationSyncing = false;
			return;
		}

		if (!waitingRefreshTimer) {
			// Keep iteration header and phase in sync for every user during
			// consensus, even if websocket updates are delayed or missed.
			waitingRefreshTimer = setInterval(() => {
				if (isConsensusIterationSyncing) {
					return;
				}

				isConsensusIterationSyncing = true;
				fetch_score_bands().finally(() => {
					isConsensusIterationSyncing = false;
				});
			}, 3000);
		}

		return () => {
			if (waitingRefreshTimer) {
				clearInterval(waitingRefreshTimer);
				waitingRefreshTimer = null;
			}
			isConsensusIterationSyncing = false;
		};
	});

	onMount(async () => {
		// Initialize WebSocket connection
		if (data.group) {
			console.log('Initializing WebSocket for group:', data.group.id);
			wsService = new WebSocketService(data.group.id, 'gdm-score-bands', data.refreshToken, () => {
				// This runs when connection is re-established after disconnection
				console.log('WebSocket reconnected, refreshing gdm-score-bands state...');
				// TODO: Would be nice to have a pop up message to user: 'Reconnected to server'. At least exists in GNIMBUS.
				fetch_score_bands();
				fetch_votes_and_confirms(true);
			});

			// Subscribe to websocket messages
			wsService.messageStore.subscribe((store) => {
				// Handle different message types from the backend:
				const msg =
					typeof store.message === 'string'
						? store.message
						: JSON.stringify(store.message);
				console.log('WebSocket message received:', msg);

				// Handle update messages (messages don't show to user, just trigger state updates)
				if (msg.includes('UPDATE: A vote has been cast.')) {
					fetch_votes_and_confirms();
					return;
				} else if (msg.includes('UPDATE')) {
					fetch_score_bands();
					fetch_votes_and_confirms(true);
					clusters_to_visible();
					return;
				}

				// Handle error messages (show error message)
				if (msg.includes('ERROR')) {
					const errMsg = msg.replace(/ERROR: /gi, '');
					errorMessage.set(`${errMsg}`);
					return;
				}
			});
		}

		await fetch_score_bands();
		await fetch_votes_and_confirms(true);

		clusters_to_visible();
	});

	// Cleanup websocket connection when component is destroyed
	onDestroy(() => {
		if (consensusVotesSyncTimer) {
			clearInterval(consensusVotesSyncTimer);
			consensusVotesSyncTimer = null;
		}
		isConsensusVoteSyncing = false;

		if (waitingRefreshTimer) {
			clearInterval(waitingRefreshTimer);
			waitingRefreshTimer = null;
		}
		isConsensusIterationSyncing = false;

		if (wsService) {
			console.log('Closing WebSocket connection');
			wsService.close();
			wsService = null;
		}
	});

	/**
	 * Fetches current SCORE bands data and history from backend
	 */
	async function fetch_score_bands() {
		try {
			const previousIterationId = iteration_id;
			const previousPhase = phase;

			const scoreResponse = await fetch('/interactive_methods/GDM-SCORE-bands/fetch_score_bands', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					group_id: data.group.id,
					score_bands_config: scoreBandsConfig,
					from_iteration: iteration_id
				})
			});

			if (!scoreResponse.ok) {
				const errorData = await scoreResponse.json();
				throw new Error(
					`Fetch score failed: ${errorData.error || `HTTP ${scoreResponse.status}: ${scoreResponse.statusText}`}`
				);
			}

			const scoreResult = await scoreResponse.json();

			if (scoreResult.success) {
				history = scoreResult.data.history;
				console.log('Full history received:', history);

				// The last item from history is the current response
				const currentResponse = history[history.length - 1];
				// Check which type of response we got and update state accordingly
				if (currentResponse.method === 'gdm-score-bands') {
					// Regular SCORE bands response - cast to proper type for TypeScript
					const scoreBandsResponse =
						currentResponse as GDMSCOREBandsResponse;
					latestIteration = scoreBandsResponse.latest_iteration
						? scoreBandsResponse.latest_iteration
						: null;
					const scoreBandsData =
						scoreBandsResponse.result as SCOREBandsResult;
					scoreBandsResult = scoreBandsData;
					scoreBandsConfig = scoreBandsData.options;
					iteration_id = scoreBandsResponse.group_iter_id;
					phase = 'Consensus Reaching Phase';
					decisionResult = null;
					console.log('SCORE bands fetched successfully:', scoreBandsResponse);
				} else if (currentResponse.method === 'gdm-score-bands-final') {
					// Decision phase response
					const finalDecisionData =
						currentResponse.result as GDMSCOREBandFinalSelection;
					latestIteration = null;
					decisionResult = finalDecisionData;
					iteration_id = currentResponse.group_iter_id;
					phase = 'Decision Phase';
					scoreBandsResult = null;
					console.log('Decision phase data fetched successfully:', currentResponse);
				} else {
					throw new Error(`Unknown method: ${currentResponse.method}`);
				}

				const iterationChanged = iteration_id !== previousIterationId;
				const phaseChanged = phase !== previousPhase;

				if (iterationChanged || phaseChanged) {
					selected_band = null;
					selected_solution = null;
				}
			} else {
				throw new Error(`Fetch score failed: ${scoreResult.error || 'Unknown error'}`);
			}
			data_loaded = true;
			loading_error = null;
		} catch (error) {
			console.error('Error in fetch_score_bands:', error);
			errorMessage.set(`${error}`);
		}
	}

	/**
	 * Submits user vote for selected band or solution
	 */
	async function vote(selection: number | null) {
		if (selection === null) {
			errorMessage.set('Please select a band or solution to vote for.');
			return;
		}
		console.log('Selection to vote for:', selection);
		try {
			const voteResponse = await fetch('/interactive_methods/GDM-SCORE-bands/vote', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					group_id: data.group.id,
					vote: selection
				})
			});

			if (!voteResponse.ok) {
				const errorData = await voteResponse.json();
				throw new Error(
					`Vote failed: ${errorData.error || `HTTP ${voteResponse.status}: ${voteResponse.statusText}`}`
				);
			}

			const voteResult = await voteResponse.json();

			if (voteResult.success) {
				console.log('Voted successfully:', voteResult.data.message);
				// Refresh local voting state immediately so vote counters update without
				// waiting for a websocket update event.
				await fetch_votes_and_confirms();
			} else {
				throw new Error(`Vote failed: ${voteResult.error || 'Unknown error'}`);
			}
		} catch (error) {
			console.error('Error in vote:', error);
			errorMessage.set(`${error}`);
		}
	}

	/**
	 * Confirms user's current vote to proceed to next phase
	 */
	async function confirm_vote() {
		if (vote_confirmed) {
			return;
		}
		try {
			const confirmResponse = await fetch('/interactive_methods/GDM-SCORE-bands/confirm_vote', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					group_id: data.group.id
				})
			});

			if (!confirmResponse.ok) {
				const errorData = await confirmResponse.json();
				throw new Error(
					`Confirm failed: ${errorData.error || `HTTP ${confirmResponse.status}: ${confirmResponse.statusText}`}`
				);
			}

			const confirmResult = await confirmResponse.json();

			if (confirmResult.success) {
				console.log('Confirmed vote successfully:', confirmResult.data.message);
			} else {
				throw new Error(`Confirm failed: ${confirmResult.error || 'Unknown error'}`);
			}
			// Refresh both vote status and iteration state locally so the UI updates
			// immediately even if websocket update delivery is delayed.
			await fetch_votes_and_confirms();
			await fetch_score_bands();
			clusters_to_visible();
		} catch (error) {
			console.error('Error in Confirm:', error);
			errorMessage.set(`${error}`);
		}
	}

	/**
	 * Fetches voting status and confirmations for all group members
	 */
	async function fetch_votes_and_confirms(selectVotedBand = false) {
		try {
			const response = await fetch('/interactive_methods/GDM-SCORE-bands/get_votes_and_confirms', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					group_id: data.group.id
				})
			});

			if (!response.ok) {
				const errorData = await response.json();
				throw new Error(
					`Get votes and confirms failed: ${errorData.error || `HTTP ${response.status}: ${response.statusText}`}`
				);
			}

			const result = await response.json();
			if (result.success) {
				votes_and_confirms = result.data;
				// If user has voted already, select the band they voted for
				// selectVotedBand parameter controls whether to update selected_band: updates happen in different situations, some should not change selected_band
				if (userId && votes_and_confirms.votes.hasOwnProperty(userId) && selectVotedBand) {
					selected_band = votes_and_confirms.votes[userId];
				}
			} else {
				throw new Error(`Get votes and confirms failed: ${result.error || 'Unknown error'}`);
			}
		} catch (error) {
			console.error('Error in get_votes_and_confirms:', error);
			errorMessage.set(`${error}`);
		}
	}

	/**
	 * Reverts group to specified iteration (owner only)
	 */
	async function revert_to(iteration: number) {
		try {
			const response = await fetch('/interactive_methods/GDM-SCORE-bands/revert', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					group_id: data.group.id,
					iteration_number: iteration
				})
			});

			if (!response.ok) {
				const errorData = await response.json();
				throw new Error(
					`Revert iteration failed: ${errorData.error || `HTTP ${response.status}: ${response.statusText}`}`
				);
			}

			const result = await response.json();
			if (result.success) {
				console.log('Reverted to previous iteration successfully:', result.data.message);
				// Refresh score bands and votes after reverting
				await fetch_score_bands();
				await fetch_votes_and_confirms();
				clusters_to_visible();
			} else {
				throw new Error(`Revert iteration failed: ${result.error || 'Unknown error'}`);
			}
		} catch (error) {
			console.error('Error in revert_iteration:', error);
			errorMessage.set(`${error}`);
		}
	}

	/**
	 * Updates SCORE bands configuration and recalculates bands (owner only)
	 */
	async function configure(config: SCOREBandsGDMConfig) {
		try {
			const configureResponse = await fetch('/interactive_methods/GDM-SCORE-bands/configure', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					// Group ID for which to apply the configuration
					group_id: data.group.id,
					// Configuration object with all SCORE bands settings
					config: config
				})
			});

			if (!configureResponse.ok) {
				const errorData = await configureResponse.json();
				throw new Error(
					`Configure failed: ${errorData.error || `HTTP ${configureResponse.status}: ${configureResponse.statusText}`}`
				);
			}

			const configureResult = await configureResponse.json();

			if (configureResult.success) {
				console.log('Configuration updated successfully:', configureResult.data.message);
				console.log('config: ', config);
			} else {
				throw new Error(`Configure failed: ${configureResult.error || 'Unknown error'}`);
			}
		} catch (error) {
			console.error('Error in configure:', error);
			errorMessage.set(`${error}`);
		}
	}
</script>

<svelte:head>
	<title>GDM-SCORE-bands | DESDEO</title>
	<meta name="description" content="Group decision making interface using Score-band method" />
</svelte:head>

<div class="container mx-auto p-6">
	{#if $errorMessage}
		<Alert title="Error" message={$errorMessage} variant="destructive" />
	{/if}

	{#if !data_loaded}
		<div class="flex h-96 items-center justify-center">
			<div class="text-center">
				<div class="loading loading-spinner loading-lg"></div>
				<p class="mt-4">Loading data...</p>
				{#if loading_error}
					<p class="text-error mt-2">Error: {loading_error}</p>
				{/if}
			</div>
		</div>
	{:else}
		<!-- Header and Instructions -->
		<div class="card bg-base-100 mb-6 shadow-xl">
			<div class="card-body">
				<div class="">
					<!-- Header Section -->
					<div class="font-semibold">
						Group SCORE Bands / {phase}, Iteration {iteration_id}
					</div>
					{#if isDecisionMaker}
						<!-- Instructions Section -->
						{#if isConsensusPhase && usersVote === null}
							<div>
								Click a cluster on the graph and vote with the button. When all votes are received,
								you can continue by confirming your vote.
							</div>
						{:else if isDecisionPhase && usersVote === null && !isGroupDecisionReached}
							<div>Select the best solution from the solutions shown below and vote for it.</div>
						{/if}
						{#if isDecisionPhase && isGroupDecisionReached}
							<div>
								The group decision process is complete! The final solution selected is Solution {winnerSolutionIndex !==
								null
									? winnerSolutionIndex + 1
									: 'N/A'}.
							</div>
						{:else}
							{#if usersVote !== null && !have_all_voted}
								<div>
									You have voted for {isConsensusPhase ? 'band' : 'solution'}
									{isConsensusPhase ? usersVote : usersVote + 1}. You can still change your vote. To
									confirm your vote, please wait for other users to vote.
								</div>
							{/if}
							{#if usersVote !== null && have_all_voted && !vote_confirmed}
								<div>
									You have voted for {isConsensusPhase ? 'band' : 'solution'}
									{isConsensusPhase ? usersVote : usersVote + 1}. You can still change your vote, or
									confirm your vote to proceed.
								</div>
							{/if}
							{#if usersVote !== null && vote_confirmed}
								<div>
									You have confirmed your vote for {isConsensusPhase ? 'band' : 'solution'}
									{isConsensusPhase ? usersVote : usersVote + 1}. Please wait for other users to
									confirm their votes.
								</div>
							{/if}
						{/if}
					{/if}
					{#if isOwner}
						<div class="mt-2 text-sm text-gray-600">
							You can revert to a previous iteration using the History Browser.
							{isConsensusPhase
								? 'You can also adjust the SCORE Bands parameters and recalculate the bands below.'
								: ''}
						</div>
					{/if}
				</div>
			</div>
		</div>

		{#if isLearningPhase}
	<div class="grid grid-cols-1 gap-4 xl:grid-cols-[280px_minmax(0,1fr)_340px]">
		<aside class="space-y-4">
			<div class="rounded-lg border bg-card shadow-sm">
				<div class="border-b px-4 py-3">
					<h2 class="text-sm font-semibold">How to explore</h2>
				</div>

				<div class="space-y-4 p-4 text-sm">
					<div>
						<div class="font-medium">1. Explore bands</div>
						<p class="text-muted-foreground">Click a band to inspect it.</p>
					</div>

					<div>
						<div class="font-medium">2. Save preferences</div>
						<p class="text-muted-foreground">Bookmark interesting bands privately.</p>
					</div>

					<div>
						<div class="font-medium">3. Explore inside a band</div>
						<p class="text-muted-foreground">Zoom in and optionally create personal sub-bands.</p>
					</div>
				</div>
			</div>

			<div class="rounded-lg border bg-card shadow-sm">
				<div class="border-b px-4 py-3">
					<h2 class="text-sm font-semibold">Filters</h2>
				</div>

				<div class="space-y-3 p-4">
					<div class="text-sm font-medium">Visible clusters</div>

					{#each SCOREBands.clusterIds as clusterId}
						<label class="flex items-center justify-between gap-2 text-sm">
							<span class="flex items-center gap-2">
								<span
									class="h-3 w-3 rounded-full"
									style={`background-color: ${cluster_colors[clusterId] || '#64748b'};`}
								></span>
								Cluster {clusterId}
							</span>

							<input
								type="checkbox"
								bind:checked={cluster_visibility_map[clusterId]}
								class="checkbox checkbox-primary checkbox-sm"
							/>
						</label>
					{/each}
				</div>
			</div>
		</aside>

		<main class="space-y-4">
			<div class="rounded-lg border bg-card shadow-sm">
				<div class="flex items-center justify-between border-b px-4 py-3">
					<div>
						<h2 class="text-sm font-semibold">Explore the solution space</h2>
						<p class="mt-1 text-xs text-muted-foreground">
							Your exploration is private and does not affect the group.
						</p>
					</div>
				</div>

				<div class="h-[520px] p-4">
					<ScoreBands
						data={SCOREBands.data}
						axisNames={SCOREBands.axisNames}
						axisPositions={SCOREBands.axisPositions}
						axisSigns={SCOREBands.axisSigns}
						groups={SCOREBands.clusterIds}
						{options}
						bands={SCOREBands.bands}
						medians={SCOREBands.medians}
						scales={SCOREBands.scales}
						clusterVisibility={cluster_visibility_map}
						clusterColors={cluster_colors}
						axisOptions={axis_options}
						axisOrder={effective_axis_order}
						onBandSelect={selectLearningBand}
						onAxisSelect={handle_axis_select}
						selectedBand={learningState.selectedBand}
						selectedAxis={selected_axis}
					/>
				</div>
			</div>

			<ClusterBandTable
				axisNames={SCOREBands.axisNames}
				bands={clusterBandRows}
				selectedBand={learningState.selectedBand}
				onBandSelect={selectLearningBand}
			/>
		</main>

		<aside class="space-y-4">
			<div class="rounded-lg border bg-card shadow-sm">
				<div class="border-b px-4 py-3">
					<h2 class="text-sm font-semibold">My exploration</h2>
					<p class="mt-1 text-xs text-muted-foreground">Visible only to you.</p>
				</div>

				<div class="space-y-3 p-4">
					{#if learningState.selectedBand !== null}
						<div class="rounded-md border p-3 text-sm">
							<div class="font-medium">Cluster {learningState.selectedBand}</div>
							<div class="text-muted-foreground">
								{SCOREBands.solutions_per_cluster[learningState.selectedBand] ?? 0} solutions
							</div>
						</div>

						<Button
							class="w-full"
							onclick={() => toggleSavedBand(learningState.selectedBand!)}
						>
							{learningState.savedBands.includes(learningState.selectedBand)
								? 'Remove saved band'
								: 'Save band'}
						</Button>

						<Button
							class="w-full"
							variant="outline"
							onclick={() => toggleCompareBand(learningState.selectedBand!)}
						>
							Compare band ({learningState.comparedBands.length}/3)
						</Button>

						<Button
							class="w-full"
							variant="outline"
							onclick={() => zoomIntoBand(learningState.selectedBand!)}
						>
							Explore inside band
						</Button>
					{:else}
						<p class="text-sm text-muted-foreground">
							Select a band to save, compare, or explore it.
						</p>
					{/if}
				</div>
			</div>

			{#if learningState.savedBands.length > 0}
				<div class="rounded-lg border bg-card shadow-sm">
					<div class="border-b px-4 py-3">
						<h2 class="text-sm font-semibold">Saved bands</h2>
					</div>

					<div class="space-y-2 p-4">
						{#each learningState.savedBands as clusterId}
							<div class="flex items-center justify-between rounded-md border px-3 py-2 text-sm">
								<span>Cluster {clusterId}</span>
								<button
									type="button"
									class="text-muted-foreground hover:text-foreground"
									onclick={() => toggleSavedBand(clusterId)}
								>
									Remove
								</button>
							</div>
						{/each}
					</div>
				</div>
			{/if}

			{#if learningState.zoomedBand !== null}
				<div class="rounded-lg border bg-card shadow-sm">
					<div class="border-b px-4 py-3">
						<h2 class="text-sm font-semibold">
							Explore inside Cluster {learningState.zoomedBand}
						</h2>
						<p class="mt-1 text-xs text-muted-foreground">
							Private zoomed-in exploration.
						</p>
					</div>

					<div class="space-y-3 p-4">
						<Button class="w-full" onclick={() => createPersonalSubBands(3)}>
							Create personal sub-bands
						</Button>

						{#each learningState.subBands as subBand}
							<div class="rounded-md border p-3 text-sm">
								<div class="font-medium">{subBand.label}</div>
								<div class="text-muted-foreground">
									{subBand.solutionIndices.length} solutions
								</div>
							</div>
						{/each}

						<Button class="w-full" variant="outline" onclick={exitBandZoom}>
							Back to all bands
						</Button>
					</div>
				</div>
			{/if}

			<div class="rounded-lg border bg-card shadow-sm">
				<div class="border-b px-4 py-3">
					<h2 class="text-sm font-semibold">What’s next?</h2>
				</div>

				<div class="space-y-3 p-4 text-sm text-muted-foreground">
					<p>
						Once you are familiar with the solution space, you will move to the consensus
						phase and vote for a preferred band.
					</p>

					{#if isOwner}
						<Button class="w-full">
							Continue to consensus phase
						</Button>
					{/if}
				</div>
			</div>
		</aside>
	</div>
		{:else if isConsensusPhase}
	<div class="grid grid-cols-1 gap-4 xl:grid-cols-[300px_minmax(0,1fr)_360px]">
		<!-- LEFT: Data & Settings -->
		<aside class="space-y-4">
			<div class="rounded-lg border bg-card shadow-sm">
				<div class="flex items-center justify-between border-b px-4 py-3">
					<h2 class="text-sm font-semibold">Data & Settings</h2>
				</div>

				<div class="space-y-4 p-4">
					<div>
						<div class="text-xs text-muted-foreground">Input data</div>
						<div class="mt-1 text-sm font-medium">
							{data.problem.name ?? 'Current problem'}
						</div>
					</div>

					<div class="space-y-2">
						<div class="text-sm font-medium">Visualization options</div>

						<label class="flex items-center gap-2 text-sm">
							<input
								type="checkbox"
								bind:checked={show_bands}
								disabled={!canToggleBands()}
								class="checkbox checkbox-primary checkbox-sm"
							/>
							Show bands
						</label>

						<label class="flex items-center gap-2 text-sm">
							<input
								type="checkbox"
								bind:checked={show_medians}
								disabled={!canToggleMedians()}
								class="checkbox checkbox-primary checkbox-sm"
							/>
							Show medians
						</label>
					</div>

					<div class="space-y-2">
						<div class="text-sm font-medium">Visible clusters</div>

						{#each SCOREBands.clusterIds as clusterId}
							<label class="flex items-center justify-between gap-2 text-sm">
								<span class="flex items-center gap-2">
									<span
										class="h-3 w-3 rounded-full"
										style={`background-color: ${cluster_colors[clusterId] || '#64748b'};`}
									></span>
									Cluster {clusterId}
								</span>

								<input
									type="checkbox"
									bind:checked={cluster_visibility_map[clusterId]}
									class="checkbox checkbox-primary checkbox-sm"
								/>
							</label>
						{/each}
					</div>
				</div>
			</div>

			<ConfigPanel
				currentConfig={scoreBandsResult?.options || null}
				{latestIteration}
				{totalVoters}
				onRecalculate={configure}
				isVisible={isOwner && isConsensusPhase}
			/>

			<HistoryBrowser
				{history}
				currentIterationId={iteration_id}
				onRevertToIteration={revert_to}
				{isOwner}
			/>
		</aside>

		<!-- CENTER: Visualization + band table -->
		<main class="space-y-4">
			<div class="rounded-lg border bg-card shadow-sm">
				<div class="flex items-center justify-between border-b px-4 py-3">
					<div>
						<h2 class="text-sm font-semibold">Visualization</h2>
						<p class="mt-1 text-xs text-muted-foreground">
							Select a band in the chart or in the table below.
						</p>
					</div>
				</div>

				<div class="h-[520px] p-4">
					<ScoreBands
						data={SCOREBands.data}
						axisNames={SCOREBands.axisNames}
						axisPositions={SCOREBands.axisPositions}
						axisSigns={SCOREBands.axisSigns}
						groups={SCOREBands.clusterIds}
						{options}
						bands={SCOREBands.bands}
						medians={SCOREBands.medians}
						scales={SCOREBands.scales}
						clusterVisibility={cluster_visibility_map}
						clusterColors={cluster_colors}
						axisOptions={axis_options}
						axisOrder={effective_axis_order}
						onBandSelect={handle_band_select}
						onAxisSelect={handle_axis_select}
						selectedBand={selected_band}
						selectedAxis={selected_axis}
					/>
				</div>

				<div class="border-t px-4 py-3 text-sm text-muted-foreground">
					Bands show the regions of the Pareto front still available after the previous
					iteration.
				</div>
			</div>

			<ClusterBandTable
				axisNames={SCOREBands.axisNames}
				bands={clusterBandRows}
				selectedBand={selected_band}
				onBandSelect={handle_band_select}
			/>
		</main>

		<!-- RIGHT: Voting + consensus -->
		<aside class="space-y-4">
			<div class="rounded-lg border bg-card shadow-sm">
				<div class="border-b px-4 py-3">
					<h2 class="text-sm font-semibold">Group voting</h2>
					<p class="mt-1 text-xs text-muted-foreground">
						{totalVoters} decision makers
					</p>
					{#if isConsensusPhase}
						<p class="mt-1 text-xs text-muted-foreground">
							Vote sync: {isConsensusVoteSyncing ? 'updating...' : 'live'}
						</p>
					{/if}
				</div>

				<div class="space-y-2 p-4">
					<div class="text-sm font-medium">Select your preferred band</div>

					{#each SCOREBands.clusterIds as clusterId}
						<button
							type="button"
							class="flex w-full items-center justify-between rounded-md border px-3 py-3 text-left text-sm hover:bg-muted
								{selected_band === clusterId ? 'border-primary bg-muted' : ''}"
							onclick={() => handle_band_select(clusterId)}
							disabled={vote_confirmed}
						>
							<span class="flex items-center gap-2">
								<span
									class="h-3 w-3 rounded-full"
									style={`background-color: ${cluster_colors[clusterId] || '#64748b'};`}
								></span>
								Cluster {clusterId}
							</span>

							<span class="text-muted-foreground">
								{getClusterVoteCount(clusterId)} / {totalVoters}
								({getClusterVotePercent(clusterId)}%)
							</span>
						</button>
					{/each}

					{#if isDecisionMaker}
						<div class="pt-4">
							<Button
								class="w-full"
								onclick={() => vote(selected_band)}
								disabled={selected_band === null || vote_confirmed}
							>
								Vote
							</Button>

							<Button
								class="mt-2 w-full"
								variant="outline"
								onclick={confirm_vote}
								disabled={!have_all_voted || vote_confirmed}
							>
								Confirm vote
							</Button>
						</div>
					{/if}
				</div>
			</div>

			<div class="rounded-lg border bg-card shadow-sm">
				<div class="flex items-center justify-between border-b px-4 py-3">
					<h2 class="text-sm font-semibold">Consensus status</h2>
					<span class="text-xs text-muted-foreground">Updates after all votes</span>
				</div>

				<div class="divide-y">
					{#each SCOREBands.axisNames as axisName}
						<div class="flex items-center justify-between px-4 py-3">
							<div>
								<div class="font-medium">{axisName}</div>
								<div class={`text-sm ${getConsensusClasses(axisName)}`}>
									{getConsensusLabel(axisName)}
								</div>
							</div>

							<div
								class="h-2 w-24 rounded-full bg-muted"
								title={getConsensusLabel(axisName)}
							>
								<div
									class="h-2 rounded-full
										{axis_agreement?.[axisName] === 'agreement'
											? 'bg-green-600'
											: axis_agreement?.[axisName] === 'disagreement'
												? 'bg-red-600'
												: 'bg-muted-foreground/40'}"
									style="width: {axis_agreement?.[axisName] === 'neutral' ? 40 : 80}%"
								></div>
							</div>
						</div>
					{/each}
				</div>
			</div>
		</aside>
	</div>
		{:else if isDecisionPhase}
			<!-- DECISION PHASE: Solution Selection Content -->
			<div class="grid grid-cols-1 gap-6 lg:grid-cols-4">
				<!-- Decision Controls -->
				<div class="lg:col-span-1">
					{#if isDecisionMaker}
						<!-- Voting -->
						<div class="card bg-base-100 shadow-xl">
							<div class="card-body">
								<h2 class="card-title">
									{isGroupDecisionReached ? 'Final Solution' : 'Solution Voting'}
								</h2>
								<div class="space-y-2 p-2">
									{#if !isGroupDecisionReached}
										<Button
											onclick={() => vote(selected_solution)}
											disabled={selected_solution === null || vote_confirmed}
										>
											Vote for Selected Solution
										</Button>
										<Button onclick={confirm_vote} disabled={!have_all_voted || vote_confirmed}>
											Confirm Final Decision
										</Button>
										{#if vote_confirmed}
											<div class="alert alert-info">
												<span>Decision Confirmed!</span>
											</div>
										{/if}
									{:else}
										<div class="alert alert-success">
											<span>Group decision reached!</span>
											<div class="mt-2 text-sm">
												Final solution: Solution {winnerSolutionIndex !== null
													? winnerSolutionIndex + 1
													: 'N/A'}
											</div>
										</div>
									{/if}
								</div>
							</div>
						</div>
					{:else if isOwner}
						<!-- Voting status for owner -->
						<div class="card bg-base-100 shadow-xl">
							<div class="card-body">
								<h2 class="card-title">
									{isGroupDecisionReached ? 'Final Solution' : 'Solution Voting'}
								</h2>
								<div class="space-y-2 p-2">
									{#if !isGroupDecisionReached}
										<div>Voting still ongoing or decision not found with these votes.</div>
									{:else}
										<div class="alert alert-success">
											<span>Group decision reached!</span>
											<div class="mt-2 text-sm">
												Final solution: Solution {winnerSolutionIndex !== null
													? winnerSolutionIndex + 1
													: 'N/A'}
											</div>
										</div>
									{/if}
								</div>
							</div>
						</div>
					{/if}

					<!-- History Browser Component -->
					<HistoryBrowser
						{history}
						currentIterationId={iteration_id}
						onRevertToIteration={revert_to}
						{isOwner}
					/>
				</div>
				<!-- Visualization Area -->
				<div class="lg:col-span-3">
					<div class="card bg-base-100 shadow-xl">
						<div class="card-body">
							{#if decisionResult && decisionSolutions.length > 0}
								<div class="flex h-[600px] w-full items-center justify-center">
									<!-- Parallel Coordinates Component -->
									<ParallelCoordinates
										data={decisionSolutions}
										dimensions={createObjectiveDimensions(data.problem)}
										selectedIndex={selected_solution}
										onLineSelect={handle_solution_select}
										referenceData={{
											preferredSolutions:
												usersVote !== null
													? [
															{
																values: decisionSolutions[usersVote],
																label: `Your Vote: Solution ${usersVote + 1}`
															}
														]
													: []
										}}
									/>
								</div>
								<h2 class="card-title mb-4">Numerical values</h2>
								<ScoreBandsSolutionTable
									problem={data.problem}
									solutions={decisionSolutions}
									selectedSolution={selected_solution}
									onSolutionSelect={handle_solution_select}
									userVotedSolution={usersVote}
									groupVotes={votes_and_confirms.votes || {}}
								/>
							{:else}
								<div class="text-center">
									<h2 class="mb-4 text-2xl font-bold">Decision Phase</h2>
									<p class="mb-4 text-gray-600">Loading solutions...</p>
								</div>
							{/if}
						</div>
					</div>
				</div>
			</div>
		{:else}
			<!-- FALLBACK: Unknown phase -->
			<div class="alert alert-error">
				<span>Unknown phase: {phase}</span>
			</div>
		{/if}
	{/if}
</div>

<style>
	:global(.container) {
		max-width: 100%;
	}
</style>
