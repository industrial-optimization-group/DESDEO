<script lang="ts">
	/**
	 * Utopia Map Component
	 * 
	 * @author Stina Palomäki <palomakistina@gmail.com>
	 * @created August 2025
	 * 
	 * @description
	 * Displays geographic map visualizations for the Utopia problem in NIMBUS.
	 * Allows users to view different time periods of the forest management solution
	 * with year selection and map description toggle functionality.
	 * 
	 * This component uses ECharts (via EchartsComponent) to render map visualizations
	 * based on the provided GeoJSON data and visualization options. It supports 
	 * up to three time periods that can be switched via a segmented control.
	 * 
	 * @props
	 * @property {Record<PeriodKey, Record<string, any>>} mapOptions - ECharts options for each period
	 * @property {PeriodKey} selectedPeriod - Currently selected period ('period1', 'period2', 'period3'), bindable
	 * @property {string[]} yearlist - List of years/labels for the periods
	 * @property {object} [geoJSON] - GeoJSON data for the map
	 * @property {string} [mapName] - Title for the map
	 * @property {string} [mapDescription] - Description text for the map (shown in popup)
	 * 
	 * @features
	 * - Period switching with SegmentedControl
	 * - Toggleable map description popup
	 * - Responsive layout that adapts to container size
	 * - Fallback when no map data is available
	 * 
	 * @dependencies
	 * - $lib/components/custom/segmented-control - For period selection
	 * - $lib/components/custom/nimbus/echarts-component - For rendering the map
	 * - $lib/components/ui/button - For description toggle
	 * 
	 * @notes
	 * - This component is specifically designed for visualizing forest management solutions
	 *   in the UTOPIA problem within NIMBUS.
	 * - The map visualization requires valid GeoJSON data and properly formatted ECharts options.
	 */
	import { SegmentedControl } from '$lib/components/custom/segmented-control';
	import EchartsComponent from '$lib/components/custom/nimbus/echarts-component.svelte';
	import { Button } from '$lib/components/ui/button';

	type PeriodKey = 'period1' | 'period2' | 'period3';

	interface Props {
		mapOptions: Record<PeriodKey, Record<string, any>>;
		selectedPeriod: PeriodKey;
		yearlist: string[];
		geoJSON?: object;
		mapName?: string;
		mapDescription?: string;
	}

	let {
		mapOptions,
		selectedPeriod = $bindable(),
		yearlist = [],
		geoJSON,
		mapName,
		mapDescription
	}: Props = $props();

	// State for showing/hiding description
    let showDescription = $state(false);
</script>


<div class="flex h-full flex-1 overflow-hidden">
	{#if mapOptions[selectedPeriod] && Object.keys(mapOptions[selectedPeriod]).length > 0 && geoJSON}
		<!-- Period selection toggle -->
		<div class="w-full">
			<div class="flex items-center mb-2 justify-around">
				<h3 class="text-lg">{mapName || 'Forest Map'}</h3>
				<div> Years: </div>
				<SegmentedControl
					bind:value={selectedPeriod}
					options={yearlist.map((year, i) => ({
						value: `period${i+1}`,
						label: year || `Period ${i+1}`
					}))}
					size="sm"
				/>
				<!-- Description toggle button -->
				{#if mapDescription}
					<div class="relative">
						<Button 
							variant="outline" 
							size="sm" 
							onclick={() => showDescription = !showDescription}
						>
							Description
						</Button>
						
						{#if showDescription}
							<div class="absolute top-full right-0 z-10 mt-2 bg-white rounded-md shadow-lg p-4 w-80 max-h-60 overflow-y-auto">
								<div class="flex justify-between items-center mb-2">
									<h4 class="font-medium">Description</h4>
									<Button variant="ghost" size="icon" onclick={() => showDescription = false} class="h-5 w-5">
										<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
									</Button>
								</div>
								<div class="text-sm" style="white-space: pre-wrap;">
									{mapDescription}
								</div>
							</div>
						{/if}
					</div>
				{/if}
				</div>
				<div class="h-full flex mb-2 justify-around">   
					<!-- The actual map visualization, including data view etc. -->
					<EchartsComponent
						option={mapOptions[selectedPeriod]}
						{geoJSON}
						{mapName}
						customStyle="height: 80%;"
					/>
			</div>
		</div>
	{:else}
		<div class="placeholder">
			<p>Select a solution to view the map visualization</p>
		</div>
	{/if}
</div>
