<script lang="ts">
	import { ToggleGroup, ToggleGroupItem } from '$lib/components/ui/toggle-group';
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
				<div>Select period: </div>
				<ToggleGroup type="single" bind:value={selectedPeriod}>
					{#each yearlist as year, i}
					<ToggleGroupItem value={`period${i+1}`}>
						{year || `Period ${i+1}`}
					</ToggleGroupItem>
					{/each}
				</ToggleGroup>
				<!-- Description toggle button -->
                {#if mapDescription}
					<Button 
						variant="outline" 
						size="sm" 
						onclick={() => showDescription = !showDescription}
					>
						{showDescription ? 'Hide' : 'Show'} description
					</Button>
                {/if}
			</div>
			<div class="h-full flex mb-2 justify-around">   
                <!-- Collapsible description -->
                {#if showDescription && mapDescription}
                    <div class="text-sm" 
                         style="white-space: pre-wrap; max-height: 200px; overflow-y: auto;">
                        {mapDescription}
                    </div>
                {/if}
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
