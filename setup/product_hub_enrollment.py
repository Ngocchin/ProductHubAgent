from __future__ import annotations

from urllib.parse import urlparse

PRODUCT_HUB_URL = "https://product-hub.vuatho.com/board"


def verify_board_page(url: str, visible_text: str) -> None:
    """Fail closed until the logged-in Product Hub board is visibly available."""
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "product-hub.vuatho.com" or not parsed.path.startswith("/board"):
        raise RuntimeError("Product Hub chưa mở đúng trang board; hãy đăng nhập và quay lại board.")
    text = " ".join((visible_text or "").casefold().split())
    if "ready for qa" not in text or "verifying" not in text:
        raise RuntimeError("Không tìm thấy cả hai cột Ready for QA và Verifying. Phiên đăng nhập hoặc cấu trúc board chưa được xác minh.")

