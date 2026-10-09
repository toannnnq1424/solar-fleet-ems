# Kiểm toán lớp tích hợp đa hãng SolarOne

04–05/10/2026. Worktree `fix/real-data-engine-integration`, HEAD `af4f1b8ab70d91e24ca0b44bc8b71d1c9f274be0`, có nhiều thay đổi chưa commit từ trước. Đây là audit code đang có, không chứng nhận toàn bộ hai nhánh/lịch sử đã được audit lại. Không sửa backend trong đợt này, không gọi tài khoản/hardware.

## Trả lời ngắn

**Có lớp chung thật, nhưng chưa hợp nhất hoàn chỉnh. Vẫn có chức năng hãng nằm ngoài đường vận hành chung.** Không nên xóa mọi phần riêng của hãng; cần đặt chúng dưới hợp đồng extension có scope, evidence, chất lượng dữ liệu và command lifecycle thống nhất.

## Phần đang nối đúng hướng

- [integration.py](../src/solar_fleet/integration.py): `IntegrationRegistry`, `IntegrationPlugin`, observations và factory/decoder/capability hooks.
- [controller.py](../src/solar_fleet/controller.py): `integration_adapter`, `discover`, `poll` dùng registry; kiểm config/credentials/binding/revision, chuyển dữ liệu qua `telemetry.normalize_points` rồi profile và store. Đây không chỉ là interface trang trí.
- [control.py](../src/solar_fleet/control.py): `CommandEngine` giữ preview/guard/serialization/idempotency/readback/quarantine; compiler đi qua registry.
- [app.py](../src/solar_fleet/app.py): các API thiết bị chung kiểm scope và feature trước khi đọc; history native được gắn `UNVERIFIED`, không giả là canonical measured.

Luồng chính hiện tại: account/vault → registry → adapter hãng → decoder/normalization → store → API/workspace. Luồng ghi hợp lệ phải qua CommandEngine và commissioning. Các thành phần có tên `Unified*` dưới đây không phải bằng chứng thay thế cho luồng này.

## Các phát hiện

### IA-01 — Hợp đồng chung còn nông, history/alarm bị để riêng

**UNBUILT, P1 cho phạm vi hãng cần pilot.** [plugins.py](../src/solar_fleet/adapters/plugins.py) `_VENDOR_CONFIG` chỉ đăng ký discovery/latest cho bảy nền tảng ngoài Deye. Deye còn khai báo history/configuration/alarms. Không được chỉ bật thêm flag để “hoàn thành”.

Các hàm đã có nhưng chưa hợp nhất:

| Adapter | Code | Vì sao chưa dùng như API chung được |
|---|---|---|
| Huawei | `history(dev_id, dev_type_id, collect_time)`, station day/month/year, `alerts` | Chữ ký khác `serial,start,end,points` của route chung; cần time/unit/type mapping |
| Solis | `history_day/month/year`, `alerts` | Có yêu cầu ngày/múi giờ/tiền tệ riêng; chưa là backfill canonical |
| SOLARMAN | `history`, `station_history`, `alerts` | Registry chưa công bố; chưa đủ pipeline normalization/incident |
| Deye | history/config/alarms được công bố | History route trả payload native `UNVERIFIED`, không nhập kho lịch sử chuẩn hóa |

Vị trí: [huawei.py](../src/solar_fleet/adapters/huawei.py), [solis.py](../src/solar_fleet/adapters/solis.py), [solarman.py](../src/solar_fleet/adapters/solarman.py); GET/POST `/api/devices/{id}/history` trong app.py. GET là retention cục bộ 7 ngày, không thể coi đã truy được toàn bộ lịch sử cloud.

### IA-02 — Có hook nhưng thiếu mapping được đăng ký

**UNBUILT, P1.** `IntegrationPlugin` có `telemetry_profiles`, `control_profiles`, `decode_alarm`, `compile_schedule`. Các builtin trong `plugins.py` không truyền các hook này, nên mặc định vẫn rỗng/None. Profile ở service khác không tự trở thành hook của registry.

