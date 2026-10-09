# Tài liệu Solar Fleet EMS — Toàn diện Kiến trúc & Hiện trạng Kỹ thuật

[README dự án](../README.md) · [Trạng thái code](implementation-status.md) · [Bao phủ 26 mockup và LOC](mockup-coverage.md) · [Kiểm thử](validation.md) · [Quy trình nghiệm thu 6 bài test](hardware-acceptance.md) · [Phân tích LOC](loc-estimation-and-product-gap-analysis.md)

Cập nhật **01/10/2026**. Mục lục này phản ánh toàn diện hiện trạng mã nguồn thực tế sau đợt nâng cấp tầng Vendor-Native chuyên sâu, thuật toán EMS tối ưu mô hình pin LFP, Local Daemon tự phục hồi và giao diện công nghiệp Cyber-Energy không emoji.

Ba nguyên tắc kỹ thuật bất di bất dịch của dự án:
1. **Zero Data Seed trong Logic Nghiệp vụ:** API nghiệp vụ chỉ xử lý dữ liệu đo đạc thực tế; nếu thiếu dữ liệu, trả về HTTP 422 hoặc ký hiệu trung thực `—` / `null`. Tuyệt đối không dùng fixture trong production code.
2. **Zero Emoji trong Giao diện:** Sử dụng 100% biểu tượng đồ họa vector SVG chuyên nghiệp, đồng bộ với bảng mã màu quang năng Cyber-Energy trong `src/solar_fleet/static/app.css`.
3. **Hardware Safety Interlock:** Toàn bộ lệnh điều khiển từ xa bị khóa cứng (HTTP 409 Locked). Chỉ mở khóa sau khi hoàn tất 6 bài kiểm tra điện lực thực địa theo chuẩn quốc tế IEC 62446-1 / IEC 62109 và được cấp chứng chỉ nghiệm thu `COMMISSIONED_VERIFIED`.

## Sản phẩm và tiến độ hiện tại

**09/10/2026 — hiện trạng ưu tiên:** [Đánh giá tiến độ và các khoảng thiếu](project-assessment-2026-10-09.md),
[kiểm tra cuối 1.894 BE/107 UI](evidence/energy-flow-ui-2026-10-09.md),
[manifest 12 ảnh tham chiếu riêng](evidence/ui-reference-manifest-2026-10-09.md).
GoodWe đã đăng nhập/đọc một phần qua SolarOne; chưa full live acceptance. UI vẫn chưa đạt
nghiệm thu người dùng, interface/history/control còn việc, DE/AI mới kế hoạch. Người dùng
yêu cầu commit/push rồi dừng chờ lệnh; đây không phải bản phát hành production.

[QA portal GoodWe chỉ đọc — 07/10/2026](evidence/goodwe-portal-qa-2026-10-07.md): đã quan sát phiên SEMS+ do người dùng đăng nhập, chưa nghiệm thu connector SolarOne; ghi rõ sửa lỗi online cố định, hướng dẫn UI và các hợp đồng còn thiếu.

