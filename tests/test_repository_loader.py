import io
import os
import shutil
import tempfile
import time
import zipfile
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

import sys
# Ensure app directory is on the path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.domain.models.repository import RepositorySourceType
from app.domain.exceptions.repository_exceptions import (
    InvalidRepositoryURLException,
    ZipSlipException,
    CloneTimeoutException,
    RepositoryLoaderException,
)
from app.infrastructure.repository_loader.git_loader import GitLoader

@pytest.fixture
def temp_storage():
    """Fixture that creates and cleans up a temporary storage directory."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)

def test_validate_url_success():
    loader = GitLoader(temp_storage_path="/tmp")
    # Should not raise exception
    loader.validate_url("https://github.com/user/repo")
    loader.validate_url("https://github.com/user/repo.git")
    loader.validate_url("http://github.com/user/repo")
    loader.validate_url("git@github.com:user/repo.git")
    loader.validate_url("git@gitlab.com:org/group/project.git")

def test_validate_url_failure():
    loader = GitLoader(temp_storage_path="/tmp")
    invalid_urls = [
        "https://github.com/user/repo.git; rm -rf /",
        "invalid-url",
        "ftp://github.com/user/repo",
        "",
        "git@github.com",
    ]
    for url in invalid_urls:
        with pytest.raises(InvalidRepositoryURLException):
            loader.validate_url(url)

@patch("git.Repo.clone_from")
def test_load_from_git_success(mock_clone, temp_storage):
    loader = GitLoader(temp_storage_path=temp_storage)
    
    # Configure mock
    def mock_clone_behavior(url, path, **kwargs):
        # Create a mock file in the path to simulate repository files
        os.makedirs(os.path.join(path, "src"), exist_ok=True)
        with open(os.path.join(path, "src", "main.py"), "w") as f:
            f.write("print('hello')")
        with open(os.path.join(path, "README.md"), "w") as f:
            f.write("Cool Repo")

    mock_clone.side_effect = mock_clone_behavior

    repo = loader.load_from_git("https://github.com/user/repo.git")
    
    assert repo.source_type == RepositorySourceType.GIT
    assert repo.file_count == 2
    assert repo.total_size_bytes > 0
    assert repo.git_url == "https://github.com/user/repo.git"
    assert Path(repo.local_path).exists()
    
    # Check cleanup
    loader.cleanup(repo)
    assert not Path(repo.local_path).exists()

@patch("git.Repo.clone_from")
def test_load_from_git_timeout(mock_clone, temp_storage):
    # Mock clone to sleep longer than settings timeout (mocked or custom)
    def slow_clone(url, path, **kwargs):
        time.sleep(3)

    mock_clone.side_effect = slow_clone

    # Override setting locally or pass a mock clone
    with patch("app.infrastructure.repository_loader.git_loader.settings") as mock_settings:
        mock_settings.CLONE_TIMEOUT_SEC = 1
        mock_settings.TEMP_STORAGE_PATH = temp_storage
        loader = GitLoader(temp_storage_path=temp_storage)

        with pytest.raises(CloneTimeoutException):
            loader.load_from_git("https://github.com/user/repo.git")

def test_load_from_zip_success(temp_storage):
    loader = GitLoader(temp_storage_path=temp_storage)

    # Create dummy zip file in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        zip_file.writestr("index.js", "console.log('hello')")
        zip_file.writestr("subfolder/utils.js", "export const add = (a, b) => a + b;")

    zip_buffer.seek(0)
    repo = loader.load_from_zip(zip_buffer)

    assert repo.source_type == RepositorySourceType.ZIP
    assert repo.file_count == 2
    assert repo.total_size_bytes > 0
    assert Path(repo.local_path).exists()

    # Cleanup
    loader.cleanup(repo)
    assert not Path(repo.local_path).exists()

def test_load_from_zip_slip_vulnerability(temp_storage):
    loader = GitLoader(temp_storage_path=temp_storage)

    # Create malicious zip file containing path traversal
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        zip_file.writestr("../traversal.txt", "evil payload")

    zip_buffer.seek(0)
    
    with pytest.raises(ZipSlipException):
        loader.load_from_zip(zip_buffer)
