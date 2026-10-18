# VuaTho QA Daily Assistant

Read-only daily QA collection and reporting for Product Hub and Telegram. Python 3.12+, Playwright, Telethon, pytest.

## Current scope and safety

The project contains the reporting, deterministic QA checklist fallback, JSON history, CI, scheduled workflow, and read-only connector implementations. It does not claim live Product Hub or Telegram access until a valid logged-in browser state and authorized MTProto session are configured. The Product Hub collector scans visible board columns and fails closed if it cannot identify fields. It never changes card state or posts comments/messages. AI calls are disabled by default; no internal company data is sent to an external model.

## Local development

Install Python 3.12, then install the project with `pip install -e '.[test]'`. Install Chromium with `playwright install chromium`; run tests with `pytest`. Run a report with `python -m main`. Missing credentials produce a report labelled `CHƯA THỂ XÁC MINH` and non-zero exit status.

## GitHub Actions configuration

Open **Settings → Secrets and variables → Actions** in the private repository.

The Windows wizard creates Telegram secrets and chat variables. Product Hub browser storage is no longer collected by the wizard. The optional Chrome Extension exports a user-selected JSON snapshot; the wizard validates it and can upload it to the private repository as encrypted secret `PRODUCT_HUB_EXTENSION_SNAPSHOT` only after an explicit confirmation. That snapshot is not consumed by scheduled cloud jobs.

The daily workflow remains scheduled at 07:30 Vietnam time (00:30 UTC), but Product Hub cloud collection now fails closed and labels the source BLOCKED until an administrator-approved server integration is implemented. Extension snapshots are not consumed by this workflow. GitHub scheduler timing is not guaranteed to finish before 08:00.

## Authentication setup status

Product Hub API access has not been verified: no public API contract is accessible, and no administrator-issued integration credentials are available in this repository. Therefore cloud automation while the PC is off is **BLOCKED**. Do not configure speculative endpoints. The Extension mode runs only while Chrome and the user's PC are available. It reads visible board/detail fields, filters `Ready for QA` and `Verifying` cards with QA exactly `Chin`, and exports JSON locally; it never reads cookies, session tokens, Google credentials, or OTP. It does not fetch linked documents; it records same-origin links when visible. The wizard's separate GitHub Sync button moves that snapshot to a GitHub Secret only after a data transfer confirmation. Telegram requires an authorized MTProto session and the exact chat ID. Never send OTP, password, session, or API hash in chat, reports, or logs.

## Windows setup wizard

The `Build Windows setup wizard` workflow packages a click-to-run `VuaThoQASetup.exe` artifact with the extension included. In GitHub, open **Actions → Build Windows setup wizard → Run workflow**, then download the `VuaThoQASetup-Windows` artifact. The wizard opens normal Chrome (not Playwright) and helps install the read-only extension from a local folder. In `chrome://extensions`, enable Developer mode and choose **Load unpacked**. Log in to Product Hub yourself in regular Chrome, then use the extension's Connect, Verify, and Sync & Export JSON controls. Import the downloaded file in the wizard with **Verify JSON**. **Sync to GitHub** asks before transmitting card content and stores it in an encrypted GitHub Secret; that manual snapshot does not enable cloud scheduling. Telegram OTP/2FA stays inside the local window; it verifies the exact chat ID/title and reads a real recent message before accepting the session. GitHub setup uses a fine-grained token scoped to this repository with **Secrets: Read and write**, **Variables: Read and write**, and **Actions: Read and write** for triggering a report (metadata read is automatic). The token is entered in a masked field, held in memory only, and removed after configuration/run or when the wizard closes.

In the wizard, use **Connect GitHub**, **Connect Product Hub**, **Test Product Hub**, **Connect Telegram**, **Test Telegram**, then **Save Configuration**. For a first report, click **Run QA Report**; if the one-time token has already been cleared, GitHub Actions opens and you can click **Run workflow**. Use **View Report** to open `reports/latest.md`.

## Repository contents

See `src/agents` for Product Hub, Telegram, QA analysis and report agents; `src/storage` for daily history; `.github/workflows` for CI and scheduled runs; `tests` for connector safety, analysis, history, and report tests.
