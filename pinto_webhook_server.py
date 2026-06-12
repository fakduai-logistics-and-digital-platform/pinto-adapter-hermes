#!/usr/bin/env python3
"""
Pinto Chat standalone webhook server for Hermes AI bot.

Standalone test server that works **without** the full Hermes gateway.
Useful for development, debugging, and quick smoke tests.

Flow:
  1. Login to Pinto → get JWT
  2. Read tunnel URL from cloudflared log (or pass --tunnel-url)
  3. Auto-update bot webhook_url in Pinto
  4. Receive webhook POSTs → call Hermes AI → reply via Pinto chat API

Run::

    python pinto_webhook_server.py [--tunnel-url https://xxx.trycloudflare.com]

Requires: ``pip install httpx aiohttp``
"""

import asyncio
import json
import logging
import os
import re
import sys
import argparse
from pathlib import Path

# ---------------------------------------------------------------------------
# Load .env
# ---------------------------------------------------------------------------
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ[k.strip()] = v.strip()

import httpx
from aiohttp import web

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            str(Path(__file__).parent / "pinto_webhook.log"), encoding="utf-8"
        ),
    ],
)
logger = logging.getLogger("pinto")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
PINTO_API_URL = os.environ.get("PINTO_API_URL", "https://api.pinto-app.com")
PINTO_EMAIL = os.environ.get("PINTO_EMAIL", "")
PINTO_PASSWORD = os.environ.get("PINTO_PASSWORD", "")
PINTO_BOT_ID = os.environ.get("PINTO_BOT_ID", "hermes_ai")
HERMES_API_URL = os.environ.get("HERMES_API_URL", "http://127.0.0.1:18789")
API_SERVER_KEY = os.environ.get("API_SERVER_KEY", "")
WEBHOOK_PATH = "/plugins/pinto/webhook"
PORT = int(os.environ.get("PINTO_WEBHOOK_PORT", "18789"))
CF_LOG = str(Path(__file__).parent / "cloudflared.log")

_token: str = ""
_http: httpx.AsyncClient = None


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
async def get_token(force: bool = False) -> str:
    """Authenticate with Pinto and return a JWT."""
    global _token
    if _token and not force:
        return _token
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.post(
            f"{PINTO_API_URL}/api/auth/login",
            json={"email": PINTO_EMAIL, "password": PINTO_PASSWORD},
            headers={"User-Agent": "Pinto-App-iOS/1.0.0"},
        )
        data = r.json()
        if not data.get("ok"):
            raise RuntimeError(f"Login failed: {data}")
        _token = data["data"]["token"]
        logger.info(
            "Logged in as @%s (prod=%s)",
            data["data"]["user"]["username"],
            "pinto-app.com" in PINTO_API_URL,
        )
    return _token


# ---------------------------------------------------------------------------
# Tunnel URL helpers
# ---------------------------------------------------------------------------
def read_tunnel_url_from_cf_log(log_path: str) -> str | None:
    """Extract latest trycloudflare URL from cloudflared log file."""
    try:
        text = Path(log_path).read_text(encoding="utf-8")
        urls = re.findall(r"https://[a-z0-9\-]+\.trycloudflare\.com", text)
        return urls[-1] if urls else None
    except Exception:
        return None


async def register_webhook_url(tunnel_url: str):
    """Update bot webhook_url in Pinto and run a test webhook."""
    token = await get_token()
    webhook_url = f"{tunnel_url}{WEBHOOK_PATH}"
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.put(
            f"{PINTO_API_URL}/v1/bots/{PINTO_BOT_ID}",
            headers={"Authorization": f"Bearer {token}"},
            json={"webhook_url": webhook_url},
        )
        data = r.json()
        if data.get("ok"):
            logger.info("✅ Webhook URL updated: %s", webhook_url)
        else:
            logger.warning("⚠️  Failed to update webhook URL: %s", data)

    # Test webhook
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.post(
            f"{PINTO_API_URL}/v1/bots/test-webhook",
            headers={"Authorization": f"Bearer {token}"},
            json={"webhook_url": webhook_url},
        )
        result = r.json()
        logger.info(
            "Webhook test: ok=%s latency=%sms",
            result.get("data", {}).get("ok"),
            result.get("data", {}).get("latency_ms"),
        )


# ---------------------------------------------------------------------------
# Pinto chat API
# ---------------------------------------------------------------------------
async def send_pinto_message(chat_id: str, content: str):
    """Send bot reply via Pinto webhook receive endpoint."""
    webhook_secret = os.environ.get("PINTO_WEBHOOK_SECRET", "")
    payload = {
        "bot_id": PINTO_BOT_ID,
        "chat_id": chat_id,
        "reply_message": content[:1000],
    }
    headers = {"Content-Type": "application/json"}
    if webhook_secret:
        headers["X-Pinto-Secret"] = webhook_secret

    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(
            f"{PINTO_API_URL}/v1/bots/webhook/receive",
            headers=headers,
            json=payload,
        )
        data = r.json()
        if not data.get("ok"):
            logger.warning("Send message failed: %s (status=%d)", data, r.status_code)
        else:
            logger.info("✅ Reply sent to chat %s", chat_id)
        return data


