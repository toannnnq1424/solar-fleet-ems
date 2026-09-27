# Đối chiếu 26 mockup và phạm vi sản phẩm

Cập nhật **27/09/2026**, trên snapshot mã được rà soát trước commit. Báo cáo này thay thế các nhận định “hoàn chỉnh luồng mã” trước đó: nhiều nhận định dựa trên số route, nút khóa và dữ liệu dựng sẵn, chưa chứng minh workflow hoạt động. Kết quả hiện tại là **pilot một controller**, không phải nền tảng O&M/EMS trưởng thành và chưa nghiệm thu thiết bị khách hàng. Xem [README dự án](../README.md), [mục lục tài liệu](README.md) và [validation theo ngày](validation.md).

## Kết luận sau đọc mã và kiểm tra

- Có BE + FE hoạt động cho quản lý dữ liệu nội bộ, tài khoản, một số đường đọc đa hãng, lập lịch nháp/biên dịch, xử lý sự cố và bảo trì. Các phép đo, báo cáo và điều khiển cần profile, quyền và dữ liệu phù hợp.
- Không có ảnh nào đã được chấp nhận đầy đủ toàn bộ chức năng, hành vi phần cứng và độ khớp UI. Chín ecosystem trong phạm vi không tương đương chín integration hoàn chỉnh.
- Đã sửa đường báo cáo/tổng quan đọc dữ liệu lưu thật; không dựng đường cong, SOC, uptime, sức khỏe, tiền tiết kiệm, CO₂ hay kết quả nghiệm thu. Dữ liệu không đủ được trả `null`/UNKNOWN, không đổi thành 0 hoặc thành công.
- Đã bỏ các compiler ghi phỏng đoán ngoài Deye. Đây là thu hồi tuyên bố hỗ trợ sai, không phải hoàn thành phần integration còn thiếu. Deye cũng chưa có hồ sơ phần cứng khách hàng được nghiệm thu trong đợt này.
- Test fixture, simulator và screenshot QA chỉ nằm trong thư mục kiểm thử/work; không là bằng chứng kết nối hãng hay thiết bị thật. Test qua được không thay nghiệm thu tại công trình.

Quy ước: **BE+FE một phần** = có luồng nối API nhưng thiếu chức năng trong ảnh; **BE riêng** = engine/API chưa nối đầy đủ vào màn hình; **khung** = catalog/form/read-only/khóa, chưa có hành vi vận hành. “Đạt test cục bộ” chỉ áp dụng đúng ca đã chạy.

## Tái sử dụng before_project — 27/09/2026

[Audit 30 dự án](legacy-project-audit.md) ghi rõ inventory khác với đọc sâu toàn bộ code; [hướng dẫn](model-library-and-home-assistant.md) và [validation](legacy-validation-2026-09-27.md) mô tả luồng đã chạy.

