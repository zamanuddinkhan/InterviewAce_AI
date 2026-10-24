# InterviewAce AI

A peer interview and solo AI practice application using **Python, FastAPI, MySQL, HTML, CSS and JavaScript**. Ollama, LangChain, LangGraph and optional Faster-Whisper run locally. No paid inference, compiler, email or video API is required.

## Run this configured workspace

The commands below describe the maintainer's configured checkout. A fresh clone has no `.env`, local database, Ollama models, or uploaded data; follow [Fresh clone install guide](#fresh-clone-install-guide-windows-cmd) before starting it.

Start Docker Desktop and Ollama, then run:

```powershell
./run.ps1
```

In CMD, use `run.cmd` from this directory. Both launchers detect an existing server instead of trying to bind port 8000 twice.

Open **http://127.0.0.1:8000**. The app now uses your PC's existing MySQL at **127.0.0.1:3306**, schema `interviewace`, as configured privately in `.env` (`LOCAL_MYSQL=0`). The earlier optional instance/data on port 3307 is preserved but is not the active application connection. Do not replace the configured `.env` with the example file.

Project-owned Docker and Hugging Face cache paths in `.env` are relative to this project folder (`./data/docker-cli` and `./data/huggingface`) and resolve from the current project root. Restart the app after editing `.env` so the process reloads its settings.

Health: `/api/live` checks the process; `/api/health` verifies MySQL connectivity. Interactive API documentation: `/docs`. Current application version: **3.3.0**.

## Current deployment

**Website:** <https://interviewaceai-tau.vercel.app>

**PC backend:** `https://laptop-v0p0dfct.tail9221c5.ts.net`

Vercel hosts the static frontend from `frontend/`. Vercel forwards `/api/*` requests through Tailscale Funnel to the FastAPI server on the owner’s Windows PC. MySQL, Ollama models, Docker code execution, uploaded files, and the backend process remain on that PC; they are not hosted by Vercel.

This means the website’s pages can load while the PC backend is unavailable, but login, data, AI, rooms, uploads, and other API-backed features need the PC awake and online. Keep the PC connected to the internet, and do not let it sleep while the service is needed. This is a personal/demo setup, not always-on hosting.

### Start the deployed service (Windows CMD)

1. Make sure the MySQL Windows service is running. Start Ollama for AI features and Docker Desktop for code execution.
2. In a CMD window at the repository root, start the backend and leave this window open:

   ```bat
   run.cmd
   ```

3. Make sure the Tailscale Windows app is signed in and connected. In another CMD window, check Funnel status:

   ```bat
   "%ProgramFiles%\Tailscale\tailscale.exe" funnel status
   ```

   If it reports `No serve config` or Funnel is off, turn it on:

   ```bat
   "%ProgramFiles%\Tailscale\tailscale.exe" funnel --bg 8000
   ```

The configured Funnel sends public HTTPS traffic to `127.0.0.1:8000`. Do not expose MySQL port `3306`, Ollama port `11434`, or the Docker API to the internet. Do not configure router port forwarding for those services.

### Verify or stop access

Check the local backend and the public Vercel route:

```bat
curl.exe -i http://127.0.0.1:8000/api/health
curl.exe -i https://interviewaceai-tau.vercel.app/api/health
```

Both should return `status: ok` and `database: mysql`. To stop public backend access while leaving Vercel’s static frontend deployed, turn Funnel off:

```bat
"%ProgramFiles%\Tailscale\tailscale.exe" funnel --https=443 off
```

To stop the backend process, press **Ctrl+C** in the CMD window running `run.cmd`. The API will be unavailable until the backend and Funnel are running again. Keep `.env` private: do not commit it or import it into Vercel. For deployment details and troubleshooting, see [Vercel + PC backend](docs/VERCEL_PC_BACKEND.md).

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
- Interviewer coding editor with 12 ready-made Python challenges, editable problem details, custom-problem preview, and candidate-only execution/final submission in restricted Docker containers.
- Private PDF, DOCX, PPTX and image sharing; local page/slide/caption-grounded RAG drafts; one combined AI resume picker/uploader; resume assessment, consented speech metrics, human feedback, readable weighted reports with missing-score guidance, JSON downloads and history charts.
- Room deletion uses a five-second server-side undo window before the room and its shared files are permanently removed.
- Solo AI practice with adaptive LangGraph difficulty.
- Additive MySQL account migration, integrity-tested backups and recovery drills, health/monitoring endpoints, security headers, bounded throttling and deployment templates.

## How the project works

