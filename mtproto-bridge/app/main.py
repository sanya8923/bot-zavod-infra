import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from pyrogram.errors import ChannelPrivate, FloodWait, PeerIdInvalid, UsernameNotOccupied

from .mtproto import bridge

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await bridge.start()
    except Exception as exc:
        logger.error("MTProto bridge failed to start: %s", exc)
        raise
    yield
    await bridge.stop()


app = FastAPI(title="MTProto Bridge", version="0.1.0", lifespan=lifespan)


class JoinRequest(BaseModel):
    handle: str


def _normalize_handle(raw: str) -> str:
    handle = raw.strip()
    for prefix in ("https://t.me/", "http://t.me/", "t.me/"):
        if handle.startswith(prefix):
            handle = handle[len(prefix):]
            break
    if not handle.startswith("@"):
        handle = "@" + handle
    return handle


def _pyrogram_exc_to_http(exc: Exception) -> HTTPException:
    if isinstance(exc, FloodWait):
        return HTTPException(status_code=429, detail=f"Rate limited: retry after {exc.value}s")
    if isinstance(exc, (UsernameNotOccupied, PeerIdInvalid)):
        return HTTPException(status_code=404, detail="Channel not found")
    if isinstance(exc, ChannelPrivate):
        return HTTPException(status_code=403, detail="Channel is private")
    return HTTPException(status_code=500, detail=str(exc))


@app.get("/health")
async def health() -> dict:
    return {"ok": bridge.is_connected()}


@app.get("/messages")
async def get_messages(
    handle: str = Query(..., min_length=2),
    after_id: int | None = Query(default=None, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[dict]:
    handle_norm = _normalize_handle(handle)
    try:
        return await bridge.get_messages(handle_norm, after_id, limit)
    except Exception as exc:
        raise _pyrogram_exc_to_http(exc)


@app.get("/validate")
async def validate(handle: str = Query(..., min_length=2)) -> dict:
    handle_norm = _normalize_handle(handle)
    try:
        return await bridge.validate(handle_norm)
    except Exception as exc:
        raise _pyrogram_exc_to_http(exc)


@app.post("/join")
async def join(req: JoinRequest) -> dict:
    handle_norm = _normalize_handle(req.handle)
    try:
        return await bridge.join(handle_norm)
    except Exception as exc:
        raise _pyrogram_exc_to_http(exc)
