import asyncio
import time
from typing import Any

from pyrogram import Client
from pyrogram.errors import FloodWait, UsernameNotOccupied, PeerIdInvalid
from pyrogram.types import Message

from .settings import settings


class RateLimiter:
    def __init__(self, min_interval: float) -> None:
        self._min_interval = max(0.0, min_interval)
        self._lock = asyncio.Lock()
        self._last_ts = 0.0

    async def wait(self) -> None:
        if self._min_interval <= 0:
            return
        async with self._lock:
            now = time.monotonic()
            delta = now - self._last_ts
            if delta < self._min_interval:
                wait_time = self._min_interval - delta
                self._last_ts = now + wait_time
                await asyncio.sleep(wait_time)
            else:
                self._last_ts = now


class MTProtoBridge:
    def __init__(self) -> None:
        # Pyrogram always requires a name; use ":memory:" when session_string is provided
        name = ":memory:" if settings.session_string else settings.session_name

        client_kwargs: dict[str, Any] = {
            "name": name,
            "api_id": settings.api_id,
            "api_hash": settings.api_hash,
        }
        if settings.session_string:
            client_kwargs["session_string"] = settings.session_string
        else:
            client_kwargs["phone_number"] = settings.phone

        self._client = Client(**client_kwargs)
        self._rate = RateLimiter(settings.request_min_interval)
        self._started = False

    async def start(self) -> None:
        if self._started:
            return
        await self._client.start()
        self._started = True

    async def stop(self) -> None:
        if not self._started:
            return
        await self._client.stop()
        self._started = False

    @staticmethod
    def _msg_to_dict(message: Message, handle: str) -> dict[str, Any]:
        text = message.text or message.caption or ""
        date = message.date.isoformat() if message.date else None
        return {
            "message_id": message.id,
            "text": text,
            "date": date,
            "from_channel": handle,
        }

    def is_connected(self) -> bool:
        return self._started and self._client.is_connected

    async def get_messages(self, handle: str, after_id: int | None, limit: int) -> list[dict[str, Any]]:
        await self._rate.wait()
        messages: list[Message] = []
        offset_id = 0  # 0 = start from latest
        async for message in self._client.get_chat_history(handle, limit=limit, offset_id=offset_id):
            if after_id is not None and after_id > 0 and message.id <= after_id:
                break
            messages.append(message)
        messages.sort(key=lambda m: m.id)
        return [self._msg_to_dict(m, handle) for m in messages]

    async def validate(self, handle: str) -> dict[str, Any]:
        await self._rate.wait()
        try:
            chat = await self._client.get_chat(handle)
        except (UsernameNotOccupied, PeerIdInvalid):
            return {"exists": False, "chat_id": None, "title": None, "members_count": None, "is_accessible": False}
        except FloodWait:
            raise  # let main.py map it to HTTP 429

        return {
            "exists": True,
            "chat_id": chat.id,
            "title": chat.title,
            "members_count": getattr(chat, "members_count", None),
            "is_accessible": True,
        }

    async def join(self, handle: str) -> dict[str, Any]:
        await self._rate.wait()
        try:
            chat = await self._client.join_chat(handle)
        except FloodWait as e:
            return {"success": False, "error": f"FloodWait: {e.value} seconds"}
        return {"success": True, "chat_id": chat.id, "title": chat.title}


bridge = MTProtoBridge()
