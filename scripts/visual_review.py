"""Render the built Flutter UI with explicit visual-test fixtures, not live data.

No database, credentials, or application server is used. These captures verify
presentation and navigation only; they do not prove backend workflow behavior.
Run after flutter build web: backend/.venv/Scripts/python.exe scripts/visual_review.py
"""

import functools
import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.private' / 'visual-review'
VERSION = {
    'id': 1, 'name': 'Certificate of Enrollment', 'version_number': 1,
    'description': 'A certificate confirming enrollment for the current term.',
    'processing_days': 3, 'eligibility_instructions': 'Review the requirements before submitting.',
    'payment': {'required': False, 'receipt_required': False},
    'requirements': [
        {'id': 1, 'label': 'Purpose', 'field_type': 'text', 'required': True,
         'min_length': 3, 'max_length': 200, 'options': []},
    ],
}
REVISION = {
    'revision_number': 1, 'answers': [{'requirement_id': 1, 'text_value': 'Scholarship application'}],
    'attachments': [], 'payment': {'reference': None, 'receipt': None},
}
REQUEST = {
    'id': 1, 'request_number': 'SDRT-VISUAL-001', 'status': 'submitted',
    'service_name': VERSION['name'], 'due_at': '2026-11-15T08:00:00Z',
    'current_revision_number': 1, 'row_version': 1,
    'student': {'full_name': 'Visual Test Student', 'student_number': 'VISUAL-001'},
    'service': {'id': 1, 'version': VERSION}, 'latest_revision': REVISION,
    'open_correction_round': None,
}


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def fixture(path, role):
    actor = {'id': 1, 'role': role, 'full_name': 'Visual Test Student' if role == 'student' else 'Visual Test Registrar',
             'student_number': 'VISUAL-001', 'email': 'visual@example.test', 'can_manage_services': True}
    if path.endswith('/auth/me'):
        return (200, actor) if role else (401, {'code': 'AUTHENTICATION_REQUIRED', 'detail': 'Sign in'})
    if path.endswith('/auth/csrf'):
        return 200, {'csrf_token': 'visual-test-only'}
    if path.endswith('/dashboard'):
        return 200, {'counts': {'submitted': 2, 'under_review': 1, 'needs_correction': 1,
                               'processing': 2, 'ready_for_release': 1, 'completed': 6},
                     'unread_notifications': 0, 'failed_automation_jobs': 0, 'recent_requests': [REQUEST]}
    if path.endswith('/staff/services'):
        return 200, {'items': [
            {'id': 100 + i, 'current_version': dict(VERSION, name=f'Visual Service {i + 1}'),
             'current_version_id': 1, 'service_code': f'VISUAL_{i + 1}',
             'is_active': True, 'has_draft': False}
            for i in range(4)]}
    if path.endswith('/services'):
        return 200, {'items': [{'id': 1, 'name': VERSION['name'], 'description': VERSION['description'],
                               'payment_required': False, 'processing_days': 3}]}
    if path.endswith('/services/1'):
        return 200, {'id': 1, 'version': VERSION}
    if path.endswith('/requests'):
        return 200, {'items': [REQUEST]}
    if path.endswith('/requests/1'):
        return 200, REQUEST
    if path.endswith('/history'):
        return 200, {'items': [{'new_status': 'submitted', 'created_at': '2026-11-12T08:00:00Z',
                                'change_source': 'student', 'public_remarks': 'Request submitted.'}]}
    if path.endswith('/revisions'):
        return 200, {'items': [{'revision_number': 1}]}
    if path.endswith('/revisions/1'):
        return 200, REVISION
    if path.endswith('/staff/reports/daily'):
        return 404, {'code': 'SUMMARY_NOT_GENERATED', 'detail': 'No summary generated'}
    if path.endswith(('/notifications', '/notes', '/staff/alerts', '/staff/automation/jobs', '/staff/automation/runs', '/staff/audit-logs')):
        return 200, {'items': []}
    return 404, {'code': 'VISUAL_FIXTURE_MISSING', 'detail': path}


def enable(page):
    page.wait_for_selector('flt-semantics-placeholder', state='attached')
    page.locator('flt-semantics-placeholder').evaluate('(e) => e.click()')


