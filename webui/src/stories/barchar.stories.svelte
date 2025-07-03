<script module>
	import { defineMeta } from '@storybook/addon-svelte-csf';
	import { Barchart } from '$lib/components/visualizations/barchart';

	const { Story } = defineMeta({
		title: 'Example/Barchart',
		component: Barchart,
		tags: ['autodocs'],
		argTypes: {
			data: { control: 'object' },
			options: { control: 'object' },
			axisRanges: { control: 'object' }
		},
		args: {
			data: [
				{ name: 'A', value: 30, direction: 'max' },
				{ name: 'B', value: 80, direction: 'max' },
				{ name: 'C', value: 45, direction: 'min' },
				{ name: 'D', value: 60, direction: 'max' },
				{ name: 'E', value: 20, direction: 'min' },
				{ name: 'F', value: 90, direction: 'max' }
			],
			options: {
				showLabels: true,
				orientation: 'horizontal'
			},
			// Example: different ranges for each bar
			axisRanges: [
				[0, 50], // A
				[50, 100], // B
				[40, 60], // C
				[50, 70], // D
				[10, 30], // E
				[80, 100] // F
			]
		}
	});
</script>

<Story name="Default" />

<Story
	name="Vertical"
	args={{
		options: {
			showLabels: true,
			orientation: 'vertical'
		},
		axisRanges: [
			[0, 50],
			[50, 100],
			[40, 60],
			[50, 70],
			[10, 30],
			[80, 100]
		]
	}}
/>
