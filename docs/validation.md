# Validation record — 0.1.0

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

CI Windows/Linux được cấu hình trong `.github/workflows/checks.yml`; trạng thái thực tế xem tab Actions của repository. Kết quả CI được ghi sau khi workflow chạy, không suy ra từ local tests.
