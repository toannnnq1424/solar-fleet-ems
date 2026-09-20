export let language =
  localStorage.getItem("solar-fleet-language") === "en" ? "en" : "vi";
export const l = (vi, en) => (language === "vi" ? vi : en);
export function setLanguage(value) {
  language = value === "en" ? "en" : "vi";
  localStorage.setItem("solar-fleet-language", language);
  document.documentElement.lang = language;
}
export const number = (value, digits = 2) =>
  value == null
    ? "—"
    : new Intl.NumberFormat(language === "vi" ? "vi-VN" : "en-GB", {
        maximumFractionDigits: digits,
      }).format(value);
export const date = (value) =>
  !value || Number.isNaN(+new Date(value))
    ? "—"
    : new Intl.DateTimeFormat(language === "vi" ? "vi-VN" : "en-GB", {
        dateStyle: "short",
        timeStyle: "short",
      }).format(new Date(value));
export const words = {
  overview: ["Tổng quan", "Overview"],
  plants: ["Nhà máy", "Plants"],
  devices: ["Thiết bị", "Devices"],
  operations: ["Vận hành", "Operations"],
  incidents: ["Sự cố & bảo trì", "Incidents & maintenance"],
  reports: ["Dữ liệu & báo cáo", "Data & reports"],
  settings: ["Cài đặt", "Settings"],
  all: ["Tất cả nhà máy", "All plants"],
  name: ["Tên", "Name"],
  vendor: ["Hãng / nền tảng", "Vendor / platform"],
  status: ["Trạng thái", "Status"],
  source: ["Nguồn dữ liệu", "Data source"],
  customer: ["Khách hàng", "Customer"],
  address: ["Địa chỉ", "Address"],
  timezone: ["Múi giờ", "Timezone"],
  capacity: ["Công suất lắp đặt (kWp)", "Installed capacity (kWp)"],
  latitude: ["Vĩ độ", "Latitude"],
  longitude: ["Kinh độ", "Longitude"],
  save: ["Lưu", "Save"],
  cancel: ["Hủy", "Cancel"],
  search: ["Tìm theo tên, hãng, số serial…", "Search name, vendor, serial…"],
  details: ["Xem chi tiết", "View details"],
  noData: ["Chưa có dữ liệu", "No data yet"],
  lastSeen: ["Dữ liệu gần nhất", "Last measurement"],
  online: ["Đang kết nối", "Connected"],
  offline: ["Mất kết nối", "Disconnected"],
  stale: ["Dữ liệu cũ / chưa rõ thời gian", "Old data / time unverified"],
  open: ["Mới ghi nhận", "Open"],
  acknowledged: ["Đã tiếp nhận", "Acknowledged"],
  in_progress: ["Đang xử lý", "In progress"],
  resolved: ["Đã xử lý", "Resolved"],
  closed: ["Đã đóng", "Closed"],
  critical: ["Nghiêm trọng", "Critical"],
  high: ["Cao", "High"],
  medium: ["Trung bình", "Medium"],
  low: ["Thấp", "Low"],
  severity: ["Mức độ", "Severity"],
  title: ["Tiêu đề", "Title"],
  description: ["Mô tả", "Description"],
  note: ["Ghi chú xử lý", "Resolution note"],
  assignee: ["Người phụ trách", "Assigned to"],
  dueDate: ["Hạn hoàn thành", "Due date"],
  unassigned: ["Chưa phân công", "Unassigned"],
  incident: ["Sự cố", "Incident"],
  work_order: ["Phiếu bảo trì", "Work order"],
  schedule: ["Lịch nháp", "Schedule draft"],
  DRAFT: ["Bản nháp · chưa thực thi", "Draft · not executing"],
  UNKNOWN: ["Chưa xác minh", "Unverified"],
  VERIFIED: ["Đã xác minh", "Verified"],
  UNSUPPORTED: ["Không hỗ trợ", "Unsupported"],
  CREATED: ["Đã tạo", "Created"],
  VALIDATING: ["Đang kiểm tra", "Validating"],
  READY: ["Sẵn sàng", "Ready"],
  SENDING: ["Đang gửi", "Sending"],
  ACCEPTED: ["Hãng đã nhận", "Vendor accepted"],
  WAITING_DEVICE: ["Chờ thiết bị", "Waiting for device"],
  VERIFYING: ["Đang đọc lại", "Verifying"],
  FAILED: ["Thất bại", "Failed"],
  TIMEOUT: ["Chưa rõ kết quả", "Outcome unknown"],
  CANCELLED: ["Đã hủy", "Cancelled"],
  CONNECTING: ["Đang kết nối", "Connecting"],
  CONNECTED: ["Kết nối thành công", "Connected"],
  ERROR: ["Cần kiểm tra", "Needs attention"],
  PILOT_CAPACITY_EXCEEDED: ["Thu thập luân phiên", "Rotating collection"],
  self_use: ["Tự tiêu thụ", "Self consumption"],
  charge: ["Sạc pin", "Charge"],
  discharge: ["Xả pin", "Discharge"],
  hold: ["Giữ pin", "Hold"],
  Viewer: ["Người xem", "Viewer"],
  Operator: ["Vận hành viên", "Operator"],
  Installer: ["Kỹ thuật viên", "Installer"],
  "Senior Engineer": ["Kỹ sư phụ trách", "Senior engineer"],
  Administrator: ["Quản trị viên", "Administrator"],
  GOOD: ["Đã chuẩn hóa", "Normalized"],
  UNVERIFIED: ["Dữ liệu gốc chưa đối chiếu", "Native data, not commissioned"],
  INVALID: ["Không hợp lệ", "Invalid"],
  MISSING: ["Chưa có", "Missing"],
  VENDOR_CLOUD: ["Cloud của hãng", "Vendor cloud"],
  LOCAL: ["Tại chỗ", "Local"],
  SITE_AGENT: ["Gateway tại site", "Site gateway"],
  MANUAL: ["Khai báo thủ công", "Manually entered"],
  pending: ["Chưa kiểm tra", "Pending"],
  pass: ["Đạt (ghi nhận)", "Pass (recorded)"],
  warning: ["Cần xem xét", "Warning"],
  fail: ["Chưa đạt", "Fail"],
  topology: ["Sơ đồ thiết bị", "Device topology"],
  meter_ct: ["Công tơ / CT", "Meter / CT"],
  power_direction: ["Chiều công suất", "Power direction"],
  battery: ["Pin / BMS", "Battery / BMS"],
  control_readback: ["Điều khiển & đọc lại", "Control & readback"],
  alarms: ["Cảnh báo thiết bị", "Device alarms"],
  key_id: ["API Key ID", "API Key ID"],
  key_secret: ["API Key Secret", "API Key Secret"],
  app_id: ["App ID", "App ID"],
  app_secret: ["App Secret", "App Secret"],
  identity_value: ["Email / tên tài khoản hãng", "Vendor email / username"],
  password: ["Mật khẩu", "Password"],
  SET_WORK_MODE: ["Chế độ vận hành", "Operating mode"],
  SET_ZERO_EXPORT: ["Không phát lưới", "Zero export"],
  SET_EXPORT_LIMIT: ["Giới hạn phát lưới", "Export limit"],
  SET_RESERVE_SOC: ["Pin dự phòng (SOC)", "Reserve SOC"],
  SET_TOU: ["Lịch sạc / xả", "Charge / discharge schedule"],
  ENABLE_GRID_CHARGE: ["Cho phép sạc lưới", "Enable grid charge"],
  SET_BACKUP_EPS: ["Nguồn dự phòng EPS", "EPS backup"],
  SET_SELF_CONSUMPTION: ["Ưu tiên tự dùng", "Prioritize self use"],
};
export const t = (key) => (words[key] ? l(...words[key]) : key);
const errors = {
  maintenance_execution_incomplete: ["Cần hoàn tất checklist, bằng chứng và ghi thời gian trước khi hoàn tất phiếu.", "Complete the checklist, evidence and work time before resolving the order."],
  maintenance_review_required: ["Cần một kỹ thuật viên khác duyệt kết quả công việc.", "Another technician must approve the work results."],
  maintenance_independent_reviewer_required: ["Người thực hiện không được tự duyệt công việc của mình.", "Work contributors cannot approve their own work."],
  maintenance_execution_changed: ["Bằng chứng đã thay đổi sau khi duyệt. Cần gửi kiểm tra lại.", "Evidence changed after approval. Submit for review again."],
  maintenance_reviewer_no_longer_authorized: ["Người duyệt không còn quyền tại nhà máy. Cần kiểm tra lại.", "The reviewer no longer has access to this plant. A new review is required."],
  maintenance_team_member_not_authorized: ["Thành viên nhóm chưa có quyền thực hiện tại nhà máy này.", "A team member does not have access to work at this plant."],
  maintenance_evidence_not_available: ["Tài liệu đã bị lưu trữ hoặc không thuộc nhà máy này.", "The evidence document was archived or belongs to another plant."],
  maintenance_technical_role_required: ["Chức năng này dành cho kỹ thuật viên hoặc kỹ sư phụ trách.", "This action requires an installer or senior engineer."],
  maintenance_not_awaiting_review: ["Phiếu chưa ở bước chờ kiểm tra. Tải lại để xem trạng thái mới.", "This order is not awaiting review. Reload its current state."],
  maintenance_step_not_found: ["Checklist đã thay đổi. Tải lại trước khi ghi kết quả.", "The checklist changed. Reload before recording a result."],
  maintenance_calendar_range_invalid: ["Chọn khoảng lịch lớn hơn 0 và tối đa 93 ngày.", "Choose a calendar range of more than zero and at most 93 days."],
  work_time_overlap: ["Khoảng thời gian bị trùng với ghi nhận khác của bạn.", "This time overlaps another entry recorded by you."],
  work_time_in_future: ["Chỉ ghi thời gian công việc đã thực hiện.", "Record only work that has already been performed."],
  work_time_entry_not_editable: ["Chỉ người ghi thời gian mới có thể hủy ghi nhận của mình.", "Only the entry author can void their active time entry."],
  work_order_completed_reopen_first: ["Phiếu đã hoàn tất. Mở lại phiếu trước khi bổ sung kết quả.", "This order is completed. Reopen it before changing execution evidence."],
  invalid_credentials: [
    "Tài khoản hoặc mật khẩu chưa đúng.",
    "Incorrect username or password.",
  ],
  request_validation_failed: [
    "Kiểm tra lại các trường, khoảng thời gian và múi giờ.",
    "Check the fields, time range and timezone.",
  ],
  vendor_auth_or_permission_denied: [
    "Hãng từ chối xác thực. Kiểm tra tài khoản, khóa API và vùng dữ liệu.",
    "Vendor authentication denied. Check credentials, API access and region.",
  ],
  local_rate_budget_exhausted: [
    "Đã tới ngân sách API. Thử lại sau một phút.",
    "Local API budget reached. Retry in one minute.",
  ],
  poll_cooldown: [
    "Vừa đồng bộ. Đợi ít nhất 15 giây.",
    "Recently synced. Wait at least 15 seconds.",
  ],
  poll_already_running: [
    "Đang đồng bộ dữ liệu. Vui lòng đợi.",
    "A sync is already running. Please wait.",
  ],
  record_changed_reload: [
    "Bản ghi vừa thay đổi. Tải lại trước khi lưu.",
    "This record changed. Reload before saving.",
  ],
  invalid_status_transition: [
    "Hãy tiếp nhận và xử lý sự cố trước khi đóng.",
    "Acknowledge and resolve the incident before closing it.",
  ],
  solis_pagination_contract_incomplete: [
    "Solis trả về danh sách chưa đầy đủ; cần xác minh phân trang.",
    "Solis returned an incomplete list; pagination needs validation.",
  ],
  credentials_incomplete: [
    "Thông tin kết nối chưa đầy đủ.",
    "Connection credentials are incomplete.",
  ],
  user_invalid_or_exists: [
    "Tên tài khoản đã tồn tại hoặc mật khẩu chưa đủ 12 ký tự.",
    "Username exists or password has fewer than 12 characters.",
  ],
  site_timezone_required: [
    "Cấu hình múi giờ nhà máy trước khi lưu lịch.",
    "Set the plant timezone before saving a schedule.",
  ],
  adapter_not_implemented: [
    "Adapter này cần bổ sung hợp đồng kết nối.",
    "This adapter needs its connection contract.",
  ],
  assignee_not_authorized_for_site: [
    "Người phụ trách chưa có quyền tại nhà máy này.",
    "The assignee has no access to this plant.",
  ],
};
export function errorText(key) {
  return errors[key]
    ? l(...errors[key])
    : l(
        "Không hoàn tất thao tác. Mã: ",
        "Could not complete the action. Code: ",
      ) + key;
}
