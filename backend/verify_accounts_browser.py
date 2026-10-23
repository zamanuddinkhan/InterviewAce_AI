"""Registration UX, private cookie sessions and responsive layout checks in Chrome."""
from pathlib import Path
from uuid import uuid4

import requests
from playwright.sync_api import sync_playwright, expect

BASE = 'http://127.0.0.1:8000'


def main():
    email=uuid4().hex+'@example.com'; password='Study-Unique-2026!'
    errors=[]
    try:
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch(channel='chrome',headless=True)
            for width in (1440,768,390,320):
                context=browser.new_context(viewport={'width':width,'height':1000},is_mobile=width<500,has_touch=width<500)
                page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto(BASE)
                page.locator('#authToggle').click()
                expect(page.locator('#firstName')).to_be_visible()
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), f'Horizontal overflow at {width}px'
                Path('data').mkdir(exist_ok=True)
                if width in (1440,390):page.screenshot(path=f'data/register-{width}.png',full_page=True)
                context.close()
            print('PASS: registration layout at 1440, 768, 390 and 320px with no horizontal overflow.',flush=True)
            context=browser.new_context(viewport={'width':1440,'height':1100})
            page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
            page.goto(BASE);page.locator('#authToggle').click()
            page.locator('#firstName').fill('Asha');page.locator('#lastName').fill('Khan')
            page.locator('#contactNumber').fill('9876543210');page.locator('#email').fill(email)
            page.locator('#password').fill(password);page.locator('#confirmPassword').fill('Different-Study-77!')
            expect(page.locator('#confirmPasswordError')).to_contain_text('do not match')
            assert page.locator('#confirmPassword').evaluate('(e)=>!e.checkValidity()')
            page.locator('#confirmPassword').fill(password);page.locator('#authSubmit').click()
            expect(page.locator('#contactNumberError')).to_contain_text('country code')
            page.locator('#contactNumber').fill('+91 98765 43210')
            page.locator('#password').fill('alllowercase777!');page.locator('#confirmPassword').fill('alllowercase777!')
            page.locator('#authSubmit').click();expect(page.locator('#passwordError')).to_contain_text('uppercase')
            page.locator('#password').fill(password);page.locator('#confirmPassword').fill(password)
            expect(page.locator('#strengthLabel')).to_contain_text('All requirements met')
            page.locator('#togglePassword').click();expect(page.locator('#password')).to_have_attribute('type','text')
            page.locator('#togglePassword').click();expect(page.locator('#password')).to_have_attribute('type','password')
            page.locator('#authSubmit').click();expect(page.locator('dialog')).to_be_visible()
            page.get_by_role('button',name='I saved my code').click()
            expect(page.locator('#memberHome')).to_be_visible()
            cookies=context.cookies();session=next(c for c in cookies if c['name']=='interviewace_session')
            assert session['httpOnly'] and session['sameSite']=='Strict'
            assert page.evaluate('sessionStorage.getItem("interviewace_token")') is None
            assert 'interviewace_session' not in page.evaluate('document.cookie')
            page.reload();expect(page.locator('#memberHome')).to_be_visible()
            profile=context.request.get(BASE+'/api/me').json()
            assert profile['first_name']=='Asha' and profile['last_name']=='Khan' and profile['contact_number']=='+919876543210'
            page.locator('#memberHome [data-page=profile]').click()
            expect(page.locator('#profileFirstName')).to_have_value('Asha')
            page.locator('#profileFirstName').fill('Updated')
            page.locator('#profileForm button').click()
            expect(page.locator('#userBadge')).to_contain_text('Updated Khan')
            expect(page.locator('#soloInitial')).to_have_text('U')
            page.locator('#logoutBtn').click();expect(page.locator('#authForm')).to_be_visible()
            page.reload();expect(page.locator('#authForm')).to_be_visible()
            assert not errors,errors
            print('PASS: mismatch/phone/weak-password errors, strength guidance, password visibility, registration, HttpOnly cookies, reload, profile update and logout; no JavaScript errors.',flush=True)
            browser.close()
    finally:
        response=requests.post(BASE+'/api/login',json={'email':email,'password':password},timeout=20)
        if response.ok:
            requests.delete(BASE+'/api/me',headers={'Authorization':'Bearer '+response.json()['token']},timeout=20).raise_for_status()
    print('Browser registration test account removed.',flush=True)


if __name__=='__main__':
    main()