| Phạm vi dự toán / ảnh | Mã hiện có sau đợt này | Phần chưa xây | Điều kiện hoàn thành |
|---|---|---|---|
| Model-aware device/native — 07, 13, 16, 26 | BE: importer, catalog 41 profile, 913 decoder trong 3.145 field, plan/validate/decode. FE: tìm/chọn field, source/digest, config/download | 2.232 field bị chặn; dynamic MPPT/pack/lookup/sentinel/derived; model-native write/readback | Đối chiếu từng field/variant, fixtures và exact hardware; không nghiệm thu chỉ vì decode được |
| Local Agent/home energy — 14, 17 | BE: TCP/V5 collector, HA sensor bridge, cùng outbox→inbox→native/mapping; FE chuẩn bị/validate config agent/site | Service/RTU/discovery/reconnect policy/mTLS/managed update; activation mapping còn thiếu | Pilot collection dài hạn, timestamp/unit/source đúng, replay/revoke/recovery và commissioning |
| EMS — 24 | BE hourly EWMA adapt từ SEM; FE baseline 24h hoặc lý do cold-start, không phát lệnh | EMHASS/OpenEMS optimizer, forecast dispatch, EV/load/generator arbitration, offline control | Forecast đánh giá trên holdout + constraints, command engine và acceptance phần cứng |
| Tổng quan/thiết bị — 02–04, 26 | BE quality/freshness/source-pair gating; FE cùng sơ đồ điện có motion, bảng/fullscreen/pause/reduced-motion, route chi tiết | Topology điện được nghiệm thu, nguồn cấp từng tải, chart hoàn chỉnh, mọi responsive state | So với meter/topology thật; QA các chiều và thiếu/cũ/conflict; usability đủ 26 ảnh |
| UI chung — tất cả | Sửa hai khối CSS thiếu dấu đóng; giữ một app.css/sidebar; bỏ số mẫu giờ chạy/SOH/chu kỳ/bảo hành còn sót | Design cleanup, full 26-screen accessibility/visual acceptance | Keyboard/error/loading/mobile và toàn bộ mockup states được quan sát |
| Core Physics & EMS Engine (Đợt 2) — 24, 08, 16 | BE: `load_predictor.py` (5 mô hình dự báo tải), `tariff_catalogue.py` (catalogue biểu giá đa quốc gia, spot feed, carbon tracker, bill calculator), `thermal_load_manager.py` (bơm nhiệt Carnot COP, bồn nước nóng DHW, mô hình 2R2C tòa nhà, SG-Ready 4 trạng thái, deferrable load scheduler), `phase_balancer.py` (thành phần đối xứng Fortescue, VUF/CUF IEC 61000-4-30, dispatch bất đối xứng 3 pha, zero-export PID, rolling peak demand shaver), `predbat_planner.py` (mô phỏng tiến 24-48h, hurdle rate khấu hao pin, arbitrage biểu giá động, lịch inverter), `genset_controller.py` (state machine máy phát diesel/gas, mô hình tiêu thụ nhiên liệu, chống wet stacking, black-start), `vendor_device_translator.py` (chuyển đổi lệnh EMS neutral sang Modbus FC06/FC16 cho GoodWe, Sungrow, Deye, Huawei, Solis, Growatt), `phase_d_api.py` (REST endpoints). | Tích hợp giao diện trực quan hóa unbalance 3 pha, thermal buffer view và timeline predbat | Thử nghiệm phần cứng thực tế, xác nhận đồng hồ đo công tơ 3 pha và máy phát vật lý |
| Grid Code, Industrial Meters, EV Fleet & Market (Đợt 3) — 24, 02, 14, 08 | BE: `grid_code_regulator.py` (Volt-Watt P(V), Volt-Var Q(V), Freq-Watt P(f), anti-islanding NA003), `smart_meter_driver.py` (driver 6 dòng công tơ 3 pha Eastron SDM630, Chint DTSU666, Carlo Gavazzi EM24, Janitza UMG96, Schneider iEM3000, ABB B23), `ev_fleet_coordinator.py` (Dynamic Load Management DLM, chuyển mạch 1p3p tự động, ngắt pin xe 80% SOC), `market_trader.py` (đấu thầu thị trường điện bán buôn DAM/IDM, phản ứng điều tần FCR sơ cấp). | Widget điều khiển trạm sạc đa cổng, giao diện giám sát 4 góc phần tư công tơ và bidding market | Thử nghiệm kết nối công tơ Modbus thực tế và trạm sạc OCPP |
| Tích hợp sâu Core Engine vào 14 Tab Sidebar (Đợt 4) — 27/09/2026 | BE: Bổ sung endpoints máy phát `/api/genset/evaluate-dispatch`, `/api/genset/black-start-sequence`, mô phỏng nhiệt 2R2C `/api/thermal/building-simulation`, tra cứu 30 hãng Modbus `/api/vendor-translator/supported-brands`. FE: Tích hợp đầy đủ vào 14 tab sidebar: Tab 1 Tổng quan (Grid code & VUF), Tab 3 SLD (phân định 4 ranh giới điện), Tab 6 Điều khiển (biên dịch Modbus FC06/FC16 30 hãng & máy phát Black-Start), Tab 7 Lịch (Predbat 24h & hurdle rate khấu hao), Tab 8 EMS (Quy chuẩn Volt-Watt/Var/Freq/NA003, Fortescue cân bằng pha, SG-Ready nhiệt & EV DLM 1p3p), Tab 9 Dữ liệu (6 công tơ 3 pha & 4 góc phần tư), Tab 11 Báo cáo (Thị trường bán buôn & FCR điều tần), Tab 12 Bảo trì (Chẩn đoán suy giảm cell pin SOH/ΔV). | Mọi chức năng đã nối trực tiếp vào giao diện 14 tab sidebar và kiểm tra cú pháp JS | Nghiệm thu thực tế trên phần cứng hiện trường |

**Sắp xếp sidebar:** Model inspector thuộc Thiết bị; link trong Tổng quan mở cùng module. Config HA/local thuộc Dữ liệu / Local Agent và dẫn tới Mapping, không tạo menu HA riêng. Baseline thuộc Điều phối EMS. Site overview và device monitoring dùng chung energy-flow component. Không nhân bản flow, policy hoặc credential UI theo nguồn dữ liệu.

## Bổ sung Eybond/SmartESS — 24/09/2026

| Ảnh / nhóm | Mã BE mới hoặc sửa | Mã FE và liên kết | Chưa hoàn thành |
|---|---|---|---|
| 13, 21 / Accounts, Bluesun onboarding | DessMonitor/ShineMonitor auth/session, vault, bounded plant→collector→device discovery, native latest; brand tách platform | Bluesun→SmartESS form VI/EN, nền tảng/company key, username trong account table; cùng sidebar/app.css | Live account acceptance, mọi model/OEM, complete onboarding/QR |
| 14 / Sources, collection, sync | Chu kỳ tối thiểu 300 s tại backend/controller; source CONNECTED/STALE/AUTH_REQUIRED; khám phá lại khi restart/check làm mất route | Collection editor cùng giới hạn 300 s, trạng thái đồng bộ lấy đúng field, kỳ polling theo nguồn thật | Source-time contract, model mappings, failover rộng, inventory lớn vượt call budget |
| 07, 26 / Device readings | Giữ title/string value/unit; stable native keys; không đặt timestamp nhận thành timestamp đo | Detail & native readings từ inventory; filter theo brand/platform; bỏ 38°C/0 kW giả và phân biệt Unknown | Phase/MPPT/latency charts, canonical profile/physical acceptance |
| 08, 16, 18 / Control | Không thêm compiler hoặc quyền ghi suy đoán từ đọc cloud thành công | Cùng capability/native groups và lý do chưa hỗ trợ | Native schemas, model controls, order/readback và hardware trial |

Đây là phạm vi code mới có thể kiểm tra, không thay thế các gap trong 26 hàng phía dưới. [Chi tiết contract](eybond-read-integration.md), [kết quả kiểm thử đợt này](eybond-validation-2026-09-24.md).

## Bổ sung Mapping workspace — 25/09/2026

