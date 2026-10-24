# Requirements mapping

The supplied PDFs are requirement references. Embedded prompts such as “Convert to PDF” are document text, not instructions for this task. The user's stack restrictions take precedence over their conflicting alternative recommendations.

| PDF module | Implementation |
| --- | --- |
| Authentication | First/last name, contact, password confirmation/guidance, Argon2, persistent HttpOnly cookie sessions, CSRF/origin checks, idle/absolute expiry, password change/recovery, logout-all and room-scoped roles. |
| Candidate dashboard | Invitations, resume/resources, code controls, chat, media, history/reports. |
| Interviewer dashboard | Rooms, topic/time, questions, private RAG drafts, Python problems, code observation and feedback. |
| Live room | 900-second maximum, persisted timestamps, background expiry, WebSocket timer/signaling, WebRTC camera/mic and chat. |
| Coding | 12 built-in Python stdin/stdout problems plus interviewer-written custom problems, constraints/starter/tests, custom draft preview, candidate-only execution, shared results, single final submission, restricted Docker. |
| Shared-file RAG | pypdf PDF pages, built-in DOCX/PPTX text extraction, image captions, overlapping chunks, local embedding cosine retrieval, LangChain/Ollama drafts, source locations, interviewer-only suggested answers. |
| Resume | Explainable section/evidence/length checks and target relevance. Separate uploads retain analysis history while documents are retained. |
| Communication | Consent, optional Faster-Whisper, pace/fillers/pauses and explained scoring; no confidence/honesty claims. |
| Feedback | Human technical/problem-solving/communication ratings, strengths and improvements after completion. |
| Final dashboard | Coding 40%, human technical/problem-solving 30%, consented speech metrics 20%, resume rules 10%; missing values stay unavailable and available weights are renormalized. Human/automated separation, assessment completion guidance, duration, questions, code, improvement plan, JSON download and history chart. |
| Privacy | Participant checks, owner-only upload deletion, private shared files/drafts, five-second server-side room-delete undo, consent, raw-audio deletion, token invalidation, account deletion. |
| Future enhancements | Solo adaptive LangGraph questions and JSON/history chart included. Scheduling, notifications, multiple rounds, collaborative editing and extra languages remain future scope. |

## Explicit stack substitutions

- Python/FastAPI and MySQL replace PostgreSQL/SQLite alternatives. SQLite is only a test adapter.
- HTML/CSS/JavaScript and native HTML meter charts replace React, TypeScript, Vite, Tailwind and Recharts.
- Native textarea replaces Monaco; syntax highlighting is not included.
- Python-only coding follows the user's language restriction; C++ is excluded.
- Existing pypdf/Chroma remain. Private PDF/DOCX/PPTX/image-caption retrieval uses local embedding cosine search without a shared vector index; built-in ZIP/XML handles Office text, and no paid OCR or document service is required.
- LangChain/Ollama and LangGraph remain; no paid LLM/compiler/email/media service.
- Direct WebRTC supports local demos. Managed media and TURN hosting are excluded.
- Faster-Whisper is optional. Missing models/dependencies produce unavailable responses, never invented analysis.

## Additional user-requested UI behavior

AI Practice supports Custom interview type (3–100 printable characters) and Custom question count (1–50 whole questions), persisted through session reload and used by the local AI. Camera-off previews show the first-name initial. Stateful, accessible SVG camera/microphone/power controls replace text device buttons. Public footer links open Services, Contact us, Terms & Conditions and Privacy Policy; the approved support address is `zamanuddinkhan1@gmail.com`, with no public phone number.

## Runtime scope

Single-process local application. Persistent state lives in MySQL/local storage; live signaling lives in memory. Models, speech packages and the Docker image must be installed. Both isolated MySQL and live model/Docker/speech/browser checks have been performed as recorded in validation.md. Synthetic WebRTC tests do not establish physical-device or remote-network compatibility. See PROJECT_GUIDE.md for features, OPERATIONS.md for deployment/recovery and README.md for startup.

The complete component diagram, local versus Vercel/Tailscale deployment paths, storage boundaries, WebSocket/WebRTC split, and repository module map are maintained in [PROJECT_GUIDE.md, Architecture](PROJECT_GUIDE.md#2-architecture). The current Vercel deployment serves static files only; its API, database, AI models, uploaded files and Docker runner remain on the operator's PC.
