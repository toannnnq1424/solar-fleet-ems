# Đối chiếu 26 mockup với mã nguồn

Cập nhật: 20/09/2026. Phạm vi: working tree hiện tại, gồm mã chưa commit. Đây là kiểm kê bằng cách đọc mã, **không phải biên bản QA hoặc nghiệm thu thiết bị thật**. Các phần vừa phát triển đang chờ đợt kiểm thử tổng hợp cuối theo yêu cầu của chủ dự án.

## Cách đọc

- **Đủ luồng mã**: có lưu trữ/API, kiểm tra quyền/đầu vào và thao tác UI nối với API cho chức năng được nêu. Chưa đồng nghĩa đã kiểm thử cuối hoặc chạy trên phần cứng.
- **Một phần**: có nền tảng nhưng còn thiếu bước quan trọng trong mockup; cột còn thiếu chỉ rõ bước đó.
- **Chỉ BE / chỉ FE / thiếu**: không tính catalog, nút khóa, form lưu nháp hoặc tài liệu thiết kế là tính năng vận hành hoàn chỉnh.
- **Chờ thiết bị**: phải đối chiếu đúng inverter, logger, firmware, tài khoản và dữ liệu/readback. Việc đăng nhập không tự hoàn thành các phần core còn thiếu.

Hiện **không có ảnh nào đạt đầy đủ mọi chức năng và nghiệm thu cuối**. Một số luồng quản lý nội bộ có đủ BE + FE; điều khiển đa hãng, bản đồ nền, dự báo, OTA, chứng chỉ và nhiều kênh thông báo còn thiếu. Không sử dụng số liệu minh họa trong ảnh làm dữ liệu sản phẩm.

## Đối chiếu từng ảnh

Số ảnh theo thứ tự 26 ảnh gốc. Ảnh `Screenshot 2026-09-13 192858.png` gửi sau trùng nội dung ảnh **21** và là chuẩn bố cục trang tài khoản hãng mới nhất.

| Ảnh | Mục đích / chức năng thể hiện | BE hiện có | FE hiện có | Kết luận và phần chưa bao phủ |
|---|---|---|---|---|
| 01 | Tổng quan fleet, danh sách, chi tiết, điều khiển nhanh, TOU, bản đồ, cảnh báo, báo cáo | Inventory, lịch nháp, sự cố, dữ liệu, command engine | Các workspace dùng chung | **Một phần**. Thiếu tổng hợp năng lượng có đầy đủ mapping; bản đồ nền; lịch vận hành thiết bị và control profile đa hãng |
| 02 | Trang nhà máy: flow PV/inverter/grid/battery/load/EPS, thiết bị, thời tiết, nhật ký, thao tác nhanh | Site energy, inventory, journal, profile/capability | Trang site, dữ liệu và điều khiển theo khả năng | **Một phần**. Flow chưa mô tả đủ topology/EPS; chưa thời tiết/dự báo; chưa control đã nghiệm thu |
| 03 | Chi tiết nhà máy, nguồn local/cloud, chart, vị trí, cấu hình nhanh | Source selection, telemetry, site profile | Chart/nguồn/site/detail | **Một phần**. Chưa fusion mọi view, bản đồ nền, flow thực theo chiều công suất và tất cả preset |
| 04 | Site overview, 6 KPI, flow, tổng năng lượng, quick control, kết nối | Canonical energy endpoint, thiết bị, integration state | Thẻ energy, thiết bị, form preview/confirm | **Một phần**. Chỉ hiện energy khi có nguồn đáng tin; chưa đủ lưới chart/KPI như ảnh, weather/EPS/quick preset |
| 05 | Danh sách nhà máy, lọc hãng/nguồn/khu vực/khách hàng, map, thống kê | Site CRUD/profile, customer records, discovery | Danh sách/tìm kiếm/lọc/phân trang, tọa độ | **Một phần**. Chưa đầy đủ kết hợp mọi bộ lọc và biểu đồ phân bố; nhập hàng loạt; nền bản đồ |
| 06 | Dữ liệu ngày/tháng/năm, chọn metric, nhiều chart, bảng, CSV/XLSX/PDF | Lịch sử có lọc trước giới hạn, CSV/XLSX, counter analytics | Bộ lọc, chart, bảng, export, print | **Một phần**. Chưa downsampling/rollup dài hạn, chart đa trục chuẩn, PDF riêng và toàn bộ biểu đồ so sánh |
| 07 | Inventory, bảng/thẻ, topology, thêm/gán/liên kết/auto-discover, firmware/reboot | Cloud discovery, manual asset, topology records | Inventory, chi tiết, thêm asset, topology | **Một phần**. Chưa gán/hợp nhất thiết bị vật lý nhiều transport bằng wizard, card view đầy đủ, quét bus, OTA/reboot đa hãng |
| 08 | Điều khiển mode/export/SOC/charge/EPS/CT/BMS/generator/grid/raw, readback | Intent catalog, schema constraints, command engine, registry acceptance theo device/account với expiry/revoke; Deye compiler giới hạn | Nhóm native dùng schema, giải thích acceptance, preview/confirm, nhật ký | **Một phần**. Registry đã có mã, chưa có shipping profile đã nghiệm thu. Catalog không phải lệnh hoạt động; thiếu compiler/field riêng model; code mới chưa chạy test |
| 09 | Lịch tuần, tariff, SOC theo giờ, ưu tiên tải, generator/backup, mô phỏng/triển khai | Version, timezone/DST/gap compiler, adapter translation contract, saved plan/digest/expiry, chuyển sang rollout có kiểm tra lại | Editor/copy/version, preview từng target và khoảng hở, chọn DST, chuẩn bị rollout | **Một phần**. Đủ mã luồng chuẩn bị có ràng buộc; thiếu native translators thực, dispatch tự động, optimizer, ưu tiên tải/generator; chưa chạy test |
| 10 | Alert dashboard, severity/trend, bảng lỗi, chẩn đoán, playbook | Correlation contract, dedup/order, recovery nhiều nguồn, SLA snapshot, versioned playbook, timeline append-only, daily trend API | Trung tâm lọc/list/detail, phân công/triage/ghi chú, SLA và phân nhóm, checklist hướng dẫn | **Một phần**. Backend trend chưa thành chart đầy đủ; chưa decoder alarm thực/cẩm nang theo model, evidence file và external notification; chưa chạy test mới |
| 11 | Nhật ký lệnh, before/after, queued/sent/ack/readback, export | Persistent journal, audit, command timeline, reconcile timeout | Bảng/chi tiết/trạng thái/reconcile | **Một phần**. Timeline audit hiện giới hạn truy vấn; chưa mọi bộ lọc và mẫu xuất đầy đủ; chờ order/readback thật |
| 12 | Báo cáo sản lượng, tiết kiệm/CO₂/uptime/cycles, report builder và email | CSV/XLSX, HTML in, counter deltas, thống kê phản hồi sự cố | Export, analytics, print report | **Một phần**. Chưa report jobs/archive/PDF riêng/email; chưa công thức savings/CO₂/cycles/uptime đã đối chiếu |
| 13 | Wizard hãng/loại/kết nối, khám phá, gán site, kiểm tra trước hoàn tất | Connector setup/discovery, manual assets | Form kết nối và đăng ký asset | **Một phần**. Chưa wizard 4 bước hoàn chỉnh, QR, rà bus; cần tách Bluesun/OEM khỏi transport |
| 14 | Nguồn dữ liệu, tài khoản, agent, ưu tiên, mapping, sync/latency/buffer | Source policy, ingress/outbox, mapping draft/simulation/independent review/version, collection policy, scoped WS invalidation | Source policy/agents, mapping editor và review, collection/sync/quality views | **Một phần**. Mapping editor đã viết; review draft không phải commissioning. Thiếu mapping hãng nghiệm thu, áp dụng mọi report, backfill, service/mTLS, latency end-to-end |
| 15 | Site config, TOU, backup, owner access, units/language, notifications | Site/tariff/notification records, user site scope | Form quản lý và VI/EN | **Một phần**. Lưu cấu hình không ghi thiết bị; chưa owner policy riêng theo site, đơn vị tùy chọn và email/Zalo/SMS/push |
| 16 | Cấu hình cơ bản/nâng cao/chuyên gia, native parameters, diff/readback | Profile registry exact identity, constraints/readback/evidence/reviewer, expiry/revoke; per-intent grants | 9 nhóm native, schema từ profile, giải thích mức tương thích và trạng thái khóa | **Một phần**. Có cơ chế profile và UI; chưa field/transport/readback nghiệm thu cho từng model; raw/grid không tự mở; chưa test/visual QA mới |
| 17 | Logger/local/network, Wi-Fi/Ethernet/4G, scan, certificate, firmware | Network draft, agent enrollment/ingress/outbox | Form network, agent token, status | **Một phần**. Chưa cấu hình network thật, Wi-Fi scan, quét RS485, ping/DNS thực, mTLS/cert và OTA |
| 18 | Cấu hình hàng loạt, kiểm tra từng site, dry-run, canary, triển khai, xác minh | Persistent rollout/digest/canary/cancel, profile resolver, schedule-source revalidation | Editor/preview/từng target, compiler explanations, chuẩn bị canary rollout | **Một phần**. Thiếu future scheduler và compiler hãng thực; chuẩn bị không gửi lệnh; source đổi hoặc profile thu hồi sẽ chặn; chưa chạy test mới |
| 19 | Users/roles/site scope/2FA/cloud/security audit | User CRUD/access/password/session revoke, grants/audit | Users/access/disable/reset password/audit | **Một phần**. Chưa MFA/SSO/role designer và security analytics; API quyền tồn tại không đồng nghĩa profile điều khiển mở |
| 20 | Commissioning 6 bước, chạy test, bằng chứng, chữ ký, biên bản | Manual checklist, readiness, attestation snapshot, report | Checklist/handover/in báo cáo | **Một phần**. Chưa auto electrical tests, upload tài liệu, chữ ký điện tử; attestation tên người không phải chữ ký số |
| 21 | Tài khoản hãng, kiểm tra quyền, certificates, API keys, secret health | Encrypted connectors, bounded connection checks, scoped read API keys cấp/thu hồi, trạng thái kho khóa | `accounts.js`: bảng trái/panel kiểm tra phải/3 thẻ đáy, account form/key dialog dùng style chung | **Một phần**. Bố cục tham chiếu đã viết, chưa visual QA xác nhận khớp ảnh. Có API keys; chưa certificate/mTLS, 5 transport còn thiếu, live grants/expiry đúng hãng |
| 22 | Bản đồ vùng, cluster, vệ tinh, lọc/list/detail, thao tác nhanh | Tọa độ site và scoped records | Sơ đồ tọa độ offline, chọn site/detail | **Một phần**. Sơ đồ tọa độ không phải GIS nền thực; chưa tiles/vệ tinh/cluster/region overlay/geocode |
| 23 | Health dashboard, maintenance jobs/plans, firmware compliance/queue | `maintenance.py`: plan/checklist/version, pinned evidence, time ledger, independent review/reopen, closing gates, immutable execution history, calendar/observation health | `maintenance-workspace.js`: health, jobs list/detail/checklist/time/history, review, calendar; kế hoạch định kỳ và firmware draft dùng chung | **Một phần**. Đủ mã luồng công việc nội bộ; BE/browser tests đã viết chưa chạy. Thiếu vật tư/hợp đồng, file upload, health scoring có phương pháp, firmware catalogue/OTA/compliance |
| 24 | Rule builder trigger/condition/action, hold/cooldown, dry-run, protected load | AND rules, evaluator, notify-only monitor, persisted runs | Multi-condition/action editor, dry-run, monitor | **Một phần**. Monitor chỉ tạo thông báo; chưa trigger lịch/event đầy đủ, precedence/arbitration/TTL/hysteresis và physical dispatch |
| 25 | Incident center, assignment/ack/close, timeline, work order, SLA/escalation | `incidents.py`/`incident_api.py`: correlation, dedup/out-of-order, ack riêng recovery, SLA snapshot/escalation, playbook version, linked jobs | `incident-center.js`: lọc/phân công/triage/notes/timeline/SLA/checklist, điều hướng bảo trì | **Một phần**. BE+FE luồng nội bộ đã viết; decoder hãng, model playbooks, external delivery và đầy đủ chart/root-cause còn thiếu. Test mới chưa chạy |
| 26 | Device realtime, energy flow, AC phases/DC strings/battery/latency, export | Native latest/history, source age, capability | Chi tiết/metric chart/tables/export | **Một phần**. Chưa canonical mapping theo model và biểu đồ nhóm đa trục/phases/strings; không có realtime 5 giây bảo đảm |