| Phạm vi dự toán / ảnh | Mã hiện có | Phần chưa xây | Điều kiện hoàn thành |
|---|---|---|---|
| Sources/integrations; ảnh 14, liên quan 06/13/17/26 | `data_workspace.py`: context chọn device/binding/agent theo scope, giữ native key/unit/value/time/quality, không trả credentials; kiểm tra dimension/sign; draft/version/digest, mô phỏng không ghi canonical, independent review. `mapping-workspace.js`: một editor VI/EN dùng shared primitives/app.css; create/edit/evidence/simulate/history/review nối API thật | Canonical profiles theo model, trình nghiệm thu/đưa profile vào sử dụng, lifecycle/deployment của profile, đối chiếu native metadata mọi hãng | Hợp đồng source-time/unit/sign theo đúng OEM/model/FW, reviewer độc lập + nghiệm thu vật lý và hồi quy downstream KPI/report/EMS, invalidation khi nguồn/profile đổi |
| Liên kết tài khoản/thiết bị → ánh xạ → dữ liệu; ảnh 14/21 | Context chỉ liệt kê kết nối còn hiệu lực. Duyệt và mô phỏng kiểm tra lại identity, site binding, tài khoản enabled hoặc agent/device membership. Sửa draft sau review tạo phiên bản mới không giữ trạng thái đã duyệt | Tự động migration profile khi đổi firmware; ảnh hưởng trên fleet và báo cáo commissioning | Không dùng bản cũ nếu identity/source khác, lịch sử review truy vết được, không nâng UNVERIFIED thành GOOD chỉ vì bấm duyệt |
| Test/QA đợt này | Test BE nguồn quá hạn/không hợp lệ, đơn vị đổi, duplicate source, nonfinite, revoke account/binding/agent, revision race. Browser create→edit→simulate→history→review→Viewer, VI/EN và dùng một stylesheet | Tài khoản/model thật, load/soak, accessibility và usability toàn 26 ảnh | Kết quả thực thi và lỗi/rerun phải ghi tại [mapping-validation-2026-09-25.md](mapping-validation-2026-09-25.md), không suy hoàn thành từ test được viết |

Luồng editor đã qua 450 test BE trong toàn suite và 13 test browser trong toàn suite trước sửa navigation. QA phát hiện hai hàng tab Data trùng nhau, đã gộp lại và chạy hồi quy navigation riêng; xem kết quả cuối ở báo cáo validation. Phần này không tự kích hoạt profile, không đổi telemetry/KPI/control và không chứng nhận tương thích hãng.

## Ma trận 26 ảnh

Số thứ tự theo 26 ảnh gốc. Ảnh gửi sau `Screenshot 2026-09-13 192858.png` là chuẩn bố cục cập nhật của **ảnh 21**. Các ảnh tổng quan lặp được quy về cùng trang nhà máy; không nhân bản sidebar hoặc command engine.

