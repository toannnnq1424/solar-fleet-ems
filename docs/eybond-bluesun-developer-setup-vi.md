# Eybond / SmartESS và Bluesun: xác định cloud/logger

Kiểm tra ngày 04/10/2026. [Checklist và mẫu thư](vendor-api-access-guide-vi.md).

## Không xin khóa chỉ dựa trên nhãn inverter

[Trang Eybond chính thức](https://www.eybond.com/) liên kết SmartESS với DessMonitor, SmartClient với ShineMonitor và công bố email `market@eybond.com`. Tên ShineMonitor không đồng nghĩa Growatt ShinePhone/ShineServer.

Chưa xác minh được một cổng tự phục vụ cấp App ID/App Secret chung cho mọi thiết bị Bluesun. Đây là giới hạn khảo sát, không phải kết luận hãng không có API.

## Các bước đề nghị

1. Xem tên ứng dụng đang dùng, đường website cloud, model logger và inverter. Chỉ chụp phần tên/model đã che QR, serial và thông tin cá nhân khi trao đổi công khai.
2. Nhờ đơn vị lắp đặt xác nhận cloud/OEM. Nếu SOLARMAN, theo [hướng dẫn SOLARMAN](solarman-developer-setup-vi.md); nếu Eybond, hỏi đội Eybond/OEM.
3. Gửi mẫu thư chung tới đầu mối đúng nền tảng; đề nghị tài liệu API, kiểu tài khoản và Company Key nếu hợp đồng đó yêu cầu.
4. Hỏi Company Key thuộc ứng dụng/nền tảng nào, có cần xét duyệt đối tác, và cách mỗi khách hàng cấp/thu hồi quyền đọc.
5. Nhận câu trả lời rồi mới chọn connector. Không thử mật khẩu lần lượt vào các cloud dựa trên phỏng đoán thương hiệu.

Đây là quy trình xác minh đề xuất, không phải cam kết hãng sẽ cấp khóa theo email.

## Dùng với SolarOne

Connector Eybond hiện nhận tên đăng nhập, mật khẩu và Company Key. Giá trị mặc định có trong code không chứng minh quyền đối tác, quyền thương mại hay sự đồng ý của khách hàng. Không sao chép khóa công khai thành “khóa riêng đã được cấp”.

Bluesun có mục trong hệ thống nhưng vẫn cần xác định exact model/logger/platform; không coi có logo và form là hỗ trợ đầy đủ. Đọc telemetry, chuẩn hóa thông số, lịch sử và điều khiển là các phần nghiệm thu riêng.