`Controller.collect_alarms` trả `NATIVE_ONLY` khi `decode_alarm is None`. Vì vậy có phương thức đọc alarms không đồng nghĩa incident đã được chuẩn hóa/correlate. Native groups chưa có field schema được nghiệm thu; phần lớn hãng chưa có `compile_intent`. Đây là engineering còn thiếu, không phải chỉ thiếu app secret.

### IA-03 — Facade UnifiedCloudAdapter có thể tạo trạng thái measured/online sai

**CONFIRMED_BUG; ưu tiên P1 trước khi dùng facade này, chưa chứng minh ảnh hưởng poll chính.** [interfaces.py](../src/solar_fleet/adapters/interfaces.py), `UnifiedCloudAdapter.get_telemetry`, khoảng dòng 740–774:

- Có row là trả `online=True`, `freshness_state="MEASURED"` và timestamp hiện tại.
- Nếu row không có `points`, toàn bộ dictionary bị coi là các điểm đo, kể cả `deviceSn`, `deviceState`, `collectionTime`, `dataList`.
- Lấy row đầu, không chứng minh SN/time/quality đúng với thiết bị yêu cầu.

Reproducer in-memory đã chạy, không mạng, không persistence:

```python
import asyncio
from solar_fleet.adapters.interfaces import UnifiedCloudAdapter

class Probe:
    async def latest(self, serials):
        return [{"deviceSn": "AUDIT-ONLY", "deviceState": 0,
                 "collectionTime": 1, "dataList": []}]

async def main():
    adapter = UnifiedCloudAdapter(Probe(), vendor="Audit", model="Audit",
                                  serial="AUDIT-ONLY", device_id="AUDIT-ONLY")
    snapshot = await adapter.get_telemetry()
    print(snapshot.online, snapshot.freshness_state, list(snapshot.points))

asyncio.run(main())
```

Kết quả: `True MEASURED ['deviceSn', 'deviceState', 'collectionTime', 'dataList']` dù đầu vào mô tả offline và thời gian rất cũ.

**Giới hạn ảnh hưởng:** tìm references trong `src/solar_fleet` chỉ thấy định nghĩa/factory và exports `adapters/__init__.py`; chưa thấy controller chính gọi facade. Controller dùng decoder khác. Không được diễn giải phát hiện này thành “dashboard đang luôn báo mọi máy online”. Đề xuất loại bỏ/quarantine facade trùng hoặc buộc nó dùng cùng decoder, không chữa bằng thêm default.

### IA-04 — API hãng riêng vẫn tồn tại, đa phần là công cụ thuần hoặc bị khóa

**ARCHITECTURE_GAP, P2; không phải bằng chứng bypass đang phát lệnh.** [phase_d_api.py](../src/solar_fleet/phase_d_api.py) còn các nhóm Deye hybrid, Solis hybrid/MQTT, Growatt SPH/multiphase/cloud, SOLARMAN V5, GoodWe SEMS/local, SmartESS, Huawei local.

Đã lần theo các trường hợp đại diện:

| Route / nhóm | Hành vi thực tế | Kết luận |
|---|---|---|
| `/api/solis-hybrid/compile-*`, `decode-*` | Biên dịch/giải mã payload qua helper | Không phải executor đã nối tài khoản |
| `/api/goodwe-sems/login` | 409, yêu cầu luồng account đã đăng ký | Không phải login SEMS+ mới |
| GoodWe station/monthly detail | Yêu cầu payload do caller cung cấp, parse | Không tự đọc cloud của người dùng |
| `/api/smartess/poll` | 409 | Không có live poll ở route này |
| SmartESS command | Client chạy với simulated=False; executor trả `LOCKED_PENDING_HARDWARE_ACCEPTANCE` | Không có bằng chứng cờ caller mở khóa được |
| `/api/growatt-cloud/plants`, devices, sph-detail | 503 | Không phải integration hoàn chỉnh |
| GoodWe/Huawei local telemetry | 503 | Helper/protocol không là live telemetry |

Không nên dùng số route/class để báo tỷ lệ hoàn thành. Các decoder/compiler hữu ích nên là thư viện nội bộ hoặc native extension có schema; không tạo một app vận hành riêng với trạng thái/permission khác.

### IA-05 — BluesunAdapter không phải đường Bluesun đang vận hành

