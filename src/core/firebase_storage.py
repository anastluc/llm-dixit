from __future__ import annotations
"""
Firebase Storage client for Dixit card image collections.

Storage layout:   collections/{name}/{filename}
Firestore index:  dixit_collections/{name}
  { name, display_name, image_count, created_at, cards: [{filename, url}] }

Required env vars (shared with firebase_store.py):
  FIREBASE_CREDENTIALS_PATH | FIREBASE_CREDENTIALS_JSON
  FIREBASE_STORAGE_BUCKET   — e.g. "your-project.appspot.com"
"""

import logging
import os
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)

_COLLECTIONS_COL = "dixit_collections"
_STORAGE_PREFIX = "collections"

_bucket = None
_bucket_initialized = False


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

def _get_bucket():
    global _bucket, _bucket_initialized
    if _bucket_initialized:
        return _bucket

    bucket_name = os.getenv("FIREBASE_STORAGE_BUCKET")
    if not bucket_name:
        logger.info("FIREBASE_STORAGE_BUCKET not set; Firebase Storage disabled")
        _bucket_initialized = True
        return None

    try:
        import firebase_admin
        from firebase_admin import storage as fb_storage

        # Firebase app may already be initialized by firebase_store.py;
        # if not, we initialise it here (without storageBucket — see note below).
        # The storageBucket is passed to storage.bucket() directly.
        if not firebase_admin._apps:
            # App not yet initialised — do a minimal init (credentials only).
            # firebase_store._init() will be called separately and also uses _apps check.
            import json
            from firebase_admin import credentials
            creds_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
            creds_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
            if creds_path:
                cred = credentials.Certificate(creds_path)
            elif creds_json:
                cred = credentials.Certificate(json.loads(creds_json))
            else:
                logger.info("No Firebase credentials; Storage disabled")
                _bucket_initialized = True
                return None
            firebase_admin.initialize_app(cred, {"storageBucket": bucket_name})
        else:
            # App already initialised — get the bucket by name
            pass

        _bucket = fb_storage.bucket(bucket_name)
        logger.info("Firebase Storage initialised (bucket: %s)", bucket_name)
    except Exception as exc:
        logger.error("Firebase Storage init failed: %s", exc)
        _bucket = None

    _bucket_initialized = True
    return _bucket


def is_available() -> bool:
    return _get_bucket() is not None


# ---------------------------------------------------------------------------
# Firestore metadata helpers (via firebase_store's _init)
# ---------------------------------------------------------------------------

def _db():
    """Return Firestore client (re-uses firebase_store's initialisation)."""
    try:
        from firebase_admin import firestore
        return firestore.client()
    except Exception:
        return None


def _col():
    db = _db()
    return db.collection(_COLLECTIONS_COL) if db else None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def upload_collection(
    local_dir: str,
    name: str,
    *,
    display_name: str | None = None,
    progress_cb: Callable[[int, int, str], None] | None = None,
) -> dict:
    """Upload every image in local_dir to Firebase Storage as collection `name`.

    Files are stored at  collections/{name}/{filename}  and made publicly readable.
    Metadata is written to Firestore  dixit_collections/{name}.

    Args:
        local_dir: Local directory containing card images.
        name: Collection identifier (URL-safe slug, e.g. "original").
        display_name: Human-readable name (defaults to `name`).
        progress_cb: Optional callback(current, total, filename).

    Returns:
        Metadata dict that was saved to Firestore.
    """
    bucket = _get_bucket()
    if bucket is None:
        raise RuntimeError("Firebase Storage not available")

    image_extensions = {".jpg", ".jpeg", ".png", ".webp"}
    paths = sorted(
        p for p in Path(local_dir).iterdir()
        if p.suffix.lower() in image_extensions
    )
    if not paths:
        raise ValueError(f"No images found in {local_dir}")

    cards = []
    for i, path in enumerate(paths):
        if progress_cb:
            progress_cb(i + 1, len(paths), path.name)

        blob_path = f"{_STORAGE_PREFIX}/{name}/{path.name}"
        blob = bucket.blob(blob_path)
        blob.upload_from_filename(str(path))
        blob.make_public()
        cards.append({"filename": path.name, "url": blob.public_url})
        logger.debug("Uploaded %s → %s", path.name, blob.public_url)

    from datetime import datetime
    metadata = {
        "name": name,
        "display_name": display_name or name,
        "image_count": len(cards),
        "created_at": datetime.now().isoformat(),
        "cards": cards,
    }

    col = _col()
    if col is not None:
        col.document(name).set(metadata)
        logger.info("Collection '%s' metadata saved to Firestore (%d cards)", name, len(cards))
    else:
        logger.warning("Firestore unavailable — collection metadata NOT saved")

    return metadata


def list_collections() -> list[dict]:
    """Return all collection metadata docs from Firestore."""
    col = _col()
    if col is None:
        return []
    try:
        return [doc.to_dict() for doc in col.stream()]
    except Exception as exc:
        logger.error("list_collections failed: %s", exc)
        return []


def get_collection(name: str) -> dict | None:
    """Return metadata for a single collection, or None if not found."""
    col = _col()
    if col is None:
        return None
    try:
        snap = col.document(name).get()
        return snap.to_dict() if snap.exists else None
    except Exception as exc:
        logger.error("get_collection(%s) failed: %s", name, exc)
        return None


def get_collection_urls(name: str) -> list[tuple[str, str]]:
    """Return [(filename, public_url), …] for every card in the collection."""
    meta = get_collection(name)
    if meta is None:
        return []
    return [(c["filename"], c["url"]) for c in meta.get("cards", [])]


def delete_collection(name: str) -> int:
    """Delete all blobs for a collection and its Firestore metadata. Returns blob count."""
    bucket = _get_bucket()
    deleted = 0
    if bucket:
        prefix = f"{_STORAGE_PREFIX}/{name}/"
        for blob in bucket.list_blobs(prefix=prefix):
            blob.delete()
            deleted += 1
    col = _col()
    if col:
        col.document(name).delete()
    logger.info("Deleted collection '%s' (%d blobs)", name, deleted)
    return deleted
