import { fail, superValidate } from "sveltekit-superforms";
import { zod4 } from "sveltekit-superforms/adapters";
import { loginLoginPost } from "$lib/gen/endpoints/DESDEOFastAPI";
import type { BodyLoginLoginPost } from '$lib/gen/endpoints/DESDEOFastAPI';
import { redirect, type Actions } from "@sveltejs/kit";
import { dev } from "$app/environment";
import { loginSchema } from "./loginSchema";


export const load = async () => {
    const form = await superValidate(zod4(loginSchema));

    return { form };
}

export const actions: Actions = {
    login: async ({request, cookies}) => {

        const form = await superValidate(request, zod4(loginSchema));

        if (!form.valid) {
            return fail(400, { form });
        }

        const body: BodyLoginLoginPost = {
            username: form.data.username,
            password: form.data.password,
            scope: ''
        }

        const response = await loginLoginPost(body);

        if (response.status != 200){
            if (response.status === 401) {
                form.message = "Invalid username or password";
            } else if (response.status >= 500) {
                form.message = "Server unavailable";
            } else {
                form.message = "Login failed. Please try again.";
            }
            console.log("RESPONSE ", response.status)
            return fail(response.status, {form});
        }

        cookies.set("access_token", response.data.access_token, {httpOnly: true, secure: !dev, sameSite: "lax", path: '/'});
        cookies.set("refresh_token", response.data.refresh_token, {httpOnly: true, secure: !dev, sameSite: "lax", path: '/'});

        throw redirect(303, '/dashboard');
    },
};
