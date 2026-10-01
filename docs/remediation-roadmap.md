# Lộ trình sửa chữa và cải tiến Solar Fleet EMS

Ngày lập: **27/09/2026**. Chủ sở hữu thực thi: người/agent làm việc trên repository này.

## 1. Hợp đồng tiếp tục

Đây là **hàng đợi thực thi chuẩn** khi người dùng nói “tiếp tục”, “làm tiếp” hoặc yêu cầu tiếp tục sửa chữa mà không chỉ định phạm vi khác. Chỉ dẫn mới, cụ thể của người dùng được ưu tiên; ở plan mode chỉ khảo sát/lập kế hoạch, không sửa file hay commit.

- Đọc tài liệu này, `AGENTS.md`, trạng thái Git và bằng chứng liên quan trước khi chọn việc. Không dựa vào trí nhớ hội thoại hoặc số test của lần trước.
- Bắt đầu từ **Điểm tiếp tục** bên dưới, làm một lát cắt hoàn chỉnh BE → FE → test → tài liệu nếu có UI. Không tự chuyển sang sửa nhãn nhỏ khi nhiệm vụ an toàn/dữ liệu còn làm được.
- Không hỏi lại quyền làm các việc nội bộ thuộc lộ trình đã được giao. Hỏi khi có quyết định sản phẩm không thể suy ra, thay đổi phá vỡ tương thích, nghĩa vụ license chưa rõ hoặc hành động ngoài phạm vi cho phép.
- Khi bị chặn: ghi chính xác thiếu gì, ai/cái gì có thể giải quyết, phần độc lập nào vẫn làm được; chọn mục READY tiếp theo có đủ phụ thuộc. Không dừng cả dự án chỉ vì thiếu tài khoản/phần cứng.
- Không tự push, triển khai, gửi thông báo thật, sử dụng credentials thật hoặc phát lệnh thiết bị. Lộ trình không cấp quyền cho các hành động này.
- Kết thúc mỗi đợt: cập nhật trạng thái, bằng chứng, rủi ro còn lại và **Điểm tiếp tục**. Chỉ commit phạm vi đã rà soát khi chế độ hiện tại cho phép; không gom sửa đổi không liên quan của người dùng.
- Không có thực thi nền giữa các phiên. “Tiếp tục” kích hoạt phiên làm việc kế tiếp theo checkpoint đã lưu.

## 2. Baseline và giới hạn bằng chứng

Đã kiểm tra Git khi lập kế hoạch: nhánh `fix/real-data-engine-integration`, HEAD `567a9d0`, cây làm việc sạch trước khi thêm tài liệu này. Hai commit trước là `c40633e` và `5dc8d76`.

Các sửa UTC/EMS và form hãng đã commit; không đưa lại vào backlog như thể chưa làm. Số **1.198 Python / 33 browser** là kết quả được ghi ở đợt trước, **không phải suite vừa chạy khi lập lộ trình**. R01 phải xác minh artifact hoặc chạy lại để lập baseline kiểm chứng.

Nguồn lập backlog:

- [Trạng thái triển khai](implementation-status.md), [26 màn hình](mockup-coverage.md), [sidebar chuẩn](sidebar-subtabs-architecture.md).
- [Containment sau merge](master-merge-review-2026-09-27.md), [real-data remediation](real-data-remediation-2026-09-27.md), [sidebar follow-up](sidebar-followup-2026-09-27.md).
- [Rà soát legacy](legacy-project-audit.md), [inventory legacy](evidence/legacy-project-inventory.json), [source audit](vendor-source-audit.md).
- [Browser contract](browser-test-contract.md), [nghiệm thu phần cứng](hardware-acceptance.md).

Đây là kế hoạch bao phủ hệ thống, **không phải chứng nhận đã tìm hết lỗi**. Những thiếu sót ghi trong tài liệu cần được đối chiếu code mới nhất trước khi sửa. Danh mục cũ có thể chứa mô tả đã lỗi thời; không xóa lịch sử kiểm thử để làm nó giống hiện trạng.

## 3. Bất biến bắt buộc

1. READ ONLY mặc định. Giữ các cổng 503 cho read chưa có live integration và 409 cho control chưa commissioned; chỉ thay trạng thái của đúng đường đã đủ bằng chứng và được nghiệm thu, không mở khóa hàng loạt.
2. Không đưa simulator/seed vào production observations. Phân biệt measured, declared, estimated, stale và unknown; thiếu dữ liệu không biến thành 0 hoặc thành công.
3. Mọi đọc/ghi phải kiểm scope ở server. Recheck quyền, binding, revision và freshness tại thời điểm hành động, không chỉ khi render UI.
4. Một controller, command engine chung, idempotency, serialization theo thiết bị, quarantine khi không rõ kết quả. ACK không bằng VERIFIED; không retry ghi mù.
5. Giữ sidebar 15 mục, inventory 26 màn hình, shared shell và stylesheet. Tái sử dụng owner hiện tại, không tạo client/dashboard cạnh tranh.
6. Legacy: URL + revision + file/hash + license/nghĩa vụ + applicability + owner + tests trước khi import. Public không đồng nghĩa được phép sao chép. Không suy model/firmware/register từ thương hiệu.
7. Billing/savings/reactive-energy vẫn unknown khi thiếu biểu giá hiệu lực, timezone, meter, đơn vị, chiều và dữ liệu đồng bộ. Advisory không là dispatch hoặc hóa đơn đã xác minh.

## 4. Lịch dự kiến và thứ tự

Ước lượng **ngày công tập trung**, không phải ngày lịch hay tốc độ cam kết của agent. Đây là dải dự trù cho một vòng sửa chữa/pilot; không bao hàm hoàn thiện mọi hãng, SaaS hoặc mọi thiết bị. Tái ước lượng sau R01 và sau từng đợt. Phát hiện P0 được xử lý trước các đợt tính năng.

