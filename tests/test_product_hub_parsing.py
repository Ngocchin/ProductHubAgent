from agents.product_hub import _column_status, _section


def test_column_status_uses_nearest_single_matching_column():
    assert _column_status(["Ready for QA\nVT-1\nVerifying", "Board"]) is None
    assert _column_status(["Ready for QA\n4 cards", "Ready for QA\nVerifying"]) == "Ready for QA"
    assert _column_status(["Verifying\nVT-2"]) == "Verifying"


def test_detail_sections_stop_at_the_next_named_section():
    text = "DESCRIPTION\nBody text\nACCEPTANCE CRITERIA\n1. Works\nREFERENCES\nNone"
    assert _section(text, "DESCRIPTION", ("ACCEPTANCE CRITERIA", "REFERENCES")) == "Body text"
    assert _section(text, "ACCEPTANCE CRITERIA", ("REFERENCES",)) == "1. Works"
