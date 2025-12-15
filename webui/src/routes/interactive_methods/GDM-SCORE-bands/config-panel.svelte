<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import type { components } from "$lib/api/client-types";

	// Component props
	const {
		currentConfig,
		totalVoters,
		onRecalculate,
		isVisible = true
	} = $props<{
		currentConfig: components['schemas']['SCOREBandsConfig'] | null;
		totalVoters: number;
		onRecalculate: (config: components['schemas']['SCOREBandsGDMConfig']) => void;
		isVisible?: boolean;
	}>();

	// Local state for form values - initialized from currentConfig or defaults
	let distance_parameter = $state(currentConfig?.distance_parameter ?? 0.05);
	let distance_formula = $state(currentConfig?.distance_formula ?? 1);
	let clustering_algorithm = $state(currentConfig?.clustering_algorithm?.name ?? 'KMeans');
	let n_clusters = $state(
		(currentConfig?.clustering_algorithm as any)?.n_clusters ?? 5
	);
	let use_absolute_correlations = $state(currentConfig?.use_absolute_correlations ?? false);
	let include_solutions = $state(currentConfig?.include_solutions ?? false);
	let include_medians = $state(currentConfig?.include_medians ?? true);
	let interval_size = $state(currentConfig?.interval_size ?? 0.25);
	let minimum_votes = $state(1);

	// Update form values when currentConfig changes
	$effect(() => {
		if (currentConfig) {
			distance_parameter = currentConfig.distance_parameter;
			distance_formula = currentConfig.distance_formula;
			clustering_algorithm = currentConfig.clustering_algorithm?.name ?? 'KMeans';
			n_clusters = (currentConfig.clustering_algorithm as any)?.n_clusters ?? 5;
			use_absolute_correlations = currentConfig.use_absolute_correlations;
			include_solutions = currentConfig.include_solutions;
			include_medians = currentConfig.include_medians;
			interval_size = currentConfig.interval_size;
		}
	});

	// Build configuration object for API call
	function buildConfiguration(): components['schemas']['SCOREBandsGDMConfig'] {
		return  {
			score_bands_config: {
				dimensions: null, // null = use all dimensions
				descriptive_names: null, // null = use default names
				units: null, // null = use default units
				axis_positions: null, // null = use default positions
				clustering_algorithm: {
					name: clustering_algorithm as any,
					...(clustering_algorithm !== 'DBSCAN' && { n_clusters: n_clusters })
				},
				distance_formula: distance_formula as components['schemas']['DistanceFormula'],
				distance_parameter: distance_parameter,
				use_absolute_correlations: use_absolute_correlations,
				include_solutions: include_solutions,
				include_medians: include_medians,
				interval_size: interval_size,
				scales: null // null = auto-calculate scales
			},
			minimum_votes: minimum_votes,
			from_iteration: null
		};

        // const configExample = {
		// 		// Configuration for the underlying SCORE bands algorithm
		// 		score_bands_config: {
		// 			dimensions: null, // null = use all dimensions
		// 			descriptive_names: null, // null = use default names. Could be {[key: string]: string}
		// 			units: null, // null = use default units. Could be {[key: string]: string}
		// 			axis_positions: null, // null = use default positions. Could be {[key: string]: number}
		// 			clustering_algorithm: {
		// 				// Algorithm name: 'DBSCAN', 'KMeans', or 'GMM'
		// 				name: 'KMeans',
		// 				// Number of clusters (for KMeans and GMM)
		// 				n_clusters: 5
		// 			},
		// 			// Distance formula: 1 = Euclidean, 2 = Manhattan
		// 			// Determines how distances between points are calculated
		// 			distance_formula: 1,
		// 			// Distance parameter for clustering (0.0 to 1.0) 
		// 			// Used in clustering algorithms to determine cluster boundaries
		// 			distance_parameter: 0.05,
		// 			// Whether to use absolute correlation in distance calculations
		// 			// true = use absolute values, false = consider sign of correlation
		// 			use_absolute_correlations: false,
		// 			include_solutions: false, // Whether to include individual solutions in visualization. This shouldnot even work, if I am right; deprecated?
		// 			include_medians: true, // Whether to include medians in visualization
		// 			// Quantile parameter for band calculation (0.0 to 0.5)
		// 			// Determines the width of the bands - smaller values = narrower bands
		// 			interval_size: 0.25,
		// 			scales: null, // null = auto-calculate scales. Could be {[key: string]: [number, number]}					
		// 		},
				
		// 		// Minimum number of votes required to proceed to next iteration
		// 		// Must be greater than 0, typically set to majority or all users
		// 		minimum_votes: 1,
				
		// 		// Iteration number from which to start considering clusters
		// 		// null = start from beginning, number = start from specific iteration
		// 		from_iteration: null // TODO: should this be the latest_iteration, is there something wrong with it since it does not give new info?
		// 	};
	}

	function handleRecalculate() {
		const config = buildConfiguration();
		onRecalculate(config);
	}
