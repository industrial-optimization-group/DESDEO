<script lang="ts">
  import { dialogState, closeDialog } from "./dialogs";
  import ConfirmDialog from "./confirmation-dialog.svelte";
  import InputDialog from "./input-dialog.svelte";
  import type { ConfirmDialogOptions, InputDialogOptions } from "./dialogs";

  // Auto-subscribe store
  $: current = $dialogState;
</script>

{#if current?.type === "confirm"}
  <ConfirmDialog
    open={true}
    {...(current.props as ConfirmDialogOptions)}
    onConfirm={() => {
      (current.props as ConfirmDialogOptions)?.onConfirm?.();
      closeDialog();
    }}
    onCancel={() => {
      (current.props as ConfirmDialogOptions)?.onCancel?.();
      closeDialog();
    }}
  />
{/if}

{#if current?.type === "input"}
  <InputDialog
    open={true}
    {...(current.props as InputDialogOptions)}
    onConfirm={(value) => {
      (current.props as InputDialogOptions)?.onConfirm?.(value);
      closeDialog();
    }}
    onCancel={() => {
      (current.props as InputDialogOptions)?.onCancel?.();
      closeDialog();
    }}
  />
{/if}
