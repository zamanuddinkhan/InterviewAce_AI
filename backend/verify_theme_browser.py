"""Shared header/footer, theme accessibility/persistence and responsive checks."""
from pathlib import Path
import requests
from playwright.sync_api import sync_playwright, expect
from .verification_helpers import registration

BASE = 'http://127.0.0.1:8000'


def check_merged_header_and_scores(browser, storage, errors):
    # Synthetic history isolates score rendering; authentication still uses the live server.
    scores = [0, 73.5, 100, None]
    rows = [{'id': f'chart-{i}', 'topic': 'Chart verification', 'role': 'candidate',
             'status': 'completed'} for i in range(len(scores))]
    for width, scale in ((1440, 1), (1440, 2), (1024, 1), (980, 1), (768, 1), (390, 2), (320, 2)):
        context = browser.new_context(viewport={'width': width, 'height': 1000},
                                      device_scale_factor=scale, storage_state=storage, color_scheme='light')
        context.route('**/api/rooms', lambda route: route.fulfill(json=rows))
        context.route('**/api/rooms/chart-*/report', lambda route: route.fulfill(
            json={'overall_score': scores[int(route.request.url.split('/')[-2].split('-')[-1])]}))
        page = context.new_page(); page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(BASE); expect(page.locator('#memberHome')).to_be_visible()
        expect(page.locator('header #studioNav')).to_have_count(1)
        expect(page.locator('main > nav')).to_have_count(0)
        for view, panel in (('solo', 'soloStudio'), ('peer', 'peerWorkspace'),
                            ('profile', 'profilePanel'), ('home', 'memberHome'), ('history', 'peerHistoryPanel')):
            link = page.locator(f'#studioNav [data-page={view}]'); link.click()
            expect(page.locator('#' + panel)).to_be_visible()
            expect(link).to_have_attribute('aria-current', 'page')
            expect(page.locator('#studioNav [aria-current=page]')).to_have_count(1)
        expect(page.locator('#progressScores meter')).to_have_count(3)
        expect(page.locator('#progressChart canvas')).to_have_count(0)
        expect(page.locator('#progressScores')).to_contain_text('73.5/100')
        for mode in ('light', 'dark'):
            if page.locator('html').get_attribute('data-theme') != mode: page.locator('#themeToggle').click()
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (width, mode)
            assert page.locator('#studioNav').evaluate('''nav => {
              const header=nav.closest('header').getBoundingClientRect();
              return [...nav.querySelectorAll('a')].filter(a=>a.getClientRects().length).every(a=>{
                const r=a.getBoundingClientRect();return r.left>=0 && r.right<=innerWidth && r.bottom<=header.bottom;
              });
            }'''), (width, mode, 'header links clipped')
            if mode == 'dark':
                assert page.evaluate('getComputedStyle(document.body).backgroundColor') == 'rgb(0, 0, 0)'
                for selector in ('header.topbar', '#peerHistoryPanel', 'footer', '#studioNav [aria-current=page]'):
                    channels = page.locator(selector).evaluate('(el)=>getComputedStyle(el).backgroundColor.match(/\\d+/g).slice(0,3).map(Number)')
                    assert len(set(channels)) == 1, (selector, channels)
            if width in (1440, 390) and scale == 2:
                page.evaluate('window.scrollTo({top:0,behavior:"instant"})')
                page.screenshot(path=f'data/history-{mode}-{width}.png', full_page=True)
        context.close()
    print('PASS: one shared header, all five navigation links, sharp empty/populated scores (0/73.5/100/null), black/gray dark surfaces, 320–1440px and standard/retina screens.', flush=True)


