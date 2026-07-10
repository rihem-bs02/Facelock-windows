import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from facelook.crypto_store import CryptoStore


class BiometricDatabase:
    """
    Stores encrypted biometric embeddings.

    Important:
    - no raw face images
    - no JPEG or PNG storage
    - only encrypted vectors
    """

    def __init__(self, db_path: Path, crypto: CryptoStore):
        self.db_path = Path(db_path)
        self.crypto = crypto
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.db_path))

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    embedding_encrypted TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS auth_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT,
                    result TEXT NOT NULL,
                    confidence REAL,
                    reason TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def save_embedding(self, username: str, embedding: np.ndarray) -> None:
        username = username.strip()

        if not username:
            raise ValueError("username is required")

        embedding = np.asarray(embedding, dtype=np.float32)

        encrypted = self.crypto.encrypt(embedding.tobytes())
        now = self._now()

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO users (
                    username,
                    embedding_encrypted,
                    created_at,
                    updated_at,
                    active
                )
                VALUES (?, ?, ?, ?, 1)
                ON CONFLICT(username)
                DO UPDATE SET
                    embedding_encrypted = excluded.embedding_encrypted,
                    updated_at = excluded.updated_at,
                    active = 1
                """,
                (username, encrypted, now, now)
            )

    def load_embedding(self, username: str) -> np.ndarray | None:
        username = username.strip()

        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT embedding_encrypted
                FROM users
                WHERE username = ?
                  AND active = 1
                """,
                (username,)
            ).fetchone()

        if row is None:
            return None

        decrypted = self.crypto.decrypt(row[0])
        return np.frombuffer(decrypted, dtype=np.float32)

    def user_exists(self, username: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT 1
                FROM users
                WHERE username = ?
                  AND active = 1
                """,
                (username.strip(),)
            ).fetchone()

        return row is not None

    def list_users(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT username, created_at, updated_at, active
                FROM users
                ORDER BY username ASC
                """
            ).fetchall()

        return [
            {
                "username": row[0],
                "created_at": row[1],
                "updated_at": row[2],
                "active": bool(row[3]),
            }
            for row in rows
        ]

    def delete_user(self, username: str) -> bool:
        username = username.strip()

        if not username:
            raise ValueError("username is required")

        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE users
                SET active = 0,
                    updated_at = ?
                WHERE username = ?
                  AND active = 1
                """,
                (self._now(), username)
            )

        return cursor.rowcount > 0

    def permanently_delete_user(self, username: str) -> bool:
        username = username.strip()

        if not username:
            raise ValueError("username is required")

        with self._connect() as conn:
            cursor = conn.execute(
                """
                DELETE FROM users
                WHERE username = ?
                """,
                (username,)
            )

        return cursor.rowcount > 0

    def log_auth(
        self,
        username: str | None,
        result: str,
        confidence: float | None,
        reason: str | None
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO auth_logs (
                    username,
                    result,
                    confidence,
                    reason,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    username,
                    result,
                    confidence,
                    reason,
                    self._now()
                )
            )

    def list_auth_logs(self, limit: int = 20) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT username, result, confidence, reason, created_at
                FROM auth_logs
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,)
            ).fetchall()

        return [
            {
                "username": row[0],
                "result": row[1],
                "confidence": row[2],
                "reason": row[3],
                "created_at": row[4],
            }
            for row in rows
        ]

    def stats(self) -> dict:
        with self._connect() as conn:
            active_users = conn.execute(
                """
                SELECT COUNT(*)
                FROM users
                WHERE active = 1
                """
            ).fetchone()[0]

            total_users = conn.execute(
                """
                SELECT COUNT(*)
                FROM users
                """
            ).fetchone()[0]

            total_logs = conn.execute(
                """
                SELECT COUNT(*)
                FROM auth_logs
                """
            ).fetchone()[0]

        return {
            "database_path": str(self.db_path),
            "active_users": active_users,
            "total_users": total_users,
            "total_auth_logs": total_logs,
        }