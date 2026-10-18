"""GitHub repository secrets/variables setup. Secrets use GitHub's libsodium sealed-box API."""
from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from urllib.parse import quote

from nacl.public import PublicKey, SealedBox

REPOSITORY = "Ngocchin/ProductHubAgent"
API_BASE = "https://api.github.com"


class GitHubSetupError(RuntimeError):
    pass


def encrypt_secret(public_key_b64: str, value: str) -> str:
    """Encrypt a repository secret using GitHub's public key and libsodium sealed box."""
    try:
        public_key = PublicKey(base64.b64decode(public_key_b64, validate=True))
        encrypted = SealedBox(public_key).encrypt(value.encode("utf-8"))
    except Exception as exc:
        raise GitHubSetupError("Không thể mã hóa secret bằng public key GitHub.") from exc
    return base64.b64encode(encrypted).decode("ascii")


class GitHubRepoConfigurator:
    def __init__(self, token: str, repository: str = REPOSITORY, opener=None) -> None:
        if not token.strip():
            raise GitHubSetupError("Hãy nhập fine-grained token trong cửa sổ ứng dụng.")
        self._token = token.strip()
        self.repository = repository
        self._opener = opener or urllib.request.urlopen

    def _request(self, method: str, path: str, payload: dict | None = None) -> dict:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(
            f"{API_BASE}{path}", data=body, method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self._token}",
                "X-GitHub-Api-Version": "2022-11-28",
                **({"Content-Type": "application/json"} if body is not None else {}),
            },
        )
        try:
            with self._opener(request, timeout=30) as response:
                raw = response.read()
                if not raw:
                    return {}
                return json.loads(raw.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            messages = {
                401: "GitHub token không hợp lệ hoặc đã hết hạn.",
                403: "GitHub từ chối quyền. Token cần quyền tương ứng với thao tác: Secrets/Variables, Actions hoặc Contents: Read and write để tải báo cáo.",
                404: "Không thấy repository hoặc token chưa được cấp quyền vào repository này.",
            }
            raise GitHubSetupError(messages.get(exc.code, f"GitHub API trả lỗi HTTP {exc.code}.") ) from None
        except (urllib.error.URLError, TimeoutError):
            raise GitHubSetupError("Không kết nối được GitHub API. Kiểm tra mạng rồi thử lại.") from None
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}

    def verify_access(self) -> str:
        repo = self._request("GET", f"/repos/{self.repository}")
        if (repo.get("full_name") or "").casefold() != self.repository.casefold():
            raise GitHubSetupError("Không xác minh được đúng repository Ngocchin/ProductHubAgent.")
        return repo.get("full_name", self.repository)

    def configure(self, secrets: dict[str, str], variables: dict[str, str]) -> dict[str, list[str]]:
        self.verify_access()
        key = self._request("GET", f"/repos/{self.repository}/actions/secrets/public-key")
        public_key, key_id = key.get("key"), key.get("key_id")
        if not public_key or not key_id:
            raise GitHubSetupError("GitHub không trả public key để mã hóa secrets.")

        for name, value in secrets.items():
            encrypted_value = encrypt_secret(public_key, value)
            self._request("PUT", f"/repos/{self.repository}/actions/secrets/{name}", {
                "encrypted_value": encrypted_value,
                "key_id": key_id,
            })
            del encrypted_value
        current_variables = self._request("GET", f"/repos/{self.repository}/actions/variables?per_page=100").get("variables", [])
        current_variable_names = {item.get("name") for item in current_variables}
        for name, value in variables.items():
            if name in current_variable_names:
                self._request("PATCH", f"/repos/{self.repository}/actions/variables/{name}", {"name": name, "value": value})
            else:
                self._request("POST", f"/repos/{self.repository}/actions/variables", {"name": name, "value": value})

        secret_names = self._request("GET", f"/repos/{self.repository}/actions/secrets?per_page=100").get("secrets", [])
        variable_names = self._request("GET", f"/repos/{self.repository}/actions/variables?per_page=100").get("variables", [])
        present_secrets = {item.get("name") for item in secret_names}
        present_variables = {item.get("name") for item in variable_names}
        expected_secrets, expected_variables = set(secrets), set(variables)
        if not expected_secrets.issubset(present_secrets) or not expected_variables.issubset(present_variables):
            raise GitHubSetupError("GitHub đã nhận cấu hình nhưng chưa xác minh đủ tên secrets/variables.")
        return {"secrets": sorted(expected_secrets), "variables": sorted(expected_variables)}

    def dispatch_daily_report(self) -> None:
        self.verify_access()
        self._request("POST", f"/repos/{self.repository}/actions/workflows/daily-qa.yml/dispatches", {"ref": "main"})

    def upload_report_file(self, repository_path: str, content: str) -> str:
        """Upload a user-approved report file to a unique path in the private repo."""
        normalized = repository_path.replace("\\", "/")
        if (not normalized.startswith("reports/manual-sync/") or ".." in normalized.split("/")
                or not normalized.endswith(("/report.md", "/report.json"))):
            raise GitHubSetupError("Đường dẫn upload báo cáo không hợp lệ.")
        self.verify_access()
        encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
        result = self._request("PUT", f"/repos/{self.repository}/contents/{quote(normalized, safe='/')}", {
            "message": f"qa: add manual Product Hub snapshot report {normalized.rsplit('/', 1)[-1]}",
            "content": encoded,
            "branch": "main",
        })
        if result.get("content", {}).get("path") != normalized:
            raise GitHubSetupError("Không xác minh được đường dẫn báo cáo sau khi upload.")
        return result.get("content", {}).get("html_url", "")

