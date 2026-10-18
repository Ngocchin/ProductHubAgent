# VuaTho QA Daily Assistant

Read-only daily QA collection and reporting for Product Hub and Telegram. Python 3.12+, Playwright, Telethon, pytest.

## Current scope and safety

The project contains the reporting, deterministic QA checklist fallback, JSON history, CI, scheduled workflow, and read-only connector implementations. Product Hub cloud collection is explicitly blocked pending verified admin-issued API access. Manual browser snapshots use the Chrome Extension. Telegram requires an authorized MTProto session. The project never changes card state or posts comments/messages. AI calls are disabled by default; no internal company data is sent to an external model.

## Local development

Install Python 3.12, then install the project with `pip install -e '.[test]'`. Install Chromium with `playwright install chromium`; run tests with `pytest`. Run a report with `python -m main`. Missing credentials produce a report labelled `CHƯA THỂ XÁC MINH` and non-zero exit status.

## GitHub Actions configuration

Open **Settings → Secrets and variables → Actions** in the private repository.

The Windows wizard creates Telegram secrets and chat variables. Product Hub browser storage is no longer collected by the wizard. The Chrome Extension exports a user-selected JSON snapshot locally. The wizard validates it and writes a Markdown report and JSON payload into a new, timestamped local folder. It can optionally upload those report files into `reports/manual-sync/` after an explicit confirmation; that requires Contents: Read and write. It does not store snapshots in GitHub Secrets.

The daily workflow remains scheduled at 07:30 Vietnam time (00:30 UTC), but Product Hub cloud collection now fails closed and labels the source BLOCKED until an administrator-approved server integration is implemented. Extension snapshots are not consumed by this workflow. GitHub scheduler timing is not guaranteed to finish before 08:00.

## Authentication setup status

Product Hub API access has not been verified: no public API contract is accessible, and no administrator-issued integration credentials are available in this repository. Therefore cloud automation while the PC is off is **BLOCKED**. Do not configure speculative endpoints. The Extension mode runs only while Chrome and the user's PC are available. It reads visible board/detail fields from both columns, filters QA exactly equal to `Chin`, and exports JSON locally; it never reads cookies, session tokens, Google credentials, or OTP. It does not fetch linked documents; it records same-origin links when visible. Manual reports generate checklists only from explicit acceptance criteria; comments remain context, and tests are never marked PASS. Telegram requires an authorized MTProto session and the exact chat ID. Never send OTP, password, session, or API hash in chat, reports, or logs.

## Windows setup wizard

The `Build Windows setup wizard` workflow packages a click-to-run `VuaThoQASetup.exe` artifact with the extension included. In GitHub, open **Actions → Build Windows setup wizard → Run workflow**, then download the `VuaThoQASetup-Windows` artifact. The wizard opens normal Chrome (not Playwright) and helps install the read-only extension from a local folder. In `chrome://extensions`, enable Developer mode and choose **Load unpacked**. Log in to Product Hub yourself in regular Chrome, then use the extension's Connect, Verify, and Sync & Export JSON controls. Use **Verify JSON** and **Create Local QA Report** in the wizard to make a timestamped report folder without overwriting report history. **Upload Saved Report** optionally sends the Markdown and JSON files to the private repo after confirmation; enable **Contents: Read and write** on the fine-grained token for this. Telegram OTP/2FA stays inside the local window; it verifies the exact chat ID/title and reads a real recent message before accepting the session. Existing GitHub secret/variable setup remains available.

In the wizard, use **Connect GitHub**, **Connect Product Hub**, **Connect Telegram**, **Test Telegram**, then **Save Configuration**. Use **Run QA Report** only to see the current cloud status; it remains BLOCKED until Product Hub admin issues a verified server-side integration.

## Repository contents

See `src/agents` for Product Hub, Telegram, QA analysis and report agents; `src/storage` for daily history; `.github/workflows` for CI and scheduled runs; `tests` for connector safety, analysis, history, and report tests.
