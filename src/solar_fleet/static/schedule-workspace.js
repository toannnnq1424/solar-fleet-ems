import { dispatchPlanCard } from "./dispatch-plan.js";
import { l, t } from "./i18n.js";
import { scheduleTimeline } from "./schedule-timeline.js";
import { scheduleWeekGrid } from './schedule-week-grid.js';

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
  if(operator()) root.append(div("form-actions",btn(l("+ Tạo lịch nháp", "+ Create draft"),()=>scheduleForm(),"primary")));
  const rows=(state.ops.schedule||[]).filter(r=>!state.site||r.site_id===state.site);
  const dayNames=[l("Thứ 2","Monday"),l("Thứ 3","Tuesday"),l("Thứ 4","Wednesday"),l("Thứ 5","Thursday"),l("Thứ 6","Friday"),l("Thứ 7","Saturday"),l("Chủ nhật","Sunday")];
  if(!rows.length) root.append(card(l('Lịch sạc/xả pin theo tuần','Weekly battery schedule'),
    p(l('Chưa có lịch được lưu. Dấu — là khung giờ chưa thiết lập, không phải chế độ nghỉ. Chọn một ô để tạo lịch nháp.',
      'No saved schedule. A dash means unconfigured, not idle mode. Select a cell to create a draft.'),'field-help'),
    scheduleWeekGrid(ui,[],dayNames,operator()?context=>scheduleForm(null,context):null)));
  for(const row of rows) {
    const actions=div("form-actions");
    if(operator()) actions.append(btn(l("Chỉnh sửa bản nháp","Edit draft"),()=>scheduleForm(row)));
    actions.append(btn(l("Biên dịch lịch này","Compile this schedule"),()=>{state.site=row.site_id; return go("operations","","schedule-plans");}));
    const technical=ui.e('details','','schedule-detail');
    technical.append(ui.e('summary',l('Xem timeline và danh sách khung giờ','View timeline and slot list')),
      scheduleTimeline(row.slots || [], dayNames),
      table([l("Ngày","Day"),l("Khung giờ","Time"),l("Chế độ","Mode"),l('Mức pin (%)','Battery level (%)'),"kW"],
        (row.slots||[]).map(s=>[dayNames[s.day],s.start+" – "+s.end,t(s.mode),s.target_soc??"—",s.power_kw??"—"])));
    root.append(card(row.name,p([ui.siteName(row.site_id),row.timezone,t(row.state)].filter(Boolean).join(" · ")),
      scheduleWeekGrid(ui,row.slots||[],dayNames,operator()?context=>scheduleForm(row,context):null),
      div("schedule-legend", ...['hold','charge','self_use','discharge'].map(mode=>div('mode-'+mode,ui.e('span','', 'schedule-legend-dot'),ui.e('span',t(mode))))),
      technical,actions));
  }

  const planning = ui.e('details','','engineering-tools');
  planning.append(ui.e('summary',l('Ước tính lịch tiết kiệm điện','Estimate an energy-saving schedule')),dispatchPlanCard(ui));
  root.append(planning);

  return root;
}
