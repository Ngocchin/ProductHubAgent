# VuaTho QA Daily Assistant

Read-only daily QA collection and reporting for Product Hub and Telegram. Python 3.12+, Playwright, Telethon, pytest.

## Current scope and safety

The project contains the reporting, deterministic QA checklist fallback, JSON history, CI, scheduled workflow, and read-only connector implementations. It does not claim live Product Hub or Telegram access until a valid logged-in browser state and authorized MTProto session are configured. The Product Hub collector scans visible board columns and fails closed if it cannot identify fields. It never changes card state or posts comments/messages. AI calls are disabled by default; no internal company data is sent to an external model.

## Local development

Install Python 3.12, then install the project with `pip install -e '.[test]'`. Install Chromium with `playwright install chromium`; run tests with `pytest`. Run a report with `python -m main`. Missing credentials produce a report labelled `CHƯA THỂ XÁC MINH` and non-zero exit status.

## GitHub Actions configuration

Open **Settings → Secrets and variables → Actions** in the private repository.

Repository secrets (never commit their values): `PRODUCT_HUB_STORAGE_STATE` (the JSON storage-state document), `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_SESSION`. Repository variables: `PRODUCT_HUB_URL`, `TELEGRAM_CHAT_TITLE`, `TELEGRAM_CHAT_ID`. The currently open, verified `[DEV] VuaTho Mobile` chat is `-1002593712725`.

The daily workflow starts at 07:30 Vietnam time (00:30 UTC), supports **Actions → Daily QA report → Run workflow**, retries collection up to three times, and commits generated reports plus `reports/history.json`. GitHub scheduler timing is not guaranteed to finish before 08:00.

## Authentication setup status

Product Hub requires an authorized read-only account. The workflow materializes the JSON browser `storage_state` from a GitHub secret into an ignored temporary file. Telegram requires an authorized MTProto session and the exact chat ID. Never send OTP, password, session, or API hash in chat, reports, or logs. The Windows wizard handles local session enrollment; a person must still paste the copied values into GitHub's Secret editor because the connected GitHub API cannot create repository secrets.

## Windows setup wizard

The `Build Windows setup wizard` workflow packages a click-to-run `VuaThoQASetup.exe` artifact. In GitHub, open **Actions → Build Windows setup wizard → Run workflow**, then download the `VuaThoQASetup-Windows` artifact from that run and open the `.exe` inside its ZIP. The wizard opens Chrome for a user-driven Product Hub login, captures the browser state in memory, and handles Telegram OTP/2FA only inside the local window. It verifies Telegram chat `-1002593712725` and provides separate copy buttons for the GitHub Secrets. It does not write credentials to disk or logs.

After setup, open **Settings → Secrets and variables → Actions** and add secrets `PRODUCT_HUB_STORAGE_STATE`, `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, and `TELEGRAM_SESSION`. Add repository variable `TELEGRAM_CHAT_ID=-1002593712725`. Then open **Actions → Daily QA report → Run workflow**.

## Repository contents

See `src/agents` for Product Hub, Telegram, QA analysis and report agents; `src/storage` for daily history; `.github/workflows` for CI and scheduled runs; `tests` for connector safety, analysis, history, and report tests.
