# Implementation status — 0.1.0

Baseline được xác lập trong [Research & Architecture Report](research-architecture-report.md). Mục tiêu đợt triển khai này là foundational domain và Deye adapter, đúng thứ tự yêu cầu. Không đánh dấu hoàn thành hardware MVP khi các blocker từ hãng/thiết bị còn tồn tại.

| Mốc | Kết quả | Điều kiện tiếp theo |
|---|---|---|
| Research trước code | Hoàn thành baseline A–N, source audit, matrix, 34 intents, 10 ADRs; bổ sung E từ account web sau đó | Cập nhật có version khi nhận tài liệu mới |
| Domain, secret, RBAC, storage | Có code và kiểm thử | Review bảo mật/hardening môi trường production |
| Deye cloud read | Có transport thật, contract tests và ingestion tests | App/account/region thật; discovery/telemetry/history/alarm đối chiếu trên tài khoản |
| Monitoring UI | Có fleet, device, logger theo discovery, raw/history/config/alarm, provenance | Canonical metric profiles và timestamp acceptance theo model |
| Control engine | Có state machine, preview/confirm, idempotency, serialization, readback, audit | Exact commissioned profile + fresh getter + range + quyền + hardware test |
| Deye native | Giữ 39 endpoint schemas và 10 nhóm UI quan sát; write khóa | Bổ sung từng mapping hợp lệ; private web menu không được coi là API public |
| Quick/Advanced/TOU forms | Capability được hiển thị với lý do khóa; chưa có form ghi được bật | Tạo form theo typed constraint của profile đầu tiên, không mở generic raw editor |
| Reconciliation | Restart/in-flight → TIMEOUT; quarantine device, không resend | Operator reconciliation có readback mới, bằng chứng và audit; không tự clear |
| Site Agent / local | Kiến trúc, failure modes và coexistence trong report/ADRs; chưa có agent chạy | Protocol/register map hợp lệ, driver read-only, outbox dedupe/mTLS; thử cloud/local |
| Multi-vendor | Đã nghiên cứu có scope; chưa adapter nào ngoài Deye | Vendor access, contract/profile/test theo cùng DoD |
| Bulk/schedule/EMS | Chưa gửi bulk, chưa controller schedule/optimizer | Hoàn thành correctness/readback của single-device trước |

Các mục cố ý bị khóa vì thiếu bằng chứng là UNKNOWN, không phải silently unsupported. Các chức năng kỹ thuật chưa viết được liệt kê riêng ở bảng để tránh hiểu nhầm “đã có kiến trúc” thành “đã chạy”.

## Bước triển khai có thể review tiếp theo

1. Cấp Deye OpenAPI app và nhập credential bằng CLI. Đối chiếu discovery với web, không nhập snapshot web thành live telemetry.
2. Thu thập nhãn inverter/logger, exact firmware, protocol document, BMS và CT/meter topology. Lưu evidence gắn model/region/account.
3. Tạo metric profile đã đối chiếu đơn vị/dấu/timestamp cho PV, grid import/export, battery charge/discharge/SOC, load và daily energy.
4. Xác minh getter mới từ thiết bị. Nếu getter cache không chứng minh freshness thì không tiếp tục write.
5. Nghiệm thu một intent ít rủi ro với kỹ thuật viên tại công trình, rồi mở typed form, reconciliation và tolerance có bằng chứng. Test mất mạng/timeout/partial apply trên môi trường phù hợp.
6. Sau Deye single-device: Site Agent/local hoặc vendor thứ hai tùy tài liệu/quyền thực có sẵn. Chưa chạy closed-loop optimizer ở pha đầu.
