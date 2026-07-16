import prometheus_client
from app.use_cases.interfaces.metrics_port import MetricsPort

class PrometheusMetricsAdapter(MetricsPort):
    """
    Adapter implementing MetricsPort by wrapping the official prometheus_client library.
    It registers prometheus collectors and maps business events to counters, gauges, and histograms.
    """
    def __init__(self) -> None:
        self._registry = prometheus_client.REGISTRY
        
        # Helper helpers to get existing or register new collectors to prevent DuplicateRegistrationError in tests
        def get_or_register_counter(name, doc, labels):
            if name in self._registry._names_to_collectors:
                return self._registry._names_to_collectors[name]
            return prometheus_client.Counter(name, doc, labels, registry=self._registry)

        def get_or_register_gauge(name, doc):
            if name in self._registry._names_to_collectors:
                return self._registry._names_to_collectors[name]
            return prometheus_client.Gauge(name, doc, registry=self._registry)

        def get_or_register_histogram(name, doc, labels):
            if name in self._registry._names_to_collectors:
                return self._registry._names_to_collectors[name]
            return prometheus_client.Histogram(name, doc, labels, registry=self._registry)

        # 1. Requests metrics
        self._requests_total = get_or_register_counter(
            "http_requests_total",
            "Total number of HTTP requests.",
            ["method", "path", "status"]
        )
        self._request_duration = get_or_register_histogram(
            "http_request_duration_seconds",
            "HTTP request latency in seconds.",
            ["method", "path"]
        )
        self._active_requests = get_or_register_gauge(
            "active_requests",
            "Number of active HTTP requests currently running."
        )

        # 2. Analysis jobs metrics
        self._jobs_started = get_or_register_counter(
            "analysis_jobs_started_total",
            "Total number of analysis jobs started.",
            []
        )
        self._jobs_completed = get_or_register_counter(
            "analysis_jobs_completed_total",
            "Total number of analysis jobs completed successfully.",
            []
        )
        self._jobs_failed = get_or_register_counter(
            "analysis_jobs_failed_total",
            "Total number of analysis jobs failed.",
            []
        )

        # 3. Celery queue and worker metrics
        self._queue_waiting_duration = get_or_register_histogram(
            "celery_queue_waiting_duration_seconds",
            "Latency of task waiting in the Redis queue before execution.",
            []
        )
        self._worker_execution_duration = get_or_register_histogram(
            "celery_worker_execution_duration_seconds",
            "Total execution latency of worker tasks.",
            []
        )
        self._task_retries = get_or_register_counter(
            "celery_task_retries_total",
            "Total number of task retries.",
            ["attempt"]
        )

    def record_request_started(self) -> None:
        self._active_requests.inc()

    def record_request_completed(self, method: str, path: str, status_code: int, latency_seconds: float) -> None:
        self._active_requests.dec()
        self._requests_total.labels(method=method, path=path, status=str(status_code)).inc()
        self._request_duration.labels(method=method, path=path).observe(latency_seconds)

    def record_analysis_started(self) -> None:
        self._jobs_started.inc()

    def record_analysis_completed(self) -> None:
        self._jobs_completed.inc()

    def record_analysis_failed(self) -> None:
        self._jobs_failed.inc()

    def record_queue_waiting_time(self, latency_seconds: float) -> None:
        self._queue_waiting_duration.observe(latency_seconds)

    def record_worker_execution_duration(self, duration_seconds: float) -> None:
        self._worker_execution_duration.observe(duration_seconds)

    def record_task_retry(self, attempt: int) -> None:
        self._task_retries.labels(attempt=str(attempt)).inc()

    def generate_prometheus_metrics(self) -> str:
        """
        Translates metric records and formats them to Prometheus-compatible plain text.
        """
        return prometheus_client.generate_latest(self._registry).decode("utf-8")
