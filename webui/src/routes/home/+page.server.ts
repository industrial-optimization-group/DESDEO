import { z } from "zod";
import { fail, superValidate } from "sveltekit-superforms";
import { zod4 } from "sveltekit-superforms/adapters";
import { loginLoginPost } from "$lib/gen/endpoints/dESDEOFastAPI";
import type { BodyLoginLoginPost } from '$lib/gen/models';
import type { Actions } from "@sveltejs/kit";

const loginSchema = z.object({
    username: z.string(),
    password: z.string()
});

export const load = async () => {
    const form = await superValidate(zod4(loginSchema));

    return { form };
}

export const actions = {
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
            return fail(response.status);
        }

        cookies.set("access_token", response.data.access_token, {httpOnly: true, secure: true, sameSite: "lax", path: '/'});
        cookies.set("refresh_token", response.data.refresh_token, {httpOnly: true, secure: true, sameSite: "lax", path: '/'});
    },
} satisfies Actions;