| Ảnh | Chức năng bắt buộc từ ảnh | BE hiện có và bằng chứng mã | FE hiện có | Thiếu / điều kiện hoàn thành |
|---|---|---|---|---|
| 01 | Fleet, list, site, nhanh, lịch, map, alert, report | `workspaces.py`, `operational_views.py`, management/control/report APIs | Các workspace chung và link chi tiết | **BE+FE một phần**; chưa đầy đủ KPI/fleet energy, basemap, preset đa hãng, dashboard rich như ảnh |
| 02 | Site flow PV/inverter/grid/battery/load/EPS, nhanh, status, weather, equipment, log | Overview có nguồn/scope/null; counter theo kỳ; weather Open-Meteo khi có GPS | 11 khối, flow component dùng chung site/device, bảng/toàn màn hình/motion/reduced-motion, route chi tiết | **Một phần**; đã có motion theo chiều công suất và freshness; chưa topology điện/source-to-load được nghiệm thu, dashboard đa biểu đồ chưa đủ, quick preset chưa triển khai theo model |
| 03 | Site chart, ưu tiên local/cloud, vị trí, trạng thái, cấu hình | Telemetry quality/source, profile, inventory, command engine | Site tabs/data/nguồn/control | **Một phần**; không suy luận flow từ cloud fields chưa xác minh; chưa hợp nhất topology và tất cả KPI |
| 04 | Site 6 KPI, flow, biểu đồ, tổng năng lượng, kết nối | Counter delta và trạng thái nguồn; EPS/lifetime chưa đủ bằng chứng | Khối KPI, thiết bị, nguồn; unknown hiển thị rõ | **Một phần**; không có mức tự dùng/savings mặc định; còn thiếu chart overlay, vị trí map, presets |
| 05 | Portfolio/filter/customer/region/source, table/card, map/statistics | Site CRUD/profile, scoped inventory, tọa độ thật | Portfolio/table/card, tìm/lọc, khách hàng; không dựng benchmark | **Một phần**; PR/yield benchmarking cần mẫu/irradiance/công suất hợp lệ; map nền và nhóm vùng còn thiếu |
| 06 | History ngày/tháng/năm/tổng, nhiều metric/trục, bảng, CSV/XLSX/PDF | Stored samples, time bounds, source ambiguity, export limits | Chọn metric/kỳ, chart điểm theo timestamp, bảng/export | **Một phần**; không tự nội suy; thiếu rollup dài hạn, overlay đa trục, PDF riêng, backfill hãng |
| 07 | Device inventory/topology/link/discover/reboot/firmware | Device/binding/integration; capability/native descriptors; catalogue 41 model/913 decoder có provenance | Inventory và detail; lệnh/nâng cấp chỉ khi thực sự hỗ trợ | **Một phần**; không có universal Modbus scanner; sức khỏe 96/100 và uptime giả đã bỏ; discovery vật lý/OTA chưa xây đủ |
| 08 | Remote control mode/export/SOC/charge/EPS/CT/BMS/generator/grid/raw, readback | Shared preview→confirm→order→readback; scope/idempotency/locks | Form intent và khả năng thực tế theo device | **Khung + engine**; chưa 12 nhóm model-specific vận hành; nút khóa không chứng minh hỗ trợ |
| 09 | TOU tuần, tariff, reserve, backup/generator/load-priority, simulate/deploy | Schedule CRUD/revision/copy, timezone/DST, compile artifact và rollout preparation | Editor dùng chung, list/compile/rollout links | **Một phần**; không có ma trận/ROI/12 thanh ghi universal như tài liệu cũ nói; thiếu editor trực quan đầy đủ và translator hãng |
| 10 | Alert trend/severity/category/device/filter, diagnostic/playbook | Incident correlation, dedup/order/recovery, trend API, SLA snapshot | List/detail/filter/assign/triage/note/playbook | **Một phần**; trend chart chưa đủ; decoder alarm/SOP theo model, external notifications chưa nghiệm thu |
| 11 | Command timeline, old/new, ack/readback/verify, filter/export | Journal nối command/audit thật, VERIFIED tách ACK | Journal list/timeline và link device | **Một phần**; cần pagination/tìm kiếm toàn lịch sử, export lớn; chưa physical verification |
| 12 | Energy reports, self-use/cost/CO₂/cycles/uptime, PDF/XLSX/email | Actual scoped counter report, immutable CSV/XLSX/HTML artifacts | Chọn kỳ, tạo/download report, danh sách artifacts | **Một phần**; PDF/email chưa có; savings/CO₂/cycles/uptime để unknown nếu thiếu mô hình/bằng chứng |
| 13 | Link wizard brand/type/cloud/local, scan, topology, kiểm tra | Chỉ hoàn tất với binding đã quan sát; không tạo SN giả; scan thiếu transport trả lỗi rõ | Hãng/platform, thông tin thiết bị, luồng tài khoản dùng chung | **Một phần**; QR, physical discovery, topology acceptance, complete guided onboarding còn thiếu |
| 14 | Data sources/cloud/agent/collection/mapping/diagnostic/sync | Integration state, source policy, collection revisions; scoped mapping-context, version/digest/review; recheck identity + binding/account/agent | Bảng nguồn, config model/HA cùng agent inbox; collection và mapping editor thật, mô phỏng, lịch sử, duyệt độc lập; links account/agent | **BE+FE một phần**; editor mapping đã nối, vẫn chưa có quy trình đưa profile vào production từ UI; health/freshness/failover chưa mọi đường |
| 15 | Site general/tariff/ownership/notification/sources/automation | Merge site config, finite GPS/IANA validation, versioned local drafts | Forms/site settings và link chức năng chung | **Một phần**; lưu nháp không ghi máy; chưa email/SMS/Zalo/push, tariff billing đầy đủ, owner policy granular |
| 16 | Advanced CT/BMS/export/grid/generator/raw/vendor-native + diff | Intent/capability/constraints, evidence and write guards | Nhóm native theo adapter + lý do khóa | **Khung**; model-specific read/edit schemas, enum/unit conversions/readback còn thiếu, không gọi register đoán |
| 17 | Logger/agent/network, IP/RSSI/SIM, Wi-Fi/DHCP, discovery/mTLS/firmware | Enrollment, scoped ingest, sequence/replay, outbox; đọc FC03/04 TCP/V5 theo digest, HA sensor bridge; network metadata quan sát | Agent list/config/diagnostic views; unknown phân biệt offline | **Một phần**; chưa agent service đầy đủ, Wi-Fi config, RTU scan, mTLS lifecycle, OTA/update/recovery |
| 18 | Bulk wizard, model compatibility Exact/Partial/Review, dry-run, canary/readback | Shared policy compilation, digest revalidation, rollout/canary/outcomes | Compatibility/compile/confirmation UI | **Engine + FE một phần**; kết quả phụ thuộc actual profile; chưa multi-vendor production rollout/scheduler |
| 19 | User/role/site scope, 2FA, vendor accounts, security log | Local users/session revoke, RBAC, vault, scoped keys; five roles | User list/filter/actions, actual role matrix/account/log | **Một phần**; đã sửa role filter/Admin control claim; MFA/SSO/multitenancy chưa xây; Raw Command là permission, không thêm role thứ sáu |
| 20 | Commissioning topology/CT/direction/BMS/control/alarm, evidence/signatures/handover | Six manual check records, handover gate; không unlock hardware | Checklist nhập bằng chứng và lịch sử chung | **Một phần**; không tự PASS điện trở/điện áp/tần số; thiếu electrical tests, signature/file storage, physical acceptance |
| 21 | Vendor accounts + diagnostic inspector + cert/key/vault, mẫu UI bắt buộc | Actual accounts/check/sync/encryption/API keys; exact vendor credentials | Shared sidebar; table trái, inspector phải, ba thẻ dưới; Bluesun và Eybond hiện diện | **BE+FE một phần**; bố cục theo ảnh, chưa pixel/usability acceptance; cert mTLS chưa cấp; chưa mọi vendor live; không giả token expiry/HTTP200 |
| 22 | Fleet geographic map/satellite/cluster/filter/site summary/maintenance links | Finite GPS, regional groups, haversine/clustering | Coordinate plot và list/detail/link | **Một phần**; chưa map tile/satellite/boundary/zoom chuẩn GIS; không gọi coordinate plot là basemap hoàn chỉnh |
| 23 | Health/work orders/firmware/calendar | Observation health, work plan versions, execution/evidence/time, independent review | Work orders/plans/service calendar/health; linked incident | **Luồng nội bộ đã kiểm tra, vẫn thiếu sản phẩm**; vật tư/SLA dịch vụ/file attachments/real OTA/compatibility/rollback chưa đủ |
| 24 | EMS trigger/condition/action, bounds, simulate/activate/log | Deterministic evaluation, quality/unit/freshness, monitor hold/notify, saved drafts; hourly baseline từ lịch sử đủ điều kiện | Rule builder/dry-run/result/log links và baseline 24h/cold-start | **Một phần**; physical dispatch disabled; chưa optimizer, forecast dispatch, full conflict/hysteresis/offline strategy |
| 25 | Incident detail/assignment/ack/workorder/note/timeline/SLA/escalation | Persisted correlation/revision/history, SLA snapshot, playbook versions, jobs | End-to-end create→respond→note→timeline→workorder; mobile stacking | **Luồng nội bộ đã kiểm tra**; thiếu channels escalation thật, vendor-specific causes, evidence attachments and service SLA |
| 26 | Device realtime energy/phase/string/battery/latency charts, status/native params | Latest source-aware metrics, stored points, device journal | Actual parameters/measurement charts/control links | **Một phần**; phase/MPPT chart sets, exact sample units/model maps and latency sampling chưa đủ; không dựng sóng giả |

