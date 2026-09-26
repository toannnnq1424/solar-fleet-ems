# Thư viện model, collector và Home Assistant

[README](../README.md) · [Nguồn dự án cũ](legacy-project-audit.md) · [Kiểm thử](legacy-validation-2026-09-27.md) · [Hardware acceptance](hardware-acceptance.md)

## Luồng dùng chung

**Thiết bị → Modbus Register Inspector** mở catalogue model; từ tổng quan nhà máy cũng đi tới cùng workspace. Tìm model, đọc source/license/commit, chọn field đọc được rồi xem kế hoạch hoặc giải mã dữ liệu đã thu. Kế hoạch/giải mã trên UI là offline, không mở socket tới thiết bị. Các trường chưa hỗ trợ có lý do cụ thể.

Nút chuẩn bị cấu hình model hoặc Home Assistant tạo JSON để kiểm tra và tải về. Config chỉ hợp lệ khi agent tồn tại, được bật và các device thuộc agent/site mà người dùng có quyền. Kết quả CONFIG_VALID xác nhận cấu trúc/membership, **không xác nhận kết nối**. Config mẫu ban đầu có chỗ cần điền, không phải cấu hình thiết bị thật.

Cầu dữ liệu giữ nguyên đường đi:
collector → SQLite outbox → agent inbox có sequence → native observations → Dữ liệu / Mapping → review độc lập → commissioning riêng.
Native data vẫn UNVERIFIED; duyệt mapping draft chưa tự kích hoạt canonical profile. Người dùng có thể xem native readings trước khi có profile chuẩn hóa được nghiệm thu.

## Collector model

Model catalogue ghim digest và nguồn. Xác định chính xác inverter model/firmware, logger model/firmware, transport, IP, port, unit ID và các field đã đối chiếu. Chỉ nhận IPv4 RFC1918 cụ thể. Không tự scan hoặc thử protocol khác khi lỗi. SOLARMAN V5 và Modbus TCP là hai transport khác nhau dù đôi khi dùng cùng số cổng.

- Modbus TCP FC03/FC04 dùng standard library, kiểm tra transaction/unit/protocol/function/byte count, nhận frame phân mảnh.
- SOLARMAN V5 cần extra `local-solarman`, dependency `pysolarmanv5==3.0.6`; phải điền logger serial.
- Field identity ASCII dùng inspector offline; collector measurements chỉ nhận số.
- Mỗi plan tối đa 100 field, 1.000 register, 64 block, không gộp qua register chưa khai báo; poll có ngân sách tối đa 120 giây.
- Không có FC ghi, RTU, tự cập nhật thời gian, cấu hình mạng hoặc firmware.
- Poll lỗi không enqueue kết quả từng phần, không tự gửi lại lệnh vật lý.

Trên máy agent, sau khi lưu config đã kiểm tra thành `model-collector.json`:

```powershell
.\.venv\Scripts\python.exe -m pip install -c constraints.txt -e ".[local-solarman]"
.\.venv\Scripts\python.exe -m solar_fleet.agent --spool data/agent-outbox.sqlite collect-model --profile model-collector.json
.\.venv\Scripts\python.exe -m solar_fleet.agent --spool data/agent-outbox.sqlite flush --controller https://controller.example
```

`SOLAR_AGENT_TOKEN` phải được cấp từ enrollment và nạp qua môi trường/bộ quản lý bí mật. Không nhập token vào JSON profile hoặc commit spool. URL trên là placeholder, thay bằng controller thực. Đây là lệnh một lần; chưa có service installer hoặc scheduler polling production.

## Home Assistant sensor bridge

