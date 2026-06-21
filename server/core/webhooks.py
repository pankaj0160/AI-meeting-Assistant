
# FILE: server/core/webhooks.py
# ACTION: Create this as a new file at that exact path.
#
# WHAT THIS FILE DOES:
#   When something important happens in Summly (a meeting finishes processing,
#   a task is updated, a member is invited), we POST a JSON payload to every
#   webhook URL the user has registered for that event type.
#
#   The user's server receives the POST, reads the payload, and can trigger
#   their own automation — e.g. post to Slack, update a project tracker, etc.
#
#   We sign every payload with HMAC-SHA256 so the user's server can verify
#   the POST genuinely came from Summly and wasn't forged.
# ═════════════════════════════════════════════════════════════════════════════
 
import hashlib
import hmac
import json
import logging
import datetime
import httpx    # async HTTP client — already in your requirements.txt
 
logger = logging.getLogger(__name__)
 
# How long to wait for the user's server to respond before giving up
WEBHOOK_TIMEOUT_SECONDS = 10
 
 
def _sign_payload(secret: str, body: str) -> str:
    """
    Generate an HMAC-SHA256 signature for a webhook payload.
 
    WHY SIGN WEBHOOKS?
        Without signing, anyone who knows your webhook URL could send fake events.
        The signature proves the payload came from Summly.
 
    HOW IT WORKS:
        1. We compute HMAC-SHA256(secret, body_as_bytes)
        2. We send the result as the X-Summly-Signature header
        3. The user's server recomputes the same HMAC using their stored secret
        4. If they match — the payload is genuine
 
    Args:
        secret : the webhook's secret (stored in webhook_endpoints.secret)
        body   : the raw JSON string we're about to send
 
    Returns:
        "sha256=<hex_digest>" — the format users expect (same as GitHub webhooks)
    """
    sig = hmac.new(
        key=secret.encode("utf-8"),
        msg=body.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()
    return f"sha256={sig}"
 
 
async def deliver_webhook(
    endpoint_id: int,
    url:         str,
    secret:      str,
    event_type:  str,
    payload:     dict,
) -> bool:
    """
    POST a webhook event to one URL.
    Logs the attempt (success or failure) to the webhook_events table.
 
    Args:
        endpoint_id : the webhook_endpoints.id (for logging)
        url         : the user's server URL to POST to
        secret      : the webhook secret for signing
        event_type  : e.g. "meeting.processed", "task.updated"
        payload     : the event data to send
 
    Returns:
        True if delivery succeeded (2xx response), False otherwise.
    """
    from server.core.database import log_webhook_event
 
    # Add standard metadata to every webhook payload
    full_payload = {
        "event":      event_type,
        "timestamp":  datetime.datetime.utcnow().isoformat() + "Z",
        "data":       payload,
    }
    body = json.dumps(full_payload, default=str)
    signature = _sign_payload(secret, body)
 
    headers = {
        "Content-Type":       "application/json",
        "X-Summly-Signature": signature,
        "X-Summly-Event":     event_type,
        "User-Agent":         "Summly-Webhooks/1.0",
    }
 
    status_code    = None
    success        = False
    error_message  = None
 
    try:
        async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT_SECONDS) as client:
            response = await client.post(url, content=body, headers=headers)
            status_code = response.status_code
            success     = 200 <= status_code < 300
 
            if not success:
                error_message = f"HTTP {status_code}: {response.text[:200]}"
 
    except httpx.TimeoutException:
        error_message = f"Timeout after {WEBHOOK_TIMEOUT_SECONDS}s"
    except httpx.ConnectError as e:
        error_message = f"Connection failed: {str(e)}"
    except Exception as e:
        error_message = f"Unexpected error: {str(e)}"
 
    # Always log the attempt, whether it worked or not
    log_webhook_event(
        endpoint_id=endpoint_id,
        event_type=event_type,
        payload=full_payload,
        status_code=status_code,
        success=success,
        error_message=error_message,
    )
 
    if success:
        logger.info(f"Webhook delivered: {event_type} → {url} [{status_code}]")
    else:
        logger.warning(f"Webhook failed: {event_type} → {url} | {error_message}")
 
    return success
 
 
async def fire_event(user_id: int, event_type: str, payload: dict) -> None:
    """
    Fire a webhook event to ALL of a user's registered endpoints
    that are subscribed to this event type.
 
    Call this from your endpoints after something important happens.
    It is non-blocking — if delivery fails, it logs the failure but does
    not raise an exception or affect the API response.
 
    Usage examples:
        await fire_event(user_id=5, event_type="meeting.processed",
                         payload={"meeting_id": 12, "filename": "standup.mp4"})
 
        await fire_event(user_id=5, event_type="task.updated",
                         payload={"task_id": 8, "status": "done"})
 
        await fire_event(user_id=5, event_type="member.invited",
                         payload={"workspace_id": 3, "invitee_email": "alice@co.com"})
 
    Valid event types:
        meeting.processed   → a meeting finished transcription + intelligence
        task.updated        → an action item status/owner/deadline changed
        task.deleted        → an action item was deleted
        member.invited      → someone was added to a workspace
        member.removed      → someone was removed from a workspace
        workspace.created   → a new workspace was created
        workspace.deleted   → a workspace was deleted
    """
    import asyncio
    from server.core.database import get_webhooks_for_user
 
    # Get all active webhooks for this user
    webhooks = get_webhooks_for_user(user_id)
 
    # Filter to those subscribed to this event type
    # events_subscribed is a list like ["meeting.processed", "task.updated"]
    subscribed = [
        w for w in webhooks
        if w["is_active"] and event_type in (w["events_subscribed"] or [])
    ]
 
    if not subscribed:
        return   # No webhooks configured for this event — nothing to do
 
    # Deliver to all subscribed endpoints concurrently
    # asyncio.gather runs all deliveries in parallel
    tasks = [
        deliver_webhook(
            endpoint_id=w["id"],
            url=w["url"],
            secret=w["secret"] if "secret" in w else "",
            event_type=event_type,
            payload=payload,
        )
        for w in subscribed
    ]
 
    # We need to get the secrets — they're not returned by get_webhooks_for_user
    # (we exclude them for security). Fetch them directly here.
    from server.core.database import get_connection
    import psycopg2.extras
 
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        endpoint_ids = [w["id"] for w in subscribed]
        cur.execute(
            "SELECT id, url, secret FROM webhook_endpoints WHERE id = ANY(%s)",
            (endpoint_ids,),
        )
        secrets_map = {r["id"]: r for r in cur.fetchall()}
 
    delivery_tasks = [
        deliver_webhook(
            endpoint_id=w["id"],
            url=secrets_map[w["id"]]["url"],
            secret=secrets_map[w["id"]]["secret"],
            event_type=event_type,
            payload=payload,
        )
        for w in subscribed
        if w["id"] in secrets_map
    ]
 
    # gather with return_exceptions=True means one failure doesn't cancel the others
    await asyncio.gather(*delivery_tasks, return_exceptions=True)