<script lang="ts">
	import { onMount } from 'svelte';
	import type { SolverResults } from '$lib/gen/models';
	import { buildMapSiteSelectionMapPost } from '$lib/gen/endpoints/DESDEOFastAPI';

	interface SiteSelectionMapNode {
		name: string;
		lat: number;
		lon: number;
		size: number;
		color: string;
		tooltip: string;
	}

	interface SiteSelectionMapEdge {
		from_lat: number;
		from_lon: number;
		to_lat: number;
		to_lon: number;
	}

	interface SiteSelectionMapResponse {
		nodes: SiteSelectionMapNode[];
		edges: SiteSelectionMapEdge[];
		center: [number, number];
	}

	interface Props {
		problem_id: number;
		solution: SolverResults;
	}

	let { problem_id, solution }: Props = $props();

	let mapContainer = $state<HTMLDivElement>();
	let map: L.Map | null = null;
	let loading = $state(true);
	let error = $state<string | null>(null);

	async function fetchMapData(): Promise<SiteSelectionMapResponse> {
		const res = await buildMapSiteSelectionMapPost({
			problem_id,
			optimal_variables: solution.optimal_variables as Record<string, unknown>
		});
		if (res.status === 404) {
			throw new Error('No site selection map metadata configured for this problem.');
		}
		if (res.status !== 200) {
			throw new Error(`Map API error: ${res.status}`);
		}
		return res.data as SiteSelectionMapResponse;
	}

	async function renderMap(data: SiteSelectionMapResponse) {
		const L = await import('leaflet');

		if (map) {
			map.remove();
			map = null;
		}

		map = L.map(mapContainer!, {
			center: data.center as [number, number],
			zoom: 9
		});

		L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
			attribution:
				'&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',
			subdomains: 'abcd',
			maxZoom: 19
		}).addTo(map);

		// Draw coverage edges
		for (const edge of data.edges) {
			L.polyline(
				[
					[edge.from_lat, edge.from_lon],
					[edge.to_lat, edge.to_lon]
				],
				{ color: 'black', weight: 1.5, opacity: 0.5 }
			).addTo(map);
		}

		// Draw node markers
		const bounds: L.LatLngExpression[] = [];
		for (const node of data.nodes) {
			const marker = L.circleMarker([node.lat, node.lon], {
				radius: node.size,
				color: 'black',
				weight: 1,
				fillColor: node.color,
				fillOpacity: 0.7
			}).addTo(map);

			marker.bindTooltip(node.tooltip, { direction: 'top', offset: [0, -5] });
			bounds.push([node.lat, node.lon]);
		}

		if (bounds.length > 0) {
			map.fitBounds(L.latLngBounds(bounds), { padding: [20, 20] });
		}

		// Legend
		const legend = new L.Control({ position: 'bottomright' });
		legend.onAdd = () => {
			const div = L.DomUtil.create('div', 'leaflet-legend');
			div.innerHTML = `
				<div style="background:white; padding:8px 12px; border-radius:6px; box-shadow:0 1px 4px rgba(0,0,0,.3); font-size:12px; line-height:20px;">
					<div style="font-weight:600; margin-bottom:4px;">Legend</div>
					<div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#FFA500;border:1px solid black;vertical-align:middle;margin-right:6px;"></span>Has active sites</div>
					<div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#FFFF00;border:1px solid black;vertical-align:middle;margin-right:6px;"></span>Covered by nearby sites</div>
					<div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#808080;border:1px solid black;vertical-align:middle;margin-right:6px;"></span>Not covered</div>
					<div style="margin-top:4px;"><span style="display:inline-block;width:20px;height:2px;background:black;vertical-align:middle;margin-right:6px;"></span>Coverage link</div>
				</div>`;
			return div;
		};
		legend.addTo(map);
	}

	async function loadMap() {
		loading = true;
		error = null;
		try {
			const data = await fetchMapData();
			await renderMap(data);
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
			console.error('Site selection map error:', e);
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		loadMap();
		return () => {
			if (map) {
				map.remove();
				map = null;
			}
		};
	});

	$effect(() => {
		// Re-render when solution changes (after initial mount)
		if (solution && mapContainer) {
			loadMap();
		}
	});
</script>

<svelte:head>
	<link
		rel="stylesheet"
		href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
		integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
		crossorigin=""
	/>
</svelte:head>

<div class="relative h-full w-full">
	{#if loading}
		<div class="flex h-full items-center justify-center text-sm text-gray-400">
			Loading map...
		</div>
	{/if}
	{#if error}
		<div class="flex h-full items-center justify-center text-sm text-red-400">
			{error}
		</div>
	{/if}
	<div bind:this={mapContainer} class="h-full w-full" class:invisible={loading || !!error}></div>
</div>
