from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class AnalysisInitiateResponse(BaseModel):
    """Schema returning the initiated analysis tracking ID."""
    analysis_id: str = Field(..., description="Unique UUID tracking the initiated repository analysis.")
    status: str = Field(..., description="Initial processing status (e.g. PENDING).")

class AnalysisStatusResponse(BaseModel):
    """Schema returning the current status and progress metrics of an analysis run."""
    analysis_id: str
    status: str = Field(..., description="Processing status (PENDING, PROCESSING, COMPLETED, FAILED).")
    progress_percentage: float = Field(..., description="Incremental progress percentage from 0.0 to 100.0.")
    current_file: Optional[str] = Field(None, description="The file currently being reviewed by the AI agent.")
    total_files: int = Field(0, description="The total number of files detected in the repository.")
    errors: List[str] = Field(default_factory=list, description="A list of warnings or failures logged during analysis.")

class HealthStatusDetail(BaseModel):
    """Schema returning healthy status checks of all system ports and runtime telemetry."""
    status: str
    details: Dict[str, str] = Field(..., description="A key-value check of system dependencies (database, llm, rag, loader).")
    application_version: Optional[str] = Field(None, description="Active application semantic version.")
    uptime: Optional[float] = Field(None, description="System uptime duration in seconds.")
    startup_timestamp: Optional[str] = Field(None, description="Application startup timestamp.")

class ReadinessStatusDetail(BaseModel):
    """Schema returning readiness checks details for operational dependency ports."""
    status: str
    details: Dict[str, str] = Field(..., description="Telemetry details for database, llm, rag, and repository loader components.")
