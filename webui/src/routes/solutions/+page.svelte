<script lang="ts">
    import { Topbar } from '$lib/components/ui/topbar';
    import SolutionObjectivesChart from '$lib/components/visualizations/solutions/solution-objectives-chart.svelte';
    import { Button } from '$lib/components/ui/button';
    import type { PageProps } from './$types';
    import { api } from '$lib/api/client';

    let { data }: PageProps = $props();

    // Build a dictionary of objective symbol -> display name.
    function getObjectiveNameMap(objectives: Array<{ symbol: string; name?: string | null }> | undefined) {
        if (!objectives) return {};
        return objectives.reduce<Record<string, string>>((acc, objective) => {
            acc[objective.symbol] = objective.name ?? objective.symbol;
            return acc;
        }, {});
    }

    // Transform API response to barchart data format
    function transformToChartData(
        objectives: Record<string, number> | undefined,
        objectiveNameBySymbol: Record<string, string>
    ) {
        if (!objectives) return [];
        return Object.entries(objectives).map(([symbol, value]) => ({
            name: objectiveNameBySymbol[symbol] ?? symbol,
            value,
            direction: 'min' as const
        }));
    }

    const objectiveNameBySymbol = $derived.by(() =>
        getObjectiveNameMap(data.problemInfo?.objectives)
    );

    // Use $derived.by so values react to data updates.
    const nimbusData = $derived.by(() =>
        transformToChartData(
            data.solutions?.nimbus_final?.objective_values ?? undefined,
            objectiveNameBySymbol
        )
    );
    const xnimbusData = $derived.by(() =>
        transformToChartData(
            data.solutions?.xnimbus_final?.objective_values ?? undefined,
            objectiveNameBySymbol
        )
    );
    // Randomize solution order and assign labels
    let randomOrder = Math.random() < 0.5;
    
    const solutions = $derived.by(() => {
        const nimbus = {
            label: 'Vega Solution',
            methodName: 'NIMBUS',
            data: nimbusData,
            objectives: data.solutions?.nimbus_final?.objective_values,
            stateId: data.solutions?.nimbus_final?.state_id
        };
        
        const xnimbus = {
            label: 'Polaris Solution',
            methodName: 'XNIMBUS',
            data: xnimbusData,
            objectives: data.solutions?.xnimbus_final?.objective_values,
            stateId: data.solutions?.xnimbus_final?.state_id
        };
        
        return randomOrder ? [nimbus, xnimbus] : [xnimbus, nimbus];
    });

    // User preference tracking
    let selectedSolution = $state<string | null>(null);
    let submitting = $state(false);
    let submitSuccess = $state(false);
    let submitError = $state<string | null>(null);


    async function submitPreference() {
        if (!selectedSolution) return;

        const preferredSolution = solutions.find(s => s.label === selectedSolution);
        if (!preferredSolution) return;

        submitting = true;
        submitError = null;

        try {
            const response = await api.POST('/method/generic/save-method-preference', {
                body: {
                    preferred_method: preferredSolution.methodName
                }
            });

            if (response.error) {
                const errorDetail = Array.isArray(response.error.detail)
                    ? response.error.detail.map(e => e.msg).join(', ')
                    : response.error.detail || 'Failed to save preference';
                throw new Error(errorDetail);
            }
            
            submitSuccess = true;
        } catch (error) {
            submitError = `Failed to submit preference: ${error}`;
        } finally {
            submitting = false;
        }
    }
</script>

