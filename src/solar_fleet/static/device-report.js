import { l, number, date } from './i18n.js';
import { icon } from './icons.js';
import { metricTiles, percentageGauge } from './ui-visuals.js';

const quantity = (value, unit) => value == null ? '—' : number(value, 2) + ' ' + unit;

export function deviceReportPanel(ui, latest = {}, device = {}) {
  const r = latest.reported;
  if (!r) return null;
  const {e, div, p, card, badge, select, field} = ui;
  const period = select([
    ['today', l('Hôm nay', 'Today')], ['week', l('Tuần này', 'This week')],
    ['month', l('Tháng này', 'This month')], ['year', l('Năm nay', 'This year')], ['total', l('Tích lũy', 'Lifetime')],
  ], 'today');
  const energy = div('stack');
  const draw = () => {
    const values = r.periods?.[period.value] || {};
    energy.replaceChildren(metricTiles(ui, [
      ['sun', l('Điện năng phát', 'Generation'), values.generation_kwh, 'kWh', 'green'],
      ['battery', l('Điện năng sạc', 'Charge energy'), values.charge_kwh, 'kWh', 'solar'],
      ['bolt', l('Điện năng xả', 'Discharge energy'), values.discharge_kwh, 'kWh', 'purple'],
    ], 'device-energy-metrics'));
    if (!r.periods?.[period.value]) energy.append(p(l('Hãng chưa trả số liệu cho kỳ này.', 'No vendor data for this period.')));
  };
  period.onchange = draw; draw();
  const received = Date.parse(latest.received_at);
  const receiptTtl = Math.max(300, (latest.collection_interval_seconds || 300) * 2 + 120) * 1000;
  const old = !Number.isFinite(received) || Date.now() - received > receiptTtl || received > Date.now() + 5000;
  const ratio = Number.isFinite(r.rated_kw) && Number.isFinite(r.ac_kw) && r.rated_kw > 0 && r.ac_kw >= 0 && r.ac_kw <= r.rated_kw ? r.ac_kw / r.rated_kw * 100 : null;
  const identity = div('device-report-identity', div('device-report-emblem', icon('device')),
    e('span', l('Số liệu riêng của thiết bị', 'This device only'), 'eyebrow'),
    e('h3', device.name || l('Biến tần', 'Inverter')),
    e('span', device.vendor_id || r.serial, 'small muted'),
    div('row', badge(l('Hãng báo cáo', 'Vendor reported'), 'warn'), old ? badge(l('Bản nhận đã cũ', 'Receipt expired'), 'warn') : null),
    div('facts', ui.fact ? ui.fact(l('Công suất định mức', 'Rated output'), quantity(r.rated_kw, 'kW')) : p(l('Công suất định mức: ', 'Rated output: ') + quantity(r.rated_kw, 'kW'))),
    p(l('Nhận lúc: ', 'Received: ') + date(latest.received_at)),
    p(l('Chưa có thời điểm đo xác minh. Không dùng số liệu này để phát lệnh hoặc tính hóa đơn.',
      'Measurement time is unverified. These values do not authorize commands or billing.')));
  const power = div('device-report-power', percentageGauge(ratio, l('So với định mức', 'Of rated output')),
    div('stack', e('span', l('Công suất AC đầu ra', 'AC output power'), 'muted'),
      e('strong', quantity(r.ac_kw, 'kW'), 'device-report-current'),
      p(l('AC có thể gồm điện từ pin; không đồng nghĩa công suất mặt trời.', 'AC can include battery discharge; it is not the same as solar power.'))));
  const metrics = metricTiles(ui, [
    ['sun', l('Tổng đầu vào DC / PV', 'Total DC / PV input'), r.pv_dc_kw, 'kW', 'solar'],
    ['thermometer', l('Nhiệt độ biến tần', 'Inverter temperature'), r.temperature_c, '°C', 'purple'],
  ], 'device-power-metrics');
  const monitor = card(l('Giám sát biến tần', 'Inverter monitoring'), power, metrics);
  const energyCard = card(l('Điện năng theo kỳ', 'Energy by period'),
    field(l('Kỳ điện năng thiết bị', 'Device energy period'), period), energy,
    p(l('Bộ đếm do hãng trả riêng cho biến tần này. Không phải số liệu tổng nhà máy; chưa xác minh ranh giới múi giờ của kỳ.',
      'Vendor counters for this inverter only, not station totals. Calendar timezone boundaries remain unverified.')));
  const root = div('device-report-panel', identity, div('stack', monitor, energyCard));
  root.setAttribute('aria-label', l('Tổng quan riêng của biến tần', 'Individual inverter overview'));
  return root;
}

export function equipmentPower(ui, device) {
  if (device.power_kw != null) return ui.e('span', quantity(device.power_kw, 'kW'));
  const ac = device.vendor_report?.ac_kw;
  return ui.div('stack gap-none', ui.e('b', quantity(ac, 'kW')),
    ac == null ? null : ui.e('small', l('AC · hãng báo cáo', 'AC · vendor reported'), 'muted'));
}
