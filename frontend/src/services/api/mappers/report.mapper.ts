import {
  TokenUsageMetadataDTO,
  ReviewIssueDTO,
  FileReviewResultDTO,
  RepositoryReviewReportDTO,
} from "../../../contracts/reports.contract";
import { ReviewIssue } from "../../../domain/entities/issue.entity";
import { FileReviewResult, RepositoryReviewReport } from "../../../domain/entities/report.entity";
import { TokenUsage } from "../../../domain/value_objects/token-usage.value-object";

export class ReportMapper {
  public static toTokenUsage(dto: TokenUsageMetadataDTO): TokenUsage {
    return new TokenUsage(
      dto.prompt_tokens,
      dto.completion_tokens,
      dto.total_tokens,
      dto.estimated_cost_usd
    );
  }

  public static toIssue(dto: ReviewIssueDTO): ReviewIssue {
    return new ReviewIssue(
      dto.id,
      dto.file_path,
      dto.line_start,
      dto.line_end,
      dto.category,
      dto.severity,
      dto.confidence,
      dto.description,
      dto.explanation,
      dto.suggested_fix,
      dto.snippet
    );
  }

  public static toFileResult(dto: FileReviewResultDTO): FileReviewResult {
    return new FileReviewResult(
      dto.file_path,
      dto.issues.map((i) => ReportMapper.toIssue(i)),
      dto.score,
      dto.review_time_sec,
      ReportMapper.toTokenUsage(dto.token_usage)
    );
  }

  public static toReport(dto: RepositoryReviewReportDTO): RepositoryReviewReport {
    return new RepositoryReviewReport(
      dto.id,
      dto.repository_id,
      new Date(dto.created_at),
      dto.files_reviewed,
      dto.total_issues,
      dto.issues_by_severity,
      dto.issues_by_category,
      dto.average_score,
      dto.file_results.map((fr) => ReportMapper.toFileResult(fr)),
      ReportMapper.toTokenUsage(dto.token_usage)
    );
  }
}
