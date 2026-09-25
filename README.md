# Solar Fleet EMS

Nền tảng O&M/EMS đa hãng cho quản lý nhà máy điện mặt trời, viết bằng Python/FastAPI và JavaScript ES modules. Giao diện tiếng Việt/English dùng chung sidebar và một hệ thống style toàn cục.

**Trạng thái ngày 25/09/2026: bản pilot 0.2.0, chưa phải sản phẩm trưởng thành theo đủ 26 mockup.** Đã có tám luồng đọc cloud với mức độ khác nhau; chưa có profile phần cứng khách hàng được nghiệm thu để bật điều khiển. Thiếu dữ liệu được hiển thị là chưa xác định, không thay bằng số liệu mẫu.

- [Trạng thái triển khai](docs/implementation-status.md): luồng đã nối BE/FE và giới hạn hiện tại.
- [Đối chiếu 26 mockup](docs/mockup-coverage.md): từng màn hình, phạm vi dự toán → mã hiện có → phần chưa xây → điều kiện hoàn thành, số dòng BE/FE/test đo được.
- [Mục lục tài liệu](docs/README.md): tài liệu hiện hành, thiết kế đích, nghiên cứu và các bản kiểm thử theo ngày.
- [Kết quả kiểm thử](docs/validation.md) và [thay đổi bản 0.2](docs/release-0.2.md).

## Chạy trên Windows

