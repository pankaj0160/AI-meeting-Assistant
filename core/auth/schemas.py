# core/auth/schemas.py

from pydantic import BaseModel, EmailStr, Field
from typing import Optional


# ── Request schemas (what frontend sends) ─────────────────────────────────────

class RegisterRequest(BaseModel):
    full_name: str  = Field(min_length=2,  max_length=100)
    email:     EmailStr
    password:  str  = Field(min_length=8,  max_length=128)


class LoginRequest(BaseModel):
    email:    EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token:        str
    new_password: str = Field(min_length=8, max_length=128)


class UpdateProfileRequest(BaseModel):
    full_name:     Optional[str]  = Field(default=None, min_length=2, max_length=100)
    profile_image: Optional[str]  = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password:     str = Field(min_length=8, max_length=128)


# ── Response schemas (what backend sends) ─────────────────────────────────────

class UserPublic(BaseModel):
    """Safe user object — never includes password_hash."""
    id:            int
    full_name:     str
    email:         str
    profile_image: Optional[str] = None
    created_at:    str
    last_login:    Optional[str] = None


class AuthResponse(BaseModel):
    """Returned on successful login or register."""
    access_token:  str
    token_type:    str = "bearer"
    user:          UserPublic


class MessageResponse(BaseModel):
    message: str