## Danh mục chức năng đã khử trùng lặp

BE = `src/solar_fleet/`; FE = `src/solar_fleet/static/`. Các tên file dưới đây là bằng chứng mã nguồn, không chỉ kế hoạch.

| ID | Chức năng duy nhất | BE | FE | Mức bao phủ / còn thiếu |
|---|---|---|---|---|
| UI01 | Shell/sidebar/topbar mọi route | Static serving `app.py` | `workspace.js`, `index.html`, `app.css` | Đủ shell chung; cần chỉnh thiết kế mới và kiểm tra responsive cuối |
| UI02 | Style/tokens/components toàn cục | — | `app.css`, helper `workspace.js` | Một stylesheet chung; quy tắc đã ghi trong AGENTS và UI contract; chưa visual QA cuối |
| UI03 | VI/EN và date/number locale | Validation codes | `i18n.js`, `workspace.js`, `workbench.js` | Một phần: có chuyển ngôn ngữ; nhiều enum/lỗi kỹ thuật cần bản dịch dễ hiểu |
| UI04 | Search, scope, keyboard/dialog/empty/error | Site isolation | Shared helper và dialog | Đủ nền tảng; chưa nghiệm thu usability/accessibility cuối |
| PL01 | Site add/edit/timezone/coordinates | `workspaces.py` SiteForm/routes | `workspace.js` siteForm | Đủ luồng mã |
| PL02 | Khách hàng/nhóm/contact | `management.py` Customer | `workbench.js` entity forms | Đủ CRUD; chưa CRM/import/bulk/customer drilldown |
| PL03 | GIS thực/cluster/satellite | Thiếu dịch vụ/provider | Chỉ sơ đồ tọa độ | Một phần; chưa GIS |
| DV01 | Cloud discovery + inventory/identity/bindings | `controller.py` discover | `workspace.js` devices/detail | Đủ đọc có contract cho 3 transport; chưa acceptance |
| DV02 | Manual asset registration | `management.py` /assets | `workbench.js` assetForm | Đủ luồng mã; trạng thái chưa biết cho đến có dữ liệu |
| DV03 | Topology edit/render | `management.py` Topology | `workbench.js` topology | Đủ lưu/vẽ quan hệ; chưa electrical validation |
| DV04 | Merge physical device / attach multiple paths | Binding model | Thiếu wizard | Một phần BE; chống serial trùng chưa thay thế quy trình merge |
| DV05 | QR / Wi-Fi / Modbus auto discovery | Thiếu | Thiếu | Chưa triển khai |
| CN01 | Deye native cloud read | `adapters/deye.py`, 39 contracts | Connect/config/alarm/native views | Có mã; chưa xác thực toàn bộ contract trên tài khoản thật |
| CN02 | Solis signed cloud read | `adapters/solis.py`, `cloud.py` | Connect/discovery/native | Có mã; chưa live acceptance, timestamp chưa có contract rõ |
| CN03 | SOLARMAN cloud read | `adapters/solarman.py` | Connect/discovery/native | Có mã; chưa live acceptance |
| CN04 | GoodWe/Sungrow/Huawei/Growatt/Eybond | `providers.py` research catalogue | Lý do chưa hỗ trợ | Thiếu transport chạy thật; không gọi là adapter hoàn chỉnh |
| CN05 | Bluesun theo model và platform | Catalogue/evidence BSM/SmartESS, BSE15KH3/Afore, BSE12KH3/Megarevo; BSE6 còn chưa xác định | Catalogue và lý do chưa hỗ trợ | Một phần; nguồn community không tự chứng minh control/readback; chưa profile nghiệm thu |
| CN06 | Account encryption/pause/resume | `security.py` Vault, `workspaces.py` | integrationForm | Đủ luồng mã |
| CN07 | Kiểm tra từng bước từng tài khoản | `accounts.py`: bounded account check, stage/status | `accounts.js`: panel check như ảnh 21 | Có luồng mã; quyền control giữ unknown nếu chưa có bằng chứng; chờ QA và live verification |
| CN08 | Local Agent enrollment/revoke | `management.py` /agents | `workbench.js` agents | Đủ luồng token theo site/device |
| CN09 | Agent ingress + durable outbox | `agent.py` | Hướng dẫn enrollment | Đủ luồng mã CLI→queue→inbox; chưa hardware collector/service installer |
| CN10 | Nguồn ưu tiên/staleness/disagreement | `telemetry.py`, `management.py` energy | Source policy/plant | Một phần; chưa áp dụng đồng nhất mọi report/evaluator |
| CN11 | Logger network write/OTA/mTLS | Chỉ network/firmware drafts | Form lưu nháp | Một phần; chưa thực thi hoặc chứng chỉ |
| DT01 | Native data/provenance/retention | `telemetry.py`, `storage.py`, `controller.py` | Device/history views | Đủ luồng mã; native UNKNOWN không thành canonical tự động |
| DT02 | Mapping canonical theo model | `data_workspace.py`: draft/simulation/review/version; code registry | `data-workspace.js`: editor/review/quality | Có luồng draft; chưa bộ mapping theo model đã nghiệm thu |
| DT03 | Counter energy + boundary/reset checks | `analytics.py` | `workbench.js` analytics | Đủ luồng mã có điều kiện; không tính khi thiếu/ambiguous |
| DT04 | Weather/forecast/irradiance | Thiếu | Thiếu | Chưa triển khai |
| DT05 | Savings/CO₂/cycles/uptime/health | Tariff metadata; kết quả chưa tính | Chưa giả số | Một phần; còn phương pháp và nguồn đầu vào |
| CT01 | Intent/capability discoverability | `catalog.py`, schemas | device/control view | Đủ catalogue; không phải toàn bộ physical controls |
| CT02 | Preview/diff/confirm/idempotency/lock | `control.py`, `capability_profiles.py` acceptance registry | schema-form/controlForm/native-device | Nền tảng mã + registry; profile expiry/revoke/ambiguous bị chặn; chưa shipping acceptance/test mới |
| CT03 | Vendor compiler + fresh readback | Deye subset; all shipped UNKNOWN | Form khóa theo capability | Một phần; chưa multi-vendor operational control |
| CT04 | Order timeline/quarantine/reconcile | `control.py`, `administration.py` | commandDetail/journal | Đủ luồng mã; cần real order acceptance; audit query hữu hạn |
| CT05 | Expert/grid/raw/CT/BMS/generator/ATS/EV | Grants + intent catalogue | Capability reason | Một phần; chưa đủ model-specific engineering UI/compiler |
| SC01 | Weekly schedule CRUD/copy/version | `workspaces.py`, `management.py` | scheduleForm/version | Đủ quản lý nháp |
| SC02 | Timezone timeline/DST validation | `runtime.py` | schedule timeline | Đủ mã timeline; không chạy lịch xuống thiết bị |
| SC03 | TOU dispatch/native slot compilation | `schedule_planning.py`: weekly compiler, gap/DST, saved translation, source hash/expiry, rollout handoff | `schedule-planner.js`: target selection/preview/reasons/gaps/handoff | Có luồng chuẩn bị; thiếu translators hãng và tự thực thi. Chưa chạy test |
| SC04 | Tariff version/slots | `management.py` Tariff | entity editor | Đủ metadata; chưa tariff billing/optimizer |
| EM01 | AND condition/action draft + dry-run | `rules.py`, `workspaces.py` | multi-rule editor | Đủ luồng mã; structured actions ngoài editor còn giới hạn |
| EM02 | Continuous hold/cooldown monitor | `runtime.py` | enable/disable/hold/cooldown | Đủ notify-only; chưa dispatch |
| EM03 | Optimizer/arbitration/protected load/failsafe | Thiếu | Thiếu | Chưa triển khai |
| BU01 | Persistent rollout/canary/remaining | `runtime.py` | rollout editor | Đủ nền tảng mã; không bỏ qua per-device controls |
| BU02 | Future rollout schedule/rollback | Thiếu scheduler/rollback | Cancel unsent | Một phần; đã gửi phải theo journal/reconcile |
| IN01 | Incident create/assign/ack/resolve/close | `incidents.py`, `incident_api.py`, legacy route delegates | `incident-center.js` | Có luồng mã, SLA/triage/notes/immutable history; chưa chạy test mới |
| IN02 | Vendor alarms→correlation/incidents | Adapter decode contract + correlation/dedup/order/recovery engine | Native alarms và incident source view | Engine đã viết; chưa shipping decoder hãng, không coi tất cả alarm đã tự chuẩn hóa |
| IN03 | Work order + incident linking + execution | `workspaces.py`, `maintenance.py`: checklist/time/review/reopen/closing gate | Incident shortcut + `maintenance-workspace.js` | Đủ mã luồng nội bộ; chưa chạy test, thiếu binary evidence/materials |
| IN04 | Recurring maintenance creation | `management.py`, `runtime.py` | maintenance plans | Đủ luồng mã |
| IN05 | In-app notification/escalation/read | `runtime.py`, `management.py` | inbox/policy | Đủ luồng mã; cần kiểm tra monitor stale gaps |
| IN06 | Email/SMS/Zalo/webhook/mobile push | Chỉ policy metadata | Config forms | Một phần; không có sender |
| IN07 | Fault taxonomy/playbooks/root-cause | Versioned playbook, incident snapshot, per-step evidence; basic categories | Editor VI/EN, checklist và phân nhóm nguyên nhân | Có mã hướng dẫn thủ công; thiếu cẩm nang theo model và chẩn đoán tự động |
| IN08 | SLA snapshots + escalation lifecycle | `incidents.py`: elapsed 24/7 targets/reopen/dedup escalations, `incident_api.py` policy/summary | SLA editor, incident deadlines, summary | Có mã; chưa calendar giờ làm việc, external delivery; chưa chạy test mới |
| IN09 | Maintenance time / review / service calendar | `maintenance.py`: time overlap/void, pinned document versions, independent reviewer/digest, calendar | Execution/time/history/review/calendar tabs | Có BE+FE+test code; chưa chạy. Kết quả ghi nhận không phải chứng nhận an toàn điện |
| CM01 | 6 manual commissioning checks | `workspaces.py` | checklist | Đủ luồng ghi nhận thủ công |
| CM02 | Readiness + handover attestation | `management.py` | handover/print | Đủ luồng mã; không ký số hoặc unlock profile |
| CM03 | Automated electrical acceptance | Thiếu | Thiếu | Chưa triển khai |
| CM04 | Documents metadata / binary attachments | `management.py` Document | Reference/hash form | Một phần; chưa upload/storage/download/signature |
| RP01 | Scoped CSV/XLSX telemetry export | `workspaces.py`, `analytics.py` | export buttons | Đủ luồng mã |
| RP02 | HTML printable site report | `management.py` | print/open link | Đủ HTML; chưa PDF generator/job/archive |
| RP03 | Monthly report builder/email/archive | Thiếu | Thiếu | Chưa triển khai |
| AD01 | Users/site scopes/grants/password/disable | `security.py`, `administration.py` | user/access forms | Đủ luồng mã |
| AD02 | Audit security/system/commands | `storage.py`, APIs | journal/activity | Đủ nội bộ; chưa external immutable audit |
| AD03 | MFA/SSO/custom-role designer | Thiếu | Thiếu | Chưa triển khai |
| AD04 | Third-party API keys + revocation | `accounts.py`: scoped read keys cấp/thu hồi | `accounts.js`: tạo/thu hồi, hiển thị key một lần | Có luồng mã; không cấp remote-control bằng read API key |
| AD05 | Local Agent certificates/mTLS | Thiếu | Thiếu | Chưa triển khai; enrollment bearer không phải certificate |

