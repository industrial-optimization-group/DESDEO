<script lang="ts">
	/**
	 * config-panel.svelte
	 *
	 * @author Stina Palomäki <palomakistina@gmail.com>
	 * @created December 2025
	 * @updated December 2025
	 *
	 * @description
	 * Configuration panel component for SCORE Bands group decision making (GDM) parameters.
	 * Provides a comprehensive interface for adjusting clustering algorithms, distance calculations,
	 * visualization options, and voting thresholds. The component follows a props-based architecture
	 * for reusability and maintainability, accepting current configuration values and notifying
	 * parent components of changes through callbacks.
	 *
	 * @props
	 * @property {SCOREBandsConfig | null} currentConfig - Current SCORE bands configuration from API
	 * @property {number} totalVoters - Total number of voters in the group for minimum votes validation
	 * @property {Function} onRecalculate - Callback function to execute when configuration changes
	 * @property {boolean} [isVisible=true] - Controls visibility of the entire configuration panel
	 *
	 * @features
	 * - **Clustering Configuration**: Algorithm selection (DBSCAN, KMeans, GMM) with dynamic cluster count
	 * - **Distance Parameters**: Formula selection and parameter tuning for axis positioning
	 * - **Visualization Options**: Controls for band width, solution inclusion, and median display
	 * - **Voting Controls**: Minimum votes threshold for group decision progression
	 * - **Real-time Updates**: Form values sync with incoming configuration changes
	 * - **Type Safety**: Full TypeScript support with OpenAPI-generated schemas
	 * - **Validation**: Input constraints and conditional field enabling
	 *
	 * @implementation_status
	 * ** IMPLEMENTED (Working)**
	 * - Basic clustering parameters (distance_parameter, distance_formula, clustering_algorithm)
	 * - Cluster count configuration (n_clusters) with DBSCAN conditional disabling
	 * - Interval size slider for band width control
	 * - Boolean toggles (use_absolute_correlations, include_solutions, include_medians)
	 * - Minimum votes configuration for GDM workflow
	 * - Form state synchronization with external configuration changes
	 * - Configuration building and callback integration
	 *
	 * **🚧 NOT IMPLEMENTED (Advanced Features)**
	 * - dimensions: Multi-select dropdown for objective subset selection
	 * - descriptive_names: Key-value editor for custom objective display names
	 * - units: Key-value editor for objective unit specifications
	 * - axis_positions: Manual axis positioning controls (drag-and-drop or numeric inputs)
	 * - scales: Min/max range inputs for objective scaling overrides
	 * - from_iteration: Historical iteration selection for configuration inheritance
	 *
	 * @dependencies
	 * - $lib/components/ui/button for action buttons
	 * - $lib/api/client-types for OpenAPI-generated TypeScript types
	 * - Svelte 5 runes ($state, $effect) for reactive state management
	 * - DaisyUI classes for consistent styling and form components
	 *
	 * @data_flow
	 * 1. Parent component passes currentConfig and callback function
	 * 2. Component initializes form state from currentConfig or defaults
	 * 3. User modifies form values through UI interactions
	 * 4. On "Recalculate Parameters" click, buildConfiguration() creates API payload
	 * 5. onRecalculate callback sends configuration to parent for API submission
	 * 6. Parent refreshes data and passes updated currentConfig back to component
	 *
	 * @usage_example
	 * ```svelte
	 * <ConfigPanel 
	 *   currentConfig={scoreBandsResult?.options || null}
	 *   totalVoters={groupUserCount}
	 *   onRecalculate={handleConfigurationUpdate}
	 *   isVisible={isOwner && isConsensusPhase}
	 * />
	 * ```
	 *
	 * @notes
	 * - Component automatically disables n_clusters input when DBSCAN is selected
	 * - Interval size uses range slider with visual feedback and descriptive tooltip
	 * - Form validation ensures minimum votes doesn't exceed total voters
	 * - Configuration building follows SCOREBandsGDMConfig schema requirements
	 * - Advanced configuration options are marked as null for future implementation
	 */
	import { Button } from '$lib/components/ui/button';
	import type { components } from "$lib/api/client-types";

	// Component props
	const {
		currentConfig,
		latestIteration,
		totalVoters,
		onRecalculate,
		isVisible = true
	} = $props<{
		currentConfig: components['schemas']['SCOREBandsConfig'] | null;
		latestIteration: number | null;
		totalVoters: number;
		onRecalculate: (config: components['schemas']['SCOREBandsGDMConfig']) => void;
		isVisible?: boolean;
	}>();

	// Local reactive state for form values - initialized from currentConfig or defaults
	// These values are bound to form controls
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
	let latest_iteration = $state(latestIteration);

	/**
	 * Effect to synchronize form values when currentConfig changes
	 * 
	 * This ensures the form stays in sync when the parent component provides
	 * updated configuration data (e.g., after API responses or iteration changes).
	 * Prevents form state from becoming stale when external data updates occur.
	 */
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
		latest_iteration = latestIteration;
	});

	/**
	 * Build configuration object for API call
	 * 
	 * Constructs a complete SCOREBandsGDMConfig object from current form values.
	 * Maps UI form state to the API schema structure required by the backend.
	 * 
	 * @returns {SCOREBandsGDMConfig} Complete configuration object for API submission
	 * 
	 * @implementation_notes
	 * ** IMPLEMENTED - Form-based Configuration**
	 * - clustering_algorithm: Maps UI selection to algorithm object with conditional n_clusters
	 * - distance_formula: Direct mapping from select dropdown (1=Euclidean, 2=Manhattan)
	 * - distance_parameter: Number input for axis spacing control (0.0-1.0)
	 * - use_absolute_correlations: Boolean toggle for correlation calculation method
	 * - include_solutions: Boolean toggle for individual solution visibility
	 * - include_medians: Boolean toggle for cluster median display
	 * - interval_size: Range slider for band width (0.1-0.95 fraction)
	 * - minimum_votes: Number input for GDM voting threshold (1 to totalVoters)
	 * - from_iteration: latest_iteration (inherits config from specified iteration)
	 * 
	 * ** HARDCODED - Default Values (Ready for Future Implementation)**
	 * - dimensions: null (use all objectives)
	 * - descriptive_names: null (use original names)
	 * - units: null (no units displayed)
	 * - axis_positions: null (auto-calculated)
	 * - scales: null (auto-calculated ranges)
	 */
	function buildConfiguration(): components['schemas']['SCOREBandsGDMConfig'] {
		return {
			score_bands_config: {
				dimensions: null, // Future: Multi-select dropdown for objective subset selection
				descriptive_names: null, // Future: Key-value editor for custom objective display names  
				units: null, // Future: Key-value editor for objective unit specifications
				axis_positions: null, // Future: Drag-and-drop or numeric inputs for manual axis positioning (axis selection exists, commented out)
				scales: null, // Future: Min/max range inputs for objective scaling overrides
				
				// IMPLEMENTED: Clustering algorithm configuration with conditional n_clusters
				clustering_algorithm: {
					name: clustering_algorithm as any,
					// Conditionally include n_clusters only for KMeans and GMM (DBSCAN uses density-based clustering)
					...(clustering_algorithm !== 'DBSCAN' && { n_clusters: n_clusters })
				},
				
				// IMPLEMENTED: Distance calculation parameters
				distance_formula: distance_formula as components['schemas']['DistanceFormula'], // 1=Euclidean, 2=Manhattan
				distance_parameter: distance_parameter, // 0.0-1.0: Controls relative distances between objective axes
				
				// IMPLEMENTED: Visualization behavior controls
				use_absolute_correlations: use_absolute_correlations, // Whether to use absolute value of correlations for axis placement
				include_solutions: include_solutions, // Whether to show individual solutions in visualization
				include_medians: include_medians, // Whether to show cluster median traces
				interval_size: interval_size, // 0.1-0.95: Fraction of solutions to include in bands (band width control)

			},
			
			// IMPLEMENTED: Group decision making parameters  
			minimum_votes: minimum_votes, // Minimum votes required to proceed to next iteration
			from_iteration: latest_iteration
		};
	}

	/**
	 * Handle recalculation button click
	 * 
	 * Builds the current configuration from form values and triggers the parent
	 * component's recalculation callback. This initiates the API call to update
	 * the SCORE bands configuration and refresh the visualization.
	 */
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