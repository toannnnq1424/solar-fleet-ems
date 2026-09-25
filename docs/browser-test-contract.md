# Browser contract tests

[Documentation index](README.md) · [Executed validation](validation.md)

The suite in [ui_tests](../ui_tests) exercises UI and the local backend together. It starts its own in-memory fixture on a reserved loopback port, verifies a per-run ownership marker, uses a fresh headless Chromium context, blocks external browser requests, and forbids outgoing HTTP from the fixture server. It does not attach to the user's Deye tab or reuse cookies.

Contracts cover incident creation/assignment/notes and related maintenance, execution/checklist/time/independent review, viewer permissions, account/native readings, mapping create/edit/simulate/history/review, canonical and legacy navigation, VI/EN, one shared stylesheet/sidebar and selected narrow-screen reflow.

## Execution status

The [25 September record](mapping-validation-2026-09-25.md) reports 13 passing browser cases before navigation QA repair and 8 affected cases after repair, including one new route test. There are 14 unique cases in the current suite; 13+8 are not 21 unique cases. The full suite was not rerun after the navigation repair; the affected workflows were.

This is not full coverage of the 26 mockups. Visual reference comparison, remaining screen states, keyboard/accessibility, load and all business journeys still require implementation and QA. [Current CI](../.github/workflows/checks.yml) does not install or run this browser suite.

## Running the suite

From the repository root, with the intended Python environment active:

```powershell
python -m pip install -c constraints.txt -e ".[dev,browser-test]"
python -m playwright install chromium
python -m pytest ui_tests -q
```

The ordinary backend suite remains separate: `python -m pytest -q` uses `tests/` from [pyproject.toml](../pyproject.toml). Missing browser dependencies must not be reported as successful browser tests. Follow the consolidated verification timing in [AGENTS.md](../AGENTS.md); rerun affected cases when fixes require it.

API usage follows the official [Playwright Python introduction](https://playwright.dev/python/docs/intro) and [network isolation documentation](https://playwright.dev/python/docs/network). No third-party example code was copied into the application.