## Quy tắc giao diện bắt buộc từ 19/09/2026

Một **global stylesheet**, một **shared shell/sidebar**, một hệ **tokens + components** cho toàn bộ routes. Không tạo stylesheet riêng cho từng route. Bố cục bảng/panel/3-card theo ảnh 21 phải là composition của các component/layout chung, có thể dùng lại ở incident/detail/diagnostics. Chi tiết tại [global UI contract](ui-design-system.md).

## Phân biệt hoàn thiện mã và kiểm chứng

1. Sau mỗi đợt phát triển, cập nhật hàng tương ứng và dẫn bằng chứng mã. Không đổi “một phần” thành “đủ” chỉ vì đã có nút.
2. Ghi kết quả kiểm thử tổng hợp cuối tại [validation](validation.md). Bảng này không dùng số test của bản cũ để xác nhận mã mới.
3. Mỗi hãng/model có biên bản hardware acceptance riêng. Không có profile đã nghiệm thu thì mọi lệnh ghi vẫn bị khóa dù FE và engine đã tồn tại.
4. Đã mở rộng incident center, capability profiles, schedule compiler và maintenance execution; tiếp tục phát triển các khoảng thiếu thực ở bảng phạm vi dưới đây. Tests viết cùng code nhưng để chạy ở đợt tổng hợp sau khi hoàn tất phạm vi, theo yêu cầu người dùng. Không gộp phần còn thiếu thành “chỉ cần login”.

