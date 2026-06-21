# core/auth/service.py

import warnings
warnings.filterwarnings('ignore', message='.*bcrypt.*')

import logging
logging.getLogger('passlib').setLevel(logging.ERROR)

import os
import datetime
import secrets
from typing import Optional

from jose import jwt, JWTError
from passlib.context import CryptContext
from dotenv import load_dotenv

import psycopg2.extras
from server.core.database import get_connection
from server.core.auth.models import User

load_dotenv()

# ── Config ─────────────────────────────────────────────────────────────────────

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "summly-secret-key-change-in-production")
ALGORITHM  = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Password helpers ───────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
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

def _row_to_user(row: dict) -> User:
    return User(
        id=            row["id"],
        full_name=     row["full_name"],
        email=         row["email"],
        password_hash= row["password_hash"],
        profile_image= row.get("profile_image"),
        created_at=    str(row["created_at"]),
        updated_at=    str(row["updated_at"]),
        last_login=    str(row["last_login"]) if row.get("last_login") else None,
    )


def get_user_by_email(email: str) -> Optional[User]:
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM users WHERE LOWER(email) = LOWER(%s)", (email,))
        row = cur.fetchone()
    return _row_to_user(dict(row)) if row else None


def get_user_by_id(user_id: int) -> Optional[User]:
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()
    return _row_to_user(dict(row)) if row else None


def create_user(full_name: str, email: str, password: str) -> User:
    if get_user_by_email(email):
        raise ValueError("Email already registered.")

    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            INSERT INTO users (full_name, email, password_hash, created_at, updated_at)
            VALUES (%s, %s, %s, NOW(), NOW())
            RETURNING *
            """,
            (full_name, email, hash_password(password)),
        )
        row = cur.fetchone()
    return _row_to_user(dict(row))


def update_last_login(user_id: int) -> None:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET last_login = NOW(), updated_at = NOW() WHERE id = %s",
            (user_id,),
        )


def update_user_profile(
    user_id: int,
    full_name: Optional[str] = None,
    profile_image: Optional[str] = None,
) -> User:
    user = get_user_by_id(user_id)
    new_name = full_name     if full_name     is not None else user.full_name
    new_img  = profile_image if profile_image is not None else user.profile_image

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET full_name = %s, profile_image = %s, updated_at = NOW() WHERE id = %s",
            (new_name, new_img, user_id),
        )
    return get_user_by_id(user_id)


def update_user_password(user_id: int, new_password: str) -> None:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET password_hash = %s, updated_at = NOW() WHERE id = %s",
            (hash_password(new_password), user_id),
        )


def authenticate_user(email: str, password: str) -> Optional[User]:
    try:
        user = get_user_by_email(email)
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        update_last_login(user.id)
        return user
    except Exception:
        import traceback
        traceback.print_exc()
        return None


# ── Password reset tokens ──────────────────────────────────────────────────────

def create_reset_token(email: str) -> Optional[str]:
    user = get_user_by_email(email)
    if not user:
        return None

    token   = secrets.token_urlsafe(32)
    expires = datetime.datetime.utcnow() + datetime.timedelta(hours=1)

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM password_reset_tokens WHERE user_id = %s", (user.id,))
        cur.execute(
            """
            INSERT INTO password_reset_tokens (user_id, token, expires_at)
            VALUES (%s, %s, NOW() + INTERVAL '1 hour')
            """,
            (user.id, token),
        )
    return token


def consume_reset_token(token: str, new_password: str) -> bool:
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM password_reset_tokens WHERE token = %s", (token,))
        row = cur.fetchone()

        if not row:
            return False

        # expires_at comes back as a real datetime from PostgreSQL (no fromisoformat needed)
        if datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc) > row["expires_at"]:
            cur.execute("DELETE FROM password_reset_tokens WHERE token = %s", (token,))
            return False

        update_user_password(row["user_id"], new_password)
        cur.execute("DELETE FROM password_reset_tokens WHERE token = %s", (token,))

    return True