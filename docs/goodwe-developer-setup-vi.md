# GoodWe: xác định nền tảng trước khi xin API

Kiểm tra ngày 04/10/2026. [Checklist và mẫu thư](vendor-api-access-guide-vi.md).

**Cập nhật 07/10/2026:** người dùng đã đăng nhập được portal SEMS+, đã kiểm tra chỉ đọc inventory và dữ liệu hiển thị. [Baseline QA](evidence/goodwe-portal-qa-2026-10-07.md). Ảnh logo ban đầu không đủ nhận diện ứng dụng, nhưng phiên portal hiện tại đã xác định là SEMS+. Không cần gửi mật khẩu trong chat.

## Phát hiện cần lưu ý

Trang [SEMS Portal](https://eu.semsportal.com/home/login) công bố thông báo ngừng dịch vụ/chuyển sang SEMS+. Điều này là lý do phải kiểm tra lại connector cũ; không phải phép thử chứng minh mọi API cũ ở mọi vùng đã bị tắt. Không tự chuyển hostname rồi cho rằng giao thức đăng nhập tương thích.

[API Introduction của GoodWe](https://community.goodwe.com/static/images/2022-11-08281223.pdf), trang 1–3, là tài liệu năm 2022: phân biệt Open API cho organization với Real-Time Data API dành cho bên thứ ba, cần thỏa thuận, danh sách thiết bị và quyền từ chủ thiết bị. Tài liệu này **không đủ xác nhận hợp đồng SEMS+ hiện nay**.

## Các bước đề nghị thực hiện

1. Ghi đúng tên app, phiên bản và vùng tài khoản; không tạo/chuyển nhà máy mới.
2. Liên hệ hỗ trợ trong app hoặc đầu mối dịch vụ GoodWe được đơn vị lắp đặt xác nhận; đề nghị chuyển yêu cầu tới đội API/SEMS+.
3. Gửi mẫu thư chung, hỏi đường tích hợp chỉ đọc dành cho ứng dụng nhiều khách hàng trên **nền tảng hiện tại**.
4. Hỏi có cần organization/API account riêng, App ID/Secret, whitelist SN hay OAuth; xin tài liệu hiện hành và cách khách hàng cấp/thu hồi quyền.
5. Chỉ sau khi có câu trả lời mới chốt cách cấu hình SolarOne. Chưa có bằng chứng về một trang tự tạo App ID phổ quát cho tài khoản chủ nhà.

## Code hiện tại

SolarOne có hai đường riêng: SEMS cũ nhận email/mật khẩu và ID nhà máy; SEMS+ thử nghiệm nhận email/mật khẩu và máy chủ rồi tự khám phá nhà máy. Cả hai form này không yêu cầu App ID/Secret. Không nhầm mật khẩu GoodWe với mật khẩu hộp thư Gmail hoặc SolarOne.

**Có thể bắt đầu thử nghiệm kết nối SEMS+ chỉ đọc do bạn nhập tài khoản trong SolarOne.** Chọn Cài đặt & Hãng → Kết nối GoodWe → SEMS+ → Tôi đã có thông tin kết nối; chọn đúng máy chủ giống app, tự nhập email/mật khẩu và đọc phần xác nhận quyền/điều khoản. Không gửi mật khẩu trong chat. Sau xác thực cần kiểm tra kết nối, đối chiếu danh mục/số đo với portal; chưa mở điều khiển. [Kiểm thử cục bộ và giới hạn](evidence/goodwe-semsplus-connector-2026-10-07.md). Tương thích vùng/tài khoản thật chưa nghiệm thu; hướng xin API chính thức bên trên vẫn là hướng dài hạn, không phải điều kiện đã chứng minh cho mọi luồng SEMS+.
