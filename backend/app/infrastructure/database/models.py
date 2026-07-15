import json
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, Text, DateTime, JSON
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class DBAnalysisRun(Base):
    """
    SQLAlchemy Database Model representing the state and report metadata of a code review run.
    """
    __tablename__ = "analysis_runs"

    analysis_id = Column(String, primary_key=True, index=True)
    repository_id = Column(String, nullable=True)
    status = Column(String, default="PENDING")
    progress_percentage = Column(Float, default=0.0)
    current_file = Column(String, nullable=True)
    total_files = Column(Integer, default=0)
    errors = Column(Text, default="[]")  # Store errors list as a JSON serialized string
    serialized_report = Column(JSON, nullable=True)  # Store aggregated RepositoryReviewReport
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
