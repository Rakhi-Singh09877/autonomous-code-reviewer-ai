import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from fastapi.testclient import TestClient
from celery.exceptions import Retry
from datetime import datetime, timezone, timedelta

# Ensure app path imports work
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.factory import ServiceFactory
from app.use_cases.interfaces.job_queue_port import JobQueuePort
from app.infrastructure.queue.celery_adapter import CeleryJobQueueAdapter
from app.infrastructure.queue.celery_tasks import analyze_repo_task
from app.use_cases.analysis.runner import IdempotencyGuard, JobStatusManager, AnalysisRunner
from app.domain.exceptions.agent_exceptions import LLMRateLimitException
from app.domain.exceptions.repository_exceptions import InvalidRepositoryURLException
from app.infrastructure.api.dependencies import get_job_queue, get_db_port
from app.main import app

def test_job_queue_port_abstraction():
    """
    Asserts that JobQueuePort is an abstract class and cannot be instantiated directly.
    """
    with pytest.raises(TypeError):
        JobQueuePort()

def test_celery_job_queue_adapter_dispatch():
    """
    Verifies that the adapter correctly schedules tasks with delays and metadata timestamps.
    """
    adapter = CeleryJobQueueAdapter()
    
    with patch("app.infrastructure.queue.celery_adapter.analyze_repo_task.delay") as mock_delay:
        adapter.enqueue_analysis(
            analysis_id="test-id-123",
            git_url="https://github.com/org/repo.git",
            branch="main",
            focus_areas=["security"],
            max_issues_per_file=10
        )
        mock_delay.assert_called_once()
        args, kwargs = mock_delay.call_args
        assert kwargs["analysis_id"] == "test-id-123"
        assert kwargs["git_url"] == "https://github.com/org/repo.git"
        assert kwargs["branch"] == "main"
        assert kwargs["focus_areas"] == ["security"]
        assert kwargs["max_issues_per_file"] == 10
        assert "enqueued_at" in kwargs

def test_api_independence_from_celery():
    """
    Validates that API endpoints interact only with the JobQueuePort and do not trigger worker processes.
    """
    mock_queue = MagicMock(spec=JobQueuePort)
    app.dependency_overrides[get_job_queue] = lambda: mock_queue
    
    mock_db = MagicMock()
    mock_db.create_analysis = AsyncMock()
    app.dependency_overrides[get_db_port] = lambda: mock_db
    
    try:
        client = TestClient(app)
        res = client.post(
            "/api/v1/analyze",
            data={"git_url": "https://github.com/org/repo.git"}
        )
        assert res.status_code == 202
        data = res.json()
        assert "analysis_id" in data
        assert data["status"] == "PENDING"
        
        mock_queue.enqueue_analysis.assert_called_once()
    finally:
        app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_idempotency_guard_completed_runs():
    """
    Ensures that IdempotencyGuard blocks execution of already completed reports.
    """
    mock_db = MagicMock()
    mock_db.get_analysis_state = AsyncMock(return_value={"status": "COMPLETED"})
    
    guard = IdempotencyGuard(db_port=mock_db)
    should_run, reason = await guard.validate_and_claim("test-id")
    assert should_run is False
    assert "completed" in reason.lower()

@pytest.mark.asyncio
async def test_idempotency_guard_processing_active_and_stale_runs():
    """
    Ensures that IdempotencyGuard blocks fresh active scans but recovers stale runs.
    """
    mock_db = MagicMock()
    now = datetime.now(timezone.utc)
    
    # 1. Fresh active run (updated 10 seconds ago) -> Skip
    mock_db.get_analysis_state = AsyncMock(return_value={
        "status": "PROCESSING",
        "updated_at": (now - timedelta(seconds=10)).isoformat()
    })
    guard = IdempotencyGuard(db_port=mock_db)
    should_run, reason = await guard.validate_and_claim("test-id")
    assert should_run is False
    assert "processing" in reason.lower()

    # 2. Stale run (updated 45 minutes ago) -> Recover and Run
    mock_db.get_analysis_state = AsyncMock(return_value={
        "status": "PROCESSING",
        "updated_at": (now - timedelta(minutes=45)).isoformat()
    })
    should_run, reason = await guard.validate_and_claim("test-id")
    assert should_run is True
    assert "stale" in reason.lower()

