<script lang="ts">
	import logo from '$lib/assets/logo.png';

	let { children } = $props();
</script>

<div class="grid h-screen grid-cols-[1fr_auto]">
	<div class="m-8">
		<div class="flex items-center gap-2">
			<img src={logo} alt="" />
			<span class="text-xl font-bold">DESDEO</span>
		</div>
		<div class="mx-28 flex h-full items-center">
			<div class="max-w-2xl">
				<h1 class="mb-12 max-w-md text-5xl font-bold leading-snug">
					Enabling Better Decision Making
				</h1>
				<p>DESDEO citation</p>
			</div>
		</div>
	</div>

	<div class="flex flex-col justify-center bg-white px-8 py-8">
		{@render children?.()}
	</div>
</div>
