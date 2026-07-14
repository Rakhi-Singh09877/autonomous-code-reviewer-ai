# Implementation Plan - Repository Loader (Module 1)

This plan details the design and implementation of **Module 1: Repository Loader** for the *Autonomous Code Reviewer AI*. It guarantees clean boundaries (Clean Architecture), strict validation (regex URL validation, path traversal check), and defense-in-depth against Zip Slip vulnerabilities.

---

## Technical Details & Security Controls

1. **Zip Slip Prevention**:
   * We will validate every file path inside the ZIP archive. We will resolve the target absolute path and verify it is strictly within the designated extract directory using `pathlib.Path.resolve()`. If any resolved path escapes the base directory, we raise a security exception immediately and abort extraction.
2. **Git URL Validation**:
   * A regex pattern will validate repository URLs to allow valid HTTP/HTTPS and SSH GitHub links while rejecting malicious command-injection strings.
3. **Workspace Isolation**:
   * Each cloned/extracted repository will reside in a unique subfolder generated using UUID v4 under the configured temporary storage path.
4. **Cleanup Protocol**:
   * The loader will expose context managers or clean methods to recursively wipe workspaces using `shutil.rmtree` upon task completion or failure.

---

## Proposed Changes

### Configuration & Logging

#### [MODIFY] [config.py](file:///c:/Users/Lenovo/Autonomous-Code-Reviewer/backend/app/core/config.py)
* Add settings for `TEMP_STORAGE_PATH` (defaults to `./storage/temp`) and `MAX_UPLOAD_SIZE_MB` (defaults to 100).

#### [MODIFY] [logging.py](file:///c:/Users/Lenovo/Autonomous-Code-Reviewer/backend/app/core/logging.py)
* Initialize standard logging formatters and stream handlers to log cloning and extraction metrics.

### Domain Layer (Entities & Exceptions)

#### [NEW] [repository.py](file:///c:/Users/Lenovo/Autonomous-Code-Reviewer/backend/app/domain/models/repository.py)
* Domain model `Repository` storing:
  * `id`: UUID
  * `local_path`: Path (resolved absolute path)
  * `source_type`: Enum (`GIT` or `ZIP`)
  * `file_count`: int
  * `total_size_bytes`: int

#### [NEW] [repository_exceptions.py](file:///c:/Users/Lenovo/Autonomous-Code-Reviewer/backend/app/domain/exceptions/repository_exceptions.py)
* Core exceptions:
  * `RepositoryLoaderException`: Base domain exception
  * `InvalidRepositoryURLException`: Raised when URL validation fails
  * `SecurityException`: Base for path traversals / Zip Slip attempts
  * `ZipSlipException`: Specific Zip Slip attempt detection
  * `CloneTimeoutException`: When git commands fail to respond within timeout

### Application Use Cases (Interfaces / Ports)

#### [MODIFY] [loader_port.py](file:///c:/Users/Lenovo/Autonomous-Code-Reviewer/backend/app/use_cases/interfaces/loader_port.py)
* Abstract Base Class `RepositoryLoaderPort` with signatures:
  * `load_from_git(url: str, branch: Optional[str] = None) -> Repository`
  * `load_from_zip(zip_file: BinaryIO) -> Repository`
  * `cleanup(repository: Repository) -> None`

### Infrastructure Layer (Adapters)

#### [MODIFY] [git_loader.py](file:///c:/Users/Lenovo/Autonomous-Code-Reviewer/backend/app/infrastructure/repository_loader/git_loader.py)
* Implementation of `RepositoryLoaderPort` using python's `subprocess` (calling Git CLI safely with positional parameters) and `zipfile` for archive extraction.

### Verification Plan

#### [NEW] [test_repository_loader.py](file:///c:/Users/Lenovo/Autonomous-Code-Reviewer/tests/test_repository_loader.py)
* Unit tests using `pytest` covering:
  * Safe extraction of normal ZIP files.
  * Rejection of ZIP files containing path traversals (Zip Slip vulnerability test).
  * URL regex validation (validating standard URLs and rejecting dangerous shell sequences).
  * Git clone timeout and process handling (mocked subprocess).
  * Cleanup method deletes files recursively.
