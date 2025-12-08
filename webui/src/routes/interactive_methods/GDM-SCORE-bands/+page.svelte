<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import ScoreBands from '$lib/components/visualizations/score-bands/score-bands.svelte';
	import { onMount, onDestroy } from 'svelte';
	import type { components } from "$lib/api/client-types";
	import { auth } from '../../../stores/auth';

	// WebSocket service import
	import { WebSocketService } from './websocket-store';
	
	// Helper functions import
	import { drawVotesChart } from './helper-functions';

	// Page data props
	type Group = components['schemas']['GroupPublic'];
	type Problem = components['schemas']['ProblemInfo'];
	
	const { data } = $props<{ 
		data: { 
			refreshToken: string;
			group: Group;
			problem: Problem;
		} 
	}>();

	// User authentication
	let userId = $auth.user?.id;
	let isOwner = $state(false);
	let isDecisionMaker = $state(false);

	// Initialize user roles if in group mode
	$effect(() => {
		if (data.group && userId) {
			isOwner = userId === data.group.owner_id;
			isDecisionMaker = data.group.user_ids.includes(userId);
		}
	});

	// WebSocket service for real-time updates
	let wsService: WebSocketService | null = $state(null);
	let websocket_message = $state('');
	
	// TODO: Add more websocket-related state variables as needed:
	// - voting status updates
	// - iteration status
	// - other users' actions

	let data_loaded = $state(false); // TODO: This is for loading spinner, but the data in question is csv-data that is probably not neededd....?
	let loading_error: string | null = $state(null); // TODO Stina: --------''----------
	let vote_given = $state(false);
	let vote_confirmed = $state(false);
	let votes_and_confirms = $state({
		confirms: [] as number[],
		votes: {} as Record<number, number>
	});
	$effect(() => {
		if (userId) {
			// Use a safe hasOwnProperty check and typed votes map so numeric indexing is allowed
			vote_given = Object.prototype.hasOwnProperty.call(votes_and_confirms.votes, userId);
			vote_confirmed = votes_and_confirms.confirms.includes(userId);
		} else {
			vote_given = false;
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
	const totalVoters = data.group ? data.group.user_ids.length : 4;

	let phase = $state('Consensus Reaching Phase'); // 'Consensus reaching phase' or 'Decision phase'
	let iteration_id = $state(0);
	let scoreBandsResult: components['schemas']['SCOREBandsResult'] | null = $state(null);
	
	let SCOREBands = $derived.by(()=> {
		if (!scoreBandsResult || scoreBandsResult === null) {
			return {
				axisNames: [] as string[],
				clusterIds: [] as number[],
				axisPositions: [] as number[],
				axisSigns: [] as number[],
				data: [] as number[][],
				// Empty objects for pre-calculated bands and medians
				bands: {}, 
				medians: {},
				scales: undefined
			};
		}
		
		// Calculate scales: use API scales if available, otherwise calculate from bands data
		function calculateScales(result: components['schemas']['SCOREBandsResult']): Record<string, [number, number]> {
			// First try to use scales from API
			if (result.options?.scales) {
				return result.options.scales;
			}
			
			// Fallback: calculate scales from bands data
			const fallbackScales: Record<string, [number, number]> = {};
			
			result.ordered_dimensions.forEach(axisName => {
				let min = Infinity;
				let max = -Infinity;
				
				// Find min/max across all clusters for this axis
				Object.values(result.bands).forEach(clusterBands => {
					if (clusterBands[axisName]) {
						const [bandMin, bandMax] = clusterBands[axisName];
						min = Math.min(min, bandMin);
						max = Math.max(max, bandMax);
					}
				});
				
				// Also check medians for additional range
				Object.values(result.medians).forEach(clusterMedians => {
					if (clusterMedians[axisName] !== undefined) {
						const median = clusterMedians[axisName];
						min = Math.min(min, median);
						max = Math.max(max, median);
					}
				});
				
				fallbackScales[axisName] = [min, max];
			});
			
			return fallbackScales;
		}
		
		const derivedData = {
			// Direct mappings
			axisNames: scoreBandsResult.ordered_dimensions,
			clusterIds: Object.keys(scoreBandsResult.bands).sort((a, b) => parseInt(a) - parseInt(b)).map(id => Number(id)),
			// Convert axis_positions dict to ordered array
			axisPositions: scoreBandsResult.ordered_dimensions.map(
				objName => scoreBandsResult?.axis_positions[objName]
			) as number[],
			
			// Missing data - need fallbacks
			axisSigns: new Array(scoreBandsResult.ordered_dimensions.length).fill(1), // Default: no flipping TODO, should this be just "Flip axes"-checkbox? In visualization options? Or is this based on something actual and should come from API?
			data: [], // Empty - use bands-only mode
			
			// Pre-calculated bands and medians as original key-based structure
			// bands[clusterId][axisName] = [minValue, maxValue] - quantile-based band limits
			bands: scoreBandsResult.bands, 
			// medians[clusterId][axisName] = medianValue - median values per cluster per axis
			medians: scoreBandsResult.medians,
			// scales[axisName] = [minValue, maxValue] - normalization scales for converting raw values to [0,1]
			scales: calculateScales(scoreBandsResult)
		};
		
		return derivedData;
	})


	// Reactive options with checkboxes
	let show_bands = $state(true);
	let show_solutions = $state(false); // Disabled for API mode - no individual solutions
	let show_medians = $state(false); // Hide medians by default
	let quantile_value = $state(0.25);
	let is_quantile_loading = $state(false); // Loading state for quantile changes

	// Conversion functions between quantile and interval_size
	function quantileToIntervalSize(quantile: number): number {
		return 1 - (2 * quantile);
	}

	// Helper functions to prevent deselecting all visualization options
	function canToggleBands() {
		// Can toggle bands off only if medians would remain on (solutions is disabled)
		return !show_bands || (show_medians || show_solutions);
	}

	function canToggleMedians() {
		// Can toggle medians off only if bands would remain on
		return !show_medians || (show_bands || show_solutions);
	}

	// Score bands calculation parameters
	let dist_parameter = $state(0.05);
	let use_absolute_corr = $state(false);
	let distance_formula = $state(1); // 1 for euclidean, 2 for manhattan
	let flip_axes = $state(true);
	let clustering_algorithm = $state('DBSCAN'); // 'DBSCAN' or 'GMM'
	let clustering_score = $state('silhoutte'); // Note: This is the correct spelling used in DESDEO

	let options = $derived.by(()=>{
		return {
		bands: show_bands,
		solutions: show_solutions,
		medians: show_medians,
		quantile: quantile_value
	}});

	// Debounced effect for reactive quantile changes
	let quantile_debounce_timer: ReturnType<typeof setTimeout> | undefined;
	
	$effect(() => {
		// Access quantile_value in the effect scope to make it reactive
		const currentQuantile = quantile_value;
		
		// Clear existing timer
		if (quantile_debounce_timer) {
			clearTimeout(quantile_debounce_timer);
		}
		
		// Set up new debounced API call
		quantile_debounce_timer = setTimeout(async () => {
			const interval_size = quantileToIntervalSize(currentQuantile);
			
			try {
				is_quantile_loading = true;
				await fetch_score_bands(interval_size);
			} catch (error) {
				console.error('❌ Error updating bands for quantile:', error);
				loading_error = `Failed to update bands: ${error}`;
			} finally {
				is_quantile_loading = false;
			}
		}, 500); // 500ms debounce delay
	});

	// Cluster visibility controls - dynamically generated based on data
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

	// Load data on component mount
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
					// showTemporaryMessage('Reconnected to server');
					fetch_score_bands(quantileToIntervalSize(quantile_value));
					// TODO: Add more specific state refresh logic here, IF NEEDED, e.g.:
					// - Refresh current voting status
					// - Update UI to show current group state
				}
			);
			
			// Subscribe to websocket messages
			wsService.messageStore.subscribe((store) => {
				websocket_message = store.message; // TODO: if I want to show messages, I can use this and filter them or sth
				// Handle different message types from the backend:
				const msg = store.message;
				
				// Handle update messages (these don't show to user, just trigger state updates)
				// TODO: in the END, look if you can make this simpler or sth. And make sure you dont make the neglect errors like before
				if (msg.includes('UPDATE: A vote has been cast.')) {
					fetch_votes_and_confirms();
					return;
				}
				
				if (msg.includes('iteration')) {
					fetch_score_bands(quantileToIntervalSize(quantile_value));
					fetch_votes_and_confirms();
					return;
				}
				
				// Handle error messages
				if (msg.includes('ERROR')) {
					console.error('WebSocket error:', msg);
					// TODO: Show error to user appropriately
					return;
				}
				
				// TODO: Handle other message types specific to score-bands
				// You might want to add more message patterns here
			});
		}

		const initial_interval_size = quantileToIntervalSize(quantile_value);
		await fetch_score_bands(initial_interval_size);
		await fetch_votes_and_confirms();
		// Ensure clusters are visible after initial load
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

	// Helper function to generate consistent cluster colors
	function generate_cluster_colors() {
		const color_palette = [
			'#1f77b4', // Strong blue
			'#ff7f0e', // Vibrant orange
			'#2ca02c', // Strong green
			'#d62728', // Bold red
			'#9467bd', // Purple
			'#8c564b', // Brown
			'#e377c2', // Pink
			'#7f7f7f', // Gray
			'#bcbd22', // Olive/yellow-green
			'#17becf' // Cyan
		];

		const cluster_colors: Record<number, string> = {};

		SCOREBands.clusterIds.forEach((clusterId, index) => {
			cluster_colors[clusterId] = color_palette[index % color_palette.length];
		});

		return cluster_colors;
	}

	let cluster_colors = $derived(SCOREBands.clusterIds.length > 0 ? generate_cluster_colors() : {});

	// Helper function to generate axis options with colors and styles
	function generate_axis_options() {
		return SCOREBands.axisNames.map((_, index) => {
			// Set specific styles for axis 1 (green) and axis 3 (red)
			if (index === 1) {
				return {
					color: '#0000FF', // Blue for axis 1
					strokeWidth: 2,
					strokeDasharray: '5,5'
				};
			}
			if (index === 3) {
				return {
					color: '#FF0000', // Red for axis 3
					strokeWidth: 3,
					strokeDasharray: '5,5' // Dashed line
				};
			}
			// Default gray color and solid line for all other axes
			return {
				color: '#666666', // Gray for all other axes
				strokeWidth: 1,
				strokeDasharray: 'none'
			};
		});
	}

	let axis_options = $derived(SCOREBands.axisNames.length > 0 ? generate_axis_options() : []);

	// Selection state
	let selected_band: number | null = $state(null);
	let selected_axis: number | null = $state(null);

	// Selection handlers
	function handle_band_select(clusterId: number | null) {
		selected_band = clusterId;
	}

	function handle_axis_select(axisIndex: number | null) {
		selected_axis = axisIndex;
	}

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

	// TODO: documentation text
	async function fetch_score_bands(interval_size: number = 0.5) {
		try {
			// Configure SCORE bands with K-means clustering and dynamic interval_size
			const scoreBandsConfig = {
				interval_size: interval_size,
				clustering_algorithm: {
					name: "KMeans",
					n_clusters: 5
				}
			};
			
			// Use group-specific problem ID if available, otherwise default to problem 1
			const problemId = data.group?.problem_id || 1;
		
			
			const scoreResponse = await fetch('/interactive_methods/GDM-SCORE-bands/fetch_score_bands', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					group_id: data.group.id,
					score_bands_config: scoreBandsConfig,
				})
			});

			if (!scoreResponse.ok) {
				const errorData = await scoreResponse.json();
				throw new Error(`Fetch score failed: ${errorData.error || `HTTP ${scoreResponse.status}: ${scoreResponse.statusText}`}`);
			}

			const scoreResult = await scoreResponse.json();
			
			if (scoreResult.success) {
				scoreBandsResult = scoreResult.data.result;
				iteration_id = scoreResult.data.group_iter_id;
				console.log('✅ SCORE bands fetched successfully:', scoreBandsResult);
			} else {
				throw new Error(`Fetch score failed: ${scoreResult.error || 'Unknown error'}`);
			}
			data_loaded = true;
			loading_error = null;
		} catch (error) {
			console.error('Error in fetch_score_bands:', error);
			alert(`Error: ${error}`);
		}
	}

	// TODO: documentation text
	async function vote(band: number | null) {
		if (band === null) {
			alert('Please select a band to vote for.');
			return;
		}
		console.log("band to vote for:", band);
		try {
			const voteResponse = await fetch('/interactive_methods/GDM-SCORE-bands/vote', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					group_id: data.group.id,
					vote: band,
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
			alert(`Error: ${error}`);
		}
	}

	// TODO: documentation text
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
			alert(`Error: ${error}`);
		}
	}

	// TODO: documentation text
	async function fetch_votes_and_confirms() {
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
				console.log('Votes and confirms fetched successfully:', result.data);
				// If user has voted already, select the band they voted for
				if (userId && votes_and_confirms.votes.hasOwnProperty(userId)) {
					selected_band = votes_and_confirms.votes[userId];
				} else {
					selected_band = null;
				}
			} else {
				throw new Error(`Get votes and confirms failed: ${result.error || 'Unknown error'}`);
			}
		} catch (error) {
			console.error('Error in get_votes_and_confirms:', error);
			alert(`Error: ${error}`);
		}
	}
