# Đánh giá sau baseline feb82ef — chờ duyệt, chưa triển khai sửa lỗi

> Cập nhật trạng thái: người dùng đã duyệt tạo nhánh và triển khai, yêu cầu bỏ seed data. Báo cáo bên dưới giữ nguyên như snapshot audit trước sửa; tiến độ và kiểm chứng mới nằm ở [real-data remediation](real-data-remediation-2026-09-27.md). Không dùng số lỗi cũ làm kết quả nhánh sửa.

Ngày: 27/09/2026. Repository: `/Users/toanlamsaoduocc/Desktop/solar-fleet-ems`.

## 1. Phạm vi và kết luận

- Baseline người dùng đã xem: `feb82ef`.
- HEAD chốt đánh giá: `897d611f63aa0636db8a2f955e7a8a195691f0b8`, nhánh `master`, đồng bộ `origin/master` tại lần pull của đợt audit này.
- Đã chạy `git pull --ff-only origin master`: fast-forward từ `8ec68fd` tới `897d611`, không reset hoặc ghi đè chỉnh sửa local. Working tree sạch trước khi tạo báo cáo.
- Ba commit sau baseline: `bfcd21d` (register/tariff/health/dispatch), `8ec68fd` (Phase D và các module hãng), `897d611` (SmartESS Local). Tổng diff: **85 file, +30.153/-164 dòng**. Đây là quy mô thay đổi, **không phải tỷ lệ hoàn thành**.
- Sidebar thực tế có **15 mục**, xác nhận tại `/Users/toanlamsaoduocc/Desktop/solar-fleet-ems/src/solar_fleet/static/workspace.js:56–102`. Giữ nguyên sidebar, shared shell và các workspace. Không đề xuất gom menu.
- Bổ sung nhiều decoder, compiler và thuật toán có ích, nhưng nhiều đường mới dừng ở **form → API → tính toán/mô phỏng**; chưa phải **thiết bị thật → adapter → storage → vận hành có kiểm chứng**.
- Có regression chặn mapping/catalog, dữ liệu sức khỏe dựng sẵn, xác thực mock và nhãn thực thi/readback không phản ánh thiết bị thật. **Không chấp nhận các tuyên bố “100% completed/verified” như bằng chứng sẵn sàng vận hành.**
- Audit này chỉ thêm tài liệu. Mọi sửa mã, đổi UX, thêm capability hay bật ghi phải được người dùng duyệt trước.

### Mức chắc chắn

Phát hiện dưới đây phân biệt đọc mã, tái hiện cục bộ và rủi ro cần xác minh. Không dùng credential thật, session browser của người dùng hoặc phần cứng. Không kiểm chứng toàn bộ register/protocol của hãng bằng tài liệu gốc trong đợt này; không cấp trạng thái hỗ trợ thiết bị từ tên hãng hay fixture.

## 2. Phát hiện ưu tiên

### A01 — P0: JSON registry lỗi làm hỏng cả luồng cũ

**Bằng chứng:** `/Users/toanlamsaoduocc/Desktop/solar-fleet-ems/src/solar_fleet/data/source-registry.json:1270–1271` có dấu phẩy thừa sau thuộc tính cuối object. `json.loads` báo `JSONDecodeError`. Test mapping, agent/model library, native catalog và source registry cùng gặp lỗi này.

**Ảnh hưởng:** phần bổ sung registry phá các integration point đã có trước baseline, không chỉ màn hình mới. Build wheel vẫn thành công, nên build xanh không phát hiện tính hợp lệ dữ liệu đóng gói.

**Khoanh vùng regression:** parse trực tiếp bằng `git show` xác nhận JSON hợp lệ tại `feb82ef` và `bfcd21d`, lỗi từ `8ec68fd` và còn ở `897d611`. Registry trong docs hiện parse được (61 record), packaged registry không parse được.

**Đề xuất chờ duyệt:** validate toàn bộ JSON; đối chiếu packaged registry với `/Users/toanlamsaoduocc/Desktop/solar-fleet-ems/docs/evidence/source-registry.json`; rà schema, unique ID, source pin và reference; không chỉ xóa dấu phẩy rồi coi provenance đã đạt. Thêm gate parse/schema vào CI/package validation.

