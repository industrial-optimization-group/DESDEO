<script lang="ts">
	import type { PageProps } from './$types';
	import Button from '$lib/components/ui/button/button.svelte';
	import { Toaster } from 'svelte-sonner';
	import { toast } from 'svelte-sonner';
	import { methodSelection } from '../../../stores/methodSelection';
	import { goto } from '$app/navigation';

	let { data }: PageProps = $props(); // from load in page.ts
	let problemList = data.problems;

	let localSelectedProblemId = $state<number | null>(null);
	let localSelectedMethod = $state<string | null>(null);

	const methods = [{ name: 'E-NAUTILUS', description: 'Evolutionary NAUTILUS method for MOO.' }];

	function startMethod() {
		// set stores
		methodSelection.set(localSelectedProblemId, localSelectedMethod);

		toast.success(
			`Starting method: ${$methodSelection.selectedMethod} with problem ID ${$methodSelection.selectedProblemId}
            Not really, this is a TODO.
            Remember to drink water!`
		);

		// Navigate to the method UI page...
		// logic
		// TODO!!!
		goto('/interactive_methods/E-NAUTILUS');
	}
</script>

<div class="mx-auto mt-10 max-w-5xl px-4">
	<h1 class="mb-6 text-2xl font-semibold">Initialize Method</h1>

	<div class="mb-4">
		{#if localSelectedProblemId && localSelectedMethod}
			<Button onclick={() => startMethod()} class="w-full">Start</Button>
		{:else}
			<Button disabled class="w-full cursor-not-allowed opacity-50">
				Select a problem and method
			</Button>
		{/if}
	</div>

	<div class="grid grid-cols-1 gap-8 md:grid-cols-2">
		<!-- Problem List -->
		<div>
			<h2 class="mb-2 text-lg font-semibold">Your Problems</h2>
			<ul class="space-y-2">
				{#each problemList as problem}
					<li>
						<button
							type="button"
							onclick={() => (localSelectedProblemId = problem.id)}
							class="hover:bg-accent focus:ring-primary w-full rounded-md border p-3 text-left transition-colors duration-200 focus:ring-2 focus:outline-none
				{localSelectedProblemId === problem.id ? 'bg-accent ring-primary ring-2' : 'bg-white'}"
						>
							<div class="font-medium">{problem.name}</div>
							<div class="text-muted-foreground truncate text-sm">{problem.description}</div>
						</button>
					</li>
				{/each}
			</ul>
		</div>

		<!-- Method List -->
		<div>
			<h2 class="mb-2 text-lg font-semibold">Available Interactive Methods</h2>
			<ul class="space-y-2">
				{#each methods as method}
					<li>
						<button
							type="button"
							onclick={() => (localSelectedMethod = method.name)}
							class="hover:bg-accent focus:ring-primary w-full rounded-md border p-3 text-left transition-colors duration-200 focus:ring-2 focus:outline-none
				{localSelectedMethod === method.name ? 'bg-accent ring-primary ring-2' : 'bg-white'}"
						>
							<div class="font-medium">{method.name}</div>
							<div class="text-muted-foreground truncate text-sm">{method.description}</div>
						</button>
					</li>
				{/each}
			</ul>
		</div>
	</div>
	<!--  Debug -->
	<div class="mt-8 text-sm text-gray-500">
		Selected Problem ID: {localSelectedProblemId}<br />
		Selected Method: {localSelectedMethod}
		<Toaster position="top-center" />
	</div>
</div>