</script>

<div class="container mx-auto p-6">
	{#if !data_loaded}
		<div class="flex h-96 items-center justify-center">
			<div class="text-center">
				<div class="loading loading-spinner loading-lg"></div>
				<p class="mt-4">Loading data...</p>
				{#if loading_error}
					<p class="text-error mt-2">Error: {loading_error}</p>
					<p class="mt-1 text-sm text-gray-500">Using fallback data instead</p>
				{/if}
			</div>
		</div>
	{:else}
		<!-- Show quantile loading indicator if updating TODO whats the point, no point anymore, remove.-->
		{#if is_quantile_loading}
			<div class="alert alert-info mb-4">
				<div class="flex items-center gap-2">
					<div class="loading loading-spinner loading-sm"></div>
					<span>Updating bands for quantile {quantile_value}...</span>
				</div>
			</div>
		{/if}
		
		<!-- Header and Instructions -->
		<div class="card bg-base-100 mb-6 shadow-xl">
			<div class="card-body">
				<div class="">
					<!-- Header Section -->
					<div class="font-semibold">
						HEADER: Iteration {iteration_id}, {phase}
					</div>
					<!-- Instructions Section TODO: instructions to match voting situation, need group info -->
					<div>Click a cluster on the graph, vote with the button, then confirm when ready to continue.</div>
					<div> Votes: {Object.keys(votes_and_confirms.votes || {}).length}</div>
					<div> Confirms: {votes_and_confirms.confirms.length}</div>

				</div>
			</div>
		</div>

		<!-- Parameter Controls -->
		 {#if isOwner}
			<div class="card bg-base-100 mb-6 shadow-xl">
				<div class="card-body">
					<h3 class="card-title">Score Bands Parameters</h3>
					<div class="grid grid-cols-2 gap-4">
						<div class="form-control">
							<label for="dist_parameter" class="label">
								<span class="label-text">Distance Parameter</span>
							</label>
							<input
								id="dist_parameter"
								type="number"
								bind:value={dist_parameter}
								min="0"
								max="1"
								step="0.1"
								class="input input-bordered"
							/>
						</div>
						<div class="form-control">
							<label for="distance_formula" class="label">
								<span class="label-text">Distance Formula</span>
							</label>
							<select
								id="distance_formula"
								bind:value={distance_formula}
								class="select select-bordered"
							>
								<option value={1}>Euclidean</option>
								<option value={2}>Manhattan</option>
							</select>
						</div>
						<div class="form-control">
							<label for="clustering_algorithm" class="label">
								<span class="label-text">Clustering Algorithm</span>
							</label>
							<select
								id="clustering_algorithm"
								bind:value={clustering_algorithm}
								class="select select-bordered"
							>
								<option value="DBSCAN">DBSCAN</option>
								<option value="GMM">GMM</option>
							</select>
						</div>
						<div class="form-control">
							<label for="clustering_score" class="label">
								<span class="label-text">Clustering Score</span>
							</label>
							<select
								id="clustering_score"
								bind:value={clustering_score}
								class="select select-bordered"
							>
								<option value="silhoutte">Silhouette</option>
								<option value="BIC">BIC</option>
							</select>
						</div>
					</div>
					<div class="mt-4 flex items-center gap-4">
						<label class="label cursor-pointer">
							<input
								type="checkbox"
								bind:checked={use_absolute_corr}
								class="checkbox checkbox-primary mr-2"
							/>
							<span class="label-text">Use Absolute Correlation</span>
						</label>
						<label class="label cursor-pointer">
							<input
								type="checkbox"
								bind:checked={flip_axes}
								class="checkbox checkbox-primary mr-2"
							/>
							<span class="label-text">Flip Axes</span>
						</label>
						<button
							onclick={()=>{}}
							class="btn btn-primary"
							disabled={SCOREBands.axisNames.length === 0}
						>
							Recalculate Parameters
						</button>
					</div>
				</div>
			</div>
		{/if}

		<div class="grid grid-cols-1 gap-6 lg:grid-cols-5">
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

						<div class="form-control">
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
						</div>

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

						<!-- Quantile Slider -->
						<div class="form-control">
							<label class="label">
								<span class="label-text">Quantile: {quantile_value}</span>
								{#if is_quantile_loading}
									<span class="loading loading-spinner loading-sm"></span>
								{/if}
							</label>
							<input
								type="range"
								min="0.1"
								max="0.5"
								step="0.05"
								bind:value={quantile_value}
								disabled={is_quantile_loading}
								class="range range-primary"
								title="Adjust quantile to change band width (triggers API call)"
							/>
							<div class="flex w-full justify-between px-2 text-xs">
								<span>0.1</span>
								<span>0.3</span>
								<span>0.5</span>
							</div>
							<div class="mt-2 text-xs text-gray-600">
								Interval size: {quantileToIntervalSize(quantile_value).toFixed(2)}
							</div>
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

							{#if selected_axis !== null}
								<div class="alert alert-warning">
									<span class="font-medium"
										>Axis "{SCOREBands.axisNames[selected_axis] || 'Unknown'}" selected</span
									>
								</div>
							{:else}
								<div class="text-sm text-gray-500">No axis selected</div>
							{/if}

							{#if selected_band === null && selected_axis === null}
								<div class="mt-2 text-xs text-gray-400">Click on bands or axes to select them</div>
							{/if}
						</div>
					</div>
				</div>


				<!-- "Voting buttons" -->
				<div class="card bg-base-100 shadow-xl">
					<div class="card-body">
						<h2 class="card-title">Voting</h2>
						<div class="space-y-2 p-2">
							<Button onclick={() => vote(selected_band)} disabled={selected_band === null || vote_confirmed}>
								Vote
							</Button>
							<Button onclick={confirm_vote} disabled={!vote_given}>
								Confirm vote
							</Button>
						</div>
					</div>
				</div>
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

			<!-- Votes Chart -->
			<div class="lg:col-span-1">
				<div class="card bg-base-100 shadow-xl">
					<div class="card-body">
						<div bind:this={votesChartContainer} class="w-full h-48"></div>
					</div>
				</div>
			</div>
		</div>
	{/if}
</div>

<style>
	:global(.container) {
		max-width: 100%;
	}
</style>
