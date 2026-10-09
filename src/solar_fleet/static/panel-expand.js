import { icon } from './icons.js';
import { l } from './i18n.js';

let fallbackPanel = null;
function updateButtons() {
  for (const button of document.querySelectorAll('[data-panel-expand]')) {
    const panel = button.closest('.card');
    const expanded = document.fullscreenElement === panel || fallbackPanel === panel;
    const label = l(expanded ? 'Thu nhỏ: ' : 'Phóng to: ', expanded ? 'Collapse: ' : 'Expand: ') + panel.dataset.panelTitle;
    button.setAttribute('aria-label', label);
    button.setAttribute('aria-expanded', String(expanded));
    button.title = label;
    button.replaceChildren(icon(expanded ? 'minimize' : 'maximize'));
  }
}
function closeFallback() {
  const panel = fallbackPanel;
  panel?.classList.remove('panel-expanded-fallback');
  fallbackPanel = null;
  updateButtons();
  panel?.querySelector('[data-panel-expand]')?.focus();
}
document.addEventListener('fullscreenchange', updateButtons);
window.addEventListener('hashchange', closeFallback);
document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && fallbackPanel) { event.preventDefault(); closeFallback(); }
});

export function addPanelExpansion(panel, title) {
  panel.classList.add('expandable-panel');
  panel.dataset.panelTitle = title;
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'panel-expand-button';
  button.dataset.panelExpand = '';
  button.setAttribute('aria-label', l('Phóng to: ', 'Expand: ') + title);
  button.setAttribute('aria-expanded', 'false');
  button.title = button.getAttribute('aria-label');
  button.append(icon('maximize'));
  const note = document.createElement('p');
  note.className = 'panel-snapshot-note';
  note.textContent = l('Bản xem phóng to giữ số liệu khi mở. Thu nhỏ để nhận bản cập nhật mới.',
    'Expanded view keeps the snapshot opened. Collapse to receive the latest update.');
  panel.querySelector('h2')?.after(note);
  button.onclick = async () => {
    if (document.fullscreenElement === panel) {
      try { await document.exitFullscreen(); } catch { /* Browser owns fullscreen. */ }
    } else if (fallbackPanel === panel) closeFallback();
    else {
      closeFallback();
      try {
        if (!panel.requestFullscreen) throw new Error('unavailable');
        await panel.requestFullscreen();
      } catch {
        fallbackPanel = panel;
        panel.classList.add('panel-expanded-fallback');
        updateButtons();
      }
    }
  };
  panel.append(button);
  return panel;
}
