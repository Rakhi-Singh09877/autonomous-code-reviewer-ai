import logging
import time
import uuid
from pathlib import Path
from typing import List, Dict, Any, Tuple

from app.core.config import settings
from app.domain.exceptions.agent_exceptions import ReviewValidationException
from app.domain.models.analysis import ReviewPolicy
from app.domain.models.issue import ReviewIssue, ReviewIssueSeverity, ReviewIssueCategory
from app.domain.models.parser import ParsedFile
from app.domain.models.report import FileReviewResult, TokenUsageMetadata
from app.domain.models.embedding import SearchResult
from app.use_cases.interfaces.llm_port import LLMPort
from app.use_cases.interfaces.agent_ports import ReviewAgentPort
from app.infrastructure.llm.prompts.builder import PromptBuilder

logger = logging.getLogger("app.infrastructure.agents.review_agent")

REVIEW_ISSUES_SCHEMA = {
    "type": "object",
    "properties": {
        "issues": {
            "type": "array",
            "description": "A list of issues found during code review.",
            "items": {
                "type": "object",
                "properties": {
                    "line_start": {
                        "type": "integer",
                        "description": "The line number in the source file where the issue begins (1-indexed)."
                    },
                    "line_end": {
                        "type": "integer",
                        "description": "The line number in the source file where the issue ends (1-indexed)."
                    },
                    "category": {
                        "type": "string",
                        "enum": [
                            "CODE_QUALITY", "BUG_DETECTION", "SECURITY",
                            "PERFORMANCE", "BEST_PRACTICES", "MAINTAINABILITY",
                            "CODE_SMELLS", "COMPLEXITY"
                        ],
                        "description": "The category of the issue."
                    },
                    "severity": {
                        "type": "string",
                        "enum": ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"],
                        "description": "The severity level of the issue."
                    },
                    "confidence": {
                        "type": "number",
                        "description": "The confidence score for this finding (value from 0.0 to 1.0)."
                    },
                    "description": {
                        "type": "string",
                        "description": "A brief summary of the issue (1 sentence)."
                    },
                    "explanation": {
                        "type": "string",
                        "description": "A detailed explanation of why this is an issue and its impact."
                    },
                    "suggested_fix": {
                        "type": "string",
                        "description": "A recommended code correction block showing how to fix the issue."
                    },
                    "snippet": {
                        "type": "string",
                        "description": "The original line or snippet of code affected by this issue."
                    }
                },
                "required": [
                    "line_start", "line_end", "category", "severity",
                    "confidence", "description", "explanation", "suggested_fix", "snippet"
                ]
            }
        }
    },
    "required": ["issues"]
}

