import { z } from "zod";

export const uploadSubmissionSchema = z.object({
  gitUrl: z.string().trim().optional().or(z.literal("")),
  branch: z.string().trim().optional(),
  zipFile: z.any().optional(),
  focusAreas: z.string().trim().optional(),
  maxIssuesPerFile: z.coerce
    .number()
    .int("Must be an integer")
    .positive("Must be a positive integer")
    .default(10),
}).superRefine((data, ctx) => {
  const hasGitUrl = !!data.gitUrl && data.gitUrl.trim().length > 0;
  const hasZipFile = !!data.zipFile;

  // 1. Enforce exactly one
  if (hasGitUrl && hasZipFile) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: "Provide either a Git repository URL or a ZIP file, but not both",
      path: ["gitUrl"],
    });
  } else if (!hasGitUrl && !hasZipFile) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: "Must be a valid Git URL",
      path: ["gitUrl"],
    });
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: "ZIP file is required",
      path: ["zipFile"],
    });
  }

  // 2. Validate URL format if provided
  if (hasGitUrl && data.gitUrl) {
    try {
      new URL(data.gitUrl);
    } catch {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Must be a valid Git URL",
        path: ["gitUrl"],
      });
    }
  }

  // 3. Validate ZIP file format if provided
  if (hasZipFile && data.zipFile instanceof File) {
    if (!data.zipFile.name.endsWith(".zip")) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "File must end with .zip",
        path: ["zipFile"],
      });
    }
  }
});

export type UploadSubmissionData = z.infer<typeof uploadSubmissionSchema>;