## Kết luận: sidebar, tab con và nội dung bắt buộc

Đây là **kiến trúc thông tin đích đã sắp xếp lại theo mục đích**, không phải tuyên bố tất cả route/tab đã được lập trình. Trạng thái thực của từng chức năng vẫn nằm trong hai bảng phía trên. Mỗi chức năng có một nơi quản lý chính; thẻ tóm tắt và shortcut ở nơi khác dẫn tới cùng route, cùng dữ liệu, cùng quyền.

### 1. Hai cấp tổng quan, một sidebar

- **Tổng quan toàn danh mục** trả lời: có bao nhiêu nhà máy, nơi nào cần chú ý, sản lượng/tiêu thụ được xác minh ra sao, công việc và kết nối nào cần xử lý. Khi chưa chọn nhà máy, không hiển thị sơ đồ điện của một nhà máy giả định.
- **Workspace một nhà máy** mở từ danh sách, bản đồ, tìm kiếm hoặc bộ chọn nhà máy trên topbar. Header giữ tên, trạng thái, địa chỉ, loại hệ, hãng/model, công suất, pin, múi giờ, nguồn và thời điểm cập nhật. Tab đầu là **Tổng quan** với đầy đủ yêu cầu bên dưới. Có breadcrumb về fleet.
- Sidebar không thay khi vào nhà máy hoặc thiết bị. Bộ lọc nhà máy và khoảng thời gian được giữ khi chuyển tab. Chỉ dùng từ **Hệ thống** để chỉ topology/mối liên hệ thiết bị của nhà máy; không tạo một danh sách “Hệ thống” trùng “Nhà máy”.
- Các chế độ cơ bản/nâng cao thay mức chi tiết trong cùng workspace. Chúng không tự tăng quyền hoặc mở khả năng thiết bị.

### 2. Sidebar chính được chốt theo nhóm công việc

Ba nhóm nhãn **Giám sát**, **Vận hành**, **Quản lý** chỉ giúp đọc sidebar; không tạo thêm route rỗng. Có 13 đích chính dưới đây. Trên mobile dùng cùng danh sách trong menu thu gọn.

| Mục sidebar | Phải thể hiện / tab con | Nơi quản lý chính và liên kết | Mockup |
|---|---|---|---|
| **Tổng quan** | Fleet KPI, chất lượng/độ mới dữ liệu, tình trạng nhà máy, sản lượng và tiêu thụ tổng hợp đúng phạm vi, việc cần xử lý, cảnh báo, công việc, nhật ký gần đây | Chọn nhà máy → workspace nhà máy; thẻ cảnh báo → incident; kết nối → dữ liệu & kết nối. Có bộ lọc fleet/nhóm/khu vực/hãng | 1–4, 22 |
| **Nhà máy** | Danh sách; khách hàng/nhóm; thêm nhà máy; chọn một nhà máy mở workspace có 10 tab | Hồ sơ vật lý, chủ sở hữu, vị trí thuộc nhà máy. Không thêm route “Hệ thống” đồng nghĩa. Map là cách xem cùng danh mục | 1–7, 13, 15, 20, 22 |
| **Bản đồ** | Danh sách + bản đồ + panel chi tiết; lọc vùng/hãng/trạng thái/loại hệ; cluster; nền/vệ tinh; toàn màn hình; legend; vị trí/nhà máy/cảnh báo | Cùng dataset và quyền của Nhà máy. Click pin mở panel rồi đi workspace/thiết bị/sự cố/bảo trì/báo cáo, không sao chép nghiệp vụ | 1, 5, 22 |
| **Thiết bị** | Tất cả; inverter; pin/BMS; logger/gateway; meter/CT; tải/EPS/UPS; generator/ATS/EV/phụ trợ. Bảng/thẻ; bộ lọc; identity/SN/FW; topology; thêm/gán/liên kết | Workspace thiết bị gồm Giám sát, Điều khiển từ xa, Cấu hình nâng cao, Nhật ký, Tài liệu, Bảo trì. Onboarding từ đây mở wizard chung | 2–4, 7, 13, 16–17, 26 |
| **Điều khiển** | Chọn site/thiết bị, giá trị hiện tại, quick presets, khả năng thực, basic/advanced/expert, diff, xác nhận, tiến trình/readback | Tái sử dụng **workspace thiết bị** và command engine. Không nhân bản 6 tab của thiết bị thành một bộ logic ghi khác. Lệnh có tác động phải có preview trước và trạng thái sau | 1–4, 8, 11, 16, 26 |
| **Lịch / TOU** | Lịch tuần; editor khung giờ; copy ngày/mẫu; timezone/DST; tariff reference; target SOC/power; phiên bản; mô phỏng; triển khai và kết quả | Là lịch điều khiển, khác biểu giá điện. Phải cho biết lịch chạy trên inverter hay controller; dẫn tới giá điện ở cấu hình nhà máy. Chưa có driver thì lưu nháp có nhãn rõ | 1, 9, 15, 18 |
| **Điều phối EMS** | Chính sách; trigger/AND-conditions/actions; ưu tiên tải; battery reserve/backup; hold/cooldown; điều kiện máy phát; mô phỏng; rollout nhiều nhà máy; các lần chạy | Một rule engine và rollout engine. Phân biệt notify-only, dry-run và thực thi. Bảng compatibility theo từng thiết bị, canary, cancel phần chưa gửi và xử lý kết quả chưa rõ | 9, 18, 24 |
| **Dữ liệu & kết nối** | Tổng quan chất lượng; dữ liệu đo/realtime/lịch sử; nguồn dữ liệu; tài khoản cloud; Local Agent; cấu hình thu thập; ánh xạ dữ liệu; chẩn đoán; nhật ký sync | Là nơi quản lý **kết nối kỹ thuật**. Tài khoản cloud mở trang dùng chung ảnh 21; quyền/khóa do quản trị quản lý. Không nhầm “ánh xạ dữ liệu” với bản đồ địa lý | 6, 13–14, 17, 21, 26 |
| **Cảnh báo** | Inbox/dashboard; severity/status/site/device/source; danh sách/detail; nguyên nhân có thể; playbook; người xử lý; ack/close; timeline/notes; SLA/escalation | Incident là hồ sơ xử lý, alarm là sự kiện nguồn. Liên kết tạo phiếu bảo trì/chẩn đoán/thiết bị, không coi ack là đã sửa lỗi máy | 1, 10, 25 |
| **Báo cáo** | Sản lượng/tiêu thụ/self-use/import-export/battery; ngày/tháng/tùy chọn; hiệu suất; sự cố; báo cáo khách hàng; tạo/xuất; lịch sử báo cáo | Dữ liệu đã chuẩn hóa/đủ thời gian, phương pháp và coverage hiển thị rõ. Savings/CO₂/uptime/cycles chỉ tính khi đủ inputs; PDF/XLSX/email là các trạng thái công việc riêng | 1, 6, 12 |
| **Bảo trì** | Sức khỏe hệ thống; công việc bảo trì; firmware; kế hoạch; commissioning/bàn giao | Jobs có người/độ ưu tiên/deadline/checklist/tài liệu; firmware có version/checksum/window/khả năng/queue; commissioning 6 bước dẫn tới cấu hình thiết bị và nhật ký liên quan | 17, 20, 23, 25 |
| **Nhật ký** | Điều khiển; hệ thống; sync; tự động hóa; quản trị/bảo mật theo quyền; tìm kiếm/lọc/export/timeline | Một truy vấn journal theo scope/category. Tab nhật ký trong site/device chỉ là view lọc sẵn, không bộ lưu trữ thứ hai. Luôn có actor/source/before/after/outcome/readback | 11, 14, 16–21, 24–26 |
| **Quản trị** | Người dùng & phân quyền; tài khoản hãng & thông tin truy cập; API keys/certificates; cấu hình tổ chức; mặc định ngôn ngữ/đơn vị; thông báo; bảo mật | Gom “Quản lý người dùng” và “Cài đặt” vào nhóm quản trị có tab rõ, tránh sidebar quá dài. **Cài đặt nhà máy** nằm trong workspace nhà máy; trang tài khoản hãng dùng chung với Dữ liệu & kết nối | 13–15, 19, 21 |

