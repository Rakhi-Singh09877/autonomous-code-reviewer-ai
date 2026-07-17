import io
import uuid
import pytest
import zipfile
import sys
import json
from pathlib import Path
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

# Ensure app directory is on the path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.main import app
from app.infrastructure.api.dependencies import get_orchestrator, get_db_port, get_llm_port, get_rag_port, get_loader_port, get_job_queue
from app.use_cases.interfaces.job_queue_port import JobQueuePort
from app.use_cases.orchestrator import RepositoryAnalysisOrchestrator
from app.use_cases.interfaces.db_port import DBPort
from app.use_cases.interfaces.llm_port import LLMPort
from app.use_cases.interfaces.rag_port import RAGPort
from app.use_cases.interfaces.loader_port import RepositoryLoaderPort
from app.domain.models.report import RepositoryReviewReport, TokenUsageMetadata

@pytest.fixture
def mock_db():
    db = MagicMock(spec=DBPort)
    db.check_health = AsyncMock(return_value=True)
    db.create_analysis = AsyncMock()
    db.update_analysis_progress = AsyncMock()
    db.save_analysis_report = AsyncMock()
    return db

@pytest.fixture
def mock_orchestrator():
    return MagicMock(spec=RepositoryAnalysisOrchestrator)

@pytest.fixture
def mock_llm():
    llm = MagicMock(spec=LLMPort)
    llm.check_health = AsyncMock(return_value=True)
    return llm

@pytest.fixture
def mock_rag():
    rag = MagicMock(spec=RAGPort)
    rag.check_health = AsyncMock(return_value=True)
    return rag

@pytest.fixture
def mock_loader():
    loader = MagicMock(spec=RepositoryLoaderPort)
    loader.check_health = MagicMock(return_value=True)
    return loader

@pytest.fixture
def mock_queue():
    return MagicMock(spec=JobQueuePort)

@pytest.fixture
def client(mock_db, mock_orchestrator, mock_llm, mock_rag, mock_loader, mock_queue):
    app.dependency_overrides[get_db_port] = lambda: mock_db
    app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator
    app.dependency_overrides[get_llm_port] = lambda: mock_llm
    app.dependency_overrides[get_rag_port] = lambda: mock_rag
    app.dependency_overrides[get_loader_port] = lambda: mock_loader
    app.dependency_overrides[get_job_queue] = lambda: mock_queue
    
    with TestClient(app) as test_client:
        yield test_client
        
    app.dependency_overrides.clear()

def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "online"

def test_analyze_git_success(client, mock_db, mock_orchestrator):
    response = client.post(
        "/api/v1/analyze",
        data={"git_url": "https://github.com/test/repo", "branch": "main"}
    )
    assert response.status_code == 202
    data = response.json()
    assert "analysis_id" in data
    assert data["status"] == "PENDING"
    
    mock_db.create_analysis.assert_called_once()

def test_analyze_zip_success(client, mock_db, mock_orchestrator):
    # Construct a valid tiny ZIP file dynamically to satisfy zipfile.ZipFile validation
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("dummy.py", "print('hello')")
    zip_data = zip_buffer.getvalue()
    
    file_payload = {"file": ("repo.zip", zip_data, "application/zip")}
    
    response = client.post(
        "/api/v1/analyze",
        files=file_payload,
        data={"max_issues_per_file": 10}
    )
    assert response.status_code == 202
    data = response.json()
    assert "analysis_id" in data
    assert data["status"] == "PENDING"

def test_analyze_invalid_inputs(client):
    # Neither git_url nor file
    response = client.post("/api/v1/analyze")
    assert response.status_code == 400
    assert "Either git_url or file" in response.json()["detail"]
    
    # Both git_url and file
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("dummy.py", "print('hello')")
    zip_data = zip_buffer.getvalue()
    
    response = client.post(
        "/api/v1/analyze",
        files={"file": ("repo.zip", zip_data, "application/zip")},
        data={"git_url": "https://github.com/test/repo"}
    )
    assert response.status_code == 400
    assert "Provide either git_url or file upload, not both" in response.json()["detail"]