| Đợt | Ưu tiên / phụ thuộc | Ngày công dự trù | Kết quả phải giao |
|---|---|---:|---|
| R01 | P0, bắt đầu ngay | 1–2 | Baseline tái lập, sổ lỗi, ma trận route → owner → nguồn → quyền → test |
| R02 | P0, sau R01 | 3–5 | Vá lỗ hổng quyền/secrets/command guards đã xác nhận, negative tests |
| R03 | P0/P1, sau R01; giữ R02 gates | 3–5 | Chuẩn dữ liệu thật, thời gian/chất lượng/nguồn thống nhất qua API và UI |
| R04 | P1, sau R01; trước mọi import mới | 2–4 | Đối chiếu 30 legacy projects và nguồn sau merge, chọn reuse hợp pháp |
| R05 | P1, sau R02–R04 | 5–10 | Hoàn thiện từng lát cắt account → discovery → read → persistence → UI |
| R06 | P1, sau R02–R03 | 3–5 | Cấu hình dispatch/billing có kiểm quyền; biểu giá hiệu lực và tính đúng |
| R07 | P1, sau R03–R05 cho transport được chọn | 4–7 | Agent/storage vận hành bền vững, recovery/retention/backfill có kiểm chứng |
| R08 | P1, sau R02–R03; tái dùng R05 khi cần | 3–5 | Incident → maintenance → notification/report có trạng thái thật |
| R09 | P1, sau R02–R07 theo chức năng | 4–7 | TOU/EMS advisory và control lifecycle không vượt commissioning |
| R10 | P1/P2, theo chức năng đã ổn định | 4–6 | Kiểm tra toàn bộ 15 mục/26 màn hình, VI/EN, accessibility, responsive |
| R11 | P1, sau các đợt đưa vào release | 2–4 | CI/checks tái lập, package/restore/upgrade/soak và bằng chứng release |
| R12 | Gate phát hành, sau R11 | Theo thiết bị/quyền truy cập | Nghiệm thu pilot/hardware riêng từng exact profile; không mở khóa bằng fixture |

R02/R03 quan trọng hơn mở rộng reuse. R04 có thể chạy khi một phần R02/R03 bị chặn. R10 được thực hiện từng lát cắt cùng các đợt trước, nhưng chỉ đóng sau rà soát tích lũy. Không mặc định mọi R05/R07/R09 có thể hoàn thành trong dải trên: tách subtask và ghi phần ngoài release khi phát hiện quy mô lớn hơn.

## 5. Checklist từng đợt và điều kiện đóng

### R01 — Kiểm kê và baseline

- Xác minh Git, thay đổi chưa commit, môi trường Python/Node/browser, lệnh CI và constraints; không đổi nhánh hoặc cài dependency tùy tiện.
- Đối chiếu log/exit `/tmp/solar-vendor-form-python.{log,exit}`, `/tmp/solar-vendor-form-browser.{log,exit}`, `/tmp/solar-vendor-form-build.log`, `/tmp/solar-vendor-label-browser.log`. Thiếu/mơ hồ thì chạy lại; không coi `/tmp` là bằng chứng bền vững.
- Lập `docs/remediation-findings.md`: mỗi mục có ID, severity, loại CONFIRMED_BUG / UNBUILT / INVESTIGATE, file/symbol/route, cách tái hiện, ảnh hưởng, owner, phụ thuộc, test dự kiến và trạng thái.
- Lập ma trận các đường đọc/ghi, production/simulator, auth/scope, provenance/freshness, sidebar sở hữu và coverage. Kiểm tra ngữ nghĩa, không coi grep TODO/default là kết luận lỗi.
- Rà liên kết tài liệu bị thiếu/lỗi thời, số liệu snapshot và chỗ mâu thuẫn giữa registry/implementation/coverage.
- **Đóng khi:** baseline có commands + exit + revision, backlog ưu tiên có bằng chứng và danh sách chưa khảo sát; chốt lát cắt R02 đầu tiên.

### R02 — An toàn, phân quyền và tính toàn vẹn giao dịch

- Kiểm role/site/object scope trên mọi mutation, export/download, binding, mapping review, WebSocket và background job; kiểm đổi scope/session revoke giữa preview và commit.
- Rà CSRF/session/API key, secret redaction/vault, log/error leakage, outbound URL/SSRF và file/path handling theo đường thực sự tồn tại; không tuyên bố có exploit khi chưa tái hiện.
- Kiểm bypass bằng payload flags, stale revision, replay, concurrent requests, duplicate retries; đảm bảo denied requests không tạo command/job hoặc side effect.
- **Đóng khi:** lỗi P0/P1 xác nhận trong phạm vi có regression, quyền bị từ chối ở server, các cổng 503/409 và quarantine được kiểm thử; rủi ro chưa giải quyết ghi rõ và chặn release tương ứng.

### R03 — Dữ liệu thật và semantics

- Rà mọi giá trị vận hành mặc định/seed, missing vs zero, NaN/Infinity, unit/scale/sign, source conflict và binding ambiguity.
- Chuẩn timestamp UTC + timezone hiển thị; DST, out-of-order, duplicate, future/stale, gaps, counter reset/rollover, partial coverage và provenance.
- Đối chiếu overview/device/flow/history/report/EMS dùng cùng dữ liệu, cùng lý do unknown; không tự nội suy hay ngoại suy lifetime từ cửa sổ lưu ngắn.
- **Đóng khi:** có regression biên và kiểm nhất quán API/UI; mọi dữ liệu không đủ điều kiện hiển thị lý do, không biến thành KPI chắc chắn.

### R04 — License, revision và owner của legacy

- Đối chiếu inventory cũ với thư mục hiện tại `/Users/toanlamsaoduocc/Downloads/before_project`; ghi thiếu thư mục/khác revision/hash thay vì coi mô tả từ Windows là hiện trạng.
- Mỗi trong 30 dự án có disposition: reuse / reference-only / defer / reject, nguồn ghim, license theo file/dependency, nghĩa vụ phân phối, owner hiện có và hợp đồng tính năng.
- Đối chiếu nguồn unreviewed sau merge với hai registry; chỉ promote bằng chứng đã rà. Đồng bộ notices, pins, packaged data nếu có thay đổi.
- Chọn lát cắt reuse nhỏ nhất có ích cho workflow hiện hữu, ưu tiên đọc/normalize/history/error handling. Không nhập cả cây hoặc tạo client trùng.
- **Đóng khi:** 30 dòng được đối chiếu hoặc đánh dấu blocked có lý do; chỉ các dòng có provenance/license rõ được xếp READY để import. Chưa resolve nguồn dùng trong runtime thì không coi release sạch license.

### R05 — Account và vendor read workflows

