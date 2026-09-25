"""Authored with the maintenance UI; reserved for the final combined QA run."""

from datetime import datetime, timedelta

from conftest import login
from playwright.sync_api import expect


def test_work_plan_result_time_and_independent_approval(browser_page):
    page, origin = browser_page
    login(page, origin)
    page.goto(origin + "/#incidents/jobs")
    page.get_by_role("button", name="+ Create work order", exact=True).click()
    dialog = page.get_by_role("dialog")
    dialog.get_by_label("Work title", exact=True).fill("SIMULATOR browser maintenance")
    dialog.get_by_role("button", name="Create work order", exact=True).click()
    expect(page.get_by_role("heading", name="SIMULATOR browser maintenance", exact=True)).to_be_visible()
    page.get_by_role("button", name="Plan this work", exact=True).click()
    dialog.get_by_label("Prerequisites and safety notes", exact=True).fill(
        "Synthetic fixture: no real hardware"
    )
    dialog.get_by_label("Step title", exact=True).fill("Inspect synthetic logger")
    dialog.get_by_label("Instructions", exact=True).fill("Record the simulated connection status")
    dialog.get_by_label("Reason for this plan or change", exact=True).fill("Initial plan")
    dialog.get_by_role("button", name="Save", exact=True).click()
    page.get_by_role("button", name="Record result", exact=True).click()
    dialog.get_by_label("Result", exact=True).select_option("pass")
    dialog.get_by_label("Measurements / evidence / reason", exact=True).fill("SIMULATOR connection observed")
    dialog.get_by_role("button", name="Save", exact=True).click()
    page.get_by_role("tab", name="Time entries", exact=True).click()
    page.get_by_role("button", name="+ Record work time", exact=True).click()
    now = datetime.now().astimezone()
    dialog.get_by_label("Start", exact=True).fill((now - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M"))
    dialog.get_by_label("End", exact=True).fill((now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M"))
    dialog.get_by_label("Work performed", exact=True).fill("Synthetic logger inspection")
    dialog.get_by_role("button", name="Save", exact=True).click()
    page.get_by_role("tab", name="Execution & Checklist", exact=True).click()
    page.get_by_role("button", name="Submit for independent review", exact=True).click()
    dialog.get_by_label("Note", exact=True).fill("Ready for the independent fixture reviewer")
    dialog.get_by_role("button", name="Save", exact=True).click()
    expect(page.get_by_text("4-eyes principle:", exact=False)).to_be_visible()
    expect(page.get_by_role("button", name="Approve completion", exact=True)).to_have_count(0)
    page.get_by_role("button", name="Sign out", exact=True).click()
    login(page, origin, "ui-reviewer")
    page.goto(origin + "/#incidents/jobs")
    page.get_by_label("Search work", exact=True).fill("SIMULATOR browser maintenance")
    page.get_by_role("button", name="Filter work", exact=True).click()
    page.get_by_role("button", name="Approve completion", exact=True).click()
    dialog.get_by_label("Note", exact=True).fill("Independent fixture evidence review")
    dialog.get_by_role("button", name="Save", exact=True).click()
    expect(page.get_by_role("heading", name="Independent review", exact=True)).to_be_visible()
    expect(page.get_by_text("Independent fixture evidence review", exact=True)).to_be_visible()


def test_maintenance_navigation_shares_shell_and_viewer_is_read_only(browser_page):
    page, origin = browser_page
    login(page, origin, "ui-viewer")
    page.goto(origin + "/#incidents/health")
    navigation = page.get_by_role("navigation", name="Main navigation")
    expect(navigation.get_by_role("button", name="Maintenance", exact=True)).to_have_attribute(
        "aria-current", "page"
    )
    expect(page.get_by_role("tab", name="System health", exact=True)).to_be_visible()
    expect(page.get_by_role("tab", name="Firmware & OTA", exact=True)).to_be_visible()
    expect(
        page.get_by_role("heading", name="Connectivity, measurements and work", exact=True)
    ).to_be_visible()
    page.get_by_role("tab", name="Work orders", exact=True).click()
    expect(page.get_by_role("button", name="+ Create work order", exact=True)).to_have_count(0)
    expect(page.get_by_role("button", name="Plan this work", exact=True)).to_have_count(0)
    expect(page.locator('link[rel="stylesheet"]')).to_have_count(1)
    expect(page.locator("style")).to_have_count(0)
    page.get_by_role("tab", name="Maintenance plans", exact=True).click()
    page.get_by_role("tab", name="90-day service calendar", exact=True).click()
    expect(page.get_by_label("Until date (exclusive)", exact=True)).to_be_visible()
