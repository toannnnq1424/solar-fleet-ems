# Quy chuẩn Kiến trúc Sidebar và Toàn bộ Không gian làm việc (Sidebar & Workspace Specification)

Cập nhật: 20/09/2026.  
Dự án: **Solar Fleet EMS**

Tài liệu này là **kết luận chuẩn hóa kiến trúc thông tin (Information Architecture)** chốt lại toàn bộ hệ thống điều hướng: danh mục các tab chính trên Sidebar, các tab con (sub-tabs) bên trong từng không gian làm việc (workspace), và chi tiết 11 khối hiển thị bắt buộc tại tab Tổng quan.

---

## I. Nguyên tắc Kiến trúc Cốt lõi

1. **Một hệ thống thiết kế toàn cục (Single Global UI):** Toàn bộ ứng dụng dùng chung một shell, một sidebar, và file định kiểu duy nhất `static/app.css` (kèm các token trong `:root`). Không tạo file CSS riêng theo route, không dùng inline CSS.
2. **Xây dựng UI hoàn chỉnh trước — Khóa an toàn trường chưa xác minh (`unknown-can't-click`):**
   - Mọi form, nút thao tác, trường dữ liệu, thẻ KPI theo 26 mockup đều phải được dựng giao diện đầy đủ, mạch lạc, thẩm mỹ cao.
   - Bất kỳ trường điều khiển vật lý hoặc dữ liệu nào chưa có profile phần cứng được nghiệm thu, chưa có chứng chỉ mTLS, hoặc đang chờ xác thực tài khoản thì **hiển thị ở trạng thái xám (disabled / grayed-out), có nhãn/tooltip giải thích lý do an toàn rõ ràng** (ví dụ: `[UNKNOWN - Chờ nghiệm thu thiết bị]`, `[Khóa: Thiếu quyền ghi]`). Tuyệt đối không ẩn giấu gây khó hiểu cho người vận hành.
3. **Mọi khối tóm tắt đều có đường dẫn chi tiết (Drill-down Links):** Các thẻ KPI, cảnh báo, thiết bị, nhật ký tại trang tổng quan luôn có nút hoặc liên kết chuyển hướng trực tiếp đến đúng route/tab quản lý chuyên sâu với bộ lọc tương ứng được giữ nguyên.

---

## II. Danh mục 14 Tab Chính trên Sidebar

Sidebar chia thành các nhóm công việc: **Giám sát**, **Vận hành**, **Quản lý & Hệ thống**, bao gồm các tab chính sau:

```
SIDEBAR
├── [GIÁM SÁT]
│   ├── 1. Tổng quan (Fleet & Site Overview)
│   ├── 2. Nhà máy (Plant Management)
│   ├── 3. Hệ thống (System Topology)
│   ├── 4. Bản đồ (GIS & Distribution Map)
│   └── 5. Thiết bị (Equipment Inventory & 6-tab Workspace)
├── [VẬN HÀNH]
│   ├── 6. Điều khiển (Control Engine & Presets)
│   ├── 7. Lịch / TOU (Weekly Schedule & Tariff Matrix)
│   ├── 8. Điều phối EMS (Rules Engine & Automated Dispatch)
│   ├── 9. Dữ liệu & Kết nối (Data, Sources & Diagnostics)
│   ├── 10. Cảnh báo (Incident Center & Alarms)
│   ├── 11. Báo cáo (Analytics & Reporting)
│   └── 12. Bảo trì (Maintenance, Health & Firmware)
└── [QUẢN LÝ]
    ├── 13. Nhật ký (Comprehensive Audit & Event Journal)
    ├── 14. Quản lý người dùng (Users, Roles & Scopes)
    └── 15. Cài đặt (Global & Plant Settings)
```

---

## III. Chi tiết Từng Tab Chính & Các Tab Con Bên Trong