Tên module là bằng chứng vị trí mã, không là bằng chứng hoàn thành. Regression tests nằm trong `tests/test_*workspace*.py`, các test adapter, `tests/test_incident_center.py`, `tests/test_maintenance_execution.py`, `tests/test_schedule_planning.py`, `ui_tests/`.

## Kết luận cấu trúc sidebar: 15 mục, một nơi sở hữu mỗi chức năng

Hash hiện tại có dạng `#page/section/tab`. Label giao diện tách khỏi tên kỹ thuật. Một site được chọn là **phạm vi**, không tạo một bộ sidebar khác. `Nhà máy` quản lý tài sản/khách hàng; `Hệ thống` chỉ topology/SLD, không lặp site CRUD. Các subtab dưới đây là hợp đồng bố trí đích; cột trạng thái phân biệt phần đã nối và phần còn thiếu.

| Sidebar / route chuẩn | Phải hiển thị / subtab sở hữu | Liên kết chung và tình trạng |
|---|---|---|
| Tổng quan `#overview/main` | Fleet KPI, việc cần chú ý; khi chọn site: Overview, Data, Equipment, Control, Schedule/TOU, Alerts, Journal, Diagnostics, Reports, Network; thẻ Giám sát quy chuẩn lưới Grid-Code (Volt-Watt P(V), tần số, Cos phi, VUF lệch áp 3 pha) | Đã nối API thật và liên kết sâu sang bộ điều phối EMS |
| Nhà máy `#plants/main` | Portfolio list/card, customers, regions, onboarding, benchmarking, danh mục vi lưới đa tài sản (PV, ESS, Genset, EV, Heat Pump, Smart Meters) | Đã có ma trận tài sản và trạng thái vận hành |
| Hệ thống / SLD `#topology/main` | Quan hệ inverter–meter–battery–load–logger, ranh giới đo, sơ đồ một sợi SLD phân định 4 vùng điện (PCC lưới, Bus AC Inverter/ESS, ATS Máy phát dự phòng, Phụ tải linh hoạt EV DLM & Bơm nhiệt SG-Ready) | Graph SVG tương tác và bảng phân định ranh giới điện |
| Bản đồ `#plants/map` | Filter vùng/hãng/state, cluster, site drawer, links overview/control/maintenance/report, trạng thái quy chuẩn lưới | Coordinate view hiện có, cluster và drawer hoạt động |
| Thiết bị `#devices/main` | Inventory; device Detail, Realtime/Data, Control, Advanced/Native, Journal, Documents, Maintenance; bộ giải mã thanh ghi và bảng mã lỗi 30 hãng | Tra cứu 30 hãng inverter/pin và SOP xử lý |
| Điều khiển `#operations/main/control` | Chọn site/device, giám sát, intent cơ bản, BMS/TOU/CT/export/generator/grid/native, preview/diff/confirm, command status; bộ biên dịch gói lệnh Modbus FC06/FC16 30 hãng và điều khiển máy phát Diesel / Black-Start | Trình biên dịch Modbus FC06/FC16 và điều độ máy phát hoạt động |
| Lịch / TOU `#operations/main/schedules` | Weekly editor, templates/copy, tariff reference, reserve, compile report, rollout; quy hoạch điều độ dự báo Predbat 24h & tính rào cản khấu hao cell pin ($/kWh) | Bộ mô phỏng Predbat 24h và biên dịch lịch tự động |
| Điều phối EMS `#operations/main/rules` | Policies/rules, triggers/conditions/actions, simulation; Bộ điều phối quy chuẩn lưới điện (Volt-Watt, Volt-Var, Freq-Watt, NA003), Cân bằng pha Fortescue IEC 61000-4-30, Quản lý phụ tải nhiệt Carnot & SG-Ready, Điều phối sạc xe điện động EV DLM & chuyển mạch 1p/3p | Toàn bộ 4 engine vật lý đã nối form và API trực tiếp |
| Dữ liệu & kết nối `#reports/main` | Overview/quality, Sources, Cloud accounts, Local Agent, Collection, Mapping, Diagnostics, Sync log; telemetry/history; Giám sát 6 dòng công tơ 3 pha công nghiệp & mặt phẳng năng lượng 4 góc phần tư Q1-Q4 | Tab Công tơ 3 pha tích hợp bộ giải mã thanh ghi Modbus |
| Cảnh báo `#incidents/main` | Center list/detail, assign/triage, notes/timeline, playbook, SLA/escalation, linked jobs; giải mã mã lỗi 30 hãng kèm quy trình SOP khắc phục | Danh mục mã lỗi 30 hãng và playbook xử lý |
| Báo cáo `#reports/analytics` | Period/scope, energy/performance/incident/customer, artifacts/export/scheduled delivery; Giao dịch thị trường điện bán buôn (DAM/IDM) & Doanh thu dịch vụ điều tần sơ cấp FCR | Mô phỏng khớp lệnh đấu thầu và tính doanh thu FCR |
| Bảo trì `#incidents/health` | Health, Work orders, Plans/calendar, Firmware; execution/checklist/time/review/history; Chẩn đoán suy giảm & sức khỏe cell pin lưu trữ BESS (Độ lệch áp ΔV, nội trở mΩ, dung lượng SOH) | Đã nối thẻ chẩn đoán BESS và nút lập phiếu kiểm tra cell |
| Nhật ký `#operations/main/journal` | Command lifecycle, operations, sync, audit/security theo quyền; Dòng thời gian điều độ EMS bất biến và kiểm tra đọc lại Readback | Dòng thời gian lệnh, xác minh đọc lại và kiểm toán an toàn |
| Người dùng `#settings/main/users` | Users, Roles/permissions, Site scope; links cloud accounts/security | Local RBAC năm vai trò, phân quyền theo nhà máy |
| Cài đặt & Hãng `#settings/main/connections` | Vendor accounts, General/site, Tariff reference, Ownership, Notification policy, Source policy, Device linking, Automation links, Secret/API keys, Evidence; Ma trận chứng cứ giao thức 30 hãng | Đã có tài khoản hãng, chính sách nguồn và chứng cứ protocol |

