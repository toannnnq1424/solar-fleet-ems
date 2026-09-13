# Bổ sung bằng chứng tài khoản Deye Cloud — 13/09/2026

Sau báo cáo nghiên cứu ban đầu, người dùng cho phép kiểm tra phiên Deye Cloud đã đăng nhập trong in-app browser. Đã đọc màn hình danh sách, một công trình hybrid, inverter, logger và các nhóm Device Control; không nhấn Setup, không nhập tham số, không gửi lệnh thay đổi. Nguồn `DEYE_UI_OBS_001`, cấp E: quan sát UI có xác thực tại [Deye Cloud](https://www.deyecloud.com/). Bản ghi này chủ ý bỏ tên công trình, serial, địa chỉ, MAC, SSID và các setpoint vận hành.

## Các thông tin thu hẹp UNKNOWN

| Phạm vi | Quan sát | Giới hạn kết luận |
|---|---|---|
| Region web | Europe Data Center | Không chứng minh app OpenAPI đã được cấp hoặc cùng quyền với web |
| Inverter | Three phase LV Hybrid, Rated Power 16 kW | Tên model thương mại chính xác chưa hiển thị; không tự gán SUN-16K-SG05LP3 |
| Version | Protocol 0104; MAIN 2107-1175-1809; HMI 1001-C05C | Chỉ thiết bị đã xem; chưa có register map tương ứng |
| Logger | Module DYDA_WiBLE_1.6.2; Extended System EMC3183 | Chưa biết tên model thương mại, local API/Modbus TCP, quyền hoặc coexistence |
| Chu kỳ | Data Uploading Period 1 Min; Data Acquisition Period 60 s | Quan sát cấu hình logger, không phải SLA API hoặc bằng chứng dữ liệu local 1 giây |
| Topology | Một inverter và một logger cùng công trình; logger hiển thị tối đa 1 thiết bị | Không suy rộng mọi công trình hoặc mọi logger |
| Web native | Battery; System Work Mode 1/2; Grid; H/LVRT; SmartLoad; Basic; Advanced 1/2; EV Charge | Menu và field không tự chứng minh lệnh hoạt động trên phần cứng |

## Các vấn đề tác động trực tiếp thiết kế

- Panel thông tin inverter có timestamp mới, trong khi Battery, Work Mode, TOU và Advanced có “Read at” từ tháng 7–8/2026. Fresh telemetry không đồng nghĩa fresh configuration. Không dùng cached config làm điều kiện cho lệnh hoặc xác minh sau lệnh.
- UI phân biệt Batt Shutdown, Batt Low và Batt Restart. Không đổi nhãn Batt Low thành Reserve SOC.
- Work Mode, Solar Sell, Max solar power, Max Sell Power, Zero export power và Hard Limit Function là các field riêng. Không rút gọn chúng thành một toggle “không phát lưới”.
- TOU có 6 dòng với start/end, Grid Charge, Gen, Sell, Power và Batt; dòng cuối có thể qua nửa đêm. Cần xác minh cách API dùng mốc thời gian và timezone trên thiết bị này trước khi ghi.
- Advanced có CT ratio, EX_MeterCT, Grid Tie Meter2, Meter Select, neutral/earth bonding, parallel, Modbus SN, DRM và peak shaving. Các field này được giữ trong catalog bằng chứng UI, chưa tạo register hoặc private web endpoint để ghi.
- Các mục SmartLoad, Advanced 2 và EV có field chưa chọn/chưa đọc. Không tính chúng là tính năng đã nghiệm thu.

## Chưa được phép nâng trạng thái

OpenAPI appId/appSecret, quyền account/app, exact inverter/logger model, protocol table, range và test readback vẫn thiếu. Phiên browser được dùng để nghiên cứu UI, không trích cookie/token để giả lập API tích hợp. Bản phần mềm tiếp tục READ ONLY và giữ mọi live control ở UNKNOWN.

Firmware quan sát được là đầu vào cho đợt tìm manual/model tiếp theo, không thay thế nhãn máy hoặc xác nhận của kỹ thuật viên. Xem [commissioning checklist](hardware-acceptance.md) cho bằng chứng còn cần.
