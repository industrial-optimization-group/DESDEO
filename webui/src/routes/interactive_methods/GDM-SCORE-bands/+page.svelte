<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import ScoreBands from '$lib/components/visualizations/score-bands/score-bands.svelte';
	import ParallelCoordinates from '$lib/components/visualizations/parallel-coordinates/parallel-coordinates.svelte';
	import ScoreBandsSolutionTable from './score-bands-solution-table.svelte';
	import HistoryBrowser from './history-browser.svelte';
	import ConfigPanel from './config-panel.svelte';
	import { onMount, onDestroy } from 'svelte';
	import type { components } from "$lib/api/client-types";
	import { auth } from '../../../stores/auth';
	import { errorMessage } from '../../../stores/uiState';
	import Alert from '$lib/components/custom/notifications/alert.svelte';
		import {
		createObjectiveDimensions
	} from '$lib/helpers/visualization-data-transform';

	import { WebSocketService } from './websocket-store';

	import {
		drawVotesChart,
		calculateAxisAgreement,
		generate_axis_options,
		generate_cluster_colors,
		calculateScales
	} from './helper-functions';
	import { json } from 'd3';
	
	const { data } = $props<{ 
		data: { 
			refreshToken: string;
			group: components['schemas']['GroupPublic'];
			problem: components['schemas']['ProblemInfo'];
		} 
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
	const totalVoters = data.group.user_ids.length;
	let have_all_voted = $derived.by(()=> {
		return totalVoters === Object.keys(votes_and_confirms.votes || {}).length;
	})

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
				0.9  // disagreement threshold
			);
		}
		
		return {}; // Return empty object when conditions aren't met
	});

	// Iteration info: history, current iteration, phase, etc.
	let history: (components["schemas"]["GDMSCOREBandsResponse"] | components["schemas"]["GDMSCOREBandsDecisionResponse"])[] = $state([]);
	let phase = $state('Consensus Reaching Phase'); // 'Consensus reaching phase' or 'Decision phase'
	let iteration_id = $state(0); // for header and fetch_score_bands
	// current iteration data for consensus reaching phase, when bands exist
	let scoreBandsResult: components['schemas']['SCOREBandsResult'] | null = $state(null);
	
	// Configuration and latestIteration are used in initialization and configPanel
	let latestIteration: number | null = $state(null);
	let scoreBandsConfig: components["schemas"]["SCOREBandsConfig"] = $state({
			clustering_algorithm: {
				name: 'KMeans',
				n_clusters: 5
			},
			distance_formula: 1,
			distance_parameter: 0.05,
			use_absolute_correlations: false,
			include_solutions: false,
			include_medians: true,
			interval_size: 0.25,
		});
	// Current iteration data for decision phase, when solutions exist and not bands
	let decisionResult: components['schemas']['GDMSCOREBandFinalSelection'] | null = $state(null);
	
	// Derived state to determine which phase we're in, for conditional component rendering
	let isDecisionPhase = $derived(phase === 'Decision Phase');
	let isConsensusPhase = $derived(phase === 'Consensus Reaching Phase');
	
	// Data from scoreBandsResult stored in format that is actually used in UI
	let SCOREBands = $derived.by(()=> {
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
				solutions_per_cluster: {} as Record<string, number>,
			};
		}
		
		const derivedData = {
			axisNames: scoreBandsResult.ordered_dimensions,
			clusterIds: Object.keys(scoreBandsResult.bands).sort((a, b) => parseInt(a) - parseInt(b)).map(id => Number(id)),
			// Convert axis_positions dict to ordered array
			axisPositions: scoreBandsResult.ordered_dimensions.map(
				objName => scoreBandsResult?.axis_positions[objName]
			) as number[],
			
			// TODO: Visualization used axisSigns, but is the info from backend or user in UI? "Flip axes" -checkbox?
			axisSigns: new Array(scoreBandsResult.ordered_dimensions.length).fill(1),
			data: [], // TODO: This could be filled with solution data, if it will be a thing later. Visualization might not work: copied, not tested.
			bands: scoreBandsResult.bands, 
			medians: scoreBandsResult.medians,
			scales: calculateScales(data.problem, scoreBandsResult), // TODO: see calculateScales function
			solutions_per_cluster: scoreBandsResult.cardinalities
		};
		return derivedData;
	})

	// Visualization options with checkboxes
	let show_bands = $state(true);
	let show_solutions = $state(false); // Disabled and hidden for now - no individual solutions
	let show_medians = $state(false); // Hide medians by default


	// Helper functions to prevent deselecting all visualization options
	function canToggleBands() {
		// Can toggle bands off only if medians would remain on
		return !show_bands || (show_medians || show_solutions);
	}

	function canToggleMedians() {
		// Can toggle medians off only if bands would remain on
		return !show_medians || (show_bands || show_solutions);
	}


	// options for drawing score bands
	let options = $derived.by(()=>{
		return {
		bands: show_bands,
		solutions: show_solutions,
		medians: show_medians,
	}});

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
	$effect(()=>{
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
	let cluster_colors = $derived(SCOREBands.clusterIds.length > 0 ? generate_cluster_colors(SCOREBands.clusterIds) : {});
	let axis_options = $derived(SCOREBands.axisNames.length > 0 ? generate_axis_options(SCOREBands.axisNames, axis_agreement) : []);

	// Selection state
	let selected_band: number | null = $state(null);
	let selected_axis: number | null = $state(null); // not used, axis selection commented out
	let selected_solution: number | null = $state(null); // for decision phase

	// Selection handlers
	function handle_band_select(clusterId: number | null) {
		selected_band = clusterId;
	}

	function handle_axis_select(axisIndex: number | null) {
		// TODO: Waiting until there is need to select an axis
		// selected_axis = axisIndex;
	}

	function handle_solution_select(index: number | null) {
		selected_solution = index;
	}

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

	// Update votes chart when votes change
	$effect(() => {
		if (votesChartContainer) {
			drawVotesChart(
				votesChartContainer,
				votes_per_cluster,
				totalVoters,
				cluster_colors
			);
		}
	});

	onMount(async () => {
		// Initialize WebSocket connection
		if (data.group) {
			console.log('Initializing WebSocket for group:', data.group.id);
			wsService = new WebSocketService(
				data.group.id, 
				'gdm-score-bands', 
				data.refreshToken, 
				() => {
					// This runs when connection is re-established after disconnection
					console.log('WebSocket reconnected, refreshing gdm-score-bands state...');
					// TODO: Pop up message to user: 'Reconnected to server'. At least exists in GNIMBUS.
					fetch_score_bands();
					fetch_votes_and_confirms(true);
				}
			);
			
			// Subscribe to websocket messages
			wsService.messageStore.subscribe((store) => {
				// Handle different message types from the backend:
				const msg = store.message;
				
				// Handle update messages (messages don't show to user, just trigger state updates)
				if (msg.includes('UPDATE: A vote has been cast.')) {
					fetch_votes_and_confirms();
					return;
				}
				
				else if (msg.includes('UPDATE')) {
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
		if (wsService) {
			console.log('Closing WebSocket connection');
			wsService.close();
			wsService = null;
		}
	});

	// TODO STINA: documentation text
	async function fetch_score_bands() {
		try {			
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
				throw new Error(`Fetch score failed: ${errorData.error || `HTTP ${scoreResponse.status}: ${scoreResponse.statusText}`}`);
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
					const scoreBandsResponse = currentResponse as components['schemas']['GDMSCOREBandsResponse'];
					latestIteration = scoreBandsResponse.latest_iteration ? scoreBandsResponse.latest_iteration : null;
					const scoreBandsData = scoreBandsResponse.result as components['schemas']['SCOREBandsResult'];
					scoreBandsResult = scoreBandsData;
					scoreBandsConfig = scoreBandsData.options;
					iteration_id = scoreBandsResponse.group_iter_id;
					phase = 'Consensus Reaching Phase';
					decisionResult = null;
					console.log('SCORE bands fetched successfully:', scoreBandsResponse);
				} else if (currentResponse.method === 'gdm-score-bands-final') {
					// Decision phase response
					const finalDecisionData = currentResponse.result as components['schemas']['GDMSCOREBandFinalSelection'];
					latestIteration = null;
					decisionResult = finalDecisionData;
					iteration_id = currentResponse.group_iter_id;
					phase = 'Decision Phase';
					scoreBandsResult = null;
					console.log('Decision phase data fetched successfully:', currentResponse);
				} else {
					throw new Error(`Unknown method: ${currentResponse.method}`);
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

	// TODO STINA: documentation text
	async function vote(selection: number | null) {
		if (selection === null) {
			errorMessage.set('Please select a band or solution to vote for.');
			return;
		}
		console.log("Selection to vote for:", selection);
		try {
			const voteResponse = await fetch('/interactive_methods/GDM-SCORE-bands/vote', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					group_id: data.group.id,
					vote: selection,
				})
			});

			if (!voteResponse.ok) {
				const errorData = await voteResponse.json();
				throw new Error(`Vote failed: ${errorData.error || `HTTP ${voteResponse.status}: ${voteResponse.statusText}`}`);
			}

			const voteResult = await voteResponse.json();
			
			if (voteResult.success) {
				console.log('Voted successfully:', voteResult.data.message);
			} else {
				throw new Error(`Vote failed: ${voteResult.error || 'Unknown error'}`);
			}
		} catch (error) {
			console.error('Error in vote:', error);
			errorMessage.set(`${error}`);
		}
	}

	// TODO STINA: documentation text
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
					group_id: data.group.id,
				})
			});

			if (!confirmResponse.ok) {
				const errorData = await confirmResponse.json();
				throw new Error(`Confirm failed: ${errorData.error || `HTTP ${confirmResponse.status}: ${confirmResponse.statusText}`}`);
			}

			const confirmResult = await confirmResponse.json();
			
			if (confirmResult.success) {
				console.log('Confirmed vote successfully:', confirmResult.data.message);
			} else {
				throw new Error(`Confirm failed: ${confirmResult.error || 'Unknown error'}`);
			}
			fetch_votes_and_confirms();
		} catch (error) {
			console.error('Error in Confirm:', error);
			errorMessage.set(`${error}`);
		}
	}

	// TODO STINA: documentation text
	async function fetch_votes_and_confirms(selectVotedBand = false) {
		try {
			const response = await fetch('/interactive_methods/GDM-SCORE-bands/get_votes_and_confirms', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					group_id: data.group.id,
				})
			});

			if (!response.ok) {
				const errorData = await response.json();
				throw new Error(`Get votes and confirms failed: ${errorData.error || `HTTP ${response.status}: ${response.statusText}`}`);
			}

			const result = await response.json();
			if (result.success) {
				votes_and_confirms = result.data;
				// If user has voted already, select the band they voted for
				// selectVotedBand parameter controls whether to update selected_band: updates happen in different situations, some should not change selected_band
				if (userId && votes_and_confirms.votes.hasOwnProperty(userId) && selectVotedBand) {
					selected_band = votes_and_confirms.votes[userId];
				} else {
					selected_band = null;
				}
			} else {
				throw new Error(`Get votes and confirms failed: ${result.error || 'Unknown error'}`);
			}
		} catch (error) {
			console.error('Error in get_votes_and_confirms:', error);
			errorMessage.set(`${error}`);
		}
	}

	// TODO STINA: documentation text
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
				throw new Error(`Revert iteration failed: ${errorData.error || `HTTP ${response.status}: ${response.statusText}`}`);
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

	// TODO STINA: documentation text
	async function configure(config: components['schemas']['SCOREBandsGDMConfig']) {
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
				throw new Error(`Configure failed: ${errorData.error || `HTTP ${configureResponse.status}: ${configureResponse.statusText}`}`);
			}

			const configureResult = await configureResponse.json();
			
			if (configureResult.success) {
				console.log('Configuration updated successfully:', configureResult.data.message);
				console.log("config: ", config);
			} else {
				throw new Error(`Configure failed: ${configureResult.error || 'Unknown error'}`);
			}
		} catch (error) {
			console.error('Error in configure:', error);
			errorMessage.set(`${error}`);
		}
	}
