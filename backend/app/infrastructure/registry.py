from datetime import datetime, timezone
import time
from app.use_cases.interfaces.metrics_port import MetricsPort
from app.infrastructure.metrics.prometheus_adapter import PrometheusMetricsAdapter

class InfrastructureServices:
    """
    Infrastructure services registry owning operational telemetry collectors and startup lifecycles.
    Decouples application logic from concrete classes by exposing singletons strictly via Ports.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(InfrastructureServices, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        
        # Expose PrometheusMetricsAdapter strictly through the MetricsPort interface
        self._metrics: MetricsPort = PrometheusMetricsAdapter()
        
        # Record startup lifecycle timestamps
        self.startup_time = time.time()
        self.startup_timestamp = datetime.now(timezone.utc).isoformat()
        
        self._initialized = True

    @property
    def metrics(self) -> MetricsPort:
        """
        Returns the active MetricsPort instance.
        """
        return self._metrics

    def get_uptime(self) -> float:
        """
        Calculates the application process uptime in seconds.
        """
        return time.time() - self.startup_time

# Singleton registry instance
services_registry = InfrastructureServices()
