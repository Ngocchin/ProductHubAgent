import asyncio
import base64
import json
import threading

import pytest
from nacl.public import PrivateKey, SealedBox

from setup.async_utils import submit_coroutine
from setup.github_config import GitHubRepoConfigurator, GitHubSetupError, encrypt_secret
from setup.product_hub_enrollment import verify_board_page
from setup import windows_wizard
import windows_setup


def test_submit_coroutine_requires_the_called_async_method():
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()

    class Example:
        async def load(self):
            return "loaded"

    try:
        example = Example()
        with pytest.raises(TypeError, match="call the async method"):
            submit_coroutine(loop, example.load)
        assert submit_coroutine(loop, example.load()).result(timeout=2) == "loaded"
    finally:
        loop.call_soon_threadsafe(loop.stop)
        thread.join(timeout=2)
        loop.close()


def test_self_test_entrypoint_does_not_create_tk_window(monkeypatch):
    def fail_if_gui_starts(*_args, **_kwargs):
        raise AssertionError("self-test must not create the Tk interface")

    monkeypatch.setattr(windows_wizard.SetupWizard, "__init__", fail_if_gui_starts)
    assert windows_setup.main(["--self-test"]) == 0


def test_self_test_verifies_extension_package_and_scoped_host_permission():
    windows_setup.verify_extension_bundle()


def test_product_hub_board_must_be_verified_before_session_capture():
    verify_board_page(
        "https://product-hub.vuatho.com/board",
        "Project board Ready for QA Verifying",
    )
    with pytest.raises(RuntimeError, match="chưa được xác minh|chưa mở đúng"):
        verify_board_page("https://product-hub.vuatho.com/login", "Email password")


def test_github_secret_encryption_uses_sealed_box():
    private_key = PrivateKey.generate()
    public_key = base64.b64encode(bytes(private_key.public_key)).decode("ascii")
    encrypted = encrypt_secret(public_key, "private-session-value")
    decrypted = SealedBox(private_key).decrypt(base64.b64decode(encrypted))
    assert decrypted.decode() == "private-session-value"
    assert "private-session-value" not in encrypted


def test_configurator_encrypts_secrets_and_verifies_names_only():
    private_key = PrivateKey.generate()
    public_key = base64.b64encode(bytes(private_key.public_key)).decode("ascii")
    secret_values = {"TELEGRAM_SESSION": "session-private", "TELEGRAM_API_HASH": "hash-private"}
    variable_values = {"TELEGRAM_CHAT_ID": "-1002593712725"}
    seen_secrets = {}
    seen_variables = {}

    class Response:
        def __init__(self, value):
            self.value = json.dumps(value).encode()

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return self.value

    def opener(request, timeout):
        assert timeout == 30
        if request.method == "GET" and request.full_url.endswith("/repos/Ngocchin/ProductHubAgent"):
            return Response({"full_name": "Ngocchin/ProductHubAgent"})
        if request.method == "GET" and request.full_url.endswith("/actions/secrets/public-key"):
            return Response({"key": public_key, "key_id": "key-id"})
        if request.method == "PUT" and "/actions/secrets/" in request.full_url:
            name = request.full_url.rsplit("/", 1)[-1]
            payload = json.loads(request.data)
            assert payload["key_id"] == "key-id"
            seen_secrets[name] = SealedBox(private_key).decrypt(base64.b64decode(payload["encrypted_value"])).decode()
            return Response({})
        if request.method == "POST" and request.full_url.endswith("/actions/variables"):
            payload = json.loads(request.data)
            seen_variables[payload["name"]] = payload["value"]
            return Response({})
        if request.method == "PATCH" and "/actions/variables/" in request.full_url:
            payload = json.loads(request.data)
            seen_variables[payload["name"]] = payload["value"]
            return Response({})
        if request.method == "GET" and request.full_url.endswith("/actions/secrets?per_page=100"):
            return Response({"secrets": [{"name": name} for name in seen_secrets]})
        if request.method == "GET" and request.full_url.endswith("/actions/variables?per_page=100"):
            return Response({"variables": [{"name": name} for name in seen_variables]})
        raise AssertionError(f"Unexpected request: {request.method} {request.full_url}")

    result = GitHubRepoConfigurator("one-time-token", opener=opener).configure(secret_values, variable_values)
    assert seen_secrets == secret_values
    assert seen_variables == variable_values
    assert result == {"secrets": sorted(secret_values), "variables": sorted(variable_values)}


def test_user_approved_report_upload_uses_contents_api_not_repository_secret():
    seen = []

    class Response:
        def __init__(self, value):
            self.value = json.dumps(value).encode()
        def __enter__(self): return self
        def __exit__(self, *_args): return False
        def read(self): return self.value

    def opener(request, timeout):
        seen.append(request)
        if request.method == "GET":
            return Response({"full_name": "Ngocchin/ProductHubAgent"})
        payload = json.loads(request.data)
        assert base64.b64decode(payload["content"]).decode() == "# Manual QA report\n"
        assert "actions/secrets" not in request.full_url
        return Response({"content": {"path": "reports/manual-sync/run-123/report.md", "html_url": "https://github.com/Ngocchin/ProductHubAgent/blob/main/reports/manual-sync/run-123/report.md"}})

    url = GitHubRepoConfigurator("token", opener=opener).upload_report_file(
        "reports/manual-sync/run-123/report.md", "# Manual QA report\n"
    )
    assert url.endswith("report.md")
    assert [request.method for request in seen] == ["GET", "PUT"]


def test_report_upload_rejects_paths_outside_manual_reports():
    with pytest.raises(GitHubSetupError, match="(?i)đường dẫn upload báo cáo"):
        GitHubRepoConfigurator("token").upload_report_file("reports/history.json", "data")
