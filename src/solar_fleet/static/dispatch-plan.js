import { l, number, date } from "./i18n.js";

// Both schedule and EMS views consume the same scoped, storage-backed engine.
export function dispatchPlanCard(ui) {
  const {state, div, p, btn, card, table} = ui;
  const output = div("stack");
  const run = btn(l("Tính kế hoạch từ dữ liệu đã xác minh", "Plan from verified observations"), async () => {
    if (!state.site) {
      output.replaceChildren(p(l("Vui lòng chọn nhà máy.", "Select a plant first.")));
      return;
    }
    run.disabled = true;
    try {
      const plan = await ui.api(`/sites/${encodeURIComponent(state.site)}/dispatch-schedule`);
      output.replaceChildren(
        p(l("Ước tính từ lịch sử; không gửi lệnh và chưa tạo lịch thiết bị.", "History-based estimate; no commands sent or device schedule created.")),
        p(`${plan.forecast_method} · ${plan.tariff_source} · SOC: ${date(plan.source_timestamp)}`),
        table([l("Thời điểm", "Time"), "PV kW", l("Tải kW", "Load kW"), "SOC %", l("Sạc kW", "Charge kW"), l("Xả kW", "Discharge kW"), "USD/kWh"],
          (plan.slots || []).map(s => [date(s.timestamp), number(s.solar_kw), number(s.load_kw), number(s.battery_soc_pct), number(s.battery_charge_kw), number(s.battery_discharge_kw), number(s.import_tariff)])),
        p(`${l("Chi phí dự kiến", "Estimated cost")}: ${number(plan.plan_cost_usd)} USD`)
      );
    } catch (error) {
      output.replaceChildren(p(error.message, "bad"));
    } finally {
      run.disabled = false;
    }
  });
  return card(l("Quy hoạch điều độ dự báo & khấu hao pin", "Predictive dispatch & battery degradation"),
    p(l("Cần ranh giới đo, lịch sử đã xác minh, SOC mới, thông số pin và biểu giá có nguồn gốc. Không tự điền dữ liệu mẫu.",
      "Requires a measurement boundary, verified history, fresh SOC, battery specifications and sourced tariffs. No sample inputs are supplied.")), run, output);
}