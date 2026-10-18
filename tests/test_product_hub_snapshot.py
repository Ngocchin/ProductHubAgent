import json

import pytest

from setup.product_hub_snapshot import ProductHubSnapshotError, validate_snapshot


def snapshot(card=None):
    return {
        "schema_version": 1,
        "source": "VuaTho QA Chrome Extension",
        "generated_at": "2026-10-18T00:00:00Z",
        "board_url": "https://product-hub.vuatho.com/board",
        "columns": ["Ready for QA", "Verifying"],
        "cards": [card or {"id": "VT-APP-123", "title": "Example", "status": "Ready for QA", "qa": "Chin"}],
    }


def test_valid_extension_snapshot_requires_real_board_and_qa_filter():
    assert validate_snapshot(json.dumps(snapshot()))["cards"][0]["qa"] == "Chin"


@pytest.mark.parametrize("change", [
    {"board_url": "https://evil.example/board"},
    {"columns": ["Ready for QA"]},
    {"cards": [{"id": "VT-APP-123", "title": "Example", "status": "Done", "qa": "Chin"}]},
    {"cards": [{"id": "VT-APP-123", "title": "Example", "status": "Verifying", "qa": "Someone else"}]},
])
def test_snapshot_rejects_unverified_source_or_unfiltered_cards(change):
    data = snapshot()
    data.update(change)
    with pytest.raises(ProductHubSnapshotError):
        validate_snapshot(json.dumps(data))


def test_extension_is_scoped_read_only_and_does_not_request_session_material():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "product-hub-extension"
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["host_permissions"] == ["https://product-hub.vuatho.com/*"]
    assert set(manifest["permissions"]) <= {"activeTab", "downloads", "storage"}
    source = "\n".join((root / name).read_text(encoding="utf-8") for name in ("content.js", "popup.js"))
    assert "QA=Chin" in source or 'qa !== "Chin"' in source
    assert "cookies" not in source and "localStorage" not in source and "sessionStorage" not in source
    assert "fetch(" not in source and "XMLHttpRequest" not in source


@pytest.mark.asyncio
async def test_cloud_product_hub_collector_is_blocked_without_verified_server_integration(tmp_path):
    from agents.product_hub import ProductHubAgent, ProductHubUnavailable

    storage = tmp_path / "legacy-state.json"
    storage.write_text('{"cookies": [], "origins": []}', encoding="utf-8")
    with pytest.raises(ProductHubUnavailable, match="BLOCKED.*API/integration server-side"):
        await ProductHubAgent(storage_state=str(storage)).collect()
