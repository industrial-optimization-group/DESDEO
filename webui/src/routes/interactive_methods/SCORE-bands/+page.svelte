<script lang="ts">
	/**
	 * +page.svelte (SCORE-bands method)
	 *
	 * @author Stina (Functionality) <palomakistina@gmail.com>
	 * @created December 2024
	 *
	 * @description
	 * This page implements the SCORE-bands interactive multiobjective optimization method in DESDEO.
	 * It displays a sidebar with problem information and SCORE-bands visualizations for individual users.
	 *
	 * @props
	 * @property {Object} data - Contains a list of optimization problems fetched from the server.
	 * @property {ProblemInfo[]} data.problems - List of problems.
	 *
	 * @features
	 * - Problem selection from available problems
	 * - SCORE-bands visualization with cluster analysis
	 * - Interactive band selection and voting
	 * - Solution table with detailed information
	 *
	 * @dependencies
	 * - ScoreBands: Component for SCORE-bands visualization
	 * - ParallelCoordinates: Component for parallel coordinates visualization
	 * - ScoreBandsSolutionTable: Table component for displaying solutions
	 * - methodSelection: Svelte store for the currently selected problem
	 */

	import { Button } from '$lib/components/ui/button';
	import ScoreBands from '$lib/components/visualizations/score-bands/score-bands.svelte';
	import ParallelCoordinates from '$lib/components/visualizations/parallel-coordinates/parallel-coordinates.svelte';
	import ScoreBandsSolutionTable from './score-bands-solution-table.svelte';
	import { onMount } from 'svelte';
	import type { components } from "$lib/api/client-types";
	import { methodSelection } from '../../../stores/methodSelection';


	// Page data props
	type Problem = components['schemas']['ProblemInfo'];
	
	const { data } = $props<{ 
		data: { 
			problems: Problem[];
		} 
	}>();
	type ProblemInfo = components['schemas']['ProblemInfo'];
	let problem: ProblemInfo | undefined = $state(undefined);
	let problem_list: ProblemInfo[] = $state(data.problems);


	let data_loaded = $state(false);
	let loading_error: string | null = $state(null);

	// SCORE-bands state variables
	let scoreBandsResult: components['schemas']['SCOREBandsResult'] | null = $state(null);
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

	// EMO state for demonstration
	let emoStateId: number | null = $state(null);
	
	let SCOREBands = $derived.by(()=> {
		if (!scoreBandsResult) {
			return {
				axisNames: [] as string[],
				clusterIds: [] as number[],
				axisPositions: [] as number[],
				axisSigns: [] as number[],
				data: [] as number[][],
				// Empty objects for pre-calculated bands and medians
				bands: {}, 
				medians: {},
				scales: {}
			};
		}
		
		// Type assertion to help TypeScript understand the structure
		const result = scoreBandsResult as components['schemas']['SCOREBandsResult'];
		
		// Calculate scales: use API scales if available, otherwise calculate from bands data 
		function calculateScales(result: components['schemas']['SCOREBandsResult']): Record<string, [number, number]> {
			// First try to use ideal and nadir from problem
			if (problem?.objectives) {
				const scales: Record<string, [number, number]> = {};
				problem.objectives.forEach((objective: any) => {
					const name = objective.name;
					const ideal = objective.ideal;
					const nadir = objective.nadir;
					if (ideal !== undefined && nadir !== undefined) {
						scales[name] = [nadir, ideal];
					}
				});
				// Only return scales from problem if we found at least one complete objective
				if (Object.keys(scales).length > 0) {
					return scales;
				}
			}
			// Second try to use scales from API
			if (result.options?.scales) {
				return result.options.scales;
			}
			
			// Fallback: calculate scales from bands data
			const fallbackScales: Record<string, [number, number]> = {};
			
			result.ordered_dimensions.forEach((axisName: string) => {
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
			axisNames: result.ordered_dimensions,
			clusterIds: Object.keys(result.bands).sort((a, b) => parseInt(a) - parseInt(b)).map(id => Number(id)),
			// Convert axis_positions dict to ordered array
			axisPositions: result.ordered_dimensions.map(
				(objName: string) => result.axis_positions[objName]
			) as number[],
			
			// Missing data - need fallbacks
			axisSigns: new Array(result.ordered_dimensions.length).fill(1), // Default: no flipping
			data: [], // Empty - use bands-only mode
			
			// Pre-calculated bands and medians as original key-based structure
			// bands[clusterId][axisName] = [minValue, maxValue] - quantile-based band limits
			bands: result.bands, 
			// medians[clusterId][axisName] = medianValue - median values per cluster per axis
			medians: result.medians,
			// scales[axisName] = [minValue, maxValue] - normalization scales for converting raw values to [0,1]
			scales: calculateScales(result)
		};
		
		return derivedData;
	})


	// Reactive options with checkboxes
	let show_bands = $state(true);
	let show_solutions = $state(false); // Disabled for now - no individual solutions
	let show_medians = $state(false); // Hide medians by default
	let quantile_value = $state(0.25);

	// TODO: do I need this? 
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
		if ($methodSelection.selectedProblemId) {
			problem = problem_list.find(
				(p: ProblemInfo) => String(p.id) === String($methodSelection.selectedProblemId)
			);

			if (problem) {
				await initializeDemoData();
				clusters_to_visible();
			} else {
				// No problem found but still show UI
				data_loaded = true;
			}
		} else {
			// No problem selected but still show UI
			data_loaded = true;
		}
	});

	// Initialize demo data using EMO endpoints for demonstration
	async function initializeDemoData() {
		// Show sample data for testing visualization
		scoreBandsResult = {
			ordered_dimensions: ['Objective 1', 'Objective 3', 'Objective 2'],
			axis_positions: { 'Objective 1': 0, 'Objective 2': 1, 'Objective 3': 0.2 },
			bands: {
				'1': { 'Objective 1': [0.1, 0.3], 'Objective 2': [0.4, 0.6], 'Objective 3': [0.2, 0.4] },
				'2': { 'Objective 1': [0.6, 0.8], 'Objective 2': [0.1, 0.3], 'Objective 3': [0.7, 0.9] }
			},
			medians: {
				'1': { 'Objective 1': 0.2, 'Objective 2': 0.5, 'Objective 3': 0.3 },
				'2': { 'Objective 1': 0.7, 'Objective 2': 0.2, 'Objective 3': 0.8 }
			},
			options: {
				scales: {
					'Objective 1': [0.0, 1.0],
					'Objective 2': [0.0, 1.0], 
					'Objective 3': [0.0, 1.0]
				}
			},
			clusters: {}
		} as unknown as components['schemas']['SCOREBandsResult'];
		
		data_loaded = true;
		loading_error = null;
		console.log('Demo mode: Sample data loaded for visualization');
	}

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
		return SCOREBands.axisNames.map((axisName: string) => {
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
	
	// Decision phase solution selection state tODO do I need the vote parameters to be separate for phases
	let selected_solution: number | null = $state(null);


	// Selection handlers
	function handle_band_select(clusterId: number | null) {
		selected_band = clusterId;
	}

	function handle_axis_select(axisIndex: number | null) {
		selected_axis = axisIndex;
	}

	// Decision phase solution selection handler
	function handle_solution_select(index: number | null, solutionData: any | null) {
		selected_solution = index;
		console.log('Selected solution:', index, solutionData);
	}

	// TODO
	async function fetch_score_bands() {
		try {			
			// This is now a placeholder - no longer fetching data
			console.log('fetch_score_bands: Not implemented for individual method');
			data_loaded = true;
			loading_error = null;
		} catch (error) {
			console.error('Error in fetch_score_bands:', error);
			alert(`Error: ${error}`);
		}
	}

	// Iterate to find new solutions based on current selection
	async function iterate(problem: ProblemInfo | undefined, selected_band: number | null) {
		if (!problem || selected_band === null) {
			alert('Please select a problem and a band to iterate from.');
			return;
		}

		console.log("Iterating from selected band:", selected_band);
		try {
			// For now, just show a message - this would call EMO iterate with preferences
			alert(`Iterate functionality: Would generate new solutions focusing on cluster ${selected_band}`);
			
			// TODO: Implement actual iteration logic
			// This would involve calling EMO iterate with preferences based on the selected band
			console.log('Iteration completed');
			
		} catch (error) {
			console.error('Error in iterate:', error);
			alert(`Error: ${error}`);
		}
	}

	// Confirm final solution selection
	async function confirmFinalSolution() {
		if (!problem || selected_solution === null) {
			alert('Please select a solution to confirm as final.');
			return;
		}

		try {
			// For now, just show a message - this would save the final solution
			alert(`Final solution confirmed: Solution ${selected_solution + 1} has been selected as the final decision.`);
			
			console.log('Final solution confirmed:', selected_solution);
			
		} catch (error) {
			console.error('Error in confirm final solution:', error);
			alert(`Error: ${error}`);
		}
	}

	// TODO: Remove this function - not needed for individual SCORE bands
	async function fetch_votes_and_confirms() {
		// This function is no longer needed for individual SCORE bands method
		console.log('fetch_votes_and_confirms: Not implemented for individual method');
	}

	// TODO: documentation text
	async function revert(iteration: number) {
		try {
			// Not implemented for individual SCORE bands method
			console.log('revert: Not implemented for individual method');
			alert('Revert functionality is not available in individual SCORE bands method');
		} catch (error) {
			console.error('Error in revert_iteration:', error);
			alert(`Error: ${error}`);
		}
	}

	// TODO: documentation text
	async function configure(config: components['schemas']['SCOREBandsGDMConfig']) {
		try {
			// Not implemented for individual SCORE bands method
			console.log('configure: Not implemented for individual method');
			alert('Configuration is not available in individual SCORE bands method');
		} catch (error) {
			console.error('Error in configure:', error);
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
						SCORE Bands demo page
					</div>
						<div>Click a cluster on the graph and iterate. Functionality is not implemented.</div>
				</div>
			</div>
		</div>

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
						onclick={()=>{}}
						class="btn btn-primary"
						disabled={SCOREBands.axisNames.length === 0}
					>
						Recalculate Parameters
					</button>
					<Button
						onclick={()=>revert(1)}
						class="btn btn-primary"
						disabled={true}
					>
						Revert to previous iteration
					</Button>
				</div>
			</div>
		</div>
		<!-- LEARNING PHASE: Existing SCORE Bands Content -->

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
							<label for="quantile_slider" class="label">
								<span class="label-text">Quantile: {quantile_value}</span>
							</label>
							<input
								id="quantile_slider"
								type="range"
								min="0.1"
								max="0.5"
								step="0.05"
								bind:value={quantile_value}
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
							<Button onclick={() => iterate(problem, selected_band)} disabled={selected_band === null}>
								Iterate
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
							{#if SCOREBands.axisNames.length > 0}
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
							{:else}
								<div class="text-center">
									<div class="text-lg font-semibold text-gray-500 mb-2">No SCORE bands data available</div>
									<div class="text-sm text-gray-400">
										{#if !problem}
											Select a problem from the NIMBUS method selection to see SCORE bands visualization
										{:else}
											Run optimization to generate data for SCORE bands analysis
										{/if}
									</div>
								</div>
							{/if}
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
