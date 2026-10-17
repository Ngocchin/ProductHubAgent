"""Deterministic, evidence-grounded test plan fallback. Never claims execution."""
from __future__ import annotations

import re
from models.schemas import Card, Release, TestCase


class QAIntelligenceAgent:
    def analyze(self, card: Card) -> dict:
        text = "\n".join(x for x in (card.title, card.description, *card.acceptance_criteria) if x).strip()
        source = card.task_id
        cases: list[TestCase] = []
        if not card.description.strip() and not card.acceptance_criteria:
            return {"test_cases": [], "clarifications": ["Card không có mô tả/acceptance criteria đọc được; chỉ có title nên chưa đủ căn cứ lập test cụ thể. Cần BA/Dev bổ sung."], "evidence": []}
        snippets = [s.strip(" -*\t") for s in re.split(r"\n+|(?<=[.!?])\s+", text) if s.strip()]
        cases.append(TestCase(f"{source}-TC01", f"Kiểm tra luồng chính: {card.title}", [], [],
                              ["Mở chức năng được mô tả trong card", "Thực hiện thao tác theo yêu cầu đã ghi"],
                              "Đối chiếu kết quả thực tế với yêu cầu/acceptance criteria được cung cấp; chưa thể kết luận trước khi chạy.", "P1", source))
        cases.append(TestCase(f"{source}-TC02", f"Kiểm tra đầu vào không hợp lệ: {card.title}", [], ["Thiếu/sai định dạng dữ liệu đầu vào (nếu trường này tồn tại)"],
                              ["Thử gửi dữ liệu không hợp lệ theo loại trường được nêu trong yêu cầu"],
                              "Hệ thống từ chối an toàn và thông báo phù hợp; quy tắc cụ thể cần BA/Dev xác nhận nếu card không nêu.", "P2", source))
        criteria = card.acceptance_criteria or snippets
        cases.extend(TestCase(f"{source}-TC{n+3:02d}", f"Xác minh yêu cầu: {criterion[:90]}", [], [],
                              [f"Kiểm tra hành vi tương ứng với: {criterion}"],
                              f"Hành vi khớp đúng nội dung nguồn: {criterion}", "P1", source)
                      for n, criterion in enumerate(criteria[:8]))
        clarifications = []
        if not card.acceptance_criteria:
            clarifications.append("Card chưa có acceptance criteria tách riêng; xác nhận tiêu chí nghiệm thu với BA/Dev.")
        if not card.priority:
            clarifications.append("Card chưa cung cấp priority gốc.")
        return {"test_cases": [x.to_dict() for x in cases], "clarifications": clarifications,
                "evidence": [card.task_id], "source_priority": card.priority, "test_priority_is_proposal": True}

    def analyze_release_impact(self, cards: list[Card], releases: list[Release]) -> list[dict]:
        out = []
        def terms_for(value: str) -> set[str]:
            normalized = value.casefold()
            for phrase, canonical in (("điện thoại", "phone"), ("số điện thoại", "phone"),
                                      ("hồ sơ", "profile"), ("cập nhật", "update")):
                normalized = normalized.replace(phrase, canonical)
            return {t for t in re.findall(r"[\wÀ-ỹ]{4,}", normalized) if t not in {"build", "release", "version", "update"}}
        for release in releases:
            terms = terms_for(release.text)
            matched = []
            for card in cards:
                card_terms = terms_for(card.title + " " + card.description)
                overlap = sorted(terms & card_terms)
                if overlap:
                    matched.append({"task_id": card.task_id, "matching_terms": overlap, "inclusion_in_build": "CHƯA THỂ XÁC MINH"})
            out.append({"release_id": release.release_id, "related_cards": matched,
                        "smoke_test": "Review release notes; run smoke tests for explicitly mentioned flows.",
                        "regression": "CHƯA THỂ XÁC MINH: release note không tự chứng minh phạm vi regression."})
        return out

