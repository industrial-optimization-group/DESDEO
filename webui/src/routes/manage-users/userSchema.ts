import { z } from "zod";

// The /add_new_dm and /add_new_analyst endpoints use FastAPI's OAuth2PasswordRequestForm,
// which sends data as application/x-www-form-urlencoded — not a JSON body. Orval does not
// generate Zod schemas for form-encoded request bodies, so this schema is defined manually.
// The generated TypeScript interfaces (BodyAddNewDmAddNewDmPost, BodyAddNewAnalystAddNewAnalystPost)
// are still used when constructing the actual API call body.
export const newUserSchema = z.object({
    username: z.string().min(1, "Username is required"),
    password: z.string().min(1, "Password is required"),
});

export type FormMessage = { success: boolean; text: string };
