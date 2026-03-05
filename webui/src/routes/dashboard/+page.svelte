<script lang="ts">
	import { Topbar } from '$lib/components/ui/topbar';
	import Method from '@lucide/svelte/icons/brain-circuit';
	import Problem from '@lucide/svelte/icons/puzzle';
	import Trees from '@lucide/svelte/icons/trees';
	import HelpCircle from '@lucide/svelte/icons/circle-help';
	import * as Card from '$lib/components/ui/card/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import ChartArea from '@lucide/svelte/icons/chart-area';
	import SquareFunction from '@lucide/svelte/icons/square-function';
	import type { components } from '$lib/api/client-types';

	import { methodSelection } from '../../stores/methodSelection';


	import { goto } from '$app/navigation';

	import type { PageProps } from './$types';
	type ProblemInfo = components['schemas']['ProblemInfo'];


	let { data }: PageProps = $props();
	let problemList = data.problemList;
	let selectedProblem = $state<ProblemInfo | undefined>(undefined);

	function goToDocumentation() {
		// Replace with the actual URL of your documentation
		const documentationUrl = 'https://desdeo.readthedocs.io/en/latest/';
		window.open(documentationUrl, '_blank');
	}
	function createCustomProblem() {
		goto('/problems/define');
	}
	function goToForestManagement() {
		goto('/interactive_methods/NIMBUS');
	}
	function goToOptimizationProblems() {
		goto('/problems');
	}
	function goToOptimizationMethods() {
		goto('/methods/initialize');
	}
	function goToScoreBands() {
		goto('/interactive_methods/SCORE-bands');
	}

	function goToExplainableNIMBUS() {
		// Get the first problem from the problem list
		const selectedProblem = problemList[0];
		// Set the selected problem in the store
		methodSelection.set(selectedProblem?.id ?? null, $methodSelection.selectedMethod); // Update method selection store with the selected problem ID
		goto('/interactive_methods/XNIMBUS');
	}
	function goToObtainedSolutions() {

		goto('/solutions');
	}
	function goToNIMBUS() {
		const selectedProblem = problemList[0];
		methodSelection.set(selectedProblem?.id ?? null, $methodSelection.selectedMethod); // Update method selection store with the selected problem ID
		goto('/interactive_methods/NIMBUS');
	}

</script>

<div class="flex min-h-screen w-full flex-col">
	<Topbar />

	<main class="mx-auto flex max-w-5xl flex-col items-center gap-6 px-4 py-8">
		<div class="space-y-6 text-center">
			<h1
				class="from-primary to-primary/80 bg-gradient-to-r bg-clip-text text-5xl font-bold text-transparent lg:text-6xl"
			>
				Welcome to DESDEO
			</h1>
			<p class="text-muted-foreground mx-auto max-w-2xl text-lg">
				Explore the features and functionalities to enhance your decision-making process.
			</p>
		</div>
		<div class="mt-2 grid grid-cols-1 place-items-stretch gap-6 sm:grid-cols-2 lg:grid-cols-3">
			<Card.Root
				class="group flex h-[300px] flex-col transition-all duration-200 hover:-translate-y-1 hover:shadow-lg"
			>
				<Card.Header class="flex items-center justify-center">
					<div
						class="bg-secondary/15 group-hover:bg-secondary/25 rounded-full p-4 transition-colors"
					>
						<Problem class="text-secondary-foreground size-12" strokeWidth={1.5} />
					</div></Card.Header
				>
				<Card.Content class="flex-1 text-left">
					<h2 class="text-secondary-foreground mb-1 text-lg font-semibold">
						NIMBUS
					</h2>
					<p class="text-muted-foreground leading-snug">
						Solve the river pollution problem using the NIMBUS method.
					</p>
				</Card.Content>
				<Card.Footer>
					<Button class="w-full" onclick={goToNIMBUS}>Start</Button>
				</Card.Footer>
			</Card.Root>
			<Card.Root
				class="group flex h-[300px] flex-col transition-all duration-200 hover:-translate-y-1 hover:shadow-lg"
			>
				<Card.Header class="flex items-center justify-center">
					<div
						class="bg-secondary/15 group-hover:bg-secondary/25 rounded-full p-4 transition-colors"
					>
						<Method class="text-secondary-foreground size-12" strokeWidth={1.5} />
					</div></Card.Header
				>
				<Card.Content class="flex-1 text-left">
					<h2 class="text-secondary-foreground mb-1 text-lg font-semibold">Explainable NIMBUS</h2>
					<p class="text-muted-foreground leading-snug">
						Use the explainable version of the NIMBUS method to solve the river pollution problem.
					</p>
				</Card.Content>
				<Card.Footer>
					<Button class="w-full" onclick={goToExplainableNIMBUS}>Start</Button>
				</Card.Footer>
			</Card.Root>
			<Card.Root
				class="group flex h-[300px] flex-col transition-all duration-200 hover:-translate-y-1 hover:shadow-lg"
			>
				<Card.Header class="flex items-center justify-center">
					<div
						class="bg-secondary/15 group-hover:bg-secondary/25 rounded-full p-4 transition-colors"
					>
						<ChartArea class="text-secondary-foreground size-12" strokeWidth={1.5} />
					</div></Card.Header
				>
				<Card.Content class="flex-1 text-left">
					<h2 class="text-secondary-foreground mb-1 text-lg font-semibold">Obtained Solutions</h2>
					<p class="text-muted-foreground leading-snug">
						See the solutions obtained from the NIMBUS and explainable NIMBUS methods.
					</p>
				</Card.Content>
				<Card.Footer>
					<Button class="w-full" onclick={goToObtainedSolutions}>View Solutions</Button>
				</Card.Footer>
			</Card.Root>
		</div>
	</main>
</div>
