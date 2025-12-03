<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import ScoreBands from '$lib/components/visualizations/score-bands/score-bands.svelte';
	import { onMount } from 'svelte';
	import type { components } from "$lib/api/client-types";

	// Data state variables
	let dummy_data: number[][] = $state([]); // TODO Stina: UI does not use this in the end.
	// let axis_names: string[] = $state([]); // TODO Stina: ? Names from API or does this use some problem like everything so that I can read it, match symbols to names?
	let axis_positions: number[] = $state([]); // TODO Stina: Comes straight from SCOREBandsResult, though need to convert dict[str, float] => number[]
	let axis_signs: number[] = $state([]); // TODO Stina: NOWHERE to be found! WHERE does this come from? It is needed in visualization for sure!
	let groups: number[] = $state([]); // TODO Stina: Not needed? Or what? There is the clusters in SCOREBandsResult that is closest to this, but not quite? Or is it?
	let data_loaded = $state(false); // This is for loading spinner, but the data in question is csv-data that is probably not neededd....?
	let loading_error: string | null = $state(null); // TODO Stina: --------''----------
	let scoreBandsResult : components['schemas']['SCOREBandsResult'] | null = $state(null); // ALRIGHT, so this has the things we will get from API in future.
	
	let SCOREBands = $derived.by(()=> {
		if (!scoreBandsResult || scoreBandsResult === null) {
			return {
				axisNames: [],
				clusterIds: [],
				axisPositions: [],
				axisSigns: [],
				data: [],
				// Empty objects for pre-calculated bands and medians
				bands: {}, 
            	medians: {}
			};
		}
		
		console.log('🏗️ SCOREBands direct structure:', (() => {
			if (!scoreBandsResult) {
				return { status: 'no data' };
			}
			
			return {
				originalBands: scoreBandsResult.bands,
				originalMedians: scoreBandsResult.medians,
				orderedDimensions: scoreBandsResult.ordered_dimensions,
				clusters: scoreBandsResult.clusters,
				clusterIds: Object.keys(scoreBandsResult.bands).sort((a, b) => parseInt(a) - parseInt(b)),
				bandsStructure: Object.keys(scoreBandsResult.bands).reduce((acc, clusterId) => {
					acc[clusterId] = Object.keys(scoreBandsResult!.bands[clusterId]);
					return acc;
				}, {} as Record<string, string[]>)
			};
		})());
		
		return {
			// Direct mappings
			axisNames: scoreBandsResult.ordered_dimensions,
			clusterIds: Object.keys(scoreBandsResult.bands).sort((a, b) => parseInt(a) - parseInt(b)).map(id => Number(id)),
			// Convert axis_positions dict to ordered array
			axisPositions: scoreBandsResult.ordered_dimensions.map(
				objName => scoreBandsResult?.axis_positions[objName]
			) as number[],
			
			// Missing data - need fallbacks
			axisSigns: new Array(scoreBandsResult.ordered_dimensions.length).fill(1), // Default: no flipping TODO
			data: [], // Empty - use bands-only mode
			
			// Pre-calculated bands and medians as original key-based structure
			// bands[clusterId][axisName] = [minValue, maxValue] - quantile-based band limits
			bands: scoreBandsResult.bands, 
			// medians[clusterId][axisName] = medianValue - median values per cluster per axis
			medians: scoreBandsResult.medians
		};
	})

	// Function to recalculate score bands parameters
	async function recalculate_parameters() {
		// if (dummy_data.length === 0 || axis_names.length === 0) {
		// 	console.warn('No data available for recalculation');
		// 	return;
		// }

		// try {
		// 	loading_error = null;

		// 	console.log('Recalculating score-bands parameters with:', {
		// 		dist_parameter,
		// 		use_absolute_corr,
		// 		distance_formula,
		// 		flip_axes,
		// 		clustering_algorithm,
		// 		clustering_score
		// 	});

		// 	const response = await fetch('/interactive_methods/GDM-SCORE-bands/calculate', {
		// 		method: 'POST',
		// 		headers: {
		// 			'Content-Type': 'application/json'
		// 		},
		// 		body: JSON.stringify({
		// 			data: dummy_data,
		// 			objs: axis_names,
		// 			dist_parameter: dist_parameter,
		// 			use_absolute_corr: use_absolute_corr,
		// 			distance_formula: distance_formula,
		// 			flip_axes: flip_axes,
		// 			clustering_algorithm: clustering_algorithm,
		// 			clustering_score: clustering_score
		// 		})
		// 	});

		// 	if (!response.ok) {
		// 		const errorData = await response.json();
		// 		throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
		// 	}

		// 	const result = await response.json();

		// 	if (!result.success) {
		// 		throw new Error(result.error || 'Failed to recalculate score bands parameters');
		// 	}

		// 	// Update parameters with new calculations
		// 	const { groups: new_groups, axis_dist, axis_signs: new_axis_signs } = result.data;

		// 	groups = new_groups;
		// 	axis_positions = axis_dist;
		// 	axis_signs = new_axis_signs || new Array(axis_names.length).fill(1);

		// 	console.log('Parameters recalculated successfully:', {
		// 		unique_groups: [...new Set(groups)].length,
		// 		axis_positions: axis_positions,
		// 		axis_signs: axis_signs
		// 	});
		// } catch (error) {
		// 	console.error('Error recalculating parameters:', error);
		// 	loading_error = error instanceof Error ? error.message : 'Unknown error occurred';
		// }
	}

	// Load data from CSV file and calculate SCORE bands parameters
	async function load_csv_data() {
		// try {
		// 	// Fetch the CSV file from the static folder
		// 	const csvResponse = await fetch('/data/dtlz7_4d.csv');
		// 	if (!csvResponse.ok) {
		// 		throw new Error(`HTTP ${csvResponse.status}: ${csvResponse.statusText}`);
		// 	}
		// 	const csv_text = await csvResponse.text();

		// 	if (!csv_text) {
		// 		throw new Error('CSV file is empty or could not be loaded');
		// 	}

		// 	const lines = csv_text.trim().split('\n');

		// 	if (lines.length < 2) {
		// 		throw new Error('CSV file must have at least a header and one data row');
		// 	}

		// 	// Parse header to get axis names
		// 	const header = lines[0].split(',').map((col) => col.trim());

		// 	// Assuming the CSV structure is: f1,f2,f3,f4,group
		// 	// where the last column is the group assignment (we'll ignore it and calculate our own)
		// 	axis_names = header.slice(0, -1); // All columns except the last one

		// 	// Parse data rows - extract only objective values (ignore existing group column)
		// 	const raw_data = [];

		// 	for (let i = 1; i < lines.length; i++) {
		// 		const values = lines[i].split(',').map((val) => parseFloat(val.trim()));

		// 		if (values.length !== header.length) {
		// 			console.warn(`Row ${i} has ${values.length} values, expected ${header.length}`);
		// 			continue;
		// 		}

		// 		// Extract objective values (all columns except the last one)
		// 		const objective_values = values.slice(0, -1);
		// 		raw_data.push(objective_values);
		// 	}

		// 	// Now call the score-bands API to calculate parameters
		// 	console.log('Calling score-bands API with data:', {
		// 		objectives: axis_names.length,
		// 		solutions: raw_data.length
		// 	});

		// 	const response = await fetch('/interactive_methods/GDM-SCORE-bands/calculate', {
		// 		method: 'POST',
		// 		headers: {
		// 			'Content-Type': 'application/json'
		// 		},
		// 		body: JSON.stringify({
		// 			data: raw_data,
		// 			objs: axis_names,
		// 			dist_parameter: dist_parameter,
		// 			use_absolute_corr: use_absolute_corr,
		// 			distance_formula: distance_formula,
		// 			flip_axes: flip_axes,
		// 			clustering_algorithm: clustering_algorithm,
		// 			clustering_score: clustering_score
		// 		})
		// 	});

		// 	if (!response.ok) {
		// 		const errorData = await response.json();
		// 		throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
		// 	}

		// 	const result = await response.json();

		// 	if (!result.success) {
		// 		throw new Error(result.error || 'Failed to calculate score bands parameters');
		// 	}

		// 	// Extract the calculated parameters
		// 	const {
		// 		groups: calculated_groups,
		// 		axis_dist,
		// 		axis_signs: calculated_axis_signs,
		// 		obj_order
		// 	} = result.data;

		// 	// Set the calculated parameters
		// 	groups = calculated_groups;
		// 	axis_positions = axis_dist;
		// 	axis_signs = calculated_axis_signs || new Array(axis_names.length).fill(1);

		// 	// Reorder the data and axis names according to the optimal objective order
		// 	const reordered_axis_names = obj_order.map((index: number) => axis_names[index]);
		// 	const reordered_data = raw_data.map((row) => obj_order.map((index: number) => row[index]));

		// 	// Update the final data
		// 	axis_names = reordered_axis_names;
		// 	dummy_data = reordered_data;

		// 	data_loaded = true;
		// 	loading_error = null;

		// 	console.log('Data loaded and parameters calculated successfully:', {
		// 		solutions: dummy_data.length,
		// 		objectives: axis_names.length,
		// 		unique_groups: [...new Set(groups)].length,
		// 		axis_positions: axis_positions,
		// 		axis_signs: axis_signs,
		// 		objective_order: obj_order
		// 	});
		// } catch (error) {
		// 	console.error('Error loading CSV data or calculating parameters:', error);
		// 	loading_error = error instanceof Error ? error.message : 'Unknown error occurred';
		// }
	}

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
		// Clear existing timer
		if (quantile_debounce_timer) {
			clearTimeout(quantile_debounce_timer);
		}
		
		// Set up new debounced API call
		quantile_debounce_timer = setTimeout(async () => {
			const interval_size = quantileToIntervalSize(quantile_value);
			
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

	// Update cluster visibility when groups data changes
	$effect(()=>{
		if (SCOREBands && SCOREBands.clusterIds.length > 0) {
	
			// Initialize all clusters as visible if not already set
			SCOREBands.clusterIds.forEach((clusterId) => {
				if ((clusterId in cluster_visibility_map)) {
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
	onMount(() => {
		// load_csv_data();
		const initial_interval_size = quantileToIntervalSize(quantile_value);
		fetch_score_bands(initial_interval_size);
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


	async function fetch_score_bands(interval_size: number = 0.5) {
		try {
			// console.log('Starting EMO iterate and fetch score test...');
			
			// // Step 1: Call iterate endpoint
			// console.log('Step 1: Calling iterate endpoint...');
			// const iterateResponse = await fetch('/interactive_methods/GDM-SCORE-bands/iterate', {
			// 	method: 'POST',
			// 	headers: {
			// 		'Content-Type': 'application/json'
			// 	},
			// 	body: JSON.stringify({
			// 		problem_id: 1, // Default test problem ID
			// 	})
			// });

			// if (!iterateResponse.ok) {
			// 	const errorData = await iterateResponse.json();
			// 	throw new Error(`Iterate failed: ${errorData.error || `HTTP ${iterateResponse.status}: ${iterateResponse.statusText}`}`);
			// }

			// const iterateResult = await iterateResponse.json();
			// console.log('Iterate completed:', iterateResult);
			
			// if (!iterateResult.success) {
			// 	throw new Error(`Iterate failed: ${iterateResult.error || 'Unknown error'}`);
			// }

			// // Step 2: Wait 10 seconds (EMO algorithms need time to complete)
			// console.log('Step 2: Waiting 20 seconds for EMO algorithm to complete...');
			// await new Promise(resolve => setTimeout(resolve, 20000));

			// Step 3: Call fetch_score_bands endpoint with state_id from iterate and SCOREBandsConfig
			console.log('Step 3: Calling fetch_score_bands endpoint with interval_size:', interval_size);
			
			// Configure SCORE bands with K-means clustering and dynamic interval_size
			const scoreBandsConfig = {
				interval_size: interval_size,
				clustering_algorithm: {
					name: "KMeans",
					n_clusters: 5
				}
			};
			
			const scoreResponse = await fetch('/interactive_methods/GDM-SCORE-bands/fetch_score_bands', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					problem_id: 1,
					session_id: null,
					parent_state_id: 10, // iterateResult.data.state_id, // Use state_id from iterate response
					config: scoreBandsConfig,
					solution_ids: []
				})
			});

			if (!scoreResponse.ok) {
				const errorData = await scoreResponse.json();
				throw new Error(`Fetch score failed: ${errorData.error || `HTTP ${scoreResponse.status}: ${scoreResponse.statusText}`}`);
			}

			const scoreResult = await scoreResponse.json();
			console.log('Fetch score completed:', scoreResult);
			
			if (scoreResult.success) {
				scoreBandsResult = scoreResult.data.result;
			} else {
				throw new Error(`Fetch score failed: ${scoreResult.error || 'Unknown error'}`);
			}
			data_loaded = true;
			loading_error = null;

		} catch (error) {
			console.error('Error in doSomething:', error);
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
		<!-- Show quantile loading indicator if updating -->
		{#if is_quantile_loading}
			<div class="alert alert-info mb-4">
				<div class="flex items-center gap-2">
					<div class="loading loading-spinner loading-sm"></div>
					<span>Updating bands for quantile {quantile_value}...</span>
				</div>
			</div>
		{/if}
		<!-- Parameter Controls -->
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
						onclick={recalculate_parameters}
						class="btn btn-primary"
						disabled={SCOREBands.axisNames.length === 0}
					>
						Recalculate Parameters
					</button>
				</div>
			</div>
		</div>

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


				<!-- "Hacky button" -->
				<div class="card bg-base-100 shadow-xl">
					<div class="card-body">
						<h2 class="card-title">Voting</h2>
						<div class="space-y-2 p-2">
							<Button onclick={() => fetch_score_bands(quantileToIntervalSize(quantile_value))}>
								Vote
							</Button>
							<Button onclick={() => fetch_score_bands(quantileToIntervalSize(quantile_value))}>
								Ready to continue
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
	{/if}
</div>

<style>
	:global(.container) {
		max-width: 100%;
	}
</style>
