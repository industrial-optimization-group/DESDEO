<!-- 
  @component
  A Svelte component that renders an ECharts chart.
 -->
<script lang="ts">
    import type { EChartsOption, EChartsType } from 'echarts';
    import * as echarts from 'echarts';
    import { onMount } from 'svelte';
    
    let {
        colors = [],
        option,
        disableAnimation = true,
        aspect = undefined,
        geoJSON = undefined,
        mapName = undefined,
        customStyle = '',
        events = undefined
    }: {
        /** An array of colors (kind of a color palette) to use for the chart series. */
        colors?: string[];
        /** The ECharts chart options. */
        option: EChartsOption;
        /** Whether to disable animations on the chart. */
        disableAnimation?: boolean;
        /** The aspect ratio of the chart container. */
        aspect?: string | undefined;
        /** The GeoJSON data to use for the chart. */
        geoJSON?: Record<string, any> | undefined;
        /** The name of the map to use for the chart. */
        mapName?: string | undefined;
        /** Custom CSS styles to apply to the chart container. */
        customStyle?: string;
        /**
         * Event handlers for the chart events.
         */
        events?: {
            [key: string]: (params: {
                dataIndex: number;
                componentType: string;
                seriesIndex: number;
                intervals: number[][];
                data: { value: number[] };
            }) => void;
        };
    } = $props();

    /** The ECharts instance used to render the chart. */
    let chart: EChartsType | undefined = $state(undefined);
    // Make chart accessible to parent components
    export { chart };

    let chartDiv: HTMLDivElement;

    // Attach the given event handlers to the chart instance when either changes
    $effect(() => {
        if (events && chart) {
            for (const [eventName, eventHandler] of Object.entries(events)) {
                chart.on(eventName, (...args: unknown[]) => {
                    // Cast args[0] to the expected params type
                    eventHandler(args[0] as {
                        dataIndex: number;
                        componentType: string;
                        seriesIndex: number;
                        intervals: number[][];
                        data: { value: number[] };
                    });
                });
            }
        }
    });

    onMount(() => {
        if (!chart) {
            chart = echarts.init(chartDiv, '', { renderer: 'svg' });

            // Register map if GeoJSON and mapName are provided
        if (geoJSON !== undefined && mapName !== undefined) {
            echarts.registerMap(mapName, { geoJSON: geoJSON } as any);
        }

            // Apply initial options
            chart.setOption(option);

            // Apply animation settings and colors
            if (disableAnimation) {
                chart.setOption({
                    color: colors,
                    // @ts-ignore -- Type issue with colorBy in ECharts types
                    colorBy: 'data',
                    animation: !disableAnimation
                });
            } else {
                // Define default emphasis styles directly without using highlightedStyle
                const defaultEmphasisStyles = {
                    color: '#1e88e5',  // A default blue color
                    opacity: 0.8,
                    width: 2
                };

                chart.setOption({
                    color: colors,
                    // @ts-ignore -- Type issue with colorBy in ECharts types
                    colorBy: 'data',
                    animation: !disableAnimation,
                    series: [
                        {
                            type: '',
                            emphasis: {
                                itemStyle: {
                                    color: defaultEmphasisStyles.color,
                                    opacity: defaultEmphasisStyles.opacity
                                },
                                lineStyle: {
                                    color: defaultEmphasisStyles.color,
                                    width: defaultEmphasisStyles.width,
                                    opacity: defaultEmphasisStyles.opacity
                                }
                            }
                        }
                    ]
                });
            }
        } else {
            chart.resize();
        }

        // Add resize listener to make chart responsive
        const resizeObserver = new ResizeObserver(() => {
            if (chart) chart.resize();
        });

        resizeObserver.observe(chartDiv);

        return () => {
            resizeObserver.disconnect();
            if (chart) chart.dispose();
        };
    });

    // Update chart when option changes
    $effect(() => {
        if (chart && option) {
            chart.setOption(option);
        }
    });
</script>

<div class={aspect} style="height: 100%; width: 100%; {customStyle};" bind:this={chartDiv} ></div>