### A02 — P0: SmartESS báo EXECUTED/readback_verified dù chỉ đổi object trong bộ nhớ

**Bằng chứng:** `/Users/toanlamsaoduocc/Desktop/solar-fleet-ems/src/solar_fleet/phase_d_api.py:1955–1993` luôn tạo `SmartEssLocalClient(..., simulated=True)`. Request nhận `unlocked` từ client; dependency chỉ là user đăng nhập. `/Users/toanlamsaoduocc/Desktop/solar-fleet-ems/src/solar_fleet/smartess_local_client.py:666–711` khởi tạo số mẫu; `:722–731` trả số mẫu; `:733–811` đổi state rồi trả `EXECUTED`, `readback_verified=True` mà không đọc thiết bị.

**Tái hiện:** gọi `SmartEssLocalClient(simulated=False).execute_command_safely('output_priority', {'priority': 1}, unlocked=True)` vẫn trả EXECUTED/readback_verified. Không có network write trong phép tái hiện. `simulated=False` không biến code này thành transport thật.

**Ảnh hưởng:** người dùng có thể hiểu nhầm đã điều khiển thiết bị. Mỗi request tạo client mới nên state mô phỏng không tồn tại giữa command và poll. Endpoint command cũng không chuyển `devaddr` vào method thực thi.

**Đề xuất:** đổi hợp đồng sandbox thành SIMULATED/COMPILED, không đọc lại giả; cấm client tự cấp commissioning. Nếu triển khai transport thật, bắt buộc binding/site/role/identity/evidence, command preview/digest, idempotency, serialization, audit và readback độc lập qua engine chung. Không kết luận đang có bypass ghi phần cứng: hiện đã chứng minh **bypass nhãn an toàn**, chưa chứng minh physical write.

### A03 — P1: GoodWe login luôn dùng mock, kể cả nhập credential

**Bằng chứng tại HEAD:** `/Users/toanlamsaoduocc/Desktop/solar-fleet-ems/src/solar_fleet/phase_d_api.py:1464–1587` (khối GoodWe). Nhánh không có tài khoản trả `authenticated=True` kèm simulated; nhánh có tài khoản/password xử lý `mock_response` rồi trả `status=success`. Station/monthly trả payload dựng sẵn khi không có đầu vào.

**Ảnh hưởng:** màn hình mới không chứng minh tài khoản hoạt động; trùng trách nhiệm với integration GoodWe trong `/Users/toanlamsaoduocc/Desktop/solar-fleet-ems/src/solar_fleet/adapters/plugins.py` và adapter hiện hữu. Không nên yêu cầu người dùng nhập secret cho màn hình chỉ mô phỏng.

**Đề xuất:** account/auth/discovery đi qua registry, vault và adapter chung; parser sandbox chỉ nhận fixture rõ nhãn, không báo authenticated và không nhập password thật. Test invalid credential phải không thành công.

### A04 — P1: “Exact model” thực tế chỉ kiểm tra chuỗi không rỗng

**Bằng chứng:** `/Users/toanlamsaoduocc/Desktop/solar-fleet-ems/src/solar_fleet/vendor_registers.py:337–445`. `KNOWN_MODELS_PER_VENDOR` không được dùng để xác nhận model trong decoder/register lookup; fallback còn match substring brand.

**Tái hiện:** `get_vendor_registers('goodwe', 'NOT-A-REAL-MODEL')` trả `VERIFIED_AUDITED`; `decode_vendor_alarm('goodwe', 1, model='NOT-A-REAL-MODEL')` trả CRITICAL và SOP thay relay.

**Đề xuất:** match profile chính xác với model/logger/firmware/protocol; thiếu evidence trả UNKNOWN. Tách community candidate khỏi commissioned support. Test model lạ, firmware khác, brand substring và bitfield/code khác dialect. SOP chỉ đưa ra khi semantics đã được xác nhận.

### A05 — P1: Bảo trì và battery health tạo cảm giác đo được khi thiếu dữ liệu

**Bằng chứng:** `/Users/toanlamsaoduocc/Desktop/solar-fleet-ems/src/solar_fleet/static/maintenance-workspace.js:227–242` hiển thị cố định 18 mV, 1,24 mΩ, 96,4%, 412 chu kỳ và 28,5°C cùng badge tốt.