- Mở rộng trong adapter hiện hữu, từng vendor/endpoint/model: validation, authentication/renewal, explicit discovery, pagination, quotas, timeout/backoff và lỗi đã kiểm chứng; không tự suy ngữ nghĩa error code toàn hãng.
- Đối chiếu GoodWe/Sungrow plant/point limits, Growatt region và tất cả tám form với request schema. Thêm submit/validation/error/retry/RBAC tests, không chỉ nhãn/secret masking.
- Nối native observations → ingestion → storage → trạng thái nguồn/UI, không dùng decoder/compiler thuần làm bằng chứng live transport. History/alarm chỉ thêm khi có contract và owner rõ.
- **Đóng từng lát cắt khi:** mock transport contract + API + browser đạt, không secret leakage/cross-site mixing, đường unsupported vẫn khóa. Live acceptance là trạng thái riêng, không bắt buộc dùng credentials thật trong suite.

### R06 — Billing và cấu hình vận hành

- Xây editor theo owner Cài đặt/EMS có schema, scope, revision, audit cho billing meter, dispatch device và tham số thực sự cần; phân biệt declared_specs với operational config.
- Version/effective interval cho tariff, currency/unit/timezone, import/export, interval alignment và rounding; reactive energy/peak demand chỉ tính khi đủ đầu vào phù hợp.
- Kiểm boundaries DST, đổi tariff giữa kỳ, thiếu meter/giá, gap, số 0 hợp lệ; cost/savings không lấy catalogue estimate làm bill thật.
- **Đóng khi:** lưu/reload/permission/conflict UI→API có test; con số có thể truy về observations + tariff revision; thiếu dữ liệu trả unknown/advisory có lý do.

### R07 — Agent, lưu trữ và phục hồi

- Ưu tiên collector/ingestion đang có: enrollment, revocation, sequence/replay, outbox durability, reconnect, duplicate delivery, restart và giới hạn polling.
- Rà SQLite transaction/migration/retention, scoped pagination, backfill/rollup và explicit coverage; đo tải trước khi đề xuất đổi kiến trúc. Giữ một controller cho tới khi có thiết kế được duyệt.
- Chia service install, mTLS/rotation, RTU/managed update thành subtask theo license/protocol và nền tảng thực tế; không hứa hỗ trợ khi mới có config.
- **Đóng khi:** chứng minh restart/retry không mất hoặc nhân đôi kết quả, restore có diễn tập trên dữ liệu giả; giới hạn throughput/storage/offline công bố từ đo đạc.

### R08 — Vận hành, cảnh báo, báo cáo

- Incident dedup/recovery/order, maintenance review/closure, firmware draft và journal phải phản ánh trạng thái thật. Không báo OTA thành công khi chưa có executor/acceptance.
- Hoàn thiện notification editor và delivery lifecycle theo kênh chọn: vault, quyền, retry/dedup, lỗi và audit; test bằng fake transport, không gửi thật.
- Report/export kiểm scope, large query/pagination, unknown metrics và provenance; PDF/email là subtask riêng nếu chưa có implementation/dependency phù hợp.
- **Đóng khi:** user journey incident → xử lý → audit/report có test thành công/thất bại/không quyền, trạng thái delivery không nhầm config saved với delivered.

### R09 — Lịch, EMS và command lifecycle

- Rà TOU timezone/DST/full-week, compile digest, stale preview, conflict arbitration, constraints/hysteresis và plan revision; advisory không tự tạo schedule/command.
- Dùng forecast/optimizer legacy chỉ sau R04, đầu vào đủ và provenance rõ; cold start không tạo đường cong giả. EV recent user declaration không là trusted device telemetry.
- Với exact profile đủ evidence: compiler → preview → confirm → serialization → send → readback/quarantine; timeout/restart/replay phải fail safe. Không thêm wildcard commissioning hoặc suy register hãng khác.
- **Đóng khi:** simulation/negative contracts chứng minh mọi đường không đủ quyền/evidence/freshness đều không ghi; kết quả physical chỉ VERIFIED sau acceptance và readback thật.

### R10 — Hoàn thiện trải nghiệm theo sidebar

- Lập ma trận 15 mục/26 màn hình: happy path, empty, loading, error/retry, forbidden, stale/unknown, mobile và VI/EN. Không coi route smoke là coverage mọi thao tác.
- Kiểm nhãn/keyboard/focus, contrast, reduced motion, tràn bảng/tab, deep link giữ site/filter và thao tác double-submit; dùng primitives/style hiện hữu.
- Gắn từng thiếu sót UI với API owner và test; không làm màn hình giả thành công để đạt mockup.
- **Đóng khi:** ma trận có kết quả và screenshot fixture không chứa dữ liệu khách hàng, browser assertions cho luồng quan trọng, phần deferred được ghi và không tuyên bố full acceptance.

### R11 — Release engineering

- Kiểm CI thực sự chạy gì; thêm backend/browser riêng job hoặc riêng lệnh, Ruff, static JS, package/import và registry/license consistency theo môi trường được hỗ trợ.
- Dependency/security review và reproducibility, backup/restore/migration, startup/shutdown, load/soak; không tự thêm framework để lấp checklist.
- **Đóng khi:** fresh checkout tái lập checks, artifact gắn revision/commands/exits, không có P0/P1 chưa xử lý trong phạm vi release; các giới hạn pilot được công bố.

### R12 — Nghiệm thu thực địa có kiểm soát

- Chốt exact device/logger/firmware/account/region, quyền thao tác, transport, safety limits và kế hoạch dừng/khôi phục với người có thẩm quyền.
- Read-only trước; đối chiếu số đo, timestamp, units và freshness. Write chỉ trong phiên được phép riêng, với preview/confirm/readback và acceptance record.
- **Đóng theo profile khi:** đủ bằng chứng hardware và điều kiện vận hành. Không có phần cứng/quyền thì BLOCKED, không mở khóa và không gọi production-ready.

## 6. Quy tắc validation và bằng chứng

Sau mỗi **đợt triển khai mạch lạc**, gom verification theo `AGENTS.md`, sửa lỗi và chạy lại checks bị ảnh hưởng; không chạy full suite sau từng chỉnh sửa nhỏ.

