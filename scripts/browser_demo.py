"""Actual Flutter Web acceptance through headless Microsoft Edge; synthetic data only."""

import os, sys, json, re, time
from pathlib import Path
from datetime import datetime, timezone
from dotenv import dotenv_values
from PIL import Image
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
cfg = dotenv_values(ROOT / ".env")
password = cfg["SDRT_SEED_PASSWORD"]
OUT = ROOT / "evidence/week13"
events = []


def record(event, **details):
    item = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **details,
    }
    events.append(item)
    print(json.dumps(item), flush=True)


def shot(page, name):
    page.screenshot(path=str(OUT / "screenshots" / name))
    record("screenshot", path="screenshots/" + name)


def enable(page):
    page.goto("http://localhost:8000")
    page.wait_for_selector("flt-semantics-placeholder", state="attached")
    page.locator("flt-semantics-placeholder").evaluate("(e)=>e.click()")
    expect(page.get_by_role("textbox").first).to_be_visible()


def login(page, email):
    page.get_by_role("textbox").nth(0).click()
    page.get_by_role("textbox").nth(0).press_sequentially(email)
    page.get_by_role("textbox").nth(1).click()
    page.get_by_role("textbox").nth(1).press_sequentially(password)
    page.get_by_role("button", name="Sign in", exact=True).click()
    expect(page.get_by_role("button", name="Services", exact=True)).to_be_visible()
    record("login", account=email)


def nav(page, name):
    paths={'Dashboard':'/dashboard','Services':'/services','Requests':'/requests','Notifications':'/notifications','Automation':'/staff/automation/jobs'}
    with page.expect_response(lambda r:r.url.split('?')[0].endswith('/api/v1'+paths[name]) and r.request.method=='GET'):
        page.get_by_role("button", name=name, exact=True).click()
    expect(page.get_by_role('button',name='Refresh current view')).to_be_enabled()


def confirm_action(page, name, expected=(200, 201)):
    page.get_by_role("button", name=name, exact=True).click()
    with page.expect_response(
        lambda r: "/api/v1/" in r.url and r.request.method == "POST"
    ) as response:
        page.get_by_role("button", name="Confirm", exact=True).click()
    assert response.value.status in expected, (
        name,
        response.value.status,
        response.value.json(),
    )
    expect(page.get_by_role("button", name="Refresh current view")).to_be_enabled()
    if response.value.status < 400:
        expect(page.get_by_text("Action saved.", exact=True).last).to_be_visible()
    record("workflow_action", action=name, status=response.value.status)


def upload(page, button, path):
    with page.expect_file_chooser() as chooser:
        page.get_by_role("button", name=button, exact=True, disabled=False).click()
    with page.expect_response(
        lambda r: r.url.endswith("/api/v1/files/staging") and r.request.method == "POST"
    ) as response:
        chooser.value.set_files(str(path))
    assert response.value.status == 201, response.value.json()
    expect(
        page.get_by_role("button", name="Submit request", exact=True)
    ).to_be_enabled()
    record("private_upload", file_id=response.value.json()["id"], filename=path.name)


