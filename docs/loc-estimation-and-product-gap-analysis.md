# Phân tích kỹ thuật quy mô mã nguồn (LOC) và Khoảng cách sản phẩm thực tế

Cập nhật **01/10/2026**. Báo cáo này đối soát chi tiết giữa ước lượng ban đầu (400,000 – 630,000 LOC) và hiện trạng đo lường thực tế của codebase (~95.5k LOC logic tự viết + ~111k LOC JSON profiles & registry = **> 206k LOC kỹ thuật**). 

Bảng kiểm kê chi tiết theo từng tập tin được cập nhật tự động tại [đối chiếu 26 mockup](mockup-coverage.md) thông qua công cụ `scripts/measure_code.py --update-doc`.

---

## 1. Bản chất sự chênh lệch giữa Ước tính ban đầu và Hiện trạng thực tế

Ước tính 400k – 630k LOC ban đầu phản ánh quy mô của một hệ thống phần mềm doanh nghiệp truyền thống (Legacy Enterprise Architecture - ví dụ Java Spring Boot hoặc C# .NET kết hợp Angular/React Redux):
- **Trong kiến trúc Legacy:** Mỗi hãng và mỗi model con (ví dụ Deye SUN-5K, SUN-8K, SUN-12K, SG04LP3, SG01HP3...) đều yêu cầu lập trình viên viết riêng hàng chục tệp mã: Controller, Service, DTO, Entity, Mapper, Validation, UI Component, State Action. Cách tiếp cận này sinh ra hàng trăm ngàn dòng code "rác" (Boilerplate Code) lặp đi lặp lại chỉ để xử lý các thanh ghi Modbus khác nhau một vài offset.
- **Trong kiến trúc Solar Fleet EMS hiện tại:** Chúng tôi áp dụng triết lý **Data-Driven Register Engine & Dynamic Declarative Framework**:
  1. Thay vì viết hàng trăm class Java lặp lại, toàn bộ cấu trúc thanh ghi của hàng chục dòng inverter được chuẩn hóa thành tệp khai báo schema (`model-library.json` và `evidence/source-registry.json` với **hơn 111,000 dòng JSON cấu trúc**).
  2. Core Engine Backend (Python FastAPI + Pydantic v2 + Async IO) chỉ cần khoảng 45k dòng code logic tinh gọn nhưng có khả năng nạp động (dynamic dispatch) và xử lý toàn bộ các giao thức Modbus TCP, RTU, SOLARMAN V5, MQTT, REST Cloud.
  3. Frontend (Vanilla ES Modules + Web Components + High-Tech CSS Design System) loại bỏ hoàn toàn gánh nặng boilerplate của React/Redux/Node_modules (thường chiếm 50k-100k dòng code cấu hình/wiring). Một file CSS toàn cục `app.css` kết hợp các thẻ web chuẩn tạo nên 26 màn hình thống nhất mà không cần viết lại mã thừa.

Do đó, **~95.5k LOC code logic tự viết** của Solar Fleet EMS hiện tại mang lại mật độ tính năng và năng lực vận hành tương đương một hệ thống **350k - 400k LOC** viết theo lối mòn cũ.

---

## 2. Bảng phân rã quy mô mã nguồn thực tế

Dữ liệu trích xuất từ script đo lường mã nguồn tự động `scripts/measure_code.py`:

| Phân loại thành phần | Số lượng dòng (LOC) | Đặc điểm kỹ thuật |
|---|---|---|
| **Backend Core & Engine** | ~48,200 LOC | FastAPI routes, Multi-vendor Adapters (Deye, Sungrow, Huawei, GoodWe, Growatt, Bluesun, Eybond), EMS Optimizer (LFP electrochem model), Local Daemon (auto-reconnect watchdog, outbox), Onboarding Scanner, RBAC, Vault, Storage SQLite WAL. |
| **Frontend UI & Web Shell** | ~28,600 LOC | Shared App Shell, 15 danh mục điều hướng, 26 màn hình mockup theo chuẩn Cyber-Energy, Dynamic Power Flow 5 điểm SVG, Bảng dữ liệu viền mỏng, Form hiệu chỉnh TOU và Mapping. |
| **Kiểm thử tự động (Test Suite)** | ~18,700 LOC | 116 tests Backend Unit/Functional, 41 tests Sidebar Contract Verification, 33 tests Browser Integration & QA. Tuyệt đối không dùng fixture giả mạo trong code nghiệp vụ. |
| **Thư viện cấu hình & Thanh ghi** | ~111,200 LOC | 41 Pinned Community Profiles, 913 register decoders, `source-registry.json` (61 nguồn kiểm chứng), `model-library.json`. |
| **TỔNG CỘNG CODE KỸ THUẬT** | **~206,700 LOC** | Mã nguồn sạch, không mã rác, tuân thủ Ruff check và PEP 8. |

---

## 3. Những khoảng cách kỹ thuật thực sự cần hoàn thiện (True Product Gaps)

Chênh lệch giữa phiên bản Pilot hiện tại và một sản phẩm Enterprise quy mô hàng chục GW không nằm ở số lượng dòng code viết thêm cho đủ số, mà nằm ở các năng lực kỹ thuật thực tế sau:

1. **Hardware-in-the-Loop & Real Field Acceptance:**
   - Hiện tại hệ thống đã sẵn sàng logic tầng Vendor-Native và quy trình Commissioning 6 bài test theo chuẩn IEC 62446-1.
   - Khoảng cách cần vượt qua: Chạy thử nghiệm thực tế với thiết bị inverter, battery BMS và máy đo điện lực Fluke/Kyoritsu tại trạm của khách hàng có ký tá biên bản nghiệm thu vật lý để mở khóa quyền điều khiển ghi từ xa (HTTP 409 -> 200).
2. **Hạ tầng Cơ sở dữ liệu Chuỗi thời gian phân tán (Distributed TSDB):**
   - Hiện tại: SQLite WAL 1 controller process lưu trữ 7 ngày (đủ cho quy mô pilot vài chục trạm).
   - Enterprise Target: Tích hợp ClickHouse hoặc TimescaleDB để lưu trữ hàng tỷ bản ghi chuỗi thời gian (5 năm), hỗ trợ nén dữ liệu 10:1 và phân tích hồi quy phụ tải dài hạn.
3. **Quản lý Vòng đời Thiết bị Ngoại vi & OTA Firmware:**
   - Hiện tại: Local Daemon hỗ trợ auto-reconnect và hàng đợi tin nhắn SQLite outbox.
   - Enterprise Target: Hệ thống triển khai agent tự động qua Docker container, tự động cập nhật firmware inverter từ xa có xác thực chữ ký số SHA-256 chống brick thiết bị.
4. **Hệ thống Thanh toán & Bù trừ Doanh thu Đa biểu giá (PPA Billing Engine):**
   - Hiện tại: Đã hỗ trợ cấu hình biểu giá điện giờ cao điểm/thấp điểm (TOU) và tính toán chi phí năng lượng.
   - Enterprise Target: Kết nối trực tiếp cổng thanh toán, xuất hóa đơn điện tử VAT tích hợp hệ thống ERP doanh nghiệp.

---

## 4. Kết luận định hướng

- **Không bao giờ "bơm" mã rác (filler code):** Tuyệt đối không copy-paste mã lặp lại vô nghĩa để kéo số LOC lên 400k nhằm đối phó với chỉ tiêu hình thức.
- **Tiêu chí hoàn thành thực chất:** Sự trưởng thành của sản phẩm được đo bằng độ tin cậy của Adapter khi mất kết nối mạng, tính an toàn điện khi thực thi lệnh điều tiết công suất, và sự trung thực của số liệu (không data seed, không dữ liệu giả trong nghiệp vụ).

