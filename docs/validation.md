# Validation records

[README dự án](../README.md) · [Mục lục tài liệu](README.md) · [Trạng thái hiện tại](implementation-status.md)

## Latest recorded validation — 27 September 2026

| Snapshot | Executed evidence | Limits |
|---|---|---|
| [Legacy reuse / flow, 27 September](legacy-validation-2026-09-27.md) | 535 unique backend cases across full run and affected rerun; 17 browser cases after shared CSS repair, with focused flow layout follow-up; package and provenance checks | No customer/vendor/hardware acceptance; visual QA remains selected workflows |
| [Mapping / navigation, 25 September](mapping-validation-2026-09-25.md) | 450 backend tests passed; 13 browser tests before navigation repair; 8 affected browser cases after repair, including one new case; Ruff, 29 JS modules, wheel/sdist and focused visual QA | 14 unique browser cases existed at that snapshot; do not add reruns. No live vendor or hardware acceptance, and not full 26-screen QA |
| [Eybond, 24 September](eybond-validation-2026-09-24.md) | Read connector/workflow, browser, package and QA evidence scoped to that earlier snapshot | Source-time/model mapping/control remain unaccepted |
| [Adapter/workspace audit, 23 September](audit-validation-2026-09-23.md) | Contract corrections, backend/browser checks and package evidence for the audit snapshot | Superseded for current totals by the later records |

Each linked record owns its actual counts, warnings, reruns and artifact hashes. Logs/screenshots under `work/` and packages under `dist/` are local ignored artifacts, not files available in a fresh checkout. The documentation refresh before commit does not constitute another full test/build run.

See [browser test instructions](browser-test-contract.md) and [current workflow](../.github/workflows/checks.yml). CI currently runs backend/lint/JS/build on Windows/Linux; browser tests and the full format check are local verification steps. A configured workflow is not proof that a remote run passed.

## Historical validation 0.1.0

The record below is retained from 13 September. Its 86-test total and 0.1 package checks are historical, not the current 0.2 result.

Ngày kiểm tra: 13/09/2026. Môi trường local: Windows, Python 3.12; dependencies cố định tại `constraints.txt`. Dữ liệu trong test là fixture SIMULATOR, không phải tài khoản khách hàng.

## Đã chạy

| Kiểm tra | Kết quả |
|---|---|
| `python -m pytest -q` | **86 passed**; 2 deprecation warnings của Starlette TestClient/httpx/AnyIO, không phải test thất bại |
| `python -m ruff check src tests` | Passed |
| `node --check src/solar_fleet/static/app.js` | Passed |
| `python -m pip check` | Không có dependency bị hỏng |
| `python -m build --no-isolation` | Tạo wheel + sdist |
| Clean environment wheel install | Import từ site-packages, app factory/routes, CLI help, static assets, 39 contracts, 34 intents, 38 sources đều có trong wheel |
| Browser QA | Đăng nhập bằng tài khoản tạm của QA server; fleet trống có giải thích; Deye Native; security log; desktop 1280×800, mobile 390×844 |

QA server dùng database memory, không có integration/vendor polling, được dừng sau kiểm tra. Không tạo tài khoản mặc định trong gói production. Đã sửa lớp nền che chữ ở login và giữ nút đăng xuất trên mobile khi kiểm tra visual.

## Các nhóm test có ý nghĩa

- Authentication bắt buộc trên loopback; Host/origin/CSRF; session revocation; giới hạn đăng nhập; phân quyền site; Administrator không tự có quyền engineering.
- Scrypt, vault encryption, secret redaction, audit trigger/hash chain; không echo password trong validation error.
- Deye region allowlist, auth/token expiry, pagination và repeated/incomplete page, latest batch 10, code/error/redirect/429/backoff, schema spelling, raw control locked, không retry write sau timeout.
- Idempotency khi confirm đồng thời và sau mở lại database, per-device serialization, lệnh chờ bị revoke, config drift cả các field liên quan ngoài field đang sửa, identity/firmware/profile thay đổi, stale/offline/cached readback.
- Accepted khác VERIFIED; pending/failed/offline/timeout/mismatch đều không được xác minh thành công. Unknown outcome khóa thiết bị; restart không resend.
- Một phần cứng qua hai account có một identity/queue, hai binding; account/device budgets không nhân đôi theo integration.
- Unit/sign normalization có evidence, giá trị raw khi semantics chưa biết, NaN/Inf, stale/future timestamp, source priority, discrepancy/time skew, battery provenance cho energy ratios, dedupe theo timestamp và retention.
- Discovery/ingestion thực thi qua adapter interface dùng mock; response sai serial không được nhập telemetry.

Test guard chặn HTTP transport thật và các kết nối ngoài loopback; chỉ cho phép socketpair nội bộ của asyncio trên Windows. Không test nào gửi request tới tài khoản Deye hay inverter thật.

## Những việc chưa kiểm chứng

Chưa chạy auth/discovery/telemetry/history/alarms trên credential OpenAPI live. Chưa nghiệm thu unit/sign profile, physical command, range, config freshness, readback tolerance, local protocol, cloud/local coexistence, nhiều nghìn thiết bị hoặc khôi phục thảm họa. UI detail trên dữ liệu phần cứng thật chờ API credentials. Giao diện Deye Cloud được xem riêng để bổ sung evidence E, không phải acceptance của adapter này.

CI Windows/Linux được cấu hình trong [checks.yml](../.github/workflows/checks.yml); trạng thái thực tế xem tab Actions của repository. Kết quả CI được ghi sau khi workflow chạy, không suy ra từ local tests.
