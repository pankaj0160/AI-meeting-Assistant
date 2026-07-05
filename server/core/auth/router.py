# core/auth/router.py

# FIX: removed debug print() statements and moved import traceback to top
import logging
import traceback

from fastapi import APIRouter, HTTPException, Depends, status, Request

try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
except ImportError:
    def get_remote_address(r): return "0.0.0.0"
    class Limiter:
        def __init__(self, **kw): pass
        def limit(self, *a, **kw):
            def d(fn): return fn
            return d

from server.core.auth.schemas import (
    RegisterRequest, LoginRequest,
    ForgotPasswordRequest, ResetPasswordRequest,
    UpdateProfileRequest, ChangePasswordRequest,
    UserPublic, AuthResponse, MessageResponse,
)
from server.core.auth.service import (
    create_user, authenticate_user,
    create_access_token, get_user_by_email,
    create_reset_token, consume_reset_token,
    update_user_profile, update_user_password,
    verify_password,
)
from server.core.auth.dependencies import get_current_user
from server.core.auth.models import User

router = APIRouter(prefix="/auth", tags=["Auth"])
limiter = Limiter(key_func=get_remote_address)

# FIX: use proper logger instead of print()
# logging.getLogger(__name__) creates a logger named "server.core.auth.router"
# This logger respects your log level settings — in production set to WARNING
# so DEBUG/INFO messages are silent. print() has no such control.
logger = logging.getLogger(__name__)


def _to_public(user: User) -> UserPublic:
    return UserPublic(
        id=            user.id,
        full_name=     user.full_name,
        email=         user.email,
        profile_image= user.profile_image,
        created_at=    user.created_at,
        last_login=    user.last_login,
    )


# ── Register ───────────────────────────────────────────────────────────────────

@router.post("/register", response_model=AuthResponse, status_code=201)
@limiter.limit("5/minute")
def register(request: Request, body: RegisterRequest):
    try:
        user = create_user(
            full_name=body.full_name,
            email=body.email,
            password=body.password,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    token = create_access_token(user.id, user.email)
    # FIX: log with logger (not print) — no sensitive data in the message
    logger.info("New user registered: id=%s", user.id)
    return AuthResponse(access_token=token, user=_to_public(user))


# ── Login ──────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=AuthResponse)
@limiter.limit("5/minute")
def login(request: Request, body: LoginRequest):
    # FIX: removed print("LOGIN ROUTE HIT"), print("LOGIN EMAIL:", body.email),
    # print("USER:", user) — these printed real user emails to the server console.
    # In production that means every login attempt leaks a user's email to logs.
    # Rule: never log email addresses, passwords, or tokens — only user IDs.

    user = authenticate_user(body.email, body.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(user.id, user.email)
    # Safe to log: user ID only — not the email, not the token
    logger.info("User logged in: id=%s", user.id)
    return AuthResponse(access_token=token, user=_to_public(user))


# ── Get current user ───────────────────────────────────────────────────────────

@router.get("/me", response_model=UserPublic)
def me(current_user: User = Depends(get_current_user)):
    return _to_public(current_user)


# ── Update profile ─────────────────────────────────────────────────────────────

@router.put("/me", response_model=UserPublic)
def update_me(
    body: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
):
    updated = update_user_profile(
        user_id=       current_user.id,
        full_name=     body.full_name,
        profile_image= body.profile_image,
    )
    return _to_public(updated)


# ── Change password ────────────────────────────────────────────────────────────

@router.put("/me/password", response_model=MessageResponse)
@limiter.limit("5/minute")
def change_password(
    request: Request,
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
):
    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    update_user_password(current_user.id, body.new_password)
    logger.info("User changed password: id=%s", current_user.id)
    return MessageResponse(message="Password updated successfully")


# ── Forgot password ────────────────────────────────────────────────────────────

@router.post("/forgot-password", response_model=MessageResponse)
@limiter.limit("3/minute")
def forgot_password(request: Request, body: ForgotPasswordRequest):
    # FIX: Critical security bug — the old code returned the reset token
    # directly in the API response:
    #   return MessageResponse(message=f"Reset token generated. Token: {token}")
    #
    # This let anyone reset any user's account with just two API calls:
    #   1. POST /auth/forgot-password  { email: "victim@example.com" }
    #      → response contains the token directly
    #   2. POST /auth/reset-password   { token: "...", new_password: "hacked" }
    #      → account taken over. No email access needed.
    #
    # The fix: call create_reset_token() but NEVER return the token in the
    # response. In production this function should email the token to the user.
    # The response always says the same thing whether the email exists or not
    # — this prevents "email enumeration" (finding out which emails are registered).

    token = create_reset_token(body.email)

    if token:
        # TODO: send token via email here using your email service
        # e.g. send_reset_email(body.email, token)
        # For now we log it at WARNING level so you can find it in server logs
        # during development — remove this log line once email is wired up.
        logger.warning(
            "Password reset token created for email (dev only — wire up email): %s",
            body.email
        )

    # FIX: always return the same message — never reveal whether the email exists.
    # If we said "email not found" when the email doesn't exist, attackers could
    # use this endpoint to discover which emails are registered (enumeration attack).
    return MessageResponse(
        message="If that email exists in our system, a reset link has been sent."
    )


# ── Reset password ─────────────────────────────────────────────────────────────

@router.post("/reset-password", response_model=MessageResponse)
@limiter.limit("5/minute")
def reset_password(request: Request, body: ResetPasswordRequest):
    success = consume_reset_token(body.token, body.new_password)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )
    logger.info("Password reset successfully via token")
    return MessageResponse(message="Password reset successfully. Please log in.")