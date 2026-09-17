"""SQLite-based job application tracker and deduplication store."""

import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from src.logger import get_logger

logger = get_logger("tracker")


class JobTracker:
    """Manages persistent SQLite storage for tracked jobs and application history."""

    def __init__(self, db_path: str | Path = "data/job_seekr.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initializes database tables and indexes."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url_hash TEXT UNIQUE NOT NULL,
                    url TEXT NOT NULL,
                    title TEXT NOT NULL,
                    company TEXT NOT NULL,
                    location TEXT,
                    source TEXT,
                    match_score INTEGER DEFAULT 0,
                    match_rationale TEXT,
                    status TEXT DEFAULT 'discovered',
                    application_path TEXT,
                    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_url_hash ON jobs(url_hash);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);")
            conn.commit()

    @staticmethod
    def normalize_url(url: str) -> str:
        """Normalizes a URL by removing common tracking parameters."""
        if not url:
            return ""
        try:
            parsed = urlparse(url.strip())
            # Filter out tracking query params
            filtered_query = [
                (k, v) for k, v in parse_qsl(parsed.query)
                if not k.lower().startswith(("utm_", "ref", "fbclid", "gclid"))
            ]
            normalized = parsed._replace(
                query=urlencode(filtered_query),
                fragment=""
            )
            return urlunparse(normalized).rstrip("/")
        except Exception:
            return url.strip()

    @classmethod
    def compute_job_hash(cls, url: str, title: str = "", company: str = "") -> str:
        """Computes a unique SHA-256 hash based on normalized URL or title+company."""
        norm_url = cls.normalize_url(url)
        if norm_url and len(norm_url) > 10:
            key = norm_url.lower()
        else:
            key = f"{title.strip().lower()}::{company.strip().lower()}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def is_job_seen(self, url: str, title: str = "", company: str = "") -> bool:
        """Checks if a job has already been tracked/processed."""
        job_hash = self.compute_job_hash(url, title, company)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM jobs WHERE url_hash = ? LIMIT 1", (job_hash,))
            return cursor.fetchone() is not None

    def add_job(
        self,
        url: str,
        title: str,
        company: str,
        location: str = "",
        source: str = "",
        match_score: int = 0,
        match_rationale: str = "",
        status: str = "discovered",
        application_path: str = "",
    ) -> int:
        """Inserts a new job record. Returns the job ID."""
        job_hash = self.compute_job_hash(url, title, company)
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO jobs (
                    url_hash, url, title, company, location, source,
                    match_score, match_rationale, status, application_path,
                    discovered_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_hash, url.strip(), title.strip(), company.strip(),
                location.strip(), source.strip(), match_score,
                match_rationale.strip(), status.strip(),
                application_path.strip(), now, now
            ))
            conn.commit()
            job_id = cursor.lastrowid
            logger.info(f"Tracked new job #{job_id}: {title} at {company} (Score: {match_score}%)")
            return job_id

    def update_job(
        self,
        job_id: int,
        status: Optional[str] = None,
        match_score: Optional[int] = None,
        match_rationale: Optional[str] = None,
        application_path: Optional[str] = None,
    ) -> bool:
        """Updates specific fields of an existing job record."""
        updates: List[str] = []
        params: List[Any] = []

        if status is not None:
            updates.append("status = ?")
            params.append(status)
        if match_score is not None:
            updates.append("match_score = ?")
            params.append(match_score)
        if match_rationale is not None:
            updates.append("match_rationale = ?")
            params.append(match_rationale)
        if application_path is not None:
            updates.append("application_path = ?")
            params.append(application_path)

        if not updates:
            return False

        updates.append("updated_at = ?")
        params.append(datetime.now(timezone.utc).isoformat())
        params.append(job_id)

        query = f"UPDATE jobs SET {', '.join(updates)} WHERE id = ?"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount > 0

    def get_job_by_id(self, job_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves a job by its integer ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_jobs(
        self,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Lists tracked jobs, optionally filtered by status, ordered by match_score DESC."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if status:
                cursor.execute(
                    "SELECT * FROM jobs WHERE status = ? ORDER BY match_score DESC, id DESC LIMIT ?",
                    (status, limit),
                )
            else:
                cursor.execute(
                    "SELECT * FROM jobs ORDER BY match_score DESC, id DESC LIMIT ?",
                    (limit,),
                )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def mark_applied(self, job_id: int) -> bool:
        """Marks a job application as applied."""
        return self.update_job(job_id, status="applied")