`/Users/toanlamsaoduocc/Desktop/solar-fleet-ems/src/solar_fleet/battery_health.py:224–269` mặc định 10 kWh, tuổi 180 ngày, throughput `cap * 25`, nhiệt độ 28,5°C; tích phân giả định mọi sample dài 5 phút, rồi ngoại suy tuổi đời. Trường BMS SOH dùng `samples[-1]` trong khi `/Users/toanlamsaoduocc/Desktop/solar-fleet-ems/src/solar_fleet/storage.py:249–271` trả newest-first: đang chọn điểm cũ nhất trong nhóm, không phải mới nhất. Nhiệt độ cộng giá trị khác null nhưng chia cả số phần tử, gây lệch nếu có null. Site endpoint bỏ qua exception của từng pin mà không trả coverage/error.

**Đề xuất:** null/UNKNOWN khi thiếu dữ liệu; tách BMS measured khỏi model estimate; trả provenance, thời gian, coverage và assumptions. Tích phân theo timestamp/quality và chiều công suất đã được profile xác nhận; chọn sample fresh; không phán bảo hành khi thiếu specification/commissioning thật. Bảo trì tiêu thụ cùng health service thay vì số riêng.

### A06 — P1: Dispatch/tariff dùng tải giả và giả định năng lượng thiếu kiểm soát

**Bằng chứng:** `/Users/toanlamsaoduocc/Desktop/solar-fleet-ems/src/solar_fleet/forecast_baseline.py:360–395` mặc định vị trí TP.HCM, PV 50 kWp, pin 30 kWh; luôn tạo đường tải tổng hợp. `.hour` lấy từ thời gian UTC trong khi lịch tariff theo timezone site. Dùng `or` cũng thay tọa độ hợp lệ bằng 0 thành default. `:220` cố định nhóm giá manufacturing/medium voltage; `:325` kẹp savings âm về 0, che kết quả mô phỏng lỗ.

`/Users/toanlamsaoduocc/Desktop/solar-fleet-ems/src/solar_fleet/tariff_engine.py:334–365` tính sample W thành kWh theo 5 phút, cộng grid của mọi device tại site không xét boundary/counter duplication, sinh tải nếu không có telemetry; Q luôn ước tính bằng 35% P. Chưa có bằng chứng đủ để dùng làm hóa đơn/PF penalty thực tế.

**Đề xuất:** hai chế độ rõ ràng “Kịch bản giả định” và “Đánh giá theo dữ liệu”; cùng forecast/tariff configuration service; timestamp/timezone/interval đúng; meter boundary và coverage; giữ savings âm; tariff có văn bản, ngày hiệu lực, đối tượng và phiên bản. Mức giá/quy định pháp lý hiện hành chưa được xác minh độc lập trong audit này.

### A07 — P1: Compiler cho phép người gọi đổi nhãn commissioning

**Bằng chứng:** `/Users/toanlamsaoduocc/Desktop/solar-fleet-ems/src/solar_fleet/growatt_sph_modbus.py:326–335,387–407,472–492` đặt `COMMISSIONED_WRITE_ENABLED` khi `bypass_safety=True`; `/Users/toanlamsaoduocc/Desktop/solar-fleet-ems/src/solar_fleet/phase_d_api.py` expose trường này trong request và truyền trực tiếp vào compiler Solis/Growatt.

**Đề xuất:** compiler chỉ trả candidate frames; capability/evidence do server xác minh, không do boolean request. Không dùng tên safety gate để thay thực thi các kiểm tra. Chưa quan sát network write từ các compiler endpoint; cần tránh diễn giải lỗi nhãn thành exploit ghi đã được chứng minh.

### A08 — P2: UI mới vi phạm design system và tăng tải nhận thức

**Bằng chứng:** `/Users/toanlamsaoduocc/Desktop/solar-fleet-ems/src/solar_fleet/static/device-workspace.js` có nhiều `.style.*` (ví dụ width tại dòng 626/634 ở phiên bản trước SmartESS; các vị trí này không đổi do append). Test `test_all_pages_share_one_global_stylesheet` thất bại. Device workspace thêm nhiều subtab protocol/vendor vào cùng khu vực vận hành.

