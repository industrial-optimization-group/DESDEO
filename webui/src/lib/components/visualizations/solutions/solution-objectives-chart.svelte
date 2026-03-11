<script lang="ts">
    import { COLOR_PALETTE } from '../utils/colors';

    type SolutionDatum = { name: string; value: number; direction?: 'max' | 'min' };
    type Props = { data?: SolutionDatum[] };

    let { data = [] }: Props = $props();

    const hasNegative = $derived.by(() => data.some((item) => item.value < 0));
    const hasPositive = $derived.by(() => data.some((item) => item.value > 0));
    const maxAbsValue = $derived.by(() => Math.max(1, ...data.map((item) => Math.abs(item.value))));

    // Place the zero baseline based on sign distribution.
    const zeroPosition = $derived.by(() => {
        if (hasNegative && hasPositive) return 50;
        if (hasNegative) return 100;
        return 0;
    });

    function getBarStyle(value: number, baseline: number, maxAbs: number): string {
        const ratio = Math.abs(value) / maxAbs;

        if (value >= 0) {
            const width = ratio * (100 - baseline);
            return `left: ${baseline}%; width: ${width}%;`;
        }

        const width = ratio * baseline;
        return `left: ${baseline - width}%; width: ${width}%;`;
    }

    function getObjectiveColor(index: number): string {
        return COLOR_PALETTE[index % COLOR_PALETTE.length];
    }
</script>

<div class="space-y-3">
    {#if data.length === 0}
        <p class="text-sm text-gray-500">No objective values available.</p>
    {:else}
        {#each data as item, idx}
            <div class="space-y-1">
                <div class="flex items-center justify-between gap-2 text-xs text-gray-600">
                    <span class="truncate">{item.name}</span>
                    <span class="font-medium text-gray-700">{item.value.toFixed(4)}</span>
                </div>
                <div class="relative h-6 overflow-hidden rounded bg-gray-100">
                    <div
                        class="absolute top-0 bottom-0 w-px bg-gray-400"
                        style={`left: ${zeroPosition}%;`}
                    ></div>
                    <div
                        class="absolute top-1 bottom-1 rounded"
                        style={`${getBarStyle(item.value, zeroPosition, maxAbsValue)} background-color: ${getObjectiveColor(idx)};`}
                    ></div>
                </div>
            </div>
        {/each}
    {/if}
</div>
