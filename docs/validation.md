# Validation record — 24 October 2026

## Latest end-to-end verification — backend 3.3.0

The current source was rechecked against the configured live services on 24 October 2026. The existing automated, browser and runtime checks passed:

| Area | Result |
| --- | --- |
| Disposable SQLite API/security suite | **77 passed** |
| Isolated real MySQL API/security suite | **77 passed**; test database removed afterward |
| Chrome account and theme checks | Passed, including mobile/desktop layouts, login, profile, theme persistence and score history |
| Chrome studio check | Passed, including custom AI setup, generated question, answer evaluation/report, media controls and speech transcription |
| Chrome peer-room check | Passed, including two-person WebRTC, synthetic camera/audio, chat, shared code, Docker submission and reports |
| Live integration | Passed MySQL operations, local Ollama embeddings/RAG, LangGraph solo question/evaluation, restricted Docker execution and consented Faster-Whisper transcription |

The speech check used the locally cached Hugging Face `Systran/faster-whisper-tiny.en` model and completed real transcription. A separate clean-cache check downloaded `tiny.en` from Hugging Face Hub into a temporary directory and transcribed the included audio sample (35 words); the temporary cache was removed. This verifies Hub download and model inference from the current environment. The AI checks exercised real local model responses, not mocked responses.

The first fresh peer-browser run hit an intermittent empty-frame issue with Chrome's default synthetic camera. The browser verifier now supplies a deterministic local Y4M camera clip; the rerun passed video/audio, signaling, chat, code, Docker submission and reports. This is a test-media stabilization, not a change to production WebRTC behavior.

The stale absolute `DOCKER_CONFIG` and `HF_HOME` values were changed to project-relative paths so they resolve from the project root after a move. Fresh-process checks confirmed both paths; isolated Docker code execution passed with the resolved Docker config directory, and offline Faster-Whisper transcription passed with the resolved local model cache. Other `.env` values, including MySQL and secrets, were preserved.

After relocation, startup exposed an unescaped `@` in the MySQL password URL, which made the remainder of the password look like the hostname. The reserved character is now URL-encoded as `%40`, and `.venv/pyvenv.cfg` points to this project's bundled Python runtime. A real `SELECT 1` connection check passed; `run.cmd` started successfully and `/api/health` returned HTTP 200. This follow-up verifies startup and database connectivity; it does not rerun the full browser or AI-generation suites.

Automated browser media uses synthetic devices. I also attempted physical capture in both headless and visible Chrome. Chrome enumerated camera/microphone devices, but Windows returned `NotAllowedError: Permission denied by system` for both capture requests; no audio/video was recorded or uploaded. Physical capture therefore remains unverified until Windows privacy settings allow desktop-app access and the check is rerun. Connections across external networks/NAT were not tested; this local configuration has no STUN/TURN server and does not promise traversal through restrictive firewalls. The local site and configured integrations passed the checks above; those results do not guarantee every physical device, browser extension or remote network setup.

## Historical validation record — backend 3.2.0

The following notes record prior feature work and historical runtime snapshots. Their version-specific figures describe those earlier runs, not the current 3.3.0 verification above.

## Custom AI setup, initial preview, icons and public footer

Added Custom interview type (3–100 printable characters) and Custom question count (whole numbers 1–50). The custom type is persisted in a nullable MySQL `custom_kind` column and passed through question generation and evaluation. The migration preserves existing records and can run repeatedly. A verified SQL/upload backup was created before applying it to the PC database.

The updated suites passed **77 tests against isolated MySQL** and **77 tests against disposable SQLite**. New checks cover custom type persistence, propagation into each AI call, two-question completion, count boundaries, invalid counts/types, malformed custom descriptions, stale-value handling and idempotent legacy schema upgrade. API and data dictionary references were regenerated; the new column was also verified on the live MySQL schema.

The camera-off preview uses the first-name initial, including after profile updates. Device buttons use labeled SVG icons, state/slash indicators and keyboard focus. The public footer opens real Services, Contact, Terms and Privacy sections; only the approved support email is published. Account and theme browser checks passed again, including the public footer links, responsive public pages and the updated profile initial.

The updated studio browser run also passed: custom fields and invalid count handling, retained custom type/count on the live API, initial/camera visibility, icon on/off/shutdown state, 320–1440px layouts, real local AI question generation, consented recording and Whisper transcription, answer review, real evaluation/report, missing-camera/audio fallback and permission-denial instructions. The AI studio screenshot was visually reviewed. Peer/editor captures and solo media run in separate browser instances because Chrome's synthetic video device disappeared after the captured peer preview was hidden; this test-device issue is recorded rather than treated as evidence about physical hardware. A separate live browser probe passed the peer-to-solo camera transition without those captures. Physical camera/microphone permissions still depend on the user's PC.

