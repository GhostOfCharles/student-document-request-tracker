"""Check real Flutter login against the current local API without logging secrets."""

import json
from datetime import datetime, timezone
from pathlib import Path

from dotenv import dotenv_values
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evidence/week13"


def main():
    password = dotenv_values(ROOT / ".env")["SDRT_SEED_PASSWORD"]
    (OUT / "screenshots").mkdir(parents=True, exist_ok=True)
    (OUT / "verification").mkdir(parents=True, exist_ok=True)
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        for account, destination in [
            ("TEST-001", "Services"),
            ("registrar@example.test", "Automation"),
        ]:
            context = browser.new_context(viewport={"width": 1440, "height": 1000})
            page = context.new_page()
            page.goto("http://localhost:8000")
            page.wait_for_selector("flt-semantics-placeholder", state="attached")
            page.locator("flt-semantics-placeholder").evaluate("e => e.click()")
            if account == "TEST-001":
                expect(page.get_by_role("textbox").first).to_be_visible()
                page.screenshot(path=str(OUT / "screenshots/login-redesign-desktop.png"))
            fields = page.get_by_role("textbox")
            fields.nth(0).click()
            fields.nth(0).press_sequentially(account)
            fields.nth(1).click()
            if account == "TEST-001":
                fields.nth(1).press_sequentially("incorrect-password")
                page.get_by_role("button", name="Sign in", exact=True).click()
                expect(page.get_by_text("The sign-in details are invalid. (INVALID_CREDENTIALS)").last).to_be_visible()
                expect(page.get_by_text("Your session expired. Sign in again.")).to_have_count(0)
                results.append({"check": "incorrect_password_message", "result": "PASS"})
                fields.nth(1).click()
                fields.nth(1).press("Control+a")
                fields.nth(1).press("Backspace")
            fields.nth(1).press_sequentially(password)
            page.get_by_role("button", name="Sign in", exact=True).click()
            expect(page.get_by_role("button", name=destination, exact=True)).to_be_visible(timeout=15000)
            if account == "TEST-001":
                expect(page.get_by_role("textbox", name="Search requests...")).to_be_visible()
                expect(page.get_by_role("button", name="User menu", exact=False)).to_be_visible()
            else:
                expect(page.get_by_role("button", name="Refresh current view")).to_be_enabled()
                expect(page.get_by_role("button", name="Automation", exact=True)).to_be_visible()
            screenshot = "student-dashboard-desktop.png" if account == "TEST-001" else "staff-dashboard-existing.png"
            page.screenshot(path=str(OUT / "screenshots" / screenshot))
            results.append({"check": "browser_login", "account": account, "result": "PASS", "screenshot": "screenshots/" + screenshot})
            if account == "TEST-001":
                page.get_by_role("button", name="Services", exact=True).click()
                expect(page.get_by_text("Document services", exact=True)).to_be_visible()
                page.screenshot(path=str(OUT / "screenshots/student-services-desktop.png"))
                page.get_by_role("button", name="View Certificate of Good Moral requirements").click()
                page.get_by_role("button", name="Create request", exact=True).click()
                expect(page.get_by_role("textbox", name="Purpose of request *")).to_be_visible()
                page.screenshot(path=str(OUT / "screenshots/student-request-form-desktop.png"))
                results.append({"check": "services_and_dynamic_form", "result": "PASS", "screenshots": ["screenshots/student-services-desktop.png", "screenshots/student-request-form-desktop.png"]})
                page.get_by_role("button", name="Notifications", exact=True).last.click()
                page.get_by_role("button", name="Confirm", exact=True).click()
                expect(page.get_by_text("Recent updates", exact=True)).to_be_visible()
                page.screenshot(path=str(OUT / "screenshots/student-notifications-desktop.png"))
                page.get_by_role("button", name="Requests", exact=True).click()
                expect(page.get_by_text("My requests", exact=True)).to_be_visible()
                page.screenshot(path=str(OUT / "screenshots/student-requests-desktop.png"))
                results.append({"check": "notifications_and_request_list", "result": "PASS", "screenshots": ["screenshots/student-notifications-desktop.png", "screenshots/student-requests-desktop.png"]})
                narrow = context.new_page()
                narrow.set_viewport_size({"width": 390, "height": 844})
                narrow.goto("http://localhost:8000")
                narrow.wait_for_selector("flt-semantics-placeholder", state="attached")
                narrow.locator("flt-semantics-placeholder").evaluate("e => e.click()")
                expect(narrow.get_by_text("Your request overview", exact=True)).to_be_visible(timeout=15000)
                expect(narrow.get_by_role("button", name="Open navigation menu")).to_be_visible()
                narrow.screenshot(path=str(OUT / "screenshots/student-dashboard-narrow.png"))
                narrow.get_by_role("button", name="Open navigation menu").click()
                expect(narrow.get_by_role("button", name="Services", exact=True)).to_be_visible()
                narrow.get_by_role("button", name="Services", exact=True).click()
                expect(narrow.get_by_text("Document services", exact=True)).to_be_visible()
                results.append({"check": "narrow_drawer_navigation", "viewport": "390x844", "result": "PASS", "screenshot": "screenshots/student-dashboard-narrow.png"})
            context.close()
        browser.close()
    report = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "base_url": "http://localhost:8000", "checks": results}
    (OUT / "verification/student-ui-smoke.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