### 3. Mười tab trong workspace một nhà máy

Các ảnh gọi workspace này là “Tổng quan”, “Nhà máy” hoặc “Hệ thống”. Đích thống nhất là **Nhà máy → [Tên nhà máy]**. Truy cập từ Tổng quan vẫn mở đúng đích này.

| Tab trong nhà máy | Nội dung bắt buộc | Drill-down |
|---|---|---|
| **Tổng quan** | Tất cả 11 khối trong bảng bên dưới; không ép người ít kinh nghiệm mở thông số kỹ thuật để biết nhà máy đang làm gì | Mỗi khối có một liên kết chi tiết rõ ràng |
| **Dữ liệu** | Realtime/lịch sử; chọn ngày/tháng/năm/tổng; metric selectors; chart đúng đơn vị/trục; bảng timestamp/quality/source; import/export/PV/load/battery/SOC; export | Metric/series → dữ liệu thiết bị hoặc bộ lọc lịch sử |
| **Thiết bị** | Inventory theo loại; SN/model/FW/status/last seen/source; bảng/thẻ; topology; thêm/gán/liên kết | Thiết bị → 6-tab device workspace |
| **Điều khiển** | Preset và các thiết lập tương thích của nhà máy; chọn thiết bị đích; before/after; preview/confirm; trạng thái lệnh và readback | Mở remote/advanced của thiết bị; nhật ký lệnh |
| **Lịch / TOU** | Lịch tuần/site timezone; SOC/power/mode; tariff; version/copy/template; mô phỏng và deploy | EMS/rule hoặc command rollout liên quan |
| **Cảnh báo** | Cảnh báo của site; mức độ/thiết bị/trạng thái/người xử lý; detail/playbook/timeline | Incident center có sẵn scope site |
| **Nhật ký** | Lệnh, hệ thống, sync, EMS đã lọc site; source/actor/before/after/result/readback | Chi tiết lệnh hoặc lần chạy tương ứng |
| **Chẩn đoán** | Sức khỏe kết nối/chất lượng dữ liệu; commissioning; cấu hình thiết bị; nhật ký kiểm tra; readiness/bàn giao | Tab con commissioning → thiết bị → nhật ký giữ nguyên scope; không tự chạy thử điện nguy hiểm |
| **Báo cáo** | Bộ tạo báo cáo theo site; năng lượng, hiệu suất/sự cố, khách hàng; xuất/lưu lịch sử | Trang báo cáo giữ nguyên date/site/filter |
| **Logger / Local Agent / Mạng** | Identity/logger/agent/network; online/last seen/RSSI/latency; topology truyền thông; cấu hình; buffer; certificate; sync; discovery và firmware đúng khả năng | Chi tiết logger, nguồn dữ liệu, chẩn đoán, firmware |

**Cài đặt nhà máy** là nút/header action mở các tab: Thông tin chung; Biểu giá điện; Quyền sở hữu & truy cập; Cảnh báo/thông báo; Nguồn dữ liệu; Liên kết thiết bị mới; Tự động hóa. Có thể dùng drawer hoặc subroute nhưng luôn thuộc site đã chọn. Nút nguồn dữ liệu/onboarding/tự động hóa dẫn tới các editor chung có scope, không tạo bản sao cấu hình.

### 4. Khối bắt buộc trong Nhà máy → Tổng quan

