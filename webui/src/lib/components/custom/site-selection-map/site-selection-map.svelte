<script lang="ts">
	import { onMount } from 'svelte';
	import type { SolverResults, VariableFixing } from '$lib/gen/models';
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
		site_variable_symbols?: string[];
		site_node_names?: string[];
	}

	type ConstraintState = 'free' | 'restricted' | 'forced';

	interface Props {
		problem_id: number;
		solution: SolverResults;
		on_constraints_changed?: (fixings: VariableFixing[]) => void;
	}

	let { problem_id, solution, on_constraints_changed }: Props = $props();

	let mapContainer = $state<HTMLDivElement>();
	let map: L.Map | null = null;
	let loading = $state(true);
	let error = $state<string | null>(null);
	let mapData = $state<SiteSelectionMapResponse | null>(null);
	let constraintStates = $state<Map<string, ConstraintState>>(new Map());
	let markerLayer: L.LayerGroup | null = null;

	const COLOR_RESTRICTED = '#EF4444';
	const COLOR_FORCED = '#22C55E';

	let fixings = $derived.by(() => {
		const result: VariableFixing[] = [];
		for (const [symbol, state] of constraintStates) {
			if (state === 'restricted') {
				result.push({ variable_symbol: symbol, fixed_value: 0 });
			} else if (state === 'forced') {
				result.push({ variable_symbol: symbol, fixed_value: 1 });
			}
		}
		return result;
	});

	$effect(() => {
		if (on_constraints_changed) {
			on_constraints_changed(fixings);
		}
	});

	function cycleConstraint(symbols: string[]) {
		// All symbols for a node cycle together; use the first symbol's state as reference
		const current = constraintStates.get(symbols[0]) ?? 'free';
		const next: ConstraintState = current === 'free' ? 'restricted' : current === 'restricted' ? 'forced' : 'free';
		const newMap = new Map(constraintStates);
		for (const sym of symbols) {
			if (next === 'free') {
				newMap.delete(sym);
			} else {
				newMap.set(sym, next);
			}
		}
		constraintStates = newMap;
	}

	function getMarkerStyle(node: SiteSelectionMapNode, symbols: string[]): { fillColor: string; html: string } {
		if (symbols.length === 0) return { fillColor: node.color, html: '' };
		// Use the first symbol's state as the display state (all should be in sync)
		const state = constraintStates.get(symbols[0]);
		if (state === 'restricted') return { fillColor: COLOR_RESTRICTED, html: '✕' };
		if (state === 'forced') return { fillColor: COLOR_FORCED, html: '✓' };
		return { fillColor: node.color, html: '' };
	}

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

	function buildNodeToSymbols(data: SiteSelectionMapResponse): Map<string, string[]> {
		const map = new Map<string, string[]>();
		if (data.site_variable_symbols && data.site_node_names) {
			for (let i = 0; i < data.site_variable_symbols.length; i++) {
				const nodeName = data.site_node_names[i];
				const existing = map.get(nodeName);
				if (existing) {
					existing.push(data.site_variable_symbols[i]);
				} else {
					map.set(nodeName, [data.site_variable_symbols[i]]);
				}
			}
		}
		return map;
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

		markerLayer = L.layerGroup().addTo(map);
		updateMarkers(data, L);

		// Fit bounds
		const bounds: L.LatLngExpression[] = data.nodes.map(n => [n.lat, n.lon]);
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
					<div style="margin-top:4px;"><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:${COLOR_RESTRICTED};border:1px solid black;vertical-align:middle;margin-right:6px;"></span>Restricted (forced out)</div>
					<div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:${COLOR_FORCED};border:1px solid black;vertical-align:middle;margin-right:6px;"></span>Forced (forced in)</div>
					<div style="margin-top:4px;"><span style="display:inline-block;width:20px;height:2px;background:black;vertical-align:middle;margin-right:6px;"></span>Coverage link</div>
				</div>`;
			return div;
		};
		legend.addTo(map);
	}

	function updateMarkers(data: SiteSelectionMapResponse, L: typeof import('leaflet')) {
		if (!markerLayer) return;
		markerLayer.clearLayers();

		const nodeToSymbols = buildNodeToSymbols(data);

		for (const node of data.nodes) {
			const symbols = nodeToSymbols.get(node.name) ?? [];
			const style = getMarkerStyle(node, symbols);

			const marker = L.circleMarker([node.lat, node.lon], {
				radius: node.size,
				color: 'black',
				weight: 1,
				fillColor: style.fillColor,
				fillOpacity: 0.7
			});

			// Add constraint icon as a DivIcon overlay if constrained
			if (style.html) {
				const icon = L.divIcon({
					className: 'constraint-icon',
					html: `<span style="font-size:14px;font-weight:bold;color:white;text-shadow:0 0 3px black;">${style.html}</span>`,
					iconSize: [20, 20],
					iconAnchor: [10, 10],
				});
				L.marker([node.lat, node.lon], { icon, interactive: false }).addTo(markerLayer!);
			}

			const state = symbols.length > 0 ? (constraintStates.get(symbols[0]) ?? 'free') : undefined;
			const stateLabel = state === 'restricted' ? ' [RESTRICTED]' : state === 'forced' ? ' [FORCED]' : '';
			marker.bindTooltip(node.tooltip + (stateLabel ? `<br><b>${stateLabel}</b>` : ''), { direction: 'top', offset: [0, -5] });

			if (symbols.length > 0) {
				marker.on('click', () => cycleConstraint(symbols));
				marker.getElement?.()?.style.setProperty('cursor', 'pointer');
			}

			marker.addTo(markerLayer!);
		}
	}

	// Re-render markers when constraint states change
	$effect(() => {
		// Read constraintStates to create dependency
		const _states = constraintStates;
		if (mapData && markerLayer) {
			import('leaflet').then(L => updateMarkers(mapData!, L));
		}
	});

	async function loadMap() {
		loading = true;
		error = null;
		try {
			const data = await fetchMapData();
			mapData = data;
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
		if (solution && mapContainer) {
			loadMap();
		}
	});

	export function clearConstraints() {
		constraintStates = new Map();
	}
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
