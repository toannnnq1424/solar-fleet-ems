import { l, t } from "./i18n.js";

// One schedule record feeds the editor, compiler, rollout and command journal.
export async function renderScheduleMainWorkspace(ui) {
  const {state, div, p, btn, card, table, notice, go, scheduleForm, operator} = ui;
  const root=div("stack schedule-workspace-root");
  root.append(div("form-actions",
    btn(l("Biểu giá điện", "Electricity tariffs"),()=>go("reports","","tariff")),
    btn(l("Kiểm tra lịch theo thiết bị", "Compile for equipment"),()=>go("operations","","schedule-plans")),
    btn(l("Triển khai đã kiểm tra", "Reviewed rollouts"),()=>go("operations","","rollouts"))));
  root.append(notice("Lưu lịch tạo bản nháp. Mỗi thiết bị cần kiểm tra múi giờ, số khung giờ và khả năng thực hiện trước khi triển khai.",
    "Saving creates a draft. Each device requires timezone, slot-limit and capability checks before deployment."));
  if(operator()) root.append(btn(l("+ Tạo lịch nháp", "+ Create draft"),()=>scheduleForm(),"primary"));
  const rows=(state.ops.schedule||[]).filter(r=>!state.site||r.site_id===state.site);
  if(!rows.length) root.append(card(l("Lịch đã lưu","Saved schedules"),p(l("Chưa có lịch. Tạo lịch hoặc chọn nhà máy khác.","No schedules. Create one or choose another plant."))));
  const dayNames=[l("Thứ 2","Monday"),l("Thứ 3","Tuesday"),l("Thứ 4","Wednesday"),l("Thứ 5","Thursday"),l("Thứ 6","Friday"),l("Thứ 7","Saturday"),l("Chủ nhật","Sunday")];
  for(const row of rows) {
    const actions=div("form-actions");
    if(operator()) actions.append(btn(l("Chỉnh sửa bản nháp","Edit draft"),()=>scheduleForm(row)));
    actions.append(btn(l("Biên dịch lịch này","Compile this schedule"),()=>{state.site=row.site_id; return go("operations","","schedule-plans");}));
    root.append(card(row.name,p([ui.siteName(row.site_id),row.timezone,row.state].filter(Boolean).join(" · ")),
      table([l("Ngày","Day"),l("Khung giờ","Time"),l("Chế độ","Mode"),"SOC %","kW"],
        (row.slots||[]).map(s=>[dayNames[s.day],s.start+" – "+s.end,t(s.mode),s.target_soc??"—",s.power_kw??"—"])),actions));
  }
  return root;
}
