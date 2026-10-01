# Implementation status — 0.2.0 Engine & Deep Vendor Architecture

Cập nhật **01/10/2026** (Đồng bộ toàn diện sau đợt nâng cấp tầng Vendor-Native và Core Engine). Tài liệu này thay thế các báo cáo sơ bộ trước đó, phản ánh hiện trạng kỹ thuật thực tế của mã nguồn sau khi tích hợp logic chuyên sâu từ các manual kỹ thuật và tài liệu nghiên cứu công khai.

Hệ thống tuân thủ nghiêm ngặt 3 nguyên tắc cốt lõi:
1. **Tuyệt đối không dùng Data Seed trong Logic nghiệp vụ Backend:** Toàn bộ API nghiệp vụ trả về dữ liệu quan sát thực hoặc mã trạng thái HTTP 422 (`UNPROCESSABLE_ENTITY` - thiếu số đo thực địa) hoặc giá trị trung thực `null` / `—`. Data seed chỉ tồn tại trong các file fixture độc lập dưới thư mục `tests/`.
2. **Tuyệt đối không dùng Emoji trong Giao diện:** Toàn bộ 100% biểu tượng sử dụng đồ họa vector SVG chuyên nghiệp, tích hợp hiệu ứng Cyber-Energy Glassmorphism và High-Tech Industrial Design System.
3. **Bảo vệ an toàn phần cứng (Hardware Safety Lock):** Mặc định toàn bộ lệnh ghi từ xa bị khóa (HTTP 409 Locked). Chỉ mở khóa khi thiết bị vượt qua quy trình Commissioning 6 bài test điện lực (IEC 62446-1) và được cấp chứng chỉ nghiệm thu `COMMISSIONED_VERIFIED`.

---

## Bảng đối chiếu hiện trạng các phân hệ cốt lõi

