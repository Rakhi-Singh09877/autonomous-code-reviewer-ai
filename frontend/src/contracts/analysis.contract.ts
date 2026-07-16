import { z } from "zod";

export const AnalysisInitiateRequestSchema = z.object({
  git_url: z.string().url().optional(),
  branch: z.string().optional(),
  focus_areas: z.array(z.string()).optional(),
  max_issues_per_file: z.number().int().nonnegative().optional(),
});

export const AnalysisInitiateResponseSchema = z.object({
  analysis_id: z.string().uuid(),
  status: z.string().default("PENDING"),
});

export const AnalysisStatusResponseSchema = z.object({
  analysis_id: z.string().uuid(),
  status: z.enum(["PENDING", "PROCESSING", "COMPLETED", "FAILED"]),
  progress_percentage: z.number().min(0).max(100),
  current_file: z.string().nullable(),
  total_files: z.number().int().nonnegative().default(0),
  errors: z.array(z.string()).default([]),
});

export type AnalysisInitiateRequestDTO = z.infer<typeof AnalysisInitiateRequestSchema>;
export type AnalysisInitiateResponseDTO = z.infer<typeof AnalysisInitiateResponseSchema>;
export type AnalysisStatusResponseDTO = z.infer<typeof AnalysisStatusResponseSchema>;
