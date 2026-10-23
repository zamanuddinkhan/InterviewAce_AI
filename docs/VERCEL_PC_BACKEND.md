# Vercel frontend with the backend on this PC

This deployment keeps the existing FastAPI app, MySQL database, Ollama models, Docker runner, uploaded files and speech model on the Windows PC. Vercel serves only the static frontend. Browser API requests go through Vercel to the PC; peer-room WebSockets connect to the PC through a short-lived, room-scoped ticket. The app remains a single-process service, so run one backend worker.

## Before making it public

- Use a restricted MySQL application account for the `interviewace` schema. The current local `.env` uses the PC's MySQL root account; do not use that account for a public-facing app. Keep `.env` private.
- The tunnel makes the FastAPI app reachable by anyone on the internet. Account registration is public, and anyone may send requests to the app. Keep MySQL, Ollama and Docker ports bound to localhost; never tunnel ports 3306, 11434 or the Docker API.
- Tailscale currently labels Funnel as beta and applies non-configurable bandwidth limits. Treat this setup as a personal/demo deployment, not a high-availability service.
- Docker code execution runs on your PC. Only expose the project if you accept that public users can use its bounded code runner; keep Docker Desktop and the runner image updated and monitor CPU, disk and logs.
- The app, database, models, files and tunnel are unavailable when the PC sleeps, loses internet, or its services stop. This is not always-on hosting.
- Vercel external rewrites have a 120-second request limit. Slow local AI or speech requests can exceed that limit. Browser checks do not prove remote network, webcam, microphone, TURN or every ISP path works.

## 1. Start the local backend

Install and sign in to Tailscale on the Windows PC from the [official Windows download](https://tailscale.com/download/windows). Start the application from the repository folder, using CMD:

```bat
run.cmd
```

Confirm the local backend responds before opening the tunnel:

```bat
curl.exe -i http://127.0.0.1:8000/api/live
```

## 2. Expose only the HTTPS app through Tailscale Funnel

In a second CMD window, run:

```bat
tailscale funnel --bg 8000
tailscale funnel status
```

If Tailscale asks, enable Funnel for this device in the approval page it opens. Copy the HTTPS `*.ts.net` origin from `tailscale funnel status`, for example `https://my-pc.example-tailnet.ts.net`. Do not add a path or credentials. Anyone who knows this address can reach the app while Funnel is enabled, so share it only as needed.

Check the tunnel:

```bat
curl.exe -i https://YOUR-PC-HOST.YOUR-TAILNET.ts.net/api/live
```

To stop publishing this app's port, run `tailscale funnel --https=443 8000 off`. The MySQL port remains private; do not configure router port forwarding.

## 3. Generate the Vercel routing and WebSocket settings

From the project root, substitute the real Funnel origin:

```powershell
powershell -ExecutionPolicy Bypass -File .\deploy\prepare-vercel.ps1 -BackendOrigin "https://YOUR-PC-HOST.YOUR-TAILNET.ts.net"
```

The script writes two public deployment files:

- `frontend/vercel.json` proxies `/api` to the PC and maps the app's existing `/assets/...` links to static frontend files. It also sets browser security headers and permits the app's direct secure WebSocket connection to the PC.
- `frontend/deploy-config.js` sets the WebSocket origin. The browser first obtains a 45-second, one-use ticket through the same-origin API proxy; the long-lived HttpOnly login cookie/token is never placed in the WebSocket URL or sent to page JavaScript.

Review the generated files, then commit/push them. They contain the public Funnel hostname, not a secret. Never add `.env`:

```bat
git add frontend\vercel.json frontend\deploy-config.js
git commit -m "Configure Vercel frontend with PC backend tunnel"
git push origin main
```

## 4. Import the GitHub project into Vercel

In Vercel, import `zamanuddinkhan/InterviewAce_AI` and set:

- **Root Directory:** `frontend`
- **Framework Preset:** `Other`
- **Build Command:** leave empty
- **Output Directory:** leave empty to serve the static files in the root directory

Deploy the `main` branch. Use the stable production domain Vercel assigns, such as `https://interviewace-ai.vercel.app`. Configure and use one canonical production domain; preview deployment domains are not accepted as the app's origin.

## 5. Configure the private PC `.env`

After you know both HTTPS origins, open CMD in the repository and run the PowerShell script with the real values:

```bat
powershell -ExecutionPolicy Bypass -File .\deploy\configure-pc-backend.ps1 -FrontendOrigin "https://YOUR-PROJECT.vercel.app" -BackendOrigin "https://YOUR-PC-HOST.YOUR-TAILNET.ts.net"
```

The script changes only `COOKIE_SECURE`, `PUBLIC_ORIGIN` and `TRUSTED_HOSTS` in the existing `.env`; it preserves `DATABASE_URL`, model/cache paths and all other private settings. It sets secure cookies and the exact canonical Vercel origin. Do not replace `.env` with `.env.example`.

Restart the running API with Ctrl+C, then run `run.cmd` again. Keep Ollama, Docker Desktop and MySQL running. For a public app, first change `DATABASE_URL` to a least-privilege MySQL application user as described in [MySQL setup](MYSQL.md).

## 6. Verify the deployed path

Run these from CMD with your real origins:

```bat
curl.exe -i https://YOUR-PC-HOST.YOUR-TAILNET.ts.net/api/live
curl.exe -i https://YOUR-PROJECT.vercel.app/api/live
curl.exe -i https://YOUR-PROJECT.vercel.app/api/health
curl.exe -I https://YOUR-PROJECT.vercel.app/assets/theme.js
```

Expected: both `/api/live` requests return JSON with `status: alive`; `/api/health` returns `status: ok` and `database: mysql`; the asset request returns HTTP 200 with JavaScript content. Then open the Vercel production URL and verify registration/login persists after reload, solo AI questions/feedback, resume upload, Docker coding submission, and speech transcription. Speech accepts recordings up to 15 MB, so verify a representative recording through the deployed Vercel route. For peer rooms, use two separate browser profiles: create/join a room, check chat/code sync, and inspect DevTools → Network → WS for a successful `wss://YOUR-PC-HOST.../api/rooms/.../ws` connection. Test microphone/camera from HTTPS and from the networks your users will use.

If the page opens but API requests fail, check `PUBLIC_ORIGIN`, `TRUSTED_HOSTS`, cookie `Secure`, the Vercel production domain, Funnel status and the API process. If peer chat fails while HTTP works, confirm `frontend/deploy-config.js` has the correct Funnel origin, the generated CSP permits that `wss://` host, and the browser's WebSocket `Origin` equals `PUBLIC_ORIGIN`.

## What this deployment does not verify

The local verification suite cannot test your Vercel account, GitHub integration, Tailscale tailnet, public DNS, ISP/firewall behavior, or real remote users. After deploying, follow section 6 and the service-specific steps in [Website dry run](DRY_RUN.md). An HTTP health check does not prove Ollama generation, Docker execution, WebRTC or speech will work through the public network.

## Official platform references

- [Tailscale Funnel](https://tailscale.com/docs/features/tailscale-funnel) exposes a local service over a public HTTPS Funnel URL; keep the PC online and the service running.
- [Tailscale Funnel CLI](https://tailscale.com/docs/reference/tailscale-cli/funnel) documents `--bg`, `status` and stopping Funnel.
- [Vercel external rewrites](https://vercel.com/docs/routing/rewrites) documents same-URL proxying to external origins.
- [Vercel limits](https://vercel.com/docs/limits) documents the current 120-second proxied-request timeout.
