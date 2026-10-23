# Website dry run — v3.3.0, 24 October 2026

## Current verification follow-up — 24 October 2026, backend 3.3.0

The full SQLite and isolated MySQL API suites each pass 77 tests. Chrome account, theme, studio and two-person peer-room checks pass. Live integration checks pass local Ollama RAG/AI responses, LangGraph solo practice, restricted Docker execution, and consented Faster-Whisper transcription with the cached Hugging Face `Systran/faster-whisper-tiny.en` model. A separate clean-cache Hub download and transcription also passed. The peer browser verifier now supplies its own deterministic Y4M camera clip so Chrome's default fake camera does not intermittently return an empty video stream.

Physical capture was attempted in visible and headless Chrome, but Windows blocked both devices with `NotAllowedError: Permission denied by system`. Enable desktop-app camera/microphone access in Windows privacy settings before repeating. External-network/WebRTC traversal remains untested and is outside the local setup; no STUN/TURN relay is configured.

Physical-device permissions and remote-network/NAT connectivity still need checks on the target PC/network. See [validation.md](validation.md) for the complete pass list and verification scope.

## Custom AI setup and footer follow-up — 24 October 2026, frontend assets 3.3.0

AI Practice now includes Custom interview type and a Custom question count from 1–50. The chosen focus is retained in MySQL and used by the local AI for generation/evaluation. A camera-off initial and accessible stateful device icons replace text-only controls. Footer links open public Services, Contact us, Terms & Conditions and Privacy Policy sections. Contact lists only `zamanuddinkhan1@gmail.com`.

The latest full API suite passed **77 MySQL tests and 77 SQLite tests**. A verified backup preceded the additive schema update, which preserves older interviews. Account and theme browser checks passed for the updated footer and profile initial. The previous 61-test results below describe the earlier full dry run.

The updated studio run passed custom option validation/persistence, initial/icon states, device toggles/shutdown, responsive layouts, actual custom local AI practice, consented recorded-answer transcription, real feedback/report and media failure fallbacks. `data/solo-ai-studio.png` shows the new controls and footer. Peer screenshots and solo media use separate browser instances after an observed Chrome synthetic-camera disappearance when hiding the captured preview. This is an automated-device limitation; a separate browser probe passed peer-to-solo camera switching, and physical hardware/permissions are not certified by the dry run.

## UI follow-up — 24 October 2026, frontend assets 3.2.1

The main and studio navigation are merged into one shared header. History scores use sharp text and accessible native meter bars, with a clear empty state. Dark mode now uses a pure black background and neutral gray surfaces and controls.

Theme/navigation/history checks and the account browser flow passed again. Header links and score layouts were checked at 320–1440px and standard/retina pixel densities, with empty and mocked populated assessments. Score fixtures do not modify MySQL. Desktop/mobile screenshots are in `data/history-{light|dark}-{1440|390}.png`. Reproduce with `python -B -m backend.verify_theme_browser` and `python -B -m backend.verify_accounts_browser` using the project's virtual environment. The full integration results below are from the earlier dry run.

## Fixes for the reported problems

- Logged-in Home stays available, including after refresh. AI Practice, Peer Rooms, History and Profile are separate views.
- Room creation/join cards disappear while working inside a room; the header separates title/role, a numeric timer, code and actions. Full invitation URLs are collapsed by default.
- The Python editor has a dedicated tab and shortcut. It is visible before start with an explanation of permissions. The interviewer sees read-only code; only the candidate can run/submit after start and problem assignment.
- Camera/microphone preview works while waiting. WebRTC signaling can connect before the timer starts. Missing-camera and blocked-permission cases have actionable messages and an independent microphone fallback.
- Registration help now says only “Your contact number stays private.” The international format validation remains unchanged.
- AI Practice includes an animated coach illustration, local read-aloud where available, optional camera preview and consented local recorded-answer transcription. It does not claim to supply a real human video stream.
- `run.cmd` and `run.ps1` detect an already running app instead of creating a duplicate server/port-8000 bind error.

## What was actually exercised

