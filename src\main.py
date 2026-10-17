from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from agents.product_hub import ProductHubAgent, ProductHubUnavailable
from agents.telegram_release import TelegramReleaseAgent, TelegramUnavailable
from agents.qa_report import QAReportAgent
from storage.history import HistoryStore


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


async def run() -> int:
    report = QAReportAgent(os.getenv("REPORTS_DIR", "reports"))
    history = HistoryStore(os.getenv("HISTORY_PATH", "reports/history.json"))
    blockers: list[str] = []
    cards, releases = [], []
    try:
        cards = await ProductHubAgent().collect()
        logging.info("Product Hub read completed: %d eligible cards", len(cards))
    except Exception as exc:
        blockers.append(str(exc) if isinstance(exc, ProductHubUnavailable) else f"CHƯA THỂ XÁC MINH Product Hub: {type(exc).__name__}")
        logging.warning("Product Hub collection unavailable (%s)", type(exc).__name__)
    try:
        releases = await TelegramReleaseAgent().collect()
        logging.info("Telegram read completed: %d release messages", len(releases))
    except Exception as exc:
        blockers.append(str(exc) if isinstance(exc, TelegramUnavailable) else f"CHƯA THỂ XÁC MINH Telegram: {type(exc).__name__}")
        logging.warning("Telegram collection unavailable (%s)", type(exc).__name__)
    today = datetime.now(ZoneInfo(os.getenv("TIMEZONE", "Asia/Ho_Chi_Minh"))).date()
    md, payload = report.render(cards, releases, today, blockers)
    payload["changes"] = history.diff(payload)
    # Re-render so the report contains the computed history delta.
    md, payload = report.render(cards, releases, today, blockers, payload["changes"])
    report.write(md, payload)
    history.save(payload["date"], payload)
    return 1 if blockers else 0


def main() -> None:
    raise SystemExit(asyncio.run(run()))


if __name__ == "__main__":
    main()
