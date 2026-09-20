# Browser contract tests (written, not yet executed)

The suite in `ui_tests/` exercises UI and the local backend together. It starts its own in-memory fixture on a reserved loopback port, verifies a per-run ownership marker, uses a fresh headless Chromium context, blocks external browser requests, and forbids outgoing HTTP from the fixture server. It does not attach to the user's Deye tab or reuse cookies.

Contracts cover incident creation, assignment, notes, related maintenance, viewer permissions, a shared stylesheet/sidebar across routes, VI/EN switching and narrow-screen reflow. Maintenance contracts additionally author the journey from work creation through planning, checklist results, time entries and independent review, and verify that its tabs reuse the global navigation. These tests have not been executed. This is an initial browser suite, not full coverage of the 26 mockups. Visual reference comparison, the remaining screen states, keyboard/accessibility and all remaining business journeys still require implementation and final QA.

Execution is deferred under the user's instruction to finish implementation first. At the consolidated verification phase, install `.[dev,browser-test]`, install Chromium with `python -m playwright install chromium`, then run `python -m pytest ui_tests`. The ordinary backend suite remains separate. Missing browser dependencies must not be reported as successful browser tests.

API usage follows the official [Playwright Python introduction](https://playwright.dev/python/docs/intro) and [network isolation documentation](https://playwright.dev/python/docs/network). No third-party example code was copied into the application.
