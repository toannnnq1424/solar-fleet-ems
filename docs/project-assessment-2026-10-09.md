# Đánh giá tiến độ SolarOne — 09/10/2026

## Kết luận

**Pilot đọc dữ liệu đang phát triển, chưa phải sản phẩm đa hãng hoàn thiện.** Người dùng xác nhận UI chưa đạt, nên không đóng nghiệm thu pixel/style. GoodWe đã đăng nhập qua SolarOne và đọc một phần số liệu trạm/thiết bị; chưa có hãng nào được nghiệm thu trọn chuỗi đọc, lịch sử, cấu hình, điều khiển và readback.

Ước lượng quản trị: **35–40% phạm vi SolarOne cốt lõi**, khoảng **30% nếu tính thêm Data Engineering và Applied AI**. Đây là đánh giá chủ quan theo các đầu ra cần nghiệm thu, độ tin cậy trung bình–thấp; không đo bằng LOC, số route, số test hay số lần đăng nhập. Không dùng tỷ lệ này suy thời gian/công sức còn lại. Phạm vi bao gồm backlog cốt lõi hiện tại; không bao gồm mọi tính năng tương lai của mọi nhà cung cấp như ERP/RMA/VPP đầy đủ.

## Cách ước lượng để các phiên sau không tự nâng phần trăm

Điểm từng nhóm là mức hoàn thiện tổng hợp **code + dữ liệu + workflow + nghiệm thu**, không phải tỷ lệ test coverage. Cho điểm phần khung đã hữu ích nhưng không cho đủ điểm khi còn thiếu acceptance. Trọng số là quy ước đề xuất ngày 09/10, không phải trọng số đã được chủ sản phẩm phê duyệt.

| Nhóm trong cốt lõi | Trọng số | Mức ước lượng | Bằng chứng / khoảng cách |
|---|---:|---:|---|
| UI/UX 26 màn, 15 owner | 15% | 45% | Có shell, editor, empty/locked states, nhiều route; người dùng chưa chấp nhận style, chart/flow/tooltip/fullscreen chưa đủ toàn bộ |
| GoodWe đọc end-to-end | 15% | 45% | Login/discovery, station và per-device reports thật; source clock, history/phases/MPPT, alarms, renew/soak/đối chiếu nhiều chu kỳ chưa hoàn tất |
| Tích hợp đọc các hãng khác | 15% | 15% | Có adapter, nghiên cứu, hướng dẫn keys và contract; chưa có nghiệm thu tài khoản thật từng ecosystem trong chương trình QA này |
| Interface chung và chất lượng dữ liệu | 15% | 40% | Registry/controller/optional reports đã nối; history/alarms/native extensions/profile/time semantics còn phân mảnh |
| Điều khiển, TOU, EMS | 15% | 25% | Command engine, guard, draft/calculator/compiler; chưa commissioning GoodWe, chưa loop read-config → preview → write → verified readback |
| Vận hành, network, báo cáo, phục hồi | 10% | 35% | Có workspaces/hợp đồng một phần; nhiều executor, notification/report lifecycle, backup/restore/soak chưa nghiệm thu đầy đủ |
| An toàn, kiểm thử, release | 15% | 55% | Có nhiều regression, scope/revision/quarantine; chưa full security/load/recovery/hardware acceptance hoặc release CI tại revision mới |

Tổng theo bảng: 37,25/100, **làm tròn thành dải 35–40%**, không báo 37,25% như độ chính xác đo được. Nếu mở rộng mẫu số: cốt lõi 80%, DE 10%, AI 10%; DE/AI chưa có implementation mới nên điểm triển khai hiện tại 0%, tổng xấp xỉ 30%. Kế hoạch đã viết không được tính là module đã làm.

## Các vấn đề phải nói rõ

