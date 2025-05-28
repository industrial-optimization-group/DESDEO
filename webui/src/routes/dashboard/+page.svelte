<script lang="ts">
	import Topbar from '$lib/components/ui/topbar/Topbar.svelte';
	import CircleUser from '@lucide/svelte/icons/user-circle';
	import Method from '@lucide/svelte/icons/brain-circuit';
	import Logo from '@lucide/svelte/icons/orbit';
	import Problem from '@lucide/svelte/icons/puzzle';
	import Archive from '@lucide/svelte/icons/archive';
	import HelpCircle from '@lucide/svelte/icons/circle-help';
	import * as Card from "$lib/components/ui/card/index.js";
	import { Button } from '$lib/components/ui/button/index.js';


</script>

<div class="flex min-h-screen w-full flex-col">
	<Topbar />

	<main
		class="mx-auto flex max-w-5xl flex-col items-center gap-6 text-center"
	>
		<h1 class="mb-6 text-4xl font-semibold text-pretty lg:text-5xl text-primary pt-4">Welcome to DESDEO</h1>
		<p class="text-lg text-gray-700 text-center">
			Explore the features and functionalities to enhance your decision-making process.
		</p>
		<div class="mt-10 grid grid-cols-1 place-items-center gap-8 sm:grid-cols-2 lg:grid-cols-3">
            <Card.Root >
              <Card.Header class="pb-1">
                <Problem class="size-4" strokeWidth={1} />
              </Card.Header>
              <Card.Content class="text-left">
                <h2 class="mb-1 text-lg font-semibold">Card Title</h2>
                <p class="leading-snug text-muted-foreground">
                  Lorem ipsum dolor sit amet consectetur.
                </p>
              </Card.Content>
              <Card.Footer>
                <Button class="w-full">Do something</Button>
              </Card.Footer>
            </Card.Root>
            <Card.Root >
              <Card.Header class="pb-1">
                <Method class="size-4" strokeWidth={1} />
              </Card.Header>
              <Card.Content class="text-left">
                <h2 class="mb-1 text-lg font-semibold">Card Title</h2>
                <p class="leading-snug text-muted-foreground">
                  Lorem ipsum dolor sit amet consectetur.
                </p>
              </Card.Content>
              <Card.Footer >
				<Button class="w-full">Do something</Button>
              </Card.Footer>
            </Card.Root>
            <Card.Root >
              <Card.Header class="pb-1">
                <Archive class="size-4" strokeWidth={1} />
              </Card.Header>
              <Card.Content class="text-left">
                <h2 class="mb-1 text-lg font-semibold">Card Title</h2>
                <p class="leading-snug text-muted-foreground">
                  Lorem ipsum dolor sit amet consectetur.
                </p>
              </Card.Content>
              <Card.Footer >
				<Button class="w-full">Do something</Button>
              </Card.Footer>
            </Card.Root>
            <Card.Root >
              <Card.Header class="pb-1">
                <HelpCircle class="size-4" strokeWidth={1} />
              </Card.Header>
              <Card.Content class="text-left">
                <h2 class="mb-1 text-lg font-semibold">Card Title</h2>
                <p class="leading-snug text-muted-foreground">
                  Lorem ipsum dolor sit amet consectetur.
                </p>
              </Card.Content>
              <Card.Footer >
				<Button class="w-full">Do something</Button>
              </Card.Footer>
            </Card.Root>
            <Card.Root >
              <Card.Header class="pb-1">
                <CircleUser class="size-4" strokeWidth={1} />
              </Card.Header>
              <Card.Content class="text-left">
                <h2 class="mb-1 text-lg font-semibold">Card Title</h2>
                <p class="leading-snug text-muted-foreground">
                  Lorem ipsum dolor sit amet consectetur.
                </p>
              </Card.Content>
              <Card.Footer >
				<Button class="w-full">Do something</Button>
              </Card.Footer>
            </Card.Root>
            <Card.Root >
              <Card.Header class="pb-1">
                <Problem class="size-4" strokeWidth={1} />
              </Card.Header>
              <Card.Content class="text-left">
                <h2 class="mb-1 text-lg font-semibold">Card Title</h2>
                <p class="leading-snug text-muted-foreground">
                  Lorem ipsum dolor sit amet consectetur.
                </p>
              </Card.Content>
              <Card.Footer >
				<Button class="w-full">Do something</Button>
              </Card.Footer>
            </Card.Root>
          </div>
	</main>
</div>
