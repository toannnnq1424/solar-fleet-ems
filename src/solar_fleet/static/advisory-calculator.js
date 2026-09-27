import { l } from "./i18n.js";

// Inputs start blank. Results are the actual API response, not fabricated KPI fields.
export function advisoryCalculator(ui, title, endpoint, fields) {
  const input = document.createElement("textarea");
  input.rows = 9;
  input.setAttribute("aria-label", title + " JSON");
  const output = ui.div("stack");
  const run = ui.btn(l("Tính từ đầu vào đã nhập", "Calculate supplied inputs"), async () => {
    run.disabled = true;
    try {
      const body = JSON.parse(input.value);
      const result = await ui.api(endpoint, body);
      const pre = document.createElement("pre");
      pre.textContent = JSON.stringify(result, null, 2);
      output.replaceChildren(pre);
    } catch (error) {
      output.replaceChildren(ui.p(error.message, "bad"));
    } finally { run.disabled = false; }
  });
  return ui.card(title,
    ui.p(l("Máy tính tư vấn với đầu vào thủ công. Không gửi lệnh, không xác minh tuân thủ hoặc kết nối thiết bị.",
      "Manual advisory calculator. No commands sent; no compliance or device connectivity verified.")),
    ui.p(fields), input, run, output);
}