def navigate(page, name):
    page.get_by_role('button', name='User menu').wait_for()
    page.wait_for_timeout(300)
    menu = page.get_by_role('button', name='Open navigation menu')
    if menu.count():
        menu.click()
    page.wait_for_timeout(300)
    page.get_by_role('button', name=name, exact=True).last.click()
    page.wait_for_timeout(450)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    handler = functools.partial(QuietHandler, directory=str(ROOT / 'build/web'))
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    results = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel='msedge', headless=True)
            for width in [1440, 390]:
                for role in [None, 'student', 'staff']:
                    context = browser.new_context(viewport={'width': width, 'height': 1000 if width == 1440 else 844})
                    page = context.new_page()
                    errors = []
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    page.on('console', lambda message: errors.append(message.text)
                            if message.type == 'error' and ('RenderFlex' in message.text or 'overflowed' in message.text) else None)

                    def intercept(route):
                        status, body = fixture(urlparse(route.request.url).path, role)
                        route.fulfill(status=status, content_type='application/json', body=json.dumps(body))

                    page.route('**/api/v1/**', intercept)
                    page.goto(f'http://127.0.0.1:{server.server_port}')
                    enable(page)

                    def shot(name):
                        page.wait_for_timeout(300)
                        filename = f'{role or "public"}-{name}-{width}.png'
                        page.screenshot(path=str(OUT / filename))
                        results.append({'file': filename, 'data': 'visual fixtures', 'page_errors': list(errors)})

                    if role is None:
                        page.get_by_role('button', name='Sign in', exact=True).wait_for()
                        shot('login')
                        page.get_by_role('button', name='Create student account', exact=True).click()
                        shot('registration')
                    else:
                        page.get_by_role('button', name='User menu').wait_for()
                        shot('dashboard')
                        page.get_by_role('button', name='User menu').click()
                        shot('user-menu')
                        page.get_by_role('menuitem', name='My account', exact=True).click()
                        shot('account')
                        page.get_by_role('button', name='Back', exact=True).click()
                        for name in ['Requests', 'Services', 'Notifications'] + (['Automation'] if role == 'staff' else []):
                            navigate(page, name)
                            shot(name.lower())
                            if name == 'Services' and role == 'staff':
                                carousel = page.get_by_label('Document service focus carousel', exact=True)
                                box = carousel.bounding_box()
                                page.mouse.move(box['x'] + box['width'] / 2, box['y'] + min(box['height'] / 2, 200))
                                page.mouse.wheel(0, 120)
                                page.wait_for_timeout(450)
                                after = carousel.bounding_box()
                                assert abs(after['y'] - box['y']) < 1, 'Carousel wheel moved the surrounding page'
                                shot('services-focused-next')
                                page.get_by_role('button', name='New service', exact=True).click()
                                shot('service-editor')
                                page.get_by_role('button', name='Add requirement', exact=True).click()
                                page.get_by_role('button', name='Answer type Text', exact=True).click()
                                page.keyboard.press('ArrowDown')
                                page.keyboard.press('ArrowDown')
                                page.keyboard.press('ArrowDown')
                                page.keyboard.press('ArrowDown')
                                page.keyboard.press('Enter')
                                page.get_by_label('Maximum file size (bytes)', exact=True).scroll_into_view_if_needed()
                                shot('service-editor-file-requirement')
                                page.get_by_role('button', name='Back', exact=True).click()
                                page.get_by_role('button', name='Leave draft', exact=True).click()
                        navigate(page, 'Requests')
                        page.get_by_text('SDRT-VISUAL-001', exact=False).last.click()
                        shot('detail')
                        if role == 'staff':
                            page.get_by_role('button', name='Begin review', exact=True).click()
                            page.get_by_role('button', name='Confirm', exact=True).wait_for()
                            shot('confirmation')
                            page.get_by_role('button', name='Go back', exact=True).click()
                        else:
                            navigate(page, 'Services')
                            page.get_by_role('button', name=f'View {VERSION["name"]} requirements').click()
                            page.get_by_role('button', name='Create request', exact=True).wait_for()
                            shot('service-dialog')
                            page.get_by_role('button', name='Create request', exact=True).click()
                            shot('request-form')
                    context.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        (OUT / 'results.json').write_text(json.dumps(results, indent=2))
    print(f'Captured {len(results)} fixture-based browser views in {OUT}')
    if any(item['page_errors'] for item in results):
        raise RuntimeError('Browser page errors recorded; inspect results.json')


if __name__ == '__main__':
    main()
