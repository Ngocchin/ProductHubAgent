"""Read-only Product Hub collector using Playwright and fail-closed field checks."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from models.schemas import Card, Comment


class ProductHubUnavailable(RuntimeError):
    pass


def _column_status(ancestor_texts: list[str]) -> str | None:
    """Find the nearest ancestor containing exactly one watched column heading."""
    for text in ancestor_texts:
        present = [status for status in ("Ready for QA", "Verifying") if re.search(rf"(?m)^\s*{re.escape(status)}\s*$", text)]
        if len(present) == 1:
            return present[0]
    return None


def _section(text: str, name: str, following: tuple[str, ...]) -> str:
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if line.strip().casefold() == name.casefold()), None)
    if start is None:
        return ""
    end = next((i for i in range(start + 1, len(lines))
                if lines[i].strip().casefold() in {x.casefold() for x in following}), len(lines))
    return "\n".join(line.strip() for line in lines[start + 1:end] if line.strip()).strip()


def _value_after_label(text: str, label: str) -> str | None:
    lines = [line.strip() for line in text.splitlines()]
    for i, line in enumerate(lines[:-1]):
        if line.casefold() == label.casefold():
            value = lines[i + 1]
            return None if value in {"—", "-", ""} else value
    return None


class ProductHubAgent:
    TARGET_STATUSES = ("Ready for QA", "Verifying")
    TASK_ID = re.compile(r"^VT-[A-Z0-9]+-\d+\b")

    def __init__(self, url: str | None = None, storage_state: str | None = None,
                 card_selector: str | None = None, column_selector: str | None = None,
                 qa_selector: str | None = None, assignee: str = "Chin") -> None:
        self.url = url or os.getenv("PRODUCT_HUB_URL", "https://product-hub.vuatho.com/board")
        self.storage_state = storage_state or os.getenv("PRODUCT_HUB_STORAGE_STATE")
        self.card_selector = card_selector or os.getenv("PRODUCT_HUB_CARD_SELECTOR", "button")
        self.column_selector = column_selector or os.getenv("PRODUCT_HUB_COLUMN_SELECTOR", "")
        self.qa_selector = qa_selector or os.getenv("PRODUCT_HUB_QA_FIELD_SELECTOR", '[role="combobox"][aria-label="QA"]')
        self.assignee = assignee

    async def _read_field(self, page: Any, label: str) -> str:
        selectors = [f'[aria-label="{label}"]', f'[data-field="{label}"]']
        if label == "QA":
            selectors.insert(0, self.qa_selector)
        for selector in dict.fromkeys(selectors):
            locator = page.locator(selector)
            if await locator.count():
                value = (await locator.first.inner_text()).strip()
                if value:
                    return value
        # Product Hub exposes Priority/Status/QA as named comboboxes in its UI.
        combo = page.get_by_role("combobox", name=label, exact=True)
        return (await combo.first.inner_text()).strip() if await combo.count() else ""

    async def collect(self) -> list[Card]:
        # Google SSO rejects automation-controlled browser sign-in. A browser
        # storage-state file is not an administrator-approved server integration.
        # Keep cloud collection disabled until a documented read-only API exists.
        raise ProductHubUnavailable(
            "BLOCKED: chưa có Product Hub API/integration server-side được quản trị viên cấp quyền và xác minh. "
            "Dùng Chrome Extension trên máy người dùng để xuất snapshot; không dùng Playwright storage state trên cloud."
        )

        found: dict[str, Card] = {}
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(storage_state=self.storage_state)
            page = await context.new_page()
            try:
                await page.goto(self.url, wait_until="domcontentloaded", timeout=45_000)
                if "login" in page.url.casefold() or "sign-in" in page.url.casefold():
                    raise ProductHubUnavailable("CHƯA THỂ XÁC MINH: phiên Product Hub hết hạn hoặc chưa đăng nhập.")
                # Repeatedly scroll the page and horizontally scroll board lanes to reveal lazy cards.
                previous = -1
                for _ in range(12):
                    count = await page.locator(self.card_selector).count()
                    if count == previous:
                        break
                    previous = count
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.evaluate("document.querySelectorAll('*').forEach(e => { if (e.scrollWidth > e.clientWidth + 8) e.scrollLeft = e.scrollWidth })")
                    await page.wait_for_timeout(250)

                candidates = []
                if self.column_selector:
                    columns = page.locator(self.column_selector)
                    if not await columns.count():
                        raise ProductHubUnavailable("CHƯA THỂ XÁC MINH: selector cột không khớp Product Hub.")
                    for col in await columns.all():
                        label = (await col.get_attribute("data-column-name") or await col.inner_text()).strip()
                        status = next((s for s in self.TARGET_STATUSES if re.search(rf"\b{re.escape(s)}\b", label, re.I)), None)
                        if status:
                            candidates.extend((item, status) for item in await col.locator(self.card_selector).all())
                else:
                    for item in await page.locator(self.card_selector).all():
                        label = (await item.inner_text()).strip()
                        if not self.TASK_ID.match(label):
                            continue
                        ancestors = await item.evaluate("""e => { const a=[]; for(let n=e.parentElement;n;n=n.parentElement){a.push(n.innerText||''); if(n===document.body)break;} return a; }""")
                        status = _column_status(ancestors)
                        if status:
                            candidates.append((item, status))
                if not candidates:
                    raise ProductHubUnavailable("CHƯA THỂ XÁC MINH: không tìm thấy card trong hai cột cần theo dõi; kiểm tra selector hoặc quyền truy cập.")

                seen: set[str] = set()
                for item, status in candidates:
                    label = (await item.inner_text()).strip()
                    id_match = self.TASK_ID.match(label)
                    if not id_match:
                        continue
                    task_id = id_match.group(0)
                    if task_id in seen:
                        continue
                    seen.add(task_id)
                    title = next((line.strip() for line in label.splitlines() if line.strip() and not line.strip().startswith(task_id)), task_id)
                    try:
                        await item.click(timeout=10_000)
                        title_node = page.locator("#sheet-title")
                        await title_node.wait_for(state="visible", timeout=10_000)
                        detail_text = await title_node.evaluate("""e => { for(let n=e;n;n=n.parentElement){const t=n.innerText||''; if(t.includes('PEOPLE')&&t.includes('DESCRIPTION')) return t;} return ''; }""")
                        if not detail_text:
                            raise ProductHubUnavailable(f"CHƯA THỂ XÁC MINH {task_id}: không đọc được phần chi tiết card.")
                        qa = await self._read_field(page, "QA")
                        if not qa:
                            raise ProductHubUnavailable(f"CHƯA THỂ XÁC MINH {task_id}: không đọc được trường QA riêng.")
                        if qa == self.assignee:
                            priority = await self._read_field(page, "Priority") or None
                            detail_status = await self._read_field(page, "Status") or status
                            actual_title = (await title_node.inner_text()).strip()
                            description = _section(detail_text, "DESCRIPTION", ("ACCEPTANCE CRITERIA", "REFERENCES", "EVIDENCE", "IMPLEMENTATION", "FIX ATTEMPTS", "ACTIVITY", "PEOPLE"))
                            criteria_text = _section(detail_text, "ACCEPTANCE CRITERIA", ("REFERENCES", "EVIDENCE", "IMPLEMENTATION", "FIX ATTEMPTS", "ACTIVITY", "PEOPLE"))
                            criteria = [re.sub(r"^\d+[.)]\s*", "", x).strip() for x in criteria_text.splitlines() if x.strip()]
                            comments_text = _section(detail_text, "COMMENTS", ("DESCRIPTION", "ACCEPTANCE CRITERIA", "REFERENCES"))
                            comments = [Comment(author="", body=x) for x in comments_text.splitlines() if x.strip() and x.strip() != "Comment"]
                            project = await self._read_field(page, "Project") or None
                            documents_text = _section(detail_text, "TÀI LIỆU MARKDOWN", ("COMMENTS", "DESCRIPTION"))
                            documents = [{"name": name, "content_read": "false"}
                                         for name in re.findall(r"[^\n]+?\.(?:md|markdown)\b", documents_text, re.I)]
                            url = page.url if "feature=" in page.url or "bug=" in page.url else f"{self.url.split('?')[0]}?feature={task_id}"
                            found[task_id] = Card(task_id, actual_title or title, url, detail_status, qa,
                                                  priority=priority, project=project, description=description,
                                                  module=_value_after_label(detail_text, "Module"),
                                                  area=_value_after_label(detail_text, "Area"),
                                                  acceptance_criteria=criteria, comments=comments,
                                                  documents=documents)
                    finally:
                        close = page.get_by_role("button", name="Đóng", exact=True)
                        if await close.count():
                            await close.first.click()
                return list(found.values())
            finally:
                await context.close()
                await browser.close()
