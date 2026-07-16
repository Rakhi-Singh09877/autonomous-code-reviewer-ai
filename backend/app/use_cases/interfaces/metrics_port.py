from abc import ABC, abstractmethod

class MetricsPort(ABC):
    """
    Interface Port defining operational telemetry recording business events.
    Exposes pure business operations, concealing collector structures from core use-cases.
    """
    @abstractmethod
    def record_request_started(self) -> None:
        """
        Increments count of active requests running in the API server.
        """
        pass

    @abstractmethod
    def record_request_completed(self, method: str, path: str, status_code: int, latency_seconds: float) -> None:
        """
        Decrements active requests and records request execution timing and HTTP status.
        """
        pass

    @abstractmethod
    def record_analysis_started(self) -> None:
        """
        Increments the counter tracking started analysis repository reviews jobs.
        """
        pass

    @abstractmethod
    def record_analysis_completed(self) -> None:
        """
        Increments the counter tracking successfully completed repository reviews jobs.
        """
        pass

    @abstractmethod
    def record_analysis_failed(self) -> None:
        """
        Increments the counter tracking failed analysis repository reviews jobs.
        """
        pass

    @abstractmethod
    def record_queue_waiting_time(self, latency_seconds: float) -> None:
        """
        Records the time a task spent waiting in the queue before execution.
        """
        pass

    @abstractmethod
    def record_worker_execution_duration(self, duration_seconds: float) -> None:
        """
        Records the total execution time of a worker task.
        """
        pass

    @abstractmethod
    def record_task_retry(self, attempt: int) -> None:
        """
        Increments task retry counters labeled by retry attempt.
        """
        pass

    @abstractmethod
    def generate_prometheus_metrics(self) -> str:
        """
        Formats and returns Prometheus-compatible metrics representation.
        """
        pass
