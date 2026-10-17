"""Read-only Telegram MTProto collector; chat ID must be explicitly verified."""
from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime, timezone

from models.schemas import Release


class TelegramUnavailable(RuntimeError):
    pass


class TelegramReleaseAgent:
    def __init__(self, api_id: str | None = None, api_hash: str | None = None,
                 session: str | None = None, chat_id: int | None = None,
                 chat_title: str | None = None) -> None:
        self.api_id = api_id or os.getenv("TELEGRAM_API_ID")
        self.api_hash = api_hash or os.getenv("TELEGRAM_API_HASH")
        self.session = session or os.getenv("TELEGRAM_SESSION")
        if chat_id is not None:
            self.chat_id = chat_id
        else:
            raw_chat_id = (os.getenv("TELEGRAM_CHAT_ID") or "").strip() or "-1002593712725"
            try:
                self.chat_id = int(raw_chat_id)
            except ValueError:
                self.chat_id = None
        self.chat_title = chat_title or os.getenv("TELEGRAM_CHAT_TITLE", "[DEV] VuaTho Mobile")

    async def collect(self, limit: int = 200) -> list[Release]:
        if not all((self.api_id, self.api_hash, self.session)) or self.chat_id is None:
            raise TelegramUnavailable("CHƯA THỂ XÁC MINH: cần MTProto credentials và TELEGRAM_CHAT_ID đã xác minh.")
        try:
            from telethon import TelegramClient
            from telethon.sessions import StringSession
            from telethon.utils import get_peer_id
        except ImportError as exc:
            raise TelegramUnavailable("Telethon chưa được cài đặt.") from exc
        client = TelegramClient(StringSession(self.session), int(self.api_id), self.api_hash)
        await client.connect()
        try:
            if not await client.is_user_authorized():
                raise TelegramUnavailable("Phiên Telegram chưa được cấp quyền; hoàn tất đăng nhập cục bộ an toàn.")
            entity = None
            async for dialog in client.iter_dialogs():
                if dialog.id == self.chat_id:
                    entity = dialog.entity
                    break
            if entity is None:
                raise TelegramUnavailable("Chat ID chưa có trong danh sách cuộc trò chuyện được tài khoản cấp quyền.")
            title = getattr(entity, "title", None) or getattr(entity, "username", None) or str(self.chat_id)
            if get_peer_id(entity) != self.chat_id:
                raise TelegramUnavailable("Chat ID trả về không khớp cấu hình.")
            if title.casefold() != self.chat_title.casefold():
                raise TelegramUnavailable("Tên chat không khớp nguồn đã cấu hình; dừng đọc để tránh nhầm cuộc trò chuyện.")
            results: list[Release] = []
            async for msg in client.iter_messages(entity, limit=limit):
                text = (msg.message or "").strip()
                if not text or not any(word in text.casefold() for word in ("build", "release", "version", "phiên bản", "cập nhật", "bug fix")):
                    continue
                date = (msg.date or datetime.now(timezone.utc)).isoformat()
                rid = hashlib.sha256(f"{self.chat_id}:{msg.id}".encode()).hexdigest()
                version = (re.search(r"\b(?:version|ver|phiên bản)\s*[:#-]?\s*v?([\d]+(?:\.[\d]+){1,3})", text, re.I)
                           or re.search(r"\[\s*Vua\s+Tho\s+App\s+v?([\d]+(?:\.[\d]+){1,3})\s*\]", text, re.I))
                build = re.search(r"\bbuild\s*[:#-]?\s*([\w.-]+)", text, re.I)
                platform = re.search(r"\b(android|ios|iOS)\b", text, re.I)
                internal_chat_id = str(abs(self.chat_id))
                if self.chat_id < 0 and internal_chat_id.startswith("100"):
                    internal_chat_id = internal_chat_id[3:]
                results.append(Release(rid, self.chat_id, title, msg.id, date, text,
                                       version.group(1) if version else None,
                                       build.group(1) if build else None,
                                       platform.group(1) if platform else None,
                                       source_url=f"https://t.me/c/{internal_chat_id}/{msg.id}"))
            return list(reversed(results))
        finally:
            await client.disconnect()
