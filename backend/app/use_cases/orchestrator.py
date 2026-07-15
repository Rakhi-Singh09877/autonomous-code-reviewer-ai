import os
import time
import uuid
import logging
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO, Optional, List, Dict, Any, Tuple

from app.domain.models.repository import Repository
from app.domain.models.analysis import ReviewPolicy
from app.domain.models.report import RepositoryReviewReport, FileReviewResult, TokenUsageMetadata
from app.domain.models.parser import ParsedFile
from app.domain.models.embedding import EmbeddingDocument, ChunkMetadata, SearchResult
from app.use_cases.interfaces.loader_port import RepositoryLoaderPort
from app.use_cases.interfaces.detector_port import LanguageDetectorPort
from app.use_cases.interfaces.parser_port import CodeParserPort
from app.use_cases.interfaces.embedding_port import EmbeddingPort
from app.use_cases.interfaces.rag_port import RAGPort
from app.use_cases.interfaces.agent_ports import ReviewAgentPort
from app.use_cases.interfaces.report_port import ReportPort

from app.use_cases.interfaces.metrics_port import MetricsPort

logger = logging.getLogger("app.use_cases.orchestrator")

class RepositoryAnalysisOrchestrator:
    """
    Orchestrator coordinating repository analysis use cases.
    Coordinates loading, language detection, parsing, embeddings, RAG lookups, agent reviews, and report generation.
    """

    def __init__(
        self,
        loader_port: RepositoryLoaderPort,
        detector_port: LanguageDetectorPort,
        parser_port: CodeParserPort,
        embedding_port: EmbeddingPort,
        rag_port: RAGPort,
        review_agent_port: ReviewAgentPort,
        report_port: ReportPort,
        metrics_port: Optional[MetricsPort] = None
    ) -> None:
        self.loader_port = loader_port
        self.detector_port = detector_port
        self.parser_port = parser_port
        self.embedding_port = embedding_port
        self.rag_port = rag_port
        self.review_agent_port = review_agent_port
        self.report_port = report_port
        self.metrics_port = metrics_port

    async def analyze_repository(
        self,
        git_url: Optional[str] = None,
        zip_file: Optional[BinaryIO] = None,
        branch: Optional[str] = None,
        policy: Optional[ReviewPolicy] = None,
        progress_callback: Optional[Any] = None
    ) -> RepositoryReviewReport:
        """
        Coordinates the complete repository code review analysis workflow.
        """
        if self.metrics_port:
            self.metrics_port.record_analysis_started()

        if policy is None:
            policy = ReviewPolicy()

        if progress_callback:
            await progress_callback("PROCESSING", 5.0, "Loading repository", None)

        repository: Optional[Repository] = None
        try:
            # 1. Load repository using RepositoryLoaderPort
            if git_url:
                logger.info("Loading repository from Git: %s", git_url)
                repository = await asyncio.to_thread(self.loader_port.load_from_git, git_url, branch)
            elif zip_file:
                logger.info("Loading repository from ZIP file")
                repository = await asyncio.to_thread(self.loader_port.load_from_zip, zip_file)
            else:
                raise ValueError("Either git_url or zip_file must be specified.")

            if progress_callback:
                await progress_callback("PROCESSING", 15.0, "Detecting language", None)

            # 2. Detect language of every file using DetectorPort
            logger.info("Detecting file languages recursively")
            detected_files: List[Tuple[Path, str]] = []
            resolved_workspace = Path(repository.local_path).resolve()
            
            def walk_files(path: Path) -> List[Path]:
                file_paths = []
                for root, dirs, files in os.walk(path):
                    # Apply standard ignores to skip dependency paths and hidden directories
                    dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "venv", "__pycache__")]
                    for file_name in files:
                        file_paths.append(Path(root) / file_name)
                return file_paths

            file_paths = await asyncio.to_thread(walk_files, resolved_workspace)

            # Notify callback of total files detected
            if progress_callback:
                await progress_callback("PROCESSING", 15.0, "Detecting language", None, len(file_paths))

            for file_path in file_paths:
                try:
                    detection = await asyncio.to_thread(self.detector_port.detect_file_language, file_path)
                    detected_files.append((file_path, detection.language))
                except Exception as e:
                    logger.error("Failed to detect language of file %s: %s", file_path, e)
                    if progress_callback:
                        await progress_callback("PROCESSING", 15.0, str(file_path.name), f"Language detection error: {e}", len(file_paths))

            if progress_callback:
                await progress_callback("PROCESSING", 30.0, "Parsing codebase", None, len(file_paths))

            # 3. Parse every supported source file using ParserPort
            supported_languages = {"python", "java", "javascript", "typescript"}
            files_to_parse: List[Tuple[Path, str]] = [
                (path, lang) for path, lang in detected_files
                if lang.lower() in supported_languages
            ]

            logger.info("Parsing %d supported source files", len(files_to_parse))
            codebase_structure = await asyncio.to_thread(
                self.parser_port.parse_repository,
                repository.local_path,
                files_to_parse
            )

            if progress_callback:
                await progress_callback("PROCESSING", 50.0, "Generating embeddings", None, len(file_paths))

            # 4. Generate embeddings using EmbeddingPort & 5. Store embeddings
            repository_id_str = str(repository.id)
            repository_name = repository.local_path.name
            repo_branch = repository.branch
            indexed_at = datetime.now(timezone.utc).isoformat()
            
            all_documents: List[EmbeddingDocument] = []
            for parsed_file in codebase_structure.files:
                for chunk in parsed_file.chunks:
                    chunk_metadata = ChunkMetadata(
                        symbols=parsed_file.symbols,
                        dependencies=parsed_file.dependencies,
                        complexity_score=parsed_file.complexity_score,
                        relative_path=parsed_file.relative_path,
                        package_name=parsed_file.package_name,
                        start_line=chunk["metadata"].get("start_line", 0),
                        end_line=chunk["metadata"].get("end_line", 0),
                        repository_name=repository_name,
                        branch=repo_branch,
                        language=parsed_file.language,
                        entity_type=chunk["metadata"].get("type", "unknown"),
                        parser_version="1.0.0",
                        indexed_at=indexed_at,
                    )
                    
                    resource_uri = f"mcp://{repository_id_str}/{parsed_file.relative_path}"
                    if "start_line" in chunk["metadata"]:
                        resource_uri += f"#L{chunk['metadata']['start_line']}-L{chunk['metadata']['end_line']}"
                        
                    doc = EmbeddingDocument(
                        id=chunk["id"],
                        repository_id=repository_id_str,
                        file_path=str(parsed_file.file_path),
                        module_name=parsed_file.module_name,
                        entity_name=chunk["entity_name"],
                        entity_type=chunk["metadata"].get("type", "unknown"),
                        language=parsed_file.language,
                        text=chunk["text"],
                        metadata=chunk_metadata,
                        resource_uri=resource_uri,
                    )
                    all_documents.append(doc)

            if all_documents:
                logger.info("Upserting %d embedding documents into vector store", len(all_documents))
                try:
                    await asyncio.to_thread(self.embedding_port.upsert_documents, repository_id_str, all_documents)
                except Exception as e:
                    logger.error("Embedding storage failed for repository %s: %s", repository_id_str, e)
                    if progress_callback:
                        await progress_callback("PROCESSING", 50.0, "embeddings", f"Embedding save error: {e}", len(file_paths))

            # Define codebase/repository context information for ReviewAgentPort
            repo_context = (
                f"Repository: {repository_name}\n"
                f"Total Files: {codebase_structure.total_files}\n"
                f"Parsed Files: {codebase_structure.parsed_files}\n"
                f"Languages: {codebase_structure.language_statistics}\n"
            )

            if progress_callback:
                await progress_callback("PROCESSING", 60.0, "Reviewing files", None, len(file_paths))

            # 6. Retrieve semantic context, 7. Review parsed files, collect timing/tokens
            file_results: List[FileReviewResult] = []
            total_token_usage = TokenUsageMetadata()

            total_parsed_files = len(codebase_structure.files)
            for idx, parsed_file in enumerate(codebase_structure.files):
                start_time = time.perf_counter()
                
                pct = 60.0 + (idx / total_parsed_files) * 35.0 if total_parsed_files > 0 else 60.0
                if progress_callback:
                    await progress_callback("PROCESSING", round(pct, 1), parsed_file.relative_path, None, len(file_paths))

                try:
                    # 6. Retrieve semantic context using RAGPort
                    rag_chunks: List[SearchResult] = []
                    try:
                        rag_chunks = await self.rag_port.retrieve_context_chunks(
                            repository_id=repository_id_str,
                            query=parsed_file.relative_path,
                            limit=5,
                            branch=repo_branch
                        )
                    except Exception as re:
                        logger.error("RAG context retrieval failed for %s: %s", parsed_file.relative_path, re)

                    # 7. Review parsed file using ReviewAgentPort
                    result = await self.review_agent_port.analyze_file(
                        file_path=parsed_file.file_path,
                        parsed_file=parsed_file,
                        repo_context=repo_context,
                        rag_chunks=rag_chunks,
                        policy=policy
                    )
                    
                    duration = time.perf_counter() - start_time
                    if result.review_time_sec == 0.0:
                        result.review_time_sec = duration

                    file_results.append(result)
                    total_token_usage.add(result.token_usage)

                except Exception as e:
                    duration = time.perf_counter() - start_time
                    logger.error("Failed to analyze file %s: %s", parsed_file.relative_path, e, exc_info=True)
                    if progress_callback:
                        await progress_callback("PROCESSING", round(pct, 1), parsed_file.relative_path, f"Review error: {e}", len(file_paths))
                    # Maintain structural integrity for failed files:
                    failure_result = FileReviewResult(
                        file_path=parsed_file.file_path,
                        issues=[],
                        score=100,
                        review_time_sec=duration,
                        token_usage=TokenUsageMetadata()
                    )
                    file_results.append(failure_result)

            if progress_callback:
                await progress_callback("PROCESSING", 95.0, "Aggregating report", None, len(file_paths))

            # 8. Aggregate every FileReviewResult into a RepositoryReviewReport
            total_issues = 0
            issues_by_severity: Dict[str, int] = {}
            issues_by_category: Dict[str, int] = {}
            total_score = 0.0

            for f_res in file_results:
                total_issues += len(f_res.issues)
                total_score += f_res.score
                for issue in f_res.issues:
                    sev = issue.severity.value if hasattr(issue.severity, 'value') else str(issue.severity)
                    cat = issue.category.value if hasattr(issue.category, 'value') else str(issue.category)
                    issues_by_severity[sev] = issues_by_severity.get(sev, 0) + 1
                    issues_by_category[cat] = issues_by_category.get(cat, 0) + 1

            files_count = len(file_results)
            average_score = total_score / files_count if files_count > 0 else 100.0

            report = RepositoryReviewReport(
                id=uuid.uuid4(),
                repository_id=repository.id,
                created_at=datetime.now(timezone.utc),
                files_reviewed=files_count,
                total_issues=total_issues,
                issues_by_severity=issues_by_severity,
                issues_by_category=issues_by_category,
                average_score=round(average_score, 2),
                file_results=file_results,
                token_usage=total_token_usage
            )

            # 9. Generate the final report using ReportPort
            try:
                self.report_port.generate_report(report)
            except Exception as e:
                logger.error("Failed to generate final report: %s", e)

            if progress_callback:
                await progress_callback("COMPLETED", 100.0, "Report complete", None, len(file_paths))

            if self.metrics_port:
                self.metrics_port.record_analysis_completed()

            return report

        except Exception as e:
            if self.metrics_port:
                self.metrics_port.record_analysis_failed()
            if progress_callback:
                num_files = len(file_paths) if 'file_paths' in locals() else 0
                await progress_callback("FAILED", 100.0, "Analysis failed", str(e), num_files)
            raise

        finally:
            if repository:
                logger.info("Cleaning up loaded repository resources for repository: %s", repository.id)
                try:
                    await asyncio.to_thread(self.loader_port.cleanup, repository)
                except Exception as e:
                    logger.error("Repository loader cleanup failed: %s", e)
