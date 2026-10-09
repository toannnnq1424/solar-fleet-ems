import { l } from './i18n.js';
import { deviceReportPanel } from './device-report.js';
import { nativeReadingsPanel } from './native-readings.js';
import { requestLatestReadings, refreshReadingMessage } from './reading-refresh.js';

// Automatic refresh reads local snapshots only; the explicit vendor-read button
// uses the shared cadence/budget guard. Never refresh control forms.
// Shared by the device dialog and the monitoring workspace.
export function deviceLiveMonitor(ui, initial, id, options = {}) {
  const {div, p, btn, api} = ui;
  let info = initial, related = options.initial, busy = false, stopped = false, mounted = false, timer;
  const status = p('', 'field-help');
  status.setAttribute('role', 'status');
  const content = div('stack');
  const refreshButton = btn(l('Lấy bản nhận mới nhất', 'Load latest receipt'), () => update());
  const resultMessage = p('', 'field-help');
  resultMessage.setAttribute('role', 'status');
  const fetchButton = initial.can_refresh ? btn(l('Lấy số liệu mới nhất', 'Fetch latest readings'), async () => {
    fetchButton.disabled = true;
    try {
      const result = await requestLatestReadings(api, {device_id: id});
      await update();
      if (root.isConnected) resultMessage.textContent = refreshReadingMessage(result);
    } catch {
      if (root.isConnected) resultMessage.textContent = l('Chưa đọc được số liệu mới. Kiểm tra quyền và kết nối.', 'Could not fetch new readings. Check permissions and connection.');
    } finally { fetchButton.disabled = false; }
  }, 'primary') : null;
  const root = div('stack device-live-monitor',
    div('device-live-toolbar', status, div('row device-live-actions', refreshButton, fetchButton)), resultMessage, content);
  function ageLabel() {
    const stamp = Date.parse(info.latest?.received_at);
    const age = Number.isFinite(stamp) ? Math.max(0, Math.floor((Date.now() - stamp) / 1000)) : null;
    const cadence = info.latest?.collection_interval_seconds;
    status.textContent = l('Tự cập nhật màn hình mỗi 15 giây.', 'Screen refreshes every 15 seconds.') + ' ' +
      (Number.isFinite(cadence) ? l('Chu kỳ lấy từ hãng: tối thiểu ', 'Vendor collection: at least ') +
        Math.ceil(cadence / 60) + l(' phút; có thể lâu hơn khi xoay vòng thiết bị hoặc lỗi kết nối. ', ' minutes; rotation or connection failures can take longer. ') : '') +
      (age == null ? l('Chưa có bản nhận.', 'No receipt yet.') :
        l('Bản nhận cách đây ', 'Receipt age: ') + age + l(' giây.', ' seconds.')) +
      l(' Không phải luồng đo tức thời từ biến tần.', ' Not a real-time inverter stream.');
  }
  function draw() {
    // Preserve read-only filters and calendar choice across receipt changes.
    const key = el => el.getAttribute('aria-label') ||
      document.getElementById(el.getAttribute('aria-labelledby'))?.textContent || el.name || el.type;
    const choices = new Map([...content.querySelectorAll('input,select')].map(el =>
      [key(el), {value: el.value, checked: el.checked, option: el.selectedOptions?.[0]?.textContent}]));
    const disclosureKey = el => el.querySelector('summary')?.textContent?.replace(/\s*\(\d+\)$/, '');
    const disclosures = new Map([...content.querySelectorAll('details')].map(el => [disclosureKey(el), el.open]));
    const toggles = new Set([...content.querySelectorAll('button[data-monitor-choice][aria-pressed="true"]')]
      .map(el => el.dataset.monitorChoice));
    const report = deviceReportPanel(ui, info.latest, info.device);
    content.replaceChildren(...(report ? [report] : []), nativeReadingsPanel(ui, info.latest),
      ...(options.render ? [options.render(info, related)] : []));
    for (const el of content.querySelectorAll('input,select')) {
      const previous = choices.get(key(el));
      if (!previous) continue;
      if (el.type === 'checkbox') el.checked = previous.checked;
      else if (el.tagName === 'SELECT') {
        // Channel options can be reordered as new history arrives: match the
        // displayed channel identity, not the previous numeric array index.
        const option = [...el.options].find(o => o.textContent === previous.option);
        if (option) el.value = option.value;
      } else el.value = previous.value;
      el.dispatchEvent(new Event(el.tagName === 'INPUT' && el.type !== 'checkbox' ? 'input' : 'change'));
    }
    for (const el of content.querySelectorAll('details')) el.open = disclosures.get(disclosureKey(el)) ?? false;
    for (const el of content.querySelectorAll('button[data-monitor-choice]')) {
      if (toggles.has(el.dataset.monitorChoice) && el.getAttribute('aria-pressed') !== 'true') el.click();
    }
    ageLabel();
  }
  async function update() {
    if (stopped || busy || !root.isConnected || document.hidden) return;
    // Never steal focus while choosing a period or typing a native-field filter.
    if (content.contains(document.activeElement) && document.activeElement.matches('input,select,textarea')) return;
    busy = true; refreshButton.disabled = true;
    try {
      const [next, nextRelated] = await Promise.all([
        api('/devices/' + encodeURIComponent(id)), options.load ? options.load() : related,
      ]);
      if (stopped || !root.isConnected) return;
      // Focus/fullscreen may have changed while the local requests were pending.
      // Never tear down a reader's active interaction after an async response.
      if (content.contains(document.activeElement) && document.activeElement.matches('input,select,textarea')) return;
      if (document.fullscreenElement && content.contains(document.fullscreenElement)) return;
      info = next;
      related = nextRelated;
      draw();
    } catch {
      if (!stopped && root.isConnected) {
        // Do not retain private readings after a scope/session revocation.
        content.replaceChildren();
        resultMessage.textContent = '';
        status.textContent = l('Không lấy được dữ liệu mới. Kiểm tra phiên đăng nhập và kết nối SolarOne.',
          'Could not refresh. Check your session and SolarOne connection.');
      }
    } finally { busy = false; refreshButton.disabled = false; }
  }
  function tick() {
    if (stopped || !root.isConnected) return stop();
    update();
    timer = setTimeout(tick, 15000);
  }
  function stop() {
    stopped = true; clearTimeout(timer); observer.disconnect();
  }
  const observer = new MutationObserver(() => {
    if (root.isConnected) mounted = true;
    else if (mounted) stop();
  });
  observer.observe(document.body, {childList: true, subtree: true});
  draw();
  timer = setTimeout(tick, 15000);
  return root;
}
