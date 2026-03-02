<script lang="ts">
  import { Button } from "$lib/components/ui/button";
  import * as Dialog from "$lib/components/ui/dialog";
  import { Progress } from "$lib/components/ui/progress";

  let {
		open = $bindable(false),
		title = "How this method works",
    steps = [],
		nextText = "Next",
		cancelText = "Cancel",
		onCancel,
		confirmVariant = "default" as "default" | "destructive" | "outline" | "secondary" | "ghost" | "link"
	}: {
		open?: boolean;
		title?: string;
		steps?: { title: string; text: string }[];
		nextText?: string;
		cancelText?: string;
		onCancel?: () => void;
		confirmVariant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link";
	} = $props();

  let currentStep = $state(0);
  let totalSteps = $derived(Math.max(steps.length, 1));
  let currentStepData = $derived(steps[currentStep]);

  function handleNext() {
    if (currentStep < steps.length - 1) {
      currentStep += 1;
    }
  }

  function handleBack() {
    if (currentStep > 0) {
      currentStep -= 1;
    }
  }

  function handleReset() {
    currentStep = 0;
  }

	function handleCancel() {
		onCancel?.();
		open = false;
	}
</script>

<Dialog.Root bind:open onOpenChange={(o) => {
	if (!o) {
		handleReset();
		handleCancel();
	}
}}>
  <Dialog.Content class="sm:max-w-lg">
    <Dialog.Header class="space-y-3">
      <div class="flex items-start gap-3">
        <div class="bg-primary/10 text-primary flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-sm font-semibold">
          ?
        </div>
        <div class="space-y-1">
          <Dialog.Title class="text-xl">{title}</Dialog.Title>
          <Dialog.Description class="text-sm text-muted-foreground">
            Follow the steps below to find a solution for an optimization problem using this method.
          </Dialog.Description>
        </div>
      </div>

<!--       <div class="space-y-2">
        <div class="flex items-center justify-between text-xs text-muted-foreground">
          <span>Step {currentStep + 1} of {steps.length}</span>
          <span>{Math.round(progressValue)}%</span>
        </div>
        <Progress value={progressValue} />
      </div> -->
    </Dialog.Header>

    <div class="mt-4 rounded-xl border bg-muted/30 p-5 shadow-sm transition-all duration-200">
      <p class="text-base font-semibold">{"Step "}{currentStep + 1} of {steps.length}: {currentStepData?.title}</p>
      <p class="mt-2 text-sm leading-6 text-muted-foreground">
        {currentStepData?.text}
      </p>
    </div>

    <div class="mt-4 flex items-center gap-2">
      {#each steps as _, index}
        <div
          class="h-1.5 flex-1 rounded-full transition-colors duration-200"
          class:bg-primary={index <= currentStep}
          class:bg-muted={index > currentStep}
        ></div>
      {/each}
    </div>

    <Dialog.Footer class="mt-6 flex items-center justify-between gap-2 sm:justify-between">
      <div class="flex items-center gap-2">
        <Button
          variant="outline"
          onclick={handleBack}
          disabled={currentStep === 0}
        >
          Back
        </Button>
        <Button variant="ghost" onclick={handleCancel}>{cancelText}</Button>
      </div>

      <div>
        {#if currentStep < steps.length - 1}
          <Button variant={confirmVariant} onclick={handleNext}>
            {nextText}
          </Button>
        {:else}
          <Dialog.Close>
            {#snippet child({ props })}
              <Button variant={confirmVariant} {...props}>
                Finish
              </Button>
            {/snippet}
          </Dialog.Close>
        {/if}
      </div>
    </Dialog.Footer>
  </Dialog.Content>
</Dialog.Root>