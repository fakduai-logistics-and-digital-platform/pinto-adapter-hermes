"""Pinto Chat platform adapter (Hermes plugin).

Allows Hermes Agent to act as a chat bot gateway on Pinto.

Configuration via environment variables or config.yaml::

    platforms:
      pinto:
        enabled: true
        extra:
          apiUrl: "https://api.pinto-app.com"
          botId: "your-bot-uuid"
          webhookSecret: "your-optional-secret"
          webhookPath: "/plugins/pinto/webhook"

Environment variables::

    PINTO_BOT_ID           – Required. Your Pinto Bot UUID or slug (e.g. "hermes_ai")
    PINTO_API_URL          – API base URL (default: https://api.pinto-app.com)
    PINTO_WEBHOOK_SECRET   – Optional secret for X-Pinto-Secret header verification
    PINTO_WEBHOOK_PATH     – Local webhook route (default: /plugins/pinto/webhook)
    PINTO_WEBHOOK_URL      – Public webhook URL; used to derive media URLs
    PINTO_PUBLIC_BASE_URL  – Optional public gateway base URL for media
    PINTO_MEDIA_PATH       – Public local-media route (default: /plugins/pinto/media)
    PINTO_MEDIA_UPLOAD_PROVIDER – Optional free public upload provider(s): catbox,litterbox,0x0,uguu,tmpfiles
    PINTO_BEARER_TOKEN     – Optional user/service JWT for native chat API testing only
    PINTO_HOME_CHANNEL     – Default chat_id for cron / notification delivery
    PINTO_ALLOWED_USERS    – Comma-separated allowlist of Pinto user IDs
    PINTO_ALLOW_ALL_USERS  – Set "true" to let any user chat with the bot
"""

import asyncio
import json
import logging
import os
import re
import time
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any, List, Optional
from urllib.parse import urlparse

try:
    from aiohttp import web
except Exception:
    web = None

if TYPE_CHECKING:
    import httpx as _httpx

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    httpx = None

from gateway.config import Platform, PlatformConfig
from gateway.platforms.base import (
    BasePlatformAdapter,
    MessageEvent,
    SendResult,
)
from gateway.session import SessionSource

logger = logging.getLogger(__name__)

DEFAULT_PINTO_API_URL = "https://api.pinto-app.com"
DEFAULT_WEBHOOK_PATH = "/plugins/pinto/webhook"
PINTO_SECRET_HEADER = "x-pinto-secret"


# ---------------------------------------------------------------------------
# Module-level helpers (used by plugin loader)
# ---------------------------------------------------------------------------

def _env_enablement() -> Optional[dict]:
    """Auto-enable platform when PINTO_BOT_ID is present in environment."""
    bot_id = os.getenv("PINTO_BOT_ID")
    if not bot_id:
        return None
    return {
        "botId": bot_id,
        "apiUrl": os.getenv("PINTO_API_URL", DEFAULT_PINTO_API_URL),
        "webhookSecret": os.getenv("PINTO_WEBHOOK_SECRET", ""),
        "webhookPath": os.getenv("PINTO_WEBHOOK_PATH", DEFAULT_WEBHOOK_PATH),
    }


def check_requirements() -> bool:
    """Return True when httpx is importable."""
    return HTTPX_AVAILABLE


def validate_config(config: PlatformConfig) -> bool:
    extra = getattr(config, "extra", {}) or {}
    bot_id = extra.get("botId") or os.getenv("PINTO_BOT_ID")
    return bool(bot_id)


def is_connected(config: PlatformConfig) -> bool:
    return validate_config(config) and config.enabled


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------

