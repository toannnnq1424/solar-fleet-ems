# Energy-flow UI và kiểm tra trước bàn giao — 09/10/2026

## Scope và giới hạn

Nhánh `fix/real-data-engine-integration`, base HEAD `af4f1b8`, nhiều thay đổi tích lũy chưa commit. Người dùng đã cho phép báo cáo, commit/push rồi dừng. Không deploy, không command phần cứng, không seed production. Báo cáo này không chứng nhận tất cả thay đổi trong lịch sử hoặc các hãng đã được nghiệm thu.

Shared flow có ba mode (SVG phối cảnh 3D minh họa, vòng nút, thiết bị), geometry riêng, preference, neutral hub không cộng PV+abs(pin), chevron/pulse đúng dấu khi GOOD/fresh. Giá trị vendor-reported có thể hiển thị nhưng không giả clock/topology hay chuyển động. Shared card expansion và daily-chart crosshair/tooltip hỗ trợ chỉ số thật trong các chuỗi hiện có; chưa mọi widget.

Trước lượt báo cáo, live read đã thấy SolarOne đăng nhập và giá trị thật; fullscreen quá cao đã được phát hiện và sửa. Sizing cuối/SOC precision/snapshot note đã qua suite fixture dưới đây nhưng **chưa visual re-acceptance live sau patch**. Không tuyên bố user đồng ý đẹp: user nói UI vẫn chưa đạt.

## Consolidated verification thực sự chạy ở code cuối

Python môi trường `work/ui-venv`, fixture riêng, không dùng account/session/hardware thật trong automated tests.

| Lệnh | Kết quả |
|---|---|
| `work/ui-venv/bin/python -m pytest tests -q` | **1.894 passed, 13 warnings, 321,85s**, exit 0 |
| `work/ui-venv/bin/python -m pytest ui_tests -q` | **107 passed, 198,83s**, exit 0 |
| `work/ui-venv/bin/python -m ruff check .` | Passed |
| `node --check --input-type=module` từng static JS qua stdin | 63 modules passed (gồm generated module; inventory JS tự viết 62) |
| `work/ui-venv/bin/python -m build` | sdist + wheel built thành công |
| `git diff --check` | Passed trước staging; chạy lại staged trước commit |
| `work/ui-venv/bin/python scripts/measure_code.py --update-doc` | Inventory regenerated, không phải test |

Warnings: Starlette/httpx TestClient, anyio BlockingPortal alias, per-request cookies deprecations. Chưa xử lý nâng dependency trong lượt này. Test đạt không là pixel-perfect, full business coverage hoặc commissioning.

Vòng trước: full UI 105 đạt/2 fail vì test đếm hit-target rectangles như energy bars; sửa selectors `.energy-bar`, không bỏ assertion. Affected 18 đạt rồi thêm sizing/snapshot/SOC patch; full **107** ở trên là kết quả sau cùng, không cộng các lần rerun.

## Còn mở

- LIVE-01 ba chu kỳ đồng nhất snapshot/scope/revision và source timestamp/timezone; no sub-second promise.
- Fullscreen native hiện đóng băng snapshot có nhãn; fallback focus trap/refresh semantics cần tiếp tục. Chưa inventory phóng to mọi custom panel.
- E09.5–11: power/phases/MPPT/SOC-price history, complete periods, heatmap, Sankey/donut đúng phân bổ, comparison, quick-control. Không nội suy giả để phủ screenshot.
- Interface I0/I3–I6; UNKNOWN receipt overwrite; các hãng khác và control cần acceptance riêng.
- [Đánh giá sản phẩm](../project-assessment-2026-10-09.md), [12 ảnh riêng](ui-reference-manifest-2026-10-09.md), [runbook](../vendor-feature-backlog-2026-10-05.md#resume-checkpoint).

Chỉ tài liệu/manifest/inventory thay đổi sau test code; không có runtime fix mới sau suite cuối. Remote CI chưa được coi là đạt trước khi có kết quả thực tế.
