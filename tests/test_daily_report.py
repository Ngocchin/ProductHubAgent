import json
from datetime import date
from agents.qa_report import QAReportAgent
from models.schemas import Card


def test_report_writes_daily_latest_and_json(tmp_path):
    c = Card("VT-10", "Thanh toán", "https://example.test/10", "Verifying", "Chin", description="Hoàn tất thanh toán")
    agent = QAReportAgent(tmp_path)
    md, data = agent.render([c], [], date(2026, 10, 17), ["CHƯA THỂ XÁC MINH Telegram"])
    agent.write(md, data)
    assert "DAILY QA REPORT — 17/10/2026" in (tmp_path / "latest.md").read_text(encoding="utf-8")
    assert "Retest" in md
    assert json.loads((tmp_path / "latest.json").read_text(encoding="utf-8"))["cards"][0]["task_id"] == "VT-10"
    assert (tmp_path / "2026-10-17.md").exists()


def test_report_does_not_claim_no_release_when_telegram_collection_failed():
    md, _ = QAReportAgent().render(
        [], [], date(2026, 10, 17),
        ["CHƯA THỂ XÁC MINH: cần MTProto credentials và TELEGRAM_CHAT_ID đã xác minh."],
    )
    assert "CHƯA THỂ XÁC MINH: chưa lấy được dữ liệu Telegram." in md
    assert "Không có thông báo build/release mới" not in md
