import pytest
from agents.product_hub import ProductHubAgent, ProductHubUnavailable
from agents.telegram_release import TelegramReleaseAgent, TelegramUnavailable


@pytest.mark.asyncio
async def test_product_hub_cloud_collection_requires_verified_server_integration(tmp_path):
    agent = ProductHubAgent(storage_state=str(tmp_path / "legacy-state.json"))
    with pytest.raises(ProductHubUnavailable, match="BLOCKED.*API/integration server-side"):
        await agent.collect()


@pytest.mark.asyncio
async def test_telegram_requires_credentials():
    agent = TelegramReleaseAgent(chat_id=-1002593712725)
    with pytest.raises(TelegramUnavailable, match="credentials"):
        await agent.collect()


def test_empty_chat_id_variable_uses_verified_default(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "")
    agent = TelegramReleaseAgent(api_id="1", api_hash="test", session="test")
    assert agent.chat_id == -1002593712725
