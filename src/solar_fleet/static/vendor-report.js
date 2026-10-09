import { l, date } from './i18n.js';
import { dailyEnergyChart, metricTiles } from './ui-visuals.js';

// Separate presentation channel: never turns vendor-local clocks into UTC and
// never feeds command, optimizer, billing or verified telemetry endpoints.
export function reportedNotice(ui, report) {
  const clock = report.source_clock?.replace('T', ' ') || '—';
  return ui.div('vendor-report-provenance stack gap-sm',
    ui.div('row', ui.badge(l('Hãng báo cáo', 'Vendor reported'), 'warn'),
      ui.e('strong', report.vendor || l('Nguồn kết nối', 'Connected source')),
      report.receipt_expired ? ui.badge(l('Bản nhận đã cũ', 'Receipt expired'), 'warn') : null),
    ui.p(l('Giờ cập nhật phía hãng: ', 'Vendor update clock: ') + clock +
      l(' · Chưa xác minh múi giờ. SolarOne nhận lúc: ', ' · Timezone unverified. Received by SolarOne: ') + date(report.received_at)),
    ui.p(l('Đồng bộ định kỳ, không phải đo tức thời. ', 'Periodic collection, not instantaneous measurement. ') +
      (Number.isFinite(report.collection_interval_seconds) ? l('Chu kỳ tài khoản tối thiểu: ', 'Minimum account interval: ') +
        Math.ceil(report.collection_interval_seconds / 60) + l(' phút. Xoay vòng nhà máy có thể lâu hơn.', ' minutes. Station rotation can take longer.') : '')),
    ui.p(l('Đây là số liệu tổng hợp do hãng cung cấp, chưa phải số đo được SolarOne xác minh cho điều khiển hoặc tính tiền. Kỳ ngày/tháng/năm theo lịch phía hãng.',
      'These are vendor aggregates, not SolarOne-verified control or billing measurements. Day/month/year follow the vendor calendar.')));
}

export function reportedEnergyChart(report) {
  return dailyEnergyChart((report.daily_energy || []).map(row => ({
    date: row.start_date, pv_kwh: row.generation_kwh, load_kwh: row.consumption_kwh,
    grid_export_kwh: row.export_kwh,
  })), {label: l('Điện năng theo ngày do hãng báo cáo', 'Vendor-reported daily energy')});
}

export function reportedSummary(ui, report, period = 'today') {
  const energy = report.periods?.[period] || {};
  const hint = l('Hãng báo cáo', 'Vendor reported');
  return ui.div('stack vendor-report-summary', reportedNotice(ui, report),
    metricTiles(ui, [
      ['sun', l('Điện mặt trời', 'Solar power'), report.power?.pv_w == null ? null : report.power.pv_w / 1000, 'kW', 'solar', hint],
      ['home', l('Đang tiêu thụ', 'Consumption'), report.power?.load_w == null ? null : report.power.load_w / 1000, 'kW', 'blue', hint],
      ['battery', l('Mức pin', 'Battery level'), report.power?.battery_soc, '%', 'purple', hint],
      ['chart', l('Sản lượng trong kỳ', 'Period generation'), energy.generation_kwh, 'kWh', 'green', hint],
      ['bolt', l('Tiêu thụ trong kỳ', 'Period consumption'), energy.consumption_kwh, 'kWh', 'solar', hint],
      ['grid', l('Mua điện trong kỳ', 'Period import'), energy.import_kwh, 'kWh', 'blue', hint],
    ], 'reported-metrics'),
    ui.p(energy.start_date ? energy.start_date + ' → ' + energy.end_date : l('Chưa có tổng hợp cho kỳ đã chọn.', 'No aggregate for the selected period.')));
}

export function reportedFlow(canonical, report) {
  if (!report) return canonical;
  const result = {...canonical, channels: {...canonical.channels}};
  for (const [key, value] of Object.entries(report.power || {})) {
    if (canonical[key] != null || !Number.isFinite(value)) continue;
    result[key] = value;
    result.channels[key] = {quality: 'VENDOR_REPORTED', sources: [], valid_until: null};
  }
  return result;
}
