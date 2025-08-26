<script lang="ts">
	/**
	 * Segmented Control Component
	 * 
	 * @author Stina Palomäki <palomakistina@gmail.com>
	 * @created August 2025
	 * 
	 * @description
	 * A segmented control (toggle button group) component built on top of RadioGroup.
	 * Provides a horizontal set of mutually exclusive options presented as connected segments.
	 * Used for view switching, mode selection, or filtering options.
	 * 
	 * @props
	 * @property {string} [class] - Optional CSS class to apply to the outer container
	 * @property {SegmentOption[]} options - Array of options to display in the control
	 * @property {string} [value] - Currently selected value, bindable with Svelte runes
	 * @property {string} [size='default'] - Size variant ('default', 'sm', 'lg')
	 * @property {any} [...restProps] - Any additional props are passed to the RadioGroup component
	 * 
	 * @interface SegmentOption
	 * @property {string} value - The unique value of this option
	 * @property {string} label - The display label for this option
	 * 
	 * @example
	 * ```svelte
	 * <SegmentedControl
	 *   bind:value={selectedView}
	 *   options={[
	 *     { value: 'daily', label: 'Daily' },
	 *     { value: 'weekly', label: 'Weekly' },
	 *     { value: 'monthly', label: 'Monthly' }
	 *   ]}
	 *   size="sm"
	 *   class="mb-4"
	 * />
	 * ```
	 * 
	 * @styles
	 * - Provides three size variants: 'default', 'sm' (small), 'lg' (large)
	 * - Applies rounded corners to the first and last items
	 * - Highlights the selected option with accent background and text colors
	 * - Uses hover states for better user interaction feedback
	 * 
	 * @dependencies
	 * - $lib/components/ui/radio-group - Base RadioGroup component
	 * - $lib/utils.js - Utility functions, specifically cn() for class name generation
	 */
	import { RadioGroup } from '$lib/components/ui/radio-group';
	import { RadioGroupItem } from '$lib/components/ui/radio-group';
	import { cn } from '$lib/utils.js';
	
	export interface SegmentOption {
		value: string;
		label: string;
	}

	let {
		class: className,
		options = [],
		value = $bindable(''),
		size = 'default',
		...restProps
	}: {
		class?: string;
		options: SegmentOption[];
		value?: string;
		size?: 'default' | 'sm' | 'lg';
	} = $props();
	
	const sizeClasses = {
		default: 'py-2 px-4 text-sm',
		sm: 'py-1 px-3 text-xs',
		lg: 'py-2.5 px-5 text-base'
	};
</script>

<div class={cn("rounded-md", className)}>
	<RadioGroup
		bind:value
		class="inline-flex rounded-md gap-0 border shadow-sm overflow-hidden"
		{...restProps}
	>
		{#each options as option, i}
			<div class="group">
				<RadioGroupItem 
					value={option.value} 
					id={`option-${option.value}-${i}`} 
					class="peer sr-only"
				/>
				<label
					for={`option-${option.value}-${i}`}
					class={cn(
						"relative inline-flex items-center justify-center whitespace-nowrap transition-colors",
						"cursor-pointer hover:bg-muted/20",
						"border-r border-muted last:border-r-0",
						"peer-data-[state=checked]:bg-accent peer-data-[state=checked]:text-accent-foreground",
						"peer-data-[state=checked]:hover:bg-accent/90",
						i === 0 && "rounded-l-md",
						i === options.length - 1 && "rounded-r-md",
						sizeClasses[size]
					)}
				>
					{option.label}
				</label>
			</div>
		{/each}
	</RadioGroup>
</div>
