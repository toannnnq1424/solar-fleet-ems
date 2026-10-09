import { l } from './i18n.js';

let pending;
export async function requestLatestReadings(api, scope = {}) {
  // All buttons share a request; the server is the authority for quotas/scope.
  if (pending) return {state: 'BUSY', updated: 0, retry_after_seconds: 15};
  pending = api('/readings/refresh', scope);
  try { return await pending; } finally { pending = null; }
}

export function refreshReadingMessage(result) {
  const messages = {
    UPDATED: l('Đã hoàn tất lượt đọc từ hãng. Hãng có thể vẫn trả cùng thời điểm đo.', 'Vendor read completed. The source may still return the same measurement time.'),
    PARTIAL: l('Chỉ cập nhật được một phần; kiểm tra Dữ liệu & kết nối.', 'Partially refreshed; check Data & connections.'),
    FAILED: l('Chưa đọc được từ hãng. Dữ liệu cũ không được coi là mới.', 'Vendor read failed. Old readings are not marked fresh.'),
    NO_SOURCE: l('Chưa có nguồn hãng đang bật trong phạm vi này.', 'No enabled vendor source in this scope.'),
    BUSY: l('Bộ thu thập đang chạy hoặc vừa chạy; màn hình sẽ nhận bản mới tự động.', 'Collector is active or has just run; the screen will receive new receipts automatically.'),
    WAITING: l('Chưa đến lượt gọi tiếp theo để bảo vệ giới hạn tài khoản.', 'Waiting for the next permitted account read.'),
  };
  return (messages[result.state] || l('Chưa xác định kết quả đồng bộ.', 'Refresh result unknown.')) +
    (result.retry_after_seconds != null && ['WAITING', 'BUSY'].includes(result.state) ?
      l(' Thử lại sau khoảng ', ' Retry in about ') + result.retry_after_seconds + l(' giây.', ' seconds.') : '');
}