Các routes tắt trong card phải giữ site scope và dẫn đến cùng chức năng sở hữu. Không thêm CSS riêng theo route; shared primitives và `static/app.css` sở hữu mọi layout/typography/semantic state. Account route tuân bố cục ảnh 21. VI/EN đã có cơ chế chung nhưng còn nhãn kỹ thuật/translation cần trau chuốt.

## Site → Tổng quan: 11 khối phải bao phủ

| Khối | Trạng thái hiện tại | Còn thiếu |
|---|---|---|
| Sơ đồ realtime | Scoped PV/battery/grid/load/EPS; null-safe, display/fullscreen, links | Inverter hub, topology/arrow direction, keyboard/fullscreen polish, streaming chart |
| Điều khiển nhanh | Preset names và route tới shared device control | Chuyển preset thành exact model intents, preview/diff và apply sau acceptance |
| Trạng thái nhà máy | Today/month/year counters; lifetime unknown khi không có nguồn | Kỳ tùy chọn/tổng/bộ chart ngay trong khối; current data không chứng minh toàn site khỏe |
| Sản lượng & tiêu thụ | Bảng kỳ từ counter; link actual timeseries chart | Multi-series chart đồng kỳ, coverage và nhiều meter boundary |
| Tỉ lệ tự dùng | Trường nullable; không mặc định 78%/65% | Energy accounting xác minh battery/grid/meter, không suy từ PV đơn lẻ |
| Thời tiết & dự báo | GPS→Open-Meteo/cache/stale metadata; chart forecast có nguồn | Vendor weather priority, malformed response tests sâu, commercial deployment terms/config |
| Thiết bị hệ thống | Actual scoped devices, status/detail links | Model-specific icons/topology/phase strings và stale freshness nhất quán |
| Kết nối & nguồn | Enrollment phân biệt online; integration metadata/unknown | Agent heartbeat, measurements latency, authority/failover ở tất cả view |
| Cảnh báo gần đây | Persisted incidents→center | Trend/widgets và live vendor decoder completeness |
| Nhật ký điều khiển | Persisted commands→journal, không suy ACK thành verified | Actor/readback diff/large history ngay card và trạng thái nhất quán |
| Vị trí & thông tin | GPS/address/customer/timezone/capacity thật; links map/edit/diagnostics | Mini-basemap, ảnh site uploads, owner metadata |

## Phạm vi dự toán → mã hiện có → phần chưa xây → điều kiện hoàn thành

Các khoảng kLOC dưới đây là **dự toán tham khảo do chủ dự án đưa ra**, không là target phải viết đủ dòng. Các khối overlap, không cộng lại để báo tổng. BE/FE thực đo ở mục inventory bên dưới. Một module có một file không tương đương đạt toàn bộ dự toán.

