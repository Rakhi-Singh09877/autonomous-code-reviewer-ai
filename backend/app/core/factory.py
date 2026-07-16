import logging
from typing import Optional
from app.core.config import settings

# Import Ports
from app.use_cases.interfaces.db_port import DBPort
from app.use_cases.interfaces.llm_port import LLMPort
from app.use_cases.interfaces.metrics_port import MetricsPort
from app.use_cases.interfaces.loader_port import RepositoryLoaderPort
from app.use_cases.interfaces.detector_port import LanguageDetectorPort
from app.use_cases.interfaces.parser_port import CodeParserPort
from app.use_cases.interfaces.embedding_port import EmbeddingPort
from app.use_cases.interfaces.rag_port import RAGPort
from app.use_cases.interfaces.agent_ports import ReviewAgentPort
from app.use_cases.interfaces.report_port import ReportPort

# Import Adapters
from app.infrastructure.database.repository import SQLAlchemyDBAdapter
from app.infrastructure.llm.claude import ClaudeLLMAdapter
from app.infrastructure.registry import services_registry
from app.infrastructure.repository_loader.git_loader import GitLoader
from app.infrastructure.language_detector.detector import DefaultLanguageDetector
from app.infrastructure.code_parser.parser import DefaultCodeParser
from app.infrastructure.rag.embedding_provider import OpenAIEmbeddingProvider
from app.infrastructure.rag.chroma_store import ChromaVectorStore
from app.infrastructure.rag.rag_engine import RAGEngine
from app.infrastructure.agents.review_agent import ReviewAgent
from app.infrastructure.report.generator import MarkdownReportGenerator
from app.use_cases.orchestrator import RepositoryAnalysisOrchestrator

class ServiceFactory:
    """
    Unified Application Composition Root.
    Constructs and configures ports and infrastructure adapters without coupling to FastAPI's dependency framework.
    Guarantees consistency across HTTP API runners and background Celery worker tasks.
    """
    _db_adapter: Optional[DBPort] = None
    _llm_adapter: Optional[LLMPort] = None

    @classmethod
    def get_db_port(cls) -> DBPort:
        """
        Returns singleton database port adapter.
        """
        if cls._db_adapter is None:
            cls._db_adapter = SQLAlchemyDBAdapter()
        return cls._db_adapter

    @classmethod
    def get_llm_port(cls) -> LLMPort:
        """
        Returns singleton Claude LLM port adapter.
        """
        if cls._llm_adapter is None:
            cls._llm_adapter = ClaudeLLMAdapter()
        return cls._llm_adapter

    @classmethod
    def get_metrics_port(cls) -> MetricsPort:
        """
        Returns the registry-managed telemetry metrics port.
        """
        return services_registry.metrics

    @classmethod
    def get_loader_port(cls) -> RepositoryLoaderPort:
        return GitLoader(temp_storage_path=settings.TEMP_STORAGE_PATH)

    @classmethod
    def get_detector_port(cls) -> LanguageDetectorPort:
        return DefaultLanguageDetector()

    @classmethod
    def get_parser_port(cls) -> CodeParserPort:
        return DefaultCodeParser()

    @classmethod
    def get_embedding_port(cls) -> EmbeddingPort:
        provider = OpenAIEmbeddingProvider(
            api_key=settings.OPENAI_API_KEY,
            dimensions=settings.EMBEDDING_DIMENSIONS
        )
        return ChromaVectorStore(embedding_provider=provider)

    @classmethod
    def get_rag_port(cls) -> RAGPort:
        provider = OpenAIEmbeddingProvider(
            api_key=settings.OPENAI_API_KEY,
            dimensions=settings.EMBEDDING_DIMENSIONS
        )
        store = cls.get_embedding_port()
        return RAGEngine(vector_store=store, embedding_provider=provider)

    @classmethod
    def get_review_agent_port(cls) -> ReviewAgentPort:
        return ReviewAgent(llm_port=cls.get_llm_port())

    @classmethod
    def get_report_port(cls) -> ReportPort:
        return MarkdownReportGenerator()

    @classmethod
    def get_orchestrator(cls) -> RepositoryAnalysisOrchestrator:
        """
        Assembles all domain ports into a fully resolved RepositoryAnalysisOrchestrator instance.
        """
        return RepositoryAnalysisOrchestrator(
            loader_port=cls.get_loader_port(),
            detector_port=cls.get_detector_port(),
            parser_port=cls.get_parser_port(),
            embedding_port=cls.get_embedding_port(),
            rag_port=cls.get_rag_port(),
            review_agent_port=cls.get_review_agent_port(),
            report_port=cls.get_report_port(),
            metrics_port=cls.get_metrics_port()
        )
