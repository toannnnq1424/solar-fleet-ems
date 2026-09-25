# Sidebar and subtab responsibilities

Updated 2026-09-25. This section mirrors the canonical navigation in [mockup coverage](mockup-coverage.md). Destination design is distinct from implementation status. See [workspace target specification](sidebar-workspace-specification.md) and the [documentation index](README.md).

## Kết luận cấu trúc sidebar: 15 mục, một nơi sở hữu mỗi chức năng

Hash hiện tại có dạng `#page/section/tab`. Label giao diện tách khỏi tên kỹ thuật. Một site được chọn là **phạm vi**, không tạo một bộ sidebar khác. `Nhà máy` quản lý tài sản/khách hàng; `Hệ thống` chỉ topology/SLD, không lặp site CRUD. Các subtab dưới đây là hợp đồng bố trí đích; cột trạng thái phân biệt phần đã nối và phần còn thiếu.

| Sidebar / route chuẩn | Phải hiển thị / subtab sở hữu | Liên kết chung và tình trạng |
|---|---|---|
| Tổng quan `#overview/main` | Fleet KPI, việc cần chú ý; khi chọn site: Overview, Data, Equipment, Control, Schedule/TOU, Alerts, Journal, Diagnostics, Reports, Network | Site tabs đã có; overview 11 khối mô tả phía dưới; chưa rich dashboard đủ ảnh |
| Nhà máy `#plants/main` | Portfolio list/card, customers, regions, onboarding, benchmarking | Site metadata sở hữu ở đây; benchmarking chỉ dữ liệu thật, không coi chart khung là engine PR |
| Hệ thống / SLD `#topology/main` | Quan hệ inverter–meter–battery–load–logger, ranh giới đo, sơ đồ và validation | Graph stored có; electrical SLD editor/validation chưa đủ |
| Bản đồ `#plants/map` | Filter vùng/hãng/state, cluster, site drawer, links overview/control/maintenance/report | Coordinate view hiện có; map nền/satellite chưa có |
| Thiết bị `#devices/main` | Inventory; device Detail, Realtime/Data, Control, Advanced/Native, Journal, Documents, Maintenance | Dùng cùng device identity/capability; native/docs/firmware phần lớn discovery/khung |
| Điều khiển `#operations/main/control` | Chọn site/device, giám sát, intent cơ bản, BMS/TOU/CT/export/generator/grid/native, preview/diff/confirm, command status | Không có đường write riêng theo route; firmware/raw không được giả là universal |
| Lịch / TOU `#operations/main/schedules` | Weekly editor, templates/copy, tariff reference, reserve, compile report, rollout | Schedule draft/compiler có; visual week editor/model translators còn thiếu |
| Điều phối EMS `#operations/main/rules` | Policies/rules, triggers/conditions/actions, simulation, constraints/conflicts, monitor/execution log, bulk rollout | Simulation/monitor/guarded bulk có; optimizer và autonomous hardware dispatch chưa có |
| Dữ liệu & kết nối `#reports/main` | Overview/quality, Sources, Cloud accounts, Local Agent, Collection, Mapping, Diagnostics, Sync log; telemetry/history | Cloud/agent đi tới màn sở hữu; commissioning ở cùng service; một hàng tab do Data workspace sở hữu, alias route cũ còn hoạt động; mapping chọn trường đã quan sát, đơn vị, chiều đo, mô phỏng/phiên bản/duyệt độc lập |
| Cảnh báo `#incidents/main` | Center list/detail, assign/triage, notes/timeline, playbook, SLA/escalation, linked jobs | Chỉ một incident service và history; phần external delivery chưa có |
| Báo cáo `#reports/analytics` | Period/scope, energy/performance/incident/customer, artifacts/export/scheduled delivery | Actual CSV/XLSX/HTML; PDF/email/financial models còn thiếu |
| Bảo trì `#incidents/health` | Health, Work orders, Plans/calendar, Firmware; execution/checklist/time/review/history | Independent review/workflow có; OTA thực và materials/contracts thiếu |
| Nhật ký `#operations/main/journal` | Command lifecycle, operations, sync, audit/security theo quyền | Common immutable history; large-history search/export và external audit anchoring thiếu |
| Người dùng `#settings/main/users` | Users, Roles/permissions, Site scope; links cloud accounts/security | Local RBAC năm vai trò, chưa MFA/SSO/tenancy. Chỉ admin tổ chức được quản trị |
| Cài đặt & Hãng `#settings/main/connections` | Vendor accounts, General/site, Tariff reference, Ownership, Notification policy, Source policy, Device linking, Automation links, Secret/API keys, Evidence | Không sao chép engine TOU/EMS/mapping. Chứng chỉ agent và thông báo chỉ khung nếu chưa transport |

Các routes tắt trong card phải giữ site scope và dẫn đến cùng chức năng sở hữu. Không thêm CSS riêng theo route; shared primitives và `static/app.css` sở hữu mọi layout/typography/semantic state. Account route tuân bố cục ảnh 21. VI/EN đã có cơ chế chung nhưng còn nhãn kỹ thuật/translation cần trau chuốt.