| Khối / field | Dữ liệu và hành vi cần có | Đi tới chi tiết |
|---|---|---|
| **Sơ đồ năng lượng realtime** | PV; inverter; lưới nhập/xuất; pin sạc/xả + SOC; tải; EPS/UPS/generator nếu topology có. Mũi tên theo chiều thật, W/kW và số cập nhật cùng mốc; nguồn + độ mới. Chọn chế độ hiển thị, phóng toàn màn hình, legend; ẩn thiết bị không có, hiện “—” khi chưa đo được | Click node → thiết bị/metric; “Xem dữ liệu” → Dữ liệu |
| **Điều khiển nhanh** | Tự dùng, zero-export, grid-charge, reserve SOC, EPS và lịch khi thực sự hỗ trợ. Thông số đọc hiện tại, giá trị đề xuất, mô tả dễ hiểu; cấu hình nhanh/chi tiết; áp dụng qua preview/confirm; outcome/readback. Nút khóa phải giải thích model/quyền/độ mới còn thiếu | Cấu hình chi tiết → Điều khiển từ xa / Nâng cao; kết quả → Nhật ký |
| **Trạng thái nhà máy** | Online/offline/stale/warning rõ nghĩa; PV/load/grid/battery power, SOC, sản lượng/tiêu thụ; hôm nay/ngày/tháng/năm/tổng; biểu đồ số liệu chi tiết cho kỳ được chọn. Không cộng số stale hoặc native chưa map vào tổng mà không báo coverage | Chỉ số → Dữ liệu với metric/date đã chọn |
| **Sản lượng & tiêu thụ** | Hôm nay/tháng/năm; PV/load/import/export/battery theo khoảng thời gian; legend bật/tắt; tooltip đơn vị/time/source; chart không ghép SOC/V/Hz vào trục kW | Mở chart lớn → Dữ liệu hoặc Báo cáo |
| **Tỷ lệ tự dùng** | PV sản xuất, PV tự dùng, bán lưới, mua lưới, tải tiêu thụ, tỷ lệ và kỳ; công thức phù hợp topology/pin; không đánh đồng self-consumption và self-sufficiency | Báo cáo năng lượng giải thích phương pháp/coverage |
| **Thời tiết & dự báo** | Ưu tiên nguồn thời tiết thực của vendor/site nếu có field/contract. Fallback provider công khai cấu hình theo tọa độ site; ghi nguồn, thời điểm cập nhật, múi giờ, cache và attribution. Hiện thời tiết, nhiệt độ, hourly forecast; mưa/gió/bức xạ/sunrise/sunset nếu provider hỗ trợ. Không mặc định mọi inverter có cảm biến thời tiết; không lấy số ảnh | Chi tiết dự báo/nguồn; forecast PV là mô hình riêng, không suy ra trực tiếp từ biểu tượng nắng |
| **Thiết bị trong hệ thống** | Danh sách ngắn theo loại, model/status/power/SOC/FW/last seen phù hợp; tổng số + xem tất cả; cảnh báo nằm cạnh thiết bị bị ảnh hưởng | Device workspace hoặc inventory đã lọc site |
| **Kết nối & nguồn dữ liệu** | Local direct, Local Agent, cloud/logger/meter theo cấu hình; online/offline/auth-expired/stale, lần nhận/lần sync, nguồn chính/dự phòng và chênh lệch. Tách API còn kết nối khỏi telemetry còn mới | Dữ liệu & kết nối / Logger-Mạng |
| **Cảnh báo gần đây** | Severity, mô tả dễ hiểu, thiết bị, xảy ra lúc nào, trạng thái/người phụ trách; xem tất cả, ưu tiên cảnh báo mở | Incident detail có scope site |
| **Nhật ký điều khiển gần đây** | Intent/mô tả, actor, lúc gửi, before/after, kết quả và xác minh; cảnh báo pending/timeout. Không báo thành công chỉ vì HTTP 200 | Command timeline/readback |
| **Vị trí & thông tin** | Địa chỉ, tọa độ/bản đồ nếu được cấu hình, timezone, customer/owner, loại hệ, installed kWp, capacity battery, ngày tạo/vận hành, liên hệ đúng quyền | Site profile/edit, Map, Customer; không gửi vị trí ra dịch vụ chưa được cấu hình |

### 5. Sáu tab thiết bị và tám nhóm dữ liệu/kết nối

**Workspace thiết bị**, dùng chung từ Thiết bị/Điều khiển/nhà máy:

| Tab | Nội dung |
|---|---|
| Giám sát | Identity + trạng thái/freshness/source, energy flow theo loại thiết bị, realtime/historical AC phases/DC strings/SOC/temp/latency đúng đơn vị, bảng tham số và export |
| Điều khiển từ xa | Presets/control fields được profile cho phép; current/read/preview/apply; readback và recent actions |
| Cấu hình nâng cao | CT/meter, battery/BMS, export/feed-in, grid-charge, generator/smart-load/grid/firmware/raw có quyền và evidence riêng; mode basic/advanced/expert; diff chung |
| Nhật ký | Lệnh, config changes, alarms/sync/security liên quan thiết bị, actor/source/time/outcome |
| Tài liệu | Hướng dẫn, protocol/reference, firmware release notes, hồ sơ commissioning/handover/ảnh lắp đặt theo quyền; version/checksum |
| Bảo trì | Health evidence, công việc/lịch, chẩn đoán, firmware compatibility/upgrade request/progress và lịch sử |

**Dữ liệu & kết nối**:

| Tab/nhóm | Nội dung và nơi liên kết |
|---|---|
| Tổng quan | Nguồn đang hoạt động/cần xác thực, devices linked, last sync, độ mới, latency, missing points, source disagreement |
| Dữ liệu đo | Realtime/history/table/charts và export, khác trang quản lý kết nối |
| Nguồn dữ liệu | Bindings thiết bị→nguồn, ưu tiên đọc/control ownership, cloud/local coexistence, fallback |
| Tài khoản cloud | Mở trang tài khoản hãng ảnh 21 dùng chung; scope site giới hạn quyền xem, chỉ admin quản lý credential |
| Local Agent | Enrollment, device/site grants, heartbeat/version, backlog/buffer/sync, revoke, certificate khi được triển khai |
| Cấu hình thu thập | Polling/quota/backoff/timezone/retention/buffer/backfill; không cho cấu hình vượt khả năng hãng/logger |
| Ánh xạ dữ liệu | Native key/register → canonical metric, unit/scale/sign, phase/direction/source, model applicability/evidence/version/acceptance |
| Chẩn đoán | Connectivity/data freshness/disagreement; commissioning, cấu hình thiết bị và nhật ký kiểm tra là subroutes dùng chung với nhà máy/Bảo trì |
| Nhật ký sync | Attempts, success/failure/auth/quota, sample coverage, last successful period/backfill và retry; không chứa secrets/raw customer payload |

### 6. Điều kiện hoàn thành của kiến trúc này

Không cần nhân bản đủ số màn hình như ảnh. Cần bao phủ đủ **mục đích + dữ liệu + thao tác + kết quả**. Mỗi khối tổng quan có link đến chi tiết đúng scope; mỗi editor lưu qua BE, phản hồi lỗi rõ và đọc lại kết quả; mỗi tính năng chưa triển khai có trạng thái minh bạch. FE-only biểu diễn số giả, BE chưa có thao tác UI, hay form lưu nháp cho chức năng đòi thực thi đều phải giữ trạng thái chưa hoàn thiện trong phần đối chiếu. Đây là tiêu chí dùng cho các đợt code và QA tiếp theo.


## Đợt core + UI ngày 20/09/2026

Cập nhật các dòng kiểm kê phía trên; không nâng toàn bộ màn lên “hoàn thiện”.

| Ảnh | BE bổ sung | FE bổ sung | Kết luận / còn thiếu |
|---|---|---|---|
| 6, 14, 26 | `streams.py`: event bền vững, scope/cookie/origin, cursor/revocation; `data_workspace.py`: chất lượng | `live.js`: reconnect, cập nhật tổng quan/danh mục khi không chỉnh form; tổng quan dữ liệu | Đủ invalidation/thống kê pilot. Chưa mọi chart realtime hoặc dữ liệu phần cứng chuẩn |
| 14 | Collection policy revision/version, interval/cap được controller dùng | Form chu kỳ/cap, trạng thái sync/cursor | Đủ polling config. Chưa cloud backfill và service agent |
| 14 | Mapping draft gắn identity/binding, unit/direction, simulation, review độc lập/version; profile nghiệm thu trong adapter | Editor kênh, nguồn, đơn vị, chiều; thử quy đổi, versions/review | Đủ draft/review. Chưa mapping thật; review không mở EMS |
| 8, 16 | `integration.py`, `adapters/plugins.py`, compiler/feature gates | `native-device.js`: 9 nhóm, tài liệu và quyền theo adapter | Khung native dùng chung; chưa field schema đã nghiệm thu theo model |
| 13, 21 | Registration theo plugin; account/check, key cấp/revoke/API đọc scope | Bảng trái, kiểm tra phải, 3 thẻ access bên dưới; form metadata | Đủ quản trị pilot; chưa chứng chỉ/adapter còn thiếu |
| 18 | Core không mặc định compiler/trạng thái Deye; test ecosystem thứ 10 | Native/config/alarms theo adapter | Có điểm mở rộng; không đồng nghĩa 8 cloud đã có transport |

