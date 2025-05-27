import type { PageServerLoad } from "./$types.js";
import { superValidate } from "sveltekit-superforms";
import { loginSchema } from "$lib/core/user_and_login";
import { zod } from "sveltekit-superforms/adapters";
 
export const load: PageServerLoad = async () => {
 return {
  form: await superValidate(zod(loginSchema)),
 };
};