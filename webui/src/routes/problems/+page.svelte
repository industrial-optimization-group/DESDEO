<script lang="ts">
	import type { PageProps } from './$types';
	import MathExpressionRenderer from '$lib/components/ui/MathExpressionRenderer/MathExpressionRenderer.svelte';

	let { data }: PageProps = $props();
	let problemList = data.problemList;
</script>

<div class="mx-auto mt-10 max-w-4xl px-4">
	<h1 class="mb-6 text-2xl font-semibold">Your Problems</h1>

	{#if problemList.length === 0}
		<p class="text-gray-600">You have not defined any problems yet.</p>
	{:else}
		<ul class="space-y-6">
			{#each problemList as problem}
				<li class="rounded-md border bg-white p-4 shadow-sm">
					<h2 class="text-xl font-bold">{problem.name}</h2>

					{#if problem.description}
						<p class="mb-2 text-gray-700 italic">{problem.description}</p>
					{/if}

					<p class="text-sm text-gray-600">Domain: {problem.variable_domain}</p>

					<p class="mt-1 text-sm text-gray-600">
						{#if problem.is_linear !== null}
							Linear: {problem.is_linear ? 'Yes' : 'No'} |
						{/if}
						{#if problem.is_convex !== null}
							Convex: {problem.is_convex ? 'Yes' : 'No'} |
						{/if}
						{#if problem.is_twice_differentiable !== null}
							Twice Differentiable: {problem.is_twice_differentiable ? 'Yes' : 'No'}
						{/if}
					</p>

					{#if problem.objectives?.length}
						<h3 class="mt-3 mb-1 text-sm font-semibold text-gray-600">Objectives:</h3>
						<ul class="list-inside list-disc space-y-1 text-sm text-gray-800">
							{#each problem.objectives as obj}
								<li>
									{obj.symbol || obj.name} - {obj.objective_type}
									{#if obj.maximize !== null}
										({obj.maximize ? 'Maximize' : 'Minimize'})
									{/if}
									<MathExpressionRenderer func={obj.func} />
								</li>
							{/each}
						</ul>
					{/if}
					{#if problem.variables?.length}
						<h3 class="mt-3 mb-1 text-sm font-semibold text-gray-600">Variables:</h3>
						<ul class="list-inside list-disc space-y-1 text-sm text-gray-800">
							{#each problem.variables as variable}
								<li>
									{variable.symbol || variable.name}
								</li>
							{/each}
						</ul>
					{/if}

					{#if problem.constraints?.length}
						<h3 class="mt-3 mb-1 text-sm font-semibold text-gray-600">Constraints:</h3>
						<ul class="list-inside list-disc space-y-1 text-sm text-gray-800">
							{#each problem.constraints as constraint}
								<li>
									{constraint.symbol || constraint.name}
									<MathExpressionRenderer func={constraint.func} />
								</li>
							{/each}
						</ul>
					{/if}
					{#if problem.extra_funcs?.length}
						<h3 class="mt-3 mb-1 text-sm font-semibold text-gray-600">
							Extra function definitions:
						</h3>
						<ul class="list-inside list-disc space-y-1 text-sm text-gray-800">
							{#each problem.extra_funcs as obj}
								<li>
									{obj.symbol || obj.name}
									<MathExpressionRenderer func={obj.func} />
								</li>
							{/each}
						</ul>
					{/if}
				</li>
			{/each}
		</ul>
	{/if}
</div>
