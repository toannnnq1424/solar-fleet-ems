# Sungrow / iSolarCloud: đăng ký ứng dụng

Kiểm tra ngày 04/10/2026. [Checklist và mẫu thư](vendor-api-access-guide-vi.md).

## Trình tự công khai

1. Mở [Sungrow Developer Portal](https://developer-api.isolarcloud.com/).
2. Đăng ký tài khoản developer và gửi yêu cầu duyệt.
3. Nộp thông tin ứng dụng và nhu cầu API qua mục Applications.
4. Sau duyệt, portal cấp AppKey. Trang công khai cũng mô tả OAuth 2.0 và các gói API.
5. Chưa rõ loại khóa/vùng/luồng ủy quyền thì hỏi đầu mối international trên portal: `lifulang@sungrowpower.com`.

Nguồn: phần Quick start/Contact us của portal trên. Không khẳng định tên từng nút hoặc vị trí Secret Key sau đăng nhập vì chưa kiểm tra bằng tài khoản được duyệt.

## Câu hỏi nên gửi thêm

Đề nghị hãng xác nhận: ứng dụng được cấp OAuth hay API login; tên secret tương ứng; endpoint khu vực; tài khoản developer không có nhà máy có được đăng ký không; khách hàng tự cấp/thu hồi quyền thế nào; danh sách điểm đo được đọc và giới hạn tần suất.

Đây là câu hỏi đề xuất của dự án, không phải khẳng định hãng sẽ duyệt mọi trường hợp.

## Ranh giới trong SolarOne

Form đang yêu cầu App Key/App Secret, tài khoản/mật khẩu cùng ID nhà máy/điểm đo. Không coi AppKey mới cấp là đủ: phải đối chiếu phiên bản API, vùng, cách ký/xác thực và discovery đang triển khai. Không nhập mã điểm đo đoán từ hãng khác; không dùng khóa chia sẻ tìm trên Internet.

Việc bỏ toàn bộ trường kỹ thuật khỏi luồng người dùng còn cần quản trị ứng dụng và consent/refresh/revoke đã kiểm chứng. Chưa có kết luận QA tài khoản thật cho Sungrow trong đợt này.
