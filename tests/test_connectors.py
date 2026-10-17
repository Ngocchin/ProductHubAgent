import pytest
from agents.product_hub import ProductHubAgent, ProductHubUnavailable
from agents.telegram_release import TelegramReleaseAgent, TelegramUnavailable


@pytest.mark.asyncio
async def test_product_hub_fails_closed_without_login_state(tmp_path):
    agent = ProductHubAgent(storage_state=str(tmp_path / "missing.json"))
    with pytest.raises(ProductHubUnavailable, match="CHƯA THỂ XÁC MINH"):
        await agent.collect()


@pytest.mark.asyncio
async def test_telegram_requires_verified_chat_id():
    agent = TelegramReleaseAgent(api_id="1", api_hash="hash", session="session", chat_id=None)
    with pytest.raises(TelegramUnavailable, match="TELEGRAM_CHAT_ID"):
        await agent.collect()