**INTEGRATION_GAP / dữ liệu suy đoán, P2 trước khi nối lớp này.** [bluesun_adapter.py](../src/solar_fleet/adapters/bluesun_adapter.py) không được đăng ký trong builtin registry; chưa tìm thấy production caller. Có nhánh dựng metadata như chemistry/nominal voltage/C-rate theo giả định. Không dùng chúng làm số đo hoặc thông số chắc chắn của mọi pin Bluesun. Write bị khóa, không khẳng định đã điều khiển phần cứng.

Đường hiện hữu là SOLARMAN hoặc Eybond/SmartESS, kèm `metadata.declared_equipment_brand`. Đây là cách tách brand/platform đúng hơn. Cần profile exact identity và nguồn chính thức, không thêm lựa chọn “Bluesun Cloud” chỉ từ tên class.

### IA-06 — Authentication chưa đồng nhất về hành trình người dùng

**UNBUILT / INVESTIGATE, P1 cho live QA.** Deye đã tách khóa ứng dụng của quản trị và email/password của tài khoản, nhưng tenancy/customer grant chưa được nghiệm thu thật. GoodWe connector legacy chưa xác nhận SEMS+; logo GoodWe không đủ xác định nền tảng. Solis `_get_oauth2_token` hiện dùng client_credentials trong khi luồng customer authorization chính thức dùng consent/code; phải đối chiếu rõ mode/endpoint trước khi thử tài khoản.

Tham khảo [các hướng dẫn theo hãng](vendor-api-access-guide-vi.md). Không phải mọi hãng đều dùng cặp App ID/App Secret, và một UI hai ô không thể bỏ điều kiện ứng dụng/quyền của hãng.

### IA-07 — Nhiều protocol chữ ký khác nhau làm tăng nguy cơ gọi lệch

**DESIGN_RISK, P2.** Ngoài ReadAdapter của registry còn các protocol/facade/mixin trong interfaces.py và base adapter. `InverterControlMixin` gọi `send` trực tiếp sau build; default build có khóa, chưa thấy đường production bypass. `_read_config` trong control.py bắt TypeError để retry signature khác; lỗi TypeError bên trong implementation cũng có thể gây đọc lần hai. Nên thống nhất hợp đồng cụ thể và adapter bridge, không dùng ngoại lệ runtime để phát hiện signature.

## Kiến trúc đích đề xuất

1. Một hợp đồng đọc: identity, scope, cursor/time range, source time, metric/unit/quality/provenance; lịch sử/alarms có kiểu dữ liệu riêng, không dictionary tùy ý.
2. Capability descriptor từ account + model + firmware + bằng chứng. UNKNOWN khác UNSUPPORTED, read khác write, saved khác verified.
3. Native extensions vẫn được giữ, có namespace/schema/permission và cùng audit/lifecycle. Ví dụ I‑V không ép thành toggle universal.
4. Mọi electrical write đi qua CommandEngine; facade/helper không được tự trở thành executor. Không sửa chỉ bằng chuyển URL.
5. Frontend dùng cùng owner nguồn/thiết bị/cảnh báo, giải thích lý do khóa; không hiển thị succeeded/online khi mới có hồ sơ.

## Thứ tự sửa và điều kiện QA

- Khoanh các facade chưa nối; viết regression cho IA-03 trước khi thay runtime.
- Chọn một hãng và một read vertical slice: auth → discovery → latest/history/alarm → lưu → UI → revoke/retry/quota. Không bật hết tính năng qua registry flag.
- Hoàn thiện GoodWe platform/consent và Deye application/customer grant theo tài khoản thật sẽ dùng.
- QA tài khoản chỉ đọc khi preflight/contract/scope/secrets sẵn sàng; đối chiếu với app hãng. Người dùng tự nhập trên giao diện, không gửi mật khẩu qua chat.
- Sau đó mới nghiệm thu control riêng theo model, không phát lệnh trong QA đăng nhập.

Chưa đủ bằng chứng nói kiến trúc đã production-ready hoặc đã tìm hết mọi lỗi. Audit này đủ để bác bỏ kết luận “chỉ thiếu tài khoản”; vẫn có engineering cụ thể cần hoàn thiện. UI có thể tiếp tục độc lập bằng empty/error/locked states trung thực.