**Đề xuất:** giữ 15 sidebar; giữ vendor-native feature khi cần, nhưng đặt công cụ protocol dưới tab kỹ thuật có nhãn sandbox rõ. Dùng class của app.css, không inline style/per-route CSS. Luồng mặc định đơn giản: chọn site/device → dữ liệu và freshness → thao tác phù hợp capability → kết quả/audit. Không coi JavaScript parse pass là UI acceptance.

### A09 — P2: Nhiều engine song song, chưa có workflow/storage ownership chung

**Regression runtime bổ sung — P1:** browser xác nhận route `#operations/main/schedules` không render được, báo `field is not defined`. `/Users/toanlamsaoduocc/Desktop/solar-fleet-ems/src/solar_fleet/static/schedule-workspace.js:5` không lấy `field` từ ui, nhưng `:100–102` gọi trực tiếp. Đây là lỗi production JS dù syntax/import linkage đều pass. Cần sửa binding và browser regression test trong giai đoạn 1; chưa sửa trong audit.

**Bằng chứng:** `/Users/toanlamsaoduocc/Desktop/solar-fleet-ems/src/solar_fleet/phase_d_api.py:317` nhận controller/admin nhưng phần endpoint mới chủ yếu khởi tạo service cục bộ rồi trả kết quả. MPC, energy optimizer, Predbat và economic dispatch có mô hình riêng; battery_health và degradation_models có hai cách ước lượng sức khỏe. Form Predbat tại `/Users/toanlamsaoduocc/Desktop/solar-fleet-ems/src/solar_fleet/static/schedule-workspace.js:26` trở đi dùng forecast mẫu; không tự lưu vào schedule record đang dùng editor/compiler/rollout.

**Đề xuất:** shared plan schema có scope, input provenance, constraints, assumptions, revision và expiry; engine là strategy sau interface chung. Plan → draft schedule → review → rollout → engine chung. Không thay thế bộ điều khiển chính bằng scheduler thứ hai. Lưu run/audit cần thiết thay vì chỉ trả object mất sau request.

### A10 — P2: Documentation/provenance đang mâu thuẫn với mã

**Bằng chứng:** `/Users/toanlamsaoduocc/Desktop/solar-fleet-ems/docs/mockup-coverage.md:9–11` nói không dựng số liệu nhưng A02/A03/A05/A06 chứng minh có. `/Users/toanlamsaoduocc/Desktop/solar-fleet-ems/docs/vendor-source-audit.md` dùng “100% COMPLETED AND VERIFIED”, đường dẫn local Windows và mô tả clean-room cho upstream GPL. `/Users/toanlamsaoduocc/Desktop/solar-fleet-ems/THIRD_PARTY_NOTICES.md` không thay đổi trong diff sau baseline.

**Đề xuất:** phân biệt copied/adapted/independently implemented/researched; pin upstream URL+revision+path+license và bằng chứng áp dụng; đồng bộ hai registry/notices. Không kết luận vi phạm bản quyền chỉ từ license GPL hoặc tên module; tuyên bố “clean-room” cũng không đủ chứng minh tuân thủ. Cần review nguồn riêng trước phát hành.

## 3. Chuỗi dữ liệu/điều khiển và ranh giới tích hợp

```text
Sidebar/shared shell
  ├─ Workspace cũ → API scoped → controller/service → IntegrationRegistry
  │    → adapter/agent → native observation → reviewed mapping → storage
  │    → quality/freshness → monitoring/report/EMS
  │
  ├─ Điều khiển cũ → capability → preview/diff/confirm → command engine
  │    → lock/idempotency → adapter → readback → journal/quarantine
  │
  └─ Nhiều card mới → phase_d_api → decoder/compiler/solver cục bộ → response
       ├─ hữu ích cho nghiên cứu/simulation
       └─ chưa chứng minh binding → storage → planner/command engine → audit
```