Trong **Dữ liệu & kết nối**: Tổng quan dữ liệu → Dữ liệu đo → Nguồn dữ liệu → Cloud → Agent → Thu thập → Mapping → Chẩn đoán/commissioning → Sync. Chẩn đoán dùng chung commissioning. Báo cáo/tariff còn shortcut cần tinh chỉnh theo IA phía trên.

Ảnh 21 được bám bố cục nhưng không điền token expiry, chứng chỉ, quyền hay account giả. Toàn bộ 26 ảnh vẫn còn các hạng mục thiếu; không suy ra phần trăm hoàn thành từ LOC hoặc số route.
## Phạm vi dự toán → mã hiện có → phần chưa xây → điều kiện hoàn thành

**Chưa hoàn thành sản phẩm được yêu cầu.** Có route, CRUD, nút hoặc bộ khung không đồng nghĩa hoàn thiện luồng nghiệp vụ. Báo cáo này phân biệt code đã viết, code đã kiểm thử, UI đã QA và thiết bị đã nghiệm thu. Việc cung cấp tài khoản hãng chỉ giải quyết một phần xác minh adapter; không thay thế các module còn thiếu.

Snapshot lịch sử trước đợt mở rộng này: backend Python **6.344 dòng**, frontend JavaScript **7.130 dòng**, CSS/HTML **1.476 dòng**, tests/fixture **2.959 dòng**, scripts **34 dòng**; code ứng dụng **14.950 dòng**. Không dùng snapshot này làm số hiện tại. **Số hiện tại nằm trong bảng đo tự động ở cuối tài liệu**, kèm manifest từng file và thời điểm đo.

Khoảng dự toán 400–630 nghìn dòng do chủ dự án đưa ra là ngân sách giả định cho sản phẩm trưởng thành: core BE 130–200k, vendor layer 65–115k, agent 20–35k, shared/core FE 130–190k và native FE 35–68k; test/infra là phần cộng thêm. Chưa có WBS và acceptance đủ chi tiết để xác nhận các khoảng này; không chuyển chúng thành phần trăm hoàn thành. Code hiện tại dùng FastAPI/Python, JavaScript ES modules và SQLite một controller, khác giả định React/TypeScript và hạ tầng fleet trưởng thành. Khác công nghệ có ảnh hưởng LOC nhưng **chênh lệch chủ yếu vẫn là phạm vi chưa xây**, không thể giải thích bằng tái sử dụng code. Không thêm code lặp để đạt LOC; nghiệm thu bằng workflow, lỗi, quyền, lưu trữ, vận hành và khả năng thiết bị.

| Phạm vi dự toán | Mã hiện có (BE / FE) | Phần chưa xây | Điều kiện hoàn thành |
|---|---|---|---|
| Core domain / organization / DB | `domain.py`, `storage.py`, `management.py`, `workspaces.py`; site/customer/device/topology editors | Tenant lifecycle/boundary, migration framework, indexed fleet queries, backup/restore flows, complete archive/import | Object scope ở mọi API; migration/restore có bằng chứng; UI create/edit/archive/conflict xuyên suốt |
| Authentication / RBAC / secrets | `security.py`, `administration.py`, `accounts.py`; local session/CSRF, scopes/grants/vault/read API keys, user/account UI | SSO/MFA, organization roles, credential rotation/recovery UI, tenant administration | Thu hồi session/key/quyền có hiệu lực; test site/tenant boundary và recovery; không lộ secret |
| Fleet & site overview (1–5) | `management.py` energy endpoint; `workspace.js`/`workbench.js` inventory, site detail, chart/control shortcuts | Đủ 11 khối overview, topology/EPS flow, weather/forecast, period comparisons, mọi drilldown | Mỗi khối có nguồn/age/coverage hoặc trạng thái thiếu; chọn scope/period không trộn dữ liệu |
| Device management (7,13,26) | Discovery, identity, assets/bindings; device inventory/detail/native groups | Guided onboarding/QR/discovery bus, physical-device merge, đầy đủ card/filter/lifecycle, AC/DC/phase charts | Một thiết bị vật lý không bị nhân đôi qua transport; attach/move/archive có kiểm tra và UI |
| Telemetry + realtime (6,14,26) | `telemetry.py`, `controller.py`, `streams.py`; provenance/quality/source priority, scoped cursor WS; `live.js` | Time-series store, durable backfill/aggregation, distributed collectors, chart streaming, end-to-end latency | Không cộng trùng nguồn; thiếu không thành 0; reconnect/restart/gap không mất hoặc lặp dữ liệu |
| History & analytics (6,12) | `analytics.py` counter windows/reset/coverage; chart/table/export | Multi-axis/rollup dài hạn, energy attribution, capacity-normalized performance, tariff/cycle/uptime methods | Chart/table/export cùng đơn vị/timezone; tính toán có nguồn và coverage, không bịa KPI |
| Universal control (8,11,16) | `control.py` read/diff/confirm/queue/readback/timeout; `capability_profiles.py` exact identity/acceptance/expiry/revoke | Production durability/scale validation, accepted device contracts, expanded fault/restart cases | Fresh pre-read và verify; unknown outcome không retry bừa; quyền/profile thay đổi chặn thực thi |
| Vendor-native UI + capabilities (8,16) | `integration.py`, profile registry; `native-device.js` 9 nhóm và schema/evidence reasons | Field descriptors/compiler/readback theo model/logger/FW, advanced grid/BMS/CT/generator workflows | Intent adapter dịch đúng semantics, per-field range/unit/permission, UI riêng khả năng thực; không đổi logo rồi gọi là hỗ trợ |
| Vendor ecosystem layer | Deye/Solis/SOLARMAN có read clients, Deye write candidates guarded; plugin registry; `accounts.js` | GoodWe/Sungrow/Huawei/Growatt/Eybond chưa có transport; Bluesun specific profiles chưa nghiệm thu; native controls/alarms/history tất cả hãng chưa đủ | Auth→discovery→telemetry→alarms→control→readback theo profile; sources/license/contract tests; live acceptance riêng |
| TOU / schedule compilation (9) | `schedule_planning.py`: gap/DST/UTC/translator contract/digest/expiry/handoff; `schedule-planner.js` | Shipping translators, native schedule acceptance, unattended scheduler, calendar exception policies | Tuần/timezone/DST đúng; lịch hoặc capability đổi làm plan cũ mất hiệu lực; từng target có kết quả |
| EMS / automation (24) | `rules.py`, `runtime.py`: AND/dry-run/hold/cooldown notify-only; rule UI | Arbitration/hysteresis/override TTL, load protection, optimizer/forecast dispatch, local failsafe | Quyết định có giải thích; mất meter/cloud không điều khiển bằng dữ liệu cũ; xung đột được xử lý |
| Bulk policy/control (18) | Persistent rollout/compatibility/canary/remaining/cancel; compiled schedule source gate; rollout UI | Future schedule, scalable worker lifecycle, model translation coverage | Idempotent và restart-safe; canary verified mới mở phần còn lại; báo từng thiết bị; không giả rollback |
| Sources / cloud / mapping (13,14,21) | `data_workspace.py`, `accounts.py`: collection policy, mapping draft/review/version, health/check; data/account UI | Backfill jobs, all-source report consistency, shipping mapping acceptance, complete wizard | Onboard→discover→map→quality→reconnect với scope/quota; review draft không tự cho phép control |
| Local agent / network (17) | `agent.py` ingress/outbox/upload; `local_solarman.py` optional read collector; enrollment/network drafts | mTLS/cert/service/update lifecycle, auto discovery, authenticated diagnostics, network change/recovery | Install/enroll/revoke/reconnect/backfill; outage không mất data; network/firmware chỉ thao tác qua contract |
| Incident center (10,25) | `incident_models.py`, `incidents.py`, `incident_api.py`; `incident-center.js`: dedup/order/correlation, SLA/triage/notes/playbook/work linking | Actual vendor alarm decoders, model playbooks, external delivery, shift calendar SLA, complete trend/root-cause charts | Ack khác recovery; source không tự clear khi im lặng; immutable history, independent playbook versions, scope và SLA consistent |
| Commissioning (20) | Manual checks/readiness/handover snapshot; `workbench.js` forms/report | Test orchestration, scoped binary evidence, calibrated readings, signatures/retest/invalidation | Không coi khai báo thủ công là đo kiểm điện; fail/warning chặn bàn giao theo policy; truy vết người/phép đo/profile |
| Maintenance execution (23) | `maintenance.py`: versioned plan/checklist/evidence/time/review/gates/history/health/calendar; `maintenance-workspace.js` | Parts/materials/procurement, service contracts, binary evidence, electrical health model, advanced resource scheduling | Create→plan→execute→independent review→close/reopen; changed/revoked evidence/quyền chặn đóng; không tự cấp chứng nhận điện |
| Firmware lifecycle (7,17,23) | `management.py` firmware request draft + editor; reported installed version | Signed manifest/model compatibility, transfer/install/verify/recovery drivers, queue/progress/compliance | Check package/provenance/identity/window; thiết bị xác nhận version/readback; recovery rõ theo hãng |
| Reports / distribution (6,12) | Scoped CSV/XLSX/printable shared-style HTML + counter coverage | Saved report runs/templates/PDF/archive/scheduled distribution, validated savings/CO₂ formulas | Có nguồn/formula/period/coverage, reproduce/download/history; external send có cấu hình và quyền |
| Map / regional fleet (5,22) | Scoped coordinate plot/list/detail | Basemap/satellite/cluster, region overlays, combined filtering, geocoding policy | List/map cùng scope/filter; tọa độ/cluster chính xác; shortcuts đúng plant/device/incident |
| Settings / audit / logs (11,15,19) | Metadata/tariff/notification/network drafts, users/session/grants, audit hash chain, journal/detail | Full tab completion, owner policies, saved filters/export, immutable external audit checkpoints | Cấu hình có revision và quyền; drilldown dùng cùng workflow; config draft khác thiết bị đã áp dụng |
| Shared UI/design system | `app.css` duy nhất, shared shell/sidebar, field/table/dialog/list-detail, VI/EN | All states/screens, translation errors/enums, accessibility/keyboard, responsive/visual matching, component modularization | Bao quát mục đích 26 ảnh; mọi thao tác có kết quả/error; một style/sidebar; QA thực sau implementation |
| Test / simulator / infra | BE synthetic tests; new profile/incident/schedule/maintenance cases; `ui_tests/` isolated browser fixtures; inventory script | Remaining business/e2e/fault/load/restore/migration tests, vendor simulators, packaging/deployment/observability | Viết test đồng thời; chạy test/build/QA tổng hợp sau đủ phạm vi; báo rõ pass/fail/not-run, không gọi fixture là live acceptance |