class PintoAdapter(BasePlatformAdapter):
    """Pinto Chat platform adapter for Hermes.

    Handles **both** webhook payload formats:

    * **Flat** (production)::

        {"user_id":"...","username":"...","message":"text","chat_id":"...","bot_id":"..."}

    * **Nested** (Swagger spec)::

        {"bot_id":"...","chat_id":"...","message":{"chat_id":"...","content":"...","sender":{}}}
    """

    def __init__(self, config: PlatformConfig):
        super().__init__(config, Platform.TELEGRAM)
        extra = getattr(config, "extra", {}) or {}
        self._bot_id = extra.get("botId") or os.getenv("PINTO_BOT_ID")
        self._api_url = (
            extra.get("apiUrl") or os.getenv("PINTO_API_URL", DEFAULT_PINTO_API_URL)
        ).rstrip("/")
        self._webhook_secret = (
            extra.get("webhookSecret") or os.getenv("PINTO_WEBHOOK_SECRET", "")
        )
        self._webhook_path = extra.get("webhookPath") or os.getenv(
            "PINTO_WEBHOOK_PATH", DEFAULT_WEBHOOK_PATH
        )
        self._media_path = extra.get("mediaPath") or os.getenv(
            "PINTO_MEDIA_PATH", "/plugins/pinto/media"
        )
        self._media_files: dict[str, str] = {}
        self._bearer_token = extra.get("bearerToken") or os.getenv("PINTO_BEARER_TOKEN", "")
        self._media_upload_provider = os.getenv("PINTO_MEDIA_UPLOAD_PROVIDER", "").lower().strip()
        self._send_media_url_field = os.getenv("PINTO_SEND_MEDIA_URL_FIELD", "false").lower() == "true"
        self._litterbox_expiry = os.getenv("PINTO_LITTERBOX_EXPIRY", "24h")
        self._typing_last_sent: dict[str, float] = {}
        self._typing_status_message = os.getenv("PINTO_TYPING_STATUS_MESSAGE", "")
        self._typing_status_interval = float(os.getenv("PINTO_TYPING_STATUS_INTERVAL", "20"))
        self._client: Optional["_httpx.AsyncClient"] = None

    # -- lifecycle -----------------------------------------------------------

    async def connect(self) -> bool:
        if not self._bot_id:
            logger.error("PINTO_BOT_ID not configured")
            return False

        self._client = httpx.AsyncClient(timeout=30.0)
        self._running = True

        # Register webhook route on the api_server aiohttp app
        try:
            from gateway.platform_registry import platform_registry

            api_entry = platform_registry.get("api_server")
            api_app = None
            api_port = "?"

            if api_entry is not None:
                live = getattr(api_entry, "_live_adapter", None) or getattr(
                    api_entry, "adapter", None
                )
                if live is not None:
                    api_app = getattr(live, "_app", None)
                    api_port = getattr(live, "_port", "?")

            if api_app is not None:
                api_app.router.add_post(self._webhook_path, self._handle_webhook)
                api_app.router.add_get(self._webhook_path, self._handle_webhook_ping)
                api_app.router.add_get(self._media_path + "/{token}", self._handle_media)
                logger.info(
                    "Pinto webhook registered at %s (api_server port %s)",
                    self._webhook_path,
                    api_port,
                )
            else:
                logger.warning(
                    "api_server aiohttp app not found — Pinto webhook not mounted. "
                    "Enable platforms.api_server in config.yaml and ensure it starts before pinto."
                )
        except Exception as e:
            logger.error("Failed to register Pinto webhook route: %s", e)

        logger.info("Pinto Chat adapter connected (bot_id=%s)", self._bot_id)
        return True

    async def disconnect(self) -> None:
        self._running = False
        if self._client:
            await self._client.aclose()
            self._client = None
        logger.info("Pinto Chat adapter disconnected")

    # -- webhook handlers ----------------------------------------------------

    async def _handle_webhook_ping(self, request):
        """GET health check."""
        from aiohttp import web as _web

        return _web.json_response({"ok": True, "channel": "pinto"})

    async def _handle_webhook(self, request):
        """Handle inbound POST from Pinto server.

        Supports **flat** production payload where ``message`` is a string
        and **nested** Swagger-style payload where ``message`` is an object
        with ``content`` and ``sender`` keys.
        """
        try:
            # -- verify secret ------------------------------------------------
            if self._webhook_secret:
                inbound_secret = request.headers.get(PINTO_SECRET_HEADER, "")
                if inbound_secret != self._webhook_secret:
                    return request.app["response_class"](
                        status=401,
                        text=json.dumps({"error": "Invalid webhook secret"}),
                        content_type="application/json",
                    )

            body = await request.json()
            logger.debug("Pinto webhook body: %s", json.dumps(body, ensure_ascii=False)[:500])

            # -- parse payload (flat or nested) --------------------------------
            bot_id = body.get("bot_id")
            raw_msg = body.get("message")

            if isinstance(raw_msg, str):
                # Flat production format: message is a plain string
                chat_id = body.get("chat_id")
                user_id = body.get("user_id") or chat_id
                message_text = raw_msg
                username = body.get("username") or str(user_id)
            elif isinstance(raw_msg, dict):
                # Nested Swagger format
                chat_id = raw_msg.get("chat_id") or body.get("chat_id")
                user_id = (raw_msg.get("sender") or {}).get("user_id") or body.get("user_id") or chat_id
                message_text = raw_msg.get("content", "")
                username = (raw_msg.get("sender") or {}).get("username") or body.get("username") or str(user_id)
            else:
                chat_id = body.get("chat_id")
                user_id = body.get("user_id") or chat_id
                message_text = str(raw_msg) if raw_msg else ""
                username = body.get("username") or str(user_id)

            if not bot_id or not chat_id or not message_text:
                return request.app["response_class"](
                    status=400,
                    text=json.dumps({"error": "Missing required fields: bot_id, chat_id, message"}),
                    content_type="application/json",
                )

            if bot_id != self._bot_id:
                return request.app["response_class"](
                    status=403,
                    text=json.dumps({"error": "bot_id mismatch"}),
                    content_type="application/json",
                )

            source = SessionSource(
                platform=self.platform,
                chat_id=str(chat_id),
                user_id=str(user_id),
                user_name=username,
                chat_type="dm",
            )
            event = MessageEvent(
                text=message_text,
                source=source,
                message_id=str(uuid.uuid4()),
                raw_message=body,
            )

            task = asyncio.create_task(self.handle_message(event))
            task.add_done_callback(
                lambda t: logger.error("Pinto background task error: %s", t.exception())
                if t.exception()
                else None
            )

            return request.app["response_class"](
                status=200,
                text=json.dumps({"ok": True, "queued": True}),
                content_type="application/json",
            )

        except Exception as e:
            logger.error("Pinto webhook error: %s", e)
            return request.app["response_class"](
                status=500,
                text=json.dumps({"error": str(e)}),
                content_type="application/json",
            )

    # -- local media ---------------------------------------------------------

    def _public_base_url(self) -> str:
        explicit = os.getenv("PINTO_PUBLIC_BASE_URL", "").rstrip("/")
        if explicit:
            return explicit

        webhook_url = os.getenv("PINTO_WEBHOOK_URL", "")
        env_path = Path(os.getenv("HERMES_HOME", "~/.hermes")).expanduser() / ".env"
        if env_path.exists():
            try:
                for line in env_path.read_text().splitlines():
                    if line.startswith("PINTO_PUBLIC_BASE_URL="):
                        explicit = line.split("=", 1)[1].strip().rstrip("/")
                        if explicit:
                            return explicit
                    elif line.startswith("PINTO_WEBHOOK_URL="):
                        webhook_url = line.split("=", 1)[1].strip()
            except Exception:
                pass

        if webhook_url:
            parsed = urlparse(webhook_url)
            if parsed.scheme and parsed.netloc:
                return f"{parsed.scheme}://{parsed.netloc}"
        return ""

    def _media_url_for_file(self, file_path: str) -> str:
        if file_path.startswith(("http://", "https://")):
            return file_path

        path = Path(file_path)
        if not path.exists() or not path.is_file():
            return file_path

        token = f"{int(time.time())}_{uuid.uuid4().hex}_{path.name}"
        self._media_files[token] = str(path)

        base = self._public_base_url()
        if not base:
            return file_path
        return f"{base}{self._media_path}/{token}"

    async def _handle_media(self, request):
        if web is None:
            return request.app["response_class"](
                status=500,
                text="aiohttp is not available",
                content_type="text/plain",
            )

        token = request.match_info.get("token", "")
        file_path = self._media_files.get(token)
        if not file_path or not Path(file_path).exists():
            return web.Response(status=404, text="Not found")
        return web.FileResponse(file_path)

    # -- send ----------------------------------------------------------------

    def _extract_media_file(self, text: str, media_files: Any = None) -> Optional[str]:
        if media_files:
            return str(media_files[0])
        if text:
            match = re.search(r"(/[^\s]+\.(?:png|jpg|jpeg|gif|webp))", text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    async def _send_native_chat_message(self, chat_id: str, text: str, media_file: Optional[str]) -> SendResult:
        """Send via Pinto native chat API when PINTO_BEARER_TOKEN is configured."""
        url = f"{self._api_url}/v1/chats/{chat_id}/messages"
        headers = {"Authorization": f"Bearer {self._bearer_token}"}
        data = {
            "content": text or " ",
            "message_type": "image" if media_file else "text",
        }
        files = None
        file_handle = None
        try:
            if media_file:
                path = Path(media_file)
                if path.exists() and path.is_file():
                    file_handle = path.open("rb")
                    files = {"media": (path.name, file_handle, "image/png")}
                elif media_file.startswith(("http://", "https://")):
                    # Native API accepts binary upload only. Fall back to webhook media_url.
                    return await self._send_webhook_receive(chat_id, text, media_file)

            resp = await self._client.post(url, data=data, files=files, headers=headers)
            if resp.status_code >= 300:
                return SendResult(success=False, error=f"Pinto native HTTP {resp.status_code}: {resp.text}")
            message_id = str(time.time())
            try:
                body = resp.json()
                message_id = str(body.get("message_id") or (body.get("data") or {}).get("message_id") or message_id)
            except Exception:
                pass
            return SendResult(success=True, message_id=message_id)
        except Exception as e:
            return SendResult(success=False, error=str(e))
        finally:
            if file_handle:
                file_handle.close()

    def _text_with_public_media_url(self, text: str, media_file: Optional[str], media_url: str) -> str:
        if not media_file or not media_url or media_url == media_file:
            return text
        if media_file in text:
            return text.replace(media_file, media_url)
        if media_url not in text:
            return f"{text}\n{media_url}" if text else media_url
        return text

    def _upload_providers(self) -> list[str]:
        raw = self._media_upload_provider
        if not raw:
            return []
        if raw in {"free", "auto", "all"}:
            return ["catbox", "litterbox", "0x0", "uguu", "tmpfiles"]
        return [p.strip() for p in raw.replace(";", ",").split(",") if p.strip()]

    async def _upload_to_provider(self, provider: str, path: Path) -> Optional[str]:
        file_field = "fileToUpload"
        data = None
        url = ""
        if provider == "catbox":
            url = "https://catbox.moe/user/api.php"
            data = {"reqtype": "fileupload"}
        elif provider == "litterbox":
            url = "https://litterbox.catbox.moe/resources/internals/api.php"
            data = {"reqtype": "fileupload", "time": self._litterbox_expiry}
        elif provider in {"0x0", "0x0.st"}:
            url = "https://0x0.st"
            file_field = "file"
        elif provider == "uguu":
            url = "https://uguu.se/upload.php"
            file_field = "files[]"
        elif provider == "tmpfiles":
            url = "https://tmpfiles.org/api/v1/upload"
            file_field = "file"
        else:
            logger.warning("Unknown Pinto media upload provider=%s", provider)
            return None

        file_handle = None
        try:
            file_handle = path.open("rb")
            files = {file_field: (path.name, file_handle, "image/png")}
            resp = await self._client.post(url, data=data, files=files, timeout=120.0)
            if resp.status_code >= 300:
                logger.warning("Pinto media upload %s failed HTTP %s: %s", provider, resp.status_code, resp.text[:300])
                return None

            text = resp.text.strip()
            public_url = ""
            if text.startswith(("http://", "https://")):
                public_url = text
            else:
                try:
                    body = resp.json()
                    if provider == "uguu":
                        files_body = body.get("files") or []
                        if files_body:
                            public_url = files_body[0].get("url") or ""
                    elif provider == "tmpfiles":
                        public_url = ((body.get("data") or {}).get("url") or "").replace("tmpfiles.org/", "tmpfiles.org/dl/")
                except Exception:
                    pass

            if public_url.startswith(("http://", "https://")):
                logger.info("Pinto media uploaded via %s: %s", provider, public_url)
                return public_url
            logger.warning("Pinto media upload %s returned non-url response: %s", provider, text[:300])
            return None
        except Exception as e:
            logger.warning("Pinto media upload %s failed: %s", provider, e)
            return None
        finally:
            if file_handle:
                file_handle.close()

    async def _upload_public_media(self, file_path: str) -> Optional[str]:
        """Upload local media to configured free public hosts, with fallback."""
        providers = self._upload_providers()
        if not providers:
            return None
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            return None
        for provider in providers:
            uploaded = await self._upload_to_provider(provider, path)
            if uploaded:
                return uploaded
        return None

    async def _public_url_for_media(self, media_file: str) -> str:
        if media_file.startswith(("http://", "https://")):
            return media_file
        uploaded = await self._upload_public_media(media_file)
        if uploaded:
            return uploaded
        return self._media_url_for_file(media_file)

    async def _send_webhook_receive(self, chat_id: str, text: str, media_file: Optional[str]) -> SendResult:
        url = f"{self._api_url}/v1/bots/webhook/receive"
        headers = {"Content-Type": "application/json"}
        if self._webhook_secret:
            headers[PINTO_SECRET_HEADER] = self._webhook_secret

        payload = {
            "bot_id": self._bot_id,
            "chat_id": chat_id,
            "reply_message": text,
        }
        if media_file:
            media_url = await self._public_url_for_media(media_file)
            if media_url != media_file:
                if self._send_media_url_field:
                    payload["media_url"] = media_url
                payload["reply_message"] = self._text_with_public_media_url(text, media_file, media_url)

        logger.info(
            "Pinto webhook send chat_id=%s has_media=%s payload_keys=%s",
            chat_id,
            bool(payload.get("media_url")),
            sorted(payload.keys()),
        )
        resp = await self._client.post(url, json=payload, headers=headers)
        if resp.status_code >= 300:
            return SendResult(success=False, error=f"Pinto HTTP {resp.status_code}: {resp.text}")
        return SendResult(success=True, message_id=str(time.time()))

    async def send(self, chat_id: str, text: str = "", content: str = "", **kwargs: Any) -> SendResult:
        """Post reply back to Pinto.

        Uses native chat API with multipart media upload when PINTO_BEARER_TOKEN
        is set. Otherwise falls back to the bot webhook receive endpoint.
        """
        if content and not text:
            text = content
        if not self._client:
            return SendResult(success=False, error="Adapter not connected")

        media_file = self._extract_media_file(text, kwargs.get("media_files"))
        try:
            if self._bearer_token:
                return await self._send_native_chat_message(chat_id, text, media_file)
            return await self._send_webhook_receive(chat_id, text, media_file)
        except Exception as e:
            return SendResult(success=False, error=str(e))

    async def send_typing(self, chat_id: str, metadata=None) -> None:
        """Send a throttled status message while Hermes is processing.

        Pinto does not currently expose a native typing indicator endpoint to
        this adapter. If PINTO_TYPING_STATUS_MESSAGE is set, use a lightweight
        chat message as a fallback and throttle it per chat.
        """
        if self._bearer_token and self._client:
            try:
                await self._client.post(
                    f"{self._api_url}/v1/chats/typing",
                    json={"chat_id": chat_id, "is_typing": True},
                    headers={"Authorization": f"Bearer {self._bearer_token}"},
                )
                return
            except Exception as e:
                logger.debug("Pinto native typing failed: %s", e)

        if not self._typing_status_message:
            return
        now = time.time()
        last = self._typing_last_sent.get(chat_id, 0)
        if now - last < self._typing_status_interval:
            return
        self._typing_last_sent[chat_id] = now
        await self.send(chat_id, self._typing_status_message)

    async def send_image(self, chat_id: str, image_url: str, caption: str) -> SendResult:
        return await self.send(chat_id, caption, media_files=[image_url])

    async def get_chat_info(self, chat_id: str) -> dict:
        return {"name": f"Pinto Chat {chat_id}", "type": "dm", "chat_id": chat_id}


# ---------------------------------------------------------------------------
# Standalone sender (for cron / background delivery outside gateway process)
# ---------------------------------------------------------------------------

async def _standalone_send(
    pconfig: PlatformConfig,
    chat_id: str,
    message: str,
    *,
    thread_id: Optional[str] = None,
    media_files: Optional[List[str]] = None,
    force_document: bool = False,
) -> dict:
    """Out-of-process delivery for cron/background tasks."""
    if not HTTPX_AVAILABLE:
        return {"error": "httpx not installed"}

    extra = getattr(pconfig, "extra", {}) or {}
    bot_id = extra.get("botId") or os.getenv("PINTO_BOT_ID")
    api_url = (
        extra.get("apiUrl") or os.getenv("PINTO_API_URL", DEFAULT_PINTO_API_URL)
    ).rstrip("/")
    webhook_secret = extra.get("webhookSecret") or os.getenv("PINTO_WEBHOOK_SECRET", "")

    if not bot_id:
        return {"error": "Pinto botId not configured"}

    url = f"{api_url}/v1/bots/webhook/receive"
    headers = {"Content-Type": "application/json"}
    if webhook_secret:
        headers[PINTO_SECRET_HEADER] = webhook_secret

    payload: dict = {
        "bot_id": bot_id,
        "chat_id": chat_id,
        "reply_message": message,
    }
    if media_files:
        payload["media_url"] = media_files[0]

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code >= 300:
            return {"error": f"Pinto HTTP {resp.status_code}: {resp.text}"}
        return {"success": True, "message_id": str(time.time())}
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Plugin registration
# ---------------------------------------------------------------------------

def register(ctx) -> None:
    """Called by Hermes plugin loader to register the Pinto platform."""
    ctx.register_platform(
        name="pinto",
        label="Pinto",
        adapter_factory=lambda cfg: PintoAdapter(cfg),
        check_fn=check_requirements,
        validate_config=validate_config,
        is_connected=is_connected,
        required_env=["PINTO_BOT_ID"],
        install_hint="pip install httpx",
        env_enablement_fn=_env_enablement,
        cron_deliver_env_var="PINTO_HOME_CHANNEL",
        standalone_sender_fn=_standalone_send,
        allowed_users_env="PINTO_ALLOWED_USERS",
        allow_all_env="PINTO_ALLOW_ALL_USERS",
        emoji="🫓",
        pii_safe=True,
        allow_update_command=False,
        platform_hint="You are chatting via Pinto Thailand Chat API.",
    )