### 1. Tab Tổng quan (Fleet / Plant Overview)
Khi chọn một nhà máy (hoặc xem tổng quan toàn fleet), tab này mở không gian làm việc với **10 tab con**:
- **Tổng quan (Overview):** Màn hình điều hành trung tâm (chi tiết 11 khối ở Phần IV).
- **Dữ liệu (Data):** Dữ liệu đo realtime & lịch sử, chọn ngày/tháng/năm/tổng, biểu đồ công suất/sản lượng/SOC, bảng timestamp chất lượng cao và xuất CSV/XLSX.
- **Thiết bị (Equipment):** Danh sách thiết bị của nhà máy theo loại (Inverter, Pin, Logger, Meter...), trạng thái online/offline, công suất tức thời.
- **Điều khiển (Control):** Các preset điều khiển nhanh và form điều khiển chi tiết cho thiết bị trong nhà máy (áp dụng qua luồng preview/diff/confirm an toàn).
- **Lịch / TOU (Schedule):** Lịch vận hành tuần của nhà máy, khung giờ sạc/xả, tham chiếu biểu giá điện theo giờ.
- **Cảnh báo (Alerts):** Danh sách sự cố và cảnh báo đang mở của nhà máy, mức độ nghiêm trọng, người phụ trách.
- **Nhật ký (Journal):** Lịch sử các lệnh điều khiển, sự kiện hệ thống và đồng bộ của nhà máy.
- **Chẩn đoán (Diagnostics):** Sức khỏe kết nối, kiểm tra chất lượng dữ liệu, checklist commissioning và biên bản bàn giao.
- **Báo cáo (Reports):** Trình tạo báo cáo sản lượng, hiệu suất PR, tiết kiệm năng lượng của nhà máy.
- **Logger / Local Agent / Mạng (Network):** Thông tin logger thu thập, Site Agent, trạng thái mạng Ethernet/Wi-Fi/4G, bộ đệm dữ liệu outbox.

---

### 2. Tab Nhà máy (Plants)
- Quản lý danh mục toàn bộ nhà máy trong hệ thống.
- Lọc theo khách hàng, khu vực địa lý, loại hình lắp đặt (Áp mái hộ gia đình, C&I công nghiệp, Farm mặt đất).
- Thêm mới, chỉnh sửa hồ sơ nhà máy, công suất đỉnh (kWp), tọa độ GPS, múi giờ vận hành.
- Nhấp vào một nhà máy sẽ mở ngay Không gian làm việc 10 tab tương ứng.

---

### 3. Tab Hệ thống (System Topology)
- Sơ đồ nguyên lý đấu nối điện (Single Line Diagram / Topology) giữa các thành phần: Dàn pin PV $\to$ Biến tần (Inverter) $\to$ Hệ thống lưu trữ (Pin/BMS) $\to$ Điểm đấu nối lưới (Grid Meter/CT) $\to$ Tải tiêu thụ (Loads) $\to$ Cổng dự phòng khẩn cấp (EPS/UPS) $\to$ Máy phát (Generator).
- Hiển thị mối quan hệ phụ thuộc truyền thông giữa Logger và các thiết bị trên đường bus RS485/Modbus.

---

### 4. Tab Bản đồ (Map)
- Bản đồ số GIS tích hợp hiển thị vị trí các nhà máy trên toàn quốc/vùng lãnh thổ.
- Gom cụm (Clustering) tự động theo mật độ khu vực; lọc nhanh theo trạng thái (Bình thường, Cảnh báo, Mất kết nối).
- Panel chi tiết bên phải hiển thị tóm tắt thông số nhà máy khi nhấp chọn pin trên bản đồ, kèm nút bấm đi tới Workspace chi tiết.

---

### 5. Tab Thiết bị (Equipment)
Quản lý toàn bộ danh mục thiết bị trong hệ thống: Inverter, Pin lưu trữ / BMS, Logger / Gateway, Đồng hồ điện (Smart Meter / CT), Tải ưu tiên / EPS, Máy phát điện (Generator / ATS).  
Khi chọn một thiết bị, mở **Không gian làm việc thiết bị (Device Workspace) gồm 6 tab con**:
1. **Giám sát (Monitoring):** Trạng thái hoạt động, thông số điện áp/dòng điện từng string DC, pha AC, công suất, nhiệt độ, SOC/SOH của pin, độ mới dữ liệu.
2. **Điều khiển từ xa (Remote Control):** Các lệnh điều khiển nhanh được cho phép theo profile (bật/tắt, giới hạn công suất, chế độ làm việc).
3. **Cấu hình nâng cao (Advanced Config):** Cài đặt chuyên sâu theo nhóm: Đồng hồ/CT, Pin/BMS, Giới hạn phát lưới (Zero-Export), Sạc từ lưới, Máy phát/Smart-load, Tham số lưới bảo vệ. *(Các trường chưa nghiệm thu hiển thị xám an toàn)*.
4. **Nhật ký (Journal):** Lịch sử lệnh gửi tới thiết bị, before/after diff, kết quả readback từ phần cứng.
5. **Tài liệu (Documents):** Tài liệu hướng dẫn sử dụng, bảng thanh ghi Modbus, biên bản nghiệm thu lắp đặt, release note firmware.
6. **Bảo trì (Maintenance):** Sức khỏe thiết bị, lịch sử sửa chữa, các yêu cầu cập nhật firmware.