Composition root tham chiếu: `/Users/toanlamsaoduocc/Desktop/solar-fleet-ems/src/solar_fleet/app.py:326–348`; plugin registration tại `/Users/toanlamsaoduocc/Desktop/solar-fleet-ems/src/solar_fleet/adapters/plugins.py`. Hợp đồng nền: `/Users/toanlamsaoduocc/Desktop/solar-fleet-ems/docs/core-extension-contract.md`. Giữ contract này; không ép mọi hãng thành một field/intent chung giả tạo.

### Khác biệt vendor cần bảo tồn

| Ecosystem mới | Có trong mã | Chưa được phép suy diễn |
|---|---|---|
| GoodWe SEMS | Parser, mock login/station; adapter cloud cũ riêng | Token, region, quyền tài khoản, history và control thật đã nối |
| Growatt SPH | BMS/TOU decoder, priority/frame compiler | SPH/SPF/MOD dùng chung map; frame compiled là commissioned write |
| Solis String/MQTT | Register decode, HA discovery payload, frame builder | Có broker publisher/subscriber, polling daemon và HA end-to-end chỉ vì tạo được JSON |
| Solis Hybrid | Storage bitmask, TOU, dispatch/current conversion | Slot/current/voltage/TTL semantics tương đương String hoặc Deye |
| Deye Hybrid | Work mode, grid charge, six-slot codecs | Compiler mới tự động là compiler Deye đã đăng ký trong engine |
| SOLARMAN V5 | Frame encoding/decoding/discovery parsing | Logger identity/sequence/checksum/Modbus profile đã nghiệm thu; không thay adapter/agent hiện hữu chỉ vì cùng tên V5 |
| SmartESS/Eybond | Binary/P17 codecs và in-memory client | Mọi Bluesun là Voltronic/P17; local TCP đang chạy; cloud Eybond adapter và local protocol có cùng contract |

Normalization đề xuất: giữ native field/raw value, register/function code, unit/scale/sign, timestamp/quality, exact identity và evidence ID; chỉ thêm canonical reading khi mapping hợp lệ. Tách grid import/export, battery charge/discharge, AC/DC, W/kW/kWh, percent/fraction và current/power. Feature không tương đương vẫn nằm trong native UI có lý do khóa, không mất khỏi giao diện.

## 4. Đánh giá theo 15 workspace hiện hữu

Các dòng “giữ luồng nền” không có nghĩa đã audit đầy đủ mọi chức năng cũ. Trọng tâm là ảnh hưởng diff; không chấm phần trăm bằng LOC/route count.

| Sidebar | Kết nối/thay đổi quan sát | Thiếu/rủi ro và đề xuất sau duyệt |
|---|---|---|
| Tổng quan | Shared monitoring/power flow; app.css/energy-flow đổi animation | Giữ quality/freshness, kiểm thử chiều dòng/unknown/reduced-motion; không đưa estimated health thành measured KPI |
| Nhà máy | Metadata/inventory; plant-workspace chỉnh trình bày | Giữ ownership tài sản/site; capacity dùng một schema chung, tránh field mới tự rơi về default |
| Hệ thống / SLD | Topology UI có bổ sung trong diff | Phân biệt sơ đồ thiết kế và topology nghiệm thu; không suy ra điện năng/ATS/control từ icon |
| Bản đồ | Route vẫn thuộc plants/map | Không có bằng chứng map integration mới đầy đủ; giữ coordinate view, kiểm tra lat/lon=0 và selected-site consistency |
| Thiết bị | Inventory + nhiều tab decoder/vendor + battery health | A02–A05/A07/A08; chia rõ vận hành/native/kỹ thuật trong workspace, không xóa vendor detail |
| Điều khiển | Luồng engine cũ + translator/genset simulation card | Candidate plan không bằng executed command; chặn client tự nâng capability; cùng preview/readback/journal |
| Lịch / TOU | Editor/draft/compiler/rollout cũ + Predbat form | A09; forecast mẫu cần nhãn; thêm bước lưu plan thành draft sau duyệt, validate slot/timezone riêng hãng |
| Điều phối EMS | Rules/batch-assess + dispatch/tariff/grid/phase/thermal/EV forms | A06/A09; chưa có closed-loop runtime bằng việc gọi solver; cần input quality, arbitration, fallback và dry-run |
| Dữ liệu & kết nối | Collection/mapping/agent + meter decoder | A01 chặn nền; decoder output chưa tự thành canonical telemetry; resolve source/meter boundary |
| Cảnh báo | Incident workflow + register/alarm catalogue | A04; model lạ phải UNKNOWN; cần nối alarm ingestion/dedup/clear/state, không chỉ decode bằng tay |
| Báo cáo | Stored analytics/export + market/FCR simulator | `/Users/toanlamsaoduocc/Desktop/solar-fleet-ems/src/solar_fleet/static/report-workspace.js:61–85` có nhãn mô phỏng nhưng giá/bid mẫu và fallback 34,5 EUR/h; không coi là doanh thu đã đối soát, phải giữ 0 hợp lệ thay vì `||` fallback |
| Bảo trì | Work-order/checklist/review nền + BESS card | A05 số cố định; dùng health chung, truy nguồn alert/device, không tạo chẩn đoán cell nếu thiếu dữ liệu |
| Nhật ký | Journal nền vẫn hiện hữu | Kết quả simulator mới không là hardware command journal; audit riêng simulation/compile, không giả execution |
| Người dùng | Shared settings/users; chưa thấy mở rộng quyền phù hợp endpoint mới | Kiểm thử viewer/operator/engineer/admin; read-only simulation không tự đòi quyền ghi, nhưng không được báo quyền commissioned |
| Cài đặt & Hãng | Registry/evidence/native catalogue liên quan | A01/A03/A04/A10; một account lifecycle qua vault/registry, support matrix có trạng thái và bằng chứng |

