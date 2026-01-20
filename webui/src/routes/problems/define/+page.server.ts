import { addProblemJsonProblemAddJsonPost } from "$lib/gen/endpoints/DESDEOFastAPI";
import { addProblemJsonProblemAddJsonPostBody } from "$lib/gen/endpoints/DESDEOFastAPIzod";
import type { Actions } from "@sveltejs/kit";
import { superValidate, fail } from 'sveltekit-superforms';
import { zod4 } from 'sveltekit-superforms/adapters';
import type { PageServerLoad } from "../$types";

const problemAddJsonSchema = addProblemJsonProblemAddJsonPostBody;

export const load: PageServerLoad = async () => {
  const form = await superValidate(zod4(problemAddJsonSchema));

  return { form };
}

export const actions: Actions = {
  upload_json: async ({ request, fetch }) => {
    const form = await superValidate(request, zod4(problemAddJsonSchema));

    if (!form.valid) {
      return fail(400, { form });
    }

    // It is very important we use the fetch that is provided by the client (browser)
    const response = await addProblemJsonProblemAddJsonPost(form.data, { fetchImpl: fetch } as RequestInit);

  }
};
