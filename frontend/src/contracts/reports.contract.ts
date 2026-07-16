import { z } from "zod";

export const TokenUsageMetadataSchema = z.object({
  prompt_tokens: z.number().int().nonnegative().default(0),
  completion_tokens: z.number().int().nonnegative().default(0),
  total_tokens: z.number().int().nonnegative().default(0),
  estimated_cost_usd: z.number().nonnegative().default(0.0),
});

export const ReviewIssueSchema = z.object({
  id: z.string().uuid(),
  file_path: z.string(),
  line_start: z.number().int().positive(),
  line_end: z.number().int().positive(),
  category: z.enum([
    "CODE_QUALITY",
    "BUG_DETECTION",
    "SECURITY",
    "PERFORMANCE",
    "BEST_PRACTICES",
    "MAINTAINABILITY",
    "CODE_SMELLS",
    "COMPLEXITY",
  ]),
  severity: z.enum(["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]),
  confidence: z.number().min(0.0).max(1.0).default(1.0),
  description: z.string(),
  explanation: z.string(),
  suggested_fix: z.string(),
  snippet: z.string(),
});

export const FileReviewResultSchema = z.object({
  file_path: z.string(),
  issues: z.array(ReviewIssueSchema).default([]),
  score: z.number().int().min(0).max(100).default(100),
  review_time_sec: z.number().nonnegative().default(0.0),
  token_usage: TokenUsageMetadataSchema,
});

export const RepositoryReviewReportSchema = z.object({
  id: z.string().uuid(),
  repository_id: z.string().uuid(),
  created_at: z.string(),
  files_reviewed: z.number().int().nonnegative(),
  total_issues: z.number().int().nonnegative(),
  issues_by_severity: z.record(z.string(), z.number().int().nonnegative()).default({}),
  issues_by_category: z.record(z.string(), z.number().int().nonnegative()).default({}),
  average_score: z.number().min(0.0).max(100.0).default(100.0),
  file_results: z.array(FileReviewResultSchema).default([]),
  token_usage: TokenUsageMetadataSchema,
});

export type TokenUsageMetadataDTO = z.infer<typeof TokenUsageMetadataSchema>;
export type ReviewIssueDTO = z.infer<typeof ReviewIssueSchema>;
export type FileReviewResultDTO = z.infer<typeof FileReviewResultSchema>;
export type RepositoryReviewReportDTO = z.infer<typeof RepositoryReviewReportSchema>;
