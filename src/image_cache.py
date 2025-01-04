import sqlite3
from datetime import datetime
import hashlib

class ImageAnalysisCache:
    def __init__(self, db_path="image_analysis_cache.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize the SQLite database with the required schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analysis_cache (
                    model TEXT,
                    image_hash TEXT,
                    prompt TEXT,
                    response TEXT,
                    timestamp DATETIME,
                    PRIMARY KEY (model, image_hash, prompt)
                )
            ''')
            conn.commit()

    def _compute_image_hash(self, image_path):
        """Compute a hash of the image file to use as part of the cache key."""
        with open(image_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()

    def get_cached_response(self, model: str, image_path: str, prompt: str) -> str | None:
        """
        Retrieve a cached response if it exists.
        Returns None if no cache entry is found.
        """
        image_hash = self._compute_image_hash(image_path)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT response
                FROM analysis_cache
                WHERE model = ? AND image_hash = ? AND prompt = ?
            ''', (model, image_hash, prompt))
            
            result = cursor.fetchone()
            return result[0] if result else None

    def cache_response(self, model: str, image_path: str, prompt: str, response: str):
        """Store a new response in the cache."""
        image_hash = self._compute_image_hash(image_path)
        timestamp = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO analysis_cache
                (model, image_hash, prompt, response, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (model, image_hash, prompt, response, timestamp))
            conn.commit()