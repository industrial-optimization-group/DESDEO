import { browser } from '$app/environment';
import { writable, derived } from 'svelte/store';

export type User = {
	id: number;
	username: string;
	role: string;
	group: string;
};

type AuthState = {
	accessToken: string | null;
	user: User | null;
};

const storageKey = 'authState';

const initialState: AuthState =
	browser && localStorage.getItem(storageKey)
		? JSON.parse(localStorage.getItem(storageKey)!)
		: { accessToken: null, user: null };

const store = writable<AuthState>(initialState);

// Persist to localStorage when store changes
if (browser) {
	store.subscribe((value) => {
		localStorage.setItem(storageKey, JSON.stringify(value));
	});
}

export const auth = {
	subscribe: store.subscribe,
	setAuth: (accessToken: string, user: User | null) =>
		store.set({ accessToken, user }),
	clearAuth: () => store.set({ accessToken: null, user: null })
};

export const isAuthenticated = derived(auth, ($auth) => !!$auth.accessToken && !!$auth.user);
