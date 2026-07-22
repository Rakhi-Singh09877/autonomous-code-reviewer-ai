import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))

from app.infrastructure.queue.celery_tasks import celery_app
print("Celery app imported OK")
print("main:", celery_app.main)
print("broker:", celery_app.conf.broker_url)
print("tasks:", list(celery_app.tasks.keys()))
