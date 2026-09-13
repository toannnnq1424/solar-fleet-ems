# Commissioning và nghiệm thu phần cứng

Trạng thái hiện tại: **CHƯA NGHIỆM THU**. Bằng chứng từ Deye web xác nhận metadata/menu của một thiết bị, không chứng minh API write/readback. Checklist này dùng cho đợt kỹ thuật tiếp theo, không phải yêu cầu gửi thêm secret vào chat.

## Hồ sơ cần có

- Exact inverter model, logger model, battery/BMS model, serial lưu riêng, firmware MAIN/HMI/logger, protocol revision, region/grid code và topology CT/meter/parallel.
- Official API app/account type, quyền thực tế theo station/device, quota được hãng xác nhận, đúng data center.
- Tài liệu chính thức giải thích enum, đơn vị, min/max/step và applicability; giới hạn cấu hình khác giới hạn BMS realtime. UI có ô 220 A không chứng minh 220 A luôn an toàn.
- Đường telemetry và control độc lập, quyền/khả năng cloud và local riêng. Không tự bật Modbus khi việc đó có thể ngắt cloud logger.
- Fresh getter có timestamp hoặc bằng chứng response liên quan trực tiếp device-read order; tuổi dữ liệu và tolerance được mô tả.

## Chạy thử theo thứ tự

1. READ ONLY: discovery đầy đủ các trang; logger/inverter không nhầm loại; phân quyền không lộ công trình khác.
2. So sánh công suất/energy/timestamp của API với dữ liệu thiết bị. Xác minh dấu import/export và charge/discharge, scaling, unit, timezone, rollover/counter reset. Giữ raw capture đã lọc secret làm evidence riêng.
3. Xác minh config getter không dùng cache tháng trước. Mất mạng/thiết bị offline phải được phát hiện; stale telemetry không được gắn LIVE.
4. Với kỹ thuật viên có quyền tại công trình, chọn intent và phạm vi thử cụ thể. Lưu before, capability profile/version/source, preview/diff, giá trị/range, operator và idempotency key; xác nhận trước khi gửi.
5. Kiểm tra order accepted → waiting → terminal status → fresh readback đúng target; timestamp sau thời điểm gửi. HTTP 200/success/order 666 riêng lẻ chưa đủ VERIFIED.
6. Test timeout, mismatch, firmware đổi, mất quyền, writer khác thay cấu hình, lịch TOU qua nửa đêm và cloud/local conflict. Kết quả không rõ phải quarantine, không tự retry hoặc rollback.
7. Hoàn thành reconciliation có nhật ký. Profile chỉ áp dụng đúng model/logger/firmware/account/region đã nghiệm thu; không wildcard.

Không thử firmware update, factory reset, grid code, serial, anti-islanding, neutral/earth bonding hoặc arbitrary raw register trong quy trình normal control. Không suy ra hardware acceptance của chúng từ UI có menu.

## Biên bản acceptance

Lưu ngày giờ, người nghiệm thu, môi trường, tài liệu/source IDs, identity đầy đủ, request/response đã lọc bí mật, timing, order ID, ảnh/đo tại thiết bị khi phù hợp, expected/actual, sai số cho phép, kết quả và giới hạn. Bí mật và dữ liệu nhận diện khách hàng nằm trong kho được kiểm soát; repository chỉ giữ schema/profile đã review cần cho adapter.
