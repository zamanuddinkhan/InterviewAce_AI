"""Full logged-in home, room/editor layout, device fallback and AI practice run."""
from pathlib import Path
import requests
from playwright.sync_api import sync_playwright, expect
from .verification_helpers import registration
from .verify_runtime import pdf

BASE='http://127.0.0.1:8000'


def login(page,payload):
    page.goto(BASE);page.locator('#email').fill(payload['email']);page.locator('#password').fill(payload['password']);page.locator('#authSubmit').click()
    expect(page.locator('#memberHome')).to_be_visible();expect(page.locator('.welcome')).to_be_visible()


def main():
    payload=registration();response=requests.post(BASE+'/api/register',json=payload,timeout=20);response.raise_for_status();token=response.json()['token'];errors=[]
    try:
        with sync_playwright() as playwright:
            sample=Path('data/speech-sample.wav').resolve()
            args=['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream']
            if sample.exists():args.append('--use-file-for-fake-audio-capture='+str(sample))
            browser=playwright.chromium.launch(channel='chrome',headless=True,args=args)
            context=browser.new_context(permissions=['camera','microphone'],viewport={'width':1440,'height':1000})
            page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
            login(page,payload)
            page.reload();expect(page.locator('#memberHome')).to_be_visible()
            page.locator('#memberHome [data-page=peer]').click();page.locator('#createRoom button').click()
            expect(page.locator('#peerRoom')).to_be_visible()
            expect(page.locator('#peerTimer')).to_have_text('15:00')
            expect(page.locator('#peerStart')).to_be_disabled()
            expect(page.locator('#enableMedia')).to_be_enabled()
            page.locator('[data-room-tab=resources]').click()
            page.locator('#peerPdf').set_input_files({'name':'studio-notes.pdf','mimeType':'application/pdf','buffer':pdf()})
            page.locator('#peerUpload button').click()
            expect(page.locator('#peerDocuments')).to_contain_text('studio-notes.pdf')
            page.locator('#ragForm button').click()
            expect(page.locator('#ragDraft .secondary')).to_be_visible(timeout=180000)
            expect(page.locator('#ragDraft')).to_contain_text('page 1')
            page.locator('#ragDraft .secondary').click()
            expect(page.locator('#peerQuestion')).to_be_visible()
            assert page.locator('#peerQuestion').input_value().strip()
            page.locator('#enableMedia').click();expect(page.locator('#mediaStatus')).to_contain_text('enabled')
            assert page.locator('#localVideo').evaluate('(video)=>video.srcObject.getVideoTracks()[0].readyState')=='live'
            page.evaluate("window.scrollTo({top:0,behavior:'instant'})");page.screenshot(path='data/room-waiting-desktop.png')
            page.locator('#openEditor').click();expect(page.locator('#peerCode')).to_be_visible()
            expect(page.locator('#editorHint')).to_contain_text('read-only')
            page.evaluate("window.scrollTo({top:0,behavior:'instant'})");page.screenshot(path='data/editor-interviewer.png')
            for width in (1440,768,390,320):
                page.set_viewport_size({'width':width,'height':1000})
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),f'Coding layout overflow at {width}'
            page.locator('[data-room-tab=live]').click()
            page.evaluate("window.scrollTo({top:0,behavior:'instant'})");page.screenshot(path='data/room-waiting-mobile.png')
            page.locator('#studioNav [data-page=home]').click();expect(page.locator('#memberHome')).to_be_visible()
            # Chrome's synthetic camera can disappear after hiding the captured peer preview.
            # Isolate screenshot/editor checks from the real solo media/AI checks below.
            storage=context.storage_state();browser.close()
            browser=playwright.chromium.launch(channel='chrome',headless=True,args=args)
            context=browser.new_context(permissions=['camera','microphone'],storage_state=storage,viewport={'width':1440,'height':1000})
            page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
            page.goto(BASE);expect(page.locator('#memberHome')).to_be_visible()
            page.locator('#memberHome [data-page=solo]').click();expect(page.locator('#aiCoach')).to_be_visible()
            expect(page.locator('#aiCoach')).to_contain_text('not a human video feed')
            expect(page.locator('#soloInitial')).to_have_text('T')
            expect(page.locator('#soloVideoPlaceholder')).to_be_visible()
            expect(page.locator('#soloCamera svg')).to_be_visible()
            expect(page.locator('#soloCamera')).to_have_attribute('aria-pressed','false')
            page.locator('#kind').select_option('custom');expect(page.locator('#customKind')).to_be_visible()
            page.locator('#customKind').fill('Python data structures')
            page.locator('#kind').select_option('technical');expect(page.locator('#customKind')).to_be_disabled()
            page.locator('#kind').select_option('custom')
            page.locator('#questionLimit').select_option('custom');expect(page.locator('#customQuestionLimit')).to_be_visible()
            for value in ('0','51','1.5'):
                page.locator('#customQuestionLimit').fill(value)
                assert not page.locator('#customQuestionLimit').evaluate('(input)=>input.checkValidity()')
            page.locator('#customQuestionLimit').fill('7')
            assert page.locator('#customQuestionLimit').evaluate('(input)=>input.checkValidity()')
            page.locator('#soloCamera').click();expect(page.locator('#soloMediaStatus')).to_contain_text('Camera enabled',timeout=20000)
            expect(page.locator('#soloVideoPlaceholder')).to_be_hidden()
            expect(page.locator('#soloCamera')).to_have_attribute('aria-pressed','true')
            page.locator('#soloCamera').click();expect(page.locator('#soloVideoPlaceholder')).to_be_visible()
            expect(page.locator('#soloInitial')).to_have_text('T')
            page.locator('#soloCamera').click()
            page.locator('#soloMic').click();expect(page.locator('#soloMediaStatus')).to_contain_text('microphone')
            expect(page.locator('#soloMic')).to_have_attribute('aria-pressed','true')
            page.locator('#soloStopMedia').click()
            expect(page.locator('#soloVideoPlaceholder')).to_be_visible()
            expect(page.locator('#soloMic')).to_have_attribute('aria-pressed','false')
            expect(page.locator('#soloCamera')).to_have_attribute('aria-pressed','false')
            page.set_viewport_size({'width':1440,'height':1000});page.evaluate("window.scrollTo({top:0,behavior:'instant'})");page.screenshot(path='data/solo-ai-studio.png',full_page=True)
            for width in (1440,768,390,320):
                page.set_viewport_size({'width':width,'height':1000})
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),f'Solo/custom/footer layout overflow at {width}'
            page.set_viewport_size({'width':1440,'height':1000})
            page.locator('#customQuestionLimit').fill('1');page.locator('#startForm button[type="submit"]').click()
            expect(page.locator('#answerForm')).to_be_visible(timeout=180000)
            interviews=context.request.get(BASE+'/api/interviews').json()
            assert interviews[0]['kind']=='custom' and interviews[0]['custom_kind']=='Python data structures'
            assert interviews[0]['question_limit']==1
            expect(page.locator('#readQuestion')).to_be_enabled();page.locator('#readQuestion').click()
            # Headless Chrome may lack a local OS voice; explicit fallback is valid.
            expect(page.locator('#voiceStatus')).not_to_have_text('Optional read-aloud uses an installed local browser voice.')
            page.locator('#soloRecord').click();expect(page.locator('#soloAudioStatus')).to_contain_text('consent')
            if sample.exists():
                page.locator('#soloAudioConsent').check();page.locator('#soloRecord').click();page.wait_for_timeout(4500);page.locator('#soloStopRecord').click()
                expect(page.locator('#soloAudioStatus')).to_contain_text('Transcription ready',timeout=180000)
                assert len(page.locator('#answerText').input_value().strip())>3
            page.locator('#answerText').fill('A Python dictionary maps unique keys to values. Lookups take average constant time, for example counting values by a key.')
            page.locator('#answerSubmit').click();expect(page.locator('#report')).to_be_visible(timeout=180000)
            page.locator('#studioNav [data-page=home]').click();expect(page.locator('#memberHome')).to_be_visible()
            assert not errors,errors
            print('PASS: Home, room/editor layouts, custom type/count, name initial, device icons/toggles/shutdown, local recorded answer and real custom AI feedback/report.',flush=True)
            context.close()
            # A blocked/missing camera must not make an available microphone fail.
            context=browser.new_context(permissions=['microphone'])
            context.add_init_script('''const original=navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
              navigator.mediaDevices.getUserMedia=constraints=>constraints.video?Promise.reject(new DOMException('No camera','NotFoundError')):original(constraints);''')
            page=context.new_page();login(page,payload);page.locator('#memberHome [data-page=peer]').click();page.locator('#createRoom button').click();page.locator('#enableMedia').click()
            expect(page.locator('#mediaStatus')).to_contain_text('microphone enabled')
            expect(page.locator('#mediaStatus')).to_contain_text('Camera device was not found')
            page.evaluate('Peer.close()');context.close()
            context=browser.new_context()
            context.add_init_script("navigator.mediaDevices.getUserMedia=()=>Promise.reject(new DOMException('Blocked','NotAllowedError'))")
            page=context.new_page();login(page,payload);page.locator('#memberHome [data-page=solo]').click();page.locator('#soloCamera').click()
            expect(page.locator('#soloMediaStatus')).to_contain_text('permission is blocked')
            expect(page.locator('#soloMediaStatus')).to_contain_text('Windows Settings')
            print('PASS: camera-missing/audio-only fallback and actionable blocked-permission instructions.',flush=True)
            browser.close()
    finally:
        requests.delete(BASE+'/api/me',headers={'Authorization':'Bearer '+token},timeout=20).raise_for_status()
    print('Studio dry-run account and owned rooms removed.',flush=True)


if __name__=='__main__':main()
