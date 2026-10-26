import re
from pathlib import Path
from playwright.sync_api import sync_playwright
path=Path(__file__).parent/'site/subjects.html'
html=path.read_text()
html=re.sub(r'<link[^>]+fonts\.googleapis\.com[^>]*>', '', html)
html=re.sub(r'<link[^>]+fonts\.gstatic\.com[^>]*>', '', html)
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-background-networking'])
 page=browser.new_page(viewport={'width':1250,'height':900});page.set_default_timeout(7000)
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.set_content(html,wait_until='commit',timeout=30000)
 page.locator('[data-open="PEA 104"]').click(timeout=6000)
 assert page.locator('[data-tab="quiz"]').count() == 1
 page.locator('[data-tab="quiz"]').click()
 assert page.locator('[data-start="grand"]').count()==1
 page.locator('[data-start="grand"]').click()
 assert page.get_by_role('button',name='Next question →').is_disabled()
 page.locator('[data-choice]').first.click()
 page.locator('[data-submit]').click()
 assert page.locator('[data-next]').is_enabled()
 assert page.locator('[data-review-pdf]').count()==0
 assert not errors,errors
 print('PASS: PEA104 opens, randomized quiz starts, Next locked until submit, no PDF review links mid-quiz, no JavaScript errors')
 browser.close()
