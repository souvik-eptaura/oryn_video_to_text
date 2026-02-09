from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Tuple

from google.cloud import firestore

from app.config import get_settings
from app.utils.time import utc_now


def _lease_expired(lease_until: datetime | None) -> bool:
    if not lease_until:
        return True
    return lease_until <= utc_now()


def acquire_lease(job_ref: firestore.DocumentReference) -> Tuple[bool, Dict[str, Any]]:
    settings = get_settings()
    db = job_ref._client

    @firestore.transactional
    def txn(transaction: firestore.Transaction) -> Tuple[bool, Dict[str, Any]]:
        snapshot = job_ref.get(transaction=transaction)
        if not snapshot.exists:
            return False, {"error": "Job not found"}

        data = snapshot.to_dict() or {}
        status = data.get("status")
        lease_until = data.get("leaseUntil")
        attempts = int(data.get("attempts", 0))

        if status == "completed":
            return False, {"status": "completed"}

        if lease_until and isinstance(lease_until, datetime):
            if lease_until.tzinfo is None:
                lease_until = lease_until.replace(tzinfo=timezone.utc)
        if lease_until and not _lease_expired(lease_until):
            return False, {"status": "leased"}

        new_lease = utc_now() + timedelta(seconds=settings.LEASE_SECONDS)
        transaction.update(
            job_ref,
            {
                "status": "running",
                "leaseUntil": new_lease,
                "attempts": attempts + 1,
                "updatedAt": firestore.SERVER_TIMESTAMP,
            },
        )
        return True, {"attempts": attempts + 1}

    return txn(db.transaction())
