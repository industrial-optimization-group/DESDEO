<script module>
	import { defineMeta } from '@storybook/addon-svelte-csf';
	import { ChernoffFace } from '$lib/components/visualizations/chernoff-face';

	const { Story } = defineMeta({
		title: 'Example/ChernoffFace',
		component: ChernoffFace,
		tags: ['autodocs'],
		argTypes: {
			data: { control: 'object' },
			options: { control: 'object' }
		},
		args: {
			data: [
				{ name: 'Objective 1', value: 0.5 },
				{ name: 'Objective 2', value: 0.5 },
				{ name: 'Objective 3', value: 0.5 },
				{ name: 'Objective 4', value: 0.5 },
				{ name: 'Objective 5', value: 0.5 }
			],
			options: {
				showLabels: false
			}
		}
	});
</script>

<Story name="Default" />