1. **Đăng nhập ≠ hỗ trợ đầy đủ GoodWe.** Cần đối chiếu đúng trạm/serial, cùng kỳ/thời điểm/đơn vị/dấu. Số liệu trạm không được gán cho từng inverter. Chưa gọi các con số đã khớp hoàn toàn SEMS+.
2. **Near-real-time chưa được nghiệm thu hoàn chỉnh.** Client đọc receipt 15s, collector SEMS+ tối thiểu 60s không chứng minh vendor đo mỗi 15s/60s. Rotation/quota có thể chậm hơn. Source time chưa xác minh thì không gắn nhãn GOOD hay animation để tạo cảm giác realtime. Snapshot đồng nhất qua mọi vùng và tối thiểu ba chu kỳ live vẫn cần chốt.
3. **UI chưa đạt yêu cầu người dùng.** Ba chế độ flow và SVG phối cảnh đã có code, không phải 3D sản phẩm chính xác/photorealistic. Fullscreen còn có snapshot freeze; tooltip hiện mở rộng cho daily chart/flow, chưa mọi biểu đồ. Power history/phases/SOC-price, heatmap, Sankey/donuts và comparison chưa đủ giống ảnh.
4. **Một số màn chưa lên dữ liệu là thiếu engineering, không chỉ thiếu tài khoản.** Endpoint/vendor contract → normalized store → workspace chưa đủ; trạng thái rỗng trung thực là cần nhưng không thay cho tính năng đã nối.
5. **Interface chung chưa chỉn chu.** Registry nhiều hãng mới discovery/latest, `decode_alarm`/profile/compiler hooks còn thiếu. GoodWe reports đã cải thiện I1/I2 nhưng I0/I3–I6 chưa đóng. Giữ extension riêng khi không có semantics chung, không bật flags để giả support.
6. **Facade trùng còn rủi ro:** kiểm lại `UnifiedCloudAdapter.get_telemetry` vẫn lấy row đầu và trả thời gian hiện tại/MEASURED/online=True. Audit trước chưa tìm thấy controller chính gọi facade này; không quy kết nó đang làm sai dashboard. Cần quarantine/dọn hoặc nối đúng decoder trước dùng (IA-03).
7. **Lưu lịch sử chưa đáp ứng warehouse.** `Store.add_samples` vẫn upsert theo source timestamp, thiếu timestamp dùng `UNKNOWN`, do đó không giữ mọi lần nhận/thay đổi. Correction cùng timestamp cũng ghi đè. DE-00 cần archive bounded trước đợt thu dài hạn; không lưu bản ghi mỗi frame/millisecond UI.
8. **Điều khiển chưa được nghiệm thu:** nút có mặt/đã đăng nhập/fixture pass không cho phép mở khóa. GoodWe mode, AC-port, backup/cold start, remote dispatch vẫn cần schema, scope, exact model, range và readback; khóa ghi thật giữ nguyên.
9. **EMS cần rà provenance đầu vào:** kiểm nguồn `ems_optimizer.py` thấy nhánh fallback SOC chấp nhận `source_timestamp or received_at` và tra history; kiểm tuổi ở đây chưa chứng minh quality, clock và battery identity đúng. Đây là rủi ro cần reproducer/negative tests, chưa kết luận có phát lệnh sai ngoài thực tế. Không gọi calculator/advisory là dispatch an toàn đã nghiệm thu (ASSESS-EMS-01).
10. **Khoảng cách vận hành/release:** chưa chứng minh long-running renewal/reconnect/quota, disk-full/backpressure, migration/restore và load toàn phạm vi. GitHub push/test xanh không phải deploy, chứng nhận security hoặc nghiệm thu phần cứng.

## Ảnh mới và thứ tự thực hiện khi được tiếp tục

[Manifest 12 ảnh ngày 09/10](evidence/ui-reference-manifest-2026-10-09.md); ảnh riêng không vào Git. Ảnh cuối bổ sung quick-control: công tắc tổng, slider hai đầu, ngày lặp, giới hạn điện mua và lưu; không suy nó là API chung hoặc GoodWe đã được cấp quyền ghi.

1. Checkpoint hội thoại trước; recovery Git/process/session, giữ một controller read-only.
2. Đóng UI-ENERGY-09.1–4: QA ba kiểu flow/card hẹp/mobile/fullscreen bằng dữ liệu thật; xử lý snapshot freeze/fallback focus; user nghiệm thu style. Không thêm dữ liệu giả.
3. LIVE-01/GW-01: chứng minh cùng snapshot/revision ở mọi panel, 3 chu kỳ, dấu/unit/timezone đúng; manual refresh/cooldown/reconnect không vượt quota.
4. I0 + I2/I3: xử lý facade song song và provenance; bổ sung history/alarm qua interface khả thi; ASSESS-EMS-01 reproducer và fix trước dùng đầu vào đó cho vận hành.
5. DE-00: append receipt/change bounded, dedup, byte/count budget, retention/rollup có thử khôi phục; không chạy retention xóa thật hoặc xuất cloud khi chưa được phép.
6. E09.5–11 và 26 màn: nối từng nguồn thật rồi chart/heatmap/comparison; quick control chỉ draft/read trước. Kiểm mouse/keyboard/touch/empty/error/stale và phóng to từng vùng.
7. QA Deye và từng hãng theo account/region/profile; research/mapping độc lập vẫn làm khi thiếu keys. Control thử riêng cần người dùng xác nhận tác động và exact target.
8. DE/AI theo runbook; AI/Text-to-SQL read-only trên semantic layer, có provenance/freshness/giới hạn; không tự điều khiển.

Chi tiết thao tác, dependencies và cổng nghiệm thu tiếp tục nằm ở [vendor backlog](vendor-feature-backlog-2026-10-05.md#resume-checkpoint). Không mở một kế hoạch cạnh tranh.

## Trạng thái đóng phiên

User yêu cầu: báo cáo → commit/push GitHub → dừng chờ lệnh. Consolidated checks, review dữ liệu nhạy cảm và kết quả Git được cập nhật trong checkpoint/evidence cuối phiên. Không dùng kết quả các phiên cũ để khai đã pass revision mới.
