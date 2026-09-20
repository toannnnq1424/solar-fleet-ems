# Không gian sản phẩm / Product workspaces

Ngày quyết định: 2026-09-13. Đầu vào: 26 mockup do chủ dự án cung cấp. Đây là ý định tính năng, không phải dữ liệu thực, chứng nhận hãng hoặc yêu cầu sao chép từng pixel.

## Điều hướng thống nhất

| Mục chính VI / EN | Chức năng có một nơi quản lý | Mockup nguồn |
|---|---|---|
| Tổng quan / Overview | Tình hình toàn danh mục, việc cần xử lý, chất lượng kết nối | 1–4 |
| Nhà máy / Plants | Danh sách, tìm kiếm, khách hàng, vị trí; chọn site để thu hẹp toàn bộ workspace | 1, 5, 15, 22 |
| Thiết bị / Devices | Inventory inverter, pin/BMS, logger, meter/CT và thiết bị phụ; dữ liệu và nguồn của từng thiết bị | 2–4, 7, 13, 17, 26 |
| Vận hành / Operations | Điều khiển theo khả năng, lịch nháp, kiểm tra nhiều thiết bị, nhật ký lệnh | 1, 8, 9, 11, 16, 18, 24 |
| Sự cố & bảo trì / Incidents & maintenance | Tiếp nhận, phân công, ghi chú, trạng thái xử lý, phiếu công việc | 10, 20, 23, 25 |
| Dữ liệu & báo cáo / Data & reports | Mẫu lịch sử, lọc khoảng thời gian/metric, xuất dữ liệu có nguồn và đơn vị | 6, 12, 26 |
| Cài đặt / Settings | Kết nối cloud, quyền người dùng, ngôn ngữ, tài liệu và mức tương thích | 13–15, 19, 21 |

Sidebar không thay đổi khi vào site/device. Site là bộ lọc phạm vi, device detail là một workspace dùng lại. Không tạo các trang “Hệ thống” và “Nhà máy” đồng nghĩa. Nút điều khiển nhanh luôn đi qua cùng bộ kiểm tra và nhật ký; không có đường ghi tắt ở trang tổng quan.

## Dành cho người ít kinh nghiệm

- Mặc định tiếng Việt, đổi sang English ở màn hình đăng nhập và trong ứng dụng; định dạng số/ngày theo ngôn ngữ.
- Màn hình đầu trả lời: đang quản lý bao nhiêu nhà máy, thiết bị nào cần chú ý, bước tiếp theo là gì. Kết nối mới theo luồng chọn hãng → nhập thông tin → khám phá → xem dữ liệu.
- Trạng thái kết nối, thời gian cập nhật và chất lượng dữ liệu tách riêng. Có kết nối API không có nghĩa telemetry mới hoặc điều khiển đã nghiệm thu.
- Dùng chữ cùng biểu tượng/màu; nhãn form rõ ràng, focus bàn phím, hỗ trợ màn hình nhỏ. Chi tiết giao thức, JSON và evidence nằm trong phần mở rộng.
- Không biến thiếu dữ liệu thành 0. Không cộng những đại lượng khác đơn vị, đo khác thời điểm hoặc chưa xác định cùng phạm vi; không vẽ SOC/V/Hz chung trục kW.
- Việc ghi nhận sự cố, lịch nháp, phiếu bảo trì là dữ liệu quản lý nội bộ. Không gọi việc “đã tiếp nhận” là đã xóa lỗi inverter; không gọi lưu lịch nháp là đã gửi xuống thiết bị.

## Nhóm nâng cao cần thực hiện theo khả năng thực

TOU trên inverter và lịch do controller chạy là hai cơ chế khác nhau. Native schedule cần giới hạn slot, timezone/DST, cách lưu và readback đúng model. Automation cần precedence, TTL, fail-safe đã thử; lưu nháp không kích hoạt scheduler. Bulk kiểm tra riêng từng thiết bị, không lấy thương hiệu làm kết luận Exact.

Firmware/network/grid-code/CT/BMS/generator/ATS và custom command cần protocol profile cụ thể. Không tự mở chức năng ghi vì mockup có nút. Khám phá qua cloud được phép đọc; quét mạng và đổi logger phải cấu hình phạm vi rõ ràng. “Raw command” là quyền kỹ thuật riêng, không tự cấp mọi quyền quản trị.

Bản đồ dùng tọa độ được cấu hình hoặc trả từ nguồn đã đối chiếu; không gửi vị trí khách hàng đến nhà cung cấp tile/geocode chưa cấu hình. Thời tiết, dự báo, tiết kiệm tiền, CO₂, uptime, health score và vòng đời pin chỉ xuất hiện khi có dữ liệu và phương pháp tính phù hợp. Chưa có dữ liệu thì hiển thị lý do, không dùng các con số trong mockup.

Commissioning lưu checklist và bằng chứng thật; các test có tác động điện cần người phụ trách công trình. Chữ ký, email/Zalo/SMS và phát hành báo cáo là các tích hợp riêng; không tự gửi thông báo từ việc người dùng cung cấp mockup.

Phạm vi đã chạy và phần còn thiếu được cập nhật trong [implementation status](implementation-status.md), không suy ra từ bảng này rằng mọi chức năng đã triển khai.