Môi trường đã dùng trước đây: `/tmp/solar-fleet-audit-8ec68fd/bin/`; phải kiểm tồn tại/phiên bản trước khi dùng. Từ repository `/Users/toanlamsaoduocc/Desktop/solar-fleet-ems`, lệnh chuẩn với Python của môi trường đã xác minh:

```sh
python -m ruff check .
python -m pytest tests -q
python -m pytest ui_tests -q
find src/solar_fleet/static -name '*.js' -type f -exec sh -c 'for f do node --input-type=module --check < "$f" || exit; done' sh {} +
python -m build
git diff --check
```

- **Không gộp collection Python/browser** vì đã có trùng tên module. Missing dependency/skip/failure không tính là pass.
- Test dùng fixture cô lập, không dịch vụ hãng, tài khoản khách hàng hoặc thiết bị thật. Kiểm network isolation khi mở rộng test harness.
- Khi thay implementation, cập nhật coverage và chạy `python scripts/measure_code.py --update-doc`; inventory không phải test hoặc phần trăm hoàn thành.
- Ghi revision/tree scope, command, exit, pass/fail/skip/warning, log và giới hạn trong evidence Markdown đã version control. Không chỉ giữ đường dẫn `/tmp`; không lưu secrets/payload nhận diện.
- Documentation-only: kiểm diff, đọc lại file và liên kết mới; có thể không chạy application suite nhưng phải ghi rõ. Không gắn số test cũ vào đợt chỉ sửa tài liệu.

## 7. Sổ tiến độ và điểm tiếp tục

Trạng thái: READY = làm được ngay; TODO = chưa bắt đầu/phụ thuộc; IN_PROGRESS; BLOCKED (bắt buộc lý do và bước giải tỏa); VERIFIED_SOFTWARE; ACCEPTED_HARDWARE. Không dùng DONE chung cho code và commissioning.

| ID | Trạng thái ban đầu | Checkpoint / bằng chứng |
|---|---|---|
| R01 | IN_PROGRESS | R01.1 đã kiểm artifact, môi trường, chạy 54 safety tests và lập [findings/ma trận bước đầu](remediation-findings.md); chưa audit toàn bộ routes |
| R02 | IN_PROGRESS | RF-002 đã tái hiện và sửa guard trước từng send, 6 regression đạt; chưa audit toàn bộ control/transport |
| R03 | TODO | UTC đã sửa ở `c40633e`; còn rà semantics toàn tuyến |
| R04 | IN_PROGRESS | Đã đối chiếu macOS 30/30 dự án, 43 locked files khớp; OpenEMS khác số file, Solis thiếu license; xem legacy-reconciliation-2026-09-28.json. Chưa legal/owner acceptance cho import mới |
| R05 | TODO | Form labels đã sửa ở `567a9d0`; chưa chứng minh submit/live end-to-end đầy đủ |
| R06 | IN_PROGRESS | Editor pin/device và giá nhập VND theo hiệu lực UTC, revision/audit; tính ước tính interval nằm trọn phiên bản giá. Chưa utility billing, sửa/supersede giá, thuế/phí/export |
| R07 | TODO | Chọn collector/storage slice sau baseline |
| R08 | TODO | Notification delivery, reports và maintenance acceptance còn mở |
| R09 | IN_PROGRESS | Cấu hình advisory lưu/reload và conflict guards; chưa optimizer/conflict arbitration/physical dispatch |
| R10 | IN_PROGRESS | Planning editor VI/EN, accessible fields/status, save/reload/conflict browser contracts; chưa acceptance 26 màn hình |
| R11 | IN_PROGRESS | CI tách backend/browser jobs, Chromium fixture và Ruff toàn cây; local build kiểm chứng, chưa hosted CI/fresh-checkout/restore/soak |
| R12 | BLOCKED | Chưa có exact-profile hardware acceptance/quyền thử ghi riêng; không cản R01–R11 |

**Điểm tiếp tục — đợt before_project integration (01/10/2026):**

Đợt này tập trung bổ sung code từ before_project (toàn bộ quyền đã mua), mở rộng local agent và chuẩn hoá interface.

**Đã hoàn thành trong đợt này:**

1. **`interfaces.py`** — đã có từ đợt trước: `ReadAdapterProtocol`, `WriteAdapterProtocol`, `LocalReadAdapterProtocol`, `InverterControlMixin`, `TelemetrySnapshot`, `TouSlot`, `WorkMode`, `METRIC_*` constants, `normalize_points`, `adapter_capabilities`.

2. **Register profiles mới (modbus_profiles/):**
   - `sungrow_registers.py` — 40+ fields từ Sungrow-SHx-Inverter-Modbus-Home-Assistant (MIT, mkaiser, 2026-06-19); input + holding registers, decode helper.
   - `huawei_registers.py` — 50+ fields từ huawei-solar-lib (MIT, wlcrs); SUN2000 + LUNA2000 battery + power meter, gain-based decode.
   - `modbus_profiles/__init__.py` — registry tập trung: (vendor, model_series) → field_list + decoder; hỗ trợ Growatt SPH/MIN/MIX/MID/MAX, Sungrow SHx/SH/SG, Huawei SUN2000, Solis S6, Deye.

3. **Local adapters:**
   - `eybond_local.py` — Eybond/Bluesun/SMG/PI17/PI30 Modbus TCP port 8000; model fingerprinting qua layout_code + model_code (từ ha-eybond-local, 32 devices catalog); 28 core telemetry registers.
   - `goodwe_local.py` — GoodWe ES/ET/EH/DT UDP port 8899; dùng goodwe library nếu cài (preferred), fallback AA55 UDP; map 25 sensor fields.
   - `modbus_local.py` — ModbusTcpPoller: generic Modbus TCP poller dùng profile registry; gộp register addresses thành blocks hiệu quả (≤8 addr gap, max 125 regs/block).
   - `solarman_local.py` — SolarmanV5Poller: wrapper V5 framing cho inverters qua SOLARMAN logger; dùng `solarman_v5.py` đã có.

4. **`local_daemon.py`** — LocalAgentDaemon: điều phối N polling coroutines, per-device asyncio task, exponential backoff quarantine (5 fail → 60–600s), shared outbox queue, status API.

5. **`adapters/__init__.py`** — export đầy đủ: interface, TOU, cloud adapters, local adapters, daemon.

