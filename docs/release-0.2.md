# Solar Fleet 0.2 — core backend and bilingual workspace

## Tiếng Việt

Sidebar được thống nhất thành **Tổng quan · Nhà máy · Thiết bị · Vận hành · Sự cố & bảo trì · Dữ liệu & báo cáo · Cài đặt**. Một bộ lọc nhà máy dùng xuyên suốt các màn hình. Các ảnh mockup được quy về nhóm công việc, không dùng số liệu và trạng thái tương thích trong ảnh làm dữ liệu thật.

- Nhà máy: thêm và sửa hồ sơ, khách hàng, địa chỉ, công suất, múi giờ và tọa độ; tách metadata người dùng khỏi discovery cloud.
- Thiết bị: danh mục nhiều hãng, nguồn và độ mới của mẫu đo, dữ liệu gốc, lịch sử, khả năng điều khiển; Deye có đọc cấu hình và cảnh báo hãng.
- Vận hành: lưu lịch tuần/TOU nháp, kiểm tra chồng giờ, sao chép khung giờ; soạn quy tắc EMS và chạy thử; đánh giá tương thích nhiều thiết bị; nhật ký lệnh và checklist nghiệm thu.
- Sự cố/bảo trì: tạo, phân công, tiếp nhận, xử lý, đóng/mở lại; liên kết phiếu bảo trì với sự cố, chống ghi đè khi có cập nhật đồng thời, nhật ký và xuất CSV.
- Dữ liệu: lọc thiết bị/thông số/thời gian, biểu đồ điểm đo có timestamp, min/max cùng đơn vị, CSV và in báo cáo. Không cộng công suất thưa thành sản lượng hoặc tự tạo chỉ số tiết kiệm.
- Cài đặt: form kết nối Deye/Solis/SOLARMAN, vùng dữ liệu, trạng thái đồng bộ, tạm dừng kết nối, người dùng/phạm vi site, khóa tài khoản và thu hồi phiên, nghiên cứu và nhật ký bảo mật.
- Ngôn ngữ: tiếng Việt/English, định dạng số/ngày theo ngôn ngữ, bố cục desktop và màn hình nhỏ.

**Đây là bản nền có các workflow thực thi và lưu trữ được; chưa phải toàn bộ sản phẩm production trong mockup.** Chưa có driver phần cứng/Site Agent, lịch thực thi tự động, bulk dispatch, OTA firmware, cấu hình mạng/logger, bản đồ nền, thông báo email/Zalo/SMS, dự báo/giá điện hoặc báo cáo tài chính. Những mục này không được giả lập là đã hoạt động. Xem [trạng thái chi tiết](implementation-status.md).

Đăng nhập web của hãng giúp nghiên cứu và đối chiếu. Kết nối API chính thức còn cần app/key và quyền truy cập tương ứng. Hiện chưa có adapter nào được nghiệm thu live với credential của khách hàng; không có lệnh ghi xuống thiết bị thật trong đợt này.

## English

The shared workspace groups 26 mockups into seven stable areas. Backend workflows cover plant metadata, scoped device inventory, encrypted connector setup, incidents and linked maintenance work, schedule drafts, deterministic EMS dry runs, compatibility assessment, commissioning notes, access management, telemetry exports and audit records.

Deye, Solis and SOLARMAN have concrete read transports with synthetic contract tests. Other vendor cards explicitly require a contract or authorized observation. Connector implementation is separate from live account acceptance and model-specific control commissioning. No production hardware has been actuated.

The controller is a local single-process pilot. Schedule/rule drafts are not executed, manual commissioning notes do not unlock control, and unknown data is not converted to zero. Missing local drivers, dispatch, map/weather/notification providers, firmware workflows and production infrastructure are tracked separately from the delivered workflows.
