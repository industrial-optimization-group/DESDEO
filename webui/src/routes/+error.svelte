<script lang="ts">
    import { Topbar } from '$lib/components/ui/topbar';
    import * as Card from '$lib/components/ui/card/index.js';
    import { Button } from '$lib/components/ui/button/index.js';
    import { goto } from '$app/navigation';
    import { page } from '$app/state';

    function goToDashboard() {
        goto('/dashboard');
    }
</script>

<div class="flex min-h-screen w-full flex-col">
    <Topbar />
    
  	<main class="mx-auto flex max-w-5xl flex-col items-center gap-10 px-4 py-20">
        <div class="space-y-20 text-center">
            <h1
                    class="from-primary to-primary/80 bg-gradient-to-r bg-clip-text text-5xl font-bold text-transparent leading-tight lg:text-6x1"
                >
                    Oops, something went wrong!
                </h1>
        </div>
        <div class="space-y-20 text-center">
            <Card.Root
                    class="group flex w-[700px] flex-col transition-all duration-200 hover:-translate-y-1 hover:shadow-lg"
                >
                <Card.Header>
                    <h2
                        class="from-primary to-primary/80 bg-gradient-to-r bg-clip-text text-5xl font-bold text-transparent lg:text-6xl"
                    >
                        {page.status}
                        <span class="text-4xl font-normal align-middle">
                            | {page.error?.message}
                        </span>
                    </h2>
                </Card.Header>

                <Card.Content>
                    {#if page.status === 404}
                        <p class="text-muted-foreground mx-auto max-w-2xl text-lg">
                            This page is like the best solution in the multiobjective optimization... <br> It doesn't really exist!
                        </p>
                    {:else if page.status === 500}
                        <p class="text-muted-foreground mx-auto max-w-2xl text-lg">
                            Something at our end is not working, it's not your fault. Sorry about that.
                        </p>
                    {:else}
                        <p class="text-muted-foreground mx-auto max-w-2xl text-lg">
                            This is kinda not working. You'd better go back home <br>...or try to refresh page <br>...or do whatever you think is optimal
                        </p>
                    {/if}
                </Card.Content>                
            </Card.Root>            
		</div>
        
        <Button class="uppercase w-[15em]" onclick={goToDashboard}>Go to homepage</Button>
    </main>  
</div>