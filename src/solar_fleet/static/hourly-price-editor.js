import { l } from './i18n.js';

// Explicit fixed Vietnam time, independent of the browser's timezone/DST.
const offset = 7 * 60 * 60 * 1000;
export function vietnamDateTime(iso) {
  const time = Date.parse(iso);
  return Number.isFinite(time) ? new Date(time + offset).toISOString().slice(0, 16) : '';
}
export function vietnamToUTC(value) {
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(value)) throw new Error(l('Chọn đủ ngày và giờ.', 'Choose a complete date and time.'));
  const time = Date.parse(value + ':00+07:00');
  if (!Number.isFinite(time) || vietnamDateTime(new Date(time).toISOString()) !== value) throw new Error(l('Ngày giờ không hợp lệ.', 'Invalid date or time.'));
  return new Date(time).toISOString();
}

export function hourlyPriceEditor(ui, saved = []) {
  const {div, e, p, input, field, btn, table} = ui;
  const start = input('datetime-local', saved[0] ? vietnamDateTime(saved[0].timestamp) : '');
  start.step = '3600';
  const inputs = Array.from({length:24}, (_, i) => {
    const buy = input('number', saved[i]?.import_per_kwh ?? '');
    const sell = input('number', saved[i]?.export_per_kwh ?? '');
    buy.step = sell.step = 'any';
    buy.setAttribute('aria-label', l(`Giá mua giờ ${i+1} (USD/kWh)`, `Hour ${i+1} import price (USD/kWh)`));
    sell.setAttribute('aria-label', l(`Giá bán giờ ${i+1} (USD/kWh)`, `Hour ${i+1} export price (USD/kWh)`));
    return {buy, sell, label:e('span', l(`Giờ ${i+1}`, `Hour ${i+1}`))};
  });
  const bulkBuy = input('number'), bulkSell = input('number');
  bulkBuy.step = bulkSell.step = 'any';
  const message = p('', 'field-help'); message.setAttribute('role', 'note');
  const apply = btn(l('Điền giá cho 24 giờ', 'Apply rates to all 24 hours'), () => {
    if (![bulkBuy, bulkSell].every(n=>n.value.trim() && Number.isFinite(Number(n.value)))) {
      message.textContent = l('Nhập cả giá mua và giá bán. Nếu không bán điện, nhập 0.', 'Enter both rates. Enter 0 if electricity is not sold.'); return;
    }
    for (const row of inputs) {row.buy.value=bulkBuy.value; row.sell.value=bulkSell.value;}
    message.textContent = l('Đã điền vào bảng; chưa lưu. Bạn có thể chỉnh riêng từng giờ.', 'Table filled, not saved. Each hour can still be edited.');
  }, 'secondary');
  const root=div('stack hourly-price-editor',
    field(l('Bắt đầu bảng giá (giờ Việt Nam, UTC+7)', 'Price start (Vietnam time, UTC+7)'),start),
    p(l('Nhập giá cho 24 giờ liên tiếp. Đơn vị USD/kWh theo bộ tính hiện tại, không phải VND. Không có giá mẫu tự điền.',
      'Enter 24 consecutive hours in USD/kWh for the current planner, not VND. No sample rates are prefilled.'),'field-help'),
    div('rate-fill-panel',div('form-grid',field(l('Giá mua chung (USD/kWh)','Bulk import rate (USD/kWh)'),bulkBuy),
      field(l('Giá bán chung (USD/kWh)','Bulk export rate (USD/kWh)'),bulkSell)),apply,message),
    div('hourly-price-scroll',table([l('Giờ Việt Nam','Vietnam time'),l('Mua (USD/kWh)','Import (USD/kWh)'),l('Bán (USD/kWh)','Export (USD/kWh)')],
      inputs.map(row=>[row.label,row.buy,row.sell]))));
  const updateLabels=()=>{
    let base; try {base=Date.parse(vietnamToUTC(start.value));} catch {base=null;}
    inputs.forEach((row,i)=>{row.label.textContent=base==null?l(`Giờ ${i+1}`,`Hour ${i+1}`):
      vietnamDateTime(new Date(base+i*3600000).toISOString()).replace('T',' · ');});
  };
  start.oninput=updateLabels; updateLabels();
  return {element:root, read:()=>{
    const base=Date.parse(vietnamToUTC(start.value));
    if (new Date(base).getUTCMinutes() !== 0) throw new Error(l('Giờ bắt đầu phải tròn giờ, ví dụ 08:00.', 'Start at a whole hour, for example 08:00.'));
    return inputs.map((row,i)=>{
      if (![row.buy,row.sell].every(n=>n.value.trim() && Number.isFinite(Number(n.value)))) throw new Error(l(`Cần giá mua và giá bán hợp lệ ở giờ ${i+1}.`, `Enter valid import and export rates for hour ${i+1}.`));
      return {timestamp:new Date(base+i*3600000).toISOString(), import_per_kwh:Number(row.buy.value),export_per_kwh:Number(row.sell.value)};
    });
  }};
}
