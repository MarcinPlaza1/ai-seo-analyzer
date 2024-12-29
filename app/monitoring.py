from prometheus_client import Counter, Histogram
import time

REQUEST_TIME = Histogram('request_processing_seconds', 'Time spent processing request')
AUDIT_COUNTER = Counter('audit_total', 'Total number of audits', ['status'])
TASK_DURATION = Histogram('celery_task_duration_seconds', 'Time spent executing Celery task', ['task_name'])

class TaskTimer:
    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, *args):
        duration = time.time() - self.start
        TASK_DURATION.labels(task_name=self.task_name).observe(duration) 