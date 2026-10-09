# Manifest ảnh UI người dùng — 09/10/2026

Đã lưu **12/12 ảnh được gửi ngày 09/10 trong ngữ cảnh hiện có**, đối chiếu bản sao nguyên byte và SHA-256. Không tự gom những screenshot khác cùng ngày mà người dùng chưa gửi.

Kho riêng trên máy người dùng: `Documents/SolarOne-private-reference/2026-10-09/INDEX.md` (ngoài Git). Mở INDEX để xem bộ ảnh. Các file gốc vẫn được giữ nguyên. Ảnh không được đẩy GitHub hoặc đóng gói; bản sao cần được mang theo riêng nếu chuyển máy. Repository chỉ lưu tên trung tính, hash và yêu cầu thiết kế. Nếu kho riêng không còn, yêu cầu người dùng gắn lại; không suy ảnh từ tên.

| File riêng | Mục học / đối chiếu | SHA-256 |
|---|---|---|
| reference-2026-10-09-09-08-29.png | Phối cảnh 3D và chiều dòng điện | `b87af014cb8cba162c463c94c2f6882e2b3ab5a2e0dd156eb685f31ab201ec11` |
| reference-2026-10-09-09-08-35.png | Sơ đồ vòng nút | `c948b20c397e0dd03d43b4e87e26e326b36eb9c32977ff59607b3a97967018bf` |
| reference-2026-10-09-09-12-46.png | Sơ đồ thiết bị, nhánh UPS riêng | `db3f529f2690a6a870ce47c8a4cc78c8dd19e7664c45e1ff7b863c759318cdde` |
| reference-2026-10-09-09-26-47.png | Đường công suất, SOC/giá và Sankey | `5dc8002da64c4e6896b95ed05e317a0913bd1405e6345b0a849384acd87f4477` |
| reference-2026-10-09-09-27-32.png | Phân pha và donut phân bổ năng lượng | `c237152d0a40252c83082a809a14dfb42fbda7f8ca7ab36a92af2c38a98f8a96` |
| reference-2026-10-09-09-27-40.png | Điện năng theo tuần, nhiều chuỗi | `76c5118f7e92223a6a190aeb0f09dd770dd62c50c54b5c6ec4ff2e3f05c8ed70` |
| reference-2026-10-09-09-27-52.png | Calendar heatmap | `5edb1dbe9ef00afe5ea8fd152a9d94f1f0f5128ce779bcc64cfd1c8f5bf5c422` |
| reference-2026-10-09-09-28-02.png | Bảng so sánh, thời điểm và nhóm chỉ số | `aff774aef0413480aaf20a701fee6d6329bec84d88725a93703f401ece48919d` |
| reference-2026-10-09-09-33-02.png | Hover nhiều chuỗi theo ngày, crosshair | `dea7019ba0fe56a6e2423a024edafb34c1f64f9ee74c0511d538fe204ba1c0d2` |
| reference-2026-10-09-09-33-09.png | Tooltip heatmap | `59d4e984994247bc7610f20675c792800707bc0179e0bc38ad4ee028cf025ef9` |
| reference-2026-10-09-09-33-21.png | Tooltip đồng bộ công suất, pha, SOC, giá | `28112655d3fae7940da65a2270497460ca11676c1893e86f1d744ef142e12a1a` |
| reference-2026-10-09-09-53-05.png | Điều khiển nhanh: khoảng giờ, giới hạn điện mua, ngày lặp | `ac2652a87a062ea0ab6d9606a44817b6d9cd08e1c9ead480b0bf70bd3efc1745` |

Không sao chép số liệu trong ảnh vào telemetry, không suy API/quyền ghi từ menu. Ba kiểu flow dùng chung snapshot có provenance; nguồn chưa xác minh thì không vẽ chuyển động giả. Mỗi biểu đồ cần phóng to, tooltip/focus/touch và states rỗng/lỗi/stale; hình thức đẹp không được che thiếu dữ liệu.
