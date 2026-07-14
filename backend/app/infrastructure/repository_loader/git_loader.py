import os
import re
import shutil
import threading
from pathlib import Path
from typing import BinaryIO, Optional, Tuple
import uuid
import git

from app.core.config import settings
from app.core.logging import logger
from app.domain.models.repository import Repository, RepositorySourceType
from app.domain.exceptions.repository_exceptions import (
    RepositoryLoaderException,
    InvalidRepositoryURLException,
    ZipSlipException,
    CloneTimeoutException,
)
from app.use_cases.interfaces.loader_port import RepositoryLoaderPort

GIT_URL_REGEX = re.compile(
    r"^(https?://([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(/[a-zA-Z0-9-_./]+)+(\.git)?/?)$"
    r"|"
    r"^(git@[a-zA-Z0-9-.]+:([a-zA-Z0-9-_./]+)(\.git)?)$"
)

class GitLoader(RepositoryLoaderPort):
    """
    Adapter implementing RepositoryLoaderPort using GitPython for cloning
    and zipfile for safe archive extraction.
    """

    def __init__(self, temp_storage_path: Optional[str] = None):
        self.temp_storage_path = Path(temp_storage_path or settings.TEMP_STORAGE_PATH).resolve()

    def validate_url(self, url: str) -> None:
        """
        Validates the format of a Git URL.
        """
        if not url or not GIT_URL_REGEX.match(url.strip()):
            raise InvalidRepositoryURLException(f"The provided Git URL format is invalid: {url}")

    def load_from_git(self, url: str, branch: Optional[str] = None) -> Repository:
        """
        Clones a Git repository into a secure workspace subfolder.
        """
        self.validate_url(url)
        workspace_id = uuid.uuid4()
        local_path = self.temp_storage_path / str(workspace_id)
        local_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"Starting Git clone for URL: {url} (branch: {branch or 'default'}) into {local_path}")
        
        timeout = settings.CLONE_TIMEOUT_SEC
        errs = []

        def clone_target():
            try:
                kwargs = {"depth": 1}
                if branch:
                    kwargs["branch"] = branch
                git.Repo.clone_from(url, str(local_path), **kwargs)
            except Exception as e:
                errs.append(e)

        thread = threading.Thread(target=clone_target)
        thread.start()
        thread.join(timeout)

        if thread.is_alive():
            self._cleanup_path(local_path)
            raise CloneTimeoutException(f"Git clone operation timed out after {timeout} seconds.")

        if errs:
            self._cleanup_path(local_path)
            raise RepositoryLoaderException(f"Failed to clone repository: {str(errs[0])}")

        file_count, total_size = self._get_workspace_metrics(local_path)

        return Repository(
            id=workspace_id,
            local_path=local_path,
            source_type=RepositorySourceType.GIT,
            file_count=file_count,
            total_size_bytes=total_size,
            branch=branch,
            git_url=url,
        )

    def load_from_zip(self, zip_file: BinaryIO) -> Repository:
        """
        Extracts an uploaded ZIP file into an isolated workspace directory with Zip Slip protection.
        """
        import zipfile

        workspace_id = uuid.uuid4()
        local_path = self.temp_storage_path / str(workspace_id)
        local_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"Extracting ZIP archive into {local_path}")

        try:
            with zipfile.ZipFile(zip_file) as archive:
                for member in archive.infolist():
                    # Zip Slip prevention: resolve target path and ensure it's nested under local_path
                    target_path = Path(local_path).joinpath(member.filename).resolve()
                    if not target_path.is_relative_to(local_path):
                        raise ZipSlipException(
                            f"Directory traversal attempt detected in zip member: {member.filename}"
                        )
                    
                    # Extract single member
                    archive.extract(member, str(local_path))
        except ZipSlipException:
            self._cleanup_path(local_path)
            raise
        except Exception as e:
            self._cleanup_path(local_path)
            raise RepositoryLoaderException(f"Failed to extract ZIP archive: {str(e)}")

        file_count, total_size = self._get_workspace_metrics(local_path)

        return Repository(
            id=workspace_id,
            local_path=local_path,
            source_type=RepositorySourceType.ZIP,
            file_count=file_count,
            total_size_bytes=total_size,
        )

    def cleanup(self, repository: Repository) -> None:
        """
        Safely removes the directory associated with the Repository.
        """
        self._cleanup_path(repository.local_path)

    def _cleanup_path(self, path: Path) -> None:
        """Helper method to remove file tree recursively."""
        resolved_path = Path(path).resolve()
        # Double check we are not deleting parent temp storage or root filesystem
        if resolved_path.exists() and resolved_path != self.temp_storage_path:
            shutil.rmtree(resolved_path, ignore_errors=True)
            logger.info(f"Cleaned up workspace at: {resolved_path}")

    def _get_workspace_metrics(self, path: Path) -> Tuple[int, int]:
        """Calculates total file count and total size in bytes, excluding the .git folder."""
        file_count = 0
        total_size = 0
        for root, dirs, files in os.walk(path):
            if ".git" in dirs:
                dirs.remove(".git")
            for f in files:
                file_path = Path(root) / f
                try:
                    if file_path.is_file() and not file_path.is_symlink():
                        file_count += 1
                        total_size += file_path.stat().st_size
                except OSError:
                    # Ignore unreadable files
                    pass
        return file_count, total_size
