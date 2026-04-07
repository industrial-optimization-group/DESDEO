import {
    addNewDmAddNewDmPost,
    addNewAnalystAddNewAnalystPost,
} from '$lib/gen/endpoints/DESDEOFastAPI';
import type {
    BodyAddNewDmAddNewDmPost,
    BodyAddNewAnalystAddNewAnalystPost,
} from '$lib/gen/endpoints/DESDEOFastAPI';

export type UserCreateResult = { success: boolean; message: string };

// Note: /add_new_dm and /add_new_analyst use FastAPI's OAuth2PasswordRequestForm
// (application/x-www-form-urlencoded). Authentication for the analyst endpoint is
// handled transparently by the SvelteKit proxy and hooks.server.ts, which attach
// the access_token cookie to outgoing requests — no manual token passing needed here.

export async function addDm(username: string, password: string): Promise<UserCreateResult> {
    const body: BodyAddNewDmAddNewDmPost = { username, password, scope: '' };
    const response = await addNewDmAddNewDmPost(body);
    const status = response.status as number;

    if (status === 401) {
        return { success: false, message: 'Unauthorized: analyst or admin role required.' };
    }
    if (status === 409) {
        return { success: false, message: 'A user with that username already exists.' };
    }
    if (status !== 201) {
        console.error('addDm failed.', status);
        return { success: false, message: 'Failed to create user. Please try again.' };
    }

    return { success: true, message: 'Decision maker created successfully.' };
}

export async function addAnalyst(username: string, password: string): Promise<UserCreateResult> {
    const body: BodyAddNewAnalystAddNewAnalystPost = { username, password, scope: '' };
    const response = await addNewAnalystAddNewAnalystPost(body);
    const status = response.status as number;

    if (status === 401) {
        return { success: false, message: 'Unauthorized: analyst or admin role required.' };
    }
    if (status === 409) {
        return { success: false, message: 'A user with that username already exists.' };
    }
    if (status !== 201) {
        console.error('addAnalyst failed.', status);
        return { success: false, message: 'Failed to create analyst. Please try again.' };
    }

    return { success: true, message: 'Analyst created successfully.' };
}
