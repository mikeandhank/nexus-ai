"""
Celery configuration for NexusOS
Enables async task processing, background jobs, and scalable architecture
"""
from celery import Celery
import os

# Redis URL from environment or default
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

app = Celery('nexusos',
             broker=REDIS_URL,
             backend=REDIS_URL)

app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 min max
    worker_prefetch_multiplier=4,
)

# Import tasks
from tasks import llm_tasks, tool_tasks

app.autodiscover_tasks(['tasks'])
