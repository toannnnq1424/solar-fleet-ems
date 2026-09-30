# Rà soát và tái sử dụng before_project — 27/09/2026

## Đối chiếu lại trên macOS — 28/09/2026

Đã kiểm tra thực tế `/Users/toanlamsaoduocc/Downloads/before_project` bằng
`scripts/reconcile_legacy.py`. [Bằng chứng từng dự án](evidence/legacy-reconciliation-2026-09-28.json)
ghi đủ 30/30 thư mục, hash license và disposition **reference-only cho mọi import mới**;
không thay đổi quyết định reuse đã được ghim bên dưới. Cả **43 file nguồn được ghim** trong
model-source-lock khớp SHA-256 hiện tại. Không tải/chạy code upstream hoặc thêm dependency.

29/30 dự án có số file khớp inventory cũ; OpenEMS có 17.011 thay vì 9.161 file theo bộ loại trừ
đã ghi. Không suy ra cùng revision chỉ từ số file: original per-file manifest và thuật toán
tree hash lịch sử không có trong checkout này. Script công bố thuật toán mới riêng, không so
hai loại tree hash như thể tương đương. `solis-modbus-ha-main` vẫn không tìm thấy license file;
không cho phép sao chép. Hash license không thay cho rà nghĩa vụ từng file/dependency.

R04 đã có đối chiếu local tái lập; vẫn mở deep license/owner review trước reuse mới và đối chiếu
phần OpenEMS khác biệt. Không gọi toàn bộ 30 dự án READY hoặc release sạch license.

[README dự án](../README.md) · [Mục lục](README.md) · [26 mockup và LOC](mockup-coverage.md) · [Hướng dẫn kết nối](model-library-and-home-assistant.md) · [Kiểm thử đợt này](legacy-validation-2026-09-27.md)

## Phạm vi thực sự đã đọc

Thư mục tìm thấy là `D:\Downloads\before_project`. Đã lập inventory 30 dự án, 16.348 file và 4.052.594 dòng UTF-8, bỏ thư mục dependency/build/cache/Git. Số này bao gồm CSV, JSON, YAML và tài liệu, **không phải LOC sản phẩm**. [Manifest dự án](evidence/legacy-project-inventory.json) giữ số file/dòng, hash cây, license và quyết định từng dự án; manifest từng file đầy đủ nằm local tại `work/legacy/file-manifest.json`.

Đã đọc README/tổng quan của cả 30 dự án, tìm protocol/profile/forecast/UI, rồi đọc sâu các file được chọn bên dưới cùng một số implementation thay thế. Đây **không phải xác nhận đã phân tích ngữ nghĩa mọi dòng trong hơn bốn triệu dòng**. Các mục chưa đọc sâu được giữ là nghiên cứu tiếp; không gọi toàn bộ code cũ đã được nghiệm thu.

Ưu tiên là mục đích 26 mockup, dùng chung sidebar, quyền và nguồn dữ liệu. Không thêm một dashboard Home Assistant riêng cạnh dashboard fleet. Những chức năng chỉ có thể chạy trong HA, Go, Java/OSGi hoặc firmware không được chuyển nguyên thư mục rồi coi là chạy được trong Python controller.

## Quyết định theo toàn bộ 30 dự án

License dưới đây là kết quả kiểm tra bản local; trước khi tái sử dụng thêm phải ghim đúng revision và kiểm tra nghĩa vụ từng file/dependency. GPL/AGPL/MPL không bị coi là cấm sử dụng: chúng cần một quyết định phân phối/tích hợp phù hợp, chưa được nhập tùy tiện trong đợt này.

