import { z } from "zod";

export const LoginRequestSchema = z.object({
  username: z.string().email("Invalid email format"),
  password: z.string().min(8, "Password must be at least 8 characters"),
});

export const LoginResponseSchema = z.object({
  access_token: z.string(),
  token_type: z.string().default("bearer"),
});

export type LoginRequestDTO = z.infer<typeof LoginRequestSchema>;
export type LoginResponseDTO = z.infer<typeof LoginResponseSchema>;
