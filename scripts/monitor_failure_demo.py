"""Actual staff browser resolution of an exhausted test job on port 8001."""
import json,re
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from browser_demo import ROOT,OUT,login,nav,shot,record,events
evidence=json.loads((OUT/'activity2/observed-jobs.json').read_text())
jid=int(next(k for k,v in evidence.items() if v['job']['attempt_count']==9))
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True)
    page=browser.new_page(viewport={'width':1440,'height':1000})
    page.goto('http://localhost:8001')
    page.wait_for_selector('flt-semantics-placeholder',state='attached')
    page.locator('flt-semantics-placeholder').evaluate('(e)=>e.click()')
    login(page,'registrar@example.test')
    nav(page,'Automation')
    page.get_by_role('button',name=re.compile(f'Job {jid}:')).click()
    expect(page.get_by_text(re.compile('Attempts 9/9')).first).to_be_visible()
    shot(page,'permanent-failure-attempts-desktop.png')
    expect(page.get_by_role('button',name='Retry safely',exact=True)).not_to_be_visible()
    page.get_by_role('button',name='Record manual handling',exact=True).click()
    page.get_by_role('textbox',name='Reason or instructions').fill('Browser-observed synthetic failure inspected; registrar manual handling recorded without claiming notification delivery.')
    with page.expect_response(lambda r:r.url.endswith(f'/api/v1/staff/automation/jobs/{jid}/resolve')) as response:
        page.get_by_role('button',name='Confirm',exact=True).click()
    assert response.value.status==200
    assert response.value.json()['status']=='resolved_manually'
    record('staff_manual_resolution',job_id=jid,status=response.value.json()['status'])
    page.set_viewport_size({'width':390,'height':844})
    page.get_by_role('button',name=re.compile(f'Job {jid}:')).click()
    expect(page.get_by_text(re.compile('Manual handling:')).first).to_be_visible()
    shot(page,'manual-resolution-narrow.png')
    browser.close()
(OUT/'verification/browser-failure-monitor.json').write_text(json.dumps(events,indent=2),encoding='utf-8')
print('PASS actual staff UI: durable exhausted failure, attempts 1–9, no further retry, audited manual handling.')

