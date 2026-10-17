"""Read-only Playwright collector. Selectors are configurable and fail closed."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from models.schemas import Card


class ProductHubUnavailable(RuntimeError):
    pass


class ProductHubAgent:
    TARGET_STATUSES = ("Ready for QA", "Verifying")

    def __init__(self, url: str | None = None, storage_state: str | None = None,
                 card_selector: str | None = None, column_selector: str | None = None,
                 qa_selector: str | None = None, assignee: str = "Chin") -> None:
        self.url = url or os.getenv("PRODUCT_HUB_URL", "https://product-hub.vuatho.com/board")
        self.storage_state = storage_state or os.getenv("PRODUCT_HUB_STORAGE_STATE")
        self.card_selector = card_selector or os.getenv("PRODUCT_HUB_CARD_SELECTOR", "[data-card-id]")
        self.column_selector = column_selector or os.getenv("PRODUCT_HUB_COLUMN_SELECTOR", "[data-column-name]")
        self.qa_selector = qa_selector or os.getenv("PRODUCT_HUB_QA_FIELD_SELECTOR", '[data-field="QA"]')
        self.assignee = assignee

    async def collect(self) -> list[Card]:
        if not self.storage_state or not Path(self.storage_state).is_file():
            raise ProductHubUnavailable("CHƯA THỂ XÁC MINH: thiếu phiên Product Hub đã đăng nhập.")
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise ProductHubUnavailable("Playwright chưa được cài đặt.") from exc

        found: dict[str, Card] = {}
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(storage_state=self.storage_state)
            page = await context.new_page()
            try:
                await page.goto(self.url, wait_until="domcontentloaded", timeout=45_000)
                # Load lazy columns/cards by scrolling the board and page until no growth.
                previous = -1
                for _ in range(12):
                    count = await page.locator(self.card_selector).count()
                    if count == previous:
                        break
                    previous = count
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(500)
                    await page.evaluate("document.querySelectorAll('*').forEach(e => { if(e.scrollWidth > e.clientWidth) e.scrollLeft = e.scrollWidth })")
                columns = page.locator(self.column_selector)
                if await columns.count() == 0:
                    raise ProductHubUnavailable("CHƯA THỂ XÁC MINH: không nhận diện được cột theo selector đã cấu hình.")
                for col in await columns.all():
                    label = (await col.get_attribute("data-column-name") or await col.inner_text()).strip()
                    status = next((s for s in self.TARGET_STATUSES if s.casefold() in label.casefold()), None)
                    if status is None:
                        continue
                    for locator in await col.locator(self.card_selector).all():
                        attrs: dict[str, Any] = await locator.evaluate("e => ({...e.dataset})")
                        task_id = str(attrs.get("cardId") or attrs.get("id") or "").strip()
                        title = (await locator.inner_text()).strip().splitlines()[0]
                        qa_node = locator.locator(self.qa_selector)
                        qa = (await qa_node.inner_text()).strip() if await qa_node.count() else ""
                        # Exact account match only; no fallback to reporter or assignee fields.
                        if qa != self.assignee or not task_id:
                            continue
                        href = await locator.get_attribute("href")
                        url = href if href and href.startswith("http") else self.url.rstrip("/") + "/" + (href or task_id).lstrip("/")
                        description = str(attrs.get("description", "")).strip()
                        priority = attrs.get("priority")
                        found[task_id] = Card(task_id, title, url, status, qa, priority=priority,
                                              description=description, build=attrs.get("build"))
            finally:
                await context.close()
                await browser.close()
        return list(found.values())
