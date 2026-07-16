import { z } from "zod";

const envSchema = z.object({
  APP_ENV: z.enum(["development", "production", "staging", "test"]).default("development"),
  BFF_URL: z.string().url().default("http://localhost:3000/api"),
  // API_URL is required on the server side (for Next.js Route Handlers BFF)
  API_URL: z.string().url().default("http://localhost:8000/api/v1"),
  POLL_INTERVAL_MS: z.coerce.number().int().nonnegative().default(2000),
  MAX_UPLOAD_SIZE_MB: z.coerce.number().int().nonnegative().default(100),
});

export type EnvConfig = z.infer<typeof envSchema>;

// Validate and parse environment variables dynamically
const parseEnv = (): EnvConfig => {
  const isServer = typeof window === "undefined";

  const rawConfig = {
    APP_ENV: process.env.NEXT_PUBLIC_APP_ENV,
    BFF_URL: process.env.NEXT_PUBLIC_BFF_URL,
    API_URL: process.env.API_URL,
    POLL_INTERVAL_MS: process.env.NEXT_PUBLIC_POLL_INTERVAL_MS,
    MAX_UPLOAD_SIZE_MB: process.env.NEXT_PUBLIC_MAX_UPLOAD_SIZE_MB,
  };

  try {
    return envSchema.parse(rawConfig);
  } catch (error) {
    if (isServer) {
      console.error("❌ Invalid environment variables configuration validation failed:", error);
      throw new Error("Invalid configuration schema parameters loaded");
    } else {
      // In browser contexts, print warning or return defaults for browser-safe variables
      const safeConfig = envSchema.safeParse(rawConfig);
      if (!safeConfig.success) {
        console.warn("⚠️ Client side environment validation warnings:", safeConfig.error.format());
        return {
          APP_ENV: "development",
          BFF_URL: "http://localhost:3000/api",
          API_URL: "http://localhost:8000/api/v1",
          POLL_INTERVAL_MS: 2000,
          MAX_UPLOAD_SIZE_MB: 100,
        };
      }
      return safeConfig.data;
    }
  }
};

export const env = parseEnv();
export default env;
