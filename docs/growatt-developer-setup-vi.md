# Growatt: xin API token

Kiểm tra ngày 04/10/2026. [Checklist và mẫu thư](vendor-api-access-guide-vi.md).

## Quy trình trong tài liệu hãng

[Installer Operation Manual](https://cdn.growatt.com/pdf/Installer%20Operation%20Manual.pdf), trang 90, minh họa:

1. Với tài khoản có quyền quản trị phù hợp, vào System Setting → System Management → API management.
2. Chọn Add API Request (API-token).
3. Điền máy chủ, công ty, quốc gia, người liên hệ, email/mã xác minh, lý do và whitelist IP/domain.
4. Đọc thỏa thuận trước khi gửi. Quyền token gắn với các tài khoản được chỉ định.

Đây là hướng dẫn installer, không chứng minh chủ nhà dùng ShinePhone cũng thấy menu. Đã xem trực tiếp ảnh trang 90; bố cục giao diện thực tế có thể thay đổi theo quyền/vùng.

## Nếu bạn chỉ có tài khoản người dùng

Nhờ đơn vị lắp đặt hoặc hỗ trợ Growatt xin quyền đọc cho đúng tài khoản/nhà máy. Không lập công ty giả để vượt màn đăng ký. Hỏi rõ hiệu lực token, danh sách tài khoản được gán, dữ liệu cho phép, giới hạn và cách thu hồi. Không đổi quyền sở hữu nhà máy để lấy token.

IP whitelist phải là IP ra ngoài của máy chạy SolarOne; chỉ điền sau khi kỹ thuật xác nhận, không lấy IP LAN của điện thoại. Đây là khuyến nghị triển khai của dự án.

## Dùng với SolarOne

Form hiện nhận `token` và vùng, không yêu cầu App ID/App Secret. Chưa nghiệm thu mọi vùng hay quy trình tự phục vụ nhiều khách hàng. Token do hãng cấp phải được kiểm phạm vi bằng discovery chỉ đọc trước khi đồng bộ; kết nối thành công không được coi là phép điều khiển inverter.
