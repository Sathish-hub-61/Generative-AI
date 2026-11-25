"""Session-based authentication & SQLite user store with Werkzeug password hashing."""

import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple

from werkzeug.security import check_password_hash, generate_password_hash

DB_PATH = Path(__file__).parent / "users.db"
SECRET_PATH = Path(__file__).parent / ".secret_key"
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def get_or_create_secret_key() -> bytes:
    """Return a persistent secret key so Flask sessions survive debug reloads."""
    env_key = os.getenv("FLASK_SECRET_KEY")
    if env_key:
        return env_key.encode("utf-8")
    if SECRET_PATH.exists():
        data = SECRET_PATH.read_bytes()
        if len(data) >= 24:
            return data
    key = os.urandom(32)
    try:
        SECRET_PATH.write_bytes(key)
    except Exception:
        pass
    return key


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize the SQLite users table if it does not exist."""
    with _get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def create_user(full_name: str, email: str, password: str) -> Tuple[bool, str, Optional[Dict]]:
    """Validate inputs, hash password securely, and create a new user."""
    name = (full_name or "").strip()
    norm_email = (email or "").strip().lower()

    if len(name) < 2:
        return False, "Full name must be at least 2 characters.", None
    if not _EMAIL_RE.match(norm_email):
        return False, "Please enter a valid email address.", None
    if not password or len(password) < 6:
        return False, "Password must be at least 6 characters long.", None

    pw_hash = generate_password_hash(password)
    created_at = datetime.now(timezone.utc).isoformat()

    init_db()
    try:
        with _get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO users (full_name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
                (name, norm_email, pw_hash, created_at),
            )
            conn.commit()
            user_id = cur.lastrowid
    except sqlite3.IntegrityError:
        return False, "An account with this email address already exists.", None

    return True, "Account created successfully.", {
        "id": user_id,
        "full_name": name,
        "email": norm_email,
    }


def authenticate_user(email: str, password: str) -> Optional[Dict]:
    """Verify email and password hash. Returns safe user dict or None."""
    norm_email = (email or "").strip().lower()
    if not norm_email or not password:
        return None

    init_db()
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT id, full_name, email, password_hash FROM users WHERE email = ?",
            (norm_email,),
        ).fetchone()

    if not row or not check_password_hash(row["password_hash"], password):
        return None

    return {
        "id": row["id"],
        "full_name": row["full_name"],
        "email": row["email"],
    }


def get_user_by_id(user_id: Optional[int]) -> Optional[Dict]:
    """Look up a user by ID without exposing password_hash."""
    if not user_id:
        return None
    init_db()
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT id, full_name, email FROM users WHERE id = ?",
            (int(user_id),),
        ).fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "full_name": row["full_name"],
        "email": row["email"],
    }
