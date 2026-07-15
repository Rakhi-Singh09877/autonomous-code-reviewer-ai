import os
from pathlib import Path
from app.domain.models.report import RepositoryReviewReport
from app.use_cases.interfaces.report_port import ReportPort

class MarkdownReportGenerator(ReportPort):
    """
    Adapter implementing ReportPort to format and serialize review reports to Markdown.
    """
    def __init__(self, output_dir: str = "./reports") -> None:
        self.output_dir = Path(output_dir)

    def generate_report(self, report: RepositoryReviewReport) -> str:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        md_lines = [
            f"# Codebase Review Report",
            f"- **Report ID**: `{report.id}`",
            f"- **Repository ID**: `{report.repository_id}`",
            f"- **Created At**: {report.created_at.strftime('%Y-%m-%d %H:%M:%S UTC') if report.created_at else 'N/A'}",
            f"- **Files Reviewed**: {report.files_reviewed}",
            f"- **Average Quality Score**: {report.average_score}/100",
            f"- **Total Issues Found**: {report.total_issues}",
            f"- **Token Usage**: {report.token_usage.total_tokens} tokens (Est. Cost: ${report.token_usage.estimated_cost_usd:.4f})",
            "",
            "## Issues by Severity"
        ]
        
        for sev, count in sorted(report.issues_by_severity.items()):
            md_lines.append(f"- **{sev}**: {count}")
            
        md_lines.append("")
        md_lines.append("## Issues by Category")
        for cat, count in sorted(report.issues_by_category.items()):
            md_lines.append(f"- **{cat}**: {count}")
            
        md_lines.append("")
        md_lines.append("## File Details")
        
        for file_res in report.file_results:
            md_lines.append(f"\n### File: `{file_res.file_path.name if hasattr(file_res.file_path, 'name') else str(file_res.file_path)}`")
            md_lines.append(f"- **Path**: `{file_res.file_path}`")
            md_lines.append(f"- **Score**: {file_res.score}/100")
            md_lines.append(f"- **Analysis Duration**: {file_res.review_time_sec:.2f}s")
            md_lines.append(f"- **Issues**: {len(file_res.issues)}")
            
            if file_res.issues:
                md_lines.append("")
                md_lines.append("| Line | Category | Severity | Description |")
                md_lines.append("| --- | --- | --- | --- |")
                for issue in file_res.issues:
                    # Retrieve severity/category values safely (which might be strings or enums)
                    sev_val = issue.severity.value if hasattr(issue.severity, 'value') else str(issue.severity)
                    cat_val = issue.category.value if hasattr(issue.category, 'value') else str(issue.category)
                    md_lines.append(f"| {issue.line_start}-{issue.line_end} | {cat_val} | {sev_val} | {issue.description} |")
                    
        report_content = "\n".join(md_lines)
        
        # Write to file
        report_file = self.output_dir / f"report_{report.id}.md"
        report_file.write_text(report_content, encoding="utf-8")
        
        return report_content
