# SOLARMAN: xin App ID và App Secret

Kiểm tra ngày 04/10/2026. [Checklist và mẫu thư](vendor-api-access-guide-vi.md).

## Các bước

1. Xác định tài khoản đang thuộc SOLARMAN Smart hay Business và vùng máy chủ.
2. Mở [hướng dẫn kích hoạt chính thức](https://helpcenter.solarmanpv.com/portal/en/kb/articles/i-want-to-open-api-how-can-i-open-api). Tạo ticket qua Help Centre hoặc liên hệ `customerservice@solarmanpv.com`.
3. Cung cấp email tài khoản, vai trò thực tế, mục đích/website nếu có, gói miễn phí hoặc trả phí muốn hỏi.
4. Yêu cầu điều khoản và báo giá/hạn mức hiện hành; tự đọc trước khi xác nhận đồng ý. Không mặc định dự án nhiều khách hàng được miễn phí.
5. Hãng xét duyệt/kích hoạt và cấp App ID/App Secret. Hỏi rõ khóa áp dụng vùng nào và cách từng khách hàng cấp quyền.

Nguồn trên mô tả quy trình trao đổi với hỗ trợ, không xác nhận có nút tự tạo ứng dụng tức thời.

## Dùng với SolarOne

Connector hiện có nhận `app_id`, `app_secret`, định danh người dùng và mật khẩu; có lựa chọn vùng. Khóa ứng dụng không thay tài khoản có quyền với nhà máy. Không cần khách hàng thông thường tự xin khóa nếu sau này SolarOne được hãng chấp thuận mô hình ứng dụng dùng chung; luồng quản trị/consent đó phải được xây và nghiệm thu riêng, hiện không được suy ra từ form.

Sau khi được cấp, chỉ báo trạng thái duyệt và vùng; giữ secret ngoài chat. Trước QA thật phải kiểm quota, quyền đọc và đúng logger/model; chưa xin quyền điều khiển.