| Check | Result |
| --- | --- |
| Full automated suite against PC MySQL on 3306 | 61 passed in an isolated temporary database |
| Disposable SQLite suite | 61 passed |
| Registration, login, refresh, profile and logout browser flow | Passed |
| Logged-in Home and navigation between studios/history/profile | Passed |
| Desktop/tablet/mobile room/editor widths: 1440/768/390/320 | Passed without horizontal overflow |
| Waiting-room camera/mic preview before session start | Passed with synthetic devices |
| Missing camera with available microphone | Passed; microphone enabled independently |
| Denied device permission | Passed; browser/Windows instructions displayed |
| Two-person WebRTC before timer start | Connected; remote video frames decoded and live audio tracks existed on both sides |
| Chat, questions, candidate code synchronization and readonly interviewer | Passed |
| Real Docker Python final submission and shared report | Passed |
| Shared PDF upload, actual local embeddings/RAG and page reference | Passed |
| Review PDF draft and return to visible live-question form | Passed |
| AI illustration and local read-aloud availability/fallback | Passed |
| AI voice-answer consent, browser recording and actual local Whisper transcript | Passed using generated English audio |
| Review transcript, submit answer, real LangGraph evaluation and final report | Passed |
| Light/dark modes, saved preference and mobile theme checks | Passed |
| MySQL, real model/RAG, resume, Docker, speech and reports API integration | Passed |
| JavaScript syntax and current API/schema documentation | Passed/regenerated |

Temporary browser/API test accounts and their owned rooms/files were deleted. No unrelated user accounts or databases were reset. The MySQL suite creates/drops only uniquely named `interviewace_test_` databases; its configured account must have permission to create/drop those temporary databases.

## Use the appropriate mode

1. Open **http://127.0.0.1:8000**, log in, and select a practice mode from Home.
2. **AI Practice:** start an interview, read/listen to the question, then type an answer or consent to Record answer → Stop and transcribe. Review the text and Submit. The avatar is an illustration. No second person is required.
3. **Peer Rooms:** the host creates a room; a different account/browser joins as candidate. Both may preview devices immediately. Connect call establishes peer video. The host starts the timer and assigns a problem using Coding editor. The candidate runs/submits code. A peer's video cannot appear if no other participant has joined/shared media.
4. Return to **Home** anytime through the shared header. Leaving a room view stops local devices but does not cancel the server's active timer; reopen the saved room from History.

## If devices still do not work on your PC

- Use `http://127.0.0.1:8000` or `http://localhost:8000` on the same PC, or HTTPS. Plain HTTP at a LAN/public IP cannot use browser camera/mic APIs.
- In Chrome/Edge, use the camera/lock icon beside the address and allow Camera and Microphone for this site.
- Check Windows **Settings → Privacy & security → Camera/Microphone**, including access for desktop apps.
- Close Zoom/Teams/other software if the device is busy. Confirm the selected devices work in another local app.
- In peer mode, make sure the other participant is joined and sharing their devices. Try Connect call again after correcting permissions.
- A network across restrictive NAT/firewalls may need a TURN relay; it is not included in this local build.

The dry run uses browser-generated media and generated speech, not your physical webcam/mic. It verifies the code paths and decoded peer frames, not your hardware, local permissions, every browser/OS, or public-network connectivity. Browser read-aloud may be unavailable without an installed local speech voice; text questions remain usable.

## Reproduce

```cmd
run.cmd
```

From another terminal in the project directory, with the application, Ollama and Docker running:

```cmd
.venv\Scripts\python.exe -B -m backend.verify_mysql
.venv\Scripts\python.exe -B -m backend.verify_accounts_browser
.venv\Scripts\python.exe -B -m backend.verify_browser
.venv\Scripts\python.exe -B -m backend.verify_studio_browser
.venv\Scripts\python.exe -B -m backend.verify_theme_browser
.venv\Scripts\python.exe -B -m backend.verify_runtime
```

Relevant screenshots in ignored `data/`: `room-waiting-desktop.png`, `room-waiting-mobile.png`, `editor-interviewer.png`, and `solo-ai-studio.png`. Green camera frames in these screenshots are Chrome's synthetic test source, not a problem with the video renderer.
