# core/auth/service.py

# Suppress passlib bcrypt version warning
import warnings
warnings.filterwarnings('ignore', message='.*bcrypt.*')

import logging
logging.getLogger('passlib').setLevel(logging.ERROR)
import os
import sqlite3
import datetime
from pathlib import Path
from typing import Optional

from jose import jwt, JWTError
from passlib.context import CryptContext
from dotenv import load_dotenv

from server.core.auth.models import User

load_dotenv()

# ── Config ─────────────────────────────────────────────────────────────────────

# service.py — top section, replace everything between "── Config ──" and pwd_ctx

SECRET_KEY  = os.getenv("JWT_SECRET_KEY", "summly-secret-key-change-in-production")
ALGORITHM   = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

from server.core.database import DB_NAME   # ← already present, keep ONLY this

print("AUTH DB =", DB_NAME)
print("AUTH DB =", DB_NAME)

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Password helpers ───────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    # bcrypt hard limit is 72 bytes — truncate silently
    return pwd_ctx.hash(password[:72])


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_ctx.verify(plain[:72], hashed)
    except Exception:
        return False


# ── JWT helpers ────────────────────────────────────────────────────────────────

def create_access_token(user_id: int, email: str) -> str:
    expire = datetime.datetime.utcnow() + datetime.timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub":   str(user_id),
        "email": email,
        "exp":   expire,
        "iat":   datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


# ── Database helpers ───────────────────────────────────────────────────────────

def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def get_user_by_email(email: str) -> Optional[User]:
    conn = _conn()
    row = conn.execute(
        "SELECT * FROM users WHERE email = ? COLLATE NOCASE",
        (email,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    return _row_to_user(row)


def get_user_by_id(user_id: int) -> Optional[User]:
    conn = _conn()
    row = conn.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    return _row_to_user(row)


def create_user(full_name: str, email: str, password: str) -> User:
    """
    Creates a new user. Raises ValueError if email already exists.
    """
    if get_user_by_email(email):
        raise ValueError("Email already registered.")

    now  = datetime.datetime.utcnow().isoformat()
    conn = _conn()

    cursor = conn.execute(
        """
        INSERT INTO users
            (full_name, email, password_hash, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (full_name, email, hash_password(password), now, now)
    )

    user_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return get_user_by_id(user_id)


def update_last_login(user_id: int) -> None:
    now  = datetime.datetime.utcnow().isoformat()
    conn = _conn()
    conn.execute(
        "UPDATE users SET last_login = ?, updated_at = ? WHERE id = ?",
        (now, now, user_id)
    )
    conn.commit()
    conn.close()


def update_user_profile(
    user_id: int,
    full_name: Optional[str] = None,
    profile_image: Optional[str] = None,
) -> User:
    conn  = _conn()
    now   = datetime.datetime.utcnow().isoformat()
    user  = get_user_by_id(user_id)

    new_name  = full_name     if full_name     is not None else user.full_name
    new_img   = profile_image if profile_image is not None else user.profile_image

    conn.execute(
        """
        UPDATE users
        SET full_name = ?, profile_image = ?, updated_at = ?
        WHERE id = ?
        """,
        (new_name, new_img, now, user_id)
    )
    conn.commit()
    conn.close()
    return get_user_by_id(user_id)


def update_user_password(user_id: int, new_password: str) -> None:
    now  = datetime.datetime.utcnow().isoformat()
    conn = _conn()
    conn.execute(
        "UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?",
        (hash_password(new_password), now, user_id)
    )
    conn.commit()
    conn.close()


def authenticate_user(email: str, password: str):
    try:
        user = get_user_by_email(email)
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        update_last_login(user.id)
        return user
    except Exception as e:
        import traceback
        traceback.print_exc()
        return None


# ── Password reset tokens (stored in DB) ──────────────────────────────────────

def create_reset_token(email: str) -> Optional[str]:
    """
    Creates a password reset token for the given email.
    Returns None if email not found.
    Token expires in 1 hour.
    """
    user = get_user_by_email(email)
    if not user:
        return None

    import secrets
    token     = secrets.token_urlsafe(32)
    expires   = (
        datetime.datetime.utcnow()
        + datetime.timedelta(hours=1)
    ).isoformat()

    conn = _conn()
    # Delete any existing tokens for this user
    conn.execute(
        "DELETE FROM password_reset_tokens WHERE user_id = ?",
        (user.id,)
    )
    conn.execute(
        """
        INSERT INTO password_reset_tokens (user_id, token, expires_at)
        VALUES (?, ?, ?)
        """,
        (user.id, token, expires)
    )
    conn.commit()
    conn.close()
    return token


def consume_reset_token(token: str, new_password: str) -> bool:
    """
    Validates and consumes a reset token.
    Returns True if password was reset, False if token invalid/expired.
    """
    conn = _conn()
    row  = conn.execute(
        "SELECT * FROM password_reset_tokens WHERE token = ?",
        (token,)
    ).fetchone()

    if not row:
        conn.close()
        return False

    expires = datetime.datetime.fromisoformat(row["expires_at"])
    if datetime.datetime.utcnow() > expires:
        conn.execute(
            "DELETE FROM password_reset_tokens WHERE token = ?",
            (token,)
        )
        conn.commit()
        conn.close()
        return False

    update_user_password(row["user_id"], new_password)
    conn.execute(
        "DELETE FROM password_reset_tokens WHERE token = ?",
        (token,)
    )
    conn.commit()
    conn.close()
    return True


# ── Private helper ─────────────────────────────────────────────────────────────

def _row_to_user(row) -> User:
    return User(
        id=            row["id"],
        full_name=     row["full_name"],
        email=         row["email"],
        password_hash= row["password_hash"],
        profile_image= row["profile_image"],
        created_at=    row["created_at"],
        updated_at=    row["updated_at"],
        last_login=    row["last_login"],
    )