import logging
import sys
from typing import Any, Dict


class JobLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        job_id = self.extra.get("jobId")
        prefix = f"jobId={job_id} " if job_id else ""
        return prefix + msg, kwargs


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def get_logger(name: str, job_id: str | None = None) -> JobLoggerAdapter:
    logger = logging.getLogger(name)
    return JobLoggerAdapter(logger, {"jobId": job_id})