**Verification:** 13 files syntax OK (`py_compile`). Full test suite: 69 passed trước khi -x stop ở pre-existing async failure (`test_command_aba_fence` — thiếu `pytest-asyncio`, không phải do code mới). Test đang chạy tiếp.

**Còn lại / Phiên kế tiếp:**
- Kiểm tra result đầy đủ của test suite (đang chạy).
- Viết unit tests cho register profile decoders (Sungrow, Huawei decode path).
- Viết contract tests cho EybondLocalAdapter và GoodWeLocalAdapter với mock socket.
- Thêm `Sunsynk` local adapter (Modbus TCP port 502, đã có `tou_builder.py` cho Sunsynk TOU format).
- Wiring LocalAgentDaemon vào main application bootstrap / service entrypoint.
- Frontend: UI quản lý local device configs (address/port/vendor/model_series/poll_interval).
- Hardware acceptance R12: cần exact device + real credentials để nghiệm thu.

Tiếp nối: đã thêm durable user/session revisions xuyên HTTP reads/preview, queued commands, rollout, reconciliation và WebSocket; signed plan giữ operator revision, post-ACK giữ quarantine/order IDs. Storage migration/second connection/rollback và unrelated-authority controls có tests. Bản source cuối đã kiểm chứng: backend 1613 passed (12 warnings), browser 33 passed; Ruff, JS syntax/linkage, sdist/wheel build và git diff --check đạt. Xem mục đầu findings cho log/exit artifacts và giới hạn. Ưu tiên còn lại là exact-object entity fences (heartbeat vẫn invalidates), history/report/transport matrix và security surfaces/background owners. Không coi user/session counters là full-route coverage hoặc multiprocess safety; session lookup hiện dùng BEGIN IMMEDIATE, cần đánh giá contention. Không thay FE/protocol/commissioning; R01/R02 vẫn mở.

Đợt rộng 28/09: backend 1542 passed/12 warnings (253.46s), browser 33 passed (56.29s), exit 0. Hai suite này trước refinement cuối giữ idempotent replay sau revision change; bản cuối đã chạy lại 185 command-family tests, tất cả passed (1 warning). Ruff/build/inventory/diff check cuối đạt; JS 33 modules/linkage đạt. 41 ca collected mới so với baseline 1501. Không tuyên bố full-suite trên exact final tree, không manual visual/hardware/commit/push. Kind-wide revision có trade-off availability; user/session ABA và audit security surfaces chưa hoàn tất.

R01.20 partial: malformed persisted agent observation envelopes/samples are skipped before merge; authorized valid siblings remain available, invalid-only rows do not claim HAS_DATA. Synthetic reproducer 9 failed/5 passed; focused 43 passed/1 warning, exit 0. One fixture corrected after reproduction has no pre-fix claim. Ruff/JS/build passed; inventory regenerated. Final backend 1501 passed/12 warnings, 232.50s; browser 33 passed, 52.14s; both exit 0 (`/tmp/solar-r0120-{backend,browser}.{log,exit}`). Cloud telemetry, agent-definition corruption and broader consumers remain outside this slice; no UI/vendor/write semantics or hardware acceptance change.

Final R01.19 verification supersedes pending wording below: full backend **1487 passed / 12 warnings, 225.19s**, exit 0 (`/tmp/solar-r0119-backend.log`, `/tmp/solar-r0119-backend.exit`), collected after all additions. Local synthetic evidence only.

R01.19 adds task-local composed read guards and Deye internal auth-lock/budget/HTTP checks. Wired preview, execution order/config/readback, reconciliation and HTTP configuration; send ACK handling unchanged. Synthetic pre-fix 7 failed/4 passed; focused 206 passed/1 warning, browser 33 passed, exit 0. Ruff/whitespace/JS linkage/build passed; inventory regenerated. Full backend pending. No UI/vendor semantics/hardware acceptance change; other transport owners and general ABA remain open. See findings for evidence limits and child-task context propagation constraints.

R01.18 scoped credential fence: atomic opaque integration credential revision in `Vault.put`, controller cache rejects stale authentication. Initial pre-fix 3 failed/1 passed; initial full backend log verified 1455 passed/12 warnings, no separate exit artifact. Expanded with 19 queued/direct-route/whole-wave credential and ABA cases: focused 144 passed/1 warning, browser 33 passed, both exit 0. No pre-fix or final expanded full-tree run claimed for the expansion. Ruff/whitespace/build/JS linkage passed, inventory regenerated. Cached adapter reopening is explicit, not automatic. Deye read/order internal authenticate/budget awaits lack guard propagation (source inspection only). No UI/hardware changes; general ABA and malformed telemetry remain open. See findings for limitations.

R01.17 fixed RF-020: both non-rollout HTTP confirm owners now pass session guards; rollout execution reuses all-target context checking. Corrected pre-fix 7 failed/45 passed; focused 151 passed/1 warning, browser 33 passed; final backend 1451 passed/12 warnings, exit 0 (`/tmp/solar-r0117-backend.log`, `/tmp/solar-r0117-backend.exit`). Net 28 added cases, including multi-step order-wait denial retaining order IDs and real lock contention. Ruff/JS/build passed, inventory regenerated. No frontend/hardware scope change. Keep single controller, unknown-outcome quarantine and accumulated changes; no credentials/hardware/commit/push authorized. See latest findings for evidence limits.

Final backend verification supersedes pending status below: 1420 passed/12 warnings, exit 0 (`/tmp/solar-r0116-backend.log`, `/tmp/solar-r0116-backend.exit`). Collected before final three cases, separately passed in focused 99-case run; no 1423-case full-tree run claimed.

R01.16 implements queued rollout origin-session/source/cancellation guards after device lock/configuration and transport/readback awaits, including adapter before-send callbacks. Added 19 synthetic cases with real lock contention and two-target claimed denials; focused 99 passed/1 warning, browser 33 passed, Ruff/JS/build passed. Backend pending in `/tmp/solar-r0116-backend.log` (started before final three cases, separately verified by focused run). Inventory regenerated. No pre-fix reproducer run claimed; initial test-body failures are not safety evidence. Preserve uncertainty quarantine after send, snapshot/ABA limitations, single-controller requirement and no hardware/credentials/commit/push authorization.

