# Quy mô dự toán và khoảng cách sản phẩm

Cập nhật 25/09/2026. Báo cáo chi tiết và số dòng có thể đo lại được duy trì tại [đối chiếu 26 mockup](mockup-coverage.md), phần **Phạm vi dự toán → mã hiện có → phần chưa xây → điều kiện hoàn thành**. Manifest từng file nằm trong [code-inventory.json](evidence/code-inventory.json). Tài liệu này không giữ một bảng LOC thứ hai dễ lỗi thời. Xem [mục lục tài liệu](README.md) và [kết quả kiểm thử theo ngày](validation.md).

## Vì sao số dòng thực tế thấp hơn dự toán?

Phần lớn chênh lệch là chức năng và độ sâu vận hành chưa được xây. Mã hiện tại vẫn là nền tảng đang phát triển, không phải sản phẩm trưởng thành đã hoàn tất. Có API, form hoặc catalog chưa đồng nghĩa đáp ứng đầy đủ luồng thực tế, sự cố, scale, vận hành và phần cứng.

Dự toán của chủ dự án khoảng 400–630k dòng production giả định core lớn, nhiều adapter, agent, shared frontend và vendor-native UI. Đây là giả định lập kế hoạch, chưa phải dự toán đã được xác nhận bằng WBS và acceptance. Hiện frontend dùng JavaScript ES modules, backend FastAPI và SQLite một controller; khác giả định React/TypeScript và hạ tầng đa tenant quy mô lớn. Sự khác biệt này có ảnh hưởng LOC nhưng không đủ để giải thích khoảng cách phạm vi.

Các con số 217 tests, số file/dòng ước chừng và câu “pilot đã hoàn thành” trong bản trước không có kết quả thực thi tương ứng được dẫn chứng. Chúng đã được bỏ, không dùng làm bằng chứng tiến độ hoặc nghiệm thu. Số dòng hiện tại phải lấy từ phép đo trong file đối chiếu; trạng thái test phải lấy từ lần chạy thực, không từ số hàm test hoặc tài liệu mô tả.

## Khoảng thiếu chính

- **Tích hợp hãng:** đã có tám read paths, gồm GoodWe Classic SEMS, Sungrow, Huawei, Growatt và Eybond; còn thiếu độ sâu history/alarm ingestion, các biến thể region/family, canonical mapping và native control/readback. Bluesun vẫn phải xác định OEM/platform/model/logger. Xem [contract hiện tại](multivendor-contracts.md); transport đã viết không đồng nghĩa hỗ trợ toàn hệ sinh thái.
- **Điều khiển/native:** có engine và exact acceptance registry; còn thiếu schema/translation/readback đã kiểm chứng theo model. Đăng nhập hãng không tự hoàn thiện adapter hoặc mở quyền ghi.
- **EMS/TOU:** có draft, compiler contract, timezone/DST/gap checks, rollout preparation và notify-only monitor; còn thiếu native translators, arbitration/hysteresis, optimizer, unattended dispatch và failsafe được nghiệm thu.
- **Vận hành production:** còn thiếu tenant lifecycle, migrations/restore, production time-series/backfill, service/mTLS/update lifecycle của agent và các bài kiểm tra scale/recovery.
- **UI/O&M:** incident/maintenance, overview có giới hạn, weather provider và mapping editor đã có BE/FE/test; vẫn thiếu dashboard/chart/GIS đầy đủ, forecast đưa vào EMS, binary evidence, commissioning orchestration, materials, firmware execution, report jobs/PDF/distribution và final visual/usability QA đủ 26 ảnh.

## Cách đánh giá tiếp theo

Đối chiếu từng chức năng bằng bốn câu hỏi: mã hiện ở đâu; FE nối BE đến bước nào; phần nào chưa xây; điều kiện nào mới cho phép đánh dấu hoàn tất. Viết test cùng implementation, chạy tổng hợp cuối đợt và kiểm tra lại phần bị ảnh hưởng sau khi sửa. Đợt 25/09 đã có kết quả tại [validation](mapping-validation-2026-09-25.md); không diễn đạt các ca đã chạy là còn hoãn. Chỉ ghi live acceptance khi có bằng chứng đúng thiết bị, firmware, logger và tài khoản.

Không dùng LOC hoặc số route làm phần trăm hoàn thành, không thêm code lặp để đạt chỉ tiêu, và không coi tất cả phần còn thiếu là “chờ login”.
