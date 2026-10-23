# InterviewAce AI

A peer interview and solo AI practice application using **Python, FastAPI, MySQL, HTML, CSS and JavaScript**. Ollama, LangChain, LangGraph and optional Faster-Whisper run locally. No paid inference, compiler, email or video API is required.

## Run this configured workspace

Start Docker Desktop and Ollama, then run:

```powershell
./run.ps1
```

In CMD, use `run.cmd` from this directory. Both launchers detect an existing server instead of trying to bind port 8000 twice.

Open **http://127.0.0.1:8000**. The app now uses your PC's existing MySQL at **127.0.0.1:3306**, schema `interviewace`, as configured privately in `.env` (`LOCAL_MYSQL=0`). The earlier optional instance/data on port 3307 is preserved but is not the active application connection. Do not replace the configured `.env` with the example file.

Project-owned Docker and Hugging Face cache paths in `.env` are relative to this project folder (`./data/docker-cli` and `./data/huggingface`) and resolve from the current project root. Restart the app after editing `.env` so the process reloads its settings.

Health: `/api/live` checks the process; `/api/health` verifies MySQL connectivity. Interactive API documentation: `/docs`. Current application version: **3.3.0**.

## What is included

- First/last name, private international contact number, email, password confirmation and live password guidance.
- Argon2 password hashing, HttpOnly cookie browser sessions, CSRF/origin checks, idle/absolute expiry, password change/recovery and logout on all devices.
- Responsive candidate/interviewer dashboards with accessible forms, inline errors, offline notices and keyboard navigation.
- One shared navigation header/footer, Created by Zaman & Saloni credit, sharp text/native score bars, and a saved sun/moon theme with a pure black dark page and neutral gray surfaces.
- A persistent logged-in Home with separate AI Practice, Peer Rooms, History and Profile views. Room tabs separate live media, coding, shared files and reports.
- A labeled illustrated AI coach, optional installed-local-voice read-aloud, camera preview and consented local answer transcription. This is not a photorealistic human video generator.
- Custom AI interview focus and 1–50 questions, first-initial preview while the camera is off, accessible camera/microphone/power icons, and public Services, Contact, Terms and Privacy information.
- Two-person peer rooms, invitations and a server-controlled maximum 15-minute timer.
- WebSocket chat, read-only interviewer code view, shared results and direct WebRTC audio/video.
- Candidate-only Python execution and final submission in restricted Docker containers.
- Private PDF, DOCX, PPTX and image sharing; local page/slide/caption-grounded RAG drafts; one combined AI resume picker/uploader; resume assessment, consented speech metrics, human feedback, reports and history charts.
- Room deletion uses a five-second server-side undo window before the room and its shared files are permanently removed.
- Solo AI practice with adaptive LangGraph difficulty.
- Additive MySQL account migration, integrity-tested backups and recovery drills, health/monitoring endpoints, security headers, bounded throttling and deployment templates.

## Documentation

| Document | Contents |
| --- | --- |
| [Project guide](docs/PROJECT_GUIDE.md) | Architecture, all feature flows, validation, authentication, sessions, roles, scoring, storage, configuration and source map |
| [Operations guide](docs/OPERATIONS.md) | Installation, startup, migrations, backup/recovery, monitoring, troubleshooting, deployment, durability and scaling limits |
| [API reference](docs/API.md) | Generated routes, authorization requirements, request models and validation limits |
| [Data dictionary](docs/DATA_DICTIONARY.md) | Generated tables, columns, types, indexes and foreign keys |
| [Requirements mapping](docs/requirements.md) | PDF features and substitutions required by the specified technology stack |
| [Validation record](docs/validation.md) | Actual test results, live checks, fixes, cleanup and remaining verification limits |
| [PC MySQL connection](docs/MYSQL.md) | Exact local connection details and MySQL Workbench instructions, without exposing passwords |
| [Website dry run](docs/DRY_RUN.md) | Current browser/API results, which mode to choose, editor roles and device permission troubleshooting |
| [Vercel + PC backend](docs/VERCEL_PC_BACKEND.md) | Static Vercel frontend, Tailscale Funnel, private PC configuration, generated routes and live deployment checks |

## Verification commands

```bat
.venv\Scripts\python.exe -B -m pytest tests -q -p no:cacheprovider
.venv\Scripts\python.exe -B -m backend.verify_mysql
.venv\Scripts\python.exe -B -m backend.verify_accounts_browser
.venv\Scripts\python.exe -B -m backend.verify_theme_browser
.venv\Scripts\python.exe -B -m backend.verify_studio_browser
.venv\Scripts\python.exe -B -m backend.verify_browser
.venv\Scripts\python.exe -B -m backend.verify_runtime
node --check frontend\app.js
node --check frontend\peer.js
node --check frontend\solo.js
node --check frontend\media.js
node --check frontend\theme.js
```

The first command uses disposable SQLite; the second uses a new isolated **real MySQL** database. Neither uses application records as test fixtures. Browser checks require Chrome and `backend/requirements-browser.txt`. Runtime checks need Ollama, Docker and the application running. Speech verification uses the included generated `data/speech-sample.wav`. Browser media tests use synthetic devices; physical hardware and remote-network compatibility need manual checks.

Generate up-to-date API/schema documentation with `.venv/Scripts/python.exe -B -m backend.document` while the server is running.

## Fresh installation

See [Operations guide](docs/OPERATIONS.md). Install Python 3.11/3.12, MySQL Community Server, Ollama and a Docker-compatible engine. Create a virtual environment and install `backend/requirements.txt`, optional `backend/requirements-speech.txt`, `backend/requirements-test.txt` for API tests, and `backend/requirements-browser.txt` for browser checks. In this workspace, use `uv --cache-dir .uv-cache pip install --python .venv/Scripts/python.exe -r <file>` because pip is not installed in the existing virtual environment.

`requirements-lock-windows.txt` records exact packages from the verified Windows/Python 3.12 environment; it includes browser-testing and speech dependencies and is not a cross-platform lock.

## Deployment scope

The current build is a verified **single-process local application**, with durable MySQL storage and recoverable backups. A Vercel static frontend with the FastAPI backend, database, Ollama and Docker kept on a PC can be configured with [the deployment guide](docs/VERCEL_PC_BACKEND.md). This requires the PC to stay online and exposes the app through a public HTTPS tunnel. Redundant hosting, database replication/failover, external uptime monitoring and a reviewed public code runner are still infrastructure tasks; this repository does not claim an HA service or a public security certification. HTTPS reverse-proxy and restart-service templates are provided under `deploy/`.
