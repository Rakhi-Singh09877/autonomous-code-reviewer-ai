from fastapi import Depends
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
from app.use_cases.interfaces.job_queue_port import JobQueuePort

# Import Composition Root and Celery Adapter
from app.core.factory import ServiceFactory
from app.infrastructure.queue.celery_adapter import CeleryJobQueueAdapter
from app.use_cases.orchestrator import RepositoryAnalysisOrchestrator

# Initialize the queue adapter instance as singleton
_job_queue = CeleryJobQueueAdapter()

def get_db_port() -> DBPort:
    """
    Resolves db port singleton from composition root.
    """
    return ServiceFactory.get_db_port()

def get_llm_port() -> LLMPort:
    """
    Resolves LLM port singleton from composition root.
    """
    return ServiceFactory.get_llm_port()

def get_metrics_port() -> MetricsPort:
    """
    Resolves MetricsPort singleton from composition root.
    """
    return ServiceFactory.get_metrics_port()

def get_job_queue() -> JobQueuePort:
    """
    Resolves the JobQueuePort messaging adapter singleton.
    """
    return _job_queue

def get_loader_port() -> RepositoryLoaderPort:
    return ServiceFactory.get_loader_port()

def get_detector_port() -> LanguageDetectorPort:
    return ServiceFactory.get_detector_port()

def get_parser_port() -> CodeParserPort:
    return ServiceFactory.get_parser_port()

def get_embedding_port(
    provider = Depends(ServiceFactory.get_embedding_port)
) -> EmbeddingPort:
    return provider

def get_rag_port(
    rag = Depends(ServiceFactory.get_rag_port)
) -> RAGPort:
    return rag

def get_review_agent_port(
    llm: LLMPort = Depends(get_llm_port)
) -> ReviewAgentPort:
    return ServiceFactory.get_review_agent_port()

def get_report_port() -> ReportPort:
    return ServiceFactory.get_report_port()

def get_orchestrator(
    orchestrator: RepositoryAnalysisOrchestrator = Depends(ServiceFactory.get_orchestrator)
) -> RepositoryAnalysisOrchestrator:
    return orchestrator
