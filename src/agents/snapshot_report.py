"""Generate a local, evidence-grounded QA checklist from an approved snapshot."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from models.schemas import Card, Comment
from setup.product_hub_snapshot import validate_snapshot


def cards_from_snapshot(raw: str) -> tuple[dict, list[Card]]:
    data = validate_snapshot(raw)
    cards = []
    for item in data["cards"]:
        comments = item.get("comments", [])
        if not isinstance(comments, list) or not all(isinstance(value, str) for value in comments):
            raise ValueError(f"{item['id']}: comments snapshot format is invalid")
        criteria = item.get("acceptance_criteria", [])
        if not isinstance(criteria, list) or not all(isinstance(value, str) for value in criteria):
            raise ValueError(f"{item['id']}: acceptance criteria snapshot format is invalid")
        documents = item.get("documents", [])
        if not isinstance(documents, list) or not all(isinstance(value, dict) for value in documents):
            raise ValueError(f"{item['id']}: document references snapshot format is invalid")
        cards.append(Card(
            task_id=item["id"], title=item["title"], url=item.get("url", data["board_url"]),
            status=item["status"], qa=item["qa"], description=item.get("description", ""),
            acceptance_criteria=criteria, comments=[Comment(author="", body=value) for value in comments],
            documents=[{"name": str(doc.get("name", "")), "url": str(doc.get("url", ""))} for doc in documents],
            source="product_hub_chrome_extension_snapshot", updated_at=data["generated_at"],
        ))
    return data, cards


def render_snapshot_report(raw: str, report_date: date | None = None) -> tuple[str, dict]:
    data, cards = cards_from_snapshot(raw)
    report_date = report_date or date.today()
    lines = [
        f"# QA Checklist — Product Hub Manual Sync — {report_date:%d/%m/%Y}", "",
        "> Nguồn: snapshot do người dùng xuất từ Chrome Extension. Đây là checklist đề xuất; không có test nào được thực thi hoặc đánh dấu PASS.",
        "", "## Trạng thái đồng bộ", "- Chế độ: Manual Sync (cần Chrome và máy người dùng hoạt động).",
        "- Cloud khi máy tắt: BLOCKED — chưa có Product Hub server-side API/integration được admin cấp quyền và xác minh.",
        f"- Board: {data['board_url']}", f"- Snapshot tạo lúc: {data['generated_at']}",
        f"- Card đã quét: {data['cards_scanned']}", f"- Card QA=Chin trong hai cột: {len(cards)}", "",
        "## Kết quả quét",
    ]
    if not cards:
        lines.append("- Quét thành công: 0 card có QA chính xác là Chin trong Ready for QA và Verifying.")
    for card in cards:
        lines += [f"### {card.task_id} — {card.title}", f"- Cột: {card.status}", f"- QA: {card.qa}", f"- Card: {card.url}"]
        if card.description:
            lines += ["", "**Mô tả đã đọc**", card.description]
        if card.comments:
            lines += ["", "**Comment đã đọc (bối cảnh, không xem là tiêu chí nghiệm thu)**"]
            lines.extend(f"- {comment.body}" for comment in card.comments)
        if card.documents:
            lines += ["", "**Liên kết tài liệu cùng miền (nội dung file chưa tải/đọc)**"]
            lines.extend(f"- [{doc['name'] or doc['url']}]({doc['url']})" for doc in card.documents)
        lines += ["", "**Checklist dựa trên acceptance criteria đã đọc**"]
        if card.acceptance_criteria:
            lines.extend(f"- [ ] Xác minh đúng yêu cầu: {criterion}" for criterion in card.acceptance_criteria)
        else:
            lines.append("- Chưa tạo test case: card không có acceptance criteria đã xác minh. Cần BA/Dev bổ sung hoặc xác nhận tiêu chí.")
        lines += ["", "- Trạng thái thực thi: CHƯA CHẠY.", ""]
    lines += ["## Giới hạn dữ liệu", "- Báo cáo chỉ dùng trường đã đọc trong snapshot; không suy diễn QA từ Reporter/Assignee.",
              "- Không có dữ liệu Telegram/release trong snapshot nên không kết luận về build mới.",
              "- Tài liệu liên kết chỉ được liệt kê; nội dung tài liệu không được tải xuống.", ""]
    payload = {"date": report_date.isoformat(), "mode": "manual_sync", "cloud_status": "BLOCKED",
               "snapshot_generated_at": data["generated_at"], "cards_scanned": data["cards_scanned"],
               "cards": [card.to_dict() for card in cards], "test_execution": "NOT_RUN"}
    return "\n".join(lines), payload


def write_snapshot_report(directory: str | Path, markdown: str, payload: dict) -> tuple[Path, Path]:
    target = Path(directory)
    target.mkdir(parents=True, exist_ok=False)
    md_path, json_path = target / "report.md", target / "report.json"
    md_path.write_text(markdown, encoding="utf-8")
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return md_path, json_path
