export type ReviewIssueSeverity = "INFO" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type ReviewIssueCategory =
  | "CODE_QUALITY"
  | "BUG_DETECTION"
  | "SECURITY"
  | "PERFORMANCE"
  | "BEST_PRACTICES"
  | "MAINTAINABILITY"
  | "CODE_SMELLS"
  | "COMPLEXITY";

export class ReviewIssue {
  constructor(
    public readonly id: string,
    public readonly filePath: string,
    public readonly lineStart: number,
    public readonly lineEnd: number,
    public readonly category: ReviewIssueCategory,
    public readonly severity: ReviewIssueSeverity,
    public readonly confidence: number,
    public readonly description: string,
    public readonly explanation: string,
    public readonly suggestedFix: string,
    public readonly snippet: string
  ) {}

  public get isSecurity(): boolean {
    return this.category === "SECURITY";
  }

  public get isCritical(): boolean {
    return this.severity === "CRITICAL" || this.severity === "HIGH";
  }
}