---

### 6. Tab Điều khiển (Control Engine)
- Giao diện trung tâm thực thi điều khiển an toàn: Chọn nhà máy $\to$ Chọn thiết bị $\to$ Chọn lệnh / preset.
- Luồng an toàn bắt buộc: So sánh tham số hiện tại $\to$ Xem trước (Diff & Preview) $\to$ Bắt buộc xác nhận chủ đích $\to$ Giám sát trạng thái gửi lệnh $\to$ Đọc lại xác minh (Readback Verification).
- Tự động khóa thiết bị nếu gặp lỗi không rõ kết quả (Timeout Quarantine) để bảo vệ an toàn vật lý.

---

### 7. Tab Lịch / TOU (Time of Use)
- Soạn thảo ma trận lịch vận hành 7 ngày trong tuần theo múi giờ địa phương.
- Cấu hình từng khung giờ: Giờ cao điểm, bình thường, thấp điểm; mức SOC mục tiêu của pin; công suất nạp/xả tối đa; cho phép sạc lưới hay phát lưới.
- Kiểm tra tự động các khoảng trống (gaps) hoặc chồng lấn giờ (overlaps).
- Lưu phiên bản lịch, chạy thử mô phỏng (dry-run simulation), và chuẩn bị triển khai an toàn xuống inverter.

---

### 8. Tab Điều phối EMS (Energy Management System)
- Bộ soạn thảo quy tắc tự động hóa (Automated Rules Engine) với nhiều điều kiện AND kết hợp và chuỗi hành động tương ứng.
- Ví dụ: *NẾU (Giá điện == Cao điểm) VÀ (Pin SOC > 50%) $\to$ THÌ (Xả pin cấp tải tiêu thụ, chặn phát lưới)*.
- Thiết lập thời gian duy trì (Hold time), thời gian hồi (Cooldown) và quy tắc chống rung lắc đóng cắt (Hysteresis).
- Bộ phát hiện xung đột giữa lịch TOU và quy tắc EMS.

---

### 9. Tab Dữ liệu & Kết nối (Data & Connectivity)
Không gian quản lý kết nối kỹ thuật toàn diện với **9 tab con**:
1. **Tổng quan (Overview):** Tổng quan chất lượng dữ liệu toàn hệ thống, số lượng kết nối đang online/offline, độ trễ và tỷ lệ mất mẫu đo.
2. **Dữ liệu đo (Telemetry Data):** Truy vấn dữ liệu chuỗi thời gian, biểu đồ nhiều trục, xuất khẩu dữ liệu raw.
3. **Nguồn dữ liệu (Data Sources):** Quản lý nguồn thu thập (Cloud API, Local Modbus, Site Agent), quy tắc ưu tiên nguồn đọc và quyền điều khiển.
4. **Tài khoản cloud (Vendor Cloud Accounts):** Thiết lập kết nối API tới các hãng (Deye, Solis, SOLARMAN, v.v.) theo chuẩn bố cục **Mockup #21** (Bảng hãng bên trái, Panel cấu hình & kiểm tra quyền bên phải, 3 thẻ trạng thái ở chân trang).
5. **Local Agent:** Quản lý các bộ thu thập cục bộ tại công trình (Site Agent), mã định danh, hàng đợi lưu đệm outbox khi mất mạng, trạng thái đồng bộ về trung tâm.
6. **Cấu hình thu thập (Collection Policies):** Chu kỳ lấy mẫu (1–5s local, 1–5 phút cloud), giới hạn quota API và thuật toán giãn cách khi gặp lỗi.
7. **Bản đồ dữ liệu / Ánh xạ (Metric Mapping):** Khung ánh xạ từ trường dữ liệu native/thanh ghi Modbus của từng hãng sang mô hình chuẩn hóa (Canonical Telemetry).
8. **Chẩn đoán (Diagnostics):** Công cụ kiểm tra sức khỏe đường truyền, bộ kiểm tra nghiệm thu (Commissioning Checklist 6 bước), chẩn đoán thiết bị và nhật ký kết nối.
9. **Nhật ký sync (Sync Logs):** Lịch sử chi tiết các lần đồng bộ dữ liệu, mã lỗi HTTP/Modbus, số lượng bản ghi đã nạp thành công.

