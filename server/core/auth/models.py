# core/auth/models.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class User:
    """
    Represents a user row from the database.
    Used internally — never sent to frontend directly.
    Use UserPublic schema for API responses.
    """
    id:            int
    full_name:     str
    email:         str
    password_hash: str
    profile_image: Optional[str]
    created_at:    str
    updated_at:    str
    last_login:    Optional[str]