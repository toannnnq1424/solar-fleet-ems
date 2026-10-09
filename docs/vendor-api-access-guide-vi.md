# Xin quyền kết nối các hãng với SolarOne

Đối chiếu nguồn công khai và code ngày **04/10/2026**. Đây là hướng dẫn chuẩn bị quyền truy cập, không phải chứng nhận các connector đã dùng được với tài khoản thật.

## Bạn nên làm gì trước?

Không phải hãng nào cũng yêu cầu App ID/App Secret. Không cần xin tất cả các hãng cùng lúc. Với tài khoản đang có, ưu tiên Deye và xác định chính xác ứng dụng GoodWe; các hãng khác chỉ chuẩn bị khi thực sự có thiết bị cần kết nối.

| Hãng / nền tảng | Thông tin mà form hiện tại nhận | Hướng dẫn |
|---|---|---|
| Deye Cloud | Quản trị viên cài khóa ứng dụng; người dùng đi qua email/mật khẩu | [Deye](deye-developer-setup-vi.md) |
| SolisCloud | Key ID / Key Secret của tài khoản | [Solis: phân biệt khóa cá nhân và ứng dụng nhiều khách hàng](solis-developer-setup-vi.md) |
| SOLARMAN | App ID / App Secret, tài khoản, mật khẩu, vùng máy chủ | [SOLARMAN](solarman-developer-setup-vi.md) |
| Sungrow / iSolarCloud | App Key / App Secret, tài khoản, mật khẩu, ID nhà máy/điểm đo | [Sungrow](sungrow-developer-setup-vi.md) |
| GoodWe | Connector cũ: email/mật khẩu + ID nhà máy, không có trường App ID | [GoodWe và chuyển đổi SEMS+](goodwe-developer-setup-vi.md) |
| Huawei / FusionSolar | Tên tài khoản Northbound / System Code | [Huawei](huawei-developer-setup-vi.md) |
| Growatt | API token và vùng máy chủ | [Growatt](growatt-developer-setup-vi.md) |
| Eybond / SmartESS; thiết bị OEM như Bluesun | Tùy nền tảng/logger; không suy từ logo inverter | [Eybond và Bluesun](eybond-bluesun-developer-setup-vi.md) |

Các trường trên được đối chiếu `src/solar_fleet/providers.py`, adapter và UI; **form có trường không có nghĩa luồng đã nghiệm thu**. Khóa OAuth, token và khóa ký HMAC không thay thế lẫn nhau.

## Một email mới, chưa có nhà máy, có dùng làm tài khoản phát triển không?

Đây là mô hình nên đề nghị hãng xét duyệt cho SolarOne: tài khoản ứng dụng tách khỏi tài khoản chủ nhà máy. Nhưng được cấp khóa ứng dụng **không tự cấp quyền đọc nhà máy của khách hàng**. Cần hãng xác nhận cơ chế chủ nhà máy đồng ý, phạm vi dữ liệu và thu hồi quyền. Không áp dụng câu trả lời của một hãng cho tất cả hãng.

Không chuyển quyền sở hữu, xóa nhà máy, thêm thiết bị giả, dùng serial của người khác hoặc khai mình là nhà lắp đặt nếu không đúng. Không gửi mật khẩu/secret trong chat, Git, ảnh QA hay biểu mẫu không rõ nguồn. Mật khẩu cần dùng là mật khẩu tài khoản hãng; địa chỉ Gmail không có nghĩa dùng mật khẩu Google.

## Hồ sơ đề nghị chuẩn bị

Đây là checklist do dự án đề xuất, không phải tất cả đều là trường bắt buộc của hãng:

1. Email liên hệ chuyên dùng; tên cá nhân/tổ chức và vai trò đúng thực tế.
2. Tên ứng dụng SolarOne; mô tả quản lý nhiều hãng, giai đoạn thử nghiệm chỉ đọc.
3. Quốc gia, máy chủ nơi tài khoản/nhà máy đang tồn tại; số nhà máy và tần suất đọc dự kiến thực tế.
4. Website nếu đã có; nếu chưa, ghi đang phát triển nội bộ, không khai URL triển khai giả.
5. Hỏi cơ chế ủy quyền từng khách hàng, hết hạn/thu hồi, hạn mức và chi phí.
6. Callback HTTPS và IP ra ngoài chỉ cung cấp sau khi phía kỹ thuật chốt. Không tự lấy localhost hoặc IP Wi-Fi làm cấu hình production.

## Mẫu thư hỏi quyền — tự điền và tự gửi

```text
Subject: Request for read-only API access and customer authorization — SolarOne

Hello [vendor] API team,

I am [name], acting as [actual role / organization], in [country].
We are developing SolarOne, a multi-vendor solar monitoring application.
The initial pilot is read-only: authorized plants, devices and measurements.
We are not requesting remote control or firmware update permissions.

Developer contact email: [email]
Monitoring platform and region: [actual app name / server]
Website or development status: [actual information]
Expected pilot scope and polling frequency: [actual estimate]

Please advise:
1. Can a developer account without plants register this application?
2. How does each plant owner authorize and revoke access independently?
3. Which API product, credentials and regional endpoints should we use?
4. What documents, quotas, fees and security requirements apply?
5. Is there a sandbox or a restricted read-only pilot option?

Please send the current application procedure and API documentation.
Please do not send customer passwords. We will review contractual terms
before accepting them and use your approved secure credential channel.

Regards,
[name]
```

Không tự gửi câu “đã đọc và đồng ý mọi điều khoản” khi chưa thực sự đọc/chấp nhận. Agent chưa đăng ký tài khoản, gửi đơn hay ký thỏa thuận thay bạn.

## Khi hãng trả lời

Bạn chỉ cần báo hãng, tên loại API, trạng thái duyệt, vùng máy chủ và yêu cầu bổ sung; không dán khóa. Cấu hình khóa qua nơi lưu bí mật dành cho quản trị viên sau khi xác nhận connector tương thích.

Trình tự QA: xác nhận đúng nền tảng → kiểm tra đăng nhập chỉ đọc → kiểm danh sách nhà máy được phép → kiểm phạm vi đồng bộ → so tên/SN/thời gian/đơn vị/số đo với app hãng → thử hết hạn/thu hồi. Không bật EMS, lịch tự động hoặc gửi lệnh thiết bị trong lượt đầu.

**Hiện chưa mời nhập tài khoản thật:** Deye thiếu khóa ứng dụng; GoodWe còn cần xác minh nền tảng và cập nhật/kiểm chứng đường kết nối phù hợp. Đây không chỉ là việc thiếu dữ liệu để tô giao diện.
