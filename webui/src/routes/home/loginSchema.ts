import { z } from "zod";

// TODO: once we update Orval to the newest release, we should generate the runtime zod schemas
// properly from the web-API.
export const loginSchema = z.object({
    username: z.string().min(1),
    password: z.string().min(1)
});