## 5. UI/UX đề xuất — sáng, đơn giản, giữ cấu trúc

1. Giữ nguyên 15 mục, thứ tự, shared shell và app.css. Không thêm sidebar theo vendor/site.
2. Mỗi workspace ưu tiên công việc chính; công cụ protocol giữ trong tab kỹ thuật, không chen nhiều card nghiên cứu lên đầu màn hình vận hành.
3. Một bộ badge nhất quán: **Đo thực / Ước lượng / Mô phỏng / Chưa có dữ liệu / Chưa nghiệm thu**; source và timestamp ở gần giá trị. Không dùng xanh cho giá trị mặc định.
4. Nền sáng, khoảng trắng và typography đồng bộ; bảng dài có overflow phù hợp, wrap subtab; trạng thái loading/empty/error/freshness rõ. Đây là đề xuất, chưa phải kết quả visual acceptance.
5. Form theo site/device đã chọn; đơn vị cạnh input; validation trước request; giữ draft khi lỗi; VI/EN đầy đủ, focus/keyboard, contrast và reduced-motion.
6. Không gộp các thao tác export/battery/meter/grid có semantics khác nhau. Dùng summary chung và native detail riêng khi cần.

## 6. Kế hoạch triển khai đề nghị duyệt

| Giai đoạn | Phạm vi | Điều kiện nghiệm thu |
|---|---|---|
| 1 — Khôi phục tính đúng | A01; bỏ nhãn success/readback/health giả; exact identity và client bypass flags | JSON/schema/registry pass; unknown không biến thành verified; không mock login thành success; không báo hardware execution trong simulation |
| 2 — Nối workflow | Account/adapter registry; canonical measurement; shared health/tariff/forecast/plan schema; plan→draft→review | Contract tests theo vendor, dữ liệu cùng scope/source giữa màn hình, no duplicate writer/controller, persistence/revision/idempotency rõ |
| 3 — UX trong sidebar cũ | Thứ tự card, native/technical tabs, global CSS, VI/EN/accessibility | Browser functional + screenshots được xem, desktop/mobile, empty/stale/error/permission states; giữ đủ 15 mục |
| 4 — Pilot từng profile | Exact device/logger/firmware/account/region, transport read, control có giám sát | Official/community evidence phân cấp; fixture không thay acceptance; fresh readback, unknown-outcome quarantine; người dùng duyệt riêng mọi physical write |

Mỗi batch sửa cần BE+FE+test phù hợp, không chỉ tô nhãn. Consolidated verification: ruff → pytest → JS link/syntax → build → browser/visual QA; sửa và chạy lại phần ảnh hưởng. Không tự làm giai đoạn nào trong báo cáo này.

