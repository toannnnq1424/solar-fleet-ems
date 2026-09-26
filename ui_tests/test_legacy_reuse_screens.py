"""Model, residential EMS and motion contracts on the isolated local fixture."""

import json
from datetime import UTC, datetime, timedelta

from conftest import login
from playwright.sync_api import expect
from test_audit_workflows import ROOT, ready


def test_model_profile_plan_decode_home_assistant_and_bilingual_layout(browser_page):
    page, origin = browser_page
    login(page, origin, "ui-admin")
    page.goto(origin + "/#devices/main")
    ready(page)
    page.get_by_role("button", name="Modbus Register Inspector", exact=True).click()
    page.get_by_label("Find profile", exact=True).fill("Solis RHI")
    page.get_by_role("button", name="Open profile", exact=True).click()
    page.get_by_label("Select powerKW", exact=True).check()
    page.get_by_role("button", name="Preview read plan", exact=True).click()
    expect(page.get_by_role("heading", name="Read plan", exact=True)).to_be_visible()
    expect(page.locator("#content")).to_contain_text("33057")
    page.get_by_label("Collected readings (JSON: function, address, value)", exact=True).fill(
        json.dumps(
            [{"function": 4, "address": 33057, "value": 0}, {"function": 4, "address": 33058, "value": 1000}]
        )
    )
    page.get_by_role("button", name="Decode readings", exact=True).click()
    expect(page.locator("#content")).to_contain_text("1 kW")
    expect(page.locator("#content")).to_contain_text("UNVERIFIED")
    page.get_by_role("button", name="Prepare Home Assistant configuration", exact=True).click()
    config = json.loads(page.get_by_label("Collection configuration JSON", exact=True).input_value())
    assert config["bindings"][0]["entity_id"] == "sensor." and "token" not in config
    page.get_by_label("Language / Ngôn ngữ").select_option("vi")
    expect(page.get_by_label("Tìm profile", exact=True)).to_be_visible()
    expect(page.locator('link[rel="stylesheet"]')).to_have_count(1)
    expect(page.locator("style")).to_have_count(0)
    page.set_viewport_size({"width": 430, "height": 900})
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")


def test_ems_baseline_uses_actual_cold_start_and_keeps_commands_empty(browser_page):
    page, origin = browser_page
    login(page, origin)
    page.goto(origin + "/#operations/main/rules")
    ready(page)
    page.get_by_role("button", name="Calculate 24-hour baseline", exact=True).click()
    expect(page.locator("#content")).to_contain_text("SINGLE_VERIFIED_SOURCE_REQUIRED")
    expect(page.locator("#content")).to_contain_text("0 dates")


def test_energy_flow_directions_expiry_motion_preferences_and_routes(browser_page):
    page, origin = browser_page
    login(page, origin, "ui-admin")
    now = datetime.now(UTC)
    values = {
        "pv_w": 6820,
        "grid_w": -150,
        "battery_w": 2500,
        "load_w": 4170,
        "eps_w": None,
        "battery_soc": 68,
    }
    snapshot = values | {
        "channels": {
            k: {
                "quality": "GOOD" if v is not None else "MISSING",
                "valid_until": (now + timedelta(minutes=2)).isoformat() if v is not None else None,
                "sources": [
                    {
                        "source": "SIMULATOR",
                        "device_id": "SIM-DEVICE-0",
                        "metric": k,
                        "source_timestamp": now.isoformat(),
                    }
                ]
                if v is not None
                else [],
            }
            for k, v in values.items()
        }
    }

    def override_flow(route):
        response = route.fetch()
        body = response.json()
        body["energy_flow"] = snapshot
        route.fulfill(response=response, json=body)

    # Only this isolated browser test substitutes a synthetic visual scenario.
    page.route("**/api/sites/SIM-SITE-0/overview-summary", override_flow)
    page.get_by_label("Plant scope", exact=True).select_option("SIM-SITE-0")
    page.goto(origin + "/#overview/main/overview")
    root = page.locator("solar-energy-flow")
    expect(root).to_be_visible()
    expect(root.get_by_role("button", name="Battery / BMS", exact=True)).to_contain_text("Charging")
    expect(root.get_by_role("button", name="Grid", exact=True)).to_contain_text("Export")
    expect(root.locator('[data-metric="grid_w"]')).to_have_attribute("data-direction", "reverse")
    expect(root.locator('[data-metric="eps_w"]')).to_have_attribute("data-direction", "stopped")
    expect(root.locator('[data-metric="pv_w"]')).to_have_attribute("data-direction", "forward")
    motion = root.locator('[data-metric="pv_w"] .power-wire-motion')
    assert motion.evaluate("el => getComputedStyle(el).animationName") == "energy-transfer"
    root.get_by_role("button", name="Pause motion", exact=True).click()
    assert motion.evaluate("el => getComputedStyle(el).animationPlayState") == "paused"
    root.get_by_role("button", name="Resume motion", exact=True).click()
    page.emulate_media(reduced_motion="reduce")
    assert motion.evaluate("el => getComputedStyle(el).animationName") == "none"
    page.emulate_media(reduced_motion="no-preference")
    assert root.locator(".power-source").evaluate_all(
        "nodes => nodes.every(n => !n.clientHeight || n.scrollHeight <= n.clientHeight)"
    )
    root.screenshot(path=str(ROOT / "work/qa-audit/energy-flow-desktop.png"))
    root.get_by_role("button", name="Table view", exact=True).click()
    expect(root.locator(".power-flow-wires")).not_to_be_visible()
    root.get_by_role("button", name="Diagram view", exact=True).click()
    page.set_viewport_size({"width": 430, "height": 920})
    assert root.locator(".power-node").evaluate_all("""nodes => nodes.every(node => {
      const bounds = node.getBoundingClientRect();
      return [...node.children].every(child => {
        const box = child.getBoundingClientRect();
        return !box.height || (box.top >= bounds.top && box.bottom <= bounds.bottom);
      });
    })""")
    root.screenshot(path=str(ROOT / "work/qa-audit/energy-flow-mobile.png"))
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
    root.get_by_role("button", name="Fullscreen", exact=True).click()
    expect(page.locator(".energy-flow-card:fullscreen")).to_be_visible()
    page.evaluate("document.exitFullscreen()")
    expect(root).to_be_visible()
    # Regression: expiry halts motion even without a websocket refresh.
    result = page.evaluate("""async () => {
      const {flowState} = await import('/static/energy-flow.js');
      return flowState('pv_w', {pv_w: 10, channels:{pv_w:{quality:'GOOD',valid_until:'2000-01-01T00:00:00Z'}}});
    }""")
    assert result["active"] is False and result["value"] is None and result["status"] == "STALE"
    root.get_by_role("button", name="Solar PV", exact=True).click()
    expect(page).to_have_url(origin + "/#overview/main/data")