| Phạm vi dự toán (BE / FE kLOC) | Mã hiện có | Phần chưa xây hoặc chưa nối | Điều kiện hoàn thành có thể kiểm chứng |
|---|---|---|---|
| Domain/API/site/device 10–18 / 4–7 | Domain models, SQLite entities, scoped CRUD, topology records | Schema migrations dài hạn, tenant/org/customer lifecycle sâu, electrical topology | Migration/recovery, isolation, referential integrity, CRUD+link E2E và topology acceptance |
| Auth/RBAC/secrets 7–12 / 5–8 | Local password/session/CSRF, 5 roles, vault, scoped API keys, revoke | MFA/SSO/tenant boundary, key rotation/backup UI, trusted external audit | Auth failure/revoke/concurrent reads passed; tenant/adversarial tests; restore/rotation diễn tập |
| Dashboard/site 4–7 / 8–14 | Operational read model, 11 site blocks, period counter, weather service, shared flow có motion/freshness | Full energy accounting, verified topology/source-to-load attribution, multi-axis charts, preset acceptance | Reconcile with site meter/counter and all missing states; 26 reference visual/usability acceptance |
| Telemetry/WS 8–14 / 5–9 | Poll clients, normalized samples/provenance, quality/source policy, scoped WS/invalidation | Production fanout/storage/backfill, broad exact profiles, clock/failover acceptance | Long-running ingest/reconnect/load tests and live profile comparison with vendor UI |
| History/analytics 6–10 / 7–12 | Bounded stored points, chart, counter/reset/coverage analysis, export | Durable years of rollup, query/downsample, multi-axis chart, cloud backfill | Known energy baselines, gaps/reset/rollover, timezone periods and scalable export |
| Device management 5–9 / 6–11 | Discovered IDs/bindings/inventory, manual assets | QR/scan, identity reconciliation across transports, peripheral topology | Same physical device deduped; onboarding and revoke tested across cloud/local |
| Remote engine 10–18 / 8–14 | Intent/capability/preview/confirm/locks/idempotency/readback/quarantine | Most model write mappings/translators, hardware commissioning | Exact account/model/logger/FW identity + accepted range/unit + physical readback + failure recovery |
| Advanced/native 5–10 / 8–15 | Native groups/evidence/catalog, unknown reasons | Real field read/write schemas for CT/BMS/grid/ATS/generator, per-model screens | Compare each field/enum/scale with native API and device; reviewed independent sensitive gates |
| TOU 5–9 / 5–9 | Versioned weekly schedules, validation, compile artifacts, source digest, prepare rollout | Visual matrix, per-vendor semantics/slot limits, unattended job execution | Full week/DST/concurrent revisions pass; hardware schedule readback matches intent |
| EMS 8–16 / 7–12 | Conditions/actions evaluator, fresh units, monitor hold/notify, simulation | Optimizer, hysteresis/conflict arbitration, weather/tariff dispatch, offline policy | Scenario simulator with constraints, blackouts/failovers and field trial accepted |
| Bulk 6–12 / 4–8 | Canary, compatibility rows, persisted rollout/cancel/outcomes | Complete multi-vendor profiles, distributed rollout worker/rate budget | Partial/unknown outcomes isolated; per-device authority; recover interrupted rollout |
| Sources/integrations 6–10 / 7–12 | Account/grants/check/sync, collection revisions/source policies; mapping BE+FE author/simulate/version/review | Shipping canonical profiles/activation acceptance, vendor history/alarm pipelines and all failover views | Credential→discovery→binding→telemetry→incident/report flow verified per ecosystem |
| Commissioning 5–9 / 6–10 | Manual check/evidence text, six-check handover gate | Electrical procedures, measurements integration, uploads/signatures | Recorded real test procedure/outcome reviewed; never auto-unlock from self-attested PASS |
| Incidents 6–11 / 7–12 | Dedup/out-of-order/recovery, triage/assign/notes/history, SLA, versioned playbook/jobs | Actual vendor alarm decoders/playbooks, external escalation channels/files | Alarm fixture→incident→assignment→job→recovery→close; channels independently observed |
| Maintenance/OTA 5–10 / 6–10 | Work plans, execution/results/time/void/review, health from observations | Parts/service contracts/uploads; firmware package verification/compatibility/transfer/rollback | Independent review plus actual OTA lab fail/recovery trials on exact hardware |
| Reports 5–9 / 5–9 | CSV/XLSX/HTML stored artifacts tied to scope/date; no fabricated financial metrics | PDF/email, tariffs/CO₂ assumptions, signed customer reports | Reproduce report from source set; correct scope and saved bytes; actual delivery receipt |
| Audit/journal 5–8 / 4–7 | Hash-linked append-only local DB audit, command state history | External anchoring, retention/search/export at scale | Tamper/recovery check and immutable external checkpoint; all commands traced to authorization |
| Map/fleet 3–6 / 5–9 | Coordinate plot, GPS validation, distance/clusters/regions | Basemap/satellite/geometry/zoom, fleet geographic interaction polish | Geospatial accuracy and map/data attribution plus device/site deep-link QA |
| Settings 5–8 / 7–11 | Local settings/ownership/source/notification drafts and adapters forms | Granular ownership, delivery integrations, versioned tariff rules | Configuration produces real downstream effect or explicitly remains draft, with audit/revert |
| Shared UI 1–3 / 10–18 | Single shell/sidebar/app.css, reusable forms/tables/dialogs, VI/EN | Component library cleanup, accessibility/full mobile/translation/visual polish | Routes share styles and semantics; tested keyboard/errors/loading and representative device sizes |
| 8 vendor platforms 65–115 / 35–68; Bluesun profile extra | Eight cloud read paths of different depth, including Eybond platform/session/collector/native read; profile/registry; Deye-only guarded compiler | Eybond source time/canonical mapping/history/alarm/control, incremental inventory; complete vendor-native maps and OEM acceptance | Contract + field evidence + live account/device acceptance per variant; cannot certify by logo |
| Site Agent 20–35 BE | Token enrollment/ingest, sequence/replay, SQLite outbox, model FC03/04 TCP/V5 và HA bridge; 41 community profile | Service install/discovery, RTU và full model TCP suite, mTLS/rotations, reconnect/backfill/update/diagnostics | Prolonged offline→reconnect/replay/load test, cert/revoke/update drills and site hardware trial |
| Tests/simulator/E2E 175–315 combined | BE contracts/workflows and isolated browser simulator; inventory below | Large model/error fixture corpus, HIL, soak/load/security/accessibility/visual acceptance | Trace each acceptance criterion to executable check and actual observed evidence |
| Infra/migrations/scripts 15–25 | Package/build, controller CLI, dev scripts, source inventory | Production deploy/HA/tenant observability/backup restore/migrations/oncall | Install/upgrade/restore/runbook and workload SLO verified in target environment |

### Vì sao code nhỏ hơn dự toán nhiều lần?

**Vì hiện còn thiếu phần lớn độ sâu của sản phẩm trưởng thành.** Reuse có giảm trùng lặp, nhưng không giải thích được toàn bộ chênh lệch. Frontend hiện là JavaScript ES modules, không phải React/TypeScript theo giả định dự toán. Storage/controller đơn tiến trình và tập workflow hẹp cũng nhỏ hơn kiến trúc SaaS/SCADA dài hạn.

Bảng dự toán 400k–630k production bao gồm nhiều model/hãng, native-control, đầy đủ agent, vận hành offline, optimizer, OTA, tenancy, long-term telemetry, reports/delivery, và UI 55–75 screen/state. Repo chưa có phần lớn các lớp đó. Có catalog/nút/form/API alias không đồng nghĩa triển khai chúng. Xóa code dựng dữ liệu hoặc compiler đoán có thể làm LOC giảm nhưng làm kết luận đúng hơn.

