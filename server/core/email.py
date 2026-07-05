# server/core/email.py
"""
Transactional email service — Resend integration.

WHY RESEND, AND WHY A RAW HTTP CALL INSTEAD OF THE `resend` SDK:
    Resend's API is a single HTTPS POST. httpx is already a project
    dependency (see core/webhooks.py), so this needs zero new packages.

GRACEFUL DEGRADATION (same pattern as core/logging_config.py and the
slowapi import guard in main.py):
    If RESEND_API_KEY is not set, sending is skipped and a WARNING is
    logged instead of raising. This means:
      - Local dev works with zero email config — auth flows still
        return correct responses, they just don't send real mail.
      - A Resend outage or misconfigured key degrades to "no email sent"
        instead of a 500 that breaks registration/login/reset flows.

SECURITY NOTE:
    Never log a full email address (same rule already established in
    core/auth/router.py). All logging here goes through _mask_email().

USAGE:
    from server.core.email import send_reset_email
    background_tasks.add_task(send_reset_email, user.email, token)

    Always call these through FastAPI's BackgroundTasks (see
    core/auth/router.py) — never inline in the request path. A slow or
    down email provider must never add latency to login/register/reset
    responses.
"""

import os
import logging

import httpx

logger = logging.getLogger(__name__)

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()
EMAIL_FROM     = os.getenv("EMAIL_FROM", "Summly <onboarding@resend.dev>")
FRONTEND_URL   = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")

RESEND_API_URL = "https://api.resend.com/emails"

# Short timeouts: this runs in a background task, but a hung connection
# should still not accumulate forever under load.
_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


def _mask_email(email: str) -> str:
    """e.g. 'pankaj@gmail.com' -> 'pa***@gmail.com' — safe to log."""
    if not email or "@" not in email:
        return "***"
    name, domain = email.split("@", 1)
    visible = name[:2] if len(name) > 2 else name[:1]
    return f"{visible}***@{domain}"


def _send(to: str, subject: str, html: str) -> bool:
    """
    Low-level send. Returns True/False, NEVER raises.

    Why never raise: this is called from background tasks and, in a few
    call sites, could be called inline. A failed email must never turn
    into a 500 for the user — e.g. forgot-password must always return
    200 regardless of whether the email actually went out, otherwise the
    response itself would leak whether the address exists (the same
    enumeration issue already fixed in the endpoint).
    """
    if not RESEND_API_KEY:
        logger.warning(
            "RESEND_API_KEY not set — skipping email to %s (subject=%r). "
            "Set RESEND_API_KEY in .env to enable real delivery.",
            _mask_email(to), subject,
        )
        return False

    try:
        response = httpx.post(
            RESEND_API_URL,
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type":  "application/json",
            },
            json={
                "from":    EMAIL_FROM,
                "to":      [to],
                "subject": subject,
                "html":    html,
            },
            timeout=_TIMEOUT,
        )
        if response.status_code >= 400:
            logger.error(
                "Resend API error (status=%s) sending to %s: %s",
                response.status_code, _mask_email(to), response.text[:300],
            )
            return False
        logger.info("Email sent to %s (subject=%r)", _mask_email(to), subject)
        return True

    except httpx.HTTPError as e:
        # Network failure, timeout, DNS issue, Resend outage, etc.
        logger.error("Email send failed (network error) to %s: %s", _mask_email(to), e)
        return False


# ── Templates ──────────────────────────────────────────────────────────────
# Kept as plain f-string HTML rather than a template engine — three emails
# doesn't justify a templating dependency. Revisit if this list grows past
# ~6-8 templates.

def _wrapper(inner_html: str) -> str:
    return f"""
    <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
                max-width:480px;margin:0 auto;color:#111827;">
      {inner_html}
      <p style="color:#9ca3af;font-size:12px;margin-top:32px;">
        Summly — AI meeting intelligence
      </p>
    </div>
    """


def send_reset_email(to: str, token: str) -> bool:
    """Password reset link. Token expires per the TTL set in auth/service.py."""
    reset_link = f"{FRONTEND_URL}/reset-password?token={token}"
    html = _wrapper(f"""
      <h2 style="color:#059669;">Reset your Summly password</h2>
      <p>We received a request to reset your password. This link expires in 30 minutes.</p>
      <p style="text-align:center;margin:32px 0;">
        <a href="{reset_link}"
           style="background:#059669;color:#fff;padding:12px 24px;border-radius:8px;
                  text-decoration:none;font-weight:600;display:inline-block;">
          Reset Password
        </a>
      </p>
      <p style="color:#6b7280;font-size:13px;">
        If you didn't request this, you can safely ignore this email —
        your password will not be changed.
      </p>
      <p style="color:#9ca3af;font-size:12px;word-break:break-all;">
        Or paste this link into your browser: {reset_link}
      </p>
    """)
    return _send(to, "Reset your Summly password", html)


def send_welcome_email(to: str, full_name: str) -> bool:
    """Sent once, right after successful registration."""
    first_name = (full_name or "there").split(" ")[0]
    html = _wrapper(f"""
      <h2 style="color:#059669;">Welcome to Summly, {first_name}!</h2>
      <p>Your account is ready. Upload a recording and Summly will pull out
         the summary, decisions, and action items automatically.</p>
      <p style="text-align:center;margin:32px 0;">
        <a href="{FRONTEND_URL}/app/upload"
           style="background:#059669;color:#fff;padding:12px 24px;border-radius:8px;
                  text-decoration:none;font-weight:600;display:inline-block;">
          Upload your first meeting
        </a>
      </p>
    """)
    return _send(to, "Welcome to Summly", html)


def send_meeting_ready_email(to: str, meeting_title: str, meeting_id: str) -> bool:
    """Sent when async processing finishes (hook this up from the Celery task)."""
    link = f"{FRONTEND_URL}/app/meetings/{meeting_id}"
    html = _wrapper(f"""
      <h2 style="color:#059669;">Your meeting is ready</h2>
      <p><strong>{meeting_title}</strong> has finished processing — summary,
         decisions, and action items are ready to view.</p>
      <p style="text-align:center;margin:32px 0;">
        <a href="{link}"
           style="background:#059669;color:#fff;padding:12px 24px;border-radius:8px;
                  text-decoration:none;font-weight:600;display:inline-block;">
          View summary
        </a>
      </p>
    """)
    return _send(to, f"Ready: {meeting_title}", html)