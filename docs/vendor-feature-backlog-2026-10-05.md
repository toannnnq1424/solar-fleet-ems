# Chức năng các hãng và backlog phát triển SolarOne

<a id="resume-checkpoint"></a>
## ĐỌC TRƯỚC — Điểm tiếp tục, cập nhật 09/10/2026

Đây là **runbook tiếp tục chuẩn** cho yêu cầu “đọc vendor-feature-backlog-2026-10-05.md và tiếp tục quy trình đang dở”. Đọc checkpoint này rồi [quy trình phục hồi và hàng đợi](#execution-runbook), không bắt đầu lại nghiên cứu từ đầu hoặc coi các báo cáo cũ là chứng nhận hoàn thành. Chỉ dẫn mới của người dùng và `AGENTS.md` vẫn có hiệu lực. Không có agent tự chạy nền sau khi phiên kết thúc.

**Quy tắc bổ sung 08/10:** mỗi lần người dùng yêu cầu tiếp tục, ngay sau khi đọc tối thiểu instruction/checkpoint để ghi an toàn, phải **lưu checkpoint đoạn chat trước và nhật ký bàn giao trước khi khảo sát sâu, sửa code, chạy test hoặc QA phiên mới**. Dùng nhật ký cuối file, giữ lịch sử append-only; không chép bí mật, không bịa phần hội thoại thiếu, không ghi trùng bàn giao đã có. Sau đó mới làm RSM-00. Checkpoint duy nhất đầu file phản ánh việc hiện tại; nhật ký giữ diễn tiến các phiên.

| Trường checkpoint | Giá trị hiện tại — phải đối chiếu lại khi tiếp tục |
|---|---|
| Workspace | `/Users/toanlamsaoduocc/Desktop/solar-fleet-ems`; nhánh `fix/real-data-engine-integration`; HEAD quan sát `af4f1b8`; working tree có nhiều sửa đổi chưa commit |
| Lát cắt đang mở | **TẠM DỪNG THEO YÊU CẦU USER sau báo cáo/commit/push**. UI-ENERGY-09 còn mở: ba kiểu flow, phối cảnh, hướng, phóng to, tooltip và quick-control E09.11 mới. LIVE-01/GW-01 chưa nghiệm thu; không tương đương toàn bộ SEMS+ |
| Bàn giao đầu phiên mới | Đã lưu **SESSION-2026-10-09-01**; bàn giao bổ sung SESSION-2026-10-09-02 bên dưới. User yêu cầu lưu toàn bộ ảnh tham chiếu hôm nay, đánh giá tiến độ thật, sau đó commit/push và dừng. Không tiếp tục mở rộng UI hoặc điều khiển thiết bị trong lát cắt báo cáo này |
| Đã triển khai và test tự động | Chu kỳ tối thiểu SEMS+ 60s, scheduler kiểm tra 15s, bỏ cache station 15 phút; device monitor tự đọc bản nhận 15s; nút đọc mới qua shared controller; selector nhà máy/hãng/tài khoản theo quyền |
| Kết quả kiểm thử của lát cắt | Final 09/10: **1.894 BE đạt/13 deprecation warnings/321,85s; 107 UI đạt/198,83s**; Ruff, syntax 63 JS, build sdist/wheel và whitespace đạt. Tests fixture tách tài khoản thật, không là pixel/hardware acceptance. [Bằng chứng](evidence/energy-flow-ui-2026-10-09.md) |
| QA thật còn thiếu | Tải lại client mới, kiểm nút/selector; đối chiếu cùng serial, kỳ, đơn vị, clock; tối thiểu ba chu kỳ đúng cadence. Không suy “realtime tức thời” từ HTTP mới hoặc WebSocket |
| Môi trường lúc bàn giao | Đã dừng server QA read-only 8765 do agent mở (SIGTERM đúng PID 86686, xác minh command trước; không còn listener), theo yêu cầu dừng phiên. DB/vault/tài khoản không bị xóa. Khi tiếp tục kiểm listener rồi mới khởi động đúng một server read-only; có thể cần user đăng nhập lại SolarOne |
| Phát hiện UI còn mở | BUG-LIVE-02 regression cuối lượt trước đạt 5; live đối chiếu được hai receipts, chưa đủ ba và chưa server-atomic. Flow cũ còn cộng PV+abs(pin) làm throughput sai; UI-ENERGY-09 bỏ số đó, dùng nút tổng hợp minh họa. Chưa xác minh thời gian GoodWe nên không chạy animation giả |
| Quyền QA | GoodWe read-only đã được người dùng cho phép; kiểm phiên hiện tại trước khi yêu cầu nhập lại. Không lưu email/serial/token vào runbook. Deye và hãng khác chờ đúng tài khoản/quyền; không tự xin hoặc chấp nhận điều khoản thay người dùng |
| Cổng an toàn | `SOLAR_WRITES_ENABLED=false`; không gửi lệnh điện thật, mở capability hàng loạt, push hoặc deploy. Đăng nhập không cấp quyền ghi |
| Kho lịch sử hiện có | `Store.add_samples` có lịch sử hữu hạn, nhưng thiếu source timestamp thì ghi đè khóa `UNKNOWN`. Snapshot kiểm tra: 220 samples/220 kênh, tất cả thiếu source time; chưa phải kho mọi lần thay đổi |
| DE / AI | **Chỉ lập kế hoạch** tại [Phần IV](#data-ai-plan); chưa có archive mới, warehouse, model AI hay SQL assistant được triển khai |
| Bước thao tác ngay phiên sau | Chỉ sau lệnh mới: checkpoint hội thoại trước → RSM-00 (Git HEAD/remote/checks/process) → đọc SESSION-2026-10-09-02/03, assessment và manifest → live visual QA E09.1–4 sizing/fullscreen/fallback/snapshot + user acceptance; tiếp LIVE-01 ba chu kỳ cùng scope/revision. Không tuyên bố endpoint đọc đồng thời là snapshot DB nguyên tử |
| Không làm lại mù | Không reset dirty tree; không khởi động poller thứ hai; không phát lại command khi không biết lần trước đã gửi hay chưa; không nhập seed để làm biểu đồ đẹp |

Thứ tự hiện tại: hoàn tất tính đúng/freshness + UI theo từng lát cắt → QA GoodWe đọc và UI toàn bộ → I0–I6 theo phụ thuộc/khả năng; Deye khi người dùng cấp tài khoản → pilot đọc → nền dữ liệu và AI theo cổng bên dưới. **DE-00 bảo toàn observations là lát cắt chống mất dữ liệu cần đưa lên trước một đợt thu thập dài hạn**, không chờ làm xong toàn bộ các hãng; chưa tự triển khai trong phiên lập kế hoạch này. Cổng ghi thật có thể chờ độc lập, không chặn pilot đọc hoặc nghiên cứu DE.

### UI-ENERGY-09 — bổ sung trực tiếp từ ảnh/user ngày 09/10

Ưu tiên hoàn thiện vùng flow trước theo yêu cầu mới, không ngụ ý đã hoàn thiện tất cả chart.

| Bước | Owner / thao tác | Trạng thái và acceptance |
|---|---|---|
| E09.1 | `energy-flow.js`, `app.css`: phối cảnh có mô hình SVG chiếu 3D, vòng nút, sơ đồ thiết bị; dùng cùng snapshot, lưu sở thích trình bày | Implemented, final fixture regression đạt; **live visual/user acceptance còn mở**. Mục tiêu nút/đường không dính/chồng/cắt mép card hẹp/mobile/fullscreen. Mô hình chung, không ảnh sản phẩm/sơ đồ đấu dây đã xác minh |
| E09.2 | Bỏ throughput cộng PV+abs(pin); kiểm dấu nhánh và gate freshness, arrow/pulse, pause/reduced motion, tooltip nguồn | Implemented; chỉ GOOD còn hạn được chạy arrow/motion. Vendor reported có giá trị/nhãn sạc/xả nhưng không giả source time, topology hay phân bổ từng nguồn |
| E09.3 | Shared `panel-expand.js` qua `card`: icon phóng to/thu nhỏ, native fullscreen và fallback/Esc; không sao chép DOM số liệu | Fixture regression đạt. Native expanded view giữ snapshot có nhãn; realtime khi fullscreen, fallback focus trap/live-refresh cần hoàn thiện. Card không tiêu đề/custom panel cần inventory; chưa phủ mọi vùng |
| E09.4 | `chart-inspector.js` + `dailyEnergyChart`: tooltip/crosshair theo ngày cho mọi chuỗi hiện có, hover/focus/touch/Esc, missing ≠ zero | Fixture regression đạt. Không có source field thì không bịa provenance; header vùng giữ provenance. History/count/heatmap và touch tooltip flow cần acceptance riêng |
| E09.5 | Đường công suất: PV/load/battery/grid, từng pha, SOC và giá trên trục/unit riêng, brush/hover đồng bộ theo timestamp | TODO: cần GoodWe historical power/phase API + timezone + range/backfill. Không dùng receipt timestamp để vẽ đường đo thực; không ép giá điện thiếu dữ liệu |
| E09.6 | Điện năng theo ngày/tuần/tháng/năm, 6–7 series, legend, tooltip đầy đủ | PARTIAL: có daily series generation/consumption/export và bộ đếm kỳ; chưa đủ charge/discharge/import/self-use lịch sử theo mọi kỳ. Bổ sung contract trước rồi UI, không chia tổng tuần thành ngày giả |
| E09.7 | Calendar heatmap đúng lịch, missing/future/partial day, scale, chọn kỳ/tooltip | TODO: reuse daily rows thật, không tô ngày thiếu thành 0; xác nhận calendar/timezone/source period. Empty state vẫn đủ khung lịch |
| E09.8 | Donut AC→load/grid, load từ PV+pin/grid và Sankey nguồn→đích | TODO: yêu cầu directional energy buckets/coverage cùng kỳ; không suy PV→pin/load từ bốn công suất tổng. Nếu thiếu chỉ hiện các tổng đã biết, không giả tỷ lệ hoặc topology |
| E09.9 | Comparison: nhóm metadata/power/SOC/energy, chọn chỉ số/nhà máy/thời điểm, tổng/trung bình có semantics, indicator trend | TODO: read-only đã thấy UI thật ở link user; chưa xác minh API. Giữ cùng scope/device/timezone; không copy query chứa customer ID vào repo; không lấy current values gán vào slider quá khứ |
| E09.10 | Inventory tooltip/fullscreen của tất cả vùng chart/table/custom widget | TODO sau E09.1–4: kiểm các owner 26 màn, không chỉ flow/daily chart. Per chart cần mouse/keyboard/touch + fullscreen/Esc + stale/empty/error/resize. Đóng khi có ảnh/interaction evidence, không chỉ tên hàm |
| E09.11 | Điều khiển nhanh theo ảnh 09:53: switch tổng, slider giờ hai đầu, ngày lặp, giới hạn điện mua tùy chọn, nút Lưu | TODO; lập trình draft/read trước. Owner control/schedule hiện hữu, không route điều khiển song song; chi tiết acceptance ngay dưới |

#### E09.11 — quick-control: từng bước, không mở khóa bằng ảnh

1. Kiểm exact vendor/platform/model/logger/firmware/role và current config bằng read-only. Nội dung ảnh chỉ chứng minh UI, chưa chứng minh API/đơn vị/giới hạn được hỗ trợ.
2. `control-workspace.js`/`schedule-editor.js` và `app.css`: card ngắn gọn, switch bật/tắt, slider hai đầu + ô giờ nhập chính xác, weekday chips đủ CN–T7, toggle giới hạn và field đơn vị, nút Lưu rõ draft/apply. Disabled phải nêu lý do và vẫn đủ contrast, không bắt chước chữ gần như không đọc được trong ảnh.
3. Draft không tự đặt 08:00–16:00, không tự tick mọi ngày, không auto bật sạc. Chỉ prefill từ config đã đọc hoặc input user; trạng thái blank phải thao tác được khi có quyền tạo draft.
4. Xác minh giới hạn ảnh hiển thị kWh là energy cap hay giới hạn khác; tuyệt đối không đổi thành kW hoặc map sang max-charge-current. Khả năng native chỉ xuất hiện khi contract đủ, unsupported có reason.
5. Chuẩn thời gian: timezone nhà máy, cross-midnight, start=end, empty weekdays, DST, resolution, overlap/số slot; preview khác draft, version/revision và xung đột TOU/EMS/Copilot. Không hứa “Copilot tự giành quyền lại” chỉ vì tooltip hãng nói vậy; cần semantics ownership/expiry có readback.
6. Chỉ chức năng cùng semantics đi qua shared schedule/intent interface. AC-port groups, month mask, smart mode hoặc cap hãng riêng giữ native extension có schema; không ép compiler các hãng khác nhận chức năng không tương đương.
7. Khi được phép ghi riêng: đọc cấu hình trước → preview tác động → confirm exact target → command engine/idempotency/serialization → ACK → fresh readback/VERIFIED; timeout unknown/quarantine, không retry mù. Lưu draft không gửi phần cứng.
8. Tests: blank/null/zero/invalid/cross-midnight/timezone/conflict/RBAC/revision/retry; mouse/keyboard/touch slider, focus/error/reduced motion/mobile; no writes khi lưu draft/khóa. Ảnh trước/sau style và đúng units; có acceptance riêng mới đóng.

#### Đánh giá sản phẩm và lưu ảnh — 09/10

- Người dùng xác nhận UI vẫn chưa đạt. [Đánh giá tiến độ có trọng số, giới hạn và 10 nhóm vấn đề](project-assessment-2026-10-09.md): ước lượng **35–40% cốt lõi**, **khoảng 30% kể cả DE/AI**, không dùng như tỷ lệ đo chính xác hoặc ETA. Chưa có vendor nào nghiệm thu đầy đủ read/history/control/readback.
- [Manifest 12 ảnh tham chiếu hôm nay](evidence/ui-reference-manifest-2026-10-09.md); ảnh nguyên bản và INDEX xem ảnh lưu riêng ngoài Git trong `Documents/SolarOne-private-reference/2026-10-09/`. Không đưa định danh khách hàng/ảnh/số liệu trong ảnh vào source hoặc seed. Nếu chuyển máy cần mang kho riêng, không tự tải từ remote.
- ASSESS-EMS-01 / INVESTIGATE P1: source inspection `ems_optimizer.py` thấy history SOC fallback dùng source timestamp hoặc receipt mà chưa chứng minh quality/clock/battery identity; cần reproducer, audit cả site/fleet và negative tests trước dùng cho vận hành. Chưa phát lệnh thật, không gọi đây là incident đã xảy ra.

Ảnh SEMS+ dùng làm chuẩn chức năng/tương tác; giữ shell/style sáng theo mock SolarOne.
Link comparison chứa định danh nhà máy: chỉ xem trong browser được phép, không lưu nguyên URL/payload vào tài liệu công khai.

### SESSION-2026-10-09-02 — checkpoint bàn giao trước đánh giá/lưu ảnh

- Ngữ cảnh trước bị gián đoạn: UI-ENERGY-09 đã sửa ba kiểu flow, mô hình SVG phối cảnh, direction/freshness gate, phóng to card dùng chung và tooltip daily chart. Chưa được người dùng nghiệm thu đẹp/đủ; phản hồi mới khẳng định UI vẫn chưa đạt.
- Bằng chứng trước theo bàn giao: 34 BE liên quan đạt; UI full vòng gần nhất 105 đạt/2 lỗi do selector đếm cả vùng hover; sau sửa selector, affected 18 đạt. Không ghi full suite là đạt. Fullscreen sizing, nhãn snapshot và độ chính xác SOC đã sửa tiếp **sau** đợt 18 test, chưa có kết quả cuối được xác minh ở checkpoint này.
- QA đọc trước: SolarOne đã đăng nhập và thấy số thật; flow source time GoodWe chưa xác minh nên không animation giả. Phóng to phát hiện hình quá cao; đã sửa CSS nhưng cần kiểm lại. Không có bằng chứng hardware writes trong lượt UI.
- Working tree vẫn giữ nhiều sửa đổi từ các phiên trước; không reset hoặc coi mọi diff là của phiên này. Không phục dựng kết quả test/process từ trí nhớ thành chứng nhận.
- Yêu cầu mới: ảnh Điều khiển nhanh (tắt/bật, khoảng giờ sạc, tùy chọn giới hạn điện mua, lặp theo ngày, lưu); lưu bộ ảnh ngày 09/10 ở kho riêng ngoài Git, thêm manifest tham chiếu; đánh giá theo acceptance, không LOC.
- Sau báo cáo, user đã cho phép commit/push GitHub rồi dừng. Chỉ đẩy code/tài liệu/test đã rà soát; không đẩy secrets, DB, raw customer data hoặc ảnh có định danh. Không deploy hay mở cổng điều khiển. Bước tiếp: kiểm kê ảnh, scope dirty tree và evidence, cập nhật đánh giá + checkpoint, consolidated verification và secret review trước commit/push.

### SESSION-2026-10-09-03 — báo cáo/verification cuối, chờ commit/push

- Lưu nguyên byte 12 ảnh user gửi ngày 09/10 ngoài Git, hash/copy đối chiếu đủ; INDEX riêng và manifest đã có. Ảnh khác cùng ngày chưa gửi không tự thu thập. Không xóa bản gốc.
- Thêm E09.11 quick-control tám bước, ASSESS-EMS-01 và đánh giá có mẫu số/trọng số/độ không chắc chắn; UI **chưa được nghiệm thu**, DE/AI là kế hoạch. Giữ bản checkpoint/handoff SESSION-02, không sửa lịch sử thành pass.
- Final code kiểm lại: 1.894 BE/107 UI đạt, 13 warnings deprecation (không giấu warnings), Ruff/63 JS/build/diff đạt. Inventory: 141 BE files/50.202 dòng, 62 JS tự viết/15.684, CSS+HTML 9.120, 121 BE test files/23.712, 32 browser files/3.217; LOC không là tiến độ.
- Kiểm trước stage: 155 text files thay đổi/new không trúng mẫu private-key/GitHub-cloud-token/JWT/customer identifiers được quét. Đây là kiểm tra có giới hạn, không chứng nhận secret/security tuyệt đối. Ảnh mới riêng không nằm repository; 3 ảnh minh họa installation type từ lượt trước được giữ là static illustration, không telemetry.
- User cho phép commit/push nhánh hiện tại rồi dừng. Kết quả commit/push phải đọc từ Git/remote receipt; **entry này viết trước push, không giả định push thành công**. Nếu bị gián đoạn, kiểm HEAD/status/remote trước khi commit/push lại. Không force push hoặc tự giải conflict remote bằng overwrite.
- Không sửa adapter/hardware/EMS trong lượt đánh giá này; không phát lệnh thật. Không tiếp tục phát triển hoặc QA sau publish nếu chưa có lệnh mới. Bước kế tiếp nằm tại checkpoint đầu file.

---

Ngày đối chiếu: 04–05/10/2026. Phạm vi: Deye, Solis, GoodWe, Growatt, Sungrow, Huawei, SOLARMAN, Bluesun, Eybond/SmartESS. Đọc cùng [kiểm toán lớp tích hợp](vendor-interface-audit-2026-10-05.md) và [hướng dẫn xin quyền API](vendor-api-access-guide-vi.md).

Cập nhật kế hoạch **07/10/2026**: [Phần II — phương án theo từng hàm, điều kiện dùng chung và tiến độ](#interface-plan) được lưu trực tiếp trong file này. Nghiên cứu hãng mang ngày kiểm chứng từng mục; một lát cắt I1/I2 SEMS+ đã được triển khai thử nghiệm như dưới đây, không phải toàn bộ kế hoạch đã hoàn thành.

### Tiến độ I1/I2 qua tài khoản thật — 08/10/2026

**Phát hiện tiếp theo từ phản hồi “Tổng quan chưa lên số”:** native inspector không
phải dashboard integration. Có API station flow/statistics mà connector đã bỏ sót.
Lát cắt mới (kiểm thử/QA xem evidence cùng ngày):

| Hàm / owner | Phương án đã viết | Giới hạn còn giữ |
|---|---|---|
| `StationReport`, `ReportedEnergy`, `StationReportReader` | Interface giám sát tùy chọn: power, calendar periods, daily energy, clock nguyên bản, evidence | Hãng không hỗ trợ không bị ép implement; không thay canonical measurements |
| `GoodWePlus.station_report`, `energy_rows` | Station flow; daily/month/year statistics, kW→W và dấu grid/battery ở adapter, dated kWh rows | Không pAc→PV; không suy timezone, không cộng inverter; lỗi/quota giữ riêng |
| `Controller.poll/reported_station` | Lưu cùng owner; context guards; tối đa một station report/chu kỳ; bỏ cache 15 phút, theo nhịp tài khoản (SEMS+ 60s nếu không có policy chậm hơn); kiểm enabled/binding/credential revision khi đọc | Receipt không là source timestamp; không cấp quyền ghi; snapshot cũ có nhãn; xoay vòng/quota có thể tăng độ trễ |
| `OperationalViews.overview`, fleet API | Trả kênh vendor_report riêng, scope cùng site | Không ghi sample GOOD hay dùng làm đầu vào EMS/billing |
| `vendor-report.js`, site/fleet overview, reports, energy-flow | KPI số hãng báo cáo, chart điện năng ngày từ response, clock/receipt/quality rõ; shared UI | Không giả đồ thị công suất theo giờ, không motion khi time unverified; exports verified chưa gộp report hãng |

Tiếp tục: power-history contract + timezone từ nguồn đáng tin; alarm history; UI các
owner thiết bị/map/data/EMS; exports có provenance. Không tuyên bố tất cả màn đã lên số.

### Đối chiếu 11 ảnh GoodWe người dùng gửi ngày 08/10 — không phải style thay thế

Ảnh portal là bằng chứng chức năng; giữ design system SolarOne và mock gốc. Không
chép số trong ảnh hoặc coi nút trên portal là quyền commissioning. Hai biến tần có
serial, công suất và bộ đếm riêng, không lấy station report gán vào từng thiết bị.

| Nhóm trong ảnh | Owner/hàm và phần đã nối | Còn thiếu / hướng xử lý |
|---|---|---|
| Tổng quan nhà máy: PV, grid, load, pin, sản lượng | `GoodWePlus.station_report` → `StationReport` → scoped store/API → fleet/site/reports; live 6 KPI, 8 ngày trong tháng | Source timezone, historical power curves, verified topology; chẩn đoán “xuất sắc”, doanh thu và cây xanh không giả định |
| Riêng mỗi biến tần: AC, công suất định mức, DC, nhiệt độ | `device_report` → `MeasurementObservation.reported: DeviceReport` → latest/equipment → shared `deviceReportPanel` | Chưa model photo chính xác; chỉ icon SVG. AC không đổi tên thành PV. Raw units/identity bắt buộc, không trộn 2 máy |
| Điện năng phát/sạc/xả ngày/tuần/tháng/năm/tổng | `latest` đọc telecounting riêng từng INVERTER; `DeviceEnergyReport`; UI chọn kỳ trong chi tiết và realtime | Kỳ do hãng định nghĩa, chưa source clock/TZ. Không dùng làm billing; chưa daily history per device |
| Pin riêng từng inverter: SOC/power/trạng thái | Related inventory có quan hệ, native inspector hiện dữ liệu đã đọc | Không lấy SOC toàn trạm cho từng pin; cần unit/sign/source-time của đúng BATTERY_BANK/BAT_SYS và mapping parent |
| AC-port, load limit, ba nhóm tháng/ngày/giờ, chế độ chuẩn/thông minh | Chưa triển khai đầy đủ GoodWe read/config/write | Giữ native capability; không ép thành lịch TOU phổ quát. Cần schema/range/enum/readback, conflict và thời gian bằng nhau |
| Backup/EPS, precision detection, first/retained cold start, load recovery | Chưa có hợp đồng và commissioning cho tài khoản/model này | Chỉ phần có semantics chung mới ánh xạ intent; cold start/recovery để native, cần quyền thử riêng |
| Self-use/backup/TOU/peak-shaving/smart-charge | Portal quan sát được; command engine chung có guard nhưng GoodWe chưa accepted | Đọc current/config trước; không đổi switch thành lệnh SET_WORK_MODE chung khi hãng dùng mode phối hợp |
| Bật/tắt, remote-grid dispatch | Chưa implemented/accepted ở SEMS+ | Không gửi lệnh từ screenshots hoặc bỏ gate, cần tác động/phạm vi và xác nhận kiểm thử riêng |
| Vòng trạng thái hoạt động 24 giờ | Chưa ingest lịch sử trạng thái GoodWe | Không tính uptime từ receipt hoặc hTotal; cần interval/event contracts, timezone/gap/unknown |
| Biểu đồ điện năng tuần từng inverter | Bộ đếm kỳ hiện có, chart theo ngày chưa nối | Nghiên cứu equipment statistics; một đường trên đúng serial, không station-history fallback |
| MPPT nhiều trục kW/A/V và AC/DC/pin/SOC historical | Native factors và khung observation/history hiện có; chưa vendor backfill | Factor IDs được hãng trả; đọc lịch sử, đơn vị/trục đúng, source time; không tạo sóng giả hoặc dùng receipt làm thời gian đo |

`DeviceReport` là phần tùy chọn của interface đọc chung, không vendor branch trong
core. Decoder GoodWe sở hữu key/unit; core kiểm serial và binding, không dùng report
cho điều khiển, GOOD samples hoặc billing. Các hãng khác có thể cấp hợp đồng này khi
có bằng chứng; chức năng riêng không bị ép đồng nhất.

- `GoodWePlus.read/latest`: đã tái hiện và sửa envelope thành công không có `data`
  ở telemetry DATA_LOGGER/BATTERY_BANK; giữ sample hợp lệ của inverter/meter trong cùng
  lượt đọc. Không mở rộng ngoại lệ sang discovery/inverter/error, không trả số 0 giả.
- `OperationalViews.equipment`: sửa chỗ còn boolean hóa UNKNOWN, thêm reading_summary
  tách số thông số đã nhận và số đã xác minh; cảnh báo thiếu độ phủ không trả 0 hardcoded.
- `nativeReadingsPanel`: interface hiển thị chung cho mọi adapter dùng native dataList,
  metadata alias/group, bộ lọc/tìm kiếm, ẩn code mặc định; giữ raw unit, missing và clock.
  Bản dịch nhãn không là telemetry mapping hoặc commissioning.
- Live hk: một plant, sáu inventory objects; sau rotation có sáu snapshots, ba có dữ liệu,
  220 native points. UI thật hiển thị 98 trên inverter, 24 trên meter và giải thích logger
  không có số đo. I1/I2 **partial live-read demonstrated**, không full support.
- Quan sát bổ sung panel work-mode: self-use/backup/TOU/peak shaving/smart charging và
  nhãn mode hiện hành. Không thao tác switch/submit, không biết command/readback contract.
  Giữ native riêng khi semantics chưa thống nhất; không ép thành SET_WORK_MODE dùng chung.
- I2 còn source-time/model/firmware/unit-sign/battery identity; I3 alarms/history và I4+
  control/readback vẫn mở. Bước tiếp theo là contract nghiên cứu/QA đọc theo phạm vi,
  không bỏ các gate để làm dashboard trông có số. Xem [bằng chứng](evidence/goodwe-live-read-ui-2026-10-08.md).

### Tiến độ I1/I2 SEMS+ — sau baseline portal, 07/10/2026 (lịch sử)

- `GoodWe.__new__` chọn classic/SEMS+ theo platform trong cùng plugin; không tạo vendor,
  controller hoặc menu cạnh tranh.
- `GoodWePlus.authenticate/headers/read`: email/mật khẩu, vùng tường minh, allowlist,
  đồng ý điều khoản, shared budgets/transport guards; không tái dùng phiên browser.
- `GoodWePlus.stations/devices/latest`: discovery phân trang, typed inventory và quan hệ
  thiết bị do hãng trả về; native factor/unit/zero/null. Không đoán model, dấu hoặc timestamp.
- `DeviceObservation/MeasurementObservation/Device` và các nơi hiển thị đã nhận connectivity
  ba trạng thái; GoodWe không còn bị gộp thiếu trạng thái thành offline. Chưa xác minh enum hãng.
- `install_goodwe_connection`: xác thực trước khi lưu vault, org-admin/CSRF/session/revision,
  reconnect và lỗi đã loại bí mật. Form SEMS+ riêng trong màn Tài khoản hiện hữu.
- Đã viết contract BE/FE synthetic, đang ghi kết quả ở
  [evidence connector](evidence/goodwe-semsplus-connector-2026-10-07.md).
  Q1-portal đã quan sát; Q1-connector/live chưa nghiệm thu. I3 alarms/history, source timestamps,
  canonical units/sign, exact identity và quyền ghi vẫn mở. Không mở capability bằng fixture.

UI toàn 26 màn vẫn cần nghiệm thu pixel/accessibility; các panel EMS chuyên sâu, nested rules,
  network executors và auto model mapping không được gọi là chỉ chờ tài khoản.

## Kết luận cho chủ sản phẩm

Có. Các nền tảng hãng còn có các nhóm sâu hơn SolarOne: chẩn đoán thiết bị, quy trình dịch vụ/bảo hành, quản trị nhà phân phối, thiết kế dự án, điều phối tải và kết nối thị trường. SolarOne đã có nền móng giám sát, lịch, cảnh báo, báo cáo, công cụ tính toán và điều khiển có cổng an toàn; **không có nghĩa các nhóm này đã chạy end-to-end cho mọi hãng**.

Ảnh Growatt là giao diện OSS dành cho tổ chức/đơn vị lắp đặt, không chỉ giao diện chủ nhà. Không nên đưa toàn bộ sidebar này vào màn hình của người dùng thông thường.

Đây là danh mục toàn bộ nhóm chức năng nhận diện được trong nguồn công khai đã kiểm tra, **không phải cam kết đã thấy mọi menu ẩn theo tài khoản, quốc gia, gói dịch vụ và firmware**. Ở baseline nghiên cứu 04–05/10 chưa dùng tài khoản thật; QA GoodWe 07–08/10 được cập nhật riêng phía trên. Không có dữ liệu mẫu từ tài liệu được đưa vào ứng dụng.

### Cách đọc bằng chứng

- **API:** tài liệu hãng mô tả interface; còn phải xin đúng quyền và nghiệm thu hợp đồng thực tế.
- **UI:** tài liệu hướng dẫn portal/app mô tả chức năng; chưa đủ bằng chứng API cho bên thứ ba.
- **Sản phẩm:** trang hãng giới thiệu; chưa xác nhận chi tiết triển khai, quyền hoặc SLA.
- **Lịch sử:** có trong manual cũ; phải kiểm lại trên sản phẩm hiện hành trước khi phát triển.
- **Chưa rõ:** chỉ thấy tên menu/branding; không suy diễn chức năng hoặc hỗ trợ API.

Trong backlog: **M** = SolarOne có một phần/khung; **C** = chưa thấy workflow end-to-end trong code đã khảo sát; **T** = có công cụ thuần nhưng chưa vận hành tích hợp; **K** = cần xác minh thêm. “C” không phủ nhận có helper cùng tên ở nơi khác.

## 1. Deye

Nguồn: [Open MCP/API tools chính thức](https://developer.deyecloud.com/openmcp/docs/deye-open-mcp-tools.html), [developer portal](https://developer.deyecloud.com/). Nhóm API đã thấy:

- Nhà máy: danh sách, thiết bị thuộc trạm, số đo hiện tại và lịch sử.
- Thiết bị: danh mục cấp tài khoản doanh nghiệp; thêm logger; đăng ký/gắn thiết bị theo hợp đồng endpoint.
- Cấu hình pin và chế độ vận hành; lịch nhiều khung giờ, thông số sạc/bán điện, máy phát theo model.
- Lệnh bất đồng bộ và truy vấn kết quả theo order ID.
- Giao diện MCP phục vụ ứng dụng/trợ lý bên ngoài.

**Khoảng cách:** discovery/latest đã có đường chung; history native chưa là kho lịch sử chuẩn hóa. Quản lý vòng đời logger phía hãng và trợ lý MCP chưa là workflow sản phẩm. Có compiler/control guard không chứng minh đã nghiệm thu model. Thêm logger/đổi liên kết là mutation quyền sở hữu, không phải thao tác “quét” vô hại. MCP không thay quyền ứng dụng hay quyền khách hàng.

## 2. Solis / SolisCloud

Nguồn API: [Data Access — User Auth](https://developer.soliscloud.com/guide/data-access-user.html), [ủy quyền](https://developer.soliscloud.com/guide/authorization.html). Danh mục có inverter, collector, EPM, weather station, ammeter; dữ liệu ngày/tháng/năm/tổng, báo lỗi, bảo hành và lịch sử tín hiệu collector. API có quy tắc phân trang riêng; không dùng giả định `total` thông thường cho mọi endpoint.

Nguồn UI: [FAQ O&M](https://doc.soliscloud.com/en/10.FAQ/04.O%26M%20Related%20Concerns.html) mô tả I‑V/string dispersion. [Manual V1.0](https://www.soliscloud.com/SolisCloud%20Operation%20Manual-UserV1.0.pdf), đặc biệt phần tools/settings, còn mô tả message center, logger chưa gắn, chuyển dữ liệu hệ cũ, cấu hình Wi‑Fi/QR và kết nối cục bộ. Đây là manual cũ, không chứng minh mọi bước còn nguyên ở bản hiện tại.

**Khoảng cách:** SolarOne có discovery/latest và một số hàm history/alarm riêng nhưng registry chưa nối chúng như năng lực chung. Chẩn đoán I‑V, quản lý EPM/weather/logger sâu, kho logger và commissioning trên điện thoại chưa hoàn chỉnh. Nhánh OAuth trong code cần đối chiếu lại customer consent; không chỉ đổi nhãn form là xong.

## 3. GoodWe / SEMS+

**QA portal 07/10/2026:** người dùng đã đăng nhập SEMS+; [baseline đã loại định danh](evidence/goodwe-portal-qa-2026-10-07.md)
ghi inventory inverter/logger/meter, timestamp, alarm recovery khác acknowledgment và
menu phân tích/báo cáo. Chưa phải Q1 connector. Logger có các mục EMS riêng: không chuyển
control scope sang inverter chỉ vì cùng nhà máy. `GoodWe.latest` đã bỏ online cố định;
connectivity ba trạng thái vẫn là việc I2. Nguồn MIT gateway SEMS+ đã ghim revision trong
evidence; chưa import và chưa thử credentials bằng adapter.

Nguồn: [SEMS+ product](https://en.goodwe.com/semsplus-series-smart-energy-management-system), [SEMS+ Web manual V1.2, 20/09/2026](https://cz.goodwe.com/Ftp/EN/Downloads/User%20Manual/GW_SEMS-PLUS-WEB_User-Manual-EN.pdf). Đã xem mục lục PDF trang vật lý 4–6 và các nhóm tương ứng:

- Dispatch center, luồng quản lý thông minh, kiểm tra sức khỏe nhà máy.
- I‑V: thông tin module/đấu nối, tác vụ quét/chẩn đoán.
- So sánh dữ liệu và phân tích độ đồng đều pin.
- Báo cáo nhà máy/thiết bị, đăng ký nhận báo cáo, kho báo cáo cá nhân.
- Nâng cấp thiết bị; cấu hình inverter, battery, meter và communication stick theo quyền.
- Tổ chức, quyền giám sát, đăng ký thông báo, nhật ký; thông tin bảo hành và tài liệu.
- Trợ lý AI.

Trang sản phẩm còn giới thiệu điều phối inverter/EV/heat pump/smart load, giá điện động, commissioning theo lô, tích hợp thiết bị phụ trợ, MFA và truy vấn bằng ngôn ngữ tự nhiên. Đây là **UI/sản phẩm**, không xác nhận tất cả được mở qua API hoặc tại Việt Nam. Thông điệp tốc độ cập nhật không phải quota/SLA API.

**Khoảng cách:** connector hiện tại vẫn mang hợp đồng SEMS legacy, không đủ để tuyên bố SEMS+ đã hỗ trợ. Các helper/parser GoodWe không thay thế xác thực/discovery/telemetry thật. AI, I‑V, battery consistency, báo cáo định kỳ và điều phối đa tải còn thiếu đường vận hành đầy đủ.

## 4. Growatt / OSS / Shine

Nguồn: [Installer Operation Manual](https://cdn.growatt.com/pdf/Installer%20Operation%20Manual.pdf), 93 trang; đã đối chiếu mục lục, phần chức năng và xem hình trang vật lý 68, 86. Danh mục nhận diện:

- Thiết kế PV; quản lý nhà máy/người dùng/thiết bị, gồm lưu trữ và bộ sạc EV.
- Kiosk màn hình lớn, logo/video/bản đồ và thống kê luân phiên.
- Service Hall: yêu cầu đổi máy, duyệt/từ chối, gửi máy thay, thu hồi máy cũ, trạng thái bất thường.
- Ticket dịch vụ, phân công/theo dõi/đóng theo quyền tổ chức.
- Phân tích điện áp/dòng/công suất, cảnh báo và tổn thất sản lượng.
- Supply System: chức năng xác nhận được là tra bảo hành, thông tin đơn hàng/model/ngày giao.
- Đại lý, tổ chức, nhân viên/quyền và quản lý API/token/whitelist.

**Khoảng cách:** SolarOne chưa có thiết kế PV, RMA/thu hồi, tích hợp tra bảo hành, cây đại lý hay kiosk hoàn chỉnh. Incident/maintenance hiện tại chỉ là một phần, không thay thế toàn bộ dịch vụ hãng. API quản lý trên OSS không có nghĩa mọi menu đều được cấp API.

### Những gì chỉ nhìn thấy trên ảnh người dùng

`Traffic System`, `After-sales O&M`, `Operator Management`, `Problem Feedback`, `Investigation and Analysis`, `mail serve` là nhãn có trong ảnh. **Chưa xác minh toàn bộ nghiệp vụ từng nhãn**. Đặc biệt không kết luận Traffic System chắc chắn là quản lý SIM, hoặc Supply System là ERP mua bán hàng hóa. Manual chỉ chứng minh phần đã nêu. Các nhãn này nằm trong danh sách cần khảo sát bằng tài khoản đúng quyền, không được tính là tính năng API đã hỗ trợ.

## 5. Sungrow / iSolarCloud

Nguồn hiện hành: [Developer Portal](https://developer-api.isolarcloud.com/) công bố các nhóm API monitoring, grid control, MQTT/live data, cấu hình nhà máy, dự báo địa phương, giao dịch năng lượng động, dữ liệu/chẩn đoán sạc và tích hợp EMS. OAuth, node vùng và gói dịch vụ là điều kiện riêng.

Nguồn lịch sử: [O&M manual V14, 2018](https://img.isolarcloud.com/pdf/UserManual/iSolarCloud%20User%20Manual_en.pdf) có phiếu lỗi/sửa chữa, phân công và đánh giá, lịch trực/nhật ký/phiếu thao tác điện, vật tư/tài sản, video, tri thức lỗi, chẩn đoán dòng/string/I‑V, email báo cáo, module truyền thông và gia hạn dịch vụ. **Chỉ là ứng viên cần kiểm chứng trên phiên bản hiện hành**, không mặc định còn được cung cấp cho tài khoản chủ nhà.

Tìm thấy [manual V26, 2026-05](https://info-support.sungrowpower.com/product-materials/8cc7a6f7-36ff-4489-b9af-15546dc42ca2.pdf), nhưng chưa đọc đủ tài liệu lớn này; không dùng nó để xác nhận lại danh mục lịch sử.

**Khoảng cách:** adapter SolarOne chưa hiện thực đầy đủ các nhóm API hiện hành trên; MQTT/dự báo/VPP không đồng nghĩa các calculator EMS hiện có. Chưa có quy trình trực/vật tư/phiếu công tác và dịch vụ truyền thông tích hợp.

## 6. Huawei / FusionSolar

Nguồn: [Smart PV Management System](https://solar.huawei.com/en/products/smart-pv-management-system/), [Smart PV Plant Management System](https://solar.huawei.com/en/products/smart-pv-plant-management-system/), [Residential](https://solar.huawei.com/in/Products/FusionSolarResidential).

- Theo dõi cấp module/optimizer, bố trí vật lý, nhận diện và mapping thiết bị hỗ trợ.
- Điều phối năng lượng theo dự báo/giá/hành vi; ưu tiên tải, EV/heat pump và hệ sinh thái nhà thông minh.
- Chẩn đoán toàn tuyến, so sánh string, I‑V, hỗ trợ O&M và tác vụ hiện trường.
- Theo dõi plant/subarray/module; hệ sinh thái tích hợp ngoài và ứng dụng nhà máy lớn.

Đây chủ yếu là **sản phẩm/UI**; model, thị trường và giấy phép quyết định khả dụng. API northbound không tự động mở toàn bộ thuật toán, firmware hoặc tính năng điện an toàn.

**Khoảng cách:** SolarOne chưa có bản đồ module/optimizer và commissioning tương ứng; history/alarm có helper riêng nhưng chưa thống nhất registry; điều phối smart home và phân tích chẩn đoán sâu chưa thành workflow live.

## 7. SOLARMAN Smart / Business

Nguồn: [FAQ Business chính thức](https://protocol.solarmanpv.com/faq/business/faq_en.html), [brochure nền tảng](https://www.solarmanpv.com/wp-content/uploads/2022/07/SOLARMAN-Smart-Energy-Monitoring-and-Management-System.pdf), [account/capabilities](https://doc.solarmanpv.com/en/Public%20Information/12Account%20and%20Capabilities).

- Business mở rộng so với Smart: màn hình lớn, báo cáo/phân tích, thông báo, kế hoạch công việc và hồ sơ bảo trì.
- Brochure mô tả đánh giá dự án/tài nguyên PV, mô phỏng sản lượng và phân tích tài sản/tài chính.
- Giám sát nhiều loại thiết bị, cấu hình/cập nhật theo quyền và giải pháp quản lý năng lượng.
- Data center và chức năng cấp tài khoản cần kiểm tra riêng; không coi tài khoản vùng này tự truy cập được vùng khác.

**Khoảng cách:** không đồng nhất “SOLARMAN là transport” với “mọi inverter OEM có cùng control”. SolarOne có history/alerts helper nhưng chưa đăng ký vào đường chung. Project finance/kiosk/work-order đầy đủ chưa xây; capability API mở riêng không phải quyền mặc định của Smart.

## 8. Eybond / SmartESS / SmartClient

Nguồn: [Household energy storage](https://www.eybond.com/Household.html), [platforms](https://www.eybond.com/intelligent-monitoring-platforms/), [SmartESS guide](https://fms.eybond.com/fms/api/auth/web/doc/html/previewOnline/72/2).

- Giám sát, cảnh báo và quản lý thiết bị/OTA là nhóm sản phẩm công bố.
- SmartESS giới thiệu quản lý lưu trữ, điều phối theo giá và công suất.
- SmartClient/SmartValue hướng tới tài khoản tổ chức, tùy biến thương hiệu và giải pháp dữ liệu riêng.
- Hướng dẫn SmartESS có thêm thiết bị, thiết lập Wi‑Fi, xem dữ liệu cloud.
- SmartLamp là nhánh đèn đường, không phải chức năng mặc định của SmartESS.

**Khoảng cách:** DessMonitor/ShineMonitor adapter hiện chủ yếu là đường đọc. Không suy API điều khiển, OTA, giá điện hay white-label từ trang marketing. Chưa có local commissioning/điều phối điện được nghiệm thu cho toàn hệ sinh thái.

## 9. Bluesun: thương hiệu, không mặc định một nền tảng

Nguồn: [BSM-5500BLV-48DA manual V2.0](https://www.bluesunpv.com/wp-content/uploads/2024/11/BSM-5500BLV-48DA-User-Manual-V2.0.pdf), [battery catalogue](https://www.bluesunpv.com/wp-content/uploads/2024/09/BLUESUNESS-BATTERY-CATALOG.pdf). Manual model trên chỉ ra SmartESS và các lựa chọn truyền thông; điều này không chứng minh mọi Bluesun dùng cùng cloud.

**Khoảng cách cần phát triển:** nhận dạng brand/model/logger/platform đúng; hướng dẫn chọn ứng dụng; đối chiếu BMS, inverter và nguồn đọc theo profile. Chưa có bằng chứng một “Bluesun API” chung để liệt kê như nền tảng độc lập. Không dùng comment `BSE Cloud` hoặc thông số pin mặc định trong code làm bằng chứng hãng. Xem audit về lớp `BluesunAdapter` chưa nối registry.

## 10. Backlog hợp nhất, không nhân bản sidebar

Các dòng dưới là đề xuất phát triển SolarOne từ chênh lệch đã thấy, không phải tuyên bố mọi hãng đều có chúng. Một chức năng có thể cần nhiều hãng hoặc chỉ một extension. P1 trước pilot đọc ổn định; P2 sau pilot; P3 mở rộng sản phẩm; R chỉ nghiên cứu. P1 không đồng nghĩa cho phép phát lệnh thật.

| ID | Chức năng đích | Hiện tại | Owner trong SolarOne | Ưu tiên / điều kiện |
|---|---|---|---|---|
| F01 | Liên kết khách hàng qua consent, không lộ app secret | M | Tài khoản hãng | P1: tenant/grant/revoke |
| F02 | Tự nhận diện nền tảng/vùng với lựa chọn người dùng xác nhận | M | Tài khoản hãng | P1: không đoán từ logo |
| F03 | Công bố capability theo account/model/firmware | M | Thiết bị / model | P1: profile có bằng chứng |
| F04 | Phân trang/discovery đầy đủ, quota và resume | M | Nguồn dữ liệu | P1: contract từng API |
| F05 | Lịch sử hãng vào schema chung và backfill | M | Lịch sử / nguồn | P1: time/unit/provenance |
| F06 | Alarm hãng thành incident thống nhất | M | Cảnh báo | P1: decoder và recovery |
| F07 | Đối chiếu timestamp/freshness giữa cloud và local | M | Nguồn dữ liệu | P1: không tạo measured giả |
| F08 | Gắn/tháo/chuyển thiết bị phía hãng | C | Liên kết thiết bị | P2: consent/ownership riêng |
| F09 | QR và provisioning Wi‑Fi/Bluetooth | C | Liên kết / mạng | P2: SDK/transport chính thức |
| F10 | Danh mục logger chưa gắn | C | Thiết bị | P2: API inventory |
| F11 | Loại trùng cùng thiết bị qua nhiều nguồn | M | Nguồn / thiết bị | P1: identity proof |
| F12 | Sơ đồ truyền thông có cạnh quan sát được | M | Mạng | P2: không suy đấu dây |
| F13 | Tín hiệu logger và lịch sử mất kết nối | M | Mạng | P2: RSSI/source-time |
| F14 | Module truyền thông, hạn dịch vụ và gia hạn | C | Mạng / vận hành | R: hợp đồng dịch vụ |
| F15 | Đo AC theo pha, DC theo string/MPPT | M | Giám sát thiết bị | P1: mapping/unit đúng |
| F16 | Lưu trữ dài hạn, rollup và so sánh nhiều trạm | M | Lịch sử / báo cáo | P2: retention/load |
| F17 | Bản đồ vật lý panel/optimizer | C | Nhà máy / thiết bị | P2: model hỗ trợ |
| F18 | Tác vụ quét I‑V và đường cong/kết luận | C | Chẩn đoán | P2: quyền scan, safety |
| F19 | Độ phân tán string, lệch dòng/áp | T | Chẩn đoán | P2: đo đồng bộ, baseline |
| F20 | Độ đồng đều cell/module pin | C | Giám sát pin | P2: BMS/cell contract |
| F21 | Sức khỏe nhà máy và tổn thất có nguyên nhân | M | Cảnh báo / analytics | P2: model giải thích được |
| F22 | Trạm thời tiết, irradiance và PR chuẩn | M | Nguồn / báo cáo | P2: cảm biến/đơn vị |
| F23 | EPM/meter như thiết bị độc lập | M | Thiết bị | P2: discovery/type mapping |
| F24 | Báo cáo riêng từng loại thiết bị | M | Báo cáo | P2: schema theo loại |
| F25 | Đăng ký báo cáo định kỳ và giao nhận | C | Báo cáo | P2: executor/retry/delivery |
| F26 | PDF, mẫu báo cáo thương hiệu | M | Báo cáo | P2: export có provenance |
| F27 | Kiosk màn hình lớn | C | Tổng quan | P3: quyền public/redaction |
| F28 | Cảnh báo push/email đa kênh | M | Cảnh báo / cài đặt | P2: delivery thật |
| F29 | Ticket dịch vụ, phân công, follow-up | M | Vận hành | P2: lifecycle/SLA |
| F30 | Bảo hành theo SN, ngày giao, quyền hãng | C | Hồ sơ thiết bị | P2: API/nguồn được phép |
| F31 | RMA, máy thay thế và thu hồi máy cũ | C | Bảo trì | P3: serial lineage |
| F32 | Kho vật tư/phụ tùng và lịch sử sử dụng | C | Vận hành | P3: tồn kho/audit |
| F33 | Lịch trực, phiếu công tác/thao tác điện | C | Vận hành | R: quy trình an toàn riêng |
| F34 | Tri thức lỗi/tài liệu gắn exact model | M | Cảnh báo / trợ giúp | P2: nguồn/version |
| F35 | Ảnh/video hiện trường theo sự cố | C | Vận hành | P3: privacy/retention |
| F36 | Firmware OTA thật và kết quả phục hồi | M | Bảo trì | P2: chữ ký/rollback/hardware |
| F37 | Cấu hình native theo schema của model | M | Điều khiển nâng cao | P1: read-only trước |
| F38 | TOU đúng slot/timezone/enum từng model | M | Lịch TOU | P1: compiler/readback |
| F39 | Lệnh theo lô, canary và dừng an toàn | M | Triển khai hàng loạt | P2: không bỏ command engine |
| F40 | Giám sát/điều phối EV charger | T | Thiết bị / EMS | P2: không coi calculator là driver |
| F41 | Heat pump/heater/smart load | T | EMS | P2: adapter và constraints |
| F42 | Generator/ATS/EPS theo capability độc lập | T | Điều khiển nâng cao | P2: không gom thành một toggle |
| F43 | Dự báo tải/PV/thời tiết với sai số | M | EMS | P2: dữ liệu/coverage |
| F44 | Giá điện động và tối ưu có giới hạn | T | EMS / biểu giá | P2: feed/currency/timezone |
| F45 | VPP/DR và giao dịch/settlement | T | EMS / thị trường | P3: hợp đồng vùng/pháp lý |
| F46 | MQTT/live streaming theo gói API | C | Nguồn dữ liệu | P2: quota/reconnect/dedup |
| F47 | Thiết kế dự án PV và phương án công suất | C | Kế hoạch dự án | P3: tách khỏi vận hành |
| F48 | Dự toán đầu tư, hoàn vốn, cashflow | T | Báo cáo / dự án | P3: declared assumptions |
| F49 | Cây tổ chức/đại lý/installer và chia sẻ trạm | M | Người dùng | P2: tenant isolation |
| F50 | MFA/SSO và quản lý phiên nâng cao | C | Bảo mật | P1: trước SaaS rộng |
| F51 | Quản lý ứng dụng, grants, quota và whitelist | M | Quản trị tích hợp | P1: admin-only |
| F52 | Tùy biến nhãn hiệu/cổng khách hàng | C | Tổ chức | P3: không fork stylesheet |
| F53 | Di chuyển dữ liệu từ hệ thống cũ | C | Nguồn dữ liệu | P3: license/consent/dedup |
| F54 | AI hỏi đáp số liệu có trích nguồn | C | Trợ giúp / analytics | P3: read-only/scoped |
| F55 | MCP/tools an toàn cho hệ bên ngoài | C | API platform | P3: không bypass permission |
| F56 | “Traffic”, mail/service/feedback Growatt sâu | K | Chưa gán | R: xác minh nghiệp vụ trước |
| F57 | Nhận dạng và onboarding OEM Bluesun | M | Liên kết thiết bị | P1: brand ≠ platform |
| F58 | Mở rộng street-light/drone ngoài PV lõi | C | Ngoài release đầu | R: nhu cầu và hợp đồng riêng |

## 11. Thứ tự nên làm

1. **Đạt pilot đọc tin cậy trước:** tài khoản, phạm vi khách hàng, discovery, số đo/chất lượng, history/alarm, UI trống và lỗi. Không cần xây 58 mục mới trước khi kiểm thử tài khoản.
2. **Chủ nhà trước, kỹ thuật viên theo vai trò:** tổng quan, thiết bị, cảnh báo, lịch, báo cáo và hướng dẫn liên kết. Native fields/phiếu vận hành để trong vùng chuyên sâu có giải thích.
3. **Hoàn thiện nhóm có doanh thu/nhu cầu rõ:** báo cáo định kỳ, bảo trì, bảo hành, so sánh hiệu suất; không sao chép sidebar hãng.
4. **Điều khiển/OTA/VPP sau:** exact-profile acceptance, quyền riêng, readback và phục hồi. Backend công bố năng lực thực sự; UI chỉ hiển thị đúng trạng thái đó.

Mỗi mục được chọn cần tài liệu endpoint/quyền, schema, owner chung, bài test lỗi/scope/time/unit và tiêu chí nghiệm thu. Có API, có tên class hoặc có mockup đều chưa là hoàn thành.


<a id="interface-plan"></a>

## Phần II — Kế hoạch thực thi interface theo từng hàm

Cập nhật tài liệu **07/10/2026** từ nghiên cứu và code snapshot ngày 05/10/2026. Trạng thái: **KẾ HOẠCH, CHƯA TRIỂN KHAI**. Không coi ngày cập nhật này là ngày đã xác minh lại mọi website hoặc mọi hàm.

Phạm vi code khảo sát: nhánh `fix/real-data-engine-integration`, HEAD `af4f1b8ab70d91e24ca0b44bc8b71d1c9f274be0` cùng worktree chưa commit. Đọc cùng [audit interface](vendor-interface-audit-2026-10-05.md). Phần I phía trên giữ nguyên nghiên cứu hãng và 58 hạng mục; phần II quy định cách triển khai sau UI và baseline QA.

## 12. Quyết định kiến trúc

**Hoàn thiện `IntegrationRegistry` / `IntegrationPlugin` đang phục vụ controller, không dựng một hệ `Unified*` thứ ba.** “Một interface chung” là một điểm vào nghiệp vụ nhất quán, không phải một class khổng lồ buộc mọi hãng implement mọi hàm.

Tách ba trách nhiệm:

1. **Dịch vụ chung:** kiểm quyền, quản lý nguồn, lịch sử, tính toán, kế hoạch lệnh, audit. UI gọi dịch vụ này.
2. **Các hợp đồng năng lực nhỏ:** discovery, telemetry, history, alarms, configuration, command transport, schedule compiler; chỉ đăng ký năng lực thực sự có.
3. **Adapter/profile hãng:** endpoint, xác thực, đơn vị, enum, thanh ghi, giới hạn, cách đọc kết quả. Chức năng đặc thù ở extension có namespace, không rải nhánh `if vendor` trong UI/core.

```text
UI / API / tác vụ nền
        │ cùng quyền, scope, revision, audit
        ▼
Dịch vụ tích hợp chung + capability resolver
        ├── Năng lực đọc → adapter/profile → quan sát → store
        ├── Tính toán dùng lại → dữ liệu chuẩn có provenance → kết quả dẫn xuất
        ├── Ý định ghi → CommandEngine → compiler → transport → readback
        └── Extension đặc thù → schema/quyền riêng → cùng guards/lifecycle
```

Không ép cloud/local dùng cùng cách xác thực. Không ép có hàm `stations()` cho thiết bị local độc lập chỉ để vừa interface. Có thể chung **kết quả discovery và identity**, khác cơ chế discovery.

## 13. Thứ tự và các cổng bắt buộc

### U — Xử lý UI còn tồn đọng trước

Tiến độ U ngày 07/10: [UI xem/so sánh số đo](evidence/ui-observation-inspector-2026-10-07.md) tiếp tục với [EMS, network và biểu đồ chuyên sâu](evidence/ui-deep-workspaces-2026-10-07.md): schema hành động theo thiết bị, giữ nguyên tham số legacy, directory/inspector/dry-run ba cột, topology cấu hình khai báo, bốn khung quan sát chọn kênh và lớp bản đồ. Chưa đóng U/F15 hoặc pixel acceptance; nested OR, mapping tự động exact model và executor mạng vẫn mở. Chưa Q1 end-to-end SolarOne hay refactor I0–I6. QA portal hãng chỉ đọc, nếu người dùng đăng nhập, phải ghi riêng với nghiệm thu connector.

Đóng theo 26 màn hình/15 owner trong [mockup coverage](mockup-coverage.md): layout, typography/spacing, chart đúng kênh, lịch TOU trống, form dễ hiểu, mobile, bàn phím, VI/EN, empty/loading/error/unknown/locked. Không dùng seed và không yêu cầu dữ liệu khách hàng để dựng layout. Lưu ảnh đối chiếu và danh sách khác biệt, không dùng số test/LOC để kết luận pixel-perfect.

### Q0 — Điều kiện tối thiểu trước khi nhờ người dùng đăng nhập

Đây là ngoại lệ nhỏ cần làm **trước QA**, không phải đẩy toàn bộ refactor lên trước UI:

- Xác định đúng nền tảng/vùng/account mode; giải quyết prerequisite Deye và contract GoodWe tương ứng. Nếu chưa có đường xác thực phù hợp, báo chưa sẵn sàng, không dùng mật khẩu để dò endpoint.
- Kiểm vault/redaction, session/scope/revision, callback allowlist nếu có OAuth, quota và tắt mọi electrical write trong phiên QA.
- IA-03 phải được khoanh không thể dùng trong QA; nếu phát hiện facade lỗi nằm trên đường thử thì sửa/regression trước. Không cần chuyển production sang facade đó.
- Nút login/test phải thông báo đúng phạm vi: xác thực, khám phá, đọc; không ngầm thay config thiết bị hoặc binding phía hãng.

### Q1 — Người dùng đăng nhập, QA chỉ đọc

Checkpoint 07/10: **Q1-portal đã quan sát; Q1-connector chưa chạy**. Xem [evidence](evidence/goodwe-portal-qa-2026-10-07.md).
Không còn yêu cầu người dùng nhận diện app chỉ từ logo: phiên vừa kiểm tra là SEMS+.
Việc cần làm là SEMS+ transport/typed discovery và common UNKNOWN connectivity, không
phải bắt người dùng xin một App Secret chưa có bằng chứng cần cho luồng này.

Người dùng tự nhập trên UI, không gửi secret trong chat. Ghi bảng kết quả đã khử định danh: platform/region/account role; app grant; model/logger/firmware; tập trạm/thiết bị; timestamp/unit/sign; history/alarm/config-read được phép; lỗi/quota quan sát được. “Chưa gặp lỗi” không là “đã test lỗi”. Kiểm logout/revoke ở SolarOne, không tự thu hồi tài khoản hãng hay cố tình vượt quota/khóa tài khoản.

- Đối chiếu trạm và thiết bị với app hãng; tài khoản thành công nhưng không có nhà máy là trạng thái hợp lệ, không tạo nhà máy mẫu.
- Lưu contract fixture tổng hợp, đã loại secret và định danh; không commit raw payload, cookie hoặc ảnh khách hàng.
- Phân loại mismatch thành auth, quyền, discovery, semantics, timestamp, UI hay unavailable.
- Kết quả **blocked một hãng không chặn cả chương trình**. Ghi blocked, dùng hãng đọc được để pilot interface; không bịa kết quả cho hãng còn lại.

### I — Thực hiện kế hoạch hàm bên dưới, sau U và kết luận Q1

Thứ tự I0 → I1 → I2 → I3 → I4 → I5 → I6. Sửa nhỏ cần cho Q0 không tự cho phép refactor toàn bộ trước U. Khi refactor xong phải **QA hồi quy lần nữa (Q2)**; QA trước sửa chỉ là baseline, không là nghiệm thu code sau sửa.

## 14. Khi nào đưa vào chung, khi nào giữ riêng

| Loại | Điều kiện | Ví dụ | Không được làm |
|---|---|---|---|
| **N — Native chung** | Cùng nghĩa, cùng đối tượng, chuyển đơn vị/time/enum chính xác | Danh sách thiết bị, SOC có unit đúng | Coi hai field giống tên là cùng nghĩa |
| **E — Chuyển đổi tương đương** | Chứng minh bảo toàn nghĩa và giới hạn, công khai conversion | kW → W; history chia ngày theo timezone; gộp hai TOU slot liền kề hoàn toàn giống nhau | Làm tròn/tự kẹp giá trị để âm thầm vừa thiết bị |
| **D — Dịch vụ dẫn xuất** | Đủ dữ liệu đầu vào có nguồn, chất lượng/coverage; có công thức/version | Lịch sử từ kho đã thu, cảnh báo do SolarOne tính, report/savings ước tính | Gọi là alarm hãng hay measured/native history |
| **X — Đặc thù** | Có giá trị nhưng không thể đồng nhất nghĩa | I‑V scan, RMA, grid-code, firmware | Ép thành generic toggle hoặc bypass engine |
| **U — Không hỗ trợ / chưa rõ** | Thiếu API, dữ liệu, quyền hoặc bằng chứng | Không có cell voltage thì không phân tích cell consistency | Trả thành công rỗng, 0, đoán register, retry ghi qua đường khác |

Quy trình quyết định cho **mỗi hàm**: xác định nghĩa/đơn vị/đối tượng → kiểm native → kiểm chuyển đổi E → kiểm khả năng tính D → nếu đặc thù có nhu cầu thì X → còn lại U. Quyết định theo account/model/firmware/transport, không chỉ theo hãng.

**Quy tắc fallback:** chọn nguồn/strategy rõ trong plan; không đổi transport sau lỗi auth/permission hoặc sau khi đã gửi lệnh. Local fallback cần enrollment và quyền local đã cấp; việc có cloud account không cho phép quét LAN. Với write bị timeout, giữ outcome unknown/quarantine; tuyệt đối không thử lại bằng hãng/protocol khác.

## 15. Hợp đồng kết quả cần chuẩn hóa

Các tên mới bên dưới là **đề xuất**, chưa tồn tại trong code. Ưu tiên đặt phần khai báo trong `integration.py`; chỉ tách module dịch vụ khi trách nhiệm rõ, không tạo controller thứ hai.

| Hợp đồng | Nội dung bắt buộc |
|---|---|
| `CapabilityDescriptor` | `operation`, `support` N/E/D/X/U, implementation status, account grant, identity/profile match, read/write, execution readiness, reason VI/EN, schema/range/step/unit, evidence, limits, coverage; không gom mọi thứ thành boolean |
| `OperationContext` | principal/session revision, site/device/binding, integration/credential/profile revision, deadline/budget, request ID; giải quyết phía server, không tin identity do client gửi |
| `DeviceRef` | ID nội bộ, vendor resource ID, station/device type, brand/platform/model/logger/firmware; chưa đủ identity thì unknown |
| `ObservationBatch` | source timestamp khác received_at; native/canonical tách, unit/sign/quality, source/binding/evidence; online là trạng thái có nguồn, không suy từ HTTP 200 |
| `HistoryQuery/Page` | target loại station/device, aware UTC `[start,end)`, timezone lịch, metric, resolution, cursor; points/aggregates tách, coverage/gaps/partial, provenance |
| `AlarmPage` | namespace + alarm ID, device/site, xảy ra/cập nhật/phục hồi, severity mapping, cursor, snapshot completeness; thiếu recovery không tự đóng |
| `ConfigurationSnapshot` | field schema/value/unit, source time/age, quyền đọc, revision/digest, observed/declared; field bị ẩn không dùng default |
| `DerivedResult` | công thức/version, IDs đầu vào, khoảng thời gian/coverage, assumptions, estimate/derived; không nâng thành `Sample.quality=GOOD` chỉ vì tính được |
| `TranslationPlan` | exact/equivalent/partial/unsupported, lý do, conversion, device clock, expected readback, affected fields, các side effect, bằng chứng; partial không được dispatch |
| `OperationError` | auth_required, forbidden, unsupported, unverified_contract, rate_limited/retry_after, timeout, offline, malformed, stale, partial, conflict, outcome_unknown; lỗi không chứa secret |

Giữ schema `Sample` hiện có trong migration đầu. Thêm result DTO hoặc migration có version khi cần biểu diễn derived/unknown, không nhét các trạng thái mới tùy tiện vào enum đang dùng. Nếu cần `online=null`, đánh giá ảnh hưởng `Device.online`/UI thay vì chỉ sửa adapter.

## 16. Kế hoạch đến từng hàm — nền tảng, xác thực, dữ liệu

Nhóm hàm liệt kê chung một dòng dùng cùng quyết định; các API biệt lệ được tách ở mục 17–19. Helper nội bộ như CRC, checksum, ký HMAC, đóng socket không cần biến thành public interface.

### I0 — Chốt ownership, loại đường song song có rủi ro

| Hàm / file hiện tại | Phương án và hạng mục chỉnh | Nghiệm thu |
|---|---|---|
| `IntegrationPlugin`, `IntegrationRegistry.register` — integration.py | Giữ composition root; đăng ký capability typed theo contract version, kiểm decoder/schema/evidence cùng lúc, không quảng bá chỉ bằng tên method | Registration atomic; duplicate/incompatible contract bị từ chối |
| `IntegrationRegistry.create/find/require` | Giữ; factory gắn context/version; không tự chọn hãng fallback; thiếu plugin → lỗi rõ | Unknown plugin không gọi network |
| `registration_catalog`, `credentials`, `describe` | Phân biệt installed/implemented/authorized/accepted; credential manifest phụ thuộc auth mode, descriptor không lộ secret | Có form không đồng nghĩa ready; snapshot descriptor đúng |
| `builtins`, `research_catalog` — adapters/plugins.py | Features suy từ contract đã đăng ký; catalogue nghiên cứu tách khỏi runtime capability; khai báo hook theo từng profile đủ bằng chứng | Không thể bật `history/alarms/write` khi thiếu handler tương ứng |
| `ReadAdapter`, `ReadAdapterProtocol`, `ControlAdapter`, `WriteAdapterProtocol`, `LocalReadAdapterProtocol` | Hợp nhất bằng protocol nhỏ; giữ shim import một giai đoạn, không bắt read-only adapter implement `send` giả | Contract suite + imports cũ; không dùng `hasattr` làm bằng chứng support |
| `UnifiedCloudAdapter.get_telemetry` | Đóng băng/quarantine trước; thay implementation bằng bridge decoder chuẩn nếu còn consumer thực; bỏ current-time/online/MEASURED fallback và row đầu không match | Offline/stale/wrong SN/empty/malformed không thành measured |
| `TelemetrySnapshot.to_samples`, `interfaces.normalize_points` | Loại normalization cạnh tranh; bridge gọi chuẩn với đủ binding/time/evidence; kiểm lỗi `to_samples` hiện không truyền các field bắt buộc của Sample trước khi dùng | Reproducer schema/missing fields; không tự điền “now”/GOOD |
| `UnifiedLocalAdapter.get_telemetry/get_device_info/_get_device_obj`, `UnifiedCloudAdapter.get_device_info/_get_device_obj` | Đòi DeviceRef/binding thật; không dựng site `default` hoặc device placeholder để ghi; tách transport reachable khỏi telemetry valid | Không identity/permission → không action; local online không đồng nghĩa có số đo |
| `adapter_capabilities`, `Unified*.capabilities`, `create_unified_adapter`, exports `adapters/__init__.py` | Chuyển về registry descriptor hoặc deprecate khi không có consumer; tìm toàn bộ imports/test/public clients trước xóa | UI/controller dùng duy nhất descriptor; shim không chứa nghiệp vụ |

### I1 — Xác thực và vòng đời kết nối

| Hàm / file | Xử lý thống nhất / giữ riêng | Nghiệm thu |
|---|---|---|
| `credential_contract` — plugins.py; `provider` — providers.py | Chung validation/result manifest; password hash/HMAC/OAuth specifics ở adapter/auth strategy. `begin_link/complete_link/check_link/revoke_link` là service đề xuất, không phải universal email/password API | Không coi API key, token và password là cùng loại; secrets không ra FE/log |
| `accounts.overview`, `accounts.check`, nested `revalidate` | Dùng LinkStatus chung, tách auth/discovery/latest; dùng scope/revision guards đang có; trạng thái saved không là connected | Disabled/revoked trong await không lưu success; empty plant hợp lệ |
| `deye_connection.state/options/require_managed_application` | Giữ điều kiện ứng dụng quản trị riêng; expose requirement descriptor qua service chung | App missing không thu mật khẩu; role/region đúng |
| `deye_connection.save_application/disable_application/evict/suspend` | Giữ owner quản trị; cache invalidation và credential revision thống nhất | Đổi/tắt app fence cả session/adapter pending; không cross-account cache |
| `deye_connection.connect` | Chuyển orchestration sang LinkService sau QA, Deye strategy giữ authenticate/hash/request riêng; không nới admin thành tenant tự phục vụ ngoài scope | Contract tương đương trước/sau; app A/customer B chỉ accepted khi QA chứng minh grant |
| `Deye.authenticate`, `Solarman.authenticate`, `GoodWe.authenticate`, `Sungrow.authenticate`, `Huawei.authenticate`, `Dessmonitor.authenticate`, `Growatt.authenticate` | Giữ implementation từng hãng; cùng AuthResult/expiry/renewal/error contract; token-only không giả quá trình password login | Expiry/revoke/clock skew/concurrent refresh/errors, không secret leakage |
| `Solis._get_oauth2_token/_read_oauth2/_read_hmac`, `signed_headers` | Tách HMAC user và OAuth customer consent; sửa theo contract chính thức được cấp; không gửi lại password qua mode khác | Redirect/state single-use/expiry/scope/refresh; dùng đúng endpoint cho từng mode |
| `Controller.integration_adapter/adapter/close`; adapters `invalidate_auth/close` | Cache theo integration + credential revision + auth mode/region; invalidate và close tài nguyên; giữ một controller | Tenant/site không lẫn; disable/restart/cancel đóng task/client |
| `ReadCloud.http`, `Deye._http`, `Dessmonitor._request/read`, từng `read/validate_response` | Shared deadline/budget/redaction/error envelope; signing/envelope/batch sizes ở adapter. Retry read chỉ lỗi transient theo policy; auth/forbidden không thử blind fallback | 401/403/429/5xx/timeout, before-I/O guard; mutation không retry mù |

Nguồn xác thực tái kiểm 05/10: [Solis Authorization](https://developer.soliscloud.com/guide/authorization.html) phân biệt HMAC user với OAuth consent của bên thứ ba. Không coi nhánh client_credentials hiện tại là đã tương đương; cần điều chỉnh theo quyền ứng dụng được cấp.

### I2 — Discovery/latest/normalization dùng một pipeline

| Hàm / file | Phương án | Nghiệm thu |
|---|---|---|
| `*.stations`, `*.devices` của tám adapter | N: kết quả chuẩn qua decoder; adapter chịu paging/batching. Giữ wrapper list tương thích, thêm bounded page/continuation khi chuyển; không đánh dấu inventory complete khi hết budget | Nhiều trang, trùng/thiếu ID, partial timeout, resume, scope isolation |
| `Deye.pages`, `Solarman.pages`, `Solis.listing`, `Growatt.listing`, `Dessmonitor._collectors` | Riêng cơ chế cursor nhưng chung PageResult/coverage; detect repeated cursor, hard cap; không suy trang cuối chỉ từ total=0 nếu API khác | Cursor loop/total sai/empty-middle/truncation; không silently lose devices |
| `Controller.discover/_persist_discovery` | Giữ stage→revalidate→transaction; partial inventory không xóa thiết bị; identity/binding bằng IDs hãng và account scope | Abort giữa discovery không persist nửa batch; SN trùng khác tài khoản không merge |
| `plant`, `device_decoder`, `measurement_decoder`, `Deye.source_time` | Rà việc envelope hiện giống Deye; chuyển parser thời gian dùng chung ra module neutral với unit contract, từng plugin decode native; trạng thái unknown khác offline | epoch s/ms, ISO zone, missing/future, kiểu bool/str không coerced sai |
| `*.latest` của tám adapter; `GoodWe/Sungrow/Huawei/Growatt/Solis.decode_native_points` | N/E với exact semantics; trả từng thiết bị kèm failures/coverage; bản ghi raw giữ namespaced khi chưa map | Wrong SN, out-of-order, missing point, zero hợp lệ, sign/unit variants |
| `Controller.poll/latest` | Chỉ một ingestion path; preserve revision/atomic guards; tách status kết nối, quality measurement, accepted profile; không UI normalize lại | Các consumer dashboard/report/EMS nhận cùng quality và scope |
| `telemetry.normalize_points` | Giữ chủ sở hữu Sample; chuyển đổi W/kW/Wh/kWh có evidence; parameter source rõ nếu dùng cho local, không mặc định cloud cho mọi nguồn | Finite/NaN/bool/unit/sign/source; native không tự thành canonical |
| `data_workspace.accepted_profile/apply_profile`; plugin `telemetry_profiles` | Nối rõ reviewed mapping với profile installed/accepted; version/revoke/identity pin; không auto-promote mapping draft | Firmware/region/account thay đổi → không dùng profile cũ |
| `refresh_quality/select_source/discrepancy` | Dùng chung timestamp/freshness; lựa chọn nguồn theo cùng device/metric/unit và policy; không trung bình cloud/local khác thời điểm | Stale/future/skew/conflicting measurements; không silent substitution |
| `Deye.stations_cached/configuration_cached/latest_cached`, `_cache_*` | Cache thuộc transport hoặc shared read service nhưng pin identity/grant/revision/age; configuration trước/saulệnh bypass cache; không cache mutation | Không biến cached thành fresh; thay quyền không trả dữ liệu cũ |
| `local_models.collect_model`, `ModbusTcpReader.read`, `SolarmanReader.read` | Ưu tiên pipeline collector/profile đang có. Giữ framing TCP/V5 riêng; đưa observations vào ingestion qua enrollment | Digest/profile/source identity, bounds/replay/sequence; không tự quét network |
| `ModbusTcpPoller/SolarmanV5Poller/GoodWeLocalAdapter/EybondLocalAdapter.read_telemetry`, `discover` | Audit overlap với collector trước; chỉ bridge đường có consumer và license/evidence, còn lại quarantine. Chỉ thống nhất result, không suy register xuyên hãng | TCP reachable nhưng không readings ≠ valid telemetry; no default device identity |

## 17. Kế hoạch từng hàm history, alarm, cấu hình

### I3 — Lịch sử và cảnh báo, nơi tái sử dụng đem lại lợi ích ngay

| Hàm hiện tại → interface dịch vụ đích (đề xuất) | Chuyển đổi/fallback có thể dùng | Cần sửa và test |
|---|---|---|
| `Deye.history(serial,start,end,points)` → `query_history(query)` | N/E: epoch/time/metric list trong adapter; payload không đủ mapping giữ native | Native response hiện `UNVERIFIED`; thêm decoder, pages, coverage, idempotent backfill |
| `Solis.history_day` → `query_history(query)` | E: chia range UTC theo ngày timezone; trim `[start,end)`; ghi resolution thật | Validate timezone/money fields; không diễn giải doanh thu hãng là biểu giá SolarOne |
| `Solis.history_month` → `query_energy_totals(query)` | N/E: giữ monthly/daily aggregate đúng resolution | Không bung tổng tháng thành đồ thị 5 phút; date boundaries và completeness |
| `Solis.history_year` → `query_energy_totals(query)` | N/E: aggregate năm/tháng theo tài liệu exact response | Không suy thiếu tháng là 0; partial year test |
| `Solis.history_date/history_currency` | Giữ helper codec/validation private | Không đưa currency/default vào generic power history |
| `Solarman.history(...,time_type)` → `query_history/query_energy_totals` | N/E: type/granularity explicit trong bridge | **Không truyền `points` vào vị trí `time_type`** như khi bật registry flag đơn thuần; test signature |
| `Solarman.station_history` → `query_energy_totals(target=station)` | N/E: scope trạm khác scope thiết bị | Không nhân tổng trạm cho từng inverter; station access test |
| `Huawei.history(dev_id,dev_type_id,collect_time)` → `query_history` | E: giải DeviceRef→devId/type, ms và chia cửa sổ query theo contract | Không giả serial=devId; không nhầm epoch s/ms; giữ granularity 5 phút khi đúng endpoint |
| `Huawei.history_station_day` → `query_energy_totals` | N/E: station code, ngày địa phương, ms | DST/ngày trạm, coverage, totals không lẫn point samples |
| `Huawei.history_station_month` → `query_energy_totals` | N/E: tổng kỳ tháng | Đơn vị/kỳ, thiếu dữ liệu, duplicate pages |
| `Huawei.history_station_year` → `query_energy_totals` | N/E: tổng kỳ năm | Boundary leap-year/partial-year |
| GoodWe/Sungrow/Growatt/Dessmonitor chưa có history contract chung | D: đọc dữ liệu **đã lưu** của SolarOne; N chỉ khi nghiên cứu/xây adapter thật | `source=LOCAL_ARCHIVE`, available range/retention rõ; không hứa lịch sử trước ngày kết nối |
| `app.history` GET; `app.vendor_history` POST | Chuyển caller sang HistoryService; giữ route cũ một giai đoạn. Query dữ liệu ≠ backfill job; backfill explicit, bounded, revision guarded | Schema version, site scope, pagination/resume, persist dedup; native export vẫn redacted |
| `Deye.alerts` → `list_alarms(query)` | N/E: serial/window → AlarmPage | Stable alarm ID/timestamp/severity/recovery contract |
| `Solis.alerts` → `list_alarms(query)` | N/E: station hoặc serial cùng mục tiêu yêu cầu | Không query toàn account để trả cho người chỉ có một trạm |
| `Solarman.alerts` → `list_alarms(query)` | N/E: page/size → cursor opaque; giữ completeness | Repeated/out-of-order pages; không coi empty là recovered |
| `Huawei.alerts` → `list_alarms(query)` | N/E: station codes + ms; resolve từng device ID | Không lộ alarms trạm ngoài scope; severity unmapped → unknown |
| `Controller.collect_alarms`, plugin `decode_alarm`, `IncidentService.apply_alarm` | Đăng ký decoder từng hãng; idempotent incident ingestion; native chỉ là nguồn, workflow incident chung | Duplicate/reopen/recovery/order/snapshot partial; empty response không đóng hàng loạt |
| Hãng thiếu API alarms → service cảnh báo nội bộ | D: threshold/offline/anomaly từ dữ liệu đủ điều kiện; namespace `solarone.*`, policy/revision rõ | Không giả code/severity native; mất dữ liệu không giả sensor=0; cooldown/recovery |
| `analytics.counter_delta`, `telemetry.energy_ratios`, report consumers | D: tổng từ counter/timeseries có coverage; không cộng đồng thời native total và local total | Reset/rollover/gap/battery attribution; không chia đều một tổng ngày thành phút |

### I4 — Cấu hình và năng lực đọc, trước khi mở control

| Hàm | Phương án | Gate |
|---|---|---|
| `Deye.configuration/dynamic_control_read` → `read_configuration(request)` | N/E; polling job riêng trong adapter, deadline/cancel; request nêu `fresh_required`, fields; snapshot có timestamp | Job success chưa đồng nghĩa values đầy đủ; cache không dùng cho readback |
| `ReadCloud.configuration/history/alerts` default | Giữ explicit unsupported, thay `*args` bằng optional protocols qua bridge | Unsupported không gọi endpoint hoặc trả dữ liệu giả |
| `CommandEngine._read_config` | Gọi signature thống nhất; bỏ catch TypeError rồi đọc lần hai; adapters cũ có shim rõ | TypeError nội bộ không phát request lần hai |
| `ProfileRegistry.register/resolve/candidates/explain/revoke`, `Controller.capability/capabilities` | Nguồn duy nhất cho quyền control; bổ sung mô tả năng lực read/derived riêng, không làm lỏng ControlProfile | Conflict profile, firmware đổi, revoked acceptance, role mismatch đều fail closed |
| Native-field schema/read APIs trong `phase_d_api.py`, model workspace | X hoặc N/E theo field đã xác nhận; chia metadata/observed value khỏi advisory input | Field không đọc được giữ unknown; không coi giá trị người nhập là readback |

## 18. Từng intent điều khiển: chỉ thống nhất khi đúng nghĩa

### I5 — Một command lifecycle, nhiều compiler có điều kiện

Đối chiếu đủ **34 intent** trong `docs/evidence/intents.json`. Đây là quyết định thiết kế dự kiến, **không phải support matrix của các hãng**. Mỗi dòng chỉ được mở cho exact profile có evidence và acceptance. N/E có thể chưa khả dụng trên bất kỳ thiết bị đã nghiệm thu nào của người dùng.

| Intent | Phương án | Điều kiện / trường hợp phải từ chối |
|---|---|---|
| `SET_WORK_MODE` | N/E enum adapter | Mỗi mode có nghĩa rõ; không map theo tên gần giống |
| `SET_SELF_CONSUMPTION` | E alias mode nếu đúng | Compiler khai báo phụ thuộc export/battery/TOU; không tự đổi các cờ khác ngoài preview |
| `SET_EXPORT_LIMIT` | N/E đơn vị giới hạn export | Phân biệt plant/inverter, total/per-phase, CT/meter; không dùng PV active limit thay export limit |
| `SET_ZERO_EXPORT` | E limit=0 **chỉ khi** hãng xác nhận semantics | Không tương đương “solar sell off” trên mọi model; không dùng vòng polling cloud làm zero-export an toàn |
| `SET_GRID_IMPORT_LIMIT` | N khi thiết bị hỗ trợ thật | Không thay bằng charge limit; tải nhà vẫn có thể nhập lưới |
| `SET_RESERVE_SOC` | N/E | Reserve khác min/shutdown SOC; đơn vị/range rõ |
| `SET_MIN_SOC` | N/E theo ngữ cảnh discharge | Không dùng reserve làm fallback nếu khác hành vi |
| `SET_SHUTDOWN_SOC` | X hoặc N theo exact contract | Tham số bảo vệ, không emulation bằng scheduler |
| `SET_RESTART_SOC` | X hoặc N theo exact contract | Phải xác định quan hệ shutdown/restart; không default hysteresis |
| `SET_MAX_CHARGE_CURRENT` | N amperes | Không chuyển W→A bằng điện áp pin danh định; conversion chỉ khi protocol định nghĩa và error bound hợp lệ |
| `SET_MAX_DISCHARGE_CURRENT` | N amperes | Tương tự charge, xét BMS constraint |
| `SET_MAX_CHARGE_POWER` | N/E W/kW hoặc % có base xác minh | Nếu % dựa công suất chưa rõ thì U; không silently round |
| `SET_MAX_DISCHARGE_POWER` | N/E | Không coi pause/force discharge cùng nghĩa |
| `ENABLE_GRID_CHARGE` | N/E boolean/enum | Tách permission cho sạc với lệnh force charge |
| `DISABLE_GRID_CHARGE` | N/E | Không tắt toàn bộ nguồn sạc pin hoặc PV nếu chỉ yêu cầu tắt grid |
| `SET_TOU` | E schedule compiler | Xem mục lịch; chỉ exact/proven-equivalent, không cắt slot âm thầm |
| `ENABLE_TOU` | N/E | Có lịch valid và hiểu ảnh hưởng mode; không tạo lịch mặc định |
| `DISABLE_TOU` | N/E | Phải biết chế độ sẽ quay về, nêu trong preview |
| `FORCE_CHARGE` | N/X | Có giới hạn SOC/power/duration và cancel; không giả bằng mode thiếu stop safety |
| `FORCE_DISCHARGE` | N/X | Xét export/BMS/grid; không bật qua số đo chưa accepted |
| `STOP_FORCE_OPERATION` | N/E explicit cancel | Không dùng power=0 nếu 0 nghĩa unlimited/invalid hoặc không khôi phục đúng |
| `SET_PEAK_SHAVING` | N native; D advisory riêng | Optimizer SolarOne không phải native protection; cloud loop không SLA tương đương |
| `SET_ACTIVE_POWER_LIMIT` | N/E giới hạn phát inverter | Không tráo với export limit tại điểm đấu nối |
| `SET_REACTIVE_POWER` | X, có thể common schema có điều kiện | Q/PF/curve/control priority/grid code khác nhau; kỹ thuật viên và commissioning riêng |
| `SET_POWER_FACTOR` | X hoặc N theo profile | Leading/lagging/sign/phase convention rõ; không suy dấu giữa hãng |
| `SET_BACKUP_EPS` | X | Cần topology/ATS/model, không universal switch |
| `SET_SMART_LOAD` | X; E chỉ schema tương đương | Port generator/load/chế độ chia sẻ, ngưỡng và tác dụng phụ |
| `SET_GENERATOR_POLICY` | X | Auto-start/dry contact/grid-charge không đồng nghĩa; interlock riêng |
| `SET_GENERATOR_METER` | X | Meter routing/model/phase chính xác |
| `SET_METER` | X | Không chuyển universal enum nếu loại/chiều không xác nhận |
| `SET_CT_RATIO` | X | Ratio/scaling/wiring/country; không lấy mặc định trong mock |
| `POWER_ON_INVERTER` | N/X nếu native | Có trạng thái lệnh/readback; không thay bằng công suất khác 0 |
| `POWER_OFF_INVERTER` | N/X nếu native | Không coi active limit=0 là electrical isolation |
| `RESTART_INVERTER` | X với lifecycle riêng | Mất liên lạc là expected nhưng không tự coi reboot thành công; không retry mù |

### Các hàm control hiện tại cần chỉnh

| Hàm | Phương án chỉnh / tiêu chí |
|---|---|
| `IntegrationRegistry.compile`, `adapters/deye_control.compile_deye`, compiler model khác | Giữ pure compiler; trả translation + affected fields + expected readback. Compiler không network; cấm mutation hidden defaults. Native compiler có thể được reuse bên trong exact profile, không chạy ngoài engine |
| `InverterControlMixin.set_battery_target_soc/set_charge_rate/set_discharge_rate/set_reserve_soc/set_work_mode/set_tou_schedule/pause_charge/pause_discharge` | Bỏ vai trò gửi trực tiếp; deprecate hoặc chuyển thành yêu cầu preview có principal/context/confirm. `target_soc` không tự alias reserve/min; pause không tự alias 0 |
| `InverterControlMixin._build_set_soc/_build_set_charge_rate/_build_set_discharge_rate/_build_set_reserve/_build_set_work_mode/_build_set_tou/_build_pause_charge/_build_pause_discharge` | Nếu có bằng chứng giữ pure private compiler; nếu chỉ placeholder giữ unsupported. Không biến một mixin thành quyền ghi chung |
| `UnifiedInverterAdapter` và `UnifiedLocalAdapter/UnifiedCloudAdapter.set_*`, `pause_*` | Cùng disposition như mixin; không delegate `inner.send` ngoài engine. `get_work_mode/get_tou_schedule` đọc ConfigurationSnapshot có source time, không derive từ việc đã gửi |
| `Deye.set_tou_schedule` | Dùng `encode_deye_tou` như pure codec trong compiler, gửi bằng engine transport; kiểm các consumer trước deprecate direct-write helper |
| `CommandEngine.validate/preview/persist_preview/confirm/_execute/validate_before_send/validate_revisions` | Giữ locks/digest/idempotency/revision guards; plan pin strategy/profile version. Nếu E nhiều lệnh, preview đủ side effects; một phần apply thì quarantine, không hứa transaction phần cứng |
| `ControlAdapter.send/order`, `Deye.send/order`, bridge transports khác | Guard bắt buộc tại điểm network; ACK/order success không là VERIFIED. Nếu hãng synchronous/no-order thì mô tả ack mode rõ, vẫn fresh readback; không chế order ID thành công giả |
| `verify_semantic_readback`, `_normalize_bool`, `_compare_tou_slots` | So sánh bằng schema/profile của intent; chỉ chấp nhận bool/unit/time equivalence có contract. Không nới comparator toàn cục để “đạt test” |
| `CommandEngine.transition/assert_clear/close` | Giữ audit/outcome unknown, restart recovery/quarantine; đóng process không coi lệnh đang chạy là hủy thành công |

### Lịch và khả năng chuyển đổi

| Hàm | Phương án |
|---|---|
| `schedule_planning.program_for/expand_program/utc_boundary/minutes/schedule_digest` | Chung ngữ nghĩa WeeklyProgram/timezone/DST/gaps/revision, không knowledge hãng |
| Plugin `compile_schedule`; nested `schedule_planning.compile_schedule` | Adapter chỉ dịch lịch; service đánh giá compatible. Code hiện chỉ cho `exact`; chỉ mở `equivalent` khi có proof/descriptor/test riêng, không đổi điều kiện thành chấp nhận mọi equivalent |
| `tou_builder.build_tou_programme/_validate_programme/encode_deye_tou/encode_sunsynk_tou` | Giữ pure codec/model-specific; `simple_offpeak_programme` chỉ explicit draft do người dùng chọn, không tự seed lịch vận hành |
| `schedule_planning.prepare_rollout`, rollout owner hiện hữu | Pin source digest và capability tại từng target, reuse command preview/canary; tạo rollout không có nghĩa đã cài lịch |

Các phép E được cân nhắc: gộp slot liền kề cùng mọi thông số; đổi HH:mm/minutes đúng; daily schedule thay weekly chỉ khi **mọi ngày thực sự giống nhau** và timezone/holiday semantics không mất. Quá số slot, độ phân giải không biểu diễn được, hoặc lịch theo ngày khác nhau trên máy chỉ hỗ trợ một ngày → reject kèm hướng dẫn sửa, không tự cắt/gộp xấp xỉ.

Hãng không hỗ trợ lịch cài trong máy: trước mắt **advisory/unsupported**. Có thể nghiên cứu scheduler SolarOne riêng sau này khi có native start/stop, durable jobs, clock/lease/restart/missed-trigger policy, watchdog và safe fallback. Đây là **orchestrated control khác native TOU**, không có tính sẵn sàng tương đương khi mất mạng; không nằm trong pilot đầu và không kích hoạt tự động.

## 19. Chức năng đặc thù và tầng tính toán dùng chung

### I6 — Dọn native routes, giữ cái có ích

| Hàm/nhóm hiện tại | Quyết định |
|---|---|
| `phase_d_api` Solis hybrid compile/decode, Deye hybrid, Growatt SPH/multiphase, SOLARMAN V5 | Pure parser/compiler giữ làm thư viện có provenance/license; route dev-tool phân quyền/tài liệu rõ, UI vận hành gọi owner chung. Không xóa trước khi kiểm consumer |
| `/goodwe-sems/login`, station/monthly parser; `/growatt-cloud/*`, `/smartess/poll`, GoodWe/Huawei local routes | Route locked không được quảng cáo live. Khi dịch vụ chung thay thế: compatibility shim cho semantics tương đương, deprecation có danh sách consumer; route không tương đương vẫn locked hoặc bỏ sau migration |
| `SmartEssLocalClient.execute_command_safely` | Giữ locked tới khi có exact transport/profile; không bật flag để làm route chung chạy được |
| `BluesunAdapter.read_telemetry/decode_branch_telemetry/get_capability_profile/write_parameter` | Chưa dùng làm “Bluesun chung”; brand routing sang platform đã xác định. Đổi guessed chemistry/voltage/C-rate thành declared/unknown trong scope sửa tương lai; write vẫn khóa; chỉ giữ decoder có nguồn đúng model |
| `EVNTOUOptimizer.optimize_24h/optimize_scenarios/get_rate_for_dt`, `FleetInverterBalancer.balance_fleet` | D: service tính toán dùng dữ liệu canonical/declared có provenance. Output plan/advisory không có quyền send; dispatcher riêng qua engine; rounding/coverage/constraint test |
| Report, comparisons, threshold alert, warranty reminders, maintenance workflow | D: dùng chung trên dữ liệu thật/SolarOne records; tách nguồn hãng với người dùng khai báo; reminder không chứng minh hãng chấp nhận bảo hành |
| I‑V scan, firmware/OTA, RMA, billing settlement, optimizer layout, SIM subscription | X: schema/permission/lifecycle đặc thù; read/result có thể dùng viewer chung. Không giả capability cho hãng không có phần cứng/API |
| AI/MCP, VPP, thiết kế PV, dealer ERP trong backlog 58 mục | Deferred, không đưa vào refactor nền tảng; API read-scoped về sau có thể reuse service chung |

**Có thể giữ riêng logic, không được giữ riêng an toàn.** Native action gây side effect vẫn cần scope/revision/audit/confirm/lifecycle; electrical write phải qua CommandEngine. Firmware/ownership/RMA cần lifecycle và quyền riêng phù hợp, không ép thành lệnh điện thông thường.

## 20. Ma trận áp dụng theo hãng

Không phải xác nhận support hiện hành; đây là thứ tự implementation sau baseline QA.

| Hãng/nền tảng | Lát cắt đầu | Hàm tận dụng | Fallback được cân nhắc | Giới hạn |
|---|---|---|---|---|
| Deye | Auth→discover→latest→history/alarm→config read | Các hàm có sẵn trong Deye | Local archive, report/alerts D | Dynamic control/TOU chỉ sau profile acceptance |
| GoodWe | Xác định SEMS/SEMS+, auth/discovery/latest đúng platform | GoodWe.*; local adapter chỉ khi có enrollment riêng | Local archive D; local transport exact profile nếu được phép | Không coi logo hay parser SEMS legacy là SEMS+ support |
| Solis | Tách HMAC/OAuth; paging/latest/history/alarm | listing/history_day/month/year/alerts | D archive/analytics | OAuth và parameters không copy từ HMAC; control model-specific |
| SOLARMAN | Discovery/latest, history/station_history/alerts | Solarman.* | D archive; V5 local nếu đã accepted | Platform không xác định semantics inverter OEM |
| Huawei | DeviceRef/type, history granularity, station alarms | history + station_* + alerts | D archive/analytics | devId/type/ms; local không tự là fallback của northbound |
| Sungrow | Auth/account points/discovery/latest contract | Sungrow.* | D archive trước | API/gói/vùng hiện hành cần source và grant; không tự thêm MQTT/VPP |
| Growatt | Token/region/listing/latest | Growatt.* | D archive/report | OSS menus không là API contract; RMA/EV/OTA giữ X |
| Eybond/SmartESS | Signed session, plant→collector→device, latest | Dessmonitor.* | D archive; local exact profile riêng | Company/platform/OEM phải match, không universal control |
| Bluesun | Resolve brand/model/logger→platform | Metadata declared brand, adapter platform tương ứng | Theo platform đã xác nhận | Không tạo giả một Bluesun cloud chung |

Một hãng mới chỉ cần implement các năng lực native của nó; lịch sử local/report/threshold/maintenance có thể dùng service D mà không chép lại thuật toán. Ngược lại, discovery/measurement schema đúng không tự cấp quyền sử dụng những phép tính đòi canonical profile tốt hơn.

## 21. Chia đợt, phụ thuộc và dự trù

Dự trù **ngày công kỹ thuật tập trung**, không là hẹn ngày production, không tính thời gian hãng duyệt API/chờ người dùng/phần cứng. Chốt lại sau Q1; không cộng các đợt song song như cam kết lịch. Mỗi đợt gồm code/test/doc; QA phần cứng riêng.

| Đợt | Phụ thuộc | Dự trù | Kết quả bàn giao / điều kiện đóng |
|---|---|---:|---|
| U | Công việc UI hiện tại | Ước lượng lại từ ma trận pixel | 26 màn có kết quả chấp nhận hoặc ngoại lệ được người dùng duyệt |
| Q0/Q1 | U; prerequisites từng hãng | 1–3 ngày công chuẩn bị/quan sát, chưa tính chờ hãng | Baseline QA đọc + contract ledger; hãng blocked có lý do cụ thể |
| I0 | Q1 có kết luận; không nhất thiết mọi hãng login thành công | 2–3 | Quyết định ownership, schema, shim, regression facade; không có bypass mới |
| I1 | I0; sửa auth tối thiểu Q0 có thể đã làm | 3–5 | Connection lifecycle chung, mode hãng riêng; revoke/scope/secrets đạt |
| I2 | I0/I1 | 4–6 | Một read pipeline, Deye + hãng thứ hai đã QA làm lát cắt mẫu; cloud/local semantics rõ |
| I3 | I2 | 4–7 | History/alarms service + archive fallback, ít nhất hai dialect; không mất thời gian/quality |
| I4 | I2; Q1 có config evidence | 2–4 | Config read/capability/profile thống nhất; unsupported rõ |
| I5 | I4; từng write profile đủ evidence | 5–10 cho lát cắt được chọn | Compiler/TOU/command tests; chưa hardware acceptance thì vẫn locked |
| I6 | I2–I5 theo consumer | 2–4 | Native routes phân loại/migrate, facades không còn cạnh tranh, release notes |
| Q2 | I0–I4 cho pilot đọc; I5 nếu scope control | 2–4 + soak phù hợp pilot | QA đọc lại, restart/revoke/retention/load; hardware QA tách riêng |

Các dải trên là **pilot hai dialect**, không bao trọn tám cloud + mọi model + 58 tính năng. Các hãng còn lại đưa vào từng lát cắt sau I2; lập dự toán từ contract thực, không nhân máy móc theo số hãng. Không đợi I5/control xong mới có thể nghiệm thu pilot **read-only**.

## 22. Migration và chống hồi quy

1. Chụp call graph/import/route consumer + test baseline. Ghi rõ cái đang live, pure, locked, unused; không xóa chỉ vì tên cũ.
2. Thêm contract version và bridges giữ API v1. Reuse observations/store đang có; không đổi identity/database cùng một đợt auth lớn.
3. Shadow **decoder trên cùng payload tổng hợp hoặc đã khử định danh**, không chạy hai poller gọi hãng. So sánh unit/time/value/quality/scope trước khi đổi reader.
4. Cắt chuyển từng operation từng integration bằng cấu hình quản trị có audit. Không runtime fallback về code cũ khi gặp permission/parse error. Rollback read giữ revisions và dữ liệu; không downgrade schema vô kế hoạch.
5. Với write, không dual-run/shadow send. Chỉ pure compiler diff; pin compiler/profile trong plan, đổi version làm preview cũ mất hiệu lực. Rollback phần mềm không phải rollback trạng thái thiết bị.
6. Sau khi consumer đã chuyển và thời hạn tương thích được duyệt mới xóa export/facade/route cũ. Nếu có public integration bên ngoài, giữ deprecation release và hướng dẫn chuyển.

## 23. Bộ kiểm thử và định nghĩa hoàn thành

Các file test mới đề xuất, chưa tạo/chạy trong phiên lập kế hoạch:

- `tests/test_integration_contracts.py`: protocol registration, capability descriptor, no phantom support; ít nhất hai dialect khác nhau cho một nghiệp vụ chung.
- `tests/test_integration_quality_bridge.py`: IA-03, to_samples/schema, stale/future/wrong identity/no data/local connectivity-only.
- `tests/test_connection_lifecycle.py`: modes, callback/revoke/expiry/parallel refresh, session and credential revisions, redaction.
- `tests/test_history_service.py`: seconds/ms/date/DST, resolution, pagination, coverage, counter reset, archive fallback, duplicate/backfill/cancel/scope.
- `tests/test_alarm_bridge.py`: identity/severity/recovery/idempotency/order/partial; SolarOne alarm namespace khác vendor alarm.
- `tests/test_configuration_contract.py`: unified signature, fresh config, cache/revision, không retry TypeError nội bộ.
- `tests/test_intent_equivalence.py`: chứng minh các phép E và phản ví dụ; zero export khác active power, reserve khác shutdown, W/A/% và không silent clamp.
- `tests/test_schedule_translations.py`: all 7 days, slot limits, timezone/DST, gap/overlap, roundtrip readback; partial/unknown rejected.
- `tests/test_native_extension_guards.py`: pure/read/mutate permissions, no direct write bypass, no cross-site/transport fallback.
- Browser tests: cùng workflow cho hai hãng, capability reason dễ hiểu, unknown/partial/derived label, no mock seeds, không vendor-specific success giả.

Dùng/reuse test hiện hữu trước khi tạo file trùng trách nhiệm. Sau một đợt mạch lạc chạy consolidated Ruff, BE, UI contracts, JS checks, build, visual QA; không gọi tài khoản thật trong suite. Live QA là phiên riêng có người dùng nhập và chốt scope.

Một hàm chỉ được đánh dấu hoàn thành khi: caller thật dùng owner chuẩn; input/output/error contract rõ; phân loại N/E/D/X/U có evidence; permissions/revisions/source-time/coverage đúng; fixtures/negative tests đạt; UI trung thực; telemetry/control acceptance đúng phạm vi. Hãng chưa test ghi vẫn locked dù shared compiler test đạt.

## 24. Phạm vi phiên lập kế hoạch 07/10/2026 (lịch sử)

Cập nhật toàn bộ kế hoạch vào chính tài liệu backlog này và liên kết roadmap/index; bản kế hoạch tách trước đây chỉ còn liên kết chuyển hướng. Không sửa adapter/controller/UI, không migration database, không gọi tài khoản hoặc lệnh thật, không triển khai/push. Các con số test ở báo cáo trước không được dùng như kết quả verification cho implementation chưa làm.

Tên method hiện có được đối chiếu source/AST; tên service/DTO/test có đánh dấu đề xuất. Các local adapters và helper mới đọc ở mức contract cần deeper audit khi thực thi; không tuyên bố đã tìm hết lỗi của mọi transport. Trước mỗi đợt phải kiểm lại code và bằng chứng hãng mới nhất.

## 25. Đối chiếu 58 hạng mục với kế hoạch thực thi

Bảng này nối backlog sản phẩm với kế hoạch hàm, không thay trạng thái M/C/T/K của phần I bằng trạng thái hoàn thành. Tại baseline 07/10 các refactor đang PLANNED, mở rộng DEFERRED/RESEARCH; các lát cắt được triển khai sau đó phải đọc ở checkpoint đầu file. I0 là nền chung; không có hạng mục nào được coi đã xong chỉ vì được gán vào một đợt.

| Hạng mục | Đợt / owner kỹ thuật | Phạm vi và giới hạn |
|---|---|---|
| F01, F02, F51 | Q0/Q1 → I1 — accounts/auth | Chuẩn hóa linking, grants, mode và lifecycle; quản trị ứng dụng sâu chỉ khi có nhu cầu, không hứa mọi hãng login hai ô |
| F03, F37 | I4 — registry/config/profile | Descriptor và schema read trước; native write chỉ exact profile |
| F04, F07, F11, F15, F57 | I2 — controller/telemetry/identity | Discovery/paging, nguồn/quality, identity và mapping; đối chiếu thiết bị hai nguồn không tự merge khi chưa đủ bằng chứng |
| F05, F06, F16, F21 | I3 — history/incidents/analytics | History/alarm chung và coverage; lưu trữ nhiều năm/chẩn đoán nguyên nhân sâu tách mở rộng sau pilot |
| F08, F09, F10, F12, F13, F14 | DEFERRED — onboarding/network | Interface có thể tiếp nhận sau; gắn/tháo phía hãng, QR, provisioning, topology, tín hiệu và thuê bao cần contract riêng |
| F17, F18, F20, F22, F23 | DEFERRED — model/diagnostics | Optimizer/I‑V/BMS/weather/EPM cần thiết bị và dữ liệu đúng loại; không emulation khi thiếu đầu vào |
| F19 | I6 phân loại → mở rộng analytics | Reuse công cụ thuần nếu input/semantics được xác nhận; chưa hứa chẩn đoán string live |
| F24, F25, F26, F27, F28 | DEFERRED — reports/notifications | Có thể reuse dữ liệu chuẩn I2/I3; PDF/email/kiosk/delivery là implementation riêng, không tự hoàn thành nhờ interface |
| F29, F30, F31, F32, F33, F34, F35 | DEFERRED/RESEARCH — operations | Workflow nội bộ dùng chung được; dữ liệu/quyền bảo hành, RMA và công tác điện giữ ranh giới riêng |
| F36 | DEFERRED — firmware/native extension | OTA không phải generic setter; cần executor, signature, recovery và hardware acceptance |
| F38, F39 | I5 — schedules/CommandEngine/rollout | Lịch biểu diễn chính xác, preview/canary/readback; hãng chưa đủ mapping vẫn khóa |
| F40, F41, F42 | I6 phân loại; implementation DEFERRED | EV/heat/smart load/generator: calculator khác driver; logic đặc thù không bị ép vào inverter common controls |
| F43, F44, F48 | I6 ranh giới derived/advisory; mở rộng sau | Tái sử dụng thuật toán khi đủ dữ liệu; forecast/giá/cashflow và dispatch thực không tự có |
| F45, F46 | DEFERRED — market/streaming | API/gói/region và hợp đồng riêng; không coi cloud polling là MQTT/VPP |
| F47 | DEFERRED — project design | Thiết kế PV ngoài pilot giám sát; có thể reuse catalogue, không đưa vào adapter |
| F49, F50, F52 | DEFERRED — tenancy/security/organization | Giữ scope hiện hữu trong I1; đa tenant/MFA/SSO/white-label là dự án riêng, bắt buộc trước release có yêu cầu tương ứng |
| F53 | DEFERRED — migration | Chuẩn history hỗ trợ nền; nhập dữ liệu hệ khác cần consent/license/dedup riêng |
| F54, F55 | DEFERRED — AI/API | Chỉ xây sau read services/scopes ổn; không expose direct adapter send |
| F56, F58 | RESEARCH | Xác minh nghiệp vụ/nhu cầu trước; không tạo API hoặc UI giả từ tên menu |

### Kiểm tra tài liệu ngày 07/10/2026

Đợt này chỉ hợp nhất tài liệu: giữ phần nghiên cứu gốc, chuyển toàn bộ kế hoạch theo hàm vào phần II, kiểm đủ 34 intent và liên kết 58 mục F01–F58 với bảng thực thi. Không chạy lại application tests/build vì không sửa runtime; không dùng kết quả test cũ để tuyên bố interface mới đã được kiểm thử. Khi tiếp tục triển khai, bắt đầu từ cổng U/Q0/Q1 và checkpoint roadmap, không nhảy thẳng vào I0–I6.

<a id="execution-runbook"></a>
## Phần III — Quy trình thực thi và phục hồi sau gián đoạn

### 26. Trạng thái, bằng chứng và quy tắc tiếp tục

Các trạng thái dưới đây áp dụng **cho từng bước**, không gộp cả vendor thành “supported”:

| Trạng thái | Ý nghĩa |
|---|---|
| TODO | Chưa bắt đầu, phụ thuộc có thể chưa đủ |
| READY | Đã đủ đầu vào và phạm vi cho phép; có thể thực hiện |
| IN_PROGRESS | Có bước đang làm, checkpoint phải ghi thao tác cuối/bước tiếp |
| IMPLEMENTED_UNVERIFIED | Có code nhưng chưa đủ kiểm thử cho chính thay đổi đó |
| VERIFIED | Có bằng chứng đạt acceptance của bước; phải ghi rõ fixture, visual, live-read hay hardware-write |
| WAITING_USER | Thiếu đăng nhập, MFA, lựa chọn hoặc phê duyệt cụ thể; nêu chính xác cần gì |
| BLOCKED | Thiếu contract, hạ tầng hoặc phụ thuộc; ghi cách tháo gỡ và việc độc lập có thể làm |
| SUPERSEDED | Đã có bước thay thế, giữ liên kết để không thực hiện bản cũ |

Không đánh dấu VERIFIED chỉ vì markdown cũ nói “đạt”, suite xanh, số LOC tăng, portal có nút, hoặc adapter trả HTTP 200. Các bước chưa liệt kê tiến độ riêng mặc định TODO. Trạng thái runbook là ghi chép công việc, không phải lệnh đổi trạng thái goal của công cụ.

**RSM-00 — bắt buộc đầu mỗi phiên tiếp tục:**

1. Đọc `AGENTS.md`, checkpoint đầu file, mục đang mở/phụ thuộc, evidence tương ứng và roadmap. Đọc đủ instruction chuyên biệt UI/adapter trước khi sửa; không cần đọc lại mọi manual không liên quan.
2. Kiểm `git status --short`, branch/HEAD/diff và file thực. Không checkout/reset/pull/merge đè thay đổi, không coi HEAD là toàn bộ code đang chạy. Nếu checkpoint mâu thuẫn code, cập nhật nhận định sau khảo sát, không ghi đè code cho giống kế hoạch.
3. Kiểm process/port và data-dir trước khi chạy app. Không tin PID, tool session ID, trạng thái login từ phiên trước. Chỉ một controller; `SOLAR_WRITES_ENABLED=false` cho QA đọc. Nếu cần chạy lại, dùng môi trường đã có và đúng data-dir, không tạo DB demo thay DB thật.
4. Kiểm sức khỏe API/UI, phiên người dùng qua UI, vault qua trạng thái kết nối **không in giá trị bí mật**. Có phiên được cho phép còn dùng được thì tiếp tục; hết phiên mới mời người dùng tự nhập trong trang đúng hãng/SolarOne, không xin password trong chat.
5. Đối chiếu thao tác bị ngắt: file có thay đổi chưa, migration có version/transaction receipt không, read job có cursor không, command có receipt/readback không. Chỉ retry đọc idempotent theo quota. Ghi không rõ kết quả → quarantine và điều tra, không gửi lại.
6. Chọn bước mở ưu tiên cao nhất đủ phụ thuộc; lưu checkpoint **trước khi** bắt đầu batch. Nếu chờ user, làm bước READY độc lập, không bỏ qua lỗi dữ liệu để chỉ trang trí UI.

**RSM-01 — cuối mỗi batch hoặc trước chuyển phạm vi:** ghi tiến độ tại chính file này, cập nhật evidence và sổ lỗi; chạy nhóm kiểm thử phù hợp rủi ro. Theo workflow repo: viết BE/FE/regression thành một lát cắt rồi consolidated verification, không chạy full suite sau từng chỉnh nhãn. Sau sửa lỗi QA chạy lại checks bị ảnh hưởng. Không tự commit/push.

Mẫu checkpoint để **cập nhật**, không chỉ append nhiều bản “hiện tại”:

```text
updated_at / branch / HEAD / dirty scope:
active_step / substep / status:
last_completed_action / evidence file:
changed_files_and_symbols:
tests_run / command / result / remaining verification:
live_scope / authorization boundary / no secrets:
pending_effects / migration version / job or command receipt alias:
blocker / exact user action if needed:
next_action (một hành động cụ thể) / acceptance:
rollback_or_recovery / independent READY task:
```

Không thể đảm bảo ghi checkpoint đúng khoảnh khắc mất điện/token/mạng. Vì vậy lưu trước/sau batch nhỏ và phục hồi bằng diff + durable receipts. `/tmp` có thể mất: ghi kết quả đã khử định danh trong `docs/evidence/`, không phụ thuộc log tạm duy nhất. Không ghi credentials, raw payload khách hàng, email/serial đầy đủ hoặc cookie vào Git. Nếu evidence trước đó chứa dữ liệu nhạy cảm, xử lý theo phạm vi cho phép, không tự xóa cả lịch sử Git.

### 27. Hàng đợi thực thi tích hợp

Mục U/Q0/Q1 và I0–I6 ở Phần II vẫn là chi tiết kiến trúc; bảng này điều phối chúng theo hiện trạng, không tạo interface hoặc sidebar thứ hai. Cho phép sửa lỗi correctness/freshness và auth tối thiểu song song UI để QA được; chưa cho phép bỏ UI chưa nghiệm thu để tuyên bố “chỉ chờ tài khoản”.

| ID / trạng thái 08/10 | Thao tác theo thứ tự | Owner/file cần đọc/sửa | Điều kiện đóng / bước sau |
|---|---|---|---|
| LIVE-01 / IN_PROGRESS | .1 tải client mới, tái hiện BUG-LIVE-02; .2 mọi vùng monitor dùng cùng snapshot/revision và age, không phá form đang nhập; .3 kiểm nút manual/cooldown/partial; .4 ba chu kỳ tự cập nhật; .5 disconnect/reconnect/scope revoke; .6 hồi quy | `controller.py`, `data_workspace.py`, `app.py`, `streams.py`; `workspace.js`, `device-live-monitor.js`, `reading-refresh.js`, `journal-workspace.js`; reuse tests hiện có | Không freeze modal/tab, không nhãn realtime sai, không gọi vượt quota, không trộn nhà máy; fixture + live-read evidence. Chưa giải được source time phải giữ UNKNOWN |
| UI-01 / IN_PROGRESS | .1 lập reference map đủ 26 màn/15 sidebar; .2 token/layout chung; .3 sửa theo nhóm màn bên dưới; .4 interaction/empty/error/accessibility; .5 ảnh cùng viewport và visual diff; .6 audit tích lũy | `static/app.css`, shared shell và từng `*-workspace.js`; `docs/ui-design-system.md`, `docs/mockup-coverage.md`, `docs/sidebar-subtabs-architecture.md` | Mỗi màn có reference, states, screenshot nhận xét và regression. Không kết luận pixel-perfect từ HTML test hoặc chỉ 5 ảnh người dùng |
| GW-01 / IN_PROGRESS | .1 portal baseline read; .2 SolarOne link đúng platform/region; .3 inventory/site/serial; .4 station vs device; .5 time/units/sign; .6 cross-screen; .7 nguồn thiếu/401/429; .8 ghi ma trận supported/partial/unknown | `goodwe_connection.py`, `adapters/goodwe_plus.py`, shared read pipeline; matrix 11 ảnh đầu file | Cùng serial/kỳ/đơn vị và thời điểm so sánh, sai số có giải thích định lượng; không gán AC=PV, không gán tổng trạm cho mỗi inverter |
| GW-02 / TODO | .1 kiểm public source + contract quan sát được; .2 history power/MPPT/energy/runtime; .3 pin-parent identity; .4 alarms/recovery; .5 config read/capabilities; .6 UI reason/coverage | I2–I4; `integration.py`, `domain.py`, adapter, incident/history consumers | Từng endpoint có permission, pagination, timezone, bounds, mapping và tests; unsupported riêng, không khẳng định feature đầy đủ |
| IF-I0…IF-I6 / TODO, có lát cắt I1/I2 | Thi hành từng hàng theo hàm ở §§16–19; cập nhật call graph trước khi chuyển owner; hai dialect thử chung cho operation khả thi; giữ native extension khi semantics khác | Owners chính xác trong Phần II; không viết service cạnh tranh | Consumer thật đi qua owner chung, negative tests/revision/quality/readback, không capability giả. Đóng từng operation, không đánh dấu cả I2 chỉ vì GoodWe có panel |
| VQA-DEYE / WAITING_USER cho live | Research/fixture độc lập tiếp tục được; khi có account/app grant thực hiện VQA-01…08 dưới đây | Deye adapter/managed connection; `deye-developer-setup-vi.md` | Không giả email/password luôn đủ; App ID/secret phía vận hành/vault, user-facing flow phù hợp grant thật |
| VQA-OTHER / TODO | Solis → Growatt → Sungrow → Huawei → SOLARMAN → Eybond/SmartESS → Bluesun; có tài khoản/contract hãng khác sớm hơn thì đổi thứ tự và ghi lý do | Mỗi hãng reuse VQA; tài liệu API access + source registry | Mỗi platform/model/region có record riêng. Bluesun phải xác minh OEM/platform/logger, không tự nhân bản Deye driver |
| DE-00 / TODO ưu tiên bảo toàn dữ liệu | Xem §33: bounded observation archive tối thiểu, kế hoạch capacity/migration trước khi thu dài hạn; tích hợp I2/I3 | Store/collector/local-agent boundary | Lưu lần nhận và correction không giả source time; quota/retention/disk-full/restore được test; chưa phải warehouse hoàn chỉnh |
| READ-PILOT / TODO | UI scope pilot + live read + restart/revoke/gap recovery + soak/capacity/backup-restore | R11/R12/Q2 trong roadmap | Công bố cụ thể hãng/model/chức năng chỉ đọc đạt; known gaps/disabled reason; hardware write không bắt buộc để đóng pilot đọc |
| DE-01…DE-07 / TODO | Contracts → archive/versioning → canonical → backfill → marts/semantic/query → vận hành/retention | §33–35 | Có lineage/quality/cost/restore, không dùng operational DB làm warehouse không giới hạn |
| AI-01…AI-06 / TODO | Baseline/evaluation → anomaly → forecast → incident → SQL assistant → shadow/rollout | §36–37 | Chỉ advisory/read-only, grounding/abstention/scope và safety tests; không nối LLM đến command executor |
| RELEASE / TODO | Chốt scope, test/visual/live evidence, dependency/security, migration/rollback và điều kiện vận hành | Roadmap release gate | Production deployment là quyết định riêng của người dùng; không tự push/deploy vì kế hoạch ghi RELEASE |

### 28. UI-01 — làm hết màn, không chỉ các ảnh ví dụ

1. **UI-01.1 inventory:** dùng danh sách route thật + `mockup-coverage.md` làm nguồn. Mỗi route/subtab/modal ghi owner, mock gốc/path, viewport, data source/API, quyền, trạng thái còn thiếu. Đọc ảnh trong `images/` trực tiếp; ảnh SolarHub tổng hợp chỉ mô tả ý tưởng. Ảnh SEMS+ là bằng chứng chức năng, không đổi SolarOne thành giao diện đen của hãng.
2. **UI-01.2 nền thiết kế:** đối chiếu typography, độ rộng sidebar/header/content, spacing grid/card/form/table, màu/viền/bóng/radius, hierarchy, icon SVG chuyên nghiệp. Sửa token/component dùng chung trước, không chồng CSS riêng từng route. Ảnh thiết bị cần đúng model và quyền sử dụng; chưa xác minh dùng icon trung tính.
3. **UI-01.3 nhóm A giám sát:** tổng quan fleet/site, danh sách nhà máy, bản đồ, thiết bị/inverter/BMS/logger, chi tiết và lịch sử/biểu đồ. Chọn nhà máy kèm hãng/tài khoản theo quyền; không lộ email cho role không được phép. Data provenance/time/units nhất quán, unknown vẫn có bố cục hoàn chỉnh.
4. **UI-01.4 nhóm B vận hành:** alarms/incident, control, lịch TOU đủ bảy ngày và khung giờ trống, EMS/dispatch, network, rule editor. Tách xem/thử tính/preview/áp dụng; nested rule phải giữ semantics, không làm mất điều kiện khi chuyển form. Unknown topology không vẽ cạnh “đang hoạt động” giả.
5. **UI-01.5 nhóm C cấu hình/phân tích:** account linking/onboarding, nguồn dữ liệu, thu thập/mapping/chẩn đoán, tariff/report, maintenance/audit, models/settings và mọi subtab còn lại trong inventory. Thay nhập JSON thường ngày bằng field có đơn vị, validation và trợ giúp; raw advanced chỉ trong disclosure cho người có quyền. Thao tác chuyên sâu khóa có lý do/cách khắc phục, không “thành công” giả.
6. **UI-01.6 state matrix từng màn:** loading, empty, partial, populated, stale, offline/error, permission denied, unsupported, long text/many rows; keyboard/focus/modal/escape, responsive, VI/EN, zoom, submit double click và chuyển site khi request đang chờ. Fixture chỉ trong test isolation; QA app thật không seed.
7. **UI-01.7 visual acceptance:** chụp cùng viewport/mock scale, so spacing/baseline/alignment/contrast; overlay/diff nếu có reference đủ chất lượng. Chỉ mask vùng số/time thay đổi, không mask lỗi layout. Ghi sai lệch còn lại từng màn, không tự đặt phần trăm “khớp pixel” từ cảm nhận. Màn chưa có ảnh chuẩn dùng design system chung và đánh dấu suy rộng, không tuyên bố exact pixel reference.
8. **UI-01.8 đóng tích lũy:** mỗi row inventory có BE/FE/interaction/visual/live status riêng và bug IDs. Đừng thêm màn cạnh tranh để né sửa owner cũ. Chỉ đóng toàn bộ khi không bỏ sót route/subtab; feature chưa thể có dữ liệu vẫn phải có trạng thái trống/khóa đúng và đẹp.

### 29. VQA-01…08 — quy trình lặp lại cho từng hãng

Áp dụng GoodWe/Deye/Solis/Growatt/Sungrow/Huawei/SOLARMAN/Eybond/Bluesun, không đòi mỗi hãng có mọi chức năng.

| Bước | Thao tác và dữ liệu cần đối chiếu | Cổng / bằng chứng |
|---|---|---|
| VQA-01 chuẩn bị | Public primary sources, license/revision, API/platform/region/auth/grant, giới hạn quota; đọc source thật và test fixture | Official vs community vs observed tách riêng, không đoán từ logo/app splash |
| VQA-02 portal | User tự login; quan sát nhà máy, thiết bị/serial, role, model/fw/logger, kỳ/ngày/timezone, config hiện hành theo quyền | Chỉ đọc, không gạt switch/submit. Thiếu session mời user đúng một việc rõ ràng |
| VQA-03 liên kết SolarOne | User nhập qua form; xác thực, discovery, vault, renewal, revoke/logout/error; kiểm server scope | Không lấy cookie hãng thay connector, không log secret, không hiện app secret ở form chủ nhà khi do hệ thống quản lý |
| VQA-04 latest | Cùng site/device/metric/unit/source clock; ba chu kỳ và manual refresh; receipt age + vendor age riêng | Không so hai ảnh khác thời điểm rồi kết luận scale sai; source time thiếu phải nêu không thể chứng minh đồng thời |
| VQA-05 history/alarm | Date range/timezone/paging/gaps/counter reset/MPPT; alarm raised/updated/recovered, duplicate/reordered | Không sinh điểm bù, không coi không đọc được alarm là “0 lỗi”; raw/native khác canonical verified |
| VQA-06 capability/config | Đọc schema/range/enum/grant, binding/revision/current config; phân loại Native/Equivalent/Derived/Native-only/Unsupported theo Phần II | Model/fw exact + evidence; monitoring riêng vẫn dùng chung được envelope nhưng không được suy ra control semantics |
| VQA-07 write **WAITING_USER mặc định** | Chốt đúng thiết bị/tham số/giá trị/mức tác động/cửa sổ thử/điều kiện dừng; xác nhận riêng; snapshot cấu hình trước; pure preview; một canary; ACK rồi readback | Chỉ sau commissioning/safety gates. Không bật/tắt điện, đổi grid code, xả pin, EPS/cold-start hay OTA chỉ để “test hết”. Timeout → UNKNOWN/quarantine, không retry mù. Khôi phục cũng là lệnh, chỉ làm trong phạm vi được duyệt |
| VQA-08 hồi quy | Kiểm SolarOne mọi consumer liên quan, audit/provenance; reconnect/restart, hết quota, revoked account; cập nhật bugs/feature matrix | Live test không thay fixture và ngược lại. Chỉ mở đúng capability đã accepted; phát sinh lỗi quay lại owner chung rồi QA lại |

Không cần chờ mọi hãng để phát triển interface: chứng minh operation dùng chung trên ít nhất hai dialect khả thi, dùng simulator cho edge cases, đánh dấu hãng chưa live. Chức năng thiếu ở hãng có thể là derived nếu đủ đầu vào và semantics đã chứng minh; không biến tính toán advisory thành hỗ trợ điều khiển.

### 30. Sổ lỗi mới, nhánh rẽ và điều kiện dừng

| ID | Loại / ưu tiên | Bằng chứng, xử lý tiếp | Trạng thái |
|---|---|---|---|
| BUG-LIVE-01 | CONFIRMED_BUG / P1 | Modal freeze/cache station/cadence; code đã sửa, suite đạt; live latest-client còn cần xác minh | IN_PROGRESS / LIVE-01 |
| BUG-LIVE-02 | INVESTIGATE / P1 | Quan sát dialog cũ: report/native tự cập nhật, bảng thông số phía dưới khác snapshot. Reproduce sau reload mới; tất cả vùng read-only cần owner snapshot chung, không rebuild form điều khiển | READY / LIVE-01.1 |
| GAP-HISTORY-01 | CONFIRMED_GAP / P1 | `UNKNOWN` overwrite và latest entity upsert; không giữ mọi lần nhận/correction. DE-00 archive bounded, I3 backfill nếu hãng cho phép | TODO / DE-00 |
| GAP-GW-TIME-01 | CONFIRMED_GAP / P1 | Chưa source timestamp/timezone đủ tin cậy; chưa đưa native/report vào GOOD/EMS/billing | TODO / GW-02 + I2 |
| GAP-UI-ALL-01 | UNFINISHED / P2 | 26 màn chưa visual acceptance; advanced/network/EMS còn thiếu luồng, không chỉ chỉnh màu | IN_PROGRESS / UI-01 |

Khi gặp lỗi: tạo ID ổn định với severity, route/symbol, bước tái hiện, expected/actual, phạm vi/account alias, evidence khử định danh, root cause/hypothesis, regression, phụ thuộc và next step. **P0** quyền/safety/secret/cross-tenant hoặc phá dữ liệu → dừng hành động bị ảnh hưởng ngay, containment và báo người dùng; **P1** số liệu sai/mất dữ liệu/luồng chính hỏng → ưu tiên trước polish; **P2/P3** usability/cosmetic → cùng UI batch. Không tự coi thông báo API là lệnh làm việc.

Lỗi hãng/quota/network: tuân backoff, ghi freshness thật, không spam login/request. Thiếu tài khoản: chuyển việc độc lập. Migration/credential reset/hardware changes không rõ quyền: dừng đúng nhánh để hỏi. Nếu không còn việc an toàn trong scope, báo blocker cụ thể; không tạo vòng chờ vô hạn hoặc tuyên bố xong.

<a id="data-ai-plan"></a>
## Phần IV — Data Engineering và Applied AI (kế hoạch, chưa triển khai)

### 31. Hiện tại đã lưu được gì, chưa lưu được gì?

Đối chiếu code ngày 08/10, không suy từ tên bảng hoặc báo cáo “có history”:

| Thành phần hiện có | Hành vi thật | Thiếu so với lịch sử phân tích |
|---|---|---|
| `Store.put` / `entities` | Upsert body hiện tại; bao gồm `latest`, `station_report` | Không snapshot version mỗi lần nhận; bản cũ bị thay |
| `Store.revisions` / `entity_revisions` | Counter/tombstone chống ABA cho safety | Không chứa giá trị trước/sau; không phải CDC |
| `Store.add_samples` | PK device/metric/binding/source timestamp; timestamp thiếu dùng `UNKNOWN`; conflict cập nhật body/receipt | Cùng timestamp có sửa số cũng mất bản cũ; UNKNOWN chỉ giữ mới nhất. Mặc định 30 ngày, cap toàn bảng 1.000.000 điểm |
| `Store.history` / `report_samples` | Truy vấn giới hạn; history mặc định 1.000, tối đa 5.000; report có trần riêng | Không phải warehouse/full-history, không kết luận coverage từ một page |
| `Store.audit/verify_audit`, command records | Audit hash chain append-only với SQLite guards, command lifecycle | Không full before/after mọi entity; hash chain không tự thành archive bất biến bên ngoài hoặc backup |
| `IncidentService.append/apply_alarm/history` | Events vòng đời incident riêng, trạng thái alarm nguồn và incident | Không mặc định giữ toàn bộ raw vendor alarm timeline/backfill |
| Agent inbox / `Outbox.enqueue/flush` | Batch/sequence/digest và retry; latest metric, add_samples | Không phải analytical archive; duplicate delivery khác observation mới |
| Weather/forecast | Chưa chứng minh một weather pipeline đạt nghiệm thu | Không tạo weather hoặc forecast giả để có dữ liệu AI |

Read-only aggregate snapshot của DB pilot: **220 samples, 220 kênh device/metric/binding, cả 220 có `source_ts=UNKNOWN`; 6 latest entities và 1 station_report**. Đây là hiện trạng một thời điểm, không hứa giữ nguyên số lượng. Dữ liệu đã bị ghi đè không phục hồi bằng đổi schema; chỉ backfill được nếu hãng có history hợp lệ. Phân biệt **biến động vật lý**, **lần nguồn lấy mẫu**, **lần SolarOne nhận**, **thay đổi cấu hình do người dùng**, **correction do hãng**: không thể hứa lưu mọi biến động vật lý khi hãng chỉ trả snapshot mỗi phút.

### 32. Kiến trúc và hợp đồng dữ liệu

Luồng mục tiêu: vendor/local agent → ingestion có giới hạn → raw/native receipt archive → canonical observations/events → warehouse/lakehouse + semantic layer → báo cáo/Applied AI read-only. Operational current-state và command safety vẫn tách khỏi analytics; không dùng AI/warehouse trễ làm fresh readback để phát lệnh.

Hợp đồng đề xuất (tên dưới đây **chưa phải schema/hàm đã có**):

- `ObservationEnvelope`: observation/receipt ID, org/site/device/binding/integration ID, source/platform/model identity, credential **revision không secret**, schema/adapter/mapping version, batch/sequence, metric native/canonical, type/unit/raw unit, value/null, quality/reason, provenance/evidence và payload hash/ref.
- Thời gian: `source_event_at` nullable, raw clock/timezone evidence, `received_at`, persisted/processed times; metric clock có thể khác nhau trong một response. Không lấy receipt thay source time. Lưu `time_basis=receipt_only` cho nguồn thiếu clock, không cho vào event-time KPI như đã xác minh.
- Identity idempotency: source event/sequence đáng tin + scope + channel + version; không có event ID thì dedup replay theo receipt/batch ID. Cùng giá trị nhưng lần nhận mới có thể là heartbeat hữu ích, không được xóa dấu phủ dữ liệu. Cùng event time đổi value là correction revision liên kết bản trước, không overwrite âm thầm.
- Device/site/config dimensions giữ valid-time và recorded-time (SCD2/bitemporal khi cần), quan hệ parent/battery/logger có hiệu lực; lịch sử gắn nguồn/account phải còn hiểu được khi chuyển kết nối. Query luôn ràng buộc quyền hiện tại và policy lịch sử; không tự lộ dữ liệu chủ cũ.
- `ConfigChangeEvent`: actor, origin (SolarOne/vendor/unknown), sanitized before/after, command/correlation ID nếu có, planned/ack/readback/verified times; quan sát config đổi ở hãng không tự gán là do người dùng SolarOne.
- Weather quan sát tách forecast `issued_at/valid_at`, location/source/license/resolution/version; không leakage dùng forecast sửa sau để đánh giá dự báo quá khứ.
- Facts tách telemetry, energy interval/counters, alarms, state transitions, weather, audit/config changes và collection attempts. Raw unsupported vẫn archive trong policy nhưng không tự thăng GOOD. Marts phải trả coverage/freshness/quality/time basis và lineage.

### 33. Từng bước và từng hàm Data Engineering

Chỉ `Store.*`, collector, incident và agent methods ghi “hiện có” là source đã tồn tại. Tất cả tên class/method còn lại là **đề xuất**, cần chốt owner/module trước khi viết, tái sử dụng outbox/transactions phù hợp thay vì thêm poller.

| ID / phụ thuộc | Hàm/owner cần làm | Trình tự triển khai và kiểm chứng |
|---|---|---|
| DE-00 / RSM + storage audit | Hiện có `Controller.poll`, agent inbox, `Store.put/add_samples`; đề xuất `ObservationArchive.append_receipt`, `ArchiveOutbox.enqueue/ack` | (1) inventory mọi ingest path; (2) chốt envelope + hard byte/count budget; (3) migration additive và backup/restore trên bản test; (4) archive receipt hợp lệ trước latest projection, transaction/outbox manifest chống orphan; (5) delivery ít nhất một lần + replay idempotent; (6) UNKNOWN giữ các receipt khác nhau, không tạo source time; (7) test restart giữa append/commit/ack, disk full, redaction và backpressure. Chưa có đủ durability thì báo archive gap, không nhận “đã lưu đủ” |
| DE-01 / DE-00 | `DataContractRegistry.validate`, `IdentityResolver.resolve`, `QualityEvaluator.evaluate`, `ClockResolver.resolve` | Schema/version native→canonical, tenant/site/device scoping, numeric/string/null/zero, units/sign/timezone/DST/future/stale/sequence/reset; ambiguous identity vào quarantine. Test ít nhất hai vendor và local agent; invalid không làm hỏng cả batch hoặc lọt GOOD |
| DE-02 / DE-01 | `RevisionStore.append_correction`, `DimensionHistory.upsert_version`, `ConfigHistory.record_change`; hook Store/incident/command transaction | Lưu before/after đã loại secret, validity/revision/origin; current-view từ history; duplicate/no-op không tạo change giả; same-time correction không phá bản gốc; rollback transaction không sinh event “đã đổi”; tenant transfer/revoke và tombstone được test |
| DE-03 / DE-01–02 + I3 | `BackfillService.plan/run_page/checkpoint/cancel`, `WatermarkStore.advance`, `CoverageService.gaps` | Capability lịch sử của từng hãng, range/chunk/resolution/quota/page cursor; live ưu tiên hơn backfill; durable resume checkpoint sau commit; late/out-of-order/correction; reconciliation hash/count; không cộng trùng archive với vendor history. UI job tiến độ/hủy/retry và phần không thể phục hồi |
| DE-04 / DE-01–03 | `CanonicalProjector.project`, `MartBuilder.aggregate`, `EnergyCounterResolver.delta`, `LineageService.trace` | Bronze raw/native, silver canonical, gold marts; energy counter reset/rollover và khoảng đo; time-weighted SOC, coverage, expected samples theo cadence; rerun cùng input/version idempotent; corrections rebuild đúng partition và version KPI. Không cộng snapshot công suất thành kWh hoặc sum cả station và inverter |
| DE-05 / DE-04 | `SemanticCatalog.metric`, `AnalyticsQueryService.query`, `ExportService.export` | Chốt grain/aggregation/timezone/denominator cho KPI; read-only scoped views/API, bounded date/page/query budget; report history chart và export chung định nghĩa; trace về source/window/mapping; receipt-only tách verified analytics. Không query SQLite operational không giới hạn từ UI |
| DE-06 / DE-00 + benchmark | `RetentionPlanner.plan`, `Compactor.compact`, `ArchiveVerifier.verify`, `StorageBudget.estimate/enforce` | Benchmark volume thực đã khử định danh/synthetic, batch/compression/partition pruning; retention theo tier; preview lượng xóa, legal/privacy holds; compact atomic manifest/checksum rồi xác minh trước dọn; disk high-water/backpressure ưu tiên audit/events. Không thực thi purge dữ liệu hiện hữu ngoài scope được duyệt |
| DE-07 / DE-03–06 | `PipelineHealth.snapshot`, `Reconciler.compare`, `RecoveryService.restore` | Monitoring lag/quality/drops/quarantine/cost; disaster restore bản sao, replay/backfill sau outage; soak và query concurrency không làm nghẽn command engine; RPO/RTO/capacity được đo và chốt trước production |

Tests đề xuất theo behavior, reuse file hiện có khi trùng: archive durable/idempotency, unknown-clock receipts, corrections/history, lineage/quality, watermarks/backfill resume, tenant scope, aggregate units/gaps/reset, retention dry-run/restore, query resource limits. Tests dùng fixture riêng, không seed app thật.

**Lựa chọn storage theo giai đoạn:** DE-00 dùng bounded local append store/outbox phù hợp app local-first để không cần cluster. Sau benchmark, chọn columnar batch files + analytical reader cho pilot hoặc warehouse/lakehouse phục vụ nhiều tenant/concurrency. ADR phải so measured ingest/query/retention/backup/cost và deployment constraints trước khi chọn dependency. Không mặc định cần Kafka/Spark/cluster, cũng không dùng SQLite triệu-row cap hiện tại làm kho vô hạn. Mọi sink qua một contract archive/query, không nối logic vendor riêng trực tiếp vào mart.

### 34. Chống bùng nổ lưu trữ — không ghi theo nhịp render

Ba nhịp độc lập: **đo ở thiết bị**, **thu thập từ hãng/agent**, **cập nhật màn hình**. Màn hình vẽ 60 lần/giây hay đọc cache 15s không tạo 60/giây hoặc 1/15s records mới. Dashboard GET/WebSocket render không là ingestion. Manual refresh dùng chung cooldown/quota/collector; refresh trùng không nhân đôi archive.

1. **Cloud:** lấy theo cadence nguồn/quota có bằng chứng; SEMS+ cấu hình hiện tại tối thiểu 60s không là bảo đảm hãng phát mẫu mới mỗi 60s. Agent high-frequency chỉ khi use case + phần cứng cần, có quyền và benchmark; không mặc định millisecond.
2. **Batch:** một envelope chứa nhiều kênh; lưu payload blob theo hash trong scope và receipt refs thay vì nhân JSON metadata cho từng metric. Nếu body giống nhưng thời điểm nhận khác, vẫn giữ receipt/heartbeat coverage; credential/header không nằm trong raw archive. “Raw” là payload nghiệp vụ cần thiết đã redaction, không bản sao request bí mật.
3. **Dedup:** phân biệt retry cùng receipt với observation mới, content trùng với correction, source clock thiếu với known time. Không dedup chỉ dựa value hoặc timestamp; không bỏ alarm/state/config transitions. Native payload đã loại metadata biến động có thể content-address với versioned canonicalization, nhưng phải giữ envelope gốc cần thiết cho provenance.
4. **Aggregate:** bin 1/5/15 phút tùy use case, giữ min/max/first/last/count/missing/coverage, quality và time basis. Power là weighted mean hoặc tích phân có gap policy, energy là counter delta/interval đúng nghĩa, SOC không cộng. Deadband/change-only chỉ sau domain review từng metric, không áp mù cho energy counter/alarms/audit; cần heartbeat để phân biệt không đổi với mất dữ liệu.
5. **Tier/retention đề xuất để benchmark, chưa áp dụng:** raw và high-resolution 7–30 ngày; minute aggregates 90 ngày; 15-minute 2 năm; daily 5 năm. Alarm/config/audit có policy riêng theo nhu cầu truy vết/privacy. Không tạo dữ liệu 1 phút giả từ nguồn 5 phút; mỗi aggregate khai báo resolution/coverage thực. Thời hạn cuối cùng phải chốt bằng dung lượng/ngân sách/quyền lưu trữ; không hứa lưu “mọi lần” vĩnh viễn.
6. **Giới hạn:** per-source/org/day bytes, count, queue age và tổng disk hard cap; warning sớm, bounded buffer, backpressure/quota-aware scheduling, dead-letter đã loại bí mật; đo dropped/rejected count + gap reason. Không nuốt lỗi đầy đĩa, không xóa audit để giữ telemetry, không tăng sample cap vô hạn. Thay cadence phải hiện trạng thái và ghi policy, không âm thầm giảm chất lượng.
7. **Compaction/partition:** tổ chức theo date + tenant/site hợp lý và hash buckets nếu cần; tránh một file cho mỗi metric/receipt hoặc quá nhiều tiny partitions. Batch theo byte/rows/time bounded; compression và file size từ benchmark. Không dùng tên email/serial làm object path công khai.

Ví dụ **minh họa capacity, không phải số đo dự án**: 100 site × 5 device × 40 metric = 20.000 kênh.

| Tần suất ghi mọi kênh | Giá trị/ngày | Nếu giả định 80 byte/giá trị, trước index/replication/backup |
|---|---:|---:|
| 60 giây | 28.800.000 | 2,304 GB/ngày |
| 1 giây | 1.728.000.000 | 138,24 GB/ngày |
| 1 mili giây | 1.728.000.000.000 | 138,24 TB/ngày |

Công thức: `sites × devices × metrics × 86.400 / interval_seconds`. Đơn vị dung lượng ở bảng là thập phân. JSON thực có thể lớn hơn nhiều; compression có thể giảm nhưng chưa đo nên không cam kết hệ số. 500 devices gửi batch một phút là 720.000 envelopes/ngày, **vẫn 28,8 triệu giá trị** nếu giữ 40 kênh: batching giảm overhead/object count, không làm mất số lượng thông tin. Capacity report phải bao gồm raw + canonical + marts + index + replicas/backups + retention, tăng trưởng 1/3/12 tháng, query scan và p95 latency, không chỉ một bảng samples.

### 35. Semantic layer và các mart dự kiến

| Mart/view đề xuất | Grain và nguồn | Cấm suy diễn / tiêu chí |
|---|---|---|
| `telemetry_quality_hourly` | device/source/hour; collection attempts + samples + expected cadence | Stale source-age riêng receipt-age; timestamp thiếu không coi fresh. Expected cadence/version lưu theo thời kỳ |
| `site_energy_daily` | site/local-calendar-day/source/metric; meter hoặc vendor energy đã phân loại | Không cộng station với thiết bị, không so partial-day với full-day, coverage/timezone bắt buộc |
| `device_energy_daily` | exact device/day; counter delta hoặc dated interval | Correction/reset/gaps phải giải thích, missing không zero |
| `battery_soc_hourly` | battery/device/time bucket; weighted SOC + coverage | Không gán SOC station cho pin con; “SOC trung bình” time-weighted hay capacity-weighted phải khai báo |
| `alarm_lifecycle` | source-alarm occurrence + revisions/recovery và incident liên quan | Dedup occurrence không xóa lặp lại thật; ack khác resolved/recovered |
| `device_state_history` / `configuration_changes` | entity + valid interval + recorded revision | Chỉ biết thời điểm quan sát thay đổi không giả thời điểm vật lý; actor unknown khi không biết |
| `weather_observation` / `weather_forecast` | location/source/observed or issued/valid time | Quyền sử dụng, resolution, missing và thời gian phát hành giữ riêng |

Semantic catalog định nghĩa PV vs AC, import/export, charge/discharge, kW/kWh, timezone, role permissions và quality filters dùng chung report/API/AI. Query response gồm tables/views, dataset version, query window/timezone, max event/receipt time, coverage, stale/unknown share, aggregation và limitations. So sánh hãng nên kèm công suất lắp đặt/độ phủ khi có, không kết luận hãng tốt/xấu từ tổng kWh không cùng quy mô.

### 36. Applied AI — từng bước/hàm, chỉ tư vấn

Mọi class/method AI sau là đề xuất, không tính là đã triển khai. Không chọn model/provider trả phí hoặc gửi dữ liệu khách hàng ra ngoài chỉ vì runbook có bước AI; cần chốt privacy, nơi xử lý và phạm vi được phép.

| ID / phụ thuộc | Hàm đề xuất | Công việc / acceptance |
|---|---|---|
| AI-01 / DE-04–05 | `AnalyticsDataset.build`, `EvaluationSuite.evaluate`, `AdvisoryPolicy.allow` | Dataset version/lineage, quality thresholds theo metric/use case, temporal/site holdout tránh leakage; baseline đơn giản trước ML/LLM. Thiếu coverage phải abstain, không sinh kết luận. Chốt tiêu chí và tập test trước tuning |
| AI-02 / AI-01 | `AnomalyDetector.detect`, `ExplanationBuilder.explain` | Mất telemetry khác PV thấp; xét ngày/đêm/weather/công suất/ràng buộc vận hành có evidence. Kết quả score/baseline/window/cause hypotheses; đánh giá precision/recall, false alarms/site/day, duplicate incidents. Không tự tạo lệnh hay khẳng định root cause |
| AI-03 / AI-01 + weather/energy đủ | `ProductionForecaster.predict`, `SocForecaster.predict`, `ForecastEvaluator.score` | Forecast horizon/issued time/interval uncertainty; MAE và metric phù hợp near-zero, so persistence/seasonal baseline; SOC cần capacity/load/charge policy đã biết, thiếu thì từ chối. Walk-forward, phân vendor/model và drift |
| AI-04 / DE alarm/config history | `IncidentSummarizer.summarize`, `EvidenceRetriever.retrieve` | Timeline source-cited, điều gì biết/chưa biết, nguyên nhân có bằng chứng, gợi ý bước kiểm tra; notes/vendor text là untrusted, không theo prompt injection. Đánh giá hallucination/omission và operator review |
| AI-05 / DE-05 + AI-01 | `SolarQueryPlanner.plan`, `SqlPolicy.validate`, `ReadOnlyQueryExecutor.execute`, `AnswerRenderer.render` | §37: chỉ semantic views và scoped analytics, AST + DB enforcement, citations/limits; câu hỏi mơ hồ hỏi lại hoặc nêu giả định; không API control, không credentials trong context |
| AI-06 / AI-02…05 theo feature | `AdvisoryRegistry.version`, `FeedbackService.record`, `DriftMonitor.check` | Shadow read-only trước; version prompts/model/dataset, evaluation regression, latency/cost cap, incident/error logs đã redaction, kill switch/rollback từng feature. Human feedback không tự thăng thành ground truth |

AI output tối thiểu: loại tư vấn, scope, khoảng dữ liệu, kết quả/đơn vị, confidence hoặc uncertainty có căn cứ, evidence refs, freshness/coverage, limitations, model/rule/version và gợi ý bước tiếp theo. Không có `execute_command` tool cho AI. Người dùng muốn điều khiển phải đi qua workflow command engine/safety hiện hữu và xác nhận riêng; không “AI đề xuất” → tự submit.

### 37. Solar Text-to-SQL: contract, bảo vệ và bài kiểm thử

1. Resolve quyền/site/device/timezone ở server, không để LLM tự chèn filter là lớp bảo mật duy nhất. Analytics account chỉ SELECT trên allowlisted views; row-level policy hoặc query service ràng buộc scope độc lập. Tách DB/network credentials khỏi production command store và vault.
2. LLM lập query trên semantic catalog, không introspect mọi bảng hoặc raw JSON khách hàng. `SqlPolicy.validate` dùng parser/AST: một SELECT, allowlist tables/columns/joins/functions, từ chối DDL/DML/multi-statement/unsafe CTE/UDF/external file/network/extension và system catalogs. Parameterize giá trị; prompt “read-only” không thay quyền DB.
3. Bắt buộc bounded date range, timeout, row/scan/memory budget, concurrency và cancel. LIMIT không đủ chặn full scan/cartesian join. Kiểm plan/cost trước chạy; không tự retry query tốn tài nguyên vô hạn. Cache scoped theo user permission revision + dataset version; revoke làm mất quyền đọc cache.
4. Render câu trả lời từ query result thật, nguồn view/table + lineage, query window/timezone, dữ liệu đến lúc nào, quality/coverage/freshness và điều không kết luận được. Cho xem SQL đã khử thông tin nhạy cảm khi phù hợp quyền. Query rỗng không là “mọi thứ bình thường”.
5. Test cross-tenant/SQL/prompt injection, untrusted alarm notes, ambiguous metric, stale/receipt-only/gaps/DST/reset, resource exhaustion, hallucinated columns, revoke giữa plan/execute và xuất dữ liệu. Không điền mock data vào app để demo AI; fixture chỉ môi trường test.

| Câu hỏi nghiệm thu người dùng | View/logic cần | Kết quả phải giải thích |
|---|---|---|
| Site nào sản lượng thấp bất thường 7 ngày qua? | `site_energy_daily` + baseline/capacity/weather nếu đủ | Baseline/window/coverage, partial-day, night/weather/capacity confounders; thiếu baseline thì không gọi “bất thường” |
| Inverter nào mất telemetry nhiều nhất? | `telemetry_quality_hourly` + lịch cadence | Missing/expected denominator, outage so với vendor clock unknown, thiết bị chưa hoạt động loại riêng |
| So sánh sản lượng Deye và Growatt theo ngày | Site/device energy và effective vendor dimensions | Cùng timezone/period, tránh double count/đổi vendor history; kWh và capacity-normalized nếu đủ metadata |
| Alarm nào lặp lại chưa xử lý? | `alarm_lifecycle` + incident status | Occurrence thật, cùng device/code trong window, recovered khác ack/closed |
| SOC trung bình các site tuần này? | `battery_soc_hourly` + device/site relationships | Time-weighted, coverage; capacity-weighted chỉ nếu đủ capacity. Không trộn station SOC với battery SOC |
| Vendor nào tỷ lệ stale cao nhất? | `telemetry_quality_hourly` | Threshold/cadence theo nguồn, denominator/time window; unknown-source-clock là nhóm riêng, không đánh đồng stale |

Đóng AI-05 khi test expected query/result/citations/scope đạt trên bộ fixtures versioned, query thực read-only được nghiệm thu với dữ liệu đủ chất lượng và negative tests không thể chạm command engine. Không hứa “hỏi gì cũng đúng”; trả “chưa đủ dữ liệu” là hành vi đúng khi bằng chứng thiếu.

### 38. Bàn giao và quy tắc hoàn thành

- Sau mỗi batch cập nhật **checkpoint đầu file** + trạng thái bước + bug ledger/evidence, rồi đồng bộ roadmap/mock coverage. Nếu phát hiện scope lớn hơn, tách substep cụ thể thay vì câu “tiếp tục xử lý”.
- Khi đủ Q0 và thiếu login, mở đúng form để user nhập, nêu hãng/platform và phạm vi QA đọc. Không báo “đã sẵn sàng kiểm thử tài khoản thật” cho mọi hãng chỉ vì một GoodWe login được.
- Khi hết các bước READY, báo đúng điều kiện chờ, không tự mở quyền/điền data giả để vượt gate. Lệnh “tiếp tục quy trình” là tiếp tục công việc đã giao, không cấp quyền hardware, reset password, purge production, trả phí, gửi dữ liệu ra ngoài hoặc deploy.
- Hoàn tất runbook/document khác hoàn tất sản phẩm. Warehouse/AI chỉ chuyển từ TODO khi có implementation + tests + evidence tương ứng. Không dùng kết quả 1.894/104 của code hiện tại làm chứng nhận các module tương lai.

### Kiểm tra đợt bổ sung runbook 08/10/2026

Đã đối chiếu `Store.put/add_samples/history`, revisions/audit và incident/agent owners;
lưu hiện trạng, backlog theo hàm và điểm tiếp tục ở đầu file. Đã đồng bộ entry point
trong `AGENTS.md`, roadmap và docs index. Ruff, syntax 61 file JavaScript và kiểm
whitespace đạt; source registry hai nơi giống nhau; inventory đã đo lại, không dùng
LOC làm phần trăm hoàn thành. Full suite 1.894 BE/104 UI là kết quả lát cắt freshness
trước khi thêm tài liệu này, không chạy lại chỉ vì thêm runbook. Chưa triển khai
archive/warehouse/AI và chưa gửi lệnh thiết bị thật. Browser latest-client QA còn mở
vì tab lỗi/điều hướng chưa phục hồi; không đổi thành VERIFIED.

<a id="session-journal"></a>
## Nhật ký bàn giao giữa các phiên

### SESSION-2026-10-09-01 — bàn giao lượt trước, ưu tiên kiểm tra an toàn

- **Nguồn:** tóm tắt hội thoại được phục hồi; không phát lại thao tác phiên trước. User yêu cầu tiếp tục rồi hỏi có đổi thiết lập làm lưới cấp tải không; tạm dừng implementation để kiểm tra read-only theo yêu cầu cụ thể mới.
- **Đã làm lượt trước:** LIVE-01.2 đưa report/native/flow/history/connectivity/latest/raw vào shared refresh, giữ filters/disclosure/presentation toggles và guard focus/fullscreen; không sửa adapter/control. Thay đổi nằm trong dirty worktree, chưa commit/push/deploy.
- **Kiểm chứng được bàn giao:** 34 BE liên quan đạt; UI suite 106 đạt trước patch toggles/focus cuối; sau patch 5 UI liên quan đạt, Ruff/build đạt. Chưa chạy lại full BE; baseline 1.894 không phải kết quả mới. Cần syntax/diff cuối batch mới.
- **QA thật lượt trước:** user đăng nhập SolarOne; chi tiết inverter ghi nhận AC trên/dưới khớp -0,85 rồi -0,92 kW; nút đọc mới trả WAITING/quota đúng; một receipt tiếp theo thấy -0,84 kW ở panel trên nhưng chưa đối chiếu bảng dưới. Không nghiệm thu đủ ba chu kỳ, không có đối chiếu SEMS+ cùng thời điểm. Các endpoint refresh chung render nhưng chưa transactional snapshot.
- **Môi trường mới kiểm:** ngày 09/10 không thấy listener 8765 trong lần kiểm; chưa khởi động server hoặc thu thập mới. SQLite mở read-only đúng data/solar.db: commands=0, plans=0; audit security=10, system=1, không control event. Không có bằng chứng lệnh SolarOne; không suy đây là nhật ký mọi thao tác trên portal hãng.
- **Ảnh mới user cung cấp:** SEMS+ ghi pin đang Sạc; PV 44,793 + grid 2,549 = battery charge 44,492 + load 2,85 kW. Chỉ là quan sát ảnh, không dùng làm seed/test data hoặc kết luận setting hiện hành.
- **Việc tiếp:** đọc design system/energy-flow, cải thiện tách nhánh/nút và chuyển động có căn cứ; không suy phân bổ từng nguồn→tải/pin chỉ từ bốn công suất tổng. Đọc chế độ/lịch/SOC thực nếu cần chẩn đoán nguyên nhân, không toggle/submit/hardware writes. Chốt evidence và checkpoint sau batch.

### SESSION-2026-10-08-01 — lưu đoạn chat trước khi tiếp tục

- **Nguồn:** đoạn hội thoại trước và checkpoint hiện có, lưu đầu lượt tiếp tục ngày 08/10/2026 (Asia/Saigon); chưa kiểm lại runtime trong lượt này.
- **Yêu cầu trước:** lập quy trình tiếp tục toàn UI/QA hãng/interface/DE/AI và giới hạn dung lượng lưu dữ liệu; người dùng chỉ cần gọi tên backlog để tiếp tục.
- **Đã làm:** thêm checkpoint, Phần III runbook, Phần IV kế hoạch DE/AI, từng bước/hàm, gates và bug ledger; nối `AGENTS.md`, roadmap, docs index; cập nhật evidence, mock coverage và inventory. DE/AI vẫn kế hoạch, không có implementation mới.
- **Kiểm chứng trước:** kiểm links/anchors/whitespace sáu tài liệu và diff đạt; Ruff, syntax 61 JS đạt. Suite 1.894 BE/104 UI và build thuộc lát cắt freshness trước đó, không phải chạy mới cho tài liệu hoặc nghiệm thu phần cứng.
- **Hiện trạng được ghi nhận:** sample thiếu source time ghi đè UNKNOWN, chưa lịch sử mọi lần nhận; BUG-LIVE-02 cần tái hiện — panel trên tự cập nhật nhưng bảng dưới khác snapshot. UI 26 màn và live acceptance chưa hoàn tất.
- **Thao tác cuối/môi trường:** mở backlog trong Codex; khởi động lại một server read-only đúng repo/data-dir sau khi không còn listener. Tab QA cũ connection-refused, browser chặn điều hướng; chưa QA client mới. Không tin PID/session còn sống ở lượt sau.
- **Không thực hiện:** không seed app, hardware write/unlock, commit/push/deploy, migration warehouse hoặc gửi dữ liệu cho AI.
- **Việc tiếp:** RSM-00 kiểm Git/process/docs liên quan; LIVE-01.1 xác minh/sửa một snapshot read-only toàn modal, regression rồi live QA theo điều kiện phiên. Không yêu cầu lại mật khẩu hãng chỉ vì tab lỗi.
- **Quy tắc mới nhận ở lượt này:** bắt buộc checkpoint + nhật ký lượt trước trước mọi công việc tiếp; đã thêm vào backlog và `AGENTS.md` trước khi tiếp tục.

### SESSION-2026-10-08-02 — bàn giao khi nhận tiếp tục trong lúc đang làm

- **Nguồn:** công việc/outputs ngay trước yêu cầu tiếp tục mới; ngày 08/10/2026 Asia/Saigon. Đây là checkpoint giữa batch, không phải batch đã hoàn thành.
- **Đã làm trước:** lưu SESSION-01 và quy tắc checkpoint-first vào AGENTS/backlog; đọc design system, kiểm dirty tree/branch; xác nhận code BUG-LIVE-02 dùng snapshot cũ ở các vùng ngoài monitor.
- **Code đang sửa:** `device-live-monitor.js` thêm loader/render cho vùng chỉ đọc, clear toàn bộ khi request lỗi, giữ lựa chọn kênh theo identity hiển thị thay array index, giữ disclosure; `workspace.js` và `journal-workspace.js` đưa flow/history/connectivity/latest/raw cùng vào monitor. `energy-flow.js` đánh dấu hai toggle presentation để giữ trạng thái; thêm guard focus/fullscreen đổi trong lúc request đang chờ.
- **Test trước patch toggles cuối:** 5 browser tập trung đạt (25,52s), 34 BE liên quan đạt (2,75s, 2 dependency warnings), build wheel/sdist thành công; Ruff/diff/syntax ba file đạt. UI suite đầy đủ đang chạy, chưa có kết quả. Patch toggles/focus vừa bổ sung chưa kiểm lại, không thừa nhận VERIFIED.
- **Tài khoản/môi trường:** không có tab cũ/listener lúc khảo sát. Khởi động đúng một server read-only port 8765; tab SolarOne mới hiện form đăng nhập. Đã hỏi user đăng nhập lại SolarOne qua câu hỏi async; chưa cần GoodWe. Không đọc password/autofill, không gửi hardware command.
- **Thao tác cuối:** sửa test giữ table-view/pause-motion và guard tương tác, căn lề cơ học hai renderer. Chưa commit/push/deploy, chưa seed app thật.
- **Việc tiếp chính xác:** thu kết quả suite đang chạy, affected regression sau patch cuối, cập nhật evidence/checkpoint; kiểm phiên login thật rồi QA ba chu kỳ/manual/failure. Nếu user chưa login, fixture/visual QA độc lập tiếp tục. Không chạy server/poller thứ hai.