def test_get_analysis_status_success(client, mock_db):
    analysis_id = str(uuid.uuid4())
    mock_db.get_analysis_state.return_value = {
        "analysis_id": analysis_id,
        "repository_id": str(uuid.uuid4()),
        "status": "PROCESSING",
        "progress_percentage": 55.5,
        "current_file": "main.py",
        "total_files": 42,
        "errors": ["Warning: parsing fallback"]
    }
    
    response = client.get(f"/api/v1/analysis/{analysis_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["analysis_id"] == analysis_id
    assert data["status"] == "PROCESSING"
    assert data["progress_percentage"] == 55.5
    assert data["total_files"] == 42
    assert "Warning: parsing fallback" in data["errors"]

def test_get_analysis_status_not_found(client, mock_db):
    mock_db.get_analysis_state.return_value = None
    response = client.get(f"/api/v1/analysis/{uuid.uuid4()}")
    assert response.status_code == 404

def test_get_analysis_report_completed(client, mock_db):
    analysis_id = str(uuid.uuid4())
    repo_id = uuid.uuid4()
    
    mock_db.get_analysis_state.return_value = {
        "analysis_id": analysis_id,
        "repository_id": str(repo_id),
        "status": "COMPLETED",
        "progress_percentage": 100.0,
        "current_file": None,
        "total_files": 2,
        "errors": []
    }
    
    mock_report = RepositoryReviewReport(
        id=uuid.uuid4(),
        repository_id=repo_id,
        created_at=datetime.now(timezone.utc),
        files_reviewed=2,
        total_issues=0,
        issues_by_severity={},
        issues_by_category={},
        average_score=100.0,
        file_results=[],
        token_usage=TokenUsageMetadata(0, 0, 0, 0.0)
    )
    mock_db.get_analysis_report.return_value = mock_report
    
    response = client.get(f"/api/v1/analysis/{analysis_id}/report")
    assert response.status_code == 200
    data = response.json()
    assert data["files_reviewed"] == 2
    assert data["average_score"] == 100.0

def test_get_analysis_report_not_completed_yet(client, mock_db):
    analysis_id = str(uuid.uuid4())
    mock_db.get_analysis_state.return_value = {
        "analysis_id": analysis_id,
        "repository_id": str(uuid.uuid4()),
        "status": "PROCESSING",
        "progress_percentage": 50.0,
        "current_file": "main.py",
        "total_files": 5,
        "errors": []
    }
    
    response = client.get(f"/api/v1/analysis/{analysis_id}/report")
    assert response.status_code == 400
    assert "report is not ready" in response.json()["detail"]

def test_health_check_healthy(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["details"]["database"] == "healthy"
    assert data["details"]["llm"] == "healthy"
    assert data["details"]["rag"] == "healthy"
    assert data["details"]["repository_loader"] == "healthy"

def test_health_check_unhealthy(client, mock_db):
    # Database check unhealthy
    mock_db.check_health.return_value = False
    
    response = client.get("/api/v1/health")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["details"]["database"] == "unhealthy"

def test_sse_invalid_uuid(client):
    response = client.get("/api/v1/events/sse?analysis_id=invalid-uuid")
    assert response.status_code == 400
    assert "Must be a valid UUID" in response.json()["detail"]

def test_sse_unknown_analysis(client, mock_db):
    mock_db.get_analysis_state.return_value = None
    unknown_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/events/sse?analysis_id={unknown_id}")
    assert response.status_code == 404
    assert "Analysis job not found" in response.json()["detail"]

def test_sse_active_streaming_and_terminal_completion(client, mock_db):
    analysis_id = str(uuid.uuid4())
    # Mock status transition: PENDING -> COMPLETED
    # Need 4 states: 1 for route validation check, 3 for active generator loop
    states = [
        {
            "analysis_id": analysis_id,
            "repository_id": str(uuid.uuid4()),
            "status": "PENDING",
            "progress_percentage": 0.0,
            "current_file": None,
            "total_files": 0,
            "errors": []
        },
        {
            "analysis_id": analysis_id,
            "repository_id": str(uuid.uuid4()),
            "status": "PENDING",
            "progress_percentage": 0.0,
            "current_file": None,
            "total_files": 0,
            "errors": []
        },
        {
            "analysis_id": analysis_id,
            "repository_id": str(uuid.uuid4()),
            "status": "PROCESSING",
            "progress_percentage": 50.0,
            "current_file": "main.py",
            "total_files": 2,
            "errors": []
        },
        {
            "analysis_id": analysis_id,
            "repository_id": str(uuid.uuid4()),
            "status": "COMPLETED",
            "progress_percentage": 100.0,
            "current_file": "done.py",
            "total_files": 2,
            "errors": []
        }
    ]
    
    mock_db.get_analysis_state.side_effect = states
    
    response = client.get(f"/api/v1/events/sse?analysis_id={analysis_id}")
    assert response.status_code == 200
    assert "text/event-stream" in (response.headers.get("content-type") or "")
    
    events = []
    for line in response.iter_lines():
        if line.startswith("data: "):
            data_str = line[len("data: "):]
            events.append(json.loads(data_str))
            
    assert len(events) == 3
    assert events[0]["payload"]["status"] == "PENDING"
    assert events[1]["payload"]["status"] == "PROCESSING"
    assert events[1]["payload"]["progress_percentage"] == 50.0
    assert events[2]["payload"]["status"] == "COMPLETED"

def test_sse_disconnect_cleanup(client, mock_db):
    analysis_id = str(uuid.uuid4())
    # Return 3 states: 1 for validation check, 2 for generator loop
    states = [
        {
            "analysis_id": analysis_id,
            "repository_id": str(uuid.uuid4()),
            "status": "PROCESSING",
            "progress_percentage": 25.0,
            "current_file": "foo.py",
            "total_files": 10,
            "errors": []
        },
        {
            "analysis_id": analysis_id,
            "repository_id": str(uuid.uuid4()),
            "status": "PROCESSING",
            "progress_percentage": 25.0,
            "current_file": "foo.py",
            "total_files": 10,
            "errors": []
        },
        {
            "analysis_id": analysis_id,
            "repository_id": str(uuid.uuid4()),
            "status": "COMPLETED",
            "progress_percentage": 100.0,
            "current_file": "foo.py",
            "total_files": 10,
            "errors": []
        }
    ]
    mock_db.get_analysis_state.side_effect = states
    
    # Read only the first event and close the connection
    response = client.get(f"/api/v1/events/sse?analysis_id={analysis_id}")
    assert response.status_code == 200
    assert "text/event-stream" in (response.headers.get("content-type") or "")
    # Read first event line
    lines = response.iter_lines()
    first_line = next(lines)
    assert first_line.startswith("data: ")
    # Close connection (simulates disconnect)
    response.close()

def test_ws_missing_analysis_id(client):
    with client.websocket_connect("/api/v1/events/ws") as websocket:
        with pytest.raises(WebSocketDisconnect) as exc_info:
            websocket.receive_text()
        assert exc_info.value.code == 1008

def test_ws_invalid_uuid(client):
    with client.websocket_connect("/api/v1/events/ws?analysis_id=invalid-uuid") as websocket:
        with pytest.raises(WebSocketDisconnect) as exc_info:
            websocket.receive_text()
        assert exc_info.value.code == 1008

def test_ws_unknown_analysis(client, mock_db):
    mock_db.get_analysis_state.return_value = None
    unknown_id = str(uuid.uuid4())
    with client.websocket_connect(f"/api/v1/events/ws?analysis_id={unknown_id}") as websocket:
        with pytest.raises(WebSocketDisconnect) as exc_info:
            websocket.receive_text()
        assert exc_info.value.code == 1008

def test_ws_successful_connection_and_updates(client, mock_db):
    analysis_id = str(uuid.uuid4())
    # 1 state check for validation, plus states for loop
    states = [
        {
            "analysis_id": analysis_id,
            "repository_id": str(uuid.uuid4()),
            "status": "PENDING",
            "progress_percentage": 0.0,
            "current_file": None,
            "total_files": 0,
            "errors": []
        },
        {
            "analysis_id": analysis_id,
            "repository_id": str(uuid.uuid4()),
            "status": "PENDING",
            "progress_percentage": 0.0,
            "current_file": None,
            "total_files": 0,
            "errors": []
        },
        {
            "analysis_id": analysis_id,
            "repository_id": str(uuid.uuid4()),
            "status": "PROCESSING",
            "progress_percentage": 50.0,
            "current_file": "main.py",
            "total_files": 2,
            "errors": []
        },
        {
            "analysis_id": analysis_id,
            "repository_id": str(uuid.uuid4()),
            "status": "COMPLETED",
            "progress_percentage": 100.0,
            "current_file": "done.py",
            "total_files": 2,
            "errors": []
        }
    ]
    mock_db.get_analysis_state.side_effect = states
    
    with client.websocket_connect(f"/api/v1/events/ws?analysis_id={analysis_id}") as websocket:
        # Receive first update (PENDING)
        msg1 = websocket.receive_json()
        assert msg1["payload"]["status"] == "PENDING"
        
        # Receive second update (PROCESSING)
        msg2 = websocket.receive_json()
        assert msg2["payload"]["status"] == "PROCESSING"
        assert msg2["payload"]["progress_percentage"] == 50.0
        
        # Receive third update (COMPLETED)
        msg3 = websocket.receive_json()
        assert msg3["payload"]["status"] == "COMPLETED"
        
        # Auto-closes after COMPLETED state, so next call raises WebSocketDisconnect
        with pytest.raises(WebSocketDisconnect):
            websocket.receive_json()

def test_ws_disconnect_cleanup(client, mock_db):
    analysis_id = str(uuid.uuid4())
    # 1 state check for validation, plus states for loop
    states = [
        {
            "analysis_id": analysis_id,
            "repository_id": str(uuid.uuid4()),
            "status": "PROCESSING",
            "progress_percentage": 25.0,
            "current_file": "foo.py",
            "total_files": 10,
            "errors": []
        },
        {
            "analysis_id": analysis_id,
            "repository_id": str(uuid.uuid4()),
            "status": "PROCESSING",
            "progress_percentage": 25.0,
            "current_file": "foo.py",
            "total_files": 10,
            "errors": []
        },
        {
            "analysis_id": analysis_id,
            "repository_id": str(uuid.uuid4()),
            "status": "COMPLETED",
            "progress_percentage": 100.0,
            "current_file": "foo.py",
            "total_files": 10,
            "errors": []
        }
    ]
    mock_db.get_analysis_state.side_effect = states
    
    with client.websocket_connect(f"/api/v1/events/ws?analysis_id={analysis_id}") as websocket:
        msg = websocket.receive_json()
        assert msg["payload"]["status"] == "PROCESSING"
        # Close connection immediately (simulates client disconnect)
        websocket.close()