Cập nhật kế hoạch **07/10/2026**: [backlog tính năng hãng — Phần II](vendor-feature-backlog-2026-10-05.md#interface-plan) là nguồn duy nhất cho kế hoạch chuẩn hóa interface theo từng hàm, 34 intent, phân loại native/chuyển đổi/dẫn xuất/đặc thù/không hỗ trợ và các đợt UI → QA đọc → refactor → QA hồi quy. Đây là kế hoạch, chưa là implementation hoặc nghiệm thu.

Đối chiếu mới **05/10/2026**: [58 hạng mục phát triển từ tính năng các hãng](vendor-feature-backlog-2026-10-05.md) và [audit lớp interface từ code](vendor-interface-audit-2026-10-05.md). Có registry/controller chung nhưng chưa hợp nhất toàn bộ history/alarm/native helpers; chưa production-ready. Các mô tả tổng quan tích cực ở đầu mục lục không thay thế kết luận có phạm vi/bằng chứng này.

Chuẩn bị kết nối hãng: [Hướng dẫn xin quyền API theo từng nền tảng](vendor-api-access-guide-vi.md) (04/10/2026), gồm Deye, Solis, SOLARMAN, Sungrow, GoodWe/SEMS+, Huawei, Growatt, Eybond/Bluesun. Phân biệt khóa ứng dụng và quyền chủ nhà máy; có mẫu thư và giới hạn connector hiện tại. Không phải tất cả đều cần App ID/App Secret.

**Khi yêu cầu “tiếp tục”:** đọc [checkpoint và runbook vendor backlog](vendor-feature-backlog-2026-10-05.md#resume-checkpoint), lưu bàn giao hội thoại trước rồi mới RSM-00; [lộ trình sửa chữa](remediation-roadmap.md) giữ chi tiết R01–R12, không có hàng đợi cạnh tranh. Các mô tả cũ bên dưới là lịch sử, không thay bằng chứng mới.

| Tài liệu | Nội dung sở hữu |
|---|---|
| [Implementation status](implementation-status.md) | Tóm tắt BE/FE đã nối, bảng trạng thái các phân hệ và giới hạn kỹ thuật |
| [Đối chiếu 26 mockup](mockup-coverage.md) | 26 màn hình, trách nhiệm sidebar/subtab, bảng dự toán → code → thiếu → điều kiện hoàn thành; bảng LOC duy nhất |
| [Code inventory](evidence/code-inventory.json) | Số dòng theo từng file; tạo bằng [measure_code.py](../scripts/measure_code.py) |
| [Dự toán và khoảng thiếu](loc-estimation-and-product-gap-analysis.md) | Phân tích quy mô 206k LOC kỹ thuật, sự tinh gọn của Register Engine so với boilerplate legacy |
| [Hardware acceptance & Commissioning](hardware-acceptance.md) | 6 bài test điện lực chuẩn IEC 62446-1, thủ tục nghiệm thu và điều kiện mở khóa quyền ghi |
| [Bản 0.2](release-0.2.md) | Tóm tắt các thay đổi hiện có, không phải thông báo đã triển khai production |


## Tiếp tục công việc sau gián đoạn

Đọc [checkpoint hiện tại](vendor-feature-backlog-2026-10-05.md#resume-checkpoint) và
[runbook từng bước](vendor-feature-backlog-2026-10-05.md#execution-runbook) trước khi
tiếp tục UI, QA hãng hoặc interface. [Kế hoạch Data Engineering / Applied AI](vendor-feature-backlog-2026-10-05.md#data-ai-plan)
bao gồm lịch sử receipt/correction, capacity/retention và Solar Text-to-SQL chỉ đọc;
đây là phạm vi dự kiến, chưa phải tính năng hoàn thành.

## UI, kiến trúc và điều kiện triển khai

| Tài liệu | Phạm vi |
|---|---|
| [Sidebar và subtab chuẩn](sidebar-subtabs-architecture.md) | 15 mục điều hướng, route sở hữu, liên kết giữa các chức năng |
| [Workspace specification](sidebar-workspace-specification.md) | Thiết kế đích: tab con, 11 khối tổng quan; chưa phải xác nhận tất cả đã xây |
| [Product workspaces](product-workspaces.md) | Nguyên tắc nhóm chức năng, site scope và luồng dùng cho người ít kinh nghiệm |
| [Global UI contract](ui-design-system.md) | Một shell/sidebar, shared primitives và một stylesheet |
| [Core extension contract](core-extension-contract.md) | Adapter/plugin, observation, compiler, mapping và realtime |
| [Hardware acceptance](hardware-acceptance.md) | Bằng chứng và phép thử cần có trước khi nghiệm thu profile/điều khiển |
| [Quy trình repository](../AGENTS.md) | Phát triển, nghiên cứu nguồn công khai, viết test và cập nhật phạm vi |

## Tích hợp hãng và bằng chứng

Bắt đầu ở [hợp đồng đa hãng hiện tại](multivendor-contracts.md). Đây là tám đường đọc có độ sâu khác nhau, cộng profile thương hiệu Bluesun; không phải chín hãng đã hỗ trợ đầy đủ.

| Tài liệu | Cách đọc |
|---|---|
| [Adapter audit 23/09](vendor-adapter-audit-2026-09-23.md) | Các sửa sai protocol/auth/field; Eybond sau đó được bổ sung ở tài liệu dưới |
| [Eybond / SmartESS](eybond-read-integration.md) | DessMonitor/ShineMonitor, session signing, inventory/native data, phần chưa xây |
| [Bluesun](bluesun-integration.md) | Tách brand/model/OEM/logger/platform; cloud routing và optional local collector |
| [Source audit](vendor-source-audit.md) | Nguồn theo ngày, applicability và các kết luận đã thu hồi |
| [Rà soát 30 dự án cũ](legacy-project-audit.md) | Quyết định từng dự án, license, nguồn ghim, phần đã port và phần chưa xây |
| [Model / Home Assistant](model-library-and-home-assistant.md) | Collector TCP/V5, sensor bridge, forecast baseline và energy flow chung |
| [Source registry](evidence/source-registry.json) | 65 ID nguồn tại checkpoint 08/10, gồm record đã thu hồi; đồng bộ với [registry đóng gói](../src/solar_fleet/data/source-registry.json) |
| [Compatibility matrix](vendor-compatibility-matrix.md) | Baseline nghiên cứu 10 phạm vi; không phải danh sách adapter đã nghiệm thu |
| [Vendor matrix JSON](evidence/vendor-matrix.json) | Dữ liệu nghiên cứu baseline, không phải runtime support registry |
| [Universal control mapping](universal-control-mapping.md) | Candidate Deye và khoảng semantic chưa xác minh |
| [Intent catalogue](evidence/intents.json) | 34 ý định điều khiển; có tên intent không đồng nghĩa có compiler/hardware support |
| [Research questions](vendor-research-questions.md) | Checklist nghiên cứu baseline và câu hỏi exact model/account còn mở |
| [Deye account observation](deye-account-observation.md) | Quan sát UI được cho phép, đã loại dữ liệu nhận diện; không phải OpenAPI acceptance |
| [Third-party notices](../THIRD_PARTY_NOTICES.md) | Phiên bản/commit, license và phạm vi dùng nguồn mở |

## Kiểm thử và QA đã ghi nhận

Mới ngày 07/10: [UI chuyên sâu EMS, mạng, biểu đồ và lớp bản đồ](evidence/ui-deep-workspaces-2026-10-07.md), tiếp nối [UI xem/so sánh số đo](evidence/ui-observation-inspector-2026-10-07.md). Bằng chứng kiểm thử tách khỏi pixel acceptance và QA tài khoản hãng.

[Validation index](validation.md) là điểm vào kết quả thực thi. [Browser contract](browser-test-contract.md) mô tả cách chạy và isolation.

- 27/09 — Legacy reuse và energy flow: file `legacy-validation-2026-09-27.md` được tham chiếu trước đây nhưng chưa có trong checkout; không dùng mục này như evidence đã kiểm chứng. Xem các evidence hiện có bên dưới và checkpoint hiện tại.
- [25/09 — Mapping và navigation](mapping-validation-2026-09-25.md): snapshot trước, 450 BE; 13 browser trước sửa UI, 8 ca rerun gồm một ca mới; build và QA có giới hạn.
- [24/09 — Eybond](eybond-validation-2026-09-24.md): contract/workflow và package của snapshot trước đó.
- [23/09 — Adapter/workspace audit](audit-validation-2026-09-23.md): kết quả snapshot theo ngày.
- [13/09 — Baseline 0.1](validation.md#historical-validation-010): giữ số liệu lịch sử, không dùng làm kết quả bản hiện tại.

Log và screenshot QA dưới `work/` là artifact local bị gitignore; checkout mới không có các file này. Không cộng số test của các lần chạy trùng nhau. Local pass, CI pass và hardware acceptance là ba loại bằng chứng riêng.

## Nghiên cứu và quyết định kiến trúc ban đầu

[Báo cáo nghiên cứu A–N](research-architecture-report.md) được lập trước code ngày 13/09. Các ADR dưới đây là quyết định baseline, không phải xác nhận mọi hệ con đã triển khai:

- [ADR-001 — Local-first architecture](adr/ADR-001.md)
- [ADR-002 — Vendor adapter architecture](adr/ADR-002.md)
- [ADR-003 — Universal policy model](adr/ADR-003.md)
- [ADR-004 — Telemetry normalization](adr/ADR-004.md)
- [ADR-005 — Command verification](adr/ADR-005.md)
- [ADR-006 — Credential security](adr/ADR-006.md)
- [ADR-007 — Site Agent architecture](adr/ADR-007.md)
- [ADR-008 — Time-series storage](adr/ADR-008.md)
- [ADR-009 — RBAC](adr/ADR-009.md)
- [ADR-010 — Vendor-native escape hatch](adr/ADR-010.md)

Khi sửa một chức năng, cập nhật tài liệu sở hữu nội dung và kiểm tra các liên kết từ README đến tài liệu đó cùng các tài liệu dẫn tiếp. Giữ số liệu snapshot theo ngày; không viết lại kết quả cũ thành kết quả của code mới.

## Kiểm tra tài liệu trước commit — 25/09/2026

Đã duyệt đệ quy từ README gốc qua 39 file Markdown, kiểm tra 249 liên kết nội bộ gồm đường dẫn, chữ hoa/thường và heading anchor: không có đích thiếu hoặc tài liệu Markdown trong `docs/` không thể đi tới. 68 URL ngoài repository chỉ được lập danh mục, không được truy cập lại trong đợt cập nhật tài liệu này; giữ ngày kiểm chứng tại từng source record. Không chạy lại toàn bộ test/build cho phần chỉnh tài liệu.
