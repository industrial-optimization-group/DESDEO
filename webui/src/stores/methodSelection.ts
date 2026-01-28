import { browser } from '$app/environment';
import { writable } from 'svelte/store';

export interface MethodSelectionState {
	selectedProblemId: number | null;
	selectedMethod: string | null;

	selectedSessionId: number | null;
	selectedSessionInfo: string | null;
}

const storageKey = 'methodSelection';

const defaultState: MethodSelectionState = {
	selectedProblemId: null,
	selectedMethod: null,
	selectedSessionId: null,
	selectedSessionInfo: null
};

const initialState: MethodSelectionState =
	browser && localStorage.getItem(storageKey)
		? { ...defaultState, ...JSON.parse(localStorage.getItem(storageKey)!) }
		: defaultState;

const store = writable<MethodSelectionState>(initialState);

if (browser) {
	store.subscribe((value) => {
		localStorage.setItem(storageKey, JSON.stringify(value));
	});
}

function setProblem(problemId: number | null) {
	store.update((s) => ({
		...s,
		selectedProblemId: problemId,
		// problem drives downstream choices
		selectedMethod: null,
		selectedSessionId: null,
		selectedSessionInfo: null
	}));
}

function setMethod(method: string | null) {
	store.update((s) => ({ ...s, selectedMethod: method }));
}

function setSession(sessionId: number | null, sessionInfo: string | null = null) {
	store.update((s) => ({
		...s,
		selectedSessionId: sessionId,
		selectedSessionInfo: sessionId === null ? null : sessionInfo
	}));
}

function clearSession() {
	setSession(null, null);
}

function clearAll() {
	store.set(defaultState);
}

export const methodSelection = {
	subscribe: store.subscribe,
	setProblem,
	setMethod,
	setSession,
	clearSession,
	clearAll,

	// pre-orval API (keep temporarily to avoid breakage)
	set: (problemId: number | null, method: string | null) => {
		// Keep behaviour consistent: setting a problem should clear dependent state
		store.set({
			...defaultState,
			selectedProblemId: problemId,
			selectedMethod: method
		});
	},
	clear: clearAll
};
