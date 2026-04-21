from __future__ import annotations
"""
Image analysis cache — SQLite-backed singleton.


Key: (model, sha256(image_file), prompt)
Value: LLM response string

Access via get_cache() to get the module-level singleton.
"""

import hashlib
import logging
import sqlite3
from datetime import datetime

logger = logging.getLogger(__name__)

_DB_PATH = "image_analysis_cache.db"
_instance: "ImageAnalysisCache | None" = None


def get_cache(db_path: str = _DB_PATH) -> "ImageAnalysisCache":
    global _instance
    if _instance is None:
        _instance = ImageAnalysisCache(db_path)
    return _instance


class ImageAnalysisCache:
    def __init__(self, db_path: str = _DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analysis_cache (
                    model       TEXT,
                    image_hash  TEXT,
                    prompt      TEXT,
                    response    TEXT,
                    timestamp   TEXT,
                    PRIMARY KEY (model, image_hash, prompt)
                )
            """)
            conn.commit()

    def _hash(self, image_path: str) -> str:
        with open(image_path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    def get(self, model: str, image_path: str, prompt: str) -> str | None:
        image_hash = self._hash(image_path)
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT response FROM analysis_cache WHERE model=? AND image_hash=? AND prompt=?",
                (model, image_hash, prompt),
            ).fetchone()
        if row:
            logger.debug("Cache hit: %s / %s", model, image_path)
        return row[0] if row else None

    def set(self, model: str, image_path: str, prompt: str, response: str) -> None:
        image_hash = self._hash(image_path)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO analysis_cache
                   (model, image_hash, prompt, response, timestamp)
                   VALUES (?, ?, ?, ?, ?)""",
                (model, image_hash, prompt, response, datetime.now().isoformat()),
            )
            conn.commit()
