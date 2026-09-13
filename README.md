# Solar Fleet EMS

Nền tảng O&M/EMS cho đội EPC, ưu tiên controller cục bộ và điều khiển có bằng chứng. **Bản 0.1.0 là nền móng và pilot chỉ đọc; chưa đạt Deye MVP nghiệm thu phần cứng.**

[Báo cáo nghiên cứu A–N](docs/research-architecture-report.md) được lập và commit **trước code**. Có 38 nguồn sau khi bổ sung quan sát Deye Cloud được người dùng cho phép, 10 phạm vi hệ sinh thái, 34 intent và 10 ADRs. Xem [quan sát tài khoản thực](docs/deye-account-observation.md), [source audit](docs/vendor-source-audit.md), [compatibility matrix](docs/vendor-compatibility-matrix.md) và [control mapping](docs/universal-control-mapping.md).

## Chạy trên Windows

Cần Python 3.12. Trong thư mục repository:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -c constraints.txt -e ".[dev]"
.\.venv\Scripts\solar-fleet.exe init --username admin
.\.venv\Scripts\solar-fleet.exe serve
```

Mở **http://127.0.0.1:8765**. `init` yêu cầu tự đặt mật khẩu tối thiểu 12 ký tự; không có mật khẩu mặc định. Tài khoản Administrator quản lý tài khoản/kết nối, không mặc nhiên có quyền kỹ thuật để điều khiển thiết bị. Không cần Node để chạy ứng dụng.

Trên Linux/macOS, dùng `python3.12 -m venv .venv`, rồi dùng `.venv/bin/python` và `.venv/bin/solar-fleet`. Cần OS keyring khả dụng, hoặc cung cấp khóa Fernet qua `SOLAR_MASTER_KEY` từ trình quản lý bí mật. Không lưu khóa này trong repository, shell history hoặc cùng bản backup database.

## Kết nối Deye thật

Dừng controller bằng Ctrl+C, rồi chạy:

```powershell
.\.venv\Scripts\solar-fleet.exe add-deye --name "Deye EU" --region eu --account-type Company
.\.venv\Scripts\solar-fleet.exe serve
```

Chọn đúng loại account đã được Deye cấp; các giá trị là `Owner`, `Installer`, `Company`, `UNKNOWN`. `--region` gồm `eu`, `am`, `india`. `--identity email|username|mobile` chọn định danh đăng nhập; thêm `--company-id` hoặc `--country-code` nếu app/account yêu cầu. CLI hỏi App ID, App Secret, định danh và mật khẩu bằng input ẩn; mật khẩu được băm SHA-256 theo contract trước khi lưu cùng credential trong vault mã hóa.

Đăng nhập Deye Cloud trên web **không** tự tạo credential OpenAPI. Phiên browser chỉ được dùng để đối chiếu thông tin; ứng dụng không đọc cookie/token web. Cần app được cấp quyền tại [Deye Developer Portal](https://developer.deyecloud.com/) và đúng data center. Không gửi App Secret hoặc mật khẩu vào chat.

Controller tự discovery, polling theo chu kỳ 120 giây; trang **Kết nối** hiển thị lỗi xác thực/quyền/quota. Chưa có credential thì fleet trống, không thay bằng JSON mẫu. Có thể dùng nút đồng bộ chỉ đọc, với cooldown và cùng rate budget. Latest tối đa 10 serial mỗi request; pagination xử lý nhiều trang. Lịch sử raw được đọc theo khoảng tối đa 24 giờ mỗi request; alert theo 24 giờ trên UI.

## Đã triển khai

| Phần | Hành vi hiện tại |
|---|---|
| Domain / storage | Identity theo inverter/logger/model/firmware/account; binding dữ liệu riêng; SQLite WAL, sample theo source timestamp, retention 7 ngày / 200.000 points |
| Deye transport thật | HTTPS allowlist theo region; token và tái xác thực khi hết hạn; discovery station/device; latest batch; config; history; alerts; native order transport/status |
| Telemetry | Giữ raw key/unit/timestamp/provenance; chỉ mapping đã review mới thành canonical; không tự đoán dấu, reserve SOC hay unit |
| Giao diện tiếng Việt | Fleet, thiết bị/logger, energy flow có trạng thái chưa biết, lịch sử, alerts, cấu hình gốc, quick/advanced capabilities, 39 endpoint native và nhóm quan sát web |
| Command engine | Dry-run bất biến, hash preview/confirm, idempotency bền vững, kiểm tra quyền/profile/config lại trước gửi, khóa từng device, order tracking, readback, audit; lỗi không rõ kết quả chặn lệnh sau |
| Bảo mật | Loopback có auth, password scrypt, secret Fernet + OS keyring, cookie HttpOnly/SameSite, CSRF/origin/Host allowlist, rate limit đăng nhập, RBAC theo site, role revoke |
| Chất lượng | Unit, contract và integration tests dùng simulator/MockTransport; lint; kiểm tra JS; build wheel/sdist; workflow Windows/Linux |

Native control transport tồn tại để phát triển profile được nghiệm thu, **không phải quyền cho người dùng gọi trực tiếp**. HTTP API không có proxy arbitrary endpoint. Mọi shipping capability hiện là UNKNOWN; ngay cả `SOLAR_WRITES_ENABLED=true` cũng không mở khóa. Giao diện chưa bật form gửi lệnh vì chưa có profile/range/readback đạt yêu cầu. Các candidate mapping (work mode, dòng pin, grid charge, export, TOU) nằm sau kiểm tra capability; không map Reserve SOC/Zero Export theo tên gần giống.

## Giới hạn cần hoàn thành trước MVP

- Chưa có credential OpenAPI để thử kết nối live, chưa có write/readback end-to-end trên inverter thật. Có bằng chứng UI cho một hệ hybrid LV 16 kW và logger; chưa đủ exact model hoặc API privileges.
- Chưa có mapping metric đã nghiệm thu cho model thực, nên sơ đồ năng lượng canonical sẽ còn “—”; bảng native vẫn hiển thị số hãng trả về khi API kết nối được.
- Các getter config Deye đã nghiên cứu không chứng minh dữ liệu mới từ device. Chúng luôn trả `freshness_verified=false`. Đây là blocker cần giải quyết trước điều khiển.
- Chưa triển khai local hardware driver, Site Agent, outbox mTLS, Modbus/IEC104 register profile, các adapter vendor khác, bulk control, reconciliation UI hoặc EMS optimizer. Xem [implementation status](docs/implementation-status.md).
- Pilot một process, tối đa 50 thiết bị cho một vòng polling. Với nhiều hơn, controller luân phiên và báo `PILOT_CAPACITY_EXCEEDED`; không hứa SLA fleet lớn. SQLite hiện chưa phải storage production cho hàng nghìn inverter.
- Audit hash chain và trigger phát hiện sửa nội dung trong database; chưa bảo vệ khỏi người có quyền hệ điều hành xóa cả file, cắt đuôi log hoặc thay chương trình. Cần backup/checkpoint ngoài máy và hardening trước production.

## Quản lý tài khoản và dữ liệu

Các lệnh quản trị chạy khi controller đã dừng; khóa hệ điều hành ngăn nhiều process ghi đồng thời.

```powershell
.\.venv\Scripts\solar-fleet.exe list-sites
.\.venv\Scripts\solar-fleet.exe add-user technician --role Installer --site SITE_ID
.\.venv\Scripts\solar-fleet.exe disable-user technician
.\.venv\Scripts\solar-fleet.exe verify-audit
```

`--site` có thể lặp lại; `--site '*'` là quyền rõ ràng cho tất cả công trình, chỉ dùng khi phù hợp. `--data-dir PATH` phải đặt **trước** tên lệnh và giữ nhất quán; khóa keyring gắn với đường dẫn dữ liệu. Dữ liệu mặc định trong `data/`, đã được gitignore. Secret được mã hóa, còn telemetry/metadata/audit cần bảo vệ bằng quyền thư mục và mã hóa ổ đĩa. `.env.example` là tài liệu tham khảo; ứng dụng không tự nạp `.env`.

Khi có lệnh TIMEOUT, không retry hoặc sửa trực tiếp database để xóa trạng thái. Engine khóa thiết bị cho đến khi có quy trình reconciliation được nghiệm thu. Không có rollback tự động vì rollback cũng là một lệnh vật lý có thể thất bại.

## Kiểm tra và build

```powershell
.\.venv\Scripts\python.exe -m ruff check src tests
.\.venv\Scripts\python.exe -m pytest -q
node --check src/solar_fleet/static/app.js
.\.venv\Scripts\python.exe -m build --no-isolation
```

`constraints.txt` cố định các phiên bản đã cài và kiểm tra cho baseline Python 3.12. Test chặn HTTP transport thật; socketpair loopback nội bộ của asyncio trên Windows được cho phép. Simulator chỉ nằm trong `tests/`, không có demo mode hoặc test device trong production package. Không test nào gửi lệnh tới Deye thật.

Xem [hardware acceptance](docs/hardware-acceptance.md) trước mọi đợt commissioning và [validation record](docs/validation.md) cho kết quả kiểm tra phiên bản này.