def main():
    errors = []
    payload = registration()
    account = None
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel='chrome', headless=True)
            for width in (1440, 768, 390, 320):
                context = browser.new_context(viewport={'width':width, 'height':1000}, color_scheme='light')
                page = context.new_page(); page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto(BASE)
                expect(page.locator('html')).to_have_attribute('data-theme','light')
                expect(page.get_by_role('button',name='Switch to dark mode')).to_be_visible()
                expect(page.locator('.footer-credit')).to_have_text('Created by Zaman & SaloniMade for learning. Built for progress.')
                assert page.locator('header').count() == page.locator('footer').count() == 1
                page.locator('#authToggle').click()
                for mode in ('dark','light'):
                    page.locator('#themeToggle').click()
                    expect(page.locator('html')).to_have_attribute('data-theme',mode)
                    expect(page.locator('#themeToggle')).to_have_attribute('aria-pressed',str(mode=='dark').lower())
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),f'{mode} layout overflow at {width}'
                    assert page.evaluate('localStorage.getItem("interviewace_theme")') == mode
                    if width in (1440,390):
                        Path('data').mkdir(exist_ok=True)
                        page.screenshot(path=f'data/theme-{mode}-{width}.png',full_page=True)
                page.locator('#themeToggle').focus(); page.keyboard.press('Enter')
                expect(page.locator('html')).to_have_attribute('data-theme','dark')
                page.reload(); expect(page.locator('html')).to_have_attribute('data-theme','dark')
                for section in ('services', 'contact', 'terms', 'privacy'):
                    page.locator(f'.footer-nav a[href="/assets/info.html#{section}"]').click()
                    expect(page.locator('#' + section + ' h2')).to_be_in_viewport()
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                expect(page.locator('#publicContact a')).to_have_attribute('href', 'mailto:zamanuddinkhan1@gmail.com')
                context.close()
            print('PASS: shared header/footer attribution, keyboard toggle, light/dark layouts at 1440/768/390/320px, preference reload and privacy navigation.',flush=True)
            context=browser.new_context(color_scheme='dark')
            page=context.new_page();page.goto(BASE)
            expect(page.locator('html')).to_have_attribute('data-theme','dark')
            page.emulate_media(color_scheme='light');expect(page.locator('html')).to_have_attribute('data-theme','light')
            page.locator('#themeToggle').click();page.emulate_media(color_scheme='light')
            expect(page.locator('html')).to_have_attribute('data-theme','dark')
            second=context.new_page();second.goto(BASE);expect(second.locator('html')).to_have_attribute('data-theme','dark')
            second.locator('#themeToggle').click();expect(page.locator('html')).to_have_attribute('data-theme','light')
            context.close()
            context=browser.new_context()
            context.add_init_script("Object.defineProperty(window,'localStorage',{get(){throw new DOMException('Storage blocked','SecurityError')}})")
            page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)));page.goto(BASE)
            initial=page.locator('html').get_attribute('data-theme');page.locator('#themeToggle').click()
            assert page.locator('html').get_attribute('data-theme') != initial
            context.close()
            print('PASS: OS preference, explicit override, cross-tab synchronization and storage-blocked fallback.',flush=True)
            response=requests.post(BASE+'/api/register',json=payload,timeout=20);response.raise_for_status();account=response.json()
            context=browser.new_context(viewport={'width':390,'height':1000},color_scheme='dark')
            page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
            page.goto(BASE);page.locator('#email').fill(payload['email']);page.locator('#password').fill(payload['password']);page.locator('#authSubmit').click()
            expect(page.locator('#memberHome')).to_be_visible()
            expect(page.locator('.header-nav .member-only')).to_have_count(4)
            for link in page.locator('.header-nav .member-only').all(): expect(link).to_be_visible()
            expect(page.locator('.header-nav .guest-only')).to_be_hidden()
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            for mode in ('dark','light'):
                if page.locator('html').get_attribute('data-theme') != mode:page.locator('#themeToggle').click()
                page.locator('.header-nav a[href="#peerHistoryPanel"]').click()
                expect(page.locator('#peerHistoryPanel')).to_be_in_viewport()
                expect(page.locator('.score-empty')).to_be_visible()
                expect(page.locator('#progressTitle')).to_have_text('Overall practice scores')
                contrast=page.evaluate('''() => {
                  function rgb(s){return s.match(/[\\d.]+/g).slice(0,3).map(Number)}
                  function l(c){return c.map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4}).reduce((s,v,i)=>s+v*[.2126,.7152,.0722][i],0)}
                  const card=document.querySelector('#peerHistoryPanel'),style=getComputedStyle(card);
                  const a=l(rgb(style.color)),b=l(rgb(style.backgroundColor));return (Math.max(a,b)+.05)/(Math.min(a,b)+.05);
                }''')
                assert contrast>=4.5,(mode,contrast)
            assert not errors,errors
            print('PASS: authenticated mobile header/history navigation and main panel text contrast; no JavaScript errors.',flush=True)
            check_merged_header_and_scores(browser, context.storage_state(), errors)
            assert not errors, errors
            browser.close()
    finally:
        if account:
            requests.delete(BASE+'/api/me',headers={'Authorization':'Bearer '+account['token']},timeout=20).raise_for_status()
    print('Theme verification account removed.',flush=True)


if __name__=='__main__':main()
