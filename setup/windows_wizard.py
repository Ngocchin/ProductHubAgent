"""Click-to-run local enrollment wizard. Sensitive values remain in process memory."""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
import threading
import tkinter as tk
import webbrowser
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from zoneinfo import ZoneInfo

from .async_utils import submit_coroutine
from .github_config import GitHubRepoConfigurator, GitHubSetupError
from .product_hub_enrollment import PRODUCT_HUB_URL
from .product_hub_snapshot import validate_snapshot
from agents.snapshot_report import render_snapshot_report, write_snapshot_report

CHAT_ID = -1002593712725
CHAT_TITLE = "[DEV] VuaTho Mobile"
REPOSITORY = "Ngocchin/ProductHubAgent"
GITHUB_TOKEN_URL = "https://github.com/settings/personal-access-tokens/new"
TELEGRAM_APPS_URL = "https://my.telegram.org/apps"
DAILY_WORKFLOW_URL = f"https://github.com/{REPOSITORY}/actions/workflows/daily-qa.yml"
REPORT_URL = f"https://github.com/{REPOSITORY}/blob/main/reports/latest.md"


class SetupWizard:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("VuaTho QA Daily Assistant — Setup")
        self.root.geometry("850x900")
        self.root.minsize(760, 760)
        self.status = tk.StringVar(value="Bắt đầu bằng Connect GitHub. Không gửi OTP, token hoặc session qua chat.")
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

        self.product_snapshot = ""
        self.product_snapshot_data = None
        self.product_report_directory: Path | None = None
        self.product_report_directory: Path | None = None
        self.tg_client = None
        self.phone_code_hash = None
        self.password_needed = False
        self.product_verified = False
        self.telegram_verified = False
        self.telegram_session = ""
        self.github_verified = False
        self._github_token_memory = ""
        self._pending_github_token = ""
        self._build()
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def _submit(self, coroutine, done=None) -> None:
        try:
            future = submit_coroutine(self.loop, coroutine)
        except Exception as exc:
            self.status.set(f"Không khởi chạy được thao tác ({type(exc).__name__}).")
            return

        if done:
            def completed(future):
                try:
                    result = future.result()
                    self.root.after(0, lambda result=result: done(result, None))
                except Exception as exc:
                    if isinstance(exc, GitHubSetupError):
                        safe_error = str(exc)
                    else:
                        safe_error = _safe_exception_message(exc)
                    self.root.after(0, lambda safe_error=safe_error: done(None, safe_error))
            future.add_done_callback(completed)

    def _build(self) -> None:
        outer = ttk.Frame(self.root, padding=16)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="Thiết lập VuaTho QA", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(outer, text=f"Repository đích: {REPOSITORY}. Token, OTP và Telegram session chỉ nằm trong bộ nhớ ứng dụng.", wraplength=810).pack(anchor="w", pady=(4, 12))

        github = ttk.LabelFrame(outer, text="1. Connect GitHub", padding=10)
        github.pack(fill="x", pady=5)
        ttk.Label(github, text="Fine-grained token chỉ cho ProductHubAgent: Secrets/Variables: Read and write để lưu cấu hình; tùy chọn Contents: Read and write nếu upload report. Metadata: Read được cấp tự động. Token chỉ nằm trong bộ nhớ phiên.", wraplength=790).pack(anchor="w")
        row = ttk.Frame(github); row.pack(fill="x", pady=6)
        ttk.Button(row, text="Connect GitHub", command=self._open_github_token_page).pack(side="left")
        self.github_token = self._entry(row, "Fine-grained token", show="*")
        ttk.Button(row, text="Verify GitHub", command=self._verify_github).pack(side="left", padx=6)

        product = ttk.LabelFrame(outer, text="2. Connect Product Hub", padding=10)
        product.pack(fill="x", pady=5)
        ttk.Label(product, text="Đăng nhập Google trong Chrome bình thường. Extension chỉ đọc nội dung hiển thị trên product-hub.vuatho.com; không lấy mật khẩu, cookie, token phiên hoặc OTP. Chưa có API Product Hub được quản trị viên xác nhận.", wraplength=790).pack(anchor="w")
        row = ttk.Frame(product); row.pack(fill="x", pady=6)
        ttk.Button(row, text="Install / Open Extension", command=self._install_extension).pack(side="left")
        ttk.Button(row, text="Connect Product Hub", command=lambda: self._open_chrome(PRODUCT_HUB_URL)).pack(side="left", padx=6)
        ttk.Button(row, text="Verify JSON", command=self._import_product_snapshot).pack(side="left")
        ttk.Button(row, text="Create Local QA Report", command=self._create_local_qa_report).pack(side="left", padx=6)
        ttk.Button(row, text="Upload Saved Report", command=self._upload_saved_report).pack(side="left")
        ttk.Label(product, text="Manual Sync: chỉ quét khi Chrome/PC hoạt động; tạo Markdown/JSON cục bộ. Cloud: BLOCKED đến khi Product Hub admin cấp và xác minh API/integration read-only server-side.", wraplength=790).pack(anchor="w", pady=(2, 0))

        telegram = ttk.LabelFrame(outer, text="3. Connect Telegram", padding=10)
        telegram.pack(fill="x", pady=5)
        ttk.Label(telegram, text=f"Nhóm mục tiêu: {CHAT_TITLE} · {CHAT_ID}. Nếu chưa có API ID/Hash, lấy tại my.telegram.org/apps; OTP/2FA chỉ nhập tại đây.", wraplength=790).pack(anchor="w")
        row = ttk.Frame(telegram); row.pack(fill="x", pady=5)
        ttk.Button(row, text="Lấy API ID/Hash", command=lambda: webbrowser.open(TELEGRAM_APPS_URL)).pack(side="left")
        self.api_id = self._entry(row, "Telegram API ID")
        self.api_hash = self._entry(row, "Telegram API Hash", show="*")
        self.phone = self._entry(row, "Số điện thoại quốc tế")
        row = ttk.Frame(telegram); row.pack(fill="x", pady=5)
        self.otp = self._entry(row, "OTP — chỉ nhập tại đây")
        self.password = self._entry(row, "Mật khẩu 2FA nếu được yêu cầu", show="*")
        ttk.Button(row, text="Connect Telegram", command=self._send_telegram_code).pack(side="left", padx=6)
        ttk.Button(row, text="Test Telegram", command=self._verify_telegram).pack(side="left")

        configure = ttk.LabelFrame(outer, text="4. Configure GitHub automatically", padding=10)
        configure.pack(fill="x", pady=5)
        ttk.Label(configure, text="Khi GitHub và Telegram được kiểm tra, ứng dụng mã hóa Telegram secrets bằng public key GitHub, cập nhật variables và xác minh tên. Không hiển thị/đọc lại giá trị secret.", wraplength=790).pack(anchor="w")
        ttk.Button(configure, text="Save Configuration", command=self._save_configuration).pack(anchor="w", pady=6)

        verify = ttk.LabelFrame(outer, text="5. Verify Connections", padding=10)
        verify.pack(fill="x", pady=5)
        row = ttk.Frame(verify); row.pack(fill="x")
        ttk.Button(row, text="Run QA Report", command=self._run_qa_report).pack(side="left")
        ttk.Button(row, text="View Report", command=lambda: webbrowser.open(REPORT_URL)).pack(side="left", padx=6)
        ttk.Label(outer, textvariable=self.status, wraplength=810).pack(anchor="w", pady=(8, 0))
        ttk.Label(outer, text="Đóng wizard sẽ xóa token/OTP/session khỏi bộ nhớ ứng dụng. Không tạo file credential cục bộ.", wraplength=810).pack(anchor="w", pady=(5, 0))

    def _entry(self, parent, label: str, show: str | None = None):
        row = ttk.Frame(parent); row.pack(fill="x", pady=2)
        ttk.Label(row, text=label, width=32).pack(side="left")
        field = ttk.Entry(row, show=show or "")
        field.pack(side="left", fill="x", expand=True)
        return field

    def _open_github_token_page(self) -> None:
        webbrowser.open(GITHUB_TOKEN_URL)
        self.status.set("Tạo fine-grained token cho riêng Ngocchin/ProductHubAgent; cấp Secrets: Read and write, Variables: Read and write, Actions: Read and write. Dán token vào ô và bấm Verify GitHub.")

    def _verify_github(self) -> None:
        token = self.github_token.get().strip()
        if not token:
            self.status.set("Dán fine-grained token vào ô GitHub trước.")
            return
        self._pending_github_token = token
        self._submit(asyncio.to_thread(GitHubRepoConfigurator(token).verify_access), self._github_verified)

    def _github_verified(self, result, error) -> None:
        self.github_verified = not error
        if not error:
            self._github_token_memory = self._pending_github_token
        self._pending_github_token = ""
        self.status.set(error or f"GitHub đã xác minh đúng {result}. Token hiện chỉ nằm trong ứng dụng.")

    def _send_telegram_code(self):
        values = (self.api_id.get().strip(), self.api_hash.get().strip(), self.phone.get().strip())
        self.telegram_verified = False
        self._submit(self.send_telegram_code(*values), self._telegram_code_sent)

    async def send_telegram_code(self, api_id: str, api_hash: str, phone: str):
        from telethon import TelegramClient
        from telethon.sessions import StringSession
        if not (api_id.isdigit() and api_hash and phone.startswith("+")):
            raise ValueError("Nhập API ID, API Hash và số điện thoại quốc tế có dấu +.")
        if self.tg_client:
            await self.tg_client.disconnect()
        self.tg_client = TelegramClient(StringSession(), int(api_id), api_hash)
        await self.tg_client.connect()
        sent = await self.tg_client.send_code_request(phone)
        self.phone_code_hash = sent.phone_code_hash
        return "Telegram đã gửi mã. Nhập mã trong cửa sổ wizard rồi bấm Test Telegram."

    def _telegram_code_sent(self, result, error):
        self.status.set(error or result)

    def _verify_telegram(self):
        values = (self.otp.get().strip(), self.password.get(), self.phone.get().strip())
        self._submit(self.test_telegram(*values), self._telegram_tested)

    async def test_telegram(self, otp: str, password: str, phone: str):
        if self.tg_client is None:
            raise RuntimeError("Bấm Connect Telegram trước để gửi mã đăng nhập.")
        from telethon.errors import SessionPasswordNeededError
        from telethon.utils import get_peer_id
        if not await self.tg_client.is_user_authorized():
            if not self.phone_code_hash:
                raise RuntimeError("Telegram chưa gửi mã trong phiên hiện tại; bấm Connect Telegram.")
            if self.password_needed:
                if not password:
                    return "Telegram yêu cầu 2FA. Nhập mật khẩu 2FA trong wizard rồi bấm Test Telegram lại."
                await self.tg_client.sign_in(password=password)
            else:
                try:
                    await self.tg_client.sign_in(phone, code=otp, phone_code_hash=self.phone_code_hash)
                except SessionPasswordNeededError:
                    self.password_needed = True
                    if not password:
                        return "Telegram yêu cầu 2FA. Nhập mật khẩu 2FA trong wizard rồi bấm Test Telegram lại."
                    await self.tg_client.sign_in(password=password)
        entity = None
        async for dialog in self.tg_client.iter_dialogs():
            if dialog.id == CHAT_ID:
                entity = dialog.entity
                break
        if entity is None or get_peer_id(entity) != CHAT_ID or getattr(entity, "title", "") != CHAT_TITLE:
            raise RuntimeError(f"Không xác minh được đúng nhóm {CHAT_TITLE} ({CHAT_ID}) trong danh sách chat.")
        # Reading one real message verifies that the authorized account can read chat history.
        messages = [message async for message in self.tg_client.iter_messages(entity, limit=1)]
        if not messages:
            raise RuntimeError("Đúng nhóm nhưng không có lịch sử tin nhắn đọc được để xác minh quyền đọc.")
        self.telegram_session = self.tg_client.session.save()
        self.telegram_verified = True
        return f"Đã xác minh nhóm đúng ID và đọc được lịch sử ({len(messages)} tin gần nhất được kiểm tra). Session chỉ ở bộ nhớ."

    def _telegram_tested(self, result, error):
        if error:
            self.telegram_verified = False
            self.telegram_session = ""
            self.status.set(error)
        else:
            if self.telegram_verified:
                self.otp.delete(0, "end")
                self.password.delete(0, "end")
            self.status.set(result)

    def _save_configuration(self) -> None:
        token = self._github_token_memory
        if not self.github_verified or not token:
            self.status.set("Cần Verify GitHub bằng fine-grained token trước.")
            return
        if not self.telegram_verified or not self.telegram_session:
            self.status.set("Cần Test Telegram thành công và xác minh quyền đọc đúng nhóm trước.")
            return
        secrets = {
            "TELEGRAM_API_ID": self.api_id.get().strip(),
            "TELEGRAM_API_HASH": self.api_hash.get().strip(),
            "TELEGRAM_SESSION": self.telegram_session,
        }
        variables = {
            "TELEGRAM_CHAT_ID": str(CHAT_ID),
            "TELEGRAM_CHAT_TITLE": CHAT_TITLE,
            "PRODUCT_HUB_URL": PRODUCT_HUB_URL,
        }
        self._submit(asyncio.to_thread(GitHubRepoConfigurator(token).configure, secrets, variables), self._configuration_saved)

    def _configuration_saved(self, result, error):
        self.github_token.delete(0, "end")
        if error:
            self.status.set(error + " Hãy kiểm tra quyền token rồi thử lại.")
        else:
            self.status.set("Đã cấu hình và chỉ xác minh tên: " + ", ".join(result["secrets"] + result["variables"]) + ". Token vẫn chỉ ở bộ nhớ đến khi đóng wizard.")

    def _install_extension(self) -> None:
        source_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1])) / "product-hub-extension"
        if not source_root.is_dir():
            self.status.set("Không tìm thấy Chrome Extension đi kèm. Cài lại artifact wizard mới nhất.")
            return
        destination = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "VuaThoQA" / "product-hub-extension"
        try:
            shutil.copytree(source_root, destination, dirs_exist_ok=True)
            self._open_chrome("chrome://extensions")
            os.startfile(str(destination))
            self.status.set(f"Extension đã được giải nén tại {destination}. Trong Chrome bật Developer mode → Load unpacked → chọn thư mục này.")
        except OSError as exc:
            self.status.set(f"Không cài/mở được extension ({type(exc).__name__}).")

    def _open_chrome(self, url: str) -> None:
        candidates = [shutil.which("chrome"), shutil.which("chrome.exe")]
        for base in (os.environ.get("PROGRAMFILES"), os.environ.get("PROGRAMFILES(X86)"), os.environ.get("LOCALAPPDATA")):
            if base:
                candidates.append(str(Path(base) / "Google" / "Chrome" / "Application" / "chrome.exe"))
        executable = next((candidate for candidate in candidates if candidate and Path(candidate).is_file()), None)
        if executable:
            subprocess.Popen([executable, url], close_fds=True)
        else:
            self.status.set("Không tìm thấy Google Chrome. Cài/mở Chrome, rồi bấm Connect Product Hub lại.")

    def _import_product_snapshot(self) -> None:
        path = filedialog.askopenfilename(title="Chọn JSON đã xuất từ VuaTho QA Extension", filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            raw = Path(path).read_text(encoding="utf-8")
            data = validate_snapshot(raw)
        except (OSError, ValueError) as exc:
            self.product_verified = False
            self.product_snapshot = ""
            self.product_snapshot_data = None
            self.status.set(f"Product Hub snapshot chưa xác minh: {exc}")
            return
        self.product_snapshot = raw
        self.product_snapshot_data = data
        self.product_verified = True
        self.product_report_directory = None
        self.status.set(f"Snapshot đúng schema: {len(data['cards'])} card QA=Chin khai báo; cột {', '.join(data['columns'])}; thời điểm xuất {data['generated_at']}. Hãy Verify board trực tiếp trong Extension.")

    def _create_local_qa_report(self) -> None:
        if not self.product_verified or not self.product_snapshot:
            self.status.set("Verify JSON trước khi tạo report.")
            return
        parent = filedialog.askdirectory(title="Chọn thư mục lưu report QA cục bộ")
        if not parent:
            return
        now = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))
        target = Path(parent) / ("manual-sync-" + now.strftime("%Y%m%d-%H%M%S-%f"))
        try:
            markdown, payload = render_snapshot_report(self.product_snapshot, now.date())
            md_path, json_path = write_snapshot_report(target, markdown, payload)
        except (OSError, ValueError) as exc:
            self.status.set(f"Không tạo được report ({type(exc).__name__}).")
            return
        self.product_report_directory = target
        self.status.set(f"Manual Sync report đã tạo: {md_path} và {json_path}. Cloud vẫn BLOCKED.")

    def _upload_saved_report(self) -> None:
        if not self.product_report_directory or not self.product_report_directory.is_dir():
            self.status.set("Tạo report cục bộ trước khi upload.")
            return
        if not self.github_verified or not self._github_token_memory:
            self.status.set("Verify GitHub trước; token cần Contents: Read and write để upload report.")
            return
        accepted = messagebox.askyesno(
            "Xác nhận upload report",
            f"Upload report Markdown và JSON của Manual Sync lên repository private {REPOSITORY}? Nội dung snapshot sẽ được commit vào reports/manual-sync/; cần quyền Contents: Read and write. Không upload credentials và không bật cloud schedule.",
        )
        if not accepted:
            self.status.set("Đã hủy upload; report vẫn chỉ lưu cục bộ.")
            return
        repo_dir = f"reports/manual-sync/{self.product_report_directory.name}"
        self.status.set("Đang upload report đã xác nhận...")
        self._submit(asyncio.to_thread(self._upload_report_files, GitHubRepoConfigurator(self._github_token_memory), self.product_report_directory, repo_dir), self._report_uploaded)

    @staticmethod
    def _upload_report_files(configurator, directory: Path, repo_dir: str) -> list[str]:
        urls = []
        for filename in ("report.md", "report.json"):
            content = (directory / filename).read_text(encoding="utf-8")
            urls.append(configurator.upload_report_file(f"{repo_dir}/{filename}", content))
        return urls

    def _report_uploaded(self, urls, error):
        if error:
            self.status.set(error)
        else:
            self.status.set(f"Đã upload {len(urls)} report files vào reports/manual-sync/ trong private repo. Lịch cloud vẫn BLOCKED.")

    def _run_qa_report(self) -> None:
        self.status.set("Báo cáo cloud đang BLOCKED vì chưa có Product Hub API/integration server-side được admin cấp quyền và xác minh. Extension snapshot không bật lịch chạy khi PC tắt.")

    def _report_dispatched(self, _result, error):
        self._github_token_memory = ""
        self.github_verified = False
        self.github_token.delete(0, "end")
        if error:
            self.status.set(error + " Token đã xóa khỏi bộ nhớ; bạn vẫn có thể chạy từ trang GitHub Actions.")
        else:
            self.status.set("GitHub Actions đã nhận yêu cầu chạy báo cáo. Token đã xóa khỏi bộ nhớ.")

    def close(self) -> None:
        self._github_token_memory = ""
        self._pending_github_token = ""
        self.product_snapshot = ""
        self.product_snapshot_data = None
        self.telegram_session = ""
        self.github_verified = False
        self.product_verified = False
        self.telegram_verified = False
        for field_name in ("github_token", "api_hash", "otp", "password"):
            field = getattr(self, field_name, None)
            if field is not None:
                try:
                    field.delete(0, "end")
                except tk.TclError:
                    pass
        async def shutdown():
            try:
                if self.tg_client:
                    await self.tg_client.disconnect()
            finally:
                self.loop.stop()
        if self.loop.is_running():
            future = asyncio.run_coroutine_threadsafe(shutdown(), self.loop)
            future.add_done_callback(lambda _future: self.root.after(0, self.root.destroy))
        else:
            self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def main() -> int:
    SetupWizard().run()
    return 0


def _safe_exception_message(exc: Exception) -> str:
    name = type(exc).__name__
    if name in {"TimeoutError", "PlaywrightTimeoutError"}:
        return "Hết thời gian chờ. Kiểm tra đăng nhập, kết nối mạng và thử lại."
    if name in {"PhoneCodeInvalidError", "PhoneCodeExpiredError"}:
        return "OTP không hợp lệ hoặc đã hết hạn. Gửi mã mới rồi thử lại."
    if name in {"PasswordHashInvalidError"}:
        return "Mật khẩu 2FA không hợp lệ. Kiểm tra và thử lại trong wizard."
    return f"Thao tác thất bại ({name}). Kiểm tra thông tin nhập và thử lại; chi tiết nhạy cảm đã được ẩn."


if __name__ == "__main__":
    raise SystemExit(main())