## Merged navigation, sharp history scores and black theme

Removed the separate studio navigation bar and placed all five member page links in the shared header. Home remains selected after login/reload and each destination updates `aria-current`. Mobile uses two rows inside the same header.

Replaced the stretched canvas with normal text and native HTML meter bars, including a readable empty state. The old bitmap could be drawn at a hidden panel's fallback width and stretched when revealed. The replacement needs no hidden-panel measurement, pixel-ratio scaling or theme redraw. Black mode now uses a pure black page/header, neutral gray surfaces and controls, and matching browser theme-color metadata.

Reran `backend.verify_theme_browser` and `backend.verify_accounts_browser`: both passed. Checks cover guest/member layouts, all five header links, history empty state, mocked populated scores of 0/73.5/100 and missing assessments, standard/retina screens, 320/390/768/980/1024/1440 pixel widths, no horizontal overflow or clipped header links, neutral dark backgrounds, contrast, keyboard toggle, persistence, cross-tab/OS preferences, blocked storage, registration, private cookies, profile updates and logout. JavaScript syntax checks passed for all three changed scripts. Desktop/mobile history screenshots were visually reviewed (`data/history-light-1440.png`, `history-dark-1440.png`, `history-light-390.png`, `history-dark-390.png`). Synthetic score responses are browser fixtures only; no sample interviews were inserted into MySQL.

The API/database suites recorded below belong to the previous full dry run; no backend/database implementation changed in this UI correction.

## Logged-in Home, editor and media corrections

Home now remains available after login/refresh; studios/history/profile are separate pages; room content uses tabs; the invitation URL is collapsed; and contact help text is shortened. Camera/mic setup and signaling work before session start while chat/code mutations still require an active session.

The current full dry run passed on PC MySQL **127.0.0.1:3306**. **61 MySQL tests and 61 SQLite tests passed.** Browser tests verified decoded remote video frames and live audio tracks on both peers before the timer started, visible role-aware editors, real Docker submission/results, PDFs/RAG review navigation, mobile room layouts, missing-camera/audio-only fallback and denied-device instructions. Solo testing covered the illustrated AI coach, local read-aloud/fallback, actual recorded-answer transcription, review-before-submit, real AI evaluation and report. Runtime RAG/resume/speech/graph integration also passed.

`docs/DRY_RUN.md` provides the steps and explicit hardware/network limits. Test media is synthetic; physical devices/permissions still need local checking. AI presence is a labeled animated illustration, not a photorealistic human video generator. `run.cmd` duplicate-server detection was verified without starting another server.

## Header, footer and theme update

Shared navigation/header and responsive footer now surround every application view. Footer credit is **Created by Zaman & Saloni**. The new dedicated Chrome check passed light/dark layouts at 1440, 768, 390 and 320 pixels, keyboard toggle, saved preference after reload, OS preference, explicit override, cross-tab synchronization, storage-blocked fallback, privacy-link expansion, authenticated mobile history navigation and a normal-text contrast check. No JavaScript page errors were observed. The existing account browser checks also passed after the page-chrome changes.

Screenshots: `data/theme-light-1440.png`, `theme-dark-1440.png`, `theme-light-390.png`, `theme-dark-390.png`. The native PC MySQL connection was reconfirmed by actual SQL; Workbench details are in MYSQL.md. No credentials were copied into documentation and no unrelated MySQL80 records were modified.

## Runtime snapshot from the 3.2.0 validation run

- FastAPI v3.2.0 running at http://127.0.0.1:8000.
- `/api/health`: `status: ok`, `database: mysql`, `version: 3.2.0`; performs an actual database query.
- Twelve MySQL tables on the configured PC MySQL80 instance at 127.0.0.1:3306. Unrelated databases remain unchanged; prior optional 3307 data is retained.
- Verified native MySQL durability settings: `innodb_flush_log_at_trx_commit=1`, `sync_binlog=1`. This does not replace backups or protect against disk loss.
- Existing users received the additive first/last/contact migration without record deletion. A checksummed backup was taken before migration and restored successfully in an isolated drill.

## Automated results

| Check | Final result |
| --- | --- |
| Real MySQL API/security/validation suite | **61 passed** |
| Disposable SQLite suite | **61 passed** |
| JavaScript syntax, app.js and peer.js | Passed |
| Python compilation | Passed |
| HTML identifiers and referenced controls | No duplicate/missing IDs |
| Local stylesheet/script/favicon responses | Passed |
| README and documentation relative links | Passed |
| Generated API/data dictionary | Refreshed from current v3 app/schema |

