from app.core.config import settings
import sys

# Set up Redis URLs from settings
broker_url = settings.CELERY_BROKER_URL
result_backend = settings.CELERY_RESULT_BACKEND

# Serialization formats
task_serializer = "json"
result_serializer = "json"
accept_content = ["json"]
timezone = "UTC"
enable_utc = True

# Task execution reliability configurations (late acks mapping for crash recovery)
task_acks_late = True
task_reject_on_worker_lost = True

# Limit worker prefetching to avoid thread lock starvation on heavy scan tasks
worker_prefetch_multiplier = 1

# Enable eager execution mode in test environment to avoid blocking on connection attempts to Redis
if "pytest" in sys.modules or settings.APP_ENV == "test":
    task_always_eager = True
