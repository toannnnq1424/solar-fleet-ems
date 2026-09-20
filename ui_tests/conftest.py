"""Isolated browser contract suite. Explicit invocation only; never uses a signed-in browser."""

import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def fixture_server(tmp_path):
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    run_id = uuid.uuid4().hex
    origin = f"http://127.0.0.1:{port}"
    log = (tmp_path / "fixture.log").open("w", encoding="utf-8")
    process = subprocess.Popen([sys.executable, "-X", "utf8", str(ROOT / "tests" / "ui_fixture.py"), "--port", str(port)],
        cwd=ROOT, env={**os.environ, "SOLAR_UI_FIXTURE_RUN_ID": run_id}, stdout=log, stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    try:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError("Isolated UI fixture exited before readiness")
            try:
                with urllib.request.urlopen(origin + "/api/fixture-marker", timeout=1) as response:
                    marker = json.load(response)
                if marker != {"fixture": "SIMULATOR", "run_id": run_id}:
                    raise RuntimeError("Refusing to test a server not owned by this test run")
                break
            except (urllib.error.URLError, TimeoutError):
                time.sleep(0.1)
        else:
            raise RuntimeError("Isolated UI fixture did not become ready")
        yield origin
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        log.close()


@pytest.fixture
def browser_page(fixture_server):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1600, "height": 1000}, locale="en-GB", service_workers="block")
        context.add_init_script("localStorage.setItem('solar-fleet-language', 'en');")
        origin = urlsplit(fixture_server)

        def guard(route):
            target = urlsplit(route.request.url)
            if (target.scheme, target.netloc) == (origin.scheme, origin.netloc):
                route.continue_()
            else:
                route.abort()

        context.route("**/*", guard)
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        yield page, fixture_server
        context.close()
        browser.close()
        assert not errors, "Browser exceptions: " + " | ".join(errors)


def login(page, origin, account="ui-review"):
    page.goto(origin)
    page.get_by_label("Local account", exact=True).fill(account)
    page.get_by_label("Password", exact=True).fill("LOCAL-UI-REVIEW-ONLY-2026")
    page.get_by_role("button", name="Open workspace →", exact=True).click()
    page.get_by_role("navigation", name="Main navigation").wait_for()