</script>

{#if isVisible}
	<div class="card bg-base-100 mb-6 shadow-xl">
		<div class="card-body">
			<h3 class="card-title">Score Bands Parameters</h3>
			<div class="grid grid-cols-2 gap-4">
				<!-- Distance Parameter (0-1) -->
				<div class="form-control">
					<label for="distance_parameter" class="label">
						<span class="label-text">Distance Parameter</span>
					</label>
					<input
						id="distance_parameter"
						type="number"
						bind:value={distance_parameter}
						min="0"
						max="1"
						step="0.01"
						class="input input-bordered"
					/>
				</div>
				
				<!-- Distance Formula (1=Euclidean, 2=Manhattan) -->
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
				
				<!-- Clustering Algorithm -->
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
						<option value="KMeans">KMeans</option>
						<option value="GMM">GMM</option>
					</select>
				</div>

                <!-- Clustering score -->
                <!-- <div class="form-control">
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
                </div> -->

				<!-- Number of Clusters (for KMeans/GMM only) -->
				<div class="form-control">
					<label for="n_clusters" class="label">
						<span class="label-text">Number of Clusters</span>
					</label>
					<input
						id="n_clusters"
						type="number"
						bind:value={n_clusters}
						min="2"
						max="20"
						step="1"
						disabled={clustering_algorithm === 'DBSCAN'}
						class="input input-bordered"
						class:input-disabled={clustering_algorithm === 'DBSCAN'}
					/>
				</div>
				
				<!-- Interval Size -->
				<div class="form-control">
					<label for="interval_size" class="label">
						<span class="label-text">Interval Size: {interval_size.toFixed(2)}</span>
					</label>
					<input
						type="range"
						min="0.1"
						max="0.95"
						step="0.05"
						bind:value={interval_size}
						class="range range-primary"
						title="Fraction of solutions to include in bands (0.1 = 10%, 0.95 = 95%)"
					/>
					<div class="flex w-full px-2 text-xs justify-between">
						<span>0.1</span>
						<span>0.5</span>
						<span>0.95</span>
					</div>
				</div>
				
				<!-- Minimum Votes -->
				<div class="form-control">
					<label for="minimum_votes" class="label">
						<span class="label-text">Minimum Votes Required</span>
					</label>
					<input
						id="minimum_votes"
						type="number"
						bind:value={minimum_votes}
						min="1"
						max={totalVoters}
						step="1"
						class="input input-bordered"
					/>
				</div>
			</div>
			
			<!-- Boolean Options -->
			<div class="mt-4 flex flex-wrap items-center gap-4">
				<label class="label cursor-pointer">
					<input
						type="checkbox"
						bind:checked={use_absolute_correlations}
						class="checkbox checkbox-primary mr-2"
					/>
					<span class="label-text">Use Absolute Correlations</span>
				</label>
				
				<label class="label cursor-pointer">
					<input
						type="checkbox"
						bind:checked={include_solutions}
						class="checkbox checkbox-primary mr-2"
					/>
					<span class="label-text">Include Individual Solutions</span>
				</label>
				
				<label class="label cursor-pointer">
					<input
						type="checkbox"
						bind:checked={include_medians}
						class="checkbox checkbox-primary mr-2"
					/>
					<span class="label-text">Include Cluster Medians</span>
				</label>
			</div>
			
			<!-- Action Button -->
			<div class="mt-4">
				<Button
					onclick={handleRecalculate}
					class="btn btn-primary"
				>
					Recalculate Parameters
				</Button>
			</div>
		</div>
	</div>
{/if}