| Dự án local | License đã thấy | Chức năng đáng lấy / quyết định hiện tại |
|---|---|---|
| batpred-main | Personal-use restriction trong License.md | Thuật toán pin/forecast đáng nghiên cứu; không sao chép code hạn chế thương mại vào sản phẩm này |
| deye-inverter-mqtt-main | Apache-2.0 | MQTT, AT/TCP/Modbus cho logger cụ thể; nghiên cứu LSE3, chưa nhập driver hoặc auto-write |
| deye-modbus-ha-main | MIT | SG04LP3/SG05LP3, nguồn đối chiếu; chưa giả định cổng 8899 là Modbus TCP thông thường |
| emhass-master | MIT | Tối ưu năng lượng/forecast; hiện có thể nhận sensor HA của cài đặt độc lập, chưa nhúng optimizer/cvxpy/dispatch |
| esp-eybond-collector-main | GPL-3.0 | Firmware collector PI30/SMG; cần thiết bị và flashing workflow, chưa tích hợp firmware |
| evcc-master | MIT base, điều kiện thành phần sponsor riêng | Đọc EnergyflowVisualization.vue để tham khảo trình bày; chưa tích hợp bộ sạc EV, chuyển pha hoặc daemon Go |
| goodwe-master | MIT | ET/EH và các giao thức UDP/TCP theo model; đối chiếu protocol, chưa thay cloud SEMS bằng thư viện local |
| growatt_modbus-main | GPL-3.0 | Tách model/register; tránh logic chỉnh thời gian tự động khi port collector; chưa nhập runtime |
| Growatt_ModbusTCP-main | MIT | Bộ model local khác; cần đối chiếu revision/word/sign trước khi nhập |
| ha-dessmonitor-3b530bf34d91eef43ec2474d971019fa48c5ae16 | MIT | Wire contract đã dùng trong Eybond/DessMonitor ở đợt trước; không tạo adapter trùng |
| ha-eybond-local-main | MPL-2.0 | Catalogue 17 model/19 biến thể PI17/18/30/SMG/SRNE; chưa chuyển protocol engine thành driver được nghiệm thu |
| ha-growatt-modbus-main | MIT | Model/phase detection; chưa tự bật profile từ một thanh ghi nhận diện |
| ha-smartess-local-master | MIT | PI17 iGrid SV IV, UDP redirect; chưa bật broadcast hoặc đổi server logger |
| ha-solarman-main | MIT | **Đã nhập 30 bộ định nghĩa**; đọc parser/common/const, chuyển phần decode đủ ngữ nghĩa sang engine riêng |
| home_assistant_solarman-main | Apache-2.0 | Profile đời khác/trùng nguồn; giữ nghiên cứu, không nhập trùng cùng tên |
| homeassistant-growatt-modbus-main | Apache-2.0 | Driver TCP/UDP/RTU; chưa hợp nhất các model không tương đương |
| huawei-solar-lib-develop | AGPL-3.0 | Không chép library vào core; cầu HA độc lập nhận sensor, chưa có full local Huawei driver |
| huawei_solar-main | AGPL-3.0 | HA integration; cùng ranh giới cầu sensor, không chuyển quyền HA thành quyền điều khiển fleet |
| ioBroker.goodwe-sems-main | MIT | Đối chiếu Classic SEMS đang có; không nhập runtime ioBroker |
| openems-develop | Edge/Backend EPL-2.0; UI AGPL-3.0 | Dispatch/edge architecture; chưa port runtime Java/OSGi hay thuật toán điều khiển |
| pygoodwe-main | MIT | Contract Classic SEMS đã tham khảo; không phải SEMS+ toàn bộ |
| PyPi_GrowattServer-6469d881462eaa4a3b3c6e3cfa6f17082e86eaf5 | MIT | Nguồn OpenAPI v1 MIN/SPH hiện có; chưa thêm toàn bộ Shine/OSS |
| pysolarmanv5-8cfe84650f48f0803c32b3c4ca061364abd9cf49 | MIT | **Dùng dependency ghim 3.0.6** cho collector SOLARMAN V5 chọn rõ logger |
| sem-community-main | MIT | **Adapt hourly EWMA**, nghiên cứu HA sensor bridge và flow card; không gọi HA services hoặc chép mọi policy |
| solar-inverter-modbus-registers-main | MIT | **Nhập cả 10 profile**, giữ FC/address offset/scale/word semantics |
| solis-modbus-ha-main | Chưa thấy license đủ rõ | Không sao chép; dùng nguồn MIT thay thế trong catalogue |
| solis2mqtt-main | GPL-3.0 | Nguồn đối chiếu Solis local, chưa nhập whole MQTT service |
| Sungrow-SHx-Inverter-Modbus-Home-Assistant-main | MIT | **Nhập 99 field trong 1 profile**, 79 field có decoder; cấu hình HA không được thực thi |
| virtual-power-plant-main | MIT | Đọc Modbus/UI/architecture; không nhập mặc định số đo giả hoặc float32 đọc một register |
| vpplib-dev | GPL-3.0 | Mô phỏng năng lượng/offline scenarios; chưa tích hợp optimizer hoặc live controller |

## Những mảng chức năng đã chuyển thành code chạy trong dự án

| Mảng / ảnh mục tiêu | Nguồn và mã mới | Liên kết thực tế | Giới hạn |
|---|---|---|---|
| Model-aware device inspection — 07, 13, 16, 26 | [Importer](../scripts/import_model_library.py), [model library](../src/solar_fleet/model_library.py), [UI](../src/solar_fleet/static/model-workspace.js) | Chọn model → chọn field → kế hoạch FC03/04 → decode dữ liệu nhập → config collector | 41 profile cộng đồng, không phải 41 máy được nghiệm thu; không write |
| Agent/local logger — 14, 17 | [Local transport](../src/solar_fleet/local_models.py), [agent](../src/solar_fleet/agent.py) | Đọc TCP/V5 → outbox bền vững → agent inbox cùng sequence/replay → native telemetry → mapping workspace | Chạy CLI từng lần; chưa RTU/service/discovery/mTLS/managed update |
| Home Assistant / home energy — 13, 14, 17 | [HA bridge](../src/solar_fleet/home_assistant_bridge.py) | GET sensor đã chọn, kiểm tra unit/time/entity → cùng outbox/ingest; có thể nhận sensor do EMHASS/SEM/HA cung cấp | Không dịch vụ điều khiển HA, không import automation YAML, chưa lập lịch polling service |
| EMS forecast baseline — 24 | [Baseline](../src/solar_fleet/forecast_baseline.py), [EMS UI](../src/solar_fleet/static/ems-workspace.js) | Lịch sử canonical đã xác minh → hourly EWMA → dự báo tham khảo 24h trong EMS | Cần dữ liệu đủ ngày/giờ; không phải optimizer, accuracy chưa nghiệm thu, không dispatch |
| Energy flow — 02–04, 26 | [Shared flow](../src/solar_fleet/static/energy-flow.js), [flow snapshot](../src/solar_fleet/operational_views.py) | Cùng component site/device; PV/grid/battery/load/EPS, generator khi có số đo; hướng theo dấu, nguồn/thời hạn, route chi tiết | Chưa topology điện được nghiệm thu hoặc phân bổ nguồn→từng tải; không giả dữ liệu thiếu |
| UI/global styles — toàn bộ | [app.css](../src/solar_fleet/static/app.css) | Một stylesheet/sidebar; chế độ bảng, toàn màn hình, dừng chuyển động, reduced motion, VI/EN | Đã sửa 2 dấu đóng CSS thiếu; chưa full usability/accessibility acceptance 26 màn hình |
| Device maintenance truthfulness — 07, 23, 26 | [Device workspace](../src/solar_fleet/static/device-workspace.js) | Bỏ giờ chạy/chu kỳ/SOH/bảo hành mẫu; firmware chuyển đến luồng bảo trì thật | Không tạo trạng thái OTA thành công giả; vẫn chưa firmware executor |

