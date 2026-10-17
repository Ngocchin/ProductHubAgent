# VuaTho QA Daily Assistant

Read-only daily QA collection and reporting for Product Hub and Telegram. Python 3.12+, Playwright, Telethon, pytest.

## Current scope and safety

The project contains the reporting, deterministic QA checklist fallback, SQLite history, CI, scheduled workflow, and read-only connector implementations. It does not claim live Product Hub or Telegram access until a valid logged-in browser state and a verified Telegram chat ID are configured. The Product Hub collector uses configurable DOM selectors and will fail closed if it cannot identify board columns. It never changes card state or posts comments/messages. AI calls are disabled by default; no internal company data is sent to an external model.

## Local development

Install Python 3.12, then install the project with `pip install -e '.[test]'`. Install Chromium with `playwright install chromium`; run tests with `pytest`. Run a report with `python -m main`. Missing credentials produce a report labelled `CHƯA THỂ XÁC MINH` and non-zero exit status.

## GitHub Actions configuration

Open **Settings → Secrets and variables → Actions** in the private repository.

Repository secrets (never commit their values): `PRODUCT_HUB_STORAGE_STATE` (the JSON storage-state document), `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_SESSION`. Repository variables: `PRODUCT_HUB_URL`, `TELEGRAM_CHAT_TITLE`, `TELEGRAM_CHAT_ID`. The currently open, verified `[DEV] VuaTho Mobile` chat is `-1002593712725`.

The daily workflow starts at 07:30 Vietnam time (00:30 UTC), supports **Actions → Daily QA report → Run workflow**, retries collection up to three times, and commits generated reports plus `reports/history.json`. GitHub scheduler timing is not guaranteed to finish before 08:00.

## Authentication setup status

Product Hub requires an authorized read-only account. The workflow materializes the JSON browser `storage_state` from a GitHub secret into an ignored temporary file; the secret must be obtained through a trusted local login flow. Telegram requires an authorized MTProto session and the exact chat ID. Never send OTP, password, session, or API hash in chat, reports, or logs. This initial delivery does not include a Windows GUI enrollment utility; secure session enrollment and protected runner provisioning remain production setup work.

## Repository contents

See `src/agents` for Product Hub, Telegram, QA analysis and report agents; `src/storage` for daily history; `.github/workflows` for CI and scheduled runs; `tests` for connector safety, analysis, history, and report tests.
