"""Responsive staff UI smoke test against the live local Flutter Web/FastAPI app."""
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from dotenv import dotenv_values
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evidence/week13/screenshots/staff-visual'
REPORT = ROOT / 'evidence/week13/verification/staff-visual-smoke.json'
BASE = 'http://localhost:8000'
PASSWORD = dotenv_values(ROOT / '.env')['SDRT_SEED_PASSWORD']
checks = []
errors = []


def shot(page, name, check):
    path = OUT / name
    if page.viewport_size['width'] < 900 and 'dialog' in check:
        dialog = page.get_by_role('alertdialog')
        if dialog.count():
            bounds = dialog.bounding_box()
            assert bounds is not None and bounds['x'] >= 0 and bounds['x'] + bounds['width'] <= page.viewport_size['width'], bounds
    page.screenshot(path=str(path), full_page=page.viewport_size['width'] >= 900)
    checks.append({'check': check, 'result': 'PASS', 'viewport': page.viewport_size, 'screenshot': str(path.relative_to(ROOT)).replace('\\', '/')})


def navigate(page, name):
    path = {'Dashboard': '/dashboard', 'Services': '/services', 'Requests': '/requests', 'Notifications': '/notifications', 'Automation': '/staff/automation/jobs'}[name]
    narrow = page.viewport_size['width'] < 900
    if narrow:
        menu = page.get_by_role('button', name='Open navigation menu')
        expect(menu).to_be_visible()
        menu.click()
        expect(page.get_by_role('button', name=name, exact=True).last).to_be_visible()
    with page.expect_response(lambda r: r.url.split('?')[0].endswith('/api/v1' + path) and r.request.method == 'GET'):
        page.get_by_role('button', name=name, exact=True).last.click()
    if narrow:
        expect(page.get_by_role('button', name='Dismiss')).to_have_count(0)


def close_dialog(page):
    close = page.get_by_role('button', name='Close', exact=True)
    if close.count():
        close.first.click()
    else:
        page.keyboard.press('Escape')
    expect(page.get_by_role('alertdialog')).to_have_count(0)


def screen_set(page, suffix):
    shot(page, f'staff-dashboard-{suffix}.png', f'staff_dashboard_{suffix}')
    navigate(page, 'Services')
    shot(page, f'staff-services-{suffix}.png', f'staff_services_{suffix}')
    service = page.get_by_role('button', name=re.compile('Certificate of Good Moral'))
    if service.count():
        service.first.click()
        expect(page.get_by_role('button', name='Close', exact=True)).to_be_visible()
        shot(page, f'staff-dialog-service-{suffix}.png', f'service_dialog_{suffix}')
        close_dialog(page)
    navigate(page, 'Requests')
    shot(page, f'staff-request-queue-{suffix}.png', f'staff_request_queue_{suffix}')
    rows = page.get_by_role('button', name=re.compile(r'SDRT-20'))
    if rows.count():
        rows.first.click()
        expect(page.get_by_text(re.compile('registrar review'))).to_be_visible()
        shot(page, f'staff-request-detail-{suffix}.png', f'staff_request_detail_{suffix}')
        note = page.get_by_role('button', name='Add Student Visible note', exact=True)
        if note.count():
            note.click()
            expect(page.get_by_role('textbox', name='Note')).to_be_visible()
            shot(page, f'staff-dialog-note-{suffix}.png', f'note_dialog_{suffix}')
            page.keyboard.press('Escape')
        revision = page.get_by_role('button', name='View revision 1', exact=True)
        if revision.count():
            revision.click()
            expect(page.get_by_role('button', name='Close', exact=True)).to_be_visible()
            shot(page, f'staff-dialog-revision-{suffix}.png', f'revision_dialog_{suffix}')
            close_dialog(page)
    navigate(page, 'Notifications')
    shot(page, f'staff-notifications-{suffix}.png', f'staff_notifications_{suffix}')
    navigate(page, 'Automation')
    shot(page, f'staff-automation-{suffix}.png', f'staff_automation_{suffix}')
    job = page.get_by_role('button', name=re.compile(r'Job\s+\d+'))
    if job.count():
        job.first.click()
        expect(page.get_by_role('button', name='Close', exact=True)).to_be_visible()
        shot(page, f'staff-dialog-job-{suffix}.png', f'job_dialog_{suffix}')
        close_dialog(page)
    page.get_by_role('button', name='User menu').click()
    page.get_by_role('menuitem', name='Sign out', exact=True).click()
    expect(page.get_by_text('Leave this development session?', exact=True)).to_be_visible()
    shot(page, f'staff-dialog-signout-{suffix}.png', f'signout_dialog_{suffix}')
    page.keyboard.press('Escape')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1000})
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(BASE)
        page.wait_for_selector('flt-semantics-placeholder', state='attached')
        page.locator('flt-semantics-placeholder').evaluate('(e) => e.click()')
        expect(page.get_by_role('textbox').first).to_be_visible()
        page.get_by_role('textbox').nth(0).click()
        page.get_by_role('textbox').nth(0).press_sequentially('registrar@example.test')
        page.get_by_role('textbox').nth(1).click()
        page.get_by_role('textbox').nth(1).press_sequentially(PASSWORD)
        page.get_by_role('button', name='Sign in', exact=True).click()
        expect(page.get_by_role('button', name='User menu')).to_be_visible(timeout=15000)
        screen_set(page, 'desktop')
        page.set_viewport_size({'width': 390, 'height': 844})
        page.goto(BASE)
        page.wait_for_selector('flt-semantics-placeholder', state='attached')
        page.locator('flt-semantics-placeholder').evaluate('(e) => e.click()')
        expect(page.get_by_role('button', name='User menu')).to_be_visible(timeout=15000)
        screen_set(page, 'narrow')
        assert not errors, errors
        checks.append({'check': 'browser_page_errors', 'result': 'PASS', 'count': 0})
        browser.close()
    report = {'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'base_url': BASE, 'checks': checks, 'page_errors': errors}
    REPORT.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