## 7. Kiểm chứng và môi trường

Môi trường cô lập `/tmp/solar-fleet-audit-8ec68fd`, Python 3.14.6, cài editable `[dev,browser-test]` theo pyproject; **không pin theo constraints.txt**, nên không coi đây là tái hiện lockfile CI. Không thêm dependency vào repository. Chromium được tải cho browser fixture cô lập, không dùng browser session thật.

- HEAD đổi trong lúc lượt pytest đầu đang chạy; kết quả lượt đó **không dùng làm chứng nhận một commit**. Lượt đầu ghi 920 passed / 22 failed; đã yêu cầu chạy lại tại HEAD cuối.
- JavaScript HEAD cuối: `node --experimental-vm-modules scripts/check-ui.cjs` pass syntax + import/export linkage cho 31 module; script không chạy application code.
- Ruff HEAD cuối: `ruff check src tests` pass.
- Build HEAD cuối: sdist + wheel pass, artifact ở `/tmp/solar-fleet-audit-final-dist`; không suy ra packaged JSON hợp lệ từ build pass.
- Browser lượt đầu: 17 setup errors vì thiếu Chromium executable; đây là thiếu môi trường, không phải 17 regression UI được chứng minh.
- Pytest HEAD cuối: **936 passed, 22 failed, 12 warnings trong 97,20 giây**. Trong 22 failure, 21 gặp `JSONDecodeError` ở packaged registry và 1 vi phạm `.style.` trong shared-stylesheet contract. Không sửa test để làm xanh. Lệnh: `/tmp/solar-fleet-audit-8ec68fd/bin/python -m pytest -q` tại repository root.
- Browser HEAD cuối: **13 passed, 4 failed trong 94,02 giây**, lệnh `/tmp/solar-fleet-audit-8ec68fd/bin/python -m pytest ui_tests -q`. Một failure do schedules render lỗi `field is not defined`; hai mapping tests timeout chờ form, artifact HTTP ghi `/api/devices/SIM-DEVICE-0/mapping-context` trả 500, phù hợp A01. Một failure do test đòi animation name `energy-transfer` nhưng CSS mới trả `energy-particles`: đây là **contract/test drift**, chưa đủ kết luận animation sai chức năng; các assertion sau điểm fail trong test đó chưa được chạy. Không tự cập nhật expectation để che regression.
- Browser artifacts nằm tại `/Users/toanlamsaoduocc/Desktop/solar-fleet-ems/work/qa-audit` (fixture tổng hợp, git-ignored). Đã đọc log/DOM/HTTP; chưa review đầy đủ screenshot hoặc visual acceptance. Các kiểm tra phần cứng, provider thật, tariff pháp lý và nghiệm thu 26 mockup **chưa thực hiện**.

Log chi tiết: `/tmp/solar-fleet-audit-final-pytest.log`, `/tmp/solar-fleet-audit-final-browser.log`, `/tmp/solar-fleet-audit-final-ruff.log`, `/tmp/solar-fleet-audit-final-js.log`, `/tmp/solar-fleet-audit-final-build.log`. Log /tmp chỉ là artifact phiên local, không được cam kết lưu lâu dài.

## 8. Context còn thiếu / quyết định cần người dùng duyệt

- Đã phục hồi ưu tiên từ AGENTS, implementation-status, research-architecture, core-extension-contract, ui-design-system, mockup-coverage và integration/vendor audit docs. Các tài liệu có mâu thuẫn được nêu rõ, không coi tài liệu là chứng minh implementation.
- Không có đầy đủ nội dung các phiên trước ngoài yêu cầu giữ UI/sidebar, audit sau feb82ef và duyệt trước khi sửa. Chưa biết thứ tự vendor/model/site pilot ưu tiên, thông số thực tế và hạng mục nào người dùng muốn thương mại hóa trước.
- Đề nghị duyệt **giai đoạn 1 trước**, đồng thời xác nhận có giữ các công cụ mô phỏng như tab kỹ thuật trong workspace hiện tại hay không. Không cần cung cấp secret để duyệt.
- Không commit/push báo cáo; không sửa application/test source. Chỉ báo cáo này là chỉnh sửa chủ động của đợt assessment.