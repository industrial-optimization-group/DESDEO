<script lang="ts">
	import { onMount } from 'svelte';
	import * as d3 from 'd3';

	// Now data is an array of objects: { name: string, value: number }
	export let data: { name: string; value: number }[] = [];
	export let options: { showLabels: boolean } = { showLabels: true };

	let container: HTMLDivElement;
	const MAX_OBJECTIVES = 5;

	const features: Record<string, number> = {
		faceWidth: 0,
		eyeSize: 1,
		mouthCurve: 2,
		browSlant: 3,
		noseLength: 4
	};

	const isValid = () => data.length <= MAX_OBJECTIVES;

	function drawChart() {
		if (!isValid()) {
			console.error('Invalid data: must have at most 5 objectives');
			return;
		}
		d3.select(container).selectAll('svg').remove();

		const width = 200;
		const height = width * 1.2; // Keep aspect ratio
		const centerX = width / 2;
		const centerY = height / 2;

		const svg = d3.select(container).append('svg').attr('width', width).attr('height', height);

		// Extract values for features in order
		const values = [
			data[features.faceWidth]?.value ?? 0.5,
			data[features.eyeSize]?.value ?? 0.5,
			data[features.mouthCurve]?.value ?? 0.5,
			data[features.browSlant]?.value ?? 0.5,
			data[features.noseLength]?.value ?? 0.5
		];

		// All features are now relative to width
		const faceWidth = d3
			.scaleLinear()
			.domain([0, 1])
			.range([0.3 * width, 0.6 * width])(values[0]);
		const faceHeight = 0.7 * width;
		const eyeSize = d3
			.scaleLinear()
			.domain([0, 1])
			.range([0.03 * width, 0.09 * width])(values[1]);
		const mouthCurve = d3
			.scaleLinear()
			.domain([0, 1])
			.range([-0.1 * width, 0.1 * width])(values[2]);
		const browSlant = d3
			.scaleLinear()
			.domain([0, 1])
			.range([-0.05 * width, 0.05 * width])(values[3]);
		const noseLength = d3
			.scaleLinear()
			.domain([0, 1])
			.range([0.1 * width, 0.25 * width])(values[4]);

		// Draw face
		svg
			.append('ellipse')
			.attr('cx', centerX)
			.attr('cy', centerY)
			.attr('rx', faceWidth / 2)
			.attr('ry', faceHeight / 2)
			.attr('fill', 'peachpuff')
			.attr('stroke', 'black');

		// Draw eyes
		const eyeY = centerY - 0.15 * width;
		const eyeOffsetX = faceWidth / 4;
		svg
			.append('circle')
			.attr('cx', centerX - eyeOffsetX)
			.attr('cy', eyeY)
			.attr('r', eyeSize)
			.attr('fill', 'black');
		svg
			.append('circle')
			.attr('cx', centerX + eyeOffsetX)
			.attr('cy', eyeY)
			.attr('r', eyeSize)
			.attr('fill', 'black');

		// Draw mouth
		const mouthY = centerY + 0.2 * width;
		const mouthWidth = faceWidth / 2;
		const mouthPath = d3.path();
		mouthPath.moveTo(centerX - mouthWidth / 2, mouthY);
		mouthPath.quadraticCurveTo(centerX, mouthY + mouthCurve, centerX + mouthWidth / 2, mouthY);
		svg
			.append('path')
			.attr('d', mouthPath.toString())
			.attr('fill', 'none')
			.attr('stroke', 'black')
			.attr('stroke-width', 2);

		// Draw nose
		const noseY1 = centerY;
		const noseY2 = centerY + noseLength / 2;
		svg
			.append('line')
			.attr('x1', centerX)
			.attr('y1', noseY1)
			.attr('x2', centerX)
			.attr('y2', noseY2)
			.attr('stroke', 'black')
			.attr('stroke-width', 2);

		// Draw brows
		const browY = eyeY - 0.08 * width;
		const browLength = 0.15 * width;
		svg
			.append('line')
			.attr('x1', centerX - eyeOffsetX - browLength / 2)
			.attr('y1', browY - browSlant)
			.attr('x2', centerX - eyeOffsetX + browLength / 2)
			.attr('y2', browY + browSlant)
			.attr('stroke', 'black')
			.attr('stroke-width', 2);
		svg
			.append('line')
			.attr('x1', centerX + eyeOffsetX - browLength / 2)
			.attr('y1', browY + browSlant)
			.attr('x2', centerX + eyeOffsetX + browLength / 2)
			.attr('y2', browY - browSlant)
			.attr('stroke', 'black')
			.attr('stroke-width', 2);

		// Add labels if enabled
		if (options.showLabels) {
			data.forEach((d, index) => {
				svg
					.append('text')
					.attr('x', 10)
					.attr('y', 20 + index * 20)
					.attr('fill', 'black')
					.text(`${d.name}: ${d.value}`);
			});
		}
	}

	onMount(drawChart);
	$: data, options, drawChart();
</script>

<div bind:this={container}></div>
