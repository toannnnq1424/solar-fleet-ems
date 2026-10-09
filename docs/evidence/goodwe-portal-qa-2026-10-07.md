# GoodWe SEMS+ — baseline QA chỉ đọc, 07/10/2026

Người dùng tự đăng nhập trên `https://semsplus.goodwe.com/` rồi cho phép tiếp tục
kiểm tra. Đây là **quan sát portal hãng**, không phải thử đăng nhập hoặc đồng bộ
qua SolarOne. Không lấy password/cookie/token, không xuất HAR, không ghi định danh,
địa chỉ, số đo khách hàng hoặc ảnh phiên đăng nhập vào repository. Chỉ điều hướng
mục đọc; không xác nhận alarm, tạo báo cáo, đăng ký nhận tin, thay cấu hình hay phát lệnh.

## Quan sát trực tiếp (E, giới hạn theo phiên/quyền hiện tại)

- Portal SEMS+ hiển thị tiếng Việt; trang login trước đó chọn máy chủ quốc tế.
  Host API/region backend chính xác chưa được quan sát, không suy ra từ ngôn ngữ.
- Danh sách đã tải có một nhà máy; hai inverter lưu trữ, một logger LAN.
  Cây thiết bị phụ thuộc logger hiển thị hai inverter và một meter. Chưa xác minh
  model/firmware hoặc toàn bộ battery/BMS inventory; không suy topology điện từ cây này.
- Dashboard có PV/lưới/tải/pin/SOC, mốc cập nhật dạng giờ địa phương, năng lượng
  ngày, đường cong công suất, heatmap và luồng năng lượng. Số đo trên chi tiết inverter
  thay đổi giữa hai lần quan sát. Điều đó không tự chứng minh độ trễ, timestamp UTC,
  dấu/quy ước đơn vị của API hoặc độ chính xác vật lý.
- Chi tiết inverter có active/reactive power, DC input, năng lượng nạp/xả, MPPT,
  lịch sử hoạt động. Hệ số công suất có thể hiển thị `--` ngay khi số đo khác có giá trị:
  tuyệt đối không thay missing bằng zero hoặc một giá trị suy đoán.
- Cảnh báo trong cửa sổ thời gian mặc định có cả trạng thái phục hồi và chưa xác nhận.
  Tab đang xảy ra trống không có nghĩa lịch sử alarm trống. Một số dòng lịch sử cùng
  SN có tên nhà máy khác tên hiện tại; **chưa biết đổi tên hay chuyển liên kết**.
  Cần lưu ID/scope theo sự kiện, không nối alarm vào site chỉ bằng tên hiện hành.
- Logger có biểu đồ công suất, tín hiệu và trạng thái; các nhãn Peak Shaving,
  bảo vệ SOC nối lưới, chế độ làm việc và quản lý nhu cầu hiện diện ở logger.
  Đây không phải bằng chứng các tính năng đó thuộc từng inverter hoặc gọi được bằng API.
- Trung tâm báo cáo liệt kê báo cáo sản xuất/thu nhập, so sánh nhà máy,
  dữ liệu vận hành inverter và so sánh thiết bị; có trạng thái chưa đăng ký.
- Menu phân tích hiển thị chẩn đoán I–V, so sánh dữ liệu, tính nhất quán pin.
  Không chạy chẩn đoán I–V: thao tác này có thể tác động thiết bị.
- Nhãn điều khiển AC/backup/work mode/on-off/điều độ có xuất hiện, nhưng không mở/gửi
  form để thử quyền ghi. Visibility không là authorization hay commissioning.

## Đối chiếu code thật

`adapters/goodwe.py` vẫn là classic SEMS: `CrossLogin`, plant ID nhập tay,
`GetMonitorDetailByPowerstationId`, `invert_full`; discovery chỉ tạo INVERTER.
Không có SEMS+ auth/discovery/logger/meter/battery contract đã nghiệm thu. Browser
đăng nhập được không xác nhận các hàm này chạy được với tài khoản vừa kiểm tra.

Phát hiện xác nhận trong code: `GoodWe.latest()` gán `deviceState=1` bất kể trạng thái
native và thời gian số đo. Đã bỏ gán online cố định, giữ `None` cùng raw native status;
5 regression trường hợp synthetic giữ số 0 hợp lệ, timestamp unknown và không báo online.
Adapter version tăng `0.3.1`. Không thêm enum theo phỏng đoán hoặc mapping SEMS+.