def main():
    sample = ROOT / ".private/browser-synthetic.png"
    sample.parent.mkdir(exist_ok=True)
    Image.new("RGB", (160, 100), "skyblue").save(sample)
    replacement = ROOT / ".private/browser-replacement.png"
    Image.new("RGB", (180, 110), "orange").save(replacement)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        student_context = browser.new_context(viewport={"width": 1440, "height": 1000})
        staff_context = browser.new_context(viewport={"width": 1440, "height": 1000})
        student = student_context.new_page()
        staff = staff_context.new_page()
        errors = []
        for page in (student, staff):
            page.on("pageerror", lambda e: errors.append(str(e)))
        enable(student)
        shot(student, "login-desktop.png")
        student.get_by_role("button", name="Sign in", exact=True).click()
        expect(
            student.get_by_text("Enter your login.", exact=True).last
        ).to_be_visible()
        shot(student, "login-validation.png")
        login(student, "student@example.test")
        shot(student, "student-dashboard-desktop.png")
        nav(student, "Services")
        student.get_by_role(
            "button", name=re.compile("Certificate of Enrollment")
        ).click()
        shot(student, "service-requirements.png")
        student.get_by_role("button", name="Create request", exact=True).click()
        expect(
            student.get_by_role("textbox", name=re.compile("Purpose of request"))
        ).to_be_visible()
        record("form_accessibility", snapshot=student.locator("body").aria_snapshot())
        shot(student, "dynamic-form-desktop.png")
        # Continue after inspecting real accessibility roles if a renderer differs.
        purpose = student.get_by_role("textbox", name=re.compile("Purpose of request"))
        purpose.click()
        purpose.press_sequentially("Browser synthetic scholarship")
        expect(purpose).to_have_value("Browser synthetic scholarship")
        student.get_by_role("button", name=re.compile("Request category")).click()
        student.get_by_role("menuitem", name="Scholarship", exact=True).click()
        expect(student.get_by_role("menu", name="Popup menu")).not_to_be_visible()
        checkbox = student.get_by_role("checkbox", name=re.compile("I confirm"))
        checkbox.click()
        expect(checkbox).to_be_checked()
        upload(student, "Upload Supporting evidence", sample)
        reference=student.get_by_role('textbox',name='Fictional payment reference')
        reference.click()
        reference.press_sequentially('FICTIONAL-BROWSER-001')
        upload(student, "Upload fictional receipt", sample)
        shot(student, "filled-submission-form.png")
        record("filled_form", snapshot=student.locator("body").aria_snapshot())
        with student.expect_response(
            lambda r: r.url.endswith("/api/v1/requests") and r.request.method == "POST"
        ) as response:
            student.get_by_role("button", name="Submit request", exact=True).click()
            record(
                "submission_prompt", snapshot=student.locator("body").aria_snapshot()
            )
            student.get_by_role("button", name="Confirm submit", exact=True).click()
        result = response.value.json()
        assert response.value.status == 201, result
        rid = result["id"]
        number = result["request_number"]
        expect(student.get_by_text(re.compile("Submission confirmed:"))).to_be_visible()
        shot(student, "submission-confirmation.png")
        record("submitted", request_id=rid, request_number=number)
        enable(staff)
        login(staff, "registrar@example.test")
        nav(staff, "Requests")
        staff.get_by_role("button", name=re.compile(number)).click()
        confirm_action(staff, "Begin review")
        shot(staff, "staff-review-payment.png")
        confirm_action(staff, "Approve requirements", expected=(409,))
        expect(staff.get_by_role('button',name='Retry / reload current state',exact=True)).to_be_visible()
        shot(staff, "adverse-payment-not-verified.png")
        staff.get_by_role("button", name="Request correction", exact=True).click()
        staff.get_by_role("button", name="Supporting evidence", exact=True).click()
        instructions=staff.get_by_role('textbox',name='Reason or instructions')
        instructions.click()
        instructions.press_sequentially('Replace with the orange synthetic example.')
        staff.get_by_role("button", name="Confirm", exact=True).click()
        staff.get_by_role("button", name="Confirm", exact=True).click()
        expect(staff.get_by_text("Needs Correction", exact=False).first).to_be_visible()
        student.get_by_role("button", name="Refresh current view").click()
        student.get_by_role("button", name="Correct and resubmit", exact=True).click()
        shot(student, "correction-form.png")
        upload(student, "Replace Supporting evidence: browser-synthetic.png", replacement)
        student.get_by_role("button", name="Submit request", exact=True).click()
        student.get_by_role("button", name="Confirm submit", exact=True).click()
        expect(
            student.get_by_text(re.compile("Submission confirmed:.*revision 2"))
        ).to_be_visible()
        record("correction_resubmitted", request_id=rid)
        staff.get_by_role("button", name="Refresh current view").click()
        confirm_action(staff, "Payment: Verified")
        confirm_action(staff, "Approve requirements")
        confirm_action(staff, "Mark ready for release")
        confirm_action(staff, "Confirm actual handover")
        student.get_by_role("button", name="Refresh current view").click()
        confirm_action(student, "Acknowledge receipt")
        expect(student.get_by_text(re.compile("Completed.*revision 2"))).to_be_visible()
        shot(student, "completed-timeline-desktop.png")
        student.get_by_role("button", name="View revision 1", exact=True).click()
        shot(student, "immutable-original-revision.png")
        student.get_by_role("button", name="Close", exact=True).click()
        record("paid_lifecycle_complete", request_id=rid, revisions=2)
        student.set_viewport_size({"width": 390, "height": 844})
        shot(student, "tracking-narrow.png")
        nav(student, "Services")
        shot(student, "services-narrow.png")
        # Offline browser state is a real failed HTTP request, not a fake response.
        student_context.set_offline(True)
        student.get_by_role("button", name="Refresh current view").click()
        expect(student.get_by_text(re.compile("NETWORK_ERROR"))).to_be_visible(
            timeout=30000
        )
        shot(student, "network-error-narrow.png")
        student_context.set_offline(False)
        student.get_by_role(
            "button", name="Retry / reload current state", exact=True
        ).click()
        nav(staff, "Automation")
        shot(staff, "automation-monitor-desktop.png")
        staff.get_by_role(
            "button", name="Regenerate current local date", exact=True
        ).click()
        expect(staff.get_by_text(re.compile("Asia/Manila date"))).to_be_visible()
        staff.set_viewport_size({"width": 390, "height": 844})
        shot(staff, "automation-monitor-narrow.png")
        # Notifications are delivered by the designated scheduler, never faked.
        nav(student, "Notifications")
        # Wait at most one real one-minute worker interval using repeated short UI checks.
        for _ in range(75):
            if student.get_by_role("button", name=re.compile(number)).count():
                break
            student.wait_for_timeout(1000)
            student.get_by_role("button", name="Refresh current view").click()
        expect(
            student.get_by_role("button", name=re.compile(number)).first
        ).to_be_visible()
        shot(student, "student-notifications-narrow.png")
        assert not errors, errors
        record(
            "browser_acceptance_pass",
            request_id=rid,
            console_errors=errors,
            viewports=["1440x1000", "390x844"],
        )
        browser.close()


if __name__ == "__main__":
    try:
        main()
    finally:
        (OUT / "verification/browser-events.json").write_text(
            json.dumps(events, indent=2), encoding="utf-8"
        )