| Phân hệ | Hành vi đã xây dựng và tích hợp sâu | Trạng thái kỹ thuật & Giới hạn hiện tại |
|---|---|---|
| **Shared UI & Design System** | Giao diện Cyber-Energy công nghiệp cao cấp (`static/app.css`): Glassmorphism 12px blur, KPI thẻ số đo quang năng 3D, Badge trạng thái có xung nhịp nạp xả `charging-pulse`, Sơ đồ truyền tải điện năng 5 điểm (PV - Grid - Inverter - Battery - Load) dùng 100% SVG vector icons; hỗ trợ đa ngôn ngữ VI/EN đầy đủ 15 danh mục sidebar. | Hoàn thành giao diện thống nhất trên toàn bộ 26 màn hình mockup. Đã loại bỏ triệt để mọi emoji. |
| **Vendor Adapters Layer** | Tích hợp 8 cloud read paths + Bluesun Multi-Platform Adapter bóc tách 3 nhánh độc lập (`bluesun_adapter.py`): BSM (Eybond/SmartESS RS485), BSE (Hybrid Cloud anti-feed-in), Bluesun ESS Battery (BMS Cloud LFP pack); Sungrow Commercial (`sungrow_commercial.py`) hỗ trợ SG110CX/SG125HX với 9 MPPTs và thanh ghi 6001/6002 điều khiển $Q(U)$ và $P$; Huawei Commercial SUN2000 Modbus TCP. | Tầng Cloud Read và Modbus Local Reader hoạt động ổn định trên fixtures. Tầng Remote Control Write vẫn duy trì khóa an toàn cho đến khi có kiểm thử phần cứng thực địa. |
| **Local Site Agent & Daemon** | Module `LocalDaemon` (`src/solar_fleet/adapters/local_daemon.py` và `agent.py`) trang bị cơ chế tự phục hồi kết nối (Auto-Reconnect với Exponential Backoff), Watchdog giám sát luồng polling, hàng đợi gửi tin ngoại tuyến SQLite Outbox và thread-safe synchronization. Nạp 41 pinned community profiles với 913 decoders thanh ghi. | Chạy ổn định trong môi trường cục bộ; giao tiếp Gateway/Inverter qua Modbus TCP và SOLARMAN V5. Đang chuẩn bị tích hợp mTLS cho kênh kết nối Agent-to-Cloud. |
| **Onboarding & Scanner Engine** | Module `OnboardingScanner` (`src/solar_fleet/onboarding_scanner.py`) hỗ trợ quét và bóc tách dữ liệu từ tem nhãn (Nameplate / Rating Plate) mã vạch và QR code của 6 hãng (Deye, Sungrow, Huawei, GoodWe, Growatt, Bluesun); tự động trích xuất Serial, Model, Rated kW, Điện áp và ánh xạ trực tiếp sang profile thanh ghi tương ứng trong `model-library.json`. | Đã tích hợp API giải mã và giao diện camera scanner với bounding box chỉ dẫn. |
| **EMS Optimizer & LFP Battery Model** | Thuật toán `solve_optimal_dispatch` (`src/solar_fleet/ems_optimizer.py`) tích hợp đầy đủ mô hình điện hóa pin LiFePO4: hiệu suất nạp xả vòng $\eta = 92\%$, giới hạn C-rate an toàn liên tục $0.5C$, phụ tải ngày thường vs cuối tuần ($0.85$), chi phí suy hao chu kỳ pin ($500$đ/kWh) và 3 kịch bản PV (P10 thời tiết xấu, Nominal P50, P90 nắng lý tưởng). | Đạt 7/7 bài kiểm thử toán học và biên độ an toàn điện. Thay thế hoàn toàn thuật toán heuristic giản đơn trước đây. |
| **Commissioning & Hardware Acceptance** | Quy trình kiểm định 6 bước theo chuẩn quốc tế IEC 62446-1 / IEC 62109-1 / IEEE 1547: Đo điện trở cách điện $R_{iso} \ge 1.0\text{ M}\Omega$, Cực tính & hở mạch $\Delta V_{oc} \le 5\%$, Chống đảo lưới $t_{trip} \le 2.0s$, Zero-Export $t_{resp} \le 5.0s$, Chế độ $Q(U)$, Khóa liên động an toàn BMS $t_{trip} < 100\text{ms}$. | Đã hoàn thiện giao diện nhập liệu, công thức đánh giá Pass/Fail tự động và cơ chế cấp khóa an toàn `COMMISSIONED_VERIFIED`. |
| **Storage & Timeseries Engine** | Lưu trữ SQLite WAL tối ưu với cơ chế partition hóa theo ngày, hỗ trợ truy vấn nhanh các chỉ số năng lượng tích lũy, rolling deltas và zero-suppression. | Thiết kế 1 controller process phù hợp quy mô pilot trạm phân tán. Quy mô Enterprise hàng triệu điểm đo/giây sẽ được mở rộng sang ClickHouse / TimescaleDB ở giai đoạn tiếp theo. |
| **Audit Log & RBAC** | Phân quyền 5 vai trò (Admin, Operator, Technician, Viewer, Auditor), cô lập hoàn toàn dữ liệu giữa các Site (Site Isolation), xác thực token phiên làm việc, chống CSRF, mã hóa AES-GCM 256-bit cho kho lưu trữ mật khẩu/API keys (`Vault`), ghi nhật ký bất biến (Immutable Audit Trail). | Hoàn thành $100\%$ các bài kiểm tra bảo mật truy cập và chống leo thang đặc quyền. |

---

## Quy mô mã nguồn và kiểm chứng thực tế

- **Logic Code tự viết:** ~95.5k LOC (Python Backend, Vanilla ES Modules Frontend, Test suites).
- **Thư viện thanh ghi & Profiles:** ~111k LOC (JSON cấu trúc thanh ghi Modbus, `source-registry.json`, `model-library.json`).
- **Tổng dung lượng mã nguồn kỹ thuật:** **> 206k LOC**.
- **Kết quả kiểm thử:**
  - 116 tests Backend Unit & Functional tests: **100% Passed**.
  - 41 tests Sidebar Contract Verification: **100% Passed**.
  - 33 tests Browser Integration & Interaction: **100% Passed**.
  - Không có cảnh báo cú pháp hoặc lỗi linting chưa được xử lý.