**Giới hạn chưa sửa:** common `DeviceObservation`/`MeasurementObservation`/`Device`
vẫn dùng boolean online. Decoder biến unknown thành `False`; bản vá chỉ loại false-positive
online, chưa hoàn thành trạng thái ba giá trị. I2 phải tách UNKNOWN/OFFLINE/ONLINE cùng
time/source; rà các UI đang diễn giải `False` thành offline trước khi nghiệm thu connector.

UI hướng dẫn SEMS+ hiện tách ba bước: tài khoản portal → kiểm tra inventory → kết nối
SolarOne chưa sẵn sàng. Không gắn trạng thái phiên của khách hàng vào giao diện chung,
không tự điền ID/số đo, không mở form legacy cho lựa chọn SEMS+.

## Nguồn công khai và hướng xử lý khả thi

Nguồn hãng: [SEMS+ product](https://en.goodwe.com/semsplus-series-smart-energy-management-system).
Nguồn triển khai cộng đồng được kiểm tra ở revision cố định:
[bueste/ioBroker.goodwe-sems](https://github.com/bueste/ioBroker.goodwe-sems/tree/5d6b4796e60a022a97b38fdb0f551304cf518033),
`lib/semsApi.js`, `test/unit/semsApi.test.js`, `lib/mapping.js`, `README.md`, `LICENSE`.
MIT, Copyright 2026 Stefan Bühler; chưa sao chép code hoặc thêm dependency.

Nguồn này triển khai SEMS+ cross-login và gateway riêng; test mô tả device metadata và
telemetry factors. Battery có thể cần related-device riêng. Đây là evidence cộng đồng,
chưa chứng minh tương thích account/region/model của phiên này. Không bê nguyên fallback
host, tự đăng nhập lại trên mọi lỗi, ghi raw response vào log hoặc tự gán `agreement=1`.
API GitHub trả 403 khi nghiên cứu; đọc public clone ghim revision, không dùng phiên khách.

Nguồn ứng viên `timvanderHorst/goodwe-semsplus` chỉ đọc README; chưa xác minh license,
không nhập code. Không suy rằng tất cả đường SEMS cũ mọi vùng đều đã chết từ một dự án EU.

## Bước triển khai tiếp theo

1. I1: transport SEMS+ read-only trong cùng plugin GoodWe, chọn platform/region tường minh,
   allowlist host/path, auth refresh có giới hạn, vault/redaction, tách lỗi auth/quota/protocol.
   Không thử hàng loạt region/host bằng tài khoản thật. Terms/customer consent phải rõ.
2. I2: account inventory phân trang → plant ID → typed inverter/logger/meter/related battery;
   đi qua Controller và scope/revision guards hiện hữu. Không tạo client song song.
3. I2: giữ native factor/unit/timestamp/quality; UNKNOWN cho thiếu thời gian/ý nghĩa dấu.
   Hoàn thiện connectivity ba trạng thái; plant aggregate không cộng lại với device totals.
4. I3: alarm ID, xảy ra/phục hồi/xác nhận, historical site scope; lịch sử có khoảng phủ và
   thời gian gốc. Không suy recovery = acknowledged, không nhập alarm theo tên site.
5. Q1 connector: fixture/negative tests trước, sau đó người dùng tự nhập tài khoản vào
   SolarOne và chỉ đọc; đối chiếu inventory/số đo/timestamp cùng cửa sổ với portal.
   Hardware write vẫn cần quyền thử riêng, exact profile và fresh readback.

## Kiểm chứng đợt sửa

- Backend: **1.815 passed, 12 deprecation warnings, 301,50s**, chạy bằng
  `/tmp/solar-fleet-audit-8ec68fd/bin/python -m pytest tests -q`, exit 0.
- Browser: **96 passed, 152,16s**, `work/ui-venv/bin/python -m pytest ui_tests -q`,
  exit 0. SEMS+ guide checked at 1600/1024/430 px, no password field or enabled
  legacy continuation. This is fixture QA, not customer-account API acceptance.
- Focused GoodWe adapter + final source-registry checks: **11 passed**, 0,08s.
- Ruff and changed-JS syntax: passed. sdist/wheel build passed; rebuilt after
  synchronizing packaged research registry. No new profile or dependency imported.
- Inventory regenerated with `scripts/measure_code.py --update-doc`; no new UI screen
  or owner. No full-screen pixel acceptance inferred from the account-dialog checks.
- First UI/build calls in the older audit environment lacked Playwright/build and
  could not run; switched to `work/ui-venv/bin/python`. Those attempts are not passes.
- Temporary logs: `/tmp/solar-goodwe-qa-backend.log`, `solar-goodwe-qa-ui.log`,
  `solar-goodwe-qa-build-final.log`. No signed-in browser was used by automated tests.
