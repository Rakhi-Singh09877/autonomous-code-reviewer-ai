import { ReviewIssue, ReviewIssueSeverity, ReviewIssueCategory } from "./issue.entity";
import { TokenUsage } from "../value_objects/token-usage.value-object";

export class FileReviewResult {
  constructor(
    public readonly filePath: string,
    public readonly issues: ReviewIssue[],
    public readonly score: number,
    public readonly reviewTimeSec: number,
    public readonly tokenUsage: TokenUsage
  ) {}

  public get criticalIssuesCount(): number {
    return this.issues.filter(
      (issue) => issue.severity === "CRITICAL" || issue.severity === "HIGH"
    ).length;
  }
}

export class RepositoryReviewReport {
  constructor(
    public readonly id: string,
    public readonly repositoryId: string,
    public readonly createdAt: Date,
    public readonly filesReviewed: number,
    public readonly totalIssues: number,
    public readonly issuesBySeverity: Record<ReviewIssueSeverity, number>,
    public readonly issuesByCategory: Record<ReviewIssueCategory, number>,
    public readonly averageScore: number,
    public readonly fileResults: FileReviewResult[],
    public readonly tokenUsage: TokenUsage
  ) {}

  public get formattedCost(): string {
    return `$${this.tokenUsage.estimatedCostUsd.toFixed(4)}`;
  }
}
