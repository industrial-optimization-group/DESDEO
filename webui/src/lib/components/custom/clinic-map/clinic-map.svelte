<script lang="ts">
	import { onMount } from 'svelte';
	import type { SolverResults } from '$lib/gen/models';

	const API_URL = import.meta.env.VITE_API_URL;

	interface ClinicMapCity {
		city: string;
		lat: number;
		lon: number;
		size: number;
		color: string;
		tooltip: string;
	}

	interface ClinicMapLine {
		from_lat: number;
		from_lon: number;
		to_lat: number;
		to_lon: number;
	}

	interface ClinicMapResponse {
		cities: ClinicMapCity[];
		lines: ClinicMapLine[];
		center: [number, number];
	}

	interface Props {
		solution: SolverResults;
	}

	let { solution }: Props = $props();

	let mapContainer: HTMLDivElement;
	let map: L.Map | null = null;
	let loading = $state(true);
	let error = $state<string | null>(null);

	function extractVectors(sol: SolverResults): { sv: number[]; cover: number[] } {
		const vars = sol.optimal_variables as Record<string, number | number[]>;
		const sv: number[] = [];
		const cover: number[] = [];

		for (let i = 1; i <= 60; i++) {
			const key = `sv_${i}`;
			const val = vars[key];
			sv.push(Array.isArray(val) ? val[0] : (val as number));
		}
		for (let i = 1; i <= 36; i++) {
			const key = `cover_${i}`;
			const val = vars[key];
			cover.push(Array.isArray(val) ? val[0] : (val as number));
		}
		return { sv, cover };
	}

	async function fetchMapData(sv: number[], cover: number[]): Promise<ClinicMapResponse> {
		const res = await fetch(`${API_URL}/clinic/map`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			credentials: 'include',
			body: JSON.stringify({ sv, cover })
		});
		if (!res.ok) {
			throw new Error(`Map API error: ${res.status}`);
		}
		return res.json();
	}

	async function renderMap(data: ClinicMapResponse) {
		const L = await import('leaflet');

		if (map) {
			map.remove();
			map = null;
		}

		map = L.map(mapContainer, {
			center: data.center as [number, number],
			zoom: 9
		});

		L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
			attribution:
				'&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',
			subdomains: 'abcd',
			maxZoom: 19
		}).addTo(map);

		// Draw coverage lines
		for (const line of data.lines) {
			L.polyline(
				[
					[line.from_lat, line.from_lon],
					[line.to_lat, line.to_lon]
				],
				{ color: 'black', weight: 1.5, opacity: 0.5 }
			).addTo(map);
		}

		// Draw city markers
		const bounds: L.LatLngExpression[] = [];
		for (const city of data.cities) {
			const marker = L.circleMarker([city.lat, city.lon], {
				radius: city.size,
				color: 'black',
				weight: 1,
				fillColor: city.color,
				fillOpacity: 0.7
			}).addTo(map);

			marker.bindTooltip(city.tooltip, { direction: 'top', offset: [0, -5] });
			bounds.push([city.lat, city.lon]);
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
					<div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:orange;border:1px solid black;vertical-align:middle;margin-right:6px;"></span>Has clinic events</div>
					<div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:yellow;border:1px solid black;vertical-align:middle;margin-right:6px;"></span>Covered by nearby events</div>
					<div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:grey;border:1px solid black;vertical-align:middle;margin-right:6px;"></span>Not covered</div>
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
			const { sv, cover } = extractVectors(solution);
			const data = await fetchMapData(sv, cover);
			await renderMap(data);
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
			console.error('Clinic map error:', e);
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
