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

	import { goto } from '$app/navigation';

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
		goto('/interactive_methods/GDM-SCORE-bands');
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
						<Trees class="text-secondary-foreground size-12" strokeWidth={1.5} />
					</div></Card.Header
				>
				<Card.Content class="flex-1 text-left">
					<h2 class="text-secondary-foreground mb-1 text-lg font-semibold">
						Forest Management Tool
					</h2>
					<p class="text-muted-foreground leading-snug">
						Optimize forest management decisions considering multiple objectives.
					</p>
				</Card.Content>
				<Card.Footer>
					<Button class="w-full" onclick={goToForestManagement}>Try Forest Management Tool</Button>
				</Card.Footer>
			</Card.Root>
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
						Optimization Problems
					</h2>
					<p class="text-muted-foreground leading-snug">
						Browse and select from a variety of pre-defined multi-objective optimization problems.
					</p>
				</Card.Content>
				<Card.Footer>
					<Button class="w-full" onclick={goToOptimizationProblems}>Explore Problems</Button>
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
					<h2 class="text-secondary-foreground mb-1 text-lg font-semibold">Optimization Methods</h2>
					<p class="text-muted-foreground leading-snug">
						Discover various interactive methods for solving multi-objective optimization problems.
					</p>
				</Card.Content>
				<Card.Footer>
					<Button class="w-full" onclick={goToOptimizationMethods}>View Methods</Button>
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
					<h2 class="text-secondary-foreground mb-1 text-lg font-semibold">SCORE Bands</h2>
					<p class="text-muted-foreground leading-snug">
						Visualize and analyze solution sets using an advanced parallel coordinates
						visualization.
					</p>
				</Card.Content>
				<Card.Footer>
					<Button class="w-full" onclick={goToScoreBands}>Open Visualization</Button>
				</Card.Footer>
			</Card.Root>
			<Card.Root
				class="group flex h-[300px] flex-col transition-all duration-200 hover:-translate-y-1 hover:shadow-lg"
			>
				<Card.Header class="flex items-center justify-center">
					<div
						class="bg-secondary/15 group-hover:bg-secondary/25 rounded-full p-4 transition-colors"
					>
						<SquareFunction class="text-secondary-foreground size-12" strokeWidth={1.5} />
					</div></Card.Header
				>
				<Card.Content class="flex-1 text-left">
					<h2 class="text-secondary-foreground mb-1 text-lg font-semibold">Custom Problem</h2>
					<p class="text-muted-foreground leading-snug">
						Create and define your own multi-objective optimization problem with custom parameters.
					</p>
				</Card.Content>
				<Card.Footer>
					<Button class="w-full" onclick={createCustomProblem}>Create Problem</Button>
				</Card.Footer>
			</Card.Root>
			<Card.Root
				class="group flex h-[300px] flex-col transition-all duration-200 hover:-translate-y-1 hover:shadow-lg"
			>
				<Card.Header class="flex items-center justify-center">
					<div
						class="bg-secondary/15 group-hover:bg-secondary/25 rounded-full p-4 transition-colors"
					>
						<HelpCircle class="text-secondary-foreground size-12" strokeWidth={1.5} />
					</div></Card.Header
				>
				<Card.Content class="flex-1 text-left">
					<h2 class="text-secondary-foreground mb-1 text-lg font-semibold">Documentation</h2>
					<p class="text-muted-foreground leading-snug">
						Access comprehensive guides, tutorials, and API documentation for DESDEO.
					</p>
				</Card.Content>
				<Card.Footer>
					<Button class="w-full" onclick={goToDocumentation}>Go to the documentation page</Button>
				</Card.Footer>
			</Card.Root>
		</div>
	</main>
</div>
