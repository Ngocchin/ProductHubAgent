from models.schemas import Card, Release
from agents.qa_intelligence import QAIntelligenceAgent


def card(**kwargs):
    base = dict(task_id="VT-1", title="Cập nhật hồ sơ", url="https://example.test/VT-1",
                status="Ready for QA", qa="Chin", description="Cho phép cập nhật số điện thoại.")
    base.update(kwargs)
    return Card(**base)


def test_analysis_is_evidence_grounded_and_not_a_pass():
    result = QAIntelligenceAgent().analyze(card())
    assert result["test_cases"]
    assert all(tc["source_requirement"] == "VT-1" for tc in result["test_cases"])
    assert all("PASS" not in tc["expected_result"] for tc in result["test_cases"])
    assert result["clarifications"]


def test_missing_description_requests_clarification():
    result = QAIntelligenceAgent().analyze(card(description=""))
    assert not result["test_cases"]
    assert result["clarifications"]


def test_release_impact_does_not_claim_build_inclusion():
    release = Release("r1", 42, "dev", 7, "2026-10-17", "Update phone profile API")
    result = QAIntelligenceAgent().analyze_release_impact([card()], [release])
    assert result[0]["related_cards"]
    assert result[0]["related_cards"][0]["inclusion_in_build"] == "CHƯA THỂ XÁC MINH"
