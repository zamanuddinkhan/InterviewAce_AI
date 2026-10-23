"""Real two-context Chrome smoke test; media uses synthetic test devices."""
from pathlib import Path
from tempfile import TemporaryDirectory

import requests
from playwright.sync_api import sync_playwright, expect
from .verification_helpers import registration

BASE = 'http://127.0.0.1:8000'
ROOT = Path(__file__).resolve().parents[1]


def synthetic_camera_clip(width=320, height=240, frames=60):
    """Return a deterministic Y4M clip for Chrome's fake camera input."""
    header = f'YUV4MPEG2 W{width} H{height} F30:1 Ip A1:1 C420jpeg\n'.encode('ascii')
    y_plane = bytes([145]) * (width * height)
    chroma_plane = bytes([128]) * (width * height // 4)
    frame = b'FRAME\n' + y_plane + chroma_plane + chroma_plane
    return header + frame * frames


def main():
    accounts = []
    errors = []
    try:
        for index in range(2):
            payload = registration()
            email, password = payload['email'], payload['password']
            response = requests.post(BASE+'/api/register', json=payload,timeout=20)
            response.raise_for_status()
            accounts.append({'email':email,'password':password,'token':response.json()['token']})
        with TemporaryDirectory(prefix='.webrtc-media-', dir=ROOT) as media_dir:
            video_path = Path(media_dir) / 'synthetic-camera.y4m'
            video_path.write_bytes(synthetic_camera_clip())
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(channel='chrome', headless=True,
                    args=['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream',
                          '--use-file-for-fake-video-capture='+str(video_path)])
                contexts = [browser.new_context(permissions=['camera','microphone'], viewport={'width':1440,'height':1100}) for _ in range(2)]
                pages = [context.new_page() for context in contexts]
                for page, account in zip(pages,accounts):
                    page.on('pageerror', lambda error:errors.append(str(error)))
                    page.goto(BASE)
                    page.locator('#email').fill(account['email'])
                    page.locator('#password').fill(account['password'])
                    page.locator('#authSubmit').click()
                    expect(page.locator('#memberHome')).to_be_visible()
                    page.locator('#memberHome [data-page=peer]').click()
                    expect(page.locator('#createRoom')).to_be_visible()
                interviewer,candidate=pages
                interviewer.locator('#peerTopic').fill('Python browser smoke test')
                interviewer.locator('#createRoom button').click()
                expect(interviewer.locator('#peerIdentity')).to_contain_text('interviewer')
                rows=requests.get(BASE+'/api/rooms', headers={'Authorization':'Bearer '+accounts[0]['token']},timeout=10).json()
                room_id=rows[0]['id']
                candidate.locator('#joinCode').fill(room_id)
                candidate.locator('#joinRoom button').click()
                expect(candidate.locator('#peerIdentity')).to_contain_text('candidate')
                expect(interviewer.locator('#peerIdentity')).to_contain_text('Candidate joined')
                for page in pages:
                    page.locator('#enableMedia').click()
                    expect(page.locator('#mediaStatus')).to_contain_text('enabled')
                interviewer.locator('#callPeer').click()
                expect(interviewer.locator('#mediaStatus')).to_contain_text('connected', timeout=20000)
                expect(candidate.locator('#mediaStatus')).to_contain_text('connected', timeout=20000)
                for page in pages:
                    page.wait_for_function("() => document.getElementById('remoteVideo').videoWidth > 0 && document.getElementById('remoteVideo').readyState >= 2",timeout=20000)
                    assert page.locator('#remoteVideo').evaluate('(video)=>video.srcObject.getAudioTracks().some(track=>track.readyState==="live")')
                print('PASS: WebRTC signaling and peer connection with deterministic synthetic camera/microphone.',flush=True)
                interviewer.locator('#peerStart').click()
                expect(candidate.locator('#peerIdentity')).to_contain_text('Interview in progress')
                assert interviewer.locator('#peerCode').evaluate('(e)=>e.readOnly')
                assert not candidate.locator('#peerCode').evaluate('(e)=>e.readOnly')
                print('PASS: login, both dashboards, room creation/join, timer and editor permissions.',flush=True)
                candidate.locator('#peerMessage').fill('Hello from candidate')
                candidate.locator('#peerChatForm button').click()
                expect(interviewer.locator('#peerChat')).to_contain_text('Hello from candidate')
                interviewer.locator('#peerQuestion').fill('Explain a Python dictionary.')
                interviewer.locator('#sendQuestion button').click()
                expect(candidate.locator('#peerChat')).to_contain_text('Explain a Python dictionary.')
                print('PASS: bidirectional real-time chat and interviewer questions.',flush=True)
                interviewer.locator('[data-room-tab=coding]').click()
                candidate.locator('[data-room-tab=coding]').click()
                interviewer.locator('#problemForm button').click()
                expect(candidate.locator('#sharedProblemTitle')).to_contain_text('Sum two integers')
                candidate.locator('#peerCode').fill('a,b=map(int,input().split());print(a+b)')
                expect(interviewer.locator('#peerCode')).to_have_value('a,b=map(int,input().split());print(a+b)')
                candidate.locator('#submitCode').click()
                expect(candidate.locator('#codeResults')).to_contain_text('"passed": 2',timeout=30000)
                expect(interviewer.locator('#codeResults')).to_contain_text('"passed": 2',timeout=30000)
                interviewer.locator('#peerEnd').click()
                expect(candidate.locator('#peerReport')).to_be_visible()
                interviewer.locator('#feedbackStrengths').fill('Clear Python solution')
                interviewer.locator('#feedbackImprovements').fill('Practise complexity explanations')
                interviewer.locator('#peerFeedback button').click()
                expect(candidate.locator('#peerReport')).to_contain_text('Human interviewer feedback')
                Path('data').mkdir(exist_ok=True)
                interviewer.screenshot(path='data/interviewer-verified.png',full_page=True)
                candidate.screenshot(path='data/candidate-verified.png',full_page=True)
                assert not errors, errors
                print('PASS: live code synchronization, real Docker submission, shared results and final reports; no JavaScript errors.',flush=True)
                for page in pages:
                    page.evaluate('Peer.close()')
                pages[0].wait_for_timeout(300)
                browser.close()
    finally:
        for account in accounts:
            requests.delete(BASE+'/api/me',headers={'Authorization':'Bearer '+account['token']},timeout=20).raise_for_status()
        print('Browser test accounts removed.',flush=True)


if __name__ == '__main__':
    main()
