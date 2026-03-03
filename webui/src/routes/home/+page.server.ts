import { z } from "zod";
import { fail, superValidate } from "sveltekit-superforms";
import { zod4 } from "sveltekit-superforms/adapters";
import { redirect, type Actions } from "@sveltejs/kit";

const loginSchema = z.object({
    username: z.string(),
    password: z.string()
});

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';

export const load = async () => {
    const form = await superValidate(zod4(loginSchema));
    return { form };
}

export const actions: Actions = {
    login: async ({ request, cookies }) => {
        const form = await superValidate(request, zod4(loginSchema));

        if (!form.valid) {
            return fail(400, { form });
        }

        // Send form-encoded data to /login endpoint
        const formData = new URLSearchParams();
        formData.append('username', form.data.username);
        formData.append('password', form.data.password);

        const response = await fetch(`${API_BASE_URL}/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: formData.toString(),
            credentials: 'include'
        });

        if (!response.ok) {
            return fail(response.status, { form });
        }

        const data = await response.json();
        cookies.set("access_token", data.access_token, { httpOnly: true, secure: true, sameSite: "lax", path: '/' });
        cookies.set("refresh_token", data.refresh_token, { httpOnly: true, secure: true, sameSite: "lax", path: '/' });

        redirect(303, '/dashboard');
    },
};