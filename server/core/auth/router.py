# core/auth/router.py

from fastapi import APIRouter, HTTPException, Depends, status

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
def register(body: RegisterRequest):
    """
    Create a new account.
    Returns JWT token + user object on success.
    """
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
    return AuthResponse(access_token=token, user=_to_public(user))


# ── Login ──────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest):
    print("LOGIN ROUTE HIT")
    try:
        print("LOGIN EMAIL:", body.email)

        user = authenticate_user(body.email, body.password)
        print("USER:", user)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        token = create_access_token(user.id, user.email)
        print("TOKEN CREATED")

        return AuthResponse(
            access_token=token,
            user=_to_public(user)
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise


# ── Get current user ───────────────────────────────────────────────────────────

@router.get("/me", response_model=UserPublic)
def me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user."""
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
def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
):
    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    update_user_password(current_user.id, body.new_password)
    return MessageResponse(message="Password updated successfully")


# ── Forgot password ────────────────────────────────────────────────────────────

@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(body: ForgotPasswordRequest):
    """
    Sends a reset token. Always returns 200 to prevent email enumeration.
    In production, send this token via email.
    For now, the token is returned in the response for testing.
    """
    token = create_reset_token(body.email)

    # TODO Phase 4: send via SMTP/Resend
    # For now return token directly (remove in production)
    if token:
        return MessageResponse(
            message=f"Reset token generated. Token: {token}"
        )
    # Return same message even if email not found (security)
    return MessageResponse(
        message="If that email exists, a reset link has been sent."
    )


# ── Reset password ─────────────────────────────────────────────────────────────

@router.post("/reset-password", response_model=MessageResponse)
def reset_password(body: ResetPasswordRequest):
    success = consume_reset_token(body.token, body.new_password)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )
    return MessageResponse(message="Password reset successfully. Please log in.")