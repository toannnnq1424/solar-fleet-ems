import { l, t, date } from "./i18n.js";

export async function renderEmsWorkspace(ui) {
  const {state, div, p, btn, card, table, select, field, notice, api, go, operator, ruleForm, showDialog, raw} = ui;
  const root=div("stack ems-workspace-root");
  root.append(div("form-actions",
    btn(l("Triển khai nhiều thiết bị","Fleet rollout"),()=>go("operations","","rollouts")),
    btn(l("Lịch / TOU","Schedules / TOU"),()=>go("operations","schedules")),
    btn(l("Nhật ký lệnh","Command journal"),()=>go("operations","journal"))));
  root.append(notice("Quy tắc sử dụng mẫu đo đã xác minh. Chạy thử chỉ đánh giá điều kiện; đề xuất lệnh dùng chung quy trình xem trước và xác nhận.",
    "Rules use verified observations. Dry runs evaluate conditions; command proposals use the shared preview and confirmation workflow."));
  if(operator()) root.append(btn(l("+ Tạo quy tắc nháp","+ Create draft rule"),ruleForm,"primary"));
  const rules=(state.ops.rule||[]).filter(r=>!state.site||r.site_id===state.site);
  root.append(card(l("Quy tắc vận hành","Operating rules"), table([t("name"),t("plants"),t("status"),l("Thao tác","Action")],rules.map(r=>[
    r.name,ui.siteName(r.site_id),r.state,
    btn(l("Đánh giá dữ liệu hiện tại","Evaluate current readings"),async()=>{
      const result=await api("/rules/"+encodeURIComponent(r.id)+"/evaluate",{});
      showDialog(r.name,raw(r.name,result));
    })]))));
  if(!rules.length) root.append(p(l("Chưa có quy tắc đã lưu.","No saved rules.")));
  const runs=(state.ops.rule_run||[]).filter(r=>!state.site||r.site_id===state.site);
  root.append(card(l("Lịch sử đánh giá","Evaluation history"),table([l("Quy tắc","Rule"),l("Thời điểm","Time"),l("Kết quả điều kiện","Condition state")],
    runs.map(r=>[rules.find(s=>s.id===r.rule_id)?.name||r.rule_id,date(r.evaluated_at),r.condition_state]))));
  const intents=[...new Set((state.fleet.devices||[]).flatMap(d=>(d.capabilities||[]).map(c=>c.intent)))];
  const intent=select((intents.length?intents:['SET_RESERVE_SOC','SET_ZERO_EXPORT','SET_TOU']).map(id=>[id,t(id)]));
  const result=div("stack");
  const assess=btn(l("Kiểm tra khả năng từng thiết bị","Assess each device"),async()=>{
    const ids=(state.fleet.sites||[]).filter(s=>!state.site||s.id===state.site).map(s=>s.id);
    if(!ids.length) {result.replaceChildren(p(l("Chưa có nhà máy.","No plants.")));return;}
    const data=await api('/ems/batch-assess',{site_ids:ids,intents:[intent.value]});
    result.replaceChildren(table([t('plants'),t('status'),l('Thiết bị / lý do','Device / reason')],data.sites.map(s=>[
      s.name,s.status,s.targets.map(d=>d.device_id+': '+d.state+' · '+d.reason).join('; ')||l('Chưa có thiết bị','No devices')])));
  });
  root.append(card(l("Tương thích đa hãng","Multi-vendor compatibility"),field(l("Chức năng","Intent"),intent),assess,result));
  const forecastDevices=(state.fleet.devices||[]).filter(d=>!state.site||d.site_id===state.site);
  const forecastDevice=select(forecastDevices.map(d=>[d.id,d.name||d.id]));
  const forecastResult=div("stack");
  root.append(card(l("Dự báo theo lịch sử", "Historical baseline forecast"),
    p(l("Học theo ngày trong tuần và giờ từ dữ liệu W đã xác minh. Cần tối thiểu 3 ngày, 24 giờ đủ mẫu. Kết quả để tham khảo; không tự gửi lệnh.",
      "Learn weekday/hour patterns from verified W observations. Requires at least 3 dates and 24 sufficiently sampled hours. Advisory results do not dispatch commands.")),
    field(l("Thiết bị dự báo", "Forecast device"),forecastDevice),
    btn(l("Tính dự báo 24 giờ", "Calculate 24-hour baseline"),async()=>{
      if(!forecastDevice.value) {forecastResult.replaceChildren(p(l("Chọn thiết bị trước.","Choose a device first.")));return;}
      try {
        const value=await api(`/devices/${encodeURIComponent(forecastDevice.value)}/forecast-baseline`);
        forecastResult.replaceChildren(...Object.entries(value.metrics).map(([metric,data])=>card(metric,
          p(`${data.status} · ${data.training_days} ${l("ngày", "dates")} · ${data.training_hours} h`),
          table([l("Giờ địa phương","Local time"),"W",l("Cơ sở dự báo","Basis")],data.points.map(point=>[
            date(point.local_time),point.value_w===null?"—":Math.round(point.value_w).toString(),point.method])))));
      } catch(err) {forecastResult.replaceChildren(p(err.message,"bad"));}
    }),forecastResult));
  return root;
}