```mermaid
flowchart LR
    Browser[Browser: HTML · CSS · JavaScript] -->|Local same-origin HTTP| Local[Local FastAPI]
    Browser -->|Production static site| Vercel[Vercel frontend]
    Browser -->|Same-origin HTTPS /api| Vercel
    Vercel -->|HTTPS rewrite| Funnel[Tailscale Funnel]
    Funnel --> API[FastAPI on owner PC<br/>one Uvicorn worker]
    Browser <-->|Room WSS via Funnel<br/>short-lived one-use ticket| API
    BrowserA[Candidate browser] <-->|Direct WebRTC media| BrowserB[Interviewer browser]
    Local --> API
    API --> DB[(MySQL<br/>users · sessions · rooms · results)]
    API --> Files[(Private data folder<br/>uploads · Chroma · caches · backups)]
    API --> AI[Ollama · LangChain · LangGraph<br/>local AI and retrieval]
    API --> Whisper[Optional Faster-Whisper<br/>consented speech analysis]
    API --> Docker[Docker CLI<br/>restricted Python runner]
```

- The frontend is plain HTML/CSS/JavaScript; it has no Node/npm build step. FastAPI serves it during local development. In production, Vercel serves these static files.
- Browser HTTP requests use `/api`. Locally they go to FastAPI. On the deployed site, the browser calls Vercel and Vercel rewrites API requests through Tailscale Funnel to the backend on the maintainer's PC. Peer-room WebSockets connect to the PC through Funnel with a room-scoped, short-lived, single-use ticket. Login tokens are not put into WebSocket URLs.
- FastAPI checks requests, permissions and sessions, then reads/writes MySQL. It stores uploaded documents and local retrieval indexes/caches under `data/`.
- Ollama runs the configured chat and embedding models on the backend PC. LangChain/LangGraph coordinate retrieval and interview practice. Docker runs candidate Python submissions in a restricted container.
- Peer-room chat, code updates and call setup use authenticated WebSocket events. Browsers send audio/video to each other directly through WebRTC; the backend coordinates signaling and room permissions. No TURN relay is included, so some remote networks may block media even when chat works.
- Passwords are hashed; browser sessions use HttpOnly cookies. Private settings and credentials belong in `.env`, which must never be committed or uploaded to Vercel.

For the detailed system architecture, data flow, trust boundaries, module map, report formula and feature behavior, see [Project guide — Architecture](docs/PROJECT_GUIDE.md#2-architecture).

### Main user flows

1. **Account and profile:** A candidate or interviewer registers and signs in. FastAPI validates the request, hashes passwords, and stores account/profile data in MySQL. The browser receives a secure, HttpOnly session cookie.
2. **Resume and preparation:** A candidate can upload a resume. The backend extracts PDF text, stores the owned file under `data/`, and uses local Ollama embeddings/retrieval to ground supported preparation and feedback in the candidate's materials.
3. **Solo practice:** The browser requests a practice session. A LangGraph workflow uses the configured Ollama chat model to generate/adapt questions, evaluate submitted answers, and produce feedback and scores. Session history and results are stored in MySQL for reports.
4. **Live interview:** An interviewer creates a room and shares its join code. The backend checks room membership and interviewer/candidate permissions. Room chat, questions, code-editor changes, timers and call signaling travel over authenticated WebSockets. Audio/video streams travel between browsers over WebRTC.
5. **Coding and results:** A candidate submits Python code; FastAPI sends it to a disposable Docker container with no network, read-only files, resource limits and the project runner image. The interviewer and candidate can see the shared test results. The app saves interview events, evaluations and final reports in MySQL.

For the hosted deployment, the frontend is on Vercel but the backend and its data remain on the maintainer's PC. A partner cloning the repository should use their own local database and services; the maintainer's production site is not a shared development database.

## Documentation

| Document | Contents |
| --- | --- |
| [Project guide](docs/PROJECT_GUIDE.md) | Full architecture and source map, data flows, validation, authentication, sessions, roles, scoring, storage and configuration |
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

## Fresh clone install guide (Windows CMD)

These steps set up a private local development copy on Windows 10/11. Python 3.12, MySQL Community Server 8.0, Ollama and Docker Desktop match the verified environment. Install them from their official pages: [Python for Windows](https://www.python.org/downloads/windows/), [MySQL Installer](https://dev.mysql.com/downloads/installer/), [Ollama for Windows](https://ollama.com/download/windows), and [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/). Install Git for Windows as well. Use Docker Desktop's Linux-container/WSL 2 mode.

### 1. Clone the repository

Open CMD in the parent folder where you want the project, then run:

```bat
git clone https://github.com/zamanuddinkhan/InterviewAce_AI.git
cd InterviewAce_AI
```

The repository does not contain the maintainer's `.env`, MySQL records, uploaded files, or downloaded models. Each clone must configure its own local services.

### 2. Create Python environment and install app dependencies

Install Python 3.12 and confirm the Python launcher can find it:

```bat
py -3.12 --version
py -3.12 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
```

Keep this CMD window in the repository root. The base requirements install FastAPI/Uvicorn, MySQL access, authentication, PDF parsing, Ollama integration, LangGraph and local retrieval. No Node.js or `npm install` is required for the frontend.

### 3. Create a local MySQL database and app user

Start the MySQL80 Windows service. In MySQL Workbench, connect as a local MySQL administrator and run this once. Replace the password placeholder with a private strong password; do not paste it into chat or commit it.

```sql
CREATE DATABASE IF NOT EXISTS interviewace CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'interviewace_app'@'localhost' IDENTIFIED BY 'REPLACE_WITH_A_LONG_RANDOM_PASSWORD';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES
ON interviewace.* TO 'interviewace_app'@'localhost';
```

If the account already exists and you are resetting its password, also run `ALTER USER 'interviewace_app'@'localhost' IDENTIFIED BY 'THE_SAME_PASSWORD';`. The app creates its tables on first start. Use the `localhost` host in the connection URL to match this MySQL account.

### 4. Create the private `.env`

In CMD at the repository root:

```bat
copy .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
python -c "from getpass import getpass; from urllib.parse import quote; print(quote(getpass('MySQL app password: '), safe=''))"
notepad .env
```

The first Python command prints a new private `JWT_SECRET`; copy that value into `.env`. The second prompts for the MySQL app password without displaying it and prints its URL-encoded form. Put that result in `DATABASE_URL` using this format:

```text
DATABASE_URL=mysql+pymysql://interviewace_app:URL_ENCODED_PASSWORD@localhost:3306/interviewace
```

Replace `URL_ENCODED_PASSWORD` with the second command's output. Set `JWT_SECRET` to the first command's output. Leave values unquoted and with no spaces. Keep `.env` private. The `MYSQL_PASSWORD` and `MYSQL_ROOT_PASSWORD` entries in `.env.example` are only for the optional Compose MySQL service; they are not the native MySQL app password.

### 5. Download AI models and prepare Docker

Start the Ollama app, then pull the configured models:

```bat
ollama pull qwen2.5:1.5b
ollama pull nomic-embed-text
ollama list
```

Start Docker Desktop and wait for it to report that the engine is running. Build the restricted code-execution image:

```bat
docker info
docker build -t interviewace-runner:local sandbox
```

Ollama is needed for AI generation and embeddings. Docker is needed for Python coding challenges/submissions. MySQL, Ollama and Docker should listen only on the local machine; do not expose their ports to the internet.

### 6. Start and verify

From the repository root, run:

```bat
run.cmd
```

Leave this CMD window open. Open <http://127.0.0.1:8000> in a browser. In another CMD window, verify process and database readiness:

```bat
curl.exe -i http://127.0.0.1:8000/api/live
curl.exe -i http://127.0.0.1:8000/api/health
```

`/api/live` should return `status: alive`; `/api/health` should return `status: ok` and `database: mysql`. These health checks do not prove that Ollama generated a response; test an AI practice action in the browser. To stop the server, press **Ctrl+C** in the window running `run.cmd`.

### Optional dependencies

Install speech transcription dependencies only if using local Faster-Whisper transcription:

```bat
python -m pip install -r backend\requirements-speech.txt
```

For API/browser verification, install the test tools separately. Browser verification also needs Chrome installed:

```bat
python -m pip install -r backend\requirements-test.txt
python -m pip install -r backend\requirements-browser.txt
```

See [Operations guide](docs/OPERATIONS.md) for backups, recovery and troubleshooting, [MySQL guide](docs/MYSQL.md) for database details, and [Vercel + PC backend](docs/VERCEL_PC_BACKEND.md) for a separate public deployment. `requirements-lock-windows.txt` records the verified Windows/Python 3.12 versions; it is not a cross-platform lock.

## Deployment scope

The application is deployed with a Vercel static frontend and the FastAPI backend, MySQL, Ollama and Docker on a Windows PC, connected by Tailscale Funnel. This requires the PC to stay online and makes the backend publicly reachable through HTTPS. The deployment guide is [here](docs/VERCEL_PC_BACKEND.md). Remote health checks have passed; those checks do not certify every AI, media, peer-room, browser, or network workflow. Redundant hosting, database replication/failover, external uptime monitoring and a reviewed public code runner are still infrastructure tasks; this repository does not claim an HA service or a public security certification. HTTPS reverse-proxy and restart-service templates are provided under `deploy/`.