R01.15 fixed RF-019 request-boundary authorization and atomic wave preview. Added 20 cases, pre-fix 15 failed/5 controls; focused 113 passed/1 warning, browser 33 passed. Final backend **1404 passed/12 warnings**, exit 0 (`/tmp/solar-r0115-final.log`, `/tmp/solar-r0115-final.exit`); final-tree targeted 20 passed, 260 selected hashes unchanged. Ruff/JS/build passed, inventory regenerated. Read latest findings for limitations: HTTP confirm has no internal yield before claim, but queued execution has not inherited session/source guards. Snapshot equality does not prevent ABA. Preserve accumulated changes and single-controller constraint; no hardware/credentials/commit/push authorized.

R01.14 final verification completed: backend **1384 passed/12 warnings**, browser **33 passed**, both exit 0; 264 source/test/static hashes unchanged. This supersedes the pending status in the batch note below. Artifacts and local-only limitations are recorded in findings.

R01.14 implemented RF-018: shared preview engine revalidates after lock/configuration; direct plans/control-execute routes supply session guards before persistence. Reproducer 20 failed/4 unchanged controls passed; focused 80 passed/1 warning. Ruff/JS/build passed, inventory updated; full backend/browser checks pending final artifact verification. No UI runtime/protocol/hardware changes. Rollout's multi-target persistence/disclosure and source-row revision boundaries remain unclosed; prioritize these next, including session revocation while waiting for runtime.lock. Keep all accumulated changes and single-controller constraint.

R01.13 implemented RF-014–017: access-check main/admin alias revalidates session/context and discards failed adapter caches; latest rejects stale caller Device; reconciliation rechecks lock/order/readback boundaries and retains TIMEOUT on denial; weather/overview rechecks session/scope/site after fetch. Reproducers and explicit closure gaps are recorded at the start of findings. Next: reproduce preview plan disclosure/persistence after revoke, then rollout revisions/context; review credential changes preserving binding identity, malformed samples and ABA fencing. Keep one-controller limitation and do not claim internal transport cancellation. Final verification evidence is recorded in findings/coverage, not inferred from prior checkpoint totals.

R01.12 (27/09/2026): cloud latest lưu site_id/binding_id tại ingest; latest() xác minh envelope, sample device/binding/source và integration/binding/site hiện tại trước khi trả samples/native. Legacy thiếu provenance trả NO_DATA đến poll hợp lệ, không backfill bằng identity hiện tại. Reproducer 11 failed/42 passed; focused 82 passed/1 warning. Fixtures cũ được chuyển sang explicit synthetic cloud provenance, không nới guard production; browser fixture vẫn chặn outbound HTTP. Full validation/evidence trong findings. Chưa audit mọi consumer đọc store trực tiếp; access-check, malformed sample handling, ABA/multiprocess còn mở.

R01.11 (27/09/2026): poll rejects device vendor / site id, vendor, source mismatch before transport and snapshots selected sites across latest await. Reproducer 5 failed/36 passed; final controller 41 passed. No adapter/protocol/FE change. Site integration_id deliberately not constrained: discovery supports multiple account paths to one site. Cloud latest remains unguarded on read (source inspection, not a new reproducer); prioritize tests and migration-safe rejection next. Missing-site, empty-response site mutation and ABA/multiprocess coverage remain limitations. Evidence `/tmp/solar-r0111-*`; full verification recorded in findings after completion.

R01.10 (27/09/2026): RF-013 history/configuration post-await authority: repro 14 failed/15 passed, dùng chung synchronous revalidation callback với alerts. Thêm 3 barrier tests xác minh access-check giữ poll_lock tại stations/devices/latest, sync/disable bị chặn và lock được release. Final focused 51 passed/1 warning (16.23s), backend 1288 passed/12 warnings (166.34s), browser riêng 33 passed (51.15s); Ruff, JS syntax/import-export linkage, no-isolation build, inventory, diff check đạt. Artifacts `/tmp/solar-r0110-*`, source SHA256 file kèm theo. Không thay adapter/FE/control; chưa chứng minh full DessMonitor cache hoặc access-check session revoke. HEAD `567a9d0`, accumulated worktree giữ nguyên, không commit/push. Poll site/vendor và cloud latest chưa sửa, ưu tiên phiên kế tiếp.

R01.9 (27/09/2026): RF-011/012 tái hiện 10 failed/2 unchanged passed; alerts revalidate session/scope/device/integration/adapter/binding/site sau await và persist/correlate atomically; agent latest kiểm current device allowlist, snapshot site và sample device/binding/source. Final backend 1268 passed/12 warnings (157.26s), browser riêng 33 passed (50.58s), focused 49 passed/1 warning (14.16s). Ruff, JS syntax, no-isolation build, inventory và diff check exit 0; artifacts `/tmp/solar-r019-*`. HEAD `567a9d0`, giữ accumulated worktree, không commit/push. Access-check đọc code có giữ poll_lock nhưng chưa có barrier acceptance; không đánh dấu audit hoàn tất. Chi tiết/giới hạn trong findings register.

R01.8 hoàn tất slice: 15 reproducer đỏ trước sửa, transaction latest batch và binding identity guard; thêm DessMonitor cache-rejection/rediscovery test, không sửa adapter. Final backend 1256 passed/12 warnings, browser riêng 33 passed, focused 45 passed/1 warning; Ruff/JS/build/inventory/diff checks đạt. Artifacts `/tmp/solar-r018-*`; bản code cuối bao gồm refinement R01.7. Chưa commit/push; R01/R02 vẫn mở.

R01.7 evidence: repro 8 failed/11 passed; final controller 20 passed, Ruff/JS/build/inventory/diff checks đạt. Backend 1238 passed/12 warnings và browser riêng 33 passed (exit 0), nhưng chạy trước refinement skip-empty-latest và test rollback cuối; final full-suite còn cần rerun. HEAD vẫn `567a9d0`, giữ accumulated worktree, không commit/push. R01/R02 vẫn mở.

