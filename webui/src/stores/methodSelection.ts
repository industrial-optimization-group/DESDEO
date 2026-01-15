import { browser } from '$app/environment';
import { writable } from 'svelte/store';

export interface MethodSelectionState {
	selectedProblemId: number | null;
	selectedMethod: string | null;
}

const storageKey = 'methodSelection';

const initialState: MethodSelectionState =
	browser && localStorage.getItem(storageKey)
		? JSON.parse(localStorage.getItem(storageKey)!)
		: { selectedProblemId: null, selectedMethod: null };

const store = writable<MethodSelectionState>(initialState);

// Persist to localStorage
if (browser) {
	store.subscribe((value) => {
		localStorage.setItem(storageKey, JSON.stringify(value));
	});
}

export const methodSelection = {
	subscribe: store.subscribe,
	set: (problemId: number | null, method: string | null) =>
		store.set({ selectedProblemId: problemId, selectedMethod: method }),
	clear: () => store.set({ selectedProblemId: null, selectedMethod: null })
};