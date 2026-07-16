import { describe, it, expect } from "vitest";

// 1. Domain Entities & Value Objects imports
import { User, Repository, Analysis, ReviewIssue, RepositoryReviewReport, FileReviewResult } from "../domain/entities";
import { TokenUsage } from "../domain/value_objects";

// 2. Validation imports
import { validateGitUrl, isSafePath, validateZipSize } from "../domain/validation";

// 3. Contract imports
import { LoginRequestSchema, AnalysisStatusResponseSchema } from "../contracts";

// 4. Mapper imports
import { UserMapper, ReportMapper } from "../services/api/mappers";

describe("Phase 2 Domain Entities & Value Objects", () => {
  it("should successfully construct and validate User entities", () => {
    const user = new User("user-1", "test@test.com", "JD", ["admin"], ["create_analysis"]);
    expect(user.id).toBe("user-1");
    expect(user.hasRole("admin")).toBe(true);
    expect(user.hasRole("editor")).toBe(false);
    expect(user.hasPermission("create_analysis")).toBe(true);
  });

  it("should calculate Repository MB size correctly", () => {
    const repo = new Repository("repo-1", "/path/to/repo", "ZIP", 10, 1024 * 1024 * 5); // 5 MB
    expect(repo.sizeInMb).toBe(5.0);
  });

  it("should inspect Analysis state properties correctly", () => {
    const pendingAnalysis = new Analysis("analysis-1", "PENDING", 0, null, 0, []);
    expect(pendingAnalysis.isFinished).toBe(false);
    expect(pendingAnalysis.isProcessing).toBe(true);

    const completedAnalysis = new Analysis("analysis-2", "COMPLETED", 100, null, 25, []);
    expect(completedAnalysis.isFinished).toBe(true);
    expect(completedAnalysis.isProcessing).toBe(false);

    const failedAnalysis = new Analysis("analysis-3", "FAILED", 100, null, 12, ["Subprocess timeout"]);
    expect(failedAnalysis.isFinished).toBe(true);
    expect(failedAnalysis.isFailed).toBe(true);
  });

  it("should construct and combine TokenUsage value objects immutability", () => {
    const usageA = new TokenUsage(100, 50, 150, 0.005);
    const usageB = new TokenUsage(200, 100, 300, 0.010);
    const combined = usageA.plus(usageB);

    expect(combined.promptTokens).toBe(300);
    expect(combined.completionTokens).toBe(150);
    expect(combined.totalTokens).toBe(450);
    expect(combined.estimatedCostUsd).toBe(0.015);

    // Verify immutability by testing execution assignment crashes
    expect(() => {
      (usageA as unknown as { promptTokens: number }).promptTokens = 500;
    }).toThrow();
  });
});

describe("Phase 2 Domain Validation Rules", () => {
  it("should validate git repository URLs correctly", () => {
    expect(validateGitUrl("https://github.com/user/repo.git")).toBe(true);
    expect(validateGitUrl("git@github.com:user/repo.git")).toBe(true);
    expect(validateGitUrl("invalid-url")).toBe(false);
  });

  it("should identify path traversals correctly", () => {
    expect(isSafePath("src/app/page.tsx")).toBe(true);
    expect(isSafePath("../../etc/passwd")).toBe(false);
    expect(isSafePath("src/../app/page.tsx")).toBe(false);
  });

  it("should check ZIP file size limits correctly", () => {
    expect(validateZipSize(1024 * 1024 * 50, 100)).toBe(true); // 50MB is under 100MB limit
    expect(validateZipSize(1024 * 1024 * 150, 100)).toBe(false); // 150MB is over 100MB limit
  });
});

describe("Phase 2 Contract Schemas", () => {
  it("should successfully parse valid Login requests", () => {
    const payload = { username: "test@domain.com", password: "securepassword123" };
    const result = LoginRequestSchema.safeParse(payload);
    expect(result.success).toBe(true);
  });

  it("should reject invalid login request payloads", () => {
    const payload = { username: "bad-email", password: "short" };
    const result = LoginRequestSchema.safeParse(payload);
    expect(result.success).toBe(false);
  });

  it("should parse valid analysis statuses correctly", () => {
    const payload = {
      analysis_id: "8547f6b0-ed28-4d60-ade9-da892e2bd9d4",
      status: "PROCESSING",
      progress_percentage: 45.5,
      current_file: "src/main.py",
      total_files: 10,
      errors: []
    };
    const result = AnalysisStatusResponseSchema.safeParse(payload);
    expect(result.success).toBe(true);
  });
});

describe("Phase 2 DTO Mappers", () => {
  it("should map User DTO correctly to domain user entity", () => {
    const dto = {
      id: "8547f6b0-ed28-4d60-ade9-da892e2bd9d4",
      email: "mapper@test.com",
      name: "Alice",
      roles: ["editor"],
      permissions: ["run_scan"]
    };
    const entity = UserMapper.toDomain(dto);
    expect(entity instanceof User).toBe(true);
    expect(entity.email).toBe("mapper@test.com");
    expect(entity.hasPermission("run_scan")).toBe(true);
  });

  it("should map Report DTO to domain reports correctly", () => {
    const dto = {
      id: "8547f6b0-ed28-4d60-ade9-da892e2bd9d4",
      repository_id: "8547f6b0-ed28-4d60-ade9-da892e2bd9d4",
      created_at: "2026-07-16T10:00:00Z",
      files_reviewed: 1,
      total_issues: 1,
      issues_by_severity: { CRITICAL: 1 },
      issues_by_category: { SECURITY: 1 },
      average_score: 90.0,
      file_results: [
        {
          file_path: "src/app.py",
          score: 90,
          review_time_sec: 1.2,
          token_usage: {
            prompt_tokens: 10,
            completion_tokens: 5,
            total_tokens: 15,
            estimated_cost_usd: 0.0001
          },
          issues: [
            {
              id: "8547f6b0-ed28-4d60-ade9-da892e2bd9d4",
              file_path: "src/app.py",
              line_start: 1,
              line_end: 2,
              category: "SECURITY" as const,
              severity: "CRITICAL" as const,
              confidence: 0.95,
              description: "SQL Injection",
              explanation: "Input parameters directly concatenated",
              suggested_fix: "Use parameterized values",
              snippet: "query = 'SELECT * FROM users WHERE name = ' + name"
            }
          ]
        }
      ],
      token_usage: {
        prompt_tokens: 10,
        completion_tokens: 5,
        total_tokens: 15,
        estimated_cost_usd: 0.0001
      }
    };
    const report = ReportMapper.toReport(dto);
    expect(report instanceof RepositoryReviewReport).toBe(true);
    expect(report.formattedCost).toBe("$0.0001");
    expect(report.fileResults[0] instanceof FileReviewResult).toBe(true);
    expect(report.fileResults[0].issues[0] instanceof ReviewIssue).toBe(true);
    expect(report.fileResults[0].issues[0].isSecurity).toBe(true);
  });
});
