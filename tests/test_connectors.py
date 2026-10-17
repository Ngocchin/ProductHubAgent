import pytest
from agents.product_hub import ProductHubAgent, ProductHubUnavailable
from agents.telegram_release import TelegramReleaseAgent, TelegramUnavailable


@pytest.mark.asyncio
async def test_product_hub_fails_closed_without_login_state(tmp_path):
    agent = ProductHubAgent(storage_state=str(tmp_path / "missing.json"))
    with pytest.raises(ProductHubUnavailable, match="CHƯA THỂ XÁC MINH"):
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
