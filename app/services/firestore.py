from __future__ import annotations

import json
from typing import Any, Dict

import firebase_admin
from firebase_admin import credentials, firestore

from app.config import get_settings


_app = None


def get_firestore_client() -> firestore.Client:
    global _app
    settings = get_settings()

    if _app is None:
        if settings.FIREBASE_SERVICE_ACCOUNT_JSON:
            info = json.loads(settings.FIREBASE_SERVICE_ACCOUNT_JSON)
            cred = credentials.Certificate(info)
        elif settings.GOOGLE_APPLICATION_CREDENTIALS:
            cred = credentials.Certificate(settings.GOOGLE_APPLICATION_CREDENTIALS)
        else:
            cred = credentials.ApplicationDefault()

        _app = firebase_admin.initialize_app(cred, {"projectId": settings.FIREBASE_PROJECT_ID})

    return firestore.client(app=_app)


def ensure_workspace_root(workspace_id: str) -> None:
    db = get_firestore_client()
    db.collection("workspaces").document(workspace_id).set(
        {"updatedAt": firestore.SERVER_TIMESTAMP}, merge=True
    )


def workspace_reel_ref(workspace_id: str, reel_id: str):
    settings = get_settings()
    db = get_firestore_client()
    ensure_workspace_root(workspace_id)
    return (
        db.collection("workspaces")
        .document(workspace_id)
        .collection(settings.FIRESTORE_REELS_COLLECTION)
        .document(reel_id)
    )


def workspace_job_ref(workspace_id: str, job_id: str):
    settings = get_settings()
    db = get_firestore_client()
    ensure_workspace_root(workspace_id)
    return (
        db.collection("workspaces")
        .document(workspace_id)
        .collection(settings.FIRESTORE_JOBS_COLLECTION)
        .document(job_id)
    )


def build_reel_doc(payload: Dict[str, Any]) -> Dict[str, Any]:
    doc = dict(payload)
    doc.setdefault("status", "queued")
    doc.setdefault("transcriptText", None)
    doc.setdefault("updatedAt", firestore.SERVER_TIMESTAMP)
    return doc


def build_job_doc(payload: Dict[str, Any]) -> Dict[str, Any]:
    doc = dict(payload)
    doc.setdefault("status", "queued")
    doc.setdefault("attempts", 0)
    doc.setdefault("leaseUntil", None)
    doc.setdefault("updatedAt", firestore.SERVER_TIMESTAMP)
    return doc