<div class="flex min-h-screen w-full flex-col">
    <Topbar />
    <main class="flex flex-1 flex-col gap-4 p-4 md:gap-8 md:p-8">
        <div class="mx-auto w-full max-w-6xl space-y-6">
            <h1 class="text-2xl font-semibold text-gray-800 md:text-3xl">
                Solutions
            </h1>
            <p class="text-md text-justify text-gray-700">
                Here you can see the solutions obtained from the NIMBUS and explainable NIMBUS methods. The solutions are presented in random order and with a random name to avoid any bias. 
            </p>

            {#if data.error}
                <div class="rounded-lg bg-red-50 p-4 text-red-700">
                    <p>Error: {data.error}</p>
                </div>
            {:else if data.solutions === null}
                <div class="rounded-lg bg-yellow-50 p-4 text-yellow-700">
                    <p>No solutions found for this problem.</p>
                </div>
            {:else if nimbusData.length === 0 && xnimbusData.length === 0}
                <div class="rounded-lg bg-yellow-50 p-4 text-yellow-700">
                    <p>No final solutions available yet.</p>
                </div>
            {:else}
                <div class="grid grid-cols-1 gap-8 md:grid-cols-2">
                    {#each solutions as solution}
                        {#if solution.data.length > 0}
                            <div class="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
                                <h2 class="text-lg font-semibold text-gray-800">{solution.label}</h2>
                                <div class="w-full">
                                    <SolutionObjectivesChart
                                        data={solution.data}
                                    />
                                </div>
                                <div class="space-y-2 border-t border-gray-100 pt-4">
                                    <!-- <p class="text-sm font-medium text-gray-600">State ID: {solution.stateId}</p> -->
                                    <div>
                                        <div class="overflow-x-auto">
                                            <table class="w-full text-sm">
                                                <thead class="border-b border-gray-200">
                                                    <tr>
                                                        <th class="text-left text-gray-600">Objective</th>
                                                        <th class="text-right text-gray-600">Value</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {#each Object.entries(solution.objectives || {}) as [objSymbol, objValue]}
                                                        <tr class="border-b border-gray-100">
                                                            <td class="py-2 text-gray-700">{objectiveNameBySymbol[objSymbol] ?? objSymbol}</td>
                                                            <td class="py-2 text-right text-gray-700">
                                                                {typeof objValue === 'number' ? objValue.toFixed(4) : objValue}
                                                            </td>
                                                        </tr>
                                                    {/each}
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        {/if}
                    {/each}
                </div>

                <!-- Preference Selection - Only show if both solutions are available -->
                {#if nimbusData.length > 0 && xnimbusData.length > 0}
                    <div class="mt-8 rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
                        <h2 class="mb-4 text-xl font-semibold text-gray-800">Which solution do you prefer?</h2>
                        <p class="mb-4 text-sm text-gray-600">
                            Please select the solution you find most suitable for the problem.
                        </p>
                        
                        <div class="space-y-3">
                            {#each solutions as solution}
                                {#if solution.data.length > 0}
                                    <label class="flex items-center space-x-3 cursor-pointer rounded-lg border border-gray-200 p-4 transition-all hover:bg-gray-50 
                                        {selectedSolution === solution.label ? 'border-blue-500 bg-blue-50' : ''}">
                                        <input 
                                            type="radio" 
                                            name="solution-preference" 
                                            value={solution.label}
                                            bind:group={selectedSolution}
                                            class="h-4 w-4 text-blue-600"
                                        />
                                        <span class="font-medium text-gray-700">{solution.label}</span>
                                    </label>
                                {/if}
                            {/each}
                        </div>

                        <div class="mt-6 flex items-center gap-4">
                            <Button 
                                onclick={submitPreference}
                                disabled={!selectedSolution || submitting || submitSuccess}
                                class="min-w-32"
                            >
                                {submitting ? 'Submitting...' : submitSuccess ? 'Submitted ✓' : 'Submit Preference'}
                            </Button>

                            {#if submitSuccess}
                                <p class="text-sm text-green-600">
                                    Thank you! Your preference has been recorded.
                                </p>
                            {/if}

                            {#if submitError}
                                <p class="text-sm text-red-600">
                                    {submitError}
                                </p>
                            {/if}
                        </div>
                    </div>
                {:else}
                    <div class="mt-8 rounded-lg border border-yellow-200 bg-yellow-50 p-6">
                        <p class="text-sm text-yellow-800">
                            Preference voting is only available when both NIMBUS and Explainable NIMBUS solutions are available.
                        </p>
                    </div>
                {/if}
            {/if}
        </div>
    </main>
</div>