Dùng một HA server trong mạng riêng, không cần nhập nguyên integration vào controller. REST client chỉ GET `/api/states/{entity_id}`; không POST service, không thay state hay automation HA. Nguồn API: [Home Assistant REST](https://developers.home-assistant.io/docs/api/rest/).

Config minh họa, **phải thay agent/device/entity bằng ID đã quan sát**:

```json
{
  "agent_id": "AGENT_ID",
  "base_url": "http://192.168.1.10:8123",
  "bindings": [
    {"entity_id": "sensor.house_load", "device_id": "DEVICE_ID", "expected_unit": "W"}
  ],
  "reviewed_by": "REVIEWER",
  "evidence_reference": "REVIEW_RECORD",
  "max_age_seconds": 300
}
```

`base_url` chỉ nhận private IPv4 origin không credentials/path/query; không follow redirect hoặc environment proxy. `SOLAR_HA_TOKEN` là token HA được người quản trị cấp, nạp qua môi trường. Profile không giữ token.

```powershell
.\.venv\Scripts\python.exe -m solar_fleet.agent --spool data/agent-outbox.sqlite collect-home-assistant --profile home-assistant.json
.\.venv\Scripts\python.exe -m solar_fleet.agent --spool data/agent-outbox.sqlite flush --controller https://controller.example
```

Kiểm tra đúng entity ID, expected unit, timestamp có timezone và độ mới. Ưu tiên `last_reported`, fallback `last_updated` trên HA cũ; số đo không đổi có timestamp cũ có thể bị từ chối bảo thủ. State unknown/unavailable giữ null, không chuyển thành 0. Đơn vị đổi hoặc timestamp tương lai/quá cũ làm poll thất bại để người dùng review binding.

Sensor từ SEM/EMHASS hoặc các integration hãng có thể đi cùng pipeline nếu thỏa contract này. Việc đọc sensor dự báo không tự coi là số đo canonical thực tế hoặc cấp quyền điều khiển.

## Dự báo cơ sở trong EMS

**Điều phối EMS → Quy tắc** có thẻ tính baseline 24 giờ cho thiết bị được chọn. API `GET /api/devices/{id}/forecast-baseline` dùng lịch sử đã lưu, không gọi dịch vụ bên ngoài.

Chỉ dùng GOOD canonical PV/load theo một binding đã xác minh, bảy ngày gần nhất; cần tối thiểu ba ngày thực tế, 24 giờ đủ mẫu, mỗi giờ ít nhất ba mốc 15 phút, dữ liệu mới trong ba giờ. Hai giá trị khác nhau cùng timestamp hoặc nhiều nguồn không rõ ràng bị từ chối. Lịch sử bị cắt bởi giới hạn đọc cũng không trả forecast có vẻ đầy đủ.

Thuật toán EWMA weekday/hour adapt từ SEM, fallback cùng giờ; thiếu dữ liệu trả trạng thái cold/insufficient kèm lý do. Đây là đường cơ sở tham khảo, không có chứng nhận độ chính xác, không tính ROI, không lập lịch hoặc phát lệnh. Tối ưu TOU/forecast dispatch còn phải xây.

## Sơ đồ năng lượng chung

Tổng quan nhà máy và giám sát thiết bị dùng cùng component, màu/spacing/button từ `app.css`. Motion thể hiện PV, nhập/xuất lưới, sạc/xả pin, tải, EPS và máy phát nếu có số đo. Net grid/battery chỉ tính khi hai chiều cùng thiết bị/binding/source và timestamp lệch không quá 5 giây. Số thiếu, cũ, nhập nhằng hoặc chưa xác minh không được tạo thành công suất 0.

Có chế độ bảng, toàn màn hình, dừng chuyển động, hỗ trợ reduced-motion và mobile. Khi sample hết hạn, motion dừng ngay cả khi chưa nhận refresh. Các node dẫn tới route chi tiết. Đường nối không chứng minh topology dây điện, EPS readiness hoặc phân bổ nguồn nào cấp riêng cho tải nào.

## Tái tạo catalogue

Chỉ cần PyYAML khi import offline; runtime không execute YAML/Jinja:

```powershell
.\.venv\Scripts\python.exe -m pip install -c constraints.txt -e ".[profile-import]"
.\.venv\Scripts\python.exe scripts/import_model_library.py --root D:\Downloads\before_project
```

Importer kiểm tra file hash trong [source lock](../src/solar_fleet/data/model-source-lock.json). Nguồn thay đổi phải được nghiên cứu/ghim lại; không bỏ hash guard để ép import. [Catalogue](../src/solar_fleet/data/model-library.json) chứa cả decoder và field bị chặn. Xem [notices/license](../THIRD_PARTY_NOTICES.md).