**Trình tự theo yêu cầu:** phát triển BE + FE + test code trên toàn phạm vi → đối chiếu lại các mục còn thiếu → chạy test và sửa lỗi → build/đóng gói → QA chức năng/visual → nghiệm thu thiết bị được cấp quyền. Không coi một đợt kiểm thử xanh hoặc vài route mới là bàn giao sản phẩm trưởng thành.

### Bằng chứng của đợt code mới (chưa chạy kiểm thử)

| Luồng | BE | FE | Test code đã viết | Trạng thái |
|---|---|---|---|---|
| Acceptance profiles | `capability_profiles.py`, controller/integration | `native-device.js` | `test_capability_profiles.py` | Chưa chạy; không có shipping profile được nghiệm thu |
| Incident center / SLA / correlation | `incident_models.py`, `incidents.py`, `incident_api.py` | `incident-center.js` | `test_incident_center.py`, `ui_tests/test_operations_screens.py` | Chưa chạy; decoder hãng và external delivery còn thiếu |
| Lịch / compile / chuẩn bị rollout | `schedule_planning.py`, runtime gates | `schedule-planner.js` | `test_schedule_planning.py` | Chưa chạy; translator tổng hợp trong test không phải hỗ trợ hãng thật |
| Maintenance execution | `maintenance.py`, record completion guard | `maintenance-workspace.js`, shared shell integration | `test_maintenance_execution.py`, `ui_tests/test_maintenance_screens.py` | Chưa chạy; chưa visual QA, firmware vẫn chỉ request |

Các test mới mô tả tình huống trùng/sai thứ tự/recovery nhiều nguồn; profile hết hạn/thu hồi/không rõ identity; lịch thay đổi/gap/DST; checklist thiếu/thất bại, thời gian trùng, tự duyệt, người duyệt mất quyền, tài liệu đổi phiên bản/archived, plan đổi và mở lại công việc. Viết test không được ghi thành test đã pass.

### Kết luận điều hướng bổ sung cho bảo trì và cảnh báo

Sidebar **Cảnh báo** mở `#incidents/main`, gồm trung tâm, hồ sơ cũ, playbook và SLA. Sidebar **Bảo trì** mở `#incidents/health`, gồm **Sức khỏe hệ thống → Công việc bảo trì → Firmware → Kế hoạch định kỳ → Lịch dịch vụ**. Route dùng chung page shell vì cùng miền vận hành, nhưng active sidebar và bộ tab phân biệt rõ hai mục đích. Phiếu từ cảnh báo mở `#incidents/jobs/<id>`; từ phiếu trở lại đúng incident/device. Các shortcut không tạo bản sao editor hoặc bỏ qua completion gate. Chỉ health quan sát có dữ liệu được hiển thị; electrical score, firmware currency chưa biết không được thay bằng số minh họa.


<!-- actual-code-inventory:start -->
## Số dòng thực tế có thể đo lại

Đo lúc **2026-09-20T04:16:39.467258+00:00** trên working tree, gồm code chưa commit.

| Nhóm | Số file | Dòng vật lý | Dòng không trống |
|---|---:|---:|---:|
| Backend Python | 38 | 7,959 | 7,100 |
| Frontend JavaScript | 13 | 7,902 | 7,866 |
| Frontend CSS / HTML | 2 | 1,500 | 1,499 |
| Test BE / simulator / fixture | 17 | 3,706 | 3,140 |
| Test UI / browser fixture | 3 | 221 | 193 |
| Scripts tự viết | 2 | 118 | 106 |
| **Tổng FE (JS + CSS/HTML)** | **15** | **9,402** | **9,365** |
| **Tổng code ứng dụng BE + FE** | **53** | **17,361** | **16,465** |
| **Tổng test / simulator / fixture** | **20** | **3,927** | **3,333** |
| **Tổng code ứng dụng + test + scripts** | **75** | **21,406** | **19,904** |

Phương pháp: đếm dòng vật lý (gồm comment và dòng trống), đồng thời công bố số dòng không trống. Không phải semantic SLOC. Không tính dependency, môi trường ảo, lock, generated, assets/ảnh, JSON hợp đồng, tài liệu, build output hoặc cache. Nhóm simulator/fixture không được tính vào production. Không cộng các dòng tổng lần nữa.

Đo lại bằng `python scripts/measure_code.py --update-doc`; lệnh chỉ đọc source và cập nhật báo cáo, không chạy test, build, QA hoặc gọi thiết bị.

Danh sách từng file và số dòng nằm trong [code-inventory.json](evidence/code-inventory.json). LOC phản ánh kích thước mã, không chứng minh workflow đúng, hoàn thiện UI hoặc nghiệm thu phần cứng.
<!-- actual-code-inventory:end -->