---

### 10. Tab Cảnh báo (Incident Center)
- Trung tâm xử lý sự cố O&M: Tiếp nhận mã lỗi từ thiết bị và các bất thường do hệ thống phát hiện.
- Phân loại mức độ nghiêm trọng: Nghiêm trọng (Critical), Cảnh báo (Warning), Thông tin (Info).
- Theo dõi thời hạn SLA 24/7 (Thời hạn phản hồi, Thời hạn khắc phục sự cố).
- Kèm quy trình hướng dẫn xử lý sự cố từng bước (Playbooks) và tính năng tạo ngay phiếu công việc bảo trì (Maintenance Work Order) liên kết.

---

### 11. Tab Báo cáo (Reports)
- Báo cáo sản lượng điện mặt trời (PV Yield), điện tự tiêu thụ, điện mua từ lưới, điện bán lên lưới.
- Báo cáo hiệu suất hệ thống PR (Performance Ratio) và chỉ số khả dụng (Uptime).
- Báo cáo tổng hợp sự cố và thời gian xử lý SLA của đội ngũ vận hành.
- Xuất dữ liệu đa định dạng: File bảng tính CSV, Excel (XLSX), và giao diện xem trước in ấn chuyên nghiệp chuẩn quốc tế (`@media print`).

---

### 12. Tab Bảo trì (Maintenance)
Quản lý công tác bảo trì kỹ thuật tại công trường với **4 tab con**:
1. **Sức khỏe hệ thống (System Health):** Đánh giá tình trạng suy giảm hiệu suất tấm pin, chu kỳ nạp/xả pin lưu trữ, nhiệt độ biến tần.
2. **Công việc bảo trì (Work Orders):** Quản lý phiếu giao việc: Người phụ trách, mức độ ưu tiên, hạn hoàn thành, checklist công việc thực tế, hồ sơ nghiệm thu.
3. **Firmware:** Quản lý danh mục phiên bản firmware cho từng dòng máy, kiểm tra checksum an toàn, hàng đợi yêu cầu nâng cấp OTA.
4. **Kế hoạch bảo trì (Maintenance Plans):** Lịch trình bảo trì phòng ngừa định kỳ (vệ sinh pin, siết bu-lông siết ốc, kiểm tra tủ điện AC/DC).

---

### 13. Tab Nhật ký (Audit Journal)
- Nhật ký toàn diện của cả hệ thống: Ghi vết toàn bộ hành động người dùng (ai, thao tác gì, trên thiết bị nào, lúc nào, giá trị trước/sau, kết quả).
- Bảo vệ tính toàn vẹn bằng chuỗi băm mật mã (Cryptographic Hash Chain) phát hiện can thiệp dữ liệu.
- Bộ lọc đa chiều theo phạm vi nhà máy, loại sự kiện, người thực hiện và khoảng thời gian.

---

### 14. Tab Quản lý người dùng (Users & RBAC)
- Danh sách tài khoản người vận hành: Administrator, Engineer, Installer, Technician, Customer/Owner.
- Phân quyền theo phạm vi nhà máy (Site Scopes): Giới hạn kỹ thuật viên chỉ được xem và thao tác trên đúng các công trình được giao.
- Khóa tài khoản tức thời, thu hồi phiên làm việc (Revoke Session), đổi mật khẩu an toàn.

---

