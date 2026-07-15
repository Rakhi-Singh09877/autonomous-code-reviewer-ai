from fastapi import Depends
from app.core.config import settings
from app.use_cases.interfaces.loader_port import RepositoryLoaderPort
from app.use_cases.interfaces.detector_port import LanguageDetectorPort
from app.use_cases.interfaces.parser_port import CodeParserPort
from app.use_cases.interfaces.embedding_port import EmbeddingPort, EmbeddingProvider
from app.use_cases.interfaces.rag_port import RAGPort
from app.use_cases.interfaces.agent_ports import ReviewAgentPort
from app.use_cases.interfaces.report_port import ReportPort
from app.use_cases.interfaces.db_port import DBPort
from app.use_cases.interfaces.llm_port import LLMPort

from app.infrastructure.repository_loader.git_loader import GitLoader
from app.infrastructure.language_detector.detector import DefaultLanguageDetector
from app.infrastructure.code_parser.parser import DefaultCodeParser
from app.infrastructure.rag.chroma_store import ChromaVectorStore
from app.infrastructure.rag.embedding_provider import OpenAIEmbeddingProvider
from app.infrastructure.rag.rag_engine import RAGEngine
from app.infrastructure.agents.review_agent import ReviewAgent
from app.infrastructure.report.generator import MarkdownReportGenerator
from app.infrastructure.database.repository import SQLAlchemyDBAdapter
from app.infrastructure.llm.claude import ClaudeLLMAdapter

from app.use_cases.orchestrator import RepositoryAnalysisOrchestrator

# Initialize singletons for database connection and Claude API client lifecycle
_db_adapter = SQLAlchemyDBAdapter()
_llm_adapter = ClaudeLLMAdapter()

def get_db_port() -> DBPort:
    return _db_adapter

def get_llm_port() -> LLMPort:
    return _llm_adapter

def get_loader_port() -> RepositoryLoaderPort:
    return GitLoader(temp_storage_path=settings.TEMP_STORAGE_PATH)

def get_detector_port() -> LanguageDetectorPort:
    return DefaultLanguageDetector()

def get_parser_port() -> CodeParserPort:
    return DefaultCodeParser()

def get_embedding_provider() -> EmbeddingProvider:
    return OpenAIEmbeddingProvider(api_key=settings.OPENAI_API_KEY, dimensions=settings.EMBEDDING_DIMENSIONS)

def get_embedding_port(
    provider: EmbeddingProvider = Depends(get_embedding_provider)
) -> EmbeddingPort:
    return ChromaVectorStore(embedding_provider=provider)

def get_rag_port(
    store: EmbeddingPort = Depends(get_embedding_port),
    provider: EmbeddingProvider = Depends(get_embedding_provider)
) -> RAGPort:
    return RAGEngine(vector_store=store, embedding_provider=provider)

def get_review_agent_port(
    llm: LLMPort = Depends(get_llm_port)
) -> ReviewAgentPort:
    return ReviewAgent(llm_port=llm)

def get_report_port() -> ReportPort:
    return MarkdownReportGenerator()

def get_orchestrator(
    loader: RepositoryLoaderPort = Depends(get_loader_port),
    detector: LanguageDetectorPort = Depends(get_detector_port),
    parser: CodeParserPort = Depends(get_parser_port),
    embedding: EmbeddingPort = Depends(get_embedding_port),
    rag: RAGPort = Depends(get_rag_port),
    review_agent: ReviewAgentPort = Depends(get_review_agent_port),
    report: ReportPort = Depends(get_report_port)
) -> RepositoryAnalysisOrchestrator:
    return RepositoryAnalysisOrchestrator(
        loader_port=loader,
        detector_port=detector,
        parser_port=parser,
        embedding_port=embedding,
        rag_port=rag,
        review_agent_port=review_agent,
        report_port=report
    )
