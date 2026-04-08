<script lang="ts">
	import FinalResultTable from '$lib/components/custom/nimbus/final-result-table.svelte';
	import Button from '$lib/components/ui/button/button.svelte';
	import type { ProblemInfo } from '$lib/gen/endpoints/DESDEOFastAPI';

	interface SolutionData {
		objective_values: { [key: string]: number } | null;
		variable_values?: { [key: string]: number | boolean | unknown } | null;
		name?: string | null;
		solution_index?: number | null;
	}

	let {
		problem,
		tableData,
		showVariables = false,
		title = 'Final Solution'
	}: {
		problem: ProblemInfo;
		tableData: SolutionData[];
		showVariables?: boolean;
		title?: string;
	} = $props();

	function prepareSolutionCSV(solution: SolutionData) {
		if (!problem) return null;

		const objectiveSection = [
			'Objectives',
			problem.objectives
				.map((obj) => (obj.unit ? `${obj.name} / ${obj.unit}` : obj.name))
				.join(','),
			problem.objectives.map((obj) => solution.objective_values?.[obj.symbol] ?? '').join(',')
		];

		if (showVariables && solution.variable_values && Object.keys(solution.variable_values).length > 0) {
			const varKeys = Object.keys(solution.variable_values);
			const varLookup = new Map<string, string>();
			for (const v of problem.variables ?? []) varLookup.set(v.symbol, v.name);
			for (const tv of problem.tensor_variables ?? []) varLookup.set(tv.symbol, tv.name);

			const separator = '';
			const variableSection = [
				'Variables',
				varKeys.map((k) => varLookup.get(k) ?? k).join(','),
				varKeys.map((k) => solution.variable_values![k] ?? '').join(',')
			];
			return [...objectiveSection, separator, ...variableSection].join('\n');
		}

		return objectiveSection.join('\n');
	}

	function downloadCSV(content: string, filename: string) {
		const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' });
		const link = document.createElement('a');
		const url = URL.createObjectURL(blob);
		link.setAttribute('href', url);
		link.setAttribute('download', filename);
		link.style.visibility = 'hidden';
		document.body.appendChild(link);
		link.click();
		document.body.removeChild(link);
		URL.revokeObjectURL(url);
	}

	function handleDownload() {
		if (!problem || !tableData || tableData.length === 0) return;

		const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
		tableData.forEach((solution, index) => {
			const csvContent = prepareSolutionCSV(solution);
			if (csvContent) {
				downloadCSV(csvContent, `solution_${index + 1}_${timestamp}.csv`);
			}
		});
	}
</script>

<div class="flex h-full flex-col gap-4">
	<div class="min-h-0 flex-1">
		<FinalResultTable
			{problem}
			solverResults={tableData}
			mode="objectives"
			{title}
		/>
	</div>

	{#if showVariables}
		<div class="min-h-0 flex-1">
			<FinalResultTable
				{problem}
				solverResults={tableData}
				mode="variables"
				title="Decision Variables"
			/>
		</div>
	{/if}

	<div class="flex-none">
		<Button onclick={handleDownload}>Download Results as CSV</Button>
	</div>
</div>