### 15. Tab Cài đặt (Settings)
Gồm các tab con cài đặt toàn cục và phân quyền:
1. **Thông tin chung (General):** Tên tổ chức, múi giờ mặc định, đơn vị đo lường (kW/MW, kWh/MWh, °C/°F), ngôn ngữ hiển thị (Tiếng Việt / English).
2. **Biểu giá điện (Tariff Matrix):** Biểu giá điện mua/bán theo khung giờ TOU (giờ cao điểm, bình thường, thấp điểm) áp dụng cho tính toán kinh tế.
3. **Quyền sở hữu & phân cấp (Ownership):** Quản lý danh mục khách hàng, hợp đồng bảo trì EPC.
4. **Cảnh báo & thông báo (Notifications):** Cấu hình kênh gửi thông báo tự động (Email, Webhook, SMS, Zalo ZNS).
5. **Nguồn dữ liệu mặc định (Data Sources):** Cấu hình các tham số kết nối hệ thống.
6. **Liên kết thiết bị mới (Onboarding Wizard):** Quy trình hướng dẫn 4 bước thêm nhà máy và thiết bị mới vào hệ thống.
7. **Tự động hóa (Automation):** Quản lý các tác vụ ngầm định kỳ của Controller.

---

## IV. Chi tiết 11 Khối Bắt buộc tại Tab Tổng quan (Overview Tab Fields)

Tại tab **Tổng quan** (của Workspace Nhà máy / Fleet), 11 khối thông tin bắt buộc phải được bố trí rõ ràng, trực quan:

| STT | Khối thông tin | Nội dung thể hiện & Hành vi giao diện | Drill-down liên kết |
|---|---|---|---|
| **1** | **Sơ đồ năng lượng realtime (Energy Flow)** | - Mô phỏng trực quan dòng năng lượng: PV $\to$ Inverter $\to$ Pin (sạc/xả + SOC%) $\to$ Lưới (mua/bán) $\to$ Tải $\to$ Cổng EPS/Máy phát.<br>- Mũi tên động theo đúng chiều công suất thực tế, hiển thị số liệu W/kW kèm độ mới dữ liệu.<br>- Chế độ hiển thị linh hoạt, nút phóng to toàn màn hình (Fullscreen mode), chú thích (legend). | Bấm vào từng khối (Node) $\to$ Chuyển đến tab **Thiết bị** hoặc **Dữ liệu** chi tiết tương ứng. |
| **2** | **Điều khiển nhanh (Quick Presets)** | - Các nút thao tác nhanh: Tự dùng tối đa, Chặn phát lưới (Zero-Export), Sạc nhanh từ lưới, Chế độ dự phòng khẩn cấp.<br>- Hiển thị tham số hiện tại và giá trị dự kiến áp dụng.<br>- Nút bấm áp dụng nhanh hoặc nút "Mở cấu hình chi tiết".<br>- **Các nút chưa có profile xác thực phần cứng được hiển thị màu xám an toàn (`unknown-can't-click`) kèm lý do rõ ràng.** | Bấm "Cấu hình chi tiết" $\to$ Mở tab **Điều khiển từ xa / Nâng cao**. |
| **3** | **Trạng thái nhà máy (Plant Status & Energy)** | - Huy hiệu trạng thái: Online, Offline, Cảnh báo, Dữ liệu trễ.<br>- Chỉ số sản lượng phát điện PV, công suất tiêu thụ tải, trạng thái pin.<br>- Lựa chọn kỳ thống kê: **Hôm nay / Ngày / Tháng / Năm / Tổng**.<br>- Biểu đồ số liệu chi tiết theo chu kỳ được chọn. | Bấm vào biểu đồ hoặc số liệu $\to$ Mở tab **Dữ liệu** với bộ lọc tương ứng. |
| **4** | **Sản lượng & tiêu thụ (Yield & Consumption)** | - So sánh sản lượng mặt trời và mức tiêu thụ tải theo các mốc: Hôm nay / Tháng này / Năm nay.<br>- Biểu đồ trực quan thanh/vùng, hỗ trợ tooltip hiển thị chính xác ngày giờ, đơn vị và nguồn đo. | Bấm "Xem phân tích chi tiết" $\to$ Mở tab **Báo cáo**. |
| **5** | **Tỉ lệ tự dùng (Self-Consumption Rate)** | - Tỉ lệ điện mặt trời được tiêu thụ tại chỗ (Self-consumption %) và tỉ lệ tải độc lập không cần lưới (Self-sufficiency %).<br>- Biểu đồ tròn/vòng đo lường mức độ tự chủ năng lượng của công trình. | Bấm vào tỉ lệ $\to$ Mở tab **Báo cáo kinh tế**. |
| **6** | **Thời tiết & dự báo (Weather & Forecast)** | - Nhiệt độ hiện tại, tình trạng thời tiết (Nắng, Nhiều mây, Mưa), độ ẩm, tốc độ gió.<br>- Chỉ số bức xạ mặt trời (Irradiance - $W/m^2$), giờ bình minh và hoàng hôn.<br>- Dự báo thời tiết theo từng giờ trong ngày.<br>- Nguồn dữ liệu: Ưu tiên cảm biến thời tiết từ trạm/inverter nếu có; fallback sang API thời tiết công khai theo tọa độ GPS của công trình. | Bấm vào khối thời tiết $\to$ Mở rộng biểu đồ dự báo bức xạ và sản lượng tiềm năng. |
| **7** | **Thiết bị trong hệ thống (System Equipment)** | - Danh sách tóm tắt thiết bị chính: Biến tần, Khối pin lưu trữ, Bộ thu thập Logger, Công tơ điện.<br>- Hiển thị Model, Serial Number, Công suất tức thời, Trạng thái online/offline, Cảnh báo đi kèm thiết bị. | Bấm "Xem tất cả thiết bị" $\to$ Mở tab **Thiết bị**. |
| **8** | **Kết nối & nguồn dữ liệu (Connectivity & Sources)** | - Trạng thái kết nối các nguồn: Local Agent, Cloud API hãng, Kết nối trực tiếp qua Modbus/RS485.<br>- Huy hiệu rõ ràng: Online (Xanh), Offline (Xám), Lỗi xác thực (Đỏ), Mất đồng bộ (Vàng).<br>- Thời điểm đồng bộ thành công gần nhất. | Bấm "Quản lý kết nối" $\to$ Mở tab **Dữ liệu & Kết nối**. |
| **9** | **Cảnh báo gần đây (Recent Alerts)** | - Danh sách 3–5 sự cố mới nhất: Mã lỗi, mô tả sự cố dễ hiểu, thiết bị bị ảnh hưởng, thời điểm xảy ra.<br>- Huy hiệu mức độ nghiêm trọng: Nghiêm trọng (Đỏ), Cảnh báo (Vàng). | Bấm "Xem toàn bộ sự cố" $\to$ Mở tab **Cảnh báo (Incident Center)**. |
| **10** | **Nhật ký điều khiển gần đây (Recent Commands)** | - Danh sách các lệnh điều khiển được gửi gần nhất: Tên lệnh, Người thực hiện, Thời điểm gửi, Trạng thái (Đang gửi, Thành công, Đã đọc lại xác minh, Thất bại). | Bấm "Xem toàn bộ nhật ký" $\to$ Mở tab **Nhật ký lệnh**. |
| **11** | **Vị trí & thông tin nhà máy (Location & Info)** | - Địa chỉ công trình, Tọa độ GPS, Công suất thiết kế ($kWp$), Dung lượng pin ($kWh$).<br>- Tên khách hàng sở hữu, Thông tin liên hệ, Ngày đóng điện vận hành. | Bấm "Xem bản đồ" $\to$ Mở tab **Bản đồ**; Bấm "Sửa hồ sơ" $\to$ Mở tab **Cài đặt nhà máy**. |

---

## V. Phương pháp Triển khai Mã nguồn Tiếp theo

Theo đúng định hướng chỉ đạo của bạn:
1. **Triển khai đồng bộ Core BE, Giao diện FE và Test code:**
   - Dựng sẵn toàn bộ cấu trúc các tab, sub-tab và 11 khối hiển thị trên giao diện.
   - Các trường cần xác thực hoặc thiếu profile thiết bị thật sẽ giữ ở trạng thái xám (`unknown-can't-click`) để sẵn sàng kết nối sau.
2. **Chưa chạy test, QA, build lặp lại trong giai đoạn viết mã:**
   - Tập trung viết code liên tục cho đến khi hoàn tất trọn vẹn toàn bộ Core và UI.
   - Khi hoàn thành đầy đủ, sẽ tiến hành một đợt xác minh tổng hợp lớn duy nhất (`ruff check`, `scripts/check-ui.cjs`, `pytest`, `python -m build`).
   - Sau đó cập nhật kết quả và xin phê duyệt kế hoạch tiếp theo.
