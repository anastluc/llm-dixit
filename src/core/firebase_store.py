from __future__ import annotations
"""
Firebase Firestore storage backend for Dixit game logs.

Required env vars:
  FIREBASE_CREDENTIALS_PATH  — path to service-account JSON file
  OR
  FIREBASE_CREDENTIALS_JSON  — service-account JSON as a string

Optional:
  FIREBASE_COLLECTION        — Firestore collection name (default: dixit_games)
"""

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_db = None
_initialized = False


def _init():
    global _db, _initialized
    if _initialized:
        return _db

    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
    except ImportError:
        logger.warning("firebase-admin not installed; Firebase storage disabled")
        _initialized = True
        return None

    creds_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
    creds_json = os.getenv("FIREBASE_CREDENTIALS_JSON")

    if not creds_path and not creds_json:
        logger.info("No Firebase credentials set; Firebase storage disabled")
        _initialized = True
        return None

    try:
        if not firebase_admin._apps:
            if creds_path:
                cred = credentials.Certificate(creds_path)
            else:
                cred = credentials.Certificate(json.loads(creds_json))
            options = {}
            bucket = os.getenv("FIREBASE_STORAGE_BUCKET")
            if bucket:
                options["storageBucket"] = bucket
            firebase_admin.initialize_app(cred, options)

        _db = firestore.client()
        logger.info("Firebase Firestore initialised")
    except Exception as exc:
        logger.error("Failed to initialise Firebase: %s", exc)
        _db = None

    _initialized = True
    return _db


def _col():
    db = _init()
    if db is None:
        return None
    return db.collection(os.getenv("FIREBASE_COLLECTION", "dixit_games"))


def is_available() -> bool:
    return _init() is not None


def save_game(game_id: str, data: dict) -> bool:
    """Upsert a game document. Returns True on success."""
    col = _col()
    if col is None:
        return False
    try:
        # Store a top-level timestamp for ordering without needing a composite index
        doc = dict(data)
        doc["_created_at"] = data.get("game_configuration", {}).get("timestamp", game_id)
        col.document(game_id).set(doc)
        logger.info("Game %s saved to Firestore", game_id)
        return True
    except Exception as exc:
        logger.error("Firestore save failed for game %s: %s", game_id, exc)
        return False


def get_game(game_id: str) -> dict | None:
    col = _col()
    if col is None:
        return None
    try:
        snap = col.document(game_id).get()
        if not snap.exists:
            return None
        d = snap.to_dict()
        d.pop("_created_at", None)
        return d
    except Exception as exc:
        logger.error("Firestore get failed for game %s: %s", game_id, exc)
        return None


def clear_all_games() -> int:
    """Delete every document in the collection. Returns the number of docs deleted."""
    col = _col()
    if col is None:
        return 0
    try:
        deleted = 0
        # Firestore recommends deleting in batches of ≤500
        while True:
            docs = list(col.limit(500).stream())
            if not docs:
                break
            batch = _init().batch()
            for doc in docs:
                batch.delete(doc.reference)
            batch.commit()
            deleted += len(docs)
        logger.info("Cleared %d game documents from Firestore", deleted)
        return deleted
    except Exception as exc:
        logger.error("Firestore clear failed: %s", exc)
        return 0


def list_games() -> list[dict]:
    """Return all game documents ordered newest-first."""
    col = _col()
    if col is None:
        return []
    try:
        docs = col.order_by("_created_at", direction="DESCENDING").stream()
        results = []
        for doc in docs:
            d = doc.to_dict()
            d.pop("_created_at", None)
            results.append(d)
        return results
    except Exception as exc:
        logger.error("Firestore list failed: %s", exc)
        return []