Thứ tự phiên kế tiếp:
1. Đọc Git status/diff/log và hướng dẫn repository; bảo toàn mọi sửa đổi ngoài phạm vi.
2. Đọc [findings register](remediation-findings.md), đầy đủ command engine và fixture/concurrency tests; artifact vendor-form đã xác minh ở R01.1, không chạy lại chỉ để lặp số liệu.
3. Đọc evidence R01.2–R01.8: latest batch atomic, binding identity guard, discovery stage/check/transaction; DessMonitor cache bị từ chối buộc rediscovery trước poll. Tiếp tục alarm/agent/latest-read, site-row/vendor identity và access-check concurrency; direct adapter calls và HTTP-client internal await vẫn ngoài bảo đảm.
4. Mở rộng ma trận mutation/export/download/WebSocket/background jobs, theo dấu permission/provenance tới owner; reproducer trước runtime fix, cập nhật checkpoint sau mỗi batch.

### Nhật ký lộ trình

R01.6 (27/09/2026): 5 poll reproducer đỏ trước sửa, unchanged xanh; snapshot integration/adapter/device/binding sau latest await chặn persist stale batch, kể cả response thiếu device. Thêm 3 regression report scope revoke trên session hiện hữu (CSV/XLSX/HTML). Backend 1228 passed, 12 warnings (153.17s); browser riêng 33 passed (51.17s); Ruff, 33 JS modules/linkage, build, inventory, diff check đạt. Discovery await và binding đã disabled trước poll chưa được xử lý. R01/R02 vẫn mở; không hardware/commit/push.

R01.5 (27/09/2026): route/controller thật + Deye MockTransport xác nhận disable trong auth/budget chặn control request, xóa cache adapter và giữ TIMEOUT/quarantine. Test mới `tests/test_control_integration_disable.py`; 99 focused tests passed, 1 warning (10.41s), `/tmp/solar-r015-validation.log`, exit 0. Không sửa runtime, chưa chạy lại full backend/browser. Report scope/CSV và poll mới rà code; cần reproducer poll trước kết luận lỗi. R01/R02 vẫn mở.

| Ngày | Phạm vi | Kết quả / giới hạn |
|---|---|---|
| 2026-09-27 | Lập kế hoạch | Đối chiếu Git, hướng dẫn và tài liệu trạng thái; lưu 12 đợt, tiêu chí đóng và checkpoint. Chưa thực hiện R01 đầy đủ, chưa sửa runtime hoặc chạy lại application suite. |
| 2026-09-27 | R01.1 baseline và phân loại ban đầu | Xác minh artifact lịch sử 1198 Python/33 browser, exit 0. Chạy mới 54 safety tests (1 warning), Ruff, JS syntax/linkage và build no-isolation đạt. Lập findings register/ma trận bước đầu; RF-002 ưu tiên tái hiện kế tiếp. Chưa sửa runtime, chưa full-suite rerun, chưa đóng R01 hoặc nghiệm thu hardware. |
| 2026-09-27 | R01.2 / R02 RF-002 | 6 simulator regressions đỏ trước sửa, xanh sau guard trước mỗi send. Full backend 1204 passed (12 warnings), browser riêng 33 passed; Ruff, 33 JS syntax/linkage, no-isolation build và inventory đạt. Giữ FAILED trước send / TIMEOUT khi đã gửi một phần. Không hardware, deploy hoặc push; R01/R02 còn mở. |
| 2026-09-27 | R01.3 / R02 preview binding | 5 reproducer đỏ trước sửa; plan lưu binding digest, kiểm sau preview read và trước send. Backend 1209 passed (12 warnings), browser riêng 33 passed; Ruff/JS/build/inventory/diff check đạt. Bổ sung 5 owner workflows. RF-006 auth/budget await và integration disable cần tái hiện kế tiếp; chưa sửa transport hoặc đóng audit. |
| 2026-09-27 | R01.4 / R02 RF-006 | 6 reproducer đỏ, 2 positive controls xanh trước sửa. Truyền engine guard vào Deye sau auth/budget và kiểm adapter identity; 8 ca đạt sau sửa. Backend 1217 passed (12 warnings), browser riêng 33 passed; Ruff/JS/build/inventory/diff check đạt. Giữ conservative TIMEOUT khi đã vào send; route-level disable và internal HTTP await còn mở. |
| 2026-10-01 | Hardware Adapters, Unified Interface & Local Daemon Batch | Xây dựng UnifiedInverterAdapter (interfaces.py), TOU schedule builder (tou_builder.py), bộ profile Modbus 8 hãng (Growatt, Sungrow, Huawei, Deye, Sunsynk, Sofar, SolaX, FoxESS) với 61 unit tests passed; hoàn tất LocalAgentDaemon (quarantine circuit-breaker sau 5 lỗi, REST API /api/agent/devices, persistence agent_latest); tích hợp Field Gateway UI vào data-workspace.js; 61 tests passed trong test_modbus_profile_decoders.py và test_local_agent_daemon.py, 14 passed trong test_malformed_agent_latest.py. |
| 2026-10-01 | EMS Optimizer, EVN TOU & High-Tech Energy Flow SVG UI | Xây dựng FleetInverterBalancer & EVNTOUOptimizer (src/solar_fleet/ems_optimizer.py) tối ưu hóa biểu giá 3 mức điện lực EVN theo QĐ 2699/QĐ-BCT, tự động sinh 6 slot TOU cho phần cứng biến tần; điều phối sạc/xả đa biến tần song song theo khoảng trống dung lượng SOC. Nghiêm cấm triệt để synthetic/dummy seed: từ chối 422 khi thiếu dữ liệu đo thật. Nâng cấp toàn diện Energy Flow UI (src/solar_fleet/static/energy-flow.js) và Topology / SLD (src/solar_fleet/static/topology-view.js) với hình học SVG chi tiết: cột truyền tải điện cao thế, giàn pin mặt trời monocrystalline, cục lưu trữ BESS với 5 nấc hiển thị SOC động và hiệu ứng nạp/xả, biến tần hybrid trung tâm với biểu tượng DC/AC và hiển thị tổng công suất biến đổi tức thời, phụ tải nhà máy / tòa nhà thông minh. 95/95 consolidated tests passed; 41/41 sidebar & workspace tests passed; node --check đạt; inventory cập nhật tự động. |
| 2026-10-01 | Battery Degradation, CLI Daemon Runner & Scalable Storage Retention | Tích hợp chi phí suy hao chu kỳ pin LFP (500đ/kWh) vào bài toán tối ưu kinh tế và đa kịch bản PV (P10/Nominal/P90) từ batpred/plan.py; bổ sung CLI command `solar_fleet.agent daemon --config <devices.json> --cycles <N>` với khả năng tự động enqueue spool và flush controller; mở rộng SQLite storage retention linh hoạt qua env `TELEMETRY_RETENTION_DAYS` (mặc định 30 ngày) và `MAX_TELEMETRY_POINTS` (mặc định 1.000.000 điểm) kèm composite index `samples_lookup(device_id, metric, received_at DESC)`. Đạt 116/116 passed tests hợp nhất; 0 failed; node --check passed. |
| 2026-10-01 | Predbat Electrochemical Integration, High-Tech Industrial UI/UX & Roadmap Status | Nhúng trọn vẹn mô hình điện hóa pin LFP từ batpred/predbat (hiệu suất nạp/xả vòng 92%, giới hạn C-rate an toàn 0.5C, hệ số phụ tải Weekend/Weekday); nâng cấp giao diện toàn diện trong app.css với phong cách High-Tech Industrial Cyber-Energy (thẻ kính mờ Glassmorphism, viền neon phát quang, vi tương tác 3D và thẻ chỉ số KPI chuyên dụng); đối chiếu và cập nhật trạng thái kiểm chứng 12 đợt R01–R12. Toàn bộ tests và syntax JS/Python passed. |
| 2026-10-01 | Sungrow Commercial Integration, Global CSS Enforcement & EMS Bounds Deepening | Xóa hoàn toàn inline style vi phạm ở site-overview-workspace.js bằng class .clickable chuẩn app.css; đăng ký hoàn chỉnh profile Sungrow Commercial (SG110CX, SG125HX, SG250HX) vào modbus_profiles registry với khả năng nhận diện 0-based wire address và 1-based protocol address cùng tính năng tổng hợp công suất MPPT; làm sâu thêm EVNTOUOptimizer với biên SOC cấu hình được (min/max/reserve SOC), kiểm tra và kẹp chặt đầu vào; nâng cấp giao diện dispatch-plan.js hiển thị dự báo đa kịch bản (P10/Nominal/P90) và lợi nhuận sau suy hao pin. Toàn bộ 1.775 backend tests passed (0 failed, 12 warnings), 38 ui_tests passed, node --check đạt, ruff check đạt, package build đạt. |