The suites cover name/contact/password boundaries, weak passwords, confirmation, case-insensitive duplicate email, rejected-input privacy, Argon2 storage, cookie flags, CSRF/origin and trusted-host checks, idle expiry, tampering, logout/logout-all, password change/reset, ownership, throttling, security/cache headers, monitoring privacy, safe DB errors, independent liveness, additive migration, corrupt/unsafe backup rejection, room roles/capacity/timer expiry, background expiry, draft privacy, PDFs, coding, report formulas and consent. Server-generated WebSocket ticks are tested not to extend idle sessions.

MySQL tests create a uniquely named `interviewace_test_` database and remove it afterwards. Application data is never substituted for a test database. SQLite tests use a disposable file. All API test bodies are synthetic.

## Real-browser checks

Chrome registration layout passed at **1440, 768, 390 and 320 pixels**, with no horizontal overflow. Verified inline invalid-phone/weak-password feedback, confirmation mismatch, five-rule password guidance, show/hide, successful registration, recovery dialog, HttpOnly/SameSite cookie properties, absence of stored browser JWT, refresh persistence, profile editing and logout. No JavaScript page errors were observed.

Two isolated Chrome contexts passed login, both dashboards, room creation/join, candidate/interviewer code permissions, live timer, bidirectional chat, interviewer questions, WebRTC signaling/connection with **synthetic** media, code synchronization, actual Docker final submission, shared results, human feedback and final reports. Cookie-backed browser WebSocket authentication was exercised.

Screenshots in ignored `data/`: `register-1440.png`, `register-390.png`, `interviewer-verified.png`, `candidate-verified.png`. These are test artifacts, not hosted assets.

## Real service/integration checks

- MySQL-backed registration, room create/join, PDF extraction and resume quality assessment passed.
- Actual local Nomic embeddings and LangChain/Qwen RAG returned question/answer drafts with page references; candidate access filtered private drafts.
- Actual restricted Docker Python execution passed both supplied tests, persisted the final submission and populated the report.
- Actual Faster-Whisper decoded/transcribed the generated English WAV and produced speech metrics. Raw test uploads were deleted after processing.
- Human feedback and combined available-component scores passed.
- Actual LangGraph solo question generation and AI evaluation completed the interview.
- Live verification accounts, their rooms and owned PDFs were removed in finally cleanup.

## Backup and recovery rehearsal

The pre-migration archive restored into an isolated database with 11 original tables. A post-migration rehearsal created a synthetic shared PDF, archived SQL and uploads, verified checksums, restored all 12 tables, validated/repointed the uploaded-file reference and removed the temporary target. Restored login sessions are invalidated. Application records and configuration were not replaced. A final clean-state archive was retained after deleting the verification account.

Backups remain under ignored `data/backups` and are preserved intentionally, including the pre-migration snapshot. For a consistent operating backup, quiesce writes as documented in OPERATIONS.md. A checksum is not a signature; restore only trusted archives.

## Resolved issues

1. Earlier real MySQL checks exposed single-precision timestamp rounding; timestamps use DOUBLE and timer tests pass on MySQL.
2. Earlier speech checks exposed a PyAV 19/Faster-Whisper decoder mismatch; compatible PyAV 16.1.0 is installed and requirements pin below 17.
3. Original full-name registration and browser sessionStorage tokens were replaced with validated split fields and server-tracked cookie sessions.
4. Validation responses now omit raw inputs, preventing rejected passwords from appearing in error JSON.
5. Browser room cleanup clears old reports/documents/code when changing rooms or logging out.
6. Server timer ticks no longer count as user session activity.
7. CSS was organized into readable base, room and theme files; test-only requirements were separated from runtime requirements.

## Cleanup performed

- Removed obsolete completed `model-download.log` and `model-retry.log`.
- Removed the old failed-browser `data/browser-check` profile/database/log artifacts.
- Removed the project `.pytest_cache` and backend/test `__pycache__` directories.
- Removed the empty restore-rehearsals folder after successful drills.
- Removed confirmed unused Python imports and separated test dependencies.

Preserved `.env`, installed Python/virtual environment, useful package/model caches, native MySQL files, original SQLite records, uploads, backups, active server/Ollama logs, current screenshots and all used source/verification/deployment files. No unrecognized user data was classified as garbage.

## Limits and remaining manual/infrastructure checks

These tests are risk-focused, not an assertion that every possible input or failure has been exhausted. Physical camera/microphone use, Firefox/Safari/other OS behavior, remote-network/TURN connectivity, formal accessibility/security audits and realistic sustained-load tests are not certified by these checks.

The running build is single-process local software, not a redundant HA deployment. Linux service/nginx templates and container restart/health settings are supplied but have not been installed publicly or exercised on a redundant cluster. Public HTTPS, failover/replication, protected offsite backups, alerting and a reviewed public execution service remain operator/infrastructure work. See OPERATIONS.md for the exact deployment boundary and recovery procedure.