def test_celery_task_retry_policies():
    """
    Asserts that tasks retry on rate limits and fail fast without retry on parameter validation errors.
    """
    mock_request = MagicMock()
    mock_request.retries = 0
    
    # 1. LLMRateLimitException -> retried
    with patch("celery.app.task.Task.request", new_callable=PropertyMock, return_value=mock_request), \
         patch("app.infrastructure.queue.celery_tasks.analyze_repo_task.retry", new_callable=MagicMock, side_effect=Retry("Simulated retry")) as mock_retry, \
         patch("app.infrastructure.queue.celery_tasks.ServiceFactory.get_orchestrator") as mock_orch, \
         patch("app.infrastructure.queue.celery_tasks.ServiceFactory.get_db_port"), \
         patch("app.infrastructure.queue.celery_tasks.AnalysisRunner.execute", side_effect=LLMRateLimitException("Rate limit")):
         
         with pytest.raises(Retry):
             analyze_repo_task.run(
                 analysis_id="test-id",
                 git_url="https://github.com/org/repo.git"
             )
         mock_retry.assert_called_once()
         
    # 2. InvalidRepositoryURLException -> fail fast without retry
    with patch("celery.app.task.Task.request", new_callable=PropertyMock, return_value=mock_request), \
         patch("app.infrastructure.queue.celery_tasks.analyze_repo_task.retry", new_callable=MagicMock, side_effect=Retry("Simulated retry")) as mock_retry, \
         patch("app.infrastructure.queue.celery_tasks.ServiceFactory.get_orchestrator"), \
         patch("app.infrastructure.queue.celery_tasks.ServiceFactory.get_db_port"), \
         patch("app.infrastructure.queue.celery_tasks.AnalysisRunner.execute", side_effect=InvalidRepositoryURLException("Invalid URL")):
         
         with pytest.raises(InvalidRepositoryURLException):
             analyze_repo_task.run(
                 analysis_id="test-id",
                 git_url="invalid-url"
             )
         mock_retry.assert_not_called()

def test_metrics_publication_on_task_run():
    """
    Asserts that queue wait time latency and execution duration metrics are published via MetricsPort.
    """
    mock_request = MagicMock()
    mock_request.retries = 0
    mock_metrics = MagicMock()
    
    with patch("celery.app.task.Task.request", new_callable=PropertyMock, return_value=mock_request), \
         patch("app.infrastructure.queue.celery_tasks.ServiceFactory.get_metrics_port", return_value=mock_metrics), \
         patch("app.infrastructure.queue.celery_tasks.ServiceFactory.get_orchestrator"), \
         patch("app.infrastructure.queue.celery_tasks.ServiceFactory.get_db_port"), \
         patch("app.infrastructure.queue.celery_tasks.AnalysisRunner.execute"):
         
         analyze_repo_task.run(
             analysis_id="test-id",
             git_url="https://github.com/org/repo.git",
             enqueued_at=time.time() - 15.0
         )
         
         # Verify queue waiting time recorded
         mock_metrics.record_queue_waiting_time.assert_called_once()
         args, _ = mock_metrics.record_queue_waiting_time.call_args
         assert args[0] >= 15.0
         
         # Verify task execution duration recorded
         mock_metrics.record_worker_execution_duration.assert_called_once()

def test_redis_unavailable_handling():
    """
    Asserts that failures are raised gracefully if connection to the queue broker fails.
    """
    adapter = CeleryJobQueueAdapter()
    
    with patch("app.infrastructure.queue.celery_adapter.analyze_repo_task.delay", side_effect=ConnectionError("Redis server unavailable")):
        with pytest.raises(ConnectionError):
            adapter.enqueue_analysis(analysis_id="test-id")