class ReviewAgent(ReviewAgentPort):
    """
    ReviewAgent implementing ReviewAgentPort.
    Handles repository code analysis orchestrating LLM execution and verification.
    """

    def __init__(self, llm_port: LLMPort) -> None:
        self._llm_port = llm_port

    async def analyze_file(
        self,
        file_path: Path,
        parsed_file: ParsedFile,
        repo_context: str,
        rag_chunks: List[SearchResult],
        policy: ReviewPolicy
    ) -> FileReviewResult:
        """
        Executes code quality review on a file.
        Detects context limitations and splits requests dynamically if needed.
        """
        start_time = time.perf_counter()
        
        # Read the file content safely
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {str(e)}")
            return FileReviewResult(file_path=file_path, issues=[], score=100)

        lines = content.splitlines()
        total_lines_count = len(lines)
        
        repo_metadata = {
            "repository_context": repo_context,
            "complexity_score": getattr(parsed_file, "complexity_score", 0),
            "line_count": total_lines_count,
            "has_tests": getattr(parsed_file, "has_tests", False)
        }

        # Build initial full prompt to check token limits
        system_prompt, user_prompt = PromptBuilder.build_prompts(
            file_path=str(parsed_file.relative_path),
            language=parsed_file.language,
            repo_metadata=repo_metadata,
            policy=policy,
            rag_chunks=rag_chunks,
            file_content=content
        )

        estimated_tokens = self._estimate_tokens(system_prompt + user_prompt)
        logger.info(f"File {file_path} review prompt estimation: {estimated_tokens} tokens.")

        all_issues: List[ReviewIssue] = []
        total_token_usage = TokenUsageMetadata()

        # Split review into chunks if token limit is exceeded
        if estimated_tokens > settings.REVIEW_CONTEXT_WINDOW_LIMIT:
            logger.warning(
                f"File {file_path} exceeds context limit ({estimated_tokens} > {settings.REVIEW_CONTEXT_WINDOW_LIMIT}). "
                "Splitting review into chunks."
            )
            chunks = self._chunk_file_content(lines, chunk_line_size=1000)
            
            line_offset = 0
            for chunk_content in chunks:
                chunk_len = len(chunk_content.splitlines())
                
                # Render prompts with offset context
                chunk_sys, chunk_usr = PromptBuilder.build_prompts(
                    file_path=str(parsed_file.relative_path),
                    language=parsed_file.language,
                    repo_metadata=repo_metadata,
                    policy=policy,
                    rag_chunks=rag_chunks,
                    file_content=chunk_content,
                    line_offset=line_offset
                )

                chunk_output, chunk_usage = await self._llm_port.generate_structured_output(
                    system_prompt=chunk_sys,
                    user_prompt=chunk_usr,
                    schema=REVIEW_ISSUES_SCHEMA
                )
                
                total_token_usage.add(chunk_usage)
                chunk_issues = self._process_and_validate_issues(
                    raw_issues=chunk_output.get("issues", []),
                    file_path=file_path,
                    total_lines=total_lines_count,
                    chunk_start_line=line_offset + 1,
                    chunk_end_line=line_offset + chunk_len
                )
                all_issues.extend(chunk_issues)
                line_offset += chunk_len
        else:
            # File is within safety limits, execute direct call
            output_data, usage = await self._llm_port.generate_structured_output(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=REVIEW_ISSUES_SCHEMA
            )
            total_token_usage.add(usage)
            issues = self._process_and_validate_issues(
                raw_issues=output_data.get("issues", []),
                file_path=file_path,
                total_lines=total_lines_count
            )
            all_issues.extend(issues)

        # Deduplicate issues based on line ranges and description
        deduplicated = self._deduplicate_issues(all_issues)
        
        # Limit issues to policy limits
        if len(deduplicated) > policy.max_issues_per_file:
            logger.info(f"Limiting file issues count to policy max: {policy.max_issues_per_file}")
            deduplicated = sorted(deduplicated, key=lambda x: self._severity_weight(x.severity), reverse=True)
            deduplicated = deduplicated[:policy.max_issues_per_file]

        # Calculate final code health score
        score = self._calculate_score(deduplicated)
        review_time = time.perf_counter() - start_time

        return FileReviewResult(
            file_path=file_path,
            issues=deduplicated,
            score=score,
            review_time_sec=review_time,
            token_usage=total_token_usage
        )

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimates the number of tokens using character-to-token ratio (approx 4 chars = 1 token).
        """
        return len(text) // 4

    def _chunk_file_content(self, lines: List[str], chunk_line_size: int) -> List[str]:
        """
        Groups lines of file content into specific block chunks.
        """
        chunks = []
        for i in range(0, len(lines), chunk_line_size):
            chunks.append("\n".join(lines[i:i + chunk_line_size]))
        return chunks

    def _process_and_validate_issues(
        self,
        raw_issues: List[Dict[str, Any]],
        file_path: Path,
        total_lines: int,
        chunk_start_line: int = 1,
        chunk_end_line: int = None
    ) -> List[ReviewIssue]:
        """
        Maps dictionary responses into ReviewIssue domain structures and verifies line number ranges.
        """
        if chunk_end_line is None:
            chunk_end_line = total_lines

        processed = []
        for raw in raw_issues:
            try:
                line_start = int(raw.get("line_start", 1))
                line_end = int(raw.get("line_end", line_start))

                # Bounds validation & clipping
                line_start = max(1, min(line_start, total_lines))
                line_end = max(1, min(line_end, total_lines))
                if line_start > line_end:
                    line_start, line_end = line_end, line_start

                # Assert issue category matches Enum values
                try:
                    category = ReviewIssueCategory(raw.get("category", "CODE_QUALITY"))
                except ValueError:
                    category = ReviewIssueCategory.CODE_QUALITY

                # Assert severity matches Enum values
                try:
                    severity = ReviewIssueSeverity(raw.get("severity", "INFO"))
                except ValueError:
                    severity = ReviewIssueSeverity.INFO

                confidence = float(raw.get("confidence", 0.8))
                confidence = max(0.0, min(1.0, confidence))

                issue = ReviewIssue(
                    id=uuid.uuid4(),
                    file_path=file_path,
                    line_start=line_start,
                    line_end=line_end,
                    category=category,
                    severity=severity,
                    confidence=confidence,
                    description=raw.get("description", "Code quality issue detected."),
                    explanation=raw.get("explanation", ""),
                    suggested_fix=raw.get("suggested_fix", ""),
                    snippet=raw.get("snippet", "")
                )
                processed.append(issue)
            except Exception as e:
                logger.error(f"Error mapping issue record: {str(e)}")
                continue
        return processed

    def _deduplicate_issues(self, issues: List[ReviewIssue]) -> List[ReviewIssue]:
        """
        Deduplicates code issues by signature (line start, category, snippet).
        """
        seen = set()
        deduplicated = []
        for issue in issues:
            key = (issue.line_start, issue.category.value, issue.snippet.strip())
            if key not in seen:
                seen.add(key)
                deduplicated.append(issue)
        return deduplicated

    def _severity_weight(self, severity: ReviewIssueSeverity) -> int:
        weights = {
            ReviewIssueSeverity.INFO: 0,
            ReviewIssueSeverity.LOW: 2,
            ReviewIssueSeverity.MEDIUM: 5,
            ReviewIssueSeverity.HIGH: 10,
            ReviewIssueSeverity.CRITICAL: 25
        }
        return weights.get(severity, 0)

    def _calculate_score(self, issues: List[ReviewIssue]) -> int:
        """
        Computes 0-100 quality score by applying deductions weighted by severity.
        """
        total_deduction = 0
        for issue in issues:
            total_deduction += self._severity_weight(issue.severity)
        
        score = 100 - total_deduction
        return max(0, min(100, score))
