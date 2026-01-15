import { browser } from '$app/environment';
import { writable, derived } from 'svelte/store';
import type { UserPublic } from '../lib/gen/models';

type AuthState = {
	accessToken: string | null;
	user: UserPublic | null;
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
	setAuth: (accessToken: string, user: UserPublic | null) =>
		store.set({ accessToken, user }),
	clearAuth: () => store.set({ accessToken: null, user: null })
};

export const isAuthenticated = derived(auth, ($auth) => !!$auth.accessToken && !!$auth.user);