</script>

<div class="container mx-auto p-6">
	{#if $errorMessage}
		<Alert 
			title="Error"
			message={$errorMessage} 
			variant='destructive'
		/>
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
							<div>Click a cluster on the graph and vote with the button. When all votes are received, you can continue by confirming your vote.</div>
						{:else if isDecisionPhase && usersVote === null}
							<div>Select the best solution from the solutions shown below and vote for it.</div>
						{/if}
						{#if usersVote !== null && !have_all_voted}
							<div>
								You have voted for {isConsensusPhase ? "band" : "solution"} {usersVote}. You can still change your vote.
								To confirm your vote, please wait for other users to vote.
							</div>
						{/if}
						{#if have_all_voted && !vote_confirmed}
							<div>
								You have voted for {isConsensusPhase ? "band" : "solution"} {usersVote}. You can still change your vote, or confirm your vote to proceed.
							</div>
						{/if}
						{#if vote_confirmed}
							<div>
								You have confirmed your vote for {isConsensusPhase ? "band" : "solution"} {usersVote}. Please wait for other users to confirm their votes.
							</div>
						{/if}
					{/if}
					{#if isOwner}
						<div class="mt-2 text-sm text-gray-600">
							You can adjust the SCORE Bands parameters and recalculate the bands below.
							You can also revert to a previous iteration using the History Browser.
						</div>
					{/if}
				</div>
			</div>
		</div>

		<!-- Parameter Controls -->
		<ConfigPanel 
			currentConfig={scoreBandsResult?.options || null}
			{latestIteration}
			{totalVoters}
			onRecalculate={configure}
			isVisible={isOwner && isConsensusPhase}
		/>

		{#if isConsensusPhase}
		<!-- CONSENSUS PHASE: Existing SCORE Bands Content -->
		<div class="grid grid-cols-1 gap-6 lg:grid-cols-4">
			<!-- Controls Panel -->
			<div class="space-y-6 lg:col-span-1">
				<div class="card bg-base-100 shadow-xl">
					<div class="card-body">
						<h2 class="card-title">Visualization Options</h2>

						<!-- Display Options -->
						<div class="form-control">
							<label class="label cursor-pointer">
								<span class="label-text">Show Bands</span>
								<input
									type="checkbox"
									bind:checked={show_bands}
									disabled={!canToggleBands()}
									class="checkbox checkbox-primary"
									title={canToggleBands() ? "" : "At least one visualization option must remain active"}
								/>
							</label>
						</div>

						<!-- TODO: when solutions can be fetched from backend, uncomment this and fix related code -->
						<!-- <div class="form-control">
							<label class="label cursor-pointer">
								<span class="label-text text-gray-500">Show Solutions</span>
								<input
									type="checkbox"
									bind:checked={show_solutions}
									disabled={true}
									class="checkbox checkbox-primary"
									title="Individual solutions are not available"
								/>
							</label>
						</div> -->

						<div class="form-control">
							<label class="label cursor-pointer">
								<span class="label-text">Show Medians</span>
								<input
									type="checkbox"
									bind:checked={show_medians}
									disabled={!canToggleMedians()}
									class="checkbox checkbox-primary"
									title={canToggleMedians() ? "" : "At least one visualization option must remain active"}
								/>
							</label>
						</div>
					</div>
				</div>

				<!-- Cluster Visibility -->
				<div class="card bg-base-100 shadow-xl">
					<div class="card-body">
						<h2 class="card-title">Cluster Visibility</h2>

						{#each SCOREBands.clusterIds as clusterId}
							<div class="form-control">
								<label class="label cursor-pointer">
									<span class="label-text">
										<span
											class="inline-block h-4 w-4 rounded"
											style="background-color: {cluster_colors[clusterId] || '#000000'};"
										></span>
										Cluster {clusterId}
										{#if SCOREBands.solutions_per_cluster && SCOREBands.solutions_per_cluster[clusterId]}
											<span class="text-xs text-gray-500 ml-1">
												({SCOREBands.solutions_per_cluster[clusterId]} solutions)
											</span>
										{/if}
									</span>
									<input
										type="checkbox"
										bind:checked={cluster_visibility_map[clusterId]}
										class="checkbox checkbox-primary"
									/>
								</label>
							</div>
						{/each}

						{#if SCOREBands.clusterIds.length === 0}
							<p class="text-sm text-gray-500">No clusters available</p>
						{/if}
					</div>
				</div>

				<!-- Selection Info -->
				<div class="card bg-base-100 shadow-xl">
					<div class="card-body">
						<h2 class="card-title">Selection</h2>
						<div class="space-y-2">
							{#if selected_band !== null}
								<div class="alert alert-info">
									<span class="font-medium">Band {selected_band} selected</span>
								</div>
							{:else}
								<div class="text-sm text-gray-500">No band selected</div>
							{/if}
							<!-- TODO: when there is a need to select an axis, uncomment code below -->
							<!-- {#if selected_axis !== null}
								<div class="alert alert-warning">
									<span class="font-medium"
										>Axis "{SCOREBands.axisNames[selected_axis] || 'Unknown'}" selected</span
									>
								</div>
							{:else}
								<div class="text-sm text-gray-500">No axis selected</div>
							{/if} -->

							{#if selected_band === null && selected_axis === null}
								<div class="mt-2 text-xs text-gray-400">Click on bands to select them</div>
							{/if}
						</div>
					</div>
				</div>

				<!-- "Voting buttons" -->
				{#if isDecisionMaker}
					<div class="card bg-base-100 shadow-xl">
						<div class="card-body">
							<h2 class="card-title">Voting</h2>
							<div class="space-y-2 p-2">
								<Button onclick={() => vote(selected_band)} disabled={selected_band === null || vote_confirmed}>
									Vote
								</Button>
								<Button onclick={confirm_vote} disabled={!have_all_voted || vote_confirmed}>
									Confirm vote
								</Button>
							</div>
						</div>
					</div>
				{/if}
				<!-- Votes Chart -->
				<div class="card bg-base-100 shadow-xl">
					<div class="card-body">
						<div bind:this={votesChartContainer} class="w-full h-48"></div>
					</div>
				</div>
				<!-- History Browser Component, visible for owner only -->
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
						<div class="flex h-[600px] w-full items-center justify-center">
							<ScoreBands
								data={SCOREBands.data}
								axisNames={SCOREBands.axisNames}
								axisPositions={SCOREBands.axisPositions}
								axisSigns={SCOREBands.axisSigns}
								groups={SCOREBands.clusterIds}
								options={options}
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
					</div>
				</div>
			</div>
		</div>
		
		{:else if isDecisionPhase}
			<!-- DECISION PHASE: Solution Selection Content -->
			<div class="grid grid-cols-1 gap-6 lg:grid-cols-4">
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
										preferredSolutions: usersVote !== null ? [{
											values: decisionSolutions[usersVote],
											label: `Your Vote: Solution ${usersVote + 1}`
										}] : []
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
									groupVotes={decisionResult.user_votes || {}}
								/>
							{:else}
							<div class="text-center">
								<h2 class="text-2xl font-bold mb-4">Decision Phase</h2>
								<p class="text-gray-600 mb-4">Loading solutions...</p>
							</div>
							{/if}
						</div>
					</div>
				</div>

				<!-- Decision Controls -->
				<div class="lg:col-span-1">
					<div class="card bg-base-100 shadow-xl">
						<div class="card-body">
							<h2 class="card-title">Solution Voting</h2>
							<div class="space-y-2 p-2">
								<p class="text-sm text-gray-600">
									Click on a solution in the visualization, then vote for it.
								</p>
								
								{#if selected_solution !== null}
									<p class="text-sm font-semibold text-blue-600">
										Selected: Solution {selected_solution + 1}
									</p>
								{/if}
								
								{#if usersVote !== null}
									<div class="alert alert-success">
										<span>You voted for Solution {usersVote ? usersVote + 1 : '?'}</span>
									</div>
								{:else}
									<Button 
										onclick={() => vote(selected_solution)} 
										disabled={selected_solution === null}
									>
										Vote for Selected Solution
									</Button>
								{/if}
								
								{#if usersVote !== null && !vote_confirmed}
									<Button 
										onclick={() => vote(selected_solution)} 
										disabled={selected_solution === null}
									>
										Vote for Selected Solution
									</Button>
									<Button onclick={confirm_vote}>
										Confirm Final Decision
									</Button>
								{:else if vote_confirmed}
									<div class="alert alert-info">
										<span>Decision Confirmed!</span>
									</div>
								{/if}
								
								<!-- Group Progress -->
								{#if decisionResult?.user_votes}
									<div class="stats stats-vertical w-full">
										<div class="stat">
											<div class="stat-title">Votes Cast</div>
											<div class="stat-value text-sm">{Object.keys(decisionResult.user_votes).length}</div>
										</div>
										<div class="stat">
											<div class="stat-title">Confirmed</div>
											<div class="stat-value text-sm">{decisionResult.user_confirms.length}</div>
										</div>
									</div>
									
									{#if decisionResult.winner_solution_objectives && Object.keys(decisionResult.winner_solution_objectives).length > 0}
										<div class="alert alert-success">
											<span>🎉 Group decision reached!</span>
										</div>
									{/if}
								{/if}
							</div>
						</div>
					</div>
					<!-- History Browser Component -->
					<HistoryBrowser 
						{history}
						currentIterationId={iteration_id}
						onRevertToIteration={revert_to}
						{isOwner}
					/>
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
