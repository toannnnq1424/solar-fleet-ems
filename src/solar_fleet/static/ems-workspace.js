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
  return root;
}