Cần Python 3.12. Chạy trong thư mục repository:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -c constraints.txt -e ".[dev]"
.\.venv\Scripts\solar-fleet.exe init --username admin
.\.venv\Scripts\solar-fleet.exe serve
```

Mở [ứng dụng cục bộ](http://127.0.0.1:8765). `init` yêu cầu đặt mật khẩu ít nhất 12 ký tự; không có mật khẩu mặc định. Administrator quản lý tài khoản/kết nối, không mặc nhiên có quyền kỹ thuật điều khiển thiết bị. Không cần Node để chạy ứng dụng.

Trên Linux/macOS, tạo môi trường bằng `python3.12 -m venv .venv`, thay executable bằng `.venv/bin/python` và `.venv/bin/solar-fleet`. Cần OS keyring khả dụng hoặc khóa Fernet qua `SOLAR_MASTER_KEY` từ trình quản lý bí mật. [`.env.example`](.env.example) chỉ là tài liệu cấu hình; ứng dụng không tự nạp `.env`.

Controller chạy một process, mặc định chỉ lắng nghe `127.0.0.1:8765`. Dữ liệu mặc định ở `data/`, dùng SQLite WAL. Không chạy đồng thời nhiều controller trên cùng thư mục dữ liệu.

## Kết nối hãng và Bluesun

Vào **Cài đặt & Hãng → Kết nối hãng**. Chọn đúng platform/vùng/tài khoản; lưu thông tin được cấp rồi kiểm tra truy cập và đồng bộ. Credentials được mã hóa tại controller, không lưu trong localStorage. Chưa kết nối thì fleet trống.

| Hệ sinh thái | Luồng đọc hiện có | Giới hạn cần biết |
|---|---|---|
| Deye Cloud | App ID/secret, tài khoản và region; discovery, latest, history, alarms, configuration | Native order transport có kiểm soát; chưa nghiệm thu canonical mapping hoặc write/readback thực |
| SolisCloud | Key ID/secret, HMAC; danh sách và chi tiết inverter, helper history/alarm | Không đoán pagination hoặc đơn vị timestamp; chưa có write compiler |
| SOLARMAN | App ID/secret, tài khoản, tùy chọn Pro organization; discovery/current data | Phải xác định OEM/logger; quyền đọc không chứng minh quyền điều khiển |
| GoodWe | Classic SEMS CrossLogin, đọc các plant ID được cấu hình | Chưa phải WEAPI/SEMS+ đầy đủ; chưa organization discovery/control |
| Sungrow | OpenAPI với app key/access key, tài khoản, plant/point ID được cấu hình | Chưa đủ region, point catalogue, unit mapping và control |
| Huawei | Northbound auth, discovery theo loại thiết bị, latest và helper history | Chưa toàn bộ FusionSolar/SmartLogger/Modbus; alarm helper chưa thành pipeline đầy đủ |
| Growatt | OpenAPI v1 token, inventory và latest cho MIN/SPH | Chưa mọi dòng máy hoặc legacy Shine/OSS login |
| Eybond / SmartESS | DessMonitor hoặc ShineMonitor; ký session, plant → collector → device → native data | Hai platform chọn riêng; chưa source timestamp/history/alarms/control đã xác minh |
| Bluesun | Brand/profile chọn transport SOLARMAN hoặc Eybond khi đúng hệ thực tế | Không có adapter Bluesun chung; BSE, BSM và BMS Cloud cần contract riêng |

[Hợp đồng đa hãng](docs/multivendor-contracts.md) liên kết đến code, nguồn và các khác biệt giao thức. [Bluesun](docs/bluesun-integration.md) và [Eybond/SmartESS](docs/eybond-read-integration.md) có hướng dẫn riêng. Có form hoặc đọc được một endpoint không đồng nghĩa hỗ trợ hoàn chỉnh hãng đó.

Polling dùng nhịp controller cơ sở 120 giây, giới hạn batch và ngân sách theo adapter. Eybond có khoảng tối thiểu 300 giây; nhịp thực tế có thể lâu hơn do tick/quota. Không coi đây là telemetry realtime ở cấp thiết bị hoặc SLA fleet lớn. WebSocket chỉ báo dữ liệu trong controller đã thay đổi.

### Kết nối Deye bằng CLI, nếu cần

Dừng controller bằng Ctrl+C trước khi dùng lệnh quản trị:

```powershell
.\.venv\Scripts\solar-fleet.exe add-deye --name "Deye EU" --region eu --account-type Company
.\.venv\Scripts\solar-fleet.exe serve
```

`--region`: `eu`, `am`, `india`; `--account-type`: `Owner`, `Installer`, `Company`, `UNKNOWN`. `--identity email|username|mobile`, `--company-id` và `--country-code` tùy contract tài khoản. CLI hỏi thông tin nhạy cảm bằng input ẩn; mật khẩu Deye được băm SHA-256 theo contract trước khi lưu vào vault.

Đăng nhập Deye trên web không tự tạo credential OpenAPI. Ứng dụng không đọc cookie/token của browser. Dùng app/key được cấp qua [Deye Developer Portal](https://developer.deyecloud.com/) và đúng data center; xem [quan sát Deye đã được cho phép](docs/deye-account-observation.md) để phân biệt bằng chứng UI với API acceptance.

## Luồng ứng dụng hiện có

| Nhóm | Phạm vi đã nối |
|---|---|
| Giao diện chung | 15 mục sidebar, một site scope, VI/EN, shared form/table/dialog và `app.css`; [route và subtab chuẩn](docs/sidebar-subtabs-architecture.md) |
| Nhà máy / thiết bị / dữ liệu | Hồ sơ, khách hàng, topology records, inventory/binding, native telemetry, nguồn/độ mới, lịch sử có giới hạn, weather khi có GPS |
| Ánh xạ dữ liệu | Chọn trường đã quan sát → đơn vị/chiều đo → mô phỏng → phiên bản → duyệt độc lập; duyệt chưa kích hoạt canonical profile |
| Điều khiển / TOU / EMS | Capability, preview/diff/confirm, khóa/idempotency, order/readback/journal; lịch nháp và compile, canary/rollout; EMS dry-run và monitor-only |
| Cảnh báo / bảo trì | Correlation, lọc/phân công/ghi chú/timeline/SLA/playbook → phiếu bảo trì → kế hoạch/checklist/time → review độc lập |
| Báo cáo / quản trị | Artifacts CSV/XLSX/HTML theo scope/kỳ, local users/site RBAC, session revoke, vault/API keys và audit |
| Local Agent | Enrollment/ingest, sequence/replay, SQLite outbox; collector SOLARMAN V5 đọc theo profile được chỉ định |

Mọi lệnh vật lý đi qua cùng command engine. Form chỉ có thể gửi khi có quyền, exact identity/profile, constraints và readback đạt yêu cầu; bật `SOLAR_WRITES_ENABLED=true` một mình không mở khóa. Deye là compiler intent duy nhất được đăng ký hiện tại, cũng chưa được nghiệm thu trên phần cứng khách hàng.

## Phần chưa hoàn thành

- Canonical model profiles, native schemas/enum/unit/sign và control/readback được nghiệm thu cho từng inverter/logger/firmware/tài khoản; các getter config cached chưa chứng minh dữ liệu mới từ thiết bị.
- History/backfill/alarm ingestion xuyên suốt mọi hãng; mapping profile activation và failover được kiểm tra trên mọi màn hình.
- EMS dispatch/optimizer, lịch chạy tự động theo model, điều khiển fleet thực và offline policies.
- Agent service, bộ driver RTU/TCP, mTLS/rotation, discovery, managed update; OTA firmware và cấu hình mạng thực.
- Time-series dài hạn, multi-tenant/SSO/MFA, scale/recovery, audit checkpoint ngoài máy. Pilot giữ tối đa 7 ngày / 200.000 điểm telemetry.
- Toàn bộ chart/topology/GIS, native UI, PDF/email/notification, commissioning điện/chữ ký/evidence upload, visual/usability/accessibility QA đủ 26 mockup.

[Phân tích chênh lệch dự toán](docs/loc-estimation-and-product-gap-analysis.md) giải thích phần engineering còn thiếu. LOC và số route không phải phần trăm hoàn thành. Đăng nhập thêm hãng giúp xác minh contract, không thay thế việc xây các module còn thiếu.

## Quản lý tài khoản và dữ liệu

Chạy khi controller đã dừng:

```powershell
.\.venv\Scripts\solar-fleet.exe list-sites
.\.venv\Scripts\solar-fleet.exe add-user technician --role Installer --site SITE_ID
.\.venv\Scripts\solar-fleet.exe disable-user technician
.\.venv\Scripts\solar-fleet.exe verify-audit
```

`--site` có thể lặp; `--site '*'` cấp rõ ràng tất cả công trình. `--data-dir PATH` đặt **trước** tên lệnh và dùng nhất quán; keyring gắn với đường dẫn dữ liệu. Bảo vệ thư mục dữ liệu/backup; không lưu master key cùng backup database hoặc trong repository.

Lệnh có kết quả không xác định phải qua reconciliation; không tự gửi lại hoặc sửa database để bỏ khóa. Rollback cũng là lệnh vật lý, không được coi luôn thành công.

Collector tùy chọn: `python -m pip install -c constraints.txt -e ".[local-solarman]"`. [Hướng dẫn local collector](docs/bluesun-integration.md#local-route) mô tả reviewed profile, spool và flush. Cloud/UI không cần extra này. Đây chưa phải bộ cài Site Agent production.

## Kiểm tra và đóng gói

Viết test cùng implementation, chạy kiểm tra tổng hợp sau mỗi đợt triển khai; khi sửa lỗi chỉ chạy lại phần bị ảnh hưởng. Dùng môi trường thử nghiệm tách khỏi tài khoản và thiết bị thật:

```powershell
.\.venv\Scripts\python.exe -m pip install -c constraints.txt -e ".[dev,browser-test]"
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe -m ruff check src tests ui_tests scripts
.\.venv\Scripts\python.exe -m ruff format --check src tests ui_tests scripts
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest ui_tests -q
node --experimental-vm-modules scripts/check-ui.cjs
.\.venv\Scripts\python.exe -m build
```

Node chỉ dùng cho kiểm tra module JS. Lệnh `pytest -q` mặc định chạy BE; browser suite cần lệnh riêng. [Browser contract](docs/browser-test-contract.md) mô tả isolation và phạm vi. [CI hiện tại](.github/workflows/checks.yml) chạy BE/lint/JS/build trên Windows/Linux, **chưa chạy browser suite hoặc toàn bộ kiểm tra format**.

[Đợt kiểm thử 25/09](docs/mapping-validation-2026-09-25.md): 450 test BE pass; 13 test browser pass trước sửa navigation, sau đó 8 ca bị ảnh hưởng pass, gồm một ca mới. Không cộng 13+8 thành số test duy nhất. Wheel/sdist và QA của luồng sửa đã được kiểm tra; đây không phải nghiệm thu toàn sản phẩm hoặc thiết bị.

Đo lại LOC bằng `python scripts/measure_code.py --update-doc`; số hiện tại chỉ duy trì tại [bảng bao phủ](docs/mockup-coverage.md) và [manifest từng file](docs/evidence/code-inventory.json). Xem [quy trình đóng góp](AGENTS.md), [hệ thống UI chung](docs/ui-design-system.md), [điều kiện hardware acceptance](docs/hardware-acceptance.md) và [thông báo nguồn mở](THIRD_PARTY_NOTICES.md) trước khi mở rộng.