## Nguồn được ghim và mức chuyển đổi

[Lockfile](../src/solar_fleet/data/model-source-lock.json) lưu commit, đường dẫn nguồn, SHA-256 và Git blob SHA-1. Những file được chọn khớp revision công khai kiểm tra, không phải khẳng định cả working tree local khớp upstream.

| Nguồn | Commit | Kết quả |
|---|---|---|
| [ha-solarman](https://github.com/davidrapan/ha-solarman/tree/ac1d88b83268beeb0511b8a1b7fc8e17deddc044) | ac1d88b83268beeb0511b8a1b7fc8e17deddc044 | 30 profile, 2.843 field; 769 decoder, 2.074 field giữ lý do chưa hỗ trợ |
| [Glance registers](https://github.com/szlaskidaniel/solar-inverter-modbus-registers/tree/9fa04b0d4a8e8ed2e578302469a445938a0f34f0) | 9fa04b0d4a8e8ed2e578302469a445938a0f34f0 | 10 profile, 203 field; 65 decoder, 138 chưa đủ ngữ nghĩa |
| [Sungrow HA](https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant/tree/310635c6e2c1122f5adb54fba7fdf33a7cb85142) | 310635c6e2c1122f5adb54fba7fdf33a7cb85142 | 1 profile, 99 field; 79 decoder, 20 chưa đủ ngữ nghĩa |
| [SEM community](https://github.com/traktore-org/sem-community/tree/45438efcb382f065927713ae44f4878b62b694f7) | 45438efcb382f065927713ae44f4878b62b694f7 | Adapt predictor hourly EWMA; flow-card/shared UI đọc để thiết kế component độc lập |

Tổng **41 profile / 3.145 field / 913 decoder**. 2.232 field còn lại vẫn hiện trong inspector với lý do; không âm thầm coi đã hỗ trợ. Conditional MPPT/pack, derived/stateful values, sentinel/custom formats và write controls cần xử lý riêng. Catalogue JSON là dữ liệu sinh từ nguồn mở, không cộng vào LOC code sản phẩm tự viết. Notices và MIT licenses nằm trong [THIRD_PARTY_NOTICES](../THIRD_PARTY_NOTICES.md) và gói wheel.

Transport TCP triển khai theo [Modbus TCP guide](https://www.modbus.org/file/secure/messagingimplementationguide.pdf) và [Application Protocol](https://www.modbus.org/docs/Modbus_Application_Protocol_V1_1b3.pdf); HA theo [REST API](https://developers.home-assistant.io/docs/api/rest/). Không suy protocol từ logo Bluesun/Deye hoặc số cổng.

## Vì sao không kéo nguyên tất cả

Code cũ chứa sản phẩm khác phạm vi và cả logic cần sửa. Ví dụ helper float32 của virtual-power-plant đọc một register dù cần hai; UI có giá trị mặc định khi thiếu sensor. Một số flow card cũng đổi thiếu dữ liệu thành 0. Bản mới giữ unknown và kiểm tra độ mới. Baseline mới đếm ngày thực tế, deduplicate theo timestamp, không lấy số ô weekday/hour làm số ngày dữ liệu, không bù zero vào khoảng trống.

Các chức năng hấp dẫn nhưng **chưa xây**: tối ưu giá/PV/battery degradation, forecast thời tiết kết hợp dispatch, EV/phase switching, priority load shedding, PI17/18/30/SRNE engine, managed MQTT/Home Assistant discovery, OpenEMS edge policies, inverter-native writes và offline recovery. Chúng cần được bổ sung dưới EMS, Thiết bị, Dữ liệu, Bảo trì hiện có với cùng RBAC/command engine. Việc loại license không phù hợp chỉ giải thích một phần; phần lớn còn là engineering chưa hoàn thành.
