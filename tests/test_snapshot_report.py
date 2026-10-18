import json
from datetime import date

from agents.snapshot_report import render_snapshot_report, write_snapshot_report


def make_snapshot(cards):
    return json.dumps({
        "schema_version": 1,
        "source": "VuaTho QA Chrome Extension",
        "generated_at": "2026-10-18T00:00:00Z",
        "board_url": "https://product-hub.vuatho.com/board",
        "columns": ["Ready for QA", "Verifying"],
        "cards_scanned": 2,
        "cards": cards,
    }, ensure_ascii=False)


def test_report_uses_only_confirmed_acceptance_criteria_and_marks_manual_blockers(tmp_path):
    card = {
        "id": "VT-APP-42", "title": "Payment", "status": "Ready for QA", "qa": "Chin",
        "url": "https://product-hub.vuatho.com/board?feature=VT-APP-42",
        "description": "Use approved gateway.", "acceptance_criteria": ["Receipt displays final amount."],
        "comments": ["Maybe add retries?"], "documents": [{"name": "Payment spec", "url": "https://product-hub.vuatho.com/docs/42"}],
    }
    markdown, payload = render_snapshot_report(make_snapshot([card]), date(2026, 10, 18))
    assert "- [ ] Xác minh đúng yêu cầu: Receipt displays final amount." in markdown
    assert "Maybe add retries?" in markdown
    assert "không xem là tiêu chí nghiệm thu" in markdown
    assert "Maybe add retries?" not in "\n".join(x for x in markdown.splitlines() if x.startswith("- [ ]"))
    assert "Cloud khi máy tắt: BLOCKED" in markdown
    assert "CHƯA CHẠY" in markdown
    assert "PASS" not in markdown
    assert payload["cloud_status"] == "BLOCKED"
    md_path, json_path = write_snapshot_report(tmp_path / "manual-sync-new", markdown, payload)
    history = tmp_path / "history.json"
    history.write_text("existing history", encoding="utf-8")
    assert md_path.exists() and json_path.exists()
    assert history.read_text(encoding="utf-8") == "existing history"


def test_zero_matching_qa_cards_is_reported_as_successful_empty_scan():
    markdown, payload = render_snapshot_report(make_snapshot([]), date(2026, 10, 18))
    assert "Quét thành công: 0 card có QA chính xác là Chin" in markdown
    assert payload["cards"] == []
