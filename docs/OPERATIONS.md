# Installation, operations and recovery

## 1. Verified environment and fresh setup

The verified workspace uses Windows, Python 3.12, MySQL Community Server 8.0, Docker Desktop/Linux containers, Ollama, Chrome, Qwen2.5 1.5B, Nomic embeddings and Faster-Whisper tiny.en/CPU. The language/framework/database constraints are Python/FastAPI/MySQL and HTML/CSS/JavaScript. SQLite is only an automated test adapter.

For a fresh machine:

1. Install Python 3.11/3.12, MySQL Community Server, Ollama, Git and a Docker-compatible engine. Respect each tool/model license and Docker Desktop's applicable free personal/education terms; Docker Engine is another free software option.
2. Open the project directory and create the environment: `py -3.12 -m venv .venv`.
3. Install base requirements: `.venv/Scripts/python.exe -m pip install -r backend/requirements.txt`.
4. Install speech requirements when needed: `.venv/Scripts/python.exe -m pip install -r backend/requirements-speech.txt`. PyAV is pinned below 17 because version 19 removed an argument required by this Faster-Whisper decoder.
5. Install API-test requirements when needed: `.venv/Scripts/python.exe -m pip install -r backend/requirements-test.txt`. Install browser-test requirements with `backend/requirements-browser.txt`. Chrome must also be installed; no browser needs to be downloaded by the script when Chrome is available.
6. Copy `.env.example` to `.env` only if no configured `.env` exists. Generate a random private JWT secret of at least 32 characters. Do not commit or paste it in chat.
7. Configure an existing MySQL database/user, or use the project-local provisioning path described below.
8. Start Ollama and pull `qwen2.5:1.5b` and `nomic-embed-text`. Build `docker build -t interviewace-runner:local sandbox` while Docker is running.
9. Start with `./run.ps1` and open http://127.0.0.1:8000. API docs are at `/docs`.

The existing workspace has no pip module in its virtual environment. Its equivalent installer is:

```powershell
uv --cache-dir .uv-cache pip install --python .venv/Scripts/python.exe -r backend/requirements.txt
```

The same command accepts speech/browser requirement files. `requirements-lock-windows.txt` records all verified installed versions, including speech/testing dependencies. Use it for matching Windows/Python 3.12 reproductions; for other platforms resolve the curated requirement files and rerun checks rather than assuming binary compatibility.

For optional solo knowledge retrieval, run `.venv/Scripts/python.exe -B -m backend.ingest` after installing the embedding model. Peer PDF retrieval does not require that curated knowledge index.

## 2. MySQL configurations

**Current workspace:** the user has switched `.env` to the existing PC MySQL80 server at 127.0.0.1:3306, schema `interviewace`, with `LOCAL_MYSQL=0`. The managed 3307 configuration below remains an optional installation path. See MYSQL.md for current Workbench settings. The MySQL verifier can use either configuration and requires permission to create/drop its uniquely named temporary test database.

### Existing MySQL server

Create the database with utf8mb4 and a dedicated local application user:

```sql
CREATE DATABASE interviewace CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'interviewace'@'localhost' IDENTIFIED BY 'YOUR_PRIVATE_PASSWORD';
GRANT ALL PRIVILEGES ON interviewace.* TO 'interviewace'@'localhost';
```

Set `DATABASE_URL=mysql+pymysql://interviewace:URL_ENCODED_PASSWORD@127.0.0.1:3306/interviewace`. Encode reserved password characters when building the URL; for example, write `@` as `%40`. Application permissions include table creation and the additive account migration. More restrictive external production credentials/migration separation require an operator-managed deployment.

### Managed project-local MySQL (configured workspace)

`python -m backend.local_mysql` uses the installed MySQL binary but a separate `data/mysql` data directory and loopback port 3307. It does not stop, replace or reconfigure MySQL80. On first initialization it generates app/root passwords, creates the database/user through a temporary bootstrap SQL file and saves configuration to ignored `.env`. The bootstrap file is removed after readiness verification. Existing nonempty/unrecognized folders are never erased automatically.

`run.ps1` calls this helper before the API. A recognized running instance is checked using its saved app credentials. Preserve `.env` and `data/mysql` together. This is a Windows/MySQL 8.0 helper using mysql_native_password, not a MySQL 8.4 provisioning script; the optional container installation uses its own standard 8.4 authentication.

### Optional containers