# ---------------------------------------------------------------------------
# Hermes AI
# ---------------------------------------------------------------------------
async def ask_hermes(user_message: str, sender_name: str, chat_id: str) -> str:
    """Forward message to Hermes AI and return the response."""
    if not API_SERVER_KEY:
        return f"[Echo] {user_message}"
    try:
        async with httpx.AsyncClient(timeout=120) as c:
            r = await c.post(
                f"{HERMES_API_URL}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {API_SERVER_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "hermes",
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are Hermes AI, a helpful assistant on Pinto Chat. "
                                "Reply concisely in the same language as the user. "
                                "Keep responses short and friendly."
                            ),
                        },
                        {"role": "user", "content": f"{sender_name}: {user_message}"},
                    ],
                    "stream": False,
                },
            )
            data = r.json()
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error("Hermes error: %s", e)
        return "ขอโทษนะ เกิดข้อผิดพลาด 😅"


# ---------------------------------------------------------------------------
# HTTP handlers
# ---------------------------------------------------------------------------
async def handle_ping(request: web.Request) -> web.Response:
    return web.json_response({"ok": True, "channel": "pinto"})


async def handle_webhook(request: web.Request) -> web.Response:
    """Handle inbound webhook from Pinto.

    Supports **both** flat (production) and nested (Swagger) payloads.
    """
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "invalid json"}, status=400)

    logger.info("📨 Webhook: %s", json.dumps(body, ensure_ascii=False)[:400])

    # Verify webhook secret if configured
    webhook_secret = os.environ.get("PINTO_WEBHOOK_SECRET", "")
    if webhook_secret:
        inbound = request.headers.get("X-Pinto-Secret", "")
        if inbound != webhook_secret:
            return web.json_response({"ok": False, "error": "invalid secret"}, status=401)

    # -- parse payload (flat or nested) ------------------------------------
    raw_msg = body.get("message", {})

    if isinstance(raw_msg, str):
        # Flat production format: message is a plain string
        chat_id = body.get("chat_id", "")
        content = raw_msg
        sender = {
            "user_id": body.get("user_id", ""),
            "username": body.get("username", ""),
            "name": body.get("username", ""),
            "is_bot": False,
        }
    elif isinstance(raw_msg, dict):
        # Nested Swagger format
        chat_id = raw_msg.get("chat_id") or body.get("chat_id", "")
        content = raw_msg.get("content", "")
        sender = raw_msg.get("sender", {})
    else:
        chat_id = body.get("chat_id", "")
        content = str(raw_msg)
        sender = {}

    # Ignore bot's own replies
    bot_owner_user_id = os.environ.get("PINTO_BOT_OWNER_USER_ID", "")
    sender_user_id = sender.get("user_id", "") or body.get("user_id", "")
    if bot_owner_user_id and sender_user_id == bot_owner_user_id:
        return web.json_response({"ok": True})

    is_bot = sender.get("is_bot", False)
    if is_bot:
        return web.json_response({"ok": True})

    if not chat_id or not content.strip():
        return web.json_response({"ok": True})

    sender_name = sender.get("name") or sender.get("username") or "User"
    logger.info("💬 @%s in %s: %s", sender.get("username", "?"), chat_id, content)

    # Reply async (Pinto expects < 300s)
    asyncio.create_task(reply_async(chat_id, content, sender_name))
    return web.json_response({"ok": True})


async def reply_async(chat_id: str, user_msg: str, sender_name: str):
    reply = await ask_hermes(user_msg, sender_name, chat_id)
    logger.info("🤖 Reply: %s", reply[:100])
    await send_pinto_message(chat_id, reply)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main(tunnel_url: str | None = None):
    global _token

    # Login (only if credentials provided)
    if PINTO_EMAIL and PINTO_PASSWORD:
        await get_token()
    else:
        logger.info("No PINTO_EMAIL/PINTO_PASSWORD set — skipping login")

    # Find tunnel URL
    if not tunnel_url:
        tunnel_url = read_tunnel_url_from_cf_log(CF_LOG)
    if not tunnel_url:
        logger.warning(
            "No tunnel URL found — webhook NOT registered. "
            "Start cloudflared then restart, or pass --tunnel-url."
        )
    else:
        if PINTO_EMAIL and PINTO_PASSWORD:
            await register_webhook_url(tunnel_url)
        else:
            logger.info("Tunnel URL: %s%s (not registered — no login)", tunnel_url, WEBHOOK_PATH)

    # Start HTTP server
    app = web.Application()
    app.router.add_get(WEBHOOK_PATH, handle_ping)
    app.router.add_post(WEBHOOK_PATH, handle_webhook)
    app.router.add_get("/health", handle_ping)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    logger.info("🚀 Pinto webhook server → port %d", PORT)
    if tunnel_url:
        logger.info("🌐 Public URL: %s%s", tunnel_url, WEBHOOK_PATH)

    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pinto standalone webhook server")
    parser.add_argument("--tunnel-url", default=None, help="Override tunnel URL")
    args = parser.parse_args()
    asyncio.run(main(tunnel_url=args.tunnel_url))
