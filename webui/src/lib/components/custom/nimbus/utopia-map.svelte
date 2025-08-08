<script lang="ts">
	import { ToggleGroup, ToggleGroupItem } from '$lib/components/ui/toggle-group';
	import EchartsComponent from '$lib/components/custom/nimbus/echarts-component.svelte';

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
</script>

<div class="overflow-auto h-full flex-1">
	<div class="flex-1">
		{#if mapOptions[selectedPeriod] && Object.keys(mapOptions[selectedPeriod]).length > 0 && geoJSON}
			<div class="flex">
				<!-- Period selection toggle -->
				<div>
					<h3 class="text-lg">{mapName || 'Forest Map'}</h3>
					<ToggleGroup type="single" bind:value={selectedPeriod}>
						{#each yearlist as year, i}
							<ToggleGroupItem value={`period${i+1}`}>
								{year || `Period ${i+1}`}
							</ToggleGroupItem>
						{/each}
					</ToggleGroup>
					<div class="text-sm" style="white-space: pre-wrap;">{mapDescription}</div>
				</div>
				<!-- The actual map visualization -->
				<EchartsComponent
					option={mapOptions[selectedPeriod]}
					{geoJSON}
					{mapName}
					customStyle="height: 400px; "
				/>
			</div>
		{:else}
			<div class="placeholder">
				<p>Select a solution to view the map visualization</p>
			</div>
		{/if}
	</div>
</div>