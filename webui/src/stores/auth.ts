import {writable, derived} from 'svelte/store';

export type User = {
    id: number
    username: string
    role: string
    group: string
}

type AuthState = {
    accessToken: string | null
    user: User | null
}

const initialAuthState: AuthState = {
    accessToken: null,
    user: null
}

const { subscribe, set, update } = writable<AuthState>(initialAuthState)

export const auth = {
    subscribe,
    setAuth: (accessToken: string, user: User | null) => set({accessToken, user}),
    clearAuth: () => set(initialAuthState)
}

export const isAuthenticated = derived(auth, ($auth) => !!$auth.accessToken && !!$auth.user)