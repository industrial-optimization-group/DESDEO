<script lang="ts">
	/**
	 * EndStateView Component
	 *
	 * Displays the final state of the GNIMBUS optimization process,
	 * showing both objective values and decision variables.
	 * Includes functionality to export results in CSV format.
	 *
	 * @component
	 * @author Stina Palomäki <palomakistina@gmail.com>
	 * @created October 2025
	 */
	import FinalResultTable from '$lib/components/custom/nimbus/final-result-table.svelte';
	import Button from '$lib/components/ui/button/button.svelte';
	import type { ProblemInfo, TableData } from '../types';

	let {
		problem,
		tableData,
		showVariables = false
	}: {
		problem: ProblemInfo;
		tableData: TableData[]; // Array of solutions
		showVariables?: boolean;
	} = $props();

	/**
	 * Prepares CSV content for a single solution
	 * Formats objective values and optionally decision variables based on showVariables prop
	 *
	 * @param solution The solution data to format
	 * @returns Formatted CSV string or null if problem is not defined
	 */
	function prepareSolutionCSV(solution: TableData) {
		if (!problem) return null;

		// Prepare objectives table
		const objectiveSection = [
			'Objectives', // Title for objectives section
			problem.objectives.map((obj) => obj.unit ? `${obj.name} / ${obj.unit}` : obj.name).join(','), // Objective names with units
			problem.objectives.map((obj) => solution.objective_values?.[obj.symbol] ?? '').join(',') // Objective values
		];

		// Only include variables section if showVariables is true
		if (showVariables && problem.variables && problem.variables.length > 0) {
			// Add blank line between sections
			const separator = '';

			// Prepare variables table
			const variableSection = [
				'Variables', // Title for variables section
				problem.variables.map((v) => v.name).join(','), // Variable names
				problem.variables.map((v) => solution.variable_values?.[v.symbol] ?? '').join(',') // Variable values
			];

			// Combine sections with blank line separator
			return [...objectiveSection, separator, ...variableSection].join('\n');
		}

		// Return only objectives section if variables are not shown
		return objectiveSection.join('\n');
	}

	/**
	 * Triggers download of a CSV file in the browser
	 *
	 * @param content CSV content to download
	 * @param filename Name for the downloaded file
	 */
	function downloadCSV(content: string, filename: string) {
		const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' });
		const link = document.createElement('a');

		// Create a URL for the blob
		const url = URL.createObjectURL(blob);

		link.setAttribute('href', url);
		link.setAttribute('download', filename);
		link.style.visibility = 'hidden';

		document.body.appendChild(link);
		link.click();
		document.body.removeChild(link);
		URL.revokeObjectURL(url);
	}

	/**
	 * Handles the download of all solutions as CSV files
	 * Generates a separate file for each solution with a timestamp
	 */
	function handleDownload() {
		if (!problem || !tableData || tableData.length === 0) return;

		const timestamp = new Date().toISOString().replace(/[:.]/g, '-');

		// Download each solution as a separate CSV file
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
			title="Final Solution"
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