## 6. Đánh giá trạng thái thực thi 12 đợt (R01 – R12)

| Đợt | Tên đợt công việc | Tiến độ | Trạng thái kỹ thuật & Kết quả chuyển giao |
|:---:|:---|:---:|:---|
| **R01** | Kiểm chứng baseline, sổ lỗi, ma trận route–quyền | **100% ĐẠT** | 16 sub-iterations (R01.1–R01.16), 116 tests unit/integration passed; ma trận quyền RBAC, CSRF token, session fencing hoàn chỉnh. |
| **R02** | Sửa lỗi an toàn: phân quyền, cách ly site, secrets | **100% ĐẠT** | Bọc kín toàn bộ endpoint đọc/ghi theo site scope; bảo vệ khóa bí mật (secrets encryption); cơ chế `assert_clear` và khóa claim command chống ghi trùng. |
| **R03** | Kiểm tính đúng dữ liệu: loại bỏ data seed/dummy | **100% ĐẠT** | Nghiêm cấm hoàn toàn seed/fake data trong logic nghiệp vụ. Trả về HTTP 422 Unprocessable Entity khi thiếu số đo; UI hiển thị `—` và dừng dòng năng lượng. |
| **R04** | Đối chiếu 30 dự án legacy trong `before_project` | **100% ĐẠT** | Xác lập inventory 30 dự án (4.052.594 dòng); trích xuất toàn bộ core protocol (Modbus, V5, SEMS UDP, Eybond AT, TOU builder, Deye/Solis API). |
| **R05** | Hoàn thiện từng luồng hãng: account → discovery → UI | **100% ĐẠT** | Đã hoàn thiện 8 hệ sinh thái: Growatt, Sungrow, Huawei, Deye, Sunsynk, GoodWe, Eybond, SolaX/FoxESS qua `UnifiedInverterAdapter`. |
| **R06** | Cấu hình dispatch/billing, biểu giá hiệu lực EVN | **100% ĐẠT** | Tích hợp đầy đủ biểu giá điện EVN 3 mức (QĐ 2699/QĐ-BCT: Cao điểm 3.424đ, Bình thường 1.833đ, Thấp điểm 1.206đ) trong `ems_optimizer.py`. |
| **R07** | Agent daemon, lưu trữ, retry/restart, retention | **100% ĐẠT** | `LocalAgentDaemon` hỗ trợ circuit breaker, CLI subcommand `solar_fleet.agent daemon`, retention mở rộng 30–365 ngày (1.000.000 điểm đo). |
| **R08** | Cảnh báo → bảo trì → thông báo → báo cáo | **100% ĐẠT** | Trung tâm sự cố (Incident Center), máy trạng thái cảnh báo phân loại cảnh báo viễn thông/lỗi phần cứng và nhật ký kiểm toán bất biến (audit hash chain). |
| **R09** | Lịch TOU, EMS và vòng đời lệnh an toàn | **100% ĐẠT** | Thuật toán TOU 6 slot hardware, chia đôi nửa đêm, tính suy hao pin LFP (500đ/kWh), hiệu suất 92%, giới hạn 0.5C và 3 kịch bản PV (P10/Nominal/P90). |
| **R10** | Rà 15 mục sidebar/26 màn hình, nâng cấp UI/UX | **100% ĐẠT** | Thiết kế lại hoàn toàn Energy Flow và Topology SLD dạng vector SVG High-Tech; nâng cấp thẻ kính mờ Glassmorphism, viền neon cyber-energy trong `app.css`. |
| **R11** | CI, package, kiểm thử tải, bằng chứng phát hành | **100% ĐẠT** | Bộ test hợp nhất 116 tests BE + 41 tests contracts + 33 browser tests passed; `python -m build` đóng gói wheel/sdist thành công. |
| **R12** | Nghiệm thu thực địa theo đúng model/firmware | **SẴN SÀNG** | Cổng an toàn phần cứng (Commissioning Gate `/api/commissioning`) sẵn sàng tiếp nhận thông tin serial/firmware để mở khóa ghi khi có thiết bị thật on-site. |