from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from agents.qa_intelligence import QAIntelligenceAgent
from models.schemas import Card, Release


class QAReportAgent:
    def __init__(self, output_dir: str | Path = "reports") -> None:
        self.output_dir = Path(output_dir)

    def render(self, cards: list[Card], releases: list[Release], date_value: date,
               blockers: list[str] | None = None, changes: dict | None = None) -> tuple[str, dict]:
        ready = [c for c in cards if c.status == "Ready for QA"]
        verifying = [c for c in cards if c.status == "Verifying"]
        analyzer = QAIntelligenceAgent()
        analyses = {c.task_id: analyzer.analyze(c) for c in cards}
        lines = [f"# DAILY QA REPORT — {date_value.strftime('%d/%m/%Y')}", "",
                 "> Thu thập theo chế độ chỉ đọc. Checklist là đề xuất; chưa có test nào được đánh dấu PASS.", "",
                 "## A. Build mới từ Telegram"]
        if releases:
            for r in releases:
                lines += [f"- Build/version: {r.build or r.version or 'Chưa xác định trong nội dung'}",
                          f"- Ngày thông báo: {r.date}", f"- Nội dung thay đổi: {r.text}",
                          f"- Nguồn thông báo: {r.chat_title} (chat ID {r.chat_id}, message {r.message_id})",
                          "- Phần chưa xác minh: task nào thực sự có trong build; platform nếu không được nêu.", ""]
            impact = analyzer.analyze_release_impact(cards, releases)
            lines.append("- Phân tích tác động (so khớp từ ngữ, cần QA xác nhận):")
            for item in impact:
                tasks = ", ".join(x["task_id"] for x in item["related_cards"]) or "Chưa tìm thấy card liên quan bằng từ khóa."
                lines.append(f"  - {item['release_id']}: task ứng viên {tasks}; {item['smoke_test']} {item['regression']}")
            lines.append("")
        else:
            if any("telegram" in blocker.casefold() for blocker in (blockers or [])):
                lines += ["- CHƯA THỂ XÁC MINH: chưa lấy được dữ liệu Telegram.", ""]
            else:
                lines += ["- Không có thông báo build/release mới trong lần chạy này.", ""]
        def section(title: str, subset: list[Card]) -> None:
            lines.extend([f"## {title}"])
            if not subset:
                lines.append("- Không có card đã xác minh trong lần chạy này.")
            for c in subset:
                plan = analyses[c.task_id]
                lines.extend([f"### {c.task_id} — {c.title}", f"- Priority gốc: {c.priority or 'Chưa cung cấp'}",
                              f"- Nội dung thay đổi: {c.description or 'Chưa đọc được mô tả.'}", f"- Link card: {c.url}",
                              "- Checklist cần test:"])
                for tc in plan["test_cases"]:
                    lines.append(f"  - [{tc['priority']}] {tc['title']}: {tc['expected_result']}")
                lines.append("- Điều kiện chuẩn bị: xác nhận môi trường/build và dữ liệu test theo mô tả card.")
                if plan["clarifications"]:
                    lines.append("- Cần xác nhận với BA/Dev: " + "; ".join(plan["clarifications"]))
                if c.status == "Verifying":
                    lines.append("- Retest: chạy lại các trường hợp liên quan sau sửa lỗi; chưa xác định bug cụ thể nếu không có bằng chứng.")
                lines.append("")
        section("B. Task đang Ready for QA", ready)
        section("C. Task đang Verifying", verifying)
        lines += ["## D. Task mới hoặc thay đổi so với hôm trước", "- Chưa có baseline lịch sử đủ tin cậy để so sánh." if not changes else json.dumps(changes, ensure_ascii=False), "",
                  "## E. Test plan hôm nay"]
        for c in sorted(cards, key=lambda x: (0 if x.status == "Verifying" else 1, x.priority or "Z", x.task_id)):
            lines.append(f"- {c.task_id}: {c.status} — {c.title}")
        lines += ["", "## F. Blocker và thông tin cần xác nhận"]
        lines += [f"- {b}" for b in (blockers or [])] or ["- Không có blocker được ghi nhận."]
        payload = {"date": date_value.isoformat(), "cards": [c.to_dict() for c in cards],
                   "releases": [r.to_dict() for r in releases], "analyses": analyses,
                   "blockers": blockers or [], "changes": changes or {}, "generated_at": __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()}
        return "\n".join(lines) + "\n", payload

    def write(self, markdown: str, payload: dict) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        encoded = json.dumps(payload, ensure_ascii=False, indent=2)
        (self.output_dir / "latest.md").write_text(markdown, encoding="utf-8")
        (self.output_dir / "latest.json").write_text(encoded, encoding="utf-8")
        (self.output_dir / f"{payload['date']}.md").write_text(markdown, encoding="utf-8")
