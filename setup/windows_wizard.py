"""GUI-only enrollment helper; credentials stay in memory and clipboard only."""
from __future__ import annotations

import asyncio
import json
import threading
import tkinter as tk
from tkinter import ttk

PRODUCT_URL = "https://product-hub.vuatho.com/board"
CHAT_ID = -1002593712725
CHAT_TITLE = "[DEV] VuaTho Mobile"


class SetupWizard:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("VuaTho QA Daily Assistant — Setup")
        self.root.geometry("720x720")
        self.root.minsize(620, 620)
        self.status = tk.StringVar(value="Sẵn sàng. Không gửi OTP hoặc session qua chat.")
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        self.pw = self.browser = self.context = None
        self.tg_client = None
        self.phone_code_hash = None
        self.password_needed = False
        self.product_storage_state = ""
        self.telegram_session = ""
        self._build()
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def _submit(self, coroutine, done=None) -> None:
        future = asyncio.run_coroutine_threadsafe(coroutine, self.loop)
        if done:
            def completed(f):
                try:
                    result = f.result()
                    self.root.after(0, lambda: done(result, None))
                except Exception as exc:  # Never show exception contents; libraries can include request data.
                    error_type = type(exc).__name__
                    self.root.after(0, lambda: done(None, error_type))
            future.add_done_callback(completed)

    def _build(self) -> None:
        outer = ttk.Frame(self.root, padding=18)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="Thiết lập kết nối QA", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(outer, text="Thông tin đăng nhập chỉ được dùng trong cửa sổ này. Sau đó bạn tự dán vào GitHub → Settings → Secrets and variables → Actions.", wraplength=680).pack(anchor="w", pady=(6, 14))

        product = ttk.LabelFrame(outer, text="1. Product Hub", padding=12)
        product.pack(fill="x", pady=6)
        ttk.Label(product, text="Mở cửa sổ Chrome có kiểm soát, tự đăng nhập, rồi quay lại bấm Lưu phiên.", wraplength=650).pack(anchor="w")
        row = ttk.Frame(product); row.pack(fill="x", pady=8)
        ttk.Button(row, text="Mở Product Hub", command=lambda: self._submit(self.open_product, self._product_opened)).pack(side="left")
        ttk.Button(row, text="Lưu phiên đăng nhập", command=lambda: self._submit(self.capture_product, self._product_captured)).pack(side="left", padx=8)
        ttk.Button(row, text="Sao chép PRODUCT_HUB_STORAGE_STATE", command=lambda: self._copy(self.product_storage_state)).pack(side="left")

        telegram = ttk.LabelFrame(outer, text="2. Telegram MTProto", padding=12)
        telegram.pack(fill="x", pady=6)
        ttk.Label(telegram, text=f"Nguồn đã xác minh: {CHAT_TITLE} · chat ID {CHAT_ID}. Cần API ID/Hash từ my.telegram.org.", wraplength=650).pack(anchor="w")
        self.api_id = self._entry(telegram, "Telegram API ID")
        self.api_hash = self._entry(telegram, "Telegram API Hash", show="*")
        self.phone = self._entry(telegram, "Số điện thoại Telegram (quốc tế)")
        self.otp = self._entry(telegram, "Mã đăng nhập — nhập tại đây, không gửi qua chat")
        self.password = self._entry(telegram, "Mật khẩu 2FA (nếu Telegram yêu cầu)", show="*")
        row = ttk.Frame(telegram); row.pack(fill="x", pady=8)
        ttk.Button(row, text="Gửi mã đăng nhập", command=self._send_telegram_code).pack(side="left")
        ttk.Button(row, text="Xác minh và kiểm tra chat", command=self._verify_telegram).pack(side="left", padx=8)
        ttk.Button(row, text="Sao chép TELEGRAM_SESSION", command=lambda: self._copy(self.telegram_session)).pack(side="left")

        secrets = ttk.LabelFrame(outer, text="3. GitHub Secrets", padding=12)
        secrets.pack(fill="x", pady=6)
        ttk.Label(secrets, text="Sao chép các giá trị riêng lẻ rồi tạo secrets: PRODUCT_HUB_STORAGE_STATE, TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_SESSION. Không chụp ảnh màn hình hoặc gửi các giá trị này cho người khác.", wraplength=650).pack(anchor="w")
        row = ttk.Frame(secrets); row.pack(fill="x", pady=6)
        ttk.Button(row, text="Sao chép API ID", command=lambda: self._copy(self.api_id.get())).pack(side="left")
        ttk.Button(row, text="Sao chép API Hash", command=lambda: self._copy(self.api_hash.get())).pack(side="left", padx=6)
        ttk.Button(row, text="Xóa clipboard", command=self._clear_clipboard).pack(side="left")

        ttk.Separator(outer).pack(fill="x", pady=10)
        ttk.Label(outer, textvariable=self.status, wraplength=680).pack(anchor="w")
        ttk.Label(outer, text="Ứng dụng không ghi secrets vào file hoặc log. Sau khi lưu GitHub Secrets, mở Actions → Daily QA report → Run workflow để chạy thử.", wraplength=680).pack(anchor="w", pady=(8, 0))

    def _entry(self, parent, label: str, show: str | None = None):
        row = ttk.Frame(parent); row.pack(fill="x", pady=2)
        ttk.Label(row, text=label, width=44).pack(side="left")
        field = ttk.Entry(row, show=show or "")
        field.pack(side="left", fill="x", expand=True)
        return field

    async def open_product(self):
        from playwright.async_api import async_playwright
        self.pw = await async_playwright().start()
        self.browser = await self.pw.chromium.launch(channel="chrome", headless=False)
        self.context = await self.browser.new_context()
        page = await self.context.new_page()
        await page.goto(PRODUCT_URL, wait_until="domcontentloaded", timeout=45_000)
        return True

    def _product_opened(self, result, error):
        self.status.set("Chrome đã mở Product Hub. Hãy tự đăng nhập trong Chrome rồi bấm ‘Lưu phiên đăng nhập’.") if not error else self.status.set(f"Không thể mở Chrome ({error}). Cài Google Chrome chính thức rồi thử lại.")

    async def capture_product(self):
        if not self.context:
            raise RuntimeError("browser not opened")
        state = await self.context.storage_state()
        return json.dumps(state, ensure_ascii=False, separators=(",", ":"))

    def _product_captured(self, value, error):
        if error:
            self.status.set(f"Chưa lưu được phiên Product Hub ({error}). Hãy xác nhận đã đăng nhập trong Chrome.")
            return
        self.product_storage_state = value
        self.status.set("Đã giữ phiên Product Hub trong bộ nhớ. Bấm Sao chép PRODUCT_HUB_STORAGE_STATE để dán trực tiếp vào GitHub Secret.")

    def _send_telegram_code(self):
        values = (self.api_id.get().strip(), self.api_hash.get().strip(), self.phone.get().strip())
        self._submit(self.send_code(*values), self._telegram_status)

    async def send_code(self, api_id: str, api_hash: str, phone: str):
        from telethon import TelegramClient
        from telethon.sessions import StringSession
        if not (api_id.isdigit() and api_hash and phone):
            raise ValueError("required fields")
        self.tg_client = TelegramClient(StringSession(), int(api_id), api_hash)
        await self.tg_client.connect()
        sent = await self.tg_client.send_code_request(phone)
        self.phone_code_hash = sent.phone_code_hash
        return True

    def _telegram_status(self, value, error):
        self.status.set("Telegram đã gửi mã đăng nhập. Nhập mã vào ô trong ứng dụng này; không gửi mã qua chat.") if not error else self.status.set(f"Không gửi được mã Telegram ({error}). Kiểm tra API ID/Hash và số điện thoại trong ứng dụng.")

    def _verify_telegram(self):
        values = (self.otp.get().strip(), self.password.get(), self.phone.get().strip())
        self._submit(self.verify_telegram(*values), self._telegram_verified)

    async def verify_telegram(self, otp: str, password: str, phone: str):
        if not self.tg_client:
            raise RuntimeError("Telegram is not connected")
        from telethon.errors import SessionPasswordNeededError
        if not await self.tg_client.is_user_authorized():
            if self.password_needed:
                if not password:
                    return "2FA_REQUIRED"
                await self.tg_client.sign_in(password=password)
            else:
                try:
                    await self.tg_client.sign_in(phone, code=otp, phone_code_hash=self.phone_code_hash)
                except SessionPasswordNeededError:
                    self.password_needed = True
                    if not password:
                        return "2FA_REQUIRED"
                    await self.tg_client.sign_in(password=password)
        from telethon.utils import get_peer_id
        entity = None
        async for dialog in self.tg_client.iter_dialogs():
            if dialog.id == CHAT_ID:
                entity = dialog.entity
                break
        if entity is None or get_peer_id(entity) != CHAT_ID or getattr(entity, "title", "") != CHAT_TITLE:
            raise ValueError("verified chat not available")
        return self.tg_client.session.save()

    def _telegram_verified(self, value, error):
        if error:
            self.status.set(f"Chưa xác minh được phiên Telegram/chat ({error}). Kiểm tra OTP/2FA và quyền tham gia chat.")
        elif value == "2FA_REQUIRED":
            self.status.set("Telegram yêu cầu mật khẩu 2FA. Nhập mật khẩu vào ô trong ứng dụng này rồi bấm Xác minh lại.")
        else:
            self.telegram_session = value
            self.status.set("Đã xác minh Telegram đúng chat ID và tên. Session chỉ nằm trong bộ nhớ; bấm Sao chép TELEGRAM_SESSION.")

    def _copy(self, value: str) -> None:
        if not value:
            self.status.set("Chưa có giá trị để sao chép.")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(value)
        self.root.update()
        self.status.set("Đã sao chép. Dán ngay vào GitHub Secret đúng tên; clipboard sẽ còn giá trị đến khi bạn xóa hoặc thay thế.")

    def _clear_clipboard(self) -> None:
        self.root.clipboard_clear()
        self.status.set("Clipboard đã được xóa.")

    def close(self) -> None:
        async def shutdown():
            try:
                if self.tg_client:
                    await self.tg_client.disconnect()
                if self.browser:
                    await self.browser.close()
                if self.pw:
                    await self.pw.stop()
            finally:
                self.loop.stop()
        asyncio.run_coroutine_threadsafe(shutdown(), self.loop)
        self.root.after(100, self.root.destroy)

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    SetupWizard().run()
