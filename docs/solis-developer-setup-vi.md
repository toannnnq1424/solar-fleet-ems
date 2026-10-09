# SolisCloud: xin đúng loại khóa

Kiểm tra ngày 04/10/2026. [Hướng dẫn chung và mẫu thư](vendor-api-access-guide-vi.md).

## Các bước do hãng công bố

**Đọc nhà máy của tài khoản hiện có:**

1. Đăng nhập [SolisCloud](https://www.soliscloud.com).
2. Vào Service → API Management → Activate Now.
3. Xác minh danh tính; nhận KeyID/KeySecret. Đăng xuất rồi đăng nhập lại.
4. Quyền theo nhà máy tài khoản sở hữu hoặc được chia sẻ.

**Ứng dụng cho nhiều khách hàng:**

1. Liên hệ Solis sales, xin biểu mẫu `SolisCloud API Activation Application.xlsx`.
2. Nộp hồ sơ; sau duyệt nhận `client_id`/`client_secret`.
3. Tích hợp OAuth: chủ nhà máy đăng nhập tại hãng và đồng ý cấp quyền.
4. Giai đoạn chỉ đọc yêu cầu `access_data`; không bỏ trống scope vì mặc định có thể gồm quyền khác.

Nguồn: [Solis Authorization](https://developer.soliscloud.com/guide/authorization.html). Hai cơ chế dùng giao diện API riêng.

## Ranh giới trong SolarOne

Form hiện tại dùng Key ID/Key Secret. Adapter có nhánh OAuth nhưng đang yêu cầu `client_credentials`; chưa có luồng chủ nhà máy cấp authorization code qua callback theo hướng dẫn hiện hành. Không coi đó là tích hợp OAuth nhiều khách hàng đã hoàn thiện, không dán OAuth secret vào ô Key Secret để thử.

Khuyến nghị: pilot tài khoản có sẵn dùng đúng khóa user-level; dự án nhiều khách hàng xin OAuth và lên kế hoạch sửa connector/consent riêng. Nếu không thấy menu, hỏi hỗ trợ Solis về vai trò và quyền API; không tạo tài khoản giả để tìm menu.
