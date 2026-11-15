"""Capture comprehensive Week 15 verification screenshots across Staff and Student portals."""
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from dotenv import dotenv_values
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
OUT_W15 = ROOT / "evidence/week15/screenshots"
OUT_W13 = ROOT / "evidence/week13/screenshots"
VERIFY_W15 = ROOT / "evidence/week15/verification"
PASSWORD = dotenv_values(ROOT / ".env")["SDRT_SEED_PASSWORD"]
BASE = "http://localhost:8000"

OUT_W15.mkdir(parents=True, exist_ok=True)
OUT_W13.mkdir(parents=True, exist_ok=True)
VERIFY_W15.mkdir(parents=True, exist_ok=True)

manifest = []


def record(name, category, viewport, dests):
    entry = {
        "name": name,
        "category": category,
        "viewport": viewport,
        "files": [str(d.relative_to(ROOT)).replace("\\", "/") for d in dests],
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }
    manifest.append(entry)


def capture():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)

        # -------------------------------------------------------------
        # 1. Staff: Request Review & Detail (Desktop & Mobile)
        # -------------------------------------------------------------
        ctx_staff_desktop = browser.new_context(viewport={"width": 1440, "height": 950})
        page = ctx_staff_desktop.new_page()
        page.goto(BASE)
        page.wait_for_selector("flt-semantics-placeholder", state="attached")
        page.locator("flt-semantics-placeholder").evaluate("e => e.click()")

        # Login as Registrar
        fields = page.get_by_role("textbox")
        fields.nth(0).click()
        fields.nth(0).press_sequentially("registrar@example.test")
        fields.nth(1).click()
        fields.nth(1).press_sequentially(PASSWORD)
        page.get_by_role("button", name="Sign in", exact=True).click()

        page.get_by_role("button", name="Requests", exact=True).wait_for(timeout=15000)
        time.sleep(1)

        # Dashboard shot
        p1 = OUT_W15 / "staff-dashboard-desktop.png"
        page.screenshot(path=str(p1), full_page=True)
        record("staff_dashboard_desktop", "Staff Dashboard", "1440x950", [p1])

        # Navigate to Requests and select SDRT-2026-000001
        page.get_by_role("button", name="Requests", exact=True).click()
        time.sleep(1.5)
        page.get_by_text("SDRT-2026-000001").first.click()
        time.sleep(2)

        # Staff Request Review Desktop (2-column layout)
        p2 = OUT_W15 / "request-review-desktop.png"
        p2_w13 = OUT_W13 / "staff-request-detail-desktop.png"
        page.screenshot(path=str(p2), full_page=True)
        page.screenshot(path=str(p2_w13), full_page=True)
        record("request_review_desktop", "Staff Review & Actions", "1440x950", [p2, p2_w13])

        # Services Management screen
        page.get_by_role("button", name="Services", exact=True).click()
        time.sleep(1.5)
        p3 = OUT_W15 / "service-management-desktop.png"
        page.screenshot(path=str(p3), full_page=True)
        record("service_management_desktop", "Services & Versioning", "1440x950", [p3])

        ctx_staff_desktop.close()

        # Staff Request Review Mobile (390x844)
        ctx_staff_mobile = browser.new_context(viewport={"width": 390, "height": 844})
        m_page = ctx_staff_mobile.new_page()
        m_page.goto(BASE)
        m_page.wait_for_selector("flt-semantics-placeholder", state="attached")
        m_page.locator("flt-semantics-placeholder").evaluate("e => e.click()")

        m_fields = m_page.get_by_role("textbox")
        m_fields.nth(0).click()
        m_fields.nth(0).press_sequentially("registrar@example.test")
        m_fields.nth(1).click()
        m_fields.nth(1).press_sequentially(PASSWORD)
        m_page.get_by_role("button", name="Sign in", exact=True).click()

        expect(m_page.get_by_role("button", name="User menu")).to_be_visible(timeout=15000)
        menu = m_page.get_by_role("button", name="Open navigation menu")
        expect(menu).to_be_visible()
        menu.click()
        m_req = m_page.get_by_role("button", name="Requests", exact=True).last
        expect(m_req).to_be_visible()
        m_req.click()
        time.sleep(1.5)
        m_page.get_by_text("SDRT-2026-000001").first.click()
        time.sleep(2)

        p4 = OUT_W15 / "request-review-mobile.png"
        p4_w13 = OUT_W13 / "staff-request-detail-narrow.png"
        m_page.screenshot(path=str(p4), full_page=True)
        m_page.screenshot(path=str(p4_w13), full_page=True)
        record("request_review_mobile", "Staff Review & Actions (Mobile)", "390x844", [p4, p4_w13])

        ctx_staff_mobile.close()

        # -------------------------------------------------------------
        # 2. Student: Request Detail & Progress View (Desktop & Mobile)
        # -------------------------------------------------------------
        ctx_stud_desktop = browser.new_context(viewport={"width": 1440, "height": 950})
        s_page = ctx_stud_desktop.new_page()
        s_page.goto(BASE)
        s_page.wait_for_selector("flt-semantics-placeholder", state="attached")
        s_page.locator("flt-semantics-placeholder").evaluate("e => e.click()")

        # Login as Student
        s_fields = s_page.get_by_role("textbox")
        s_fields.nth(0).click()
        s_fields.nth(0).press_sequentially("TEST-001")
        s_fields.nth(1).click()
        s_fields.nth(1).press_sequentially(PASSWORD)
        s_page.get_by_role("button", name="Sign in", exact=True).click()

        s_page.get_by_role("button", name="Requests", exact=True).wait_for(timeout=15000)
        time.sleep(1)

        # Student Dashboard shot
        p5 = OUT_W15 / "student-dashboard-desktop.png"
        s_page.screenshot(path=str(p5), full_page=True)
        record("student_dashboard_desktop", "Student Portal", "1440x950", [p5])

        # Navigate to Requests and open detail
        s_page.get_by_role("button", name="Requests", exact=True).click()
        time.sleep(1.5)
        s_page.get_by_text("SDRT-2026-000001").first.click()
        time.sleep(2)

        # Student Request Detail Desktop
        p6 = OUT_W15 / "student-request-detail-desktop.png"
        s_page.screenshot(path=str(p6), full_page=True)
        record("student_request_detail_desktop", "Student Request Status", "1440x950", [p6])

        ctx_stud_desktop.close()

        # Student Request Detail Mobile (390x844)
        ctx_stud_mobile = browser.new_context(viewport={"width": 390, "height": 844})
        sm_page = ctx_stud_mobile.new_page()
        sm_page.goto(BASE)
        sm_page.wait_for_selector("flt-semantics-placeholder", state="attached")
        sm_page.locator("flt-semantics-placeholder").evaluate("e => e.click()")

        sm_fields = sm_page.get_by_role("textbox")
        sm_fields.nth(0).click()
        sm_fields.nth(0).press_sequentially("TEST-001")
        sm_fields.nth(1).click()
        sm_fields.nth(1).press_sequentially(PASSWORD)
        sm_page.get_by_role("button", name="Sign in", exact=True).click()

        expect(sm_page.get_by_role("button", name="User menu")).to_be_visible(timeout=15000)
        sm_menu = sm_page.get_by_role("button", name="Open navigation menu")
        expect(sm_menu).to_be_visible()
        sm_menu.click()
        sm_req = sm_page.get_by_role("button", name="Requests", exact=True).last
        expect(sm_req).to_be_visible()
        sm_req.click()
        time.sleep(1.5)
        sm_page.get_by_text("SDRT-2026-000001").first.click()
        time.sleep(2)

        p7 = OUT_W15 / "student-request-detail-mobile.png"
        sm_page.screenshot(path=str(p7), full_page=True)
        record("student_request_detail_mobile", "Student Request Status (Mobile)", "390x844", [p7])

        ctx_stud_mobile.close()
        browser.close()

    # Save manifest
    manifest_path = VERIFY_W15 / "visual-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Captured {len(manifest)} views and saved manifest to {manifest_path}")


if __name__ == "__main__":
    capture()
