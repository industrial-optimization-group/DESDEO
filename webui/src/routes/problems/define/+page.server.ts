import { z } from "zod";
import type { Actions } from "@sveltejs/kit";
import { superValidate, fail } from 'sveltekit-superforms';
import { zod4 } from 'sveltekit-superforms/adapters';
import type { PageServerLoad } from "../$types";

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';

// Simple validation schema for JSON problem file
const problemAddJsonSchema = z.object({
  json_problem: z.instanceof(File)
});

export const load: PageServerLoad = async () => {
  const form = await superValidate(zod4(problemAddJsonSchema));

  return { form };
}

export const actions: Actions = {
  upload_json: async ({ request, cookies }) => {
    const form = await superValidate(request, zod4(problemAddJsonSchema));

    if (!form.valid) {
      return fail(400, { form });
    }

    const formData = new FormData();
    formData.append('json_problem', form.data.json_problem);

    const refreshToken = cookies.get('refresh_token');
    const response = await fetch(`${API_BASE_URL}/problem/add_json`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${refreshToken}`
      },
      body: formData
    });

    if (!response.ok) {
      return fail(response.status);
    }

    return { success: true };
  }
};
