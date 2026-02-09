from redis import Redis
from rq import Queue

from app.config import get_settings


QUEUE_NAME = "sources"


def get_queue() -> Queue:
    settings = get_settings()
    redis_conn = Redis.from_url(settings.REDIS_URL)
    return Queue(name=QUEUE_NAME, connection=redis_conn)


def enqueue_job(job_id: str, workspace_id: str) -> None:
    queue = get_queue()
    queue.enqueue("app.workers.worker.process_job", job_id, workspace_id)
