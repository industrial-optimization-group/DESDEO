// src/lib/dialogs.ts
import { writable } from "svelte/store";

export type DialogType = "confirm" | "input";

export interface ConfirmDialogOptions {
  title?: string;
  description?: string;
  confirmText?: string;
  cancelText?: string;
  confirmVariant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link";
  onConfirm?: () => void;
  onCancel?: () => void;
}

export interface InputDialogOptions {
  title?: string;
  description?: string;
  confirmText?: string;
  cancelText?: string;
  initialValue?: string;
  placeholder?: string;
  onConfirm?: (value: string) => void;
  onCancel?: () => void;
}

interface DialogState {
  type: DialogType | null;
  props?: ConfirmDialogOptions | InputDialogOptions;
}

export const dialogState = writable<DialogState>({ type: null });

export function openConfirmDialog(props: ConfirmDialogOptions) {
  dialogState.set({ type: "confirm", props });
}

export function openInputDialog(props: InputDialogOptions) {
  dialogState.set({ type: "input", props });
}

export function closeDialog() {
  dialogState.set({ type: null });
}
