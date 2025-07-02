<script module>
	import { defineMeta } from '@storybook/addon-svelte-csf';
	import { HorizontalBar } from '$lib/components/visualizations/horizontal-bar';
	import { action } from '@storybook/addon-actions';

	let selected = 70;

	const { Story } = defineMeta({
		title: 'Example/HorizontalBar',
		component: HorizontalBar,
		tags: ['autodocs'],
		argTypes: {
			axisRanges: { control: 'object' },
			solutionValue: { control: 'number' },
			selectedValue: { control: 'number' },
			previousValue: { control: 'number' },
			barColor: { control: 'color' },
			options: {
				barHeight: { control: 'number' },
				decimalPrecision: { control: 'number' },
				showPreviousValue: { control: 'boolean' },
				aspectRatio: { control: 'text' }
			}
		},
		args: {
			axisRanges: [0, 100],
			solutionValue: 60,
			selectedValue: selected,
			previousValue: 50,
			barColor: '#4f8cff',
			direction: 'min',
			options: {
				barHeight: 32,
				decimalPrecision: 2,
				showPreviousValue: true,
				aspectRatio: 'aspect-[11/2]'
			},
			onSelect: action('onSelect')
		}
	});
</script>

<Story name="Default" let:args>
	<p>Selected value: {args.selectedValue}</p>
</Story>
