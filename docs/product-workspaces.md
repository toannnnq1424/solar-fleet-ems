# Không gian sản phẩm / Product workspaces

[README dự án](../README.md) · [Mục lục tài liệu](README.md)

Cập nhật 25/09/2026 từ 26 mockup của chủ dự án. Bảy nhóm ban đầu ngày 13/09 đã được thay bằng **15 mục sidebar chuẩn** trong [bảng route/subtab](sidebar-subtabs-architecture.md). [Workspace specification](sidebar-workspace-specification.md) mô tả thiết kế đích; [đối chiếu 26 mockup](mockup-coverage.md) xác định phần thực sự có BE/FE.

## Một nơi sở hữu mỗi chức năng

- Tổng quan tóm tắt fleet hoặc site và dẫn tới chức năng chi tiết. Nhà máy sở hữu hồ sơ/khách hàng; Hệ thống sở hữu topology/SLD; Bản đồ sở hữu phân bố địa lý; Thiết bị sở hữu inventory/detail.
- Điều khiển sở hữu preview/confirm và vòng đời lệnh. Lịch/TOU và Điều phối EMS soạn mục tiêu/chính sách qua cùng capability/compiler, không có đường ghi tắt.
- Dữ liệu & kết nối sở hữu telemetry, source quality, collection, mapping và sync; liên kết tới màn chủ của cloud accounts, Local Agent và diagnostics. Báo cáo sở hữu artifact theo scope/kỳ.
- Cảnh báo sở hữu incident/timeline/SLA; Bảo trì sở hữu work order/plan/execution/review. Tạo phiếu từ incident giữ liên kết hai chiều.
- Nhật ký tập hợp dữ liệu command/operations/sync/security theo quyền. Người dùng sở hữu local roles/site scope; Cài đặt & Hãng sở hữu accounts và cấu hình, dẫn tới TOU/EMS/mapping dùng chung.

Sidebar không thay đổi khi vào site/device. Site là phạm vi của workspace, không phải một bản sao sidebar. Nhà máy và Hệ thống không cùng quản lý lại site CRUD. Các route tắt phải giữ scope; mọi page dùng [hệ thống UI chung](ui-design-system.md).

## Dành cho người ít kinh nghiệm

- Tiếng Việt/English có cùng cấu trúc; định dạng số/ngày theo ngôn ngữ.
- Trang đầu trả lời: nhà máy nào cần chú ý, nguồn nào có vấn đề, bước tiếp theo là gì. Kết nối mới theo luồng chọn brand/platform → thông tin được cấp → khám phá → xem dữ liệu.
- Trạng thái API, trạng thái thiết bị, độ mới và chất lượng mẫu đo là những thông tin khác nhau. Đọc thành công không đồng nghĩa dữ liệu mới hoặc control đã nghiệm thu.
- Nhãn form rõ ràng, chữ đi cùng biểu tượng/màu, focus bàn phím và layout nhỏ dùng chung. Chi tiết giao thức/evidence đặt trong phần chuyên sâu; chất lượng thực tế cần QA tiếp.
- Không đổi dữ liệu thiếu thành 0 hoặc cộng khác đơn vị/phạm vi/thời điểm. Không đặt SOC/V/Hz chung trục kW.
- Ghi nhận incident không xóa alarm trên inverter; lưu lịch nháp không gửi xuống thiết bị; review mapping không kích hoạt canonical profile.

## Ranh giới của thiết kế và hiện thực

Native TOU trên inverter khác scheduler của controller: slot, timezone/DST, enum, readback tùy model. Automation cần precedence/TTL/failsafe; bulk phải kiểm tra từng identity, không đánh giá Exact theo thương hiệu.

Firmware/network/grid-code/CT/BMS/generator/ATS và raw command cần contract cụ thể. Form khóa phải nói rõ lý do; có nút trong mockup chưa chứng minh transport đã xây. Physical discovery cần phạm vi và driver phù hợp.

Coordinate view chưa phải GIS basemap. Weather có provider khi có GPS; tiết kiệm, CO₂, uptime, health score hoặc vòng đời pin cần dữ liệu/phương pháp thực. Không dùng số mockup làm production data.

Commissioning có checklist thủ công và evidence references; electrical tests, evidence uploads, chữ ký, notification delivery và các phần khác vẫn còn thiếu. [Implementation status](implementation-status.md) và bảng phạm vi là căn cứ báo tiến độ.
