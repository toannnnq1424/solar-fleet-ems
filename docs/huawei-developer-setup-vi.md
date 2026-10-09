# Huawei / FusionSolar: tài khoản Northbound

Kiểm tra ngày 04/10/2026. [Checklist và mẫu thư](vendor-api-access-guide-vi.md).

## Loại thông tin cần phân biệt

Giao diện login Northbound chính thức dùng `userName` và `systemCode`; System Code là mật khẩu của tài khoản API, không phải mặc định App Secret của ứng dụng. Nguồn: [Huawei Login Interface](https://info.support.huawei.com/enterprise/en/doc/EDOC1100307213/9e1a18d2/login-interface). Nội dung được đối chiếu qua chỉ mục tài liệu chính thức; trang mở trực tiếp trả hạn chế truy cập trong đợt này.

## Trình tự đề nghị

1. Giữ tài khoản chủ nhà máy hiện tại. Xác định máy chủ/vùng FusionSolar đang dùng.
2. Nhờ quản trị viên công ty lắp đặt hoặc hỗ trợ Huawei kiểm tra khả năng cấp **Northbound API account chỉ đọc**.
3. Gửi mục đích, nhà máy thực sự được phép, danh sách dữ liệu muốn đọc, thời hạn và tần suất.
4. Đề nghị cấp tài khoản API, System Code, base URL đúng vùng và tài liệu áp dụng. Yêu cầu xác nhận rõ quyền đọc/ghi và cách thu hồi.
5. Nếu muốn phục vụ nhiều chủ nhà độc lập, hỏi mô hình ủy quyền được hãng hỗ trợ; không coi tài khoản API của một công ty tự truy cập được mọi tài khoản.

Các bước 2–5 là quy trình liên hệ đề xuất, **không phải đường menu đã xác minh**. Không hướng dẫn giả định mọi tài khoản người dùng đều có Northbound Management. Nếu thiếu menu, hỏi quản trị viên/hãng; không khai sai vai trò để đăng ký.

## Dùng với SolarOne

Connector nhận `user_name`/`system_code`, không phải email và mật khẩu app thông thường. Quản trị viên chuẩn bị quyền này; người dùng không nên phải đoán System Code. Cấp được tài khoản chưa chứng minh endpoint, vùng, model và đơn vị đã tương thích; cần QA chỉ đọc riêng.
