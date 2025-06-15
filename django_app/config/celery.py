import os
from celery import Celery
from django.conf import settings
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('t3_chat')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat Configuration for Periodic Tasks
app.conf.beat_schedule = {
    # Run analytics report generation every hour
    'generate-analytics-report': {
        'task': 'chat.tasks.generate_analytics_report',
        'schedule': crontab(minute=0),  # Every hour at minute 0
    },
    
    # Run data cleanup daily at 2 AM
    'cleanup-old-data': {
        'task': 'chat.tasks.cleanup_old_data',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2:00 AM
    },
    
    # Warm cache every 30 minutes
    'warm-cache': {
        'task': 'chat.tasks.warm_cache',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
    },
    
    # Health check every 5 minutes
    'health-check': {
        'task': 'chat.tasks.health_check',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
}

# Celery Configuration
app.conf.update(
    # Task routing
    task_routes={
        'chat.tasks.process_ai_chat_request': {'queue': 'ai_requests'},
        'chat.tasks.process_image_generation': {'queue': 'image_generation'},
        'chat.tasks.process_file_upload': {'queue': 'file_processing'},
        'chat.tasks.cleanup_old_data': {'queue': 'maintenance'},
        'chat.tasks.generate_analytics_report': {'queue': 'analytics'},
        'chat.tasks.warm_cache': {'queue': 'maintenance'},
        'chat.tasks.health_check': {'queue': 'monitoring'},
    },
    
    # Task priorities
    task_default_priority=5,
    task_inherit_parent_priority=True,
    task_priority_steps=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    
    # Result backend configuration
    result_expires=3600,  # Results expire after 1 hour
    result_persistent=True,
    
    # Task execution configuration
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    
    # Worker configuration
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    worker_disable_rate_limits=False,
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # Security
    task_always_eager=False,  # Set to True for testing
    task_eager_propagates=True,
    
    # Timezone
    timezone='UTC',
    enable_utc=True,
)

@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery setup"""
    print(f'Request: {self.request!r}')
    return 'Celery is working!' 