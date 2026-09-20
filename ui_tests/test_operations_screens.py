"""UI + local backend contracts to run in the final consolidated verification phase."""

from playwright.sync_api import expect

from conftest import login


def test_incident_creation_assignment_and_notes(browser_page):
    page, origin = browser_page
    login(page, origin)
    page.goto(origin + "/#incidents/main")
    page.get_by_role("button", name="+ Create alert", exact=True).click()
    dialog = page.get_by_role("dialog")
    dialog.get_by_label("Name", exact=True).fill("SIMULATOR browser incident")
    dialog.get_by_label("Description", exact=True).fill("Synthetic connection investigation")
    dialog.get_by_role("button", name="Save", exact=True).click()
    expect(page.get_by_role("heading", name="SIMULATOR browser incident", exact=True)).to_be_visible()
    page.get_by_label("Workflow status", exact=True).select_option("in_progress")
    page.get_by_label("Response note", exact=True).fill("Investigating the synthetic equipment")
    page.get_by_role("button", name="Save response", exact=True).click()
    page.get_by_label("Investigation note", exact=True).fill("The logger simulator recovered")
    page.get_by_role("button", name="Add note", exact=True).click()
    page.get_by_role("tab", name="Timeline", exact=True).click()
    expect(page.get_by_text("The logger simulator recovered", exact=True)).to_be_visible()
    page.get_by_role("button", name="Create work order", exact=True).click()
    dialog.get_by_label("Work instructions", exact=True).fill("Inspect the synthetic logger")
    dialog.get_by_role("button", name="Save", exact=True).click()
    page.get_by_role("tab", name="Related", exact=True).click()
    expect(page.get_by_role("heading", name="Linked work orders", exact=True)).to_be_visible()


def test_viewer_cannot_create_or_change_incidents(browser_page):
    page, origin = browser_page
    login(page, origin, "ui-viewer")
    page.goto(origin + "/#incidents/main")
    expect(page.get_by_role("heading", name="Alert list", exact=True)).to_be_visible()
    expect(page.get_by_role("button", name="+ Create alert", exact=True)).to_have_count(0)
    expect(page.get_by_role("button", name="Save response", exact=True)).to_have_count(0)


def test_global_shell_styles_and_bilingual_navigation(browser_page):
    page, origin = browser_page
    login(page, origin)
    for route in ("incidents/main", "incidents/playbooks", "operations/schedule-plans", "reports/mapping"):
        page.goto(origin + "/#" + route)
        expect(page.get_by_role("navigation", name="Main navigation")).to_have_count(1)
        expect(page.locator('link[rel="stylesheet"]')).to_have_count(1)
        expect(page.locator('link[rel="stylesheet"]')).to_have_attribute("href", "/static/app.css")
        expect(page.locator("style")).to_have_count(0)
        expect(page.get_by_text("Could not load this page", exact=True)).to_have_count(0)
    page.get_by_label("Language / Ngôn ngữ").select_option("vi")
    expect(page.locator("html")).to_have_attribute("lang", "vi")
    page.goto(origin + "/#incidents/main")
    expect(page.get_by_role("heading", name="Danh sách cảnh báo", exact=True)).to_be_visible()


def test_incident_workspace_reflows_on_small_screen(browser_page):
    page, origin = browser_page
    login(page, origin)
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(origin + "/#incidents/main")
    expect(page.get_by_role("heading", name="Alert list", exact=True)).to_be_visible()
    columns = page.locator(".workbench-layout").evaluate("node => getComputedStyle(node).gridTemplateColumns")
    assert len(columns.split()) == 1
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 2")
