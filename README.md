# VuaTho QA Daily Assistant

Read-only daily QA collection and reporting for Product Hub and Telegram. Python 3.12+, Playwright, Telethon, pytest.

## Current scope and safety

The project contains the reporting, deterministic QA checklist fallback, JSON history, CI, scheduled workflow, and read-only connector implementations. It does not claim live Product Hub or Telegram access until a valid logged-in browser state and authorized MTProto session are configured. The Product Hub collector scans visible board columns and fails closed if it cannot identify fields. It never changes card state or posts comments/messages. AI calls are disabled by default; no internal company data is sent to an external model.

## Local development

Install Python 3.12, then install the project with `pip install -e '.[test]'`. Install Chromium with `playwright install chromium`; run tests with `pytest`. Run a report with `python -m main`. Missing credentials produce a report labelled `CHƯA THỂ XÁC MINH` and non-zero exit status.

## GitHub Actions configuration

Open **Settings → Secrets and variables → Actions** in the private repository.

The Windows wizard can create/update repository secrets `PRODUCT_HUB_STORAGE_STATE`, `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_SESSION` and variables `PRODUCT_HUB_URL`, `TELEGRAM_CHAT_TITLE`, `TELEGRAM_CHAT_ID`. It encrypts each secret with the GitHub-provided public key and verifies only the configured names afterward. Secret values are never read back.

The daily workflow starts at 07:30 Vietnam time (00:30 UTC), supports **Actions → Daily QA report → Run workflow**, retries collection up to three times, and commits generated reports plus `reports/history.json`. GitHub scheduler timing is not guaranteed to finish before 08:00.

## Authentication setup status

Product Hub requires an authorized read-only account. The workflow materializes the JSON browser `storage_state` from a GitHub secret into an ignored temporary file. Telegram requires an authorized MTProto session and the exact chat ID. Never send OTP, password, session, or API hash in chat, reports, or logs.

## Windows setup wizard

The `Build Windows setup wizard` workflow packages a click-to-run `VuaThoQASetup.exe` artifact. In GitHub, open **Actions → Build Windows setup wizard → Run workflow**, then download the `VuaThoQASetup-Windows` artifact from that run and open the `.exe` inside its ZIP. The wizard opens Chrome for a user-driven Product Hub login and only captures browser state after verifying the board. Telegram OTP/2FA stays inside the local window; it verifies the exact chat ID/title and reads a real recent message before accepting the session. GitHub setup uses a fine-grained token scoped to this repository with **Secrets: Read and write**, **Variables: Read and write**, and **Actions: Read and write** for triggering a report (metadata read is automatic). The token is entered in a masked field, held in memory only, and removed after configuration/run or when the wizard closes. GitHub secrets are encrypted with GitHub's public key before transmission. The wizard does not write credentials to disk or logs.

In the wizard, use **Connect GitHub**, **Connect Product Hub**, **Test Product Hub**, **Connect Telegram**, **Test Telegram**, then **Save Configuration**. For a first report, click **Run QA Report**; if the one-time token has already been cleared, GitHub Actions opens and you can click **Run workflow**. Use **View Report** to open `reports/latest.md`.

## Repository contents

See `src/agents` for Product Hub, Telegram, QA analysis and report agents; `src/storage` for daily history; `.github/workflows` for CI and scheduled runs; `tests` for connector safety, analysis, history, and report tests.
