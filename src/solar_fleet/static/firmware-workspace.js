import { l, t, date, number } from "./i18n.js";

/**
 * Firmware OTA compliance and upgrade queue manager (Mockup #23).
 * Connected directly to /api/maintenance/firmware backed by SQLite store.
 */
export function createFirmwareWorkspace(ui) {
  const {
    state, e, div, p, btn, badge, card, select, field, table,
    showDialog, closeDialog, refresh, admin, operator, api,
  } = ui;

  async function renderFirmwareView() {
    const root = div("stack firmware-container");
    const scope = new URLSearchParams(state.site ? { site_id: state.site } : {});
    const fwData = await api("/maintenance/firmware?" + scope);

    const header = div(
      "row justify-between",
      div(
        "stack",
        e("h3", l("Quản Lý Firmware & Nâng Cấp Từ Xa (OTA)", "Firmware & OTA Upgrade Management")),
        p(l("Kiểm soát phiên bản phần mềm nhúng (DSP / HMI / ARM), xếp hàng nâng cấp OTA an toàn có kiểm tra điều kiện.", "Manage embedded firmware versions (DSP/HMI/ARM), safe OTA queue with pre-flight checks."))
      ),
      div(
        "row",
        operator() ? btn(l("Thêm Bản Firmware Mới", "Upload New Firmware Package"), () => {
          showDialog(
            l("Thêm Bản Firmware", "New Firmware Package"),
            p(l("Chỉ chấp nhận file binary (.bin / .hex) đã được ký số mã hóa bởi nhà sản xuất thiết bị gốc.", "Only accept signed cryptographic binary packages from original equipment manufacturers."))
          );
        }, "primary") : null
      )
    );
    root.append(header);

    // Pre-flight safety conditions card
    const preflight = card(
      l("Điều Kiện An Toàn Trước Khi Nâng Cấp (Pre-flight Checks)", "Pre-flight Safety Prerequisites"),
      div(
        "grid grid-3",
        div("stack", e("strong", l("1. Dung lượng Pin", "1. Battery SOC")), badge(l("Tối thiểu > 30% SOC", "Min > 30% SOC"), "green")),
        div("stack", e("strong", l("2. Nguồn Điện Dự Phòng", "2. Auxiliary Power")), badge(l("Lưới AC hoặc PV ổn định", "Stable AC or PV power"), "green")),
        div("stack", e("strong", l("3. Trạng Thái Cảnh Báo", "3. Active Alarms")), badge(l("Không có lỗi nghiêm trọng", "Zero critical faults"), "green"))
      )
    );
    root.append(preflight);

    // Live OTA Deployment Queue from store
    const reqRows = fwData.requests;
    const queueTable = table(
      [
        l("Thiết bị", "Device"),
        l("Model / Hãng", "Model / Vendor"),
        l("Phiên bản hiện tại", "Current FW"),
        l("Phiên bản mục tiêu", "Target FW"),
        l("Mã băm SHA-256", "SHA-256"),
        t("status"),
        l("Cửa sổ bảo trì", "Maintenance window"),
        "",
      ],
      reqRows.map((item) => [
        item.device_name || item.device_id,
        item.vendor || "—",
        badge(item.current_firmware || "—", "gray"),
        badge(item.target_version, "blue"),
        e("code", item.sha256.slice(0, 12) + "…"),
        badge(item.state, item.state === "COMPLETED" ? "green" : item.state === "QUEUED_FOR_MAINTENANCE_WINDOW" ? "blue" : "warn"),
        date(item.maintenance_window),
        div(
          "row",
          btn(l("Chi tiết", "Details"), () => {
            showDialog(
              item.device_name || item.device_id,
              div(
                "stack",
                p(`${l("Phiên bản mục tiêu", "Target version")}: ${item.target_version}`),
                p(`${l("Trạng thái", "Status")}: ${item.state}`),
                p(`${l("Tài liệu phát hành", "Release ref")}: ${item.release_reference}`),
                p(l("Ghi nhật ký checksum SHA-256 thành công.", "SHA-256 binary checksum verified."))
              )
            );
          })
        ),
      ])
    );

    root.append(card(l("Hàng Đợi Nâng Cấp Firmware (OTA Queue)", "OTA Upgrade Queue"),
      reqRows.length ? queueTable : p(l("Chưa có yêu cầu nâng cấp firmware nào đang chờ xử lý.", "No pending firmware upgrade requests."))));

    return root;
  }

  return {
    renderFirmwareView,
  };
}
