import { z } from "zod";

export const UserSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  name: z.string(),
  roles: z.array(z.string()).default([]),
  permissions: z.array(z.string()).default([]),
});

export type UserDTO = z.infer<typeof UserSchema>;