`compose.yaml` can run MySQL 8.4 on 127.0.0.1:3307 and Ollama on 127.0.0.1:11434 with named volumes and restart policies. Set `MYSQL_PASSWORD` and `MYSQL_ROOT_PASSWORD`, then `docker compose up -d`. Do not start a container on a port already occupied by the managed MySQL instance or native Ollama. Pick one installation path and configure the corresponding URL. The Compose and native data directories are separate.

## 3. Configuration reference

| Variable | Purpose / default |
| --- | --- |
| `DATABASE_URL` | Required MySQL/PyMySQL connection URL. Application SQLite is rejected unless explicitly in test mode. |
| `JWT_SECRET` | Private signing secret, at least 32 characters; known placeholder/default values are rejected. |
| `OLLAMA_URL` | Local model endpoint; default `http://127.0.0.1:11434`. |
| `CHAT_MODEL` | `qwen2.5:1.5b` by default. |
| `EMBED_MODEL` | `nomic-embed-text` by default. |
| `WHISPER_MODEL` | `tiny.en` by default; English tiny model. Other local selections require re-verification. |
| `COOKIE_SECURE` | `false` for local HTTP; set `true` on HTTPS to enable Secure cookies and HSTS. |
| `SESSION_HOURS` | Absolute session duration, default 8 hours. |
| `SESSION_IDLE_MINUTES` | Idle session timeout, default 30 minutes. |
| `TRUSTED_HOSTS` | Comma-separated allowed hosts, default `127.0.0.1,localhost,testserver`. Replace with the deployed hostname; do not use a permissive wildcard. |
| `PUBLIC_ORIGIN` | Optional exact HTTPS public origin, no trailing slash. Used for HTTP/WebSocket origin checks. |
| `RUNNER_IMAGE` | Built restricted code image; default `interviewace-runner:local`. |
| `ENABLE_CODE_EXECUTION` | `true` for trusted local demos; `false` disables runner calls. Linux deployment template defaults to false. |
| `DOCKER_HOST`, `DOCKER_CONFIG` | Optional Docker CLI connection/configuration. Configured workspace uses the Desktop Linux named pipe and `./data/docker-cli`; project-relative paths resolve from the project root after a folder move. |
| `HF_HOME` | Optional Hugging Face model-cache location; configured as `./data/huggingface` and resolved from the project root after a folder move. |
| `LOCAL_MYSQL` | Internal marker `1` for the managed instance. Do not set it for an unrelated database. |
| `LOCAL_MYSQL_PORT` | Managed instance port; default 3307. |
| `MYSQLD_PATH` | Installed mysqld executable for local startup and related client discovery. |
| `LOCAL_MYSQL_PASSWORD`, `LOCAL_MYSQL_ROOT_PASSWORD` | Generated private credentials for the managed app account and recovery/test tools. Never publish them. |
| `MYSQL_PASSWORD`, `MYSQL_ROOT_PASSWORD` | Optional Compose MySQL credentials; separate from native managed credentials. |
| `INTERVIEWACE_TESTING` | Internal test adapter flag; never enable in a deployed application. |
| `TEST_DATABASE_URL` | Test-only override; must name an `interviewace_test_` database. Set by the real-MySQL verifier, not a production URL. |

Changing signing keys invalidates prior JWTs. Cookies, session fields and generated documentation do not include the JWT secret. Configuration errors should be fixed locally rather than bypassing validation.

## 4. Startup, shutdown and migration

Use one Uvicorn worker:

For CMD, `run.cmd` is the recommended launcher; PowerShell uses `./run.ps1`. Both delegate to `backend.launch`, which checks an occupied port and reports an already running InterviewAce instance. They do not kill another process automatically. If `.env` changes, stop the prior server with Ctrl+C before starting again. `run.cmd --port 8001` is available when a different port is needed.

```powershell
.venv/Scripts/python.exe -B -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --workers 1 --ws-max-size 32768
```

Tables are created on application import. `schema.upgrade` additively adds the three user fields and backfills legacy names without dropping records. It is idempotent. Take a backup and schedule a maintenance window before applying schema changes. Existing sessions from the former browser-token implementation require a fresh login; existing password hashes remain valid.

Stop the foreground API with Ctrl+C. For a background process, identify the PID bound to 8000 and verify its command line belongs to this project before stopping it. Never stop unrelated Python or MySQL processes by name. Stop managed MySQL cleanly with MySQL Workbench/admin tooling and its private local root credentials; do not forcibly remove `data/mysql` while running. The API can be restarted while retaining MySQL, PDFs and models. Rooms past their stored deadline expire on restart; reconnecting video may require clicking Connect call again.

## 5. Backup, verification and recovery

Archives contain `database.sql`, uploads and `manifest.json` with SHA-256 checksums. Credentials are supplied to MySQL clients through a temporary private option file, not process arguments. Backup archives are staged, verified and atomically published under `data/backups`. They do not include `.env`, local model downloads or MySQL raw data files.

For a consistent SQL-and-file snapshot, stop/quiesce the application before backup so file uploads/deletions cannot race the SQL snapshot. MySQL uses a single-transaction logical dump. Back up `.env` separately into a secure operator-controlled secret store; the archive deliberately excludes it.

```powershell
.venv/Scripts/python.exe -B -m backend.backup create
.venv/Scripts/python.exe -B -m backend.backup verify data/backups/YOUR_ARCHIVE.zip
.venv/Scripts/python.exe -B -m backend.backup drill data/backups/YOUR_ARCHIVE.zip
```

`drill` creates a random `interviewace_restore_` database, imports SQL, restores/uploads references, checks table counts and referenced file existence, invalidates restored login sessions, then deletes only that newly created rehearsal database/folder. It never restores over the application database. Corrupt checksums and unsafe upload paths are rejected. Failed rehearsal/restore attempts also clean their new target rather than overwriting application records.

To retain a recovery target:

```powershell
.venv/Scripts/python.exe -B -m backend.backup restore data/backups/YOUR_ARCHIVE.zip
```

This creates a **new** recovery database/folder and reports its name. It does not switch the running application. Review recovered counts/files, create an appropriately restricted application user/grant for that new database, stop the API, securely update `DATABASE_URL` to that database, then start and test the app. Recovered file paths point to the retained recovery uploads folder. Restored users must log in again. Do not delete that folder after promoting the recovery database.

Automatic restore is restricted to the managed local instance because it has known separate admin credentials. For an external database use an authorized DBA and equivalent new-database restore steps. Only restore trusted archives you created: a checksum detects corruption, not a maliciously rewritten SQL archive or a cryptographic signature.

Suggested operating policy: daily archives while the app is quiescent, off-device encrypted copies, seven daily and four weekly copies, and a regular restore drill. No scheduled task, encryption key storage, external backup destination, retention deletion or alerting service is silently installed. Confirm a backup is usable before manually removing old copies. Account deletion does not retroactively erase backup copies; define retention/privacy obligations accordingly.

## 6. Monitoring and incident handling

| Endpoint / artifact | Use |
| --- | --- |
| `GET /api/live` | Process liveness without a DB query. |
| `GET /api/health` | Readiness: actual SQL query and connected dialect/version; 503 if unavailable. |
| `GET /api/monitoring` | Authenticated aggregate process uptime, status counts and active socket count; no personal records. |
| `X-Request-ID` | Safe identifier for a failed request; included in server logs. |
| `Server-Timing` | API processing duration for browser diagnostics. |
| `server.log`, `server-error.log` | Current local API access/operational output when started in background. |
| `data/mysql-server.log` | Managed MySQL startup/runtime log. |

Request logs contain method, route template, status, duration and request ID, not raw bodies, passwords, emails, cookies or tokens. Unexpected and DB failures log exception type without private SQL/credentials. Metrics and rate limits are process-local and reset on restart. Configure OS/proxy log rotation and external uptime alerts for an operated service; no external account/service is assumed.

Investigate rising 5xx by request ID and dependency health. Inspect 429 Retry-After before retrying. Do not auto-retry submissions blindly: the prior request may have committed before the response was lost. Check room/report state first. Never paste `.env`, cookies or private PDF content into diagnostics.

## 7. Deployment, availability and scaling

For the Vercel static frontend with FastAPI, MySQL, Ollama and Docker retained on the Windows PC, follow [Vercel + PC backend](VERCEL_PC_BACKEND.md). It includes the Tailscale Funnel setup, same-origin API proxy, short-lived peer WebSocket tickets, public deployment `.env` values and remote verification commands. The PC must remain awake and connected; this is not always-on hosting.

The provided Dockerfile uses a non-root app user and a readiness healthcheck. Compose persists MySQL/Ollama through volumes and restarts them unless stopped. `deploy/interviewace.service` supplies a Linux restart-on-failure example; `deploy/nginx.conf` supplies an HTTPS/WebSocket reverse-proxy template. Replace paths, domain, certificates, service user and configuration before installation. These files are reviewable examples; no public site or OS service was automatically deployed.

Set a real `PUBLIC_ORIGIN`, narrow `TRUSTED_HOSTS`, `COOKIE_SECURE=true`, and protect the private environment and data directories. Trust forwarded headers only from your proxy. Keep MySQL, Ollama and Docker off public interfaces. The Docker application image does not contain speech dependencies by default; install the optional speech requirements in a derived image if speech is required.

The public Linux service template sets `ENABLE_CODE_EXECUTION=false`. Do not add a Docker socket mount to a public web service to enable code execution. A separately reviewed runner/service boundary is required; the current host-runner design is appropriate for trusted local demos.

**High availability is not achieved by these templates alone.** The current application supports one signaling process and one local MySQL instance. They are single points of failure. API restart policies help recovery, not redundancy. Multi-worker deployment would require coordinated WebSocket delivery, distributed throttling/locks and explicit session routing; adding workers blindly breaks live room events. Full HA additionally needs redundant hosts/load balancing, database replication/failover, tested durable external storage, monitored offsite backups, model capacity and media relay infrastructure. Those are operator/infrastructure work, not implemented or claimed here.

Data durability depends on MySQL/InnoDB persistence settings, disk health and working backups. Foreign keys, uniqueness and transactions provide logical integrity; they cannot protect against total disk loss. Public video may need a TURN relay; free software does not guarantee free hosting. The documentation distinguishes verified local behavior from these future operating requirements.

## 8. Troubleshooting

| Symptom | Action |
| --- | --- |
| MySQL unavailable / startup error | Run local helper, inspect `data/mysql-server.log`, check saved credentials/port; never erase a nonempty data folder to retry. |
| Port 8000 already used | Identify and verify the owning process; stop only the prior project instance or choose a separate port/origin. |
| 401 after upgrade/restart | Existing pre-cookie sessions need a fresh login; idle/absolute expiry or logout-all also requires login. |
| Cookie login works only intermittently | Check host consistency (localhost vs 127.0.0.1), Secure vs HTTP, exact public origin and proxy headers. |
| 403 CSRF/origin error | Send the browser request header and correct same origin; do not disable checks or enable wildcard CORS. |
| 422 account errors | Read safe inline messages; contact needs `+` country code, names need letters, password/confirmation must meet policy. |
| AI/RAG 503 | Check Ollama and both model names; verify local inference and embeddings. |
| Code execution unavailable | Start Docker, build the runner image, check CLI connection and `ENABLE_CODE_EXECUTION`; host fallback is intentionally absent. |
| Speech 503 | Install optional speech requirements, compatible PyAV and Whisper model; test a decodable file within limits. |
| Camera/microphone unavailable | Use localhost/HTTPS, grant permissions, check devices; enable both sides then connect. |
| Video fails across networks | Test locally first; firewall/NAT may require TURN configuration outside this build. |
| Shared file rejected | Use PDF, DOCX, PPTX, PNG, JPG, GIF or WebP up to 3 MB. PDFs need selectable text; Office files are parsed locally; images need a searchable caption. OCR is not implemented. |
| Empty final scores | Missing assessments remain unavailable; final code submission and human feedback are distinct from trial runs. |
| Old styles after upgrade | Reload; versioned local assets revalidate. Do not cache private API responses. |

## 9. Testing, documentation and cleanup

Run the commands in README.md and review validation.md. Tests use disposable databases and synthetic accounts; runtime test accounts and owned files are removed in finally blocks. Browser verification uses synthetic media and does not certify physical devices, every OS/browser or remote-network routing. Test coverage is representative and risk-focused, not proof of all possible cases or production penetration/load testing.

Regenerate API/data docs using `python -m backend.document` with the current app running. Update PROJECT_GUIDE.md when changing behavior, limits or privacy. Keep dependency locks platform-specific and run live speech checks after codec upgrades.

Confirmed obsolete failed-browser artifacts, completed download logs and project Python/pytest caches can be removed. Preserve `.env`, `.venv`, bundled Python, active model/MySQL files, uploads, backups, active service logs and verification scripts. The cleanup record lists actual removals; it is not a recursive wipe of `data/`.

## 10. Primary references

Session controls follow the principles in the [OWASP session management guidance](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html). Deployment scope and process-memory limitations are described in [FastAPI deployment concepts](https://fastapi.tiangolo.com/deployment/concepts/). Logical backups use documented [MySQL mysqldump options](https://dev.mysql.com/doc/refman/8.0/en/mysqldump.html). These references support design decisions; they are not an audit or certification of this project.