Không thể dùng `LOC hiện có / LOC dự toán` làm % hoàn thành; cũng không thể dùng “kiến trúc sạch” để kết luận đã làm xong. Chỉ đóng một mục khi đủ điều kiện ở cột cuối, có BE/FE liên kết, test tương ứng và bằng chứng cần thiết.

## Liên kết chức năng đã kiểm tra và ranh giới

1. Cloud account → adapter → discovery → device binding → telemetry/native provenance → mapping/quality/source → chart/report. Discovery/latest có contract theo từng hãng; shipping canonical profiles/backfill chưa đầy đủ. Editor mapping đã nối tới native observations và version/review service; approved draft vẫn không phải commissioned profile và không thay dữ liệu vận hành.
2. Device intent → capability → preview/diff → confirmation → serialize/idempotency → send/order → readback → journal. ACK không phải VERIFIED; UNKNOWN_OUTCOME không tự retry ghi. Chưa chứng minh hardware acceptance.
3. Schedule revision → compile/capability report → source digest recheck → rollout/canary → per-device outcomes. Lịch đổi hoặc profile bị thu hồi phải vô hiệu kế hoạch cũ. Không có universal slot/register mapping.
4. Native alarm → normalized alarm observation → correlation/dedup/order → incident → response/note/playbook → work order → execution/time → independent review → close. Core có test; vendor alarm decoding/delivery còn thiếu.
5. Site/profile/source policy → all relevant views. Đã bỏ các alias ghi không gắn engine và dữ liệu hardcode; topology reconciliation/source selection mọi metric vẫn cần mở rộng.

## Kiểm thử và QA

Đợt mới nhất 27/09: [legacy validation](legacy-validation-2026-09-27.md), gồm full browser sau sửa global CSS và QA flow desktop/mobile. Các bản dưới đây giữ số liệu snapshot cũ.

Kết quả tổng hợp cuối được ghi trong [audit-validation-2026-09-23.md](audit-validation-2026-09-23.md). Các lỗi phát hiện được sửa rồi chỉ chạy lại kiểm tra bị ảnh hưởng; không coi lần chạy trước sửa là kiểm thử bản cuối. Không dùng tài khoản/thiết bị thật trong suite này.

Đợt Eybond bổ sung: full BE 429 pass/3 fail; sau sửa, 73 ca thuộc nhóm bị ảnh hưởng đều pass. Full browser 10 pass/1 fail; sửa selector test rồi ca đó pass. Ruff/28 module JS qua. Chi tiết, log và giới hạn QA nằm tại [eybond-validation-2026-09-24.md](eybond-validation-2026-09-24.md), không cộng số ca rerun vào tổng suite.

Đợt Mapping 25/09: xem [mapping-validation-2026-09-25.md](mapping-validation-2026-09-25.md). Full BE **450 passed**; full browser **13 passed** trước sửa tab theo QA. Gộp điều hướng Data về một hàng tab dùng chung; hồi quy riêng ghi trong validation. Số test không được cộng qua các lần chạy.

Screenshots local QA: `work/qa-audit/accounts-vi.png`, `site-overview.png`, ảnh alert mobile và work-order workflow. Đã xem trực tiếp các ảnh đại diện: chung sidebar/styles; account layout theo cấu trúc ảnh 21, có Bluesun/Eybond; các trường unknown không tô thành thành công. Còn khoảng cách UI: tổng quan quá dọc, topology điện/phân bổ nguồn→tải chưa đầy đủ, một số bảng ở độ rộng nhỏ chưa tối ưu. Đợt 27/09 đã bổ sung flow có motion và sửa CSS toàn cục; ảnh mới được ghi trong validation mới. Không kết luận khớp 100% 26 ảnh.


<!-- actual-code-inventory:start -->
## Số dòng thực tế có thể đo lại

Đo lúc **2026-09-27T05:08:24.405534+00:00** trên working tree, gồm code chưa commit.

| Nhóm | Số file | Dòng vật lý | Dòng không trống |
|---|---:|---:|---:|
| Backend Python | 110 | 39,346 | 34,355 |
| Frontend JavaScript | 31 | 16,618 | 15,748 |
| Frontend CSS / HTML | 2 | 6,012 | 5,502 |
| Test BE / simulator / fixture | 80 | 16,930 | 14,381 |
| Test UI / browser fixture | 6 | 702 | 640 |
| Scripts tự viết | 3 | 518 | 478 |
| **Tổng FE (JS + CSS/HTML)** | **33** | **22,630** | **21,250** |
| **Tổng code ứng dụng BE + FE** | **143** | **61,976** | **55,605** |
| **Tổng test / simulator / fixture** | **86** | **17,632** | **15,021** |
| **Tổng code ứng dụng + test + scripts** | **232** | **80,126** | **71,104** |

Phương pháp: đếm dòng vật lý (gồm comment và dòng trống), đồng thời công bố số dòng không trống. Không phải semantic SLOC. Không tính dependency, môi trường ảo, lock, generated, assets/ảnh, JSON hợp đồng, tài liệu, build output hoặc cache. Nhóm simulator/fixture không được tính vào production. Không cộng các dòng tổng lần nữa.

Đo lại bằng `python scripts/measure_code.py --update-doc`; lệnh chỉ đọc source và cập nhật báo cáo, không chạy test, build, QA hoặc gọi thiết bị.

Danh sách từng file và số dòng nằm trong [code-inventory.json](evidence/code-inventory.json). LOC phản ánh kích thước mã, không chứng minh workflow đúng, hoàn thiện UI hoặc nghiệm thu phần cứng.
<!-- actual-code-inventory:end -->
