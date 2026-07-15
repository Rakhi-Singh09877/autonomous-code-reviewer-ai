import json
import logging
from typing import Optional, Dict, Any
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings
from app.domain.models.report import RepositoryReviewReport, FileReviewResult, TokenUsageMetadata
from app.domain.models.issue import ReviewIssue, ReviewIssueSeverity, ReviewIssueCategory
from app.use_cases.interfaces.db_port import DBPort
from app.infrastructure.database.models import Base, DBAnalysisRun
from pathlib import Path

logger = logging.getLogger("app.infrastructure.database.repository")

class SQLAlchemyDBAdapter(DBPort):
    """
    Adapter implementing DBPort using SQLAlchemy session.
    Automatically creates all tables on start up.
    """
    def __init__(self, database_url: Optional[str] = None) -> None:
        self.url = database_url or settings.DATABASE_URL
        
        # Ensure thread safety check is disabled only for SQLite
        connect_args = {}
        if self.url.startswith("sqlite"):
            connect_args["check_same_thread"] = False
            
        self.engine = create_engine(self.url, connect_args=connect_args)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    async def initialize(self) -> None:
        """
        Initializes the database schema and creates all tables.
        """
        import asyncio
        await asyncio.to_thread(Base.metadata.create_all, bind=self.engine)
        logger.info("Database tables initialized for url: %s", self.url)

    def _get_session(self) -> Session:
        return self.SessionLocal()
        
    def _serialize_report(self, report: RepositoryReviewReport) -> Dict[str, Any]:
        file_results = []
        for f in report.file_results:
            issues = []
            for issue in f.issues:
                issues.append({
                    "id": str(issue.id),
                    "file_path": str(issue.file_path),
                    "line_start": issue.line_start,
                    "line_end": issue.line_end,
                    "category": issue.category.value if hasattr(issue.category, "value") else str(issue.category),
                    "severity": issue.severity.value if hasattr(issue.severity, "value") else str(issue.severity),
                    "confidence": issue.confidence,
                    "description": issue.description,
                    "explanation": issue.explanation,
                    "suggested_fix": issue.suggested_fix,
                    "snippet": issue.snippet
                })
            file_results.append({
                "file_path": str(f.file_path),
                "issues": issues,
                "score": f.score,
                "review_time_sec": f.review_time_sec,
                "token_usage": {
                    "prompt_tokens": f.token_usage.prompt_tokens,
                    "completion_tokens": f.token_usage.completion_tokens,
                    "total_tokens": f.token_usage.total_tokens,
                    "estimated_cost_usd": f.token_usage.estimated_cost_usd
                }
            })
        return {
            "id": str(report.id),
            "repository_id": str(report.repository_id),
            "created_at": report.created_at.isoformat() if report.created_at else None,
            "files_reviewed": report.files_reviewed,
            "total_issues": report.total_issues,
            "issues_by_severity": report.issues_by_severity,
            "issues_by_category": report.issues_by_category,
            "average_score": report.average_score,
            "file_results": file_results,
            "token_usage": {
                "prompt_tokens": report.token_usage.prompt_tokens,
                "completion_tokens": report.token_usage.completion_tokens,
                "total_tokens": report.token_usage.total_tokens,
                "estimated_cost_usd": report.token_usage.estimated_cost_usd
            }
        }

    def _deserialize_report(self, data: Dict[str, Any]) -> RepositoryReviewReport:
        import uuid
        from datetime import datetime
        
        file_results = []
        for f in data.get("file_results", []):
            issues = []
            for issue in f.get("issues", []):
                issues.append(ReviewIssue(
                    id=uuid.UUID(issue["id"]),
                    file_path=Path(issue["file_path"]),
                    line_start=issue["line_start"],
                    line_end=issue["line_end"],
                    category=ReviewIssueCategory(issue["category"]),
                    severity=ReviewIssueSeverity(issue["severity"]),
                    confidence=issue["confidence"],
                    description=issue["description"],
                    explanation=issue["explanation"],
                    suggested_fix=issue["suggested_fix"],
                    snippet=issue["snippet"]
                ))
            tu = f.get("token_usage", {})
            file_results.append(FileReviewResult(
                file_path=Path(f["file_path"]),
                issues=issues,
                score=f["score"],
                review_time_sec=f["review_time_sec"],
                token_usage=TokenUsageMetadata(
                    prompt_tokens=tu.get("prompt_tokens", 0),
                    completion_tokens=tu.get("completion_tokens", 0),
                    total_tokens=tu.get("total_tokens", 0),
                    estimated_cost_usd=tu.get("estimated_cost_usd", 0.0)
                )
            ))
            
        tu_report = data.get("token_usage", {})
        created_at_str = data.get("created_at")
        created_at = datetime.fromisoformat(created_at_str) if created_at_str else None
        
        return RepositoryReviewReport(
            id=uuid.UUID(data["id"]),
            repository_id=uuid.UUID(data["repository_id"]),
            created_at=created_at,
            files_reviewed=data["files_reviewed"],
            total_issues=data["total_issues"],
            issues_by_severity=data["issues_by_severity"],
            issues_by_category=data["issues_by_category"],
            average_score=data["average_score"],
            file_results=file_results,
            token_usage=TokenUsageMetadata(
                prompt_tokens=tu_report.get("prompt_tokens", 0),
                completion_tokens=tu_report.get("completion_tokens", 0),
                total_tokens=tu_report.get("total_tokens", 0),
                estimated_cost_usd=tu_report.get("estimated_cost_usd", 0.0)
            )
        )

    async def create_analysis(self, analysis_id: str, repository_id: Optional[str] = None) -> None:
        with self._get_session() as session:
            db_run = DBAnalysisRun(
                analysis_id=analysis_id,
                repository_id=repository_id,
                status="PENDING",
                progress_percentage=0.0,
                errors="[]"
            )
            session.add(db_run)
            session.commit()

    async def update_analysis_progress(
        self,
        analysis_id: str,
        status: str,
        progress_percentage: float,
        current_file: Optional[str] = None,
        error: Optional[str] = None,
        total_files: Optional[int] = None
    ) -> None:
        with self._get_session() as session:
            db_run = session.query(DBAnalysisRun).filter_by(analysis_id=analysis_id).first()
            if db_run:
                db_run.status = status
                db_run.progress_percentage = progress_percentage
                if current_file is not None:
                    db_run.current_file = current_file
                if total_files is not None:
                    db_run.total_files = total_files
                if error:
                    try:
                        errs = json.loads(db_run.errors)
                    except Exception:
                        errs = []
                    errs.append(error)
                    db_run.errors = json.dumps(errs)
                session.commit()

    async def save_analysis_report(self, analysis_id: str, report: RepositoryReviewReport) -> None:
        with self._get_session() as session:
            db_run = session.query(DBAnalysisRun).filter_by(analysis_id=analysis_id).first()
            if db_run:
                db_run.status = "COMPLETED"
                db_run.progress_percentage = 100.0
                db_run.serialized_report = self._serialize_report(report)
                session.commit()

    async def get_analysis_state(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        with self._get_session() as session:
            db_run = session.query(DBAnalysisRun).filter_by(analysis_id=analysis_id).first()
            if not db_run:
                return None
            try:
                errors_list = json.loads(db_run.errors)
            except Exception:
                errors_list = []
            return {
                "analysis_id": db_run.analysis_id,
                "repository_id": db_run.repository_id,
                "status": db_run.status,
                "progress_percentage": db_run.progress_percentage,
                "current_file": db_run.current_file,
                "total_files": db_run.total_files,
                "errors": errors_list
            }

    async def get_analysis_report(self, analysis_id: str) -> Optional[RepositoryReviewReport]:
        with self._get_session() as session:
            db_run = session.query(DBAnalysisRun).filter_by(analysis_id=analysis_id).first()
            if not db_run or not db_run.serialized_report:
                return None
            return self._deserialize_report(db_run.serialized_report)

    async def check_health(self) -> bool:
        try:
            with self._get_session() as session:
                session.execute(select(1))
                return True
        except Exception as e:
            logger.warning("Database health check failed: %s", e)
            return False
