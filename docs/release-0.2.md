# Solar Fleet 0.2 — trạng thái pilot ngày 25/09/2026

[README dự án](../README.md) · [Mục lục](README.md) · [Bao phủ 26 mockup](mockup-coverage.md) · [Validation](validation.md)

## Tiếng Việt

Bản 0.2 hiện dùng một shell, **15 mục sidebar**, site scope và style global. Đây là mốc phát triển local controller, chưa phải release production đã nghiệm thu.

- Tám luồng đọc cloud: Deye, Solis, SOLARMAN, GoodWe Classic SEMS, Sungrow, Huawei, Growatt và Eybond/SmartESS. Mỗi adapter có contract/field/auth riêng; Bluesun chọn transport theo hệ thực, không giả định một API chung.
- Nhà máy/thiết bị/nguồn dùng dữ liệu được lưu và quyền theo site. Thời tiết Open-Meteo có khi có tọa độ; telemetry chưa xác minh không thành canonical KPI.
- Data → Mapping đã nối chọn field quan sát, unit/direction, edit/version, simulate và review độc lập. Review chưa cài profile hay bật điều khiển. Data workspace sở hữu một hàng tab, giữ alias route cũ.
- Điều khiển dùng cùng preview/diff/confirm, idempotency, khóa, order/readback và journal. Deye là compiler intent duy nhất hiện đăng ký; các compiler phỏng đoán ngoài Deye đã bị loại bỏ.
- TOU có nháp/version/compiler; bulk có assessment/canary/rollout được kiểm soát. EMS có dry-run và monitor-only, chưa autonomous hardware dispatch.
- Trung tâm cảnh báo nối correlation/dedup, phân công, ghi chú, timeline/SLA/playbook với phiếu bảo trì. Bảo trì có kế hoạch phiên bản, checklist, time entries và review độc lập.
- Báo cáo xuất artifact CSV/XLSX/HTML theo scope/kỳ. Quản trị có local RBAC, vault, API keys, session revoke và audit.
- Local Agent có enrollment/ingest/outbox và optional SOLARMAN V5 read collector; chưa phải service/driver suite/mTLS/OTA đầy đủ.

Đợt [25/09](mapping-validation-2026-09-25.md) ghi 450 BE pass, 13 browser pass trước QA sửa navigation và 8 ca rerun sau sửa, gồm một ca mới. Các lần chạy có trùng ca; không cộng thành 21 test duy nhất. Build/QA áp dụng snapshot và luồng được ghi trong báo cáo.

Chưa có live account/hardware acceptance của các adapter trong các đợt này. Native schemas và mapping theo model, EMS dispatch, scheduler thực, agent lifecycle, OTA/network writes, dữ liệu dài hạn, tenancy/MFA/SSO, đầy đủ chart/GIS/report delivery và QA đủ 26 ảnh vẫn còn thiếu. [Implementation status](implementation-status.md) và [bảng phạm vi](mockup-coverage.md) sở hữu chi tiết.

## English

The 0.2 pilot has eight cloud read paths of varying depth, a shared bilingual shell with fifteen sidebar destinations, connected mapping/review and incident-to-maintenance workflows, stored-data reports and a guarded command engine.

Connector code and synthetic tests do not establish complete vendor support or live hardware acceptance. Mapping review does not activate a canonical profile. The controller remains single-process with bounded SQLite retention. Native model schemas, accepted controls, autonomous EMS, agent lifecycle, production infrastructure and full reference-screen acceptance remain unfinished.
