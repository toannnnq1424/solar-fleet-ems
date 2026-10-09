import { l, t, number, date } from './i18n.js';
import { icon } from './icons.js';

const stateLabel=state=>({TRUE:l('Thỏa điều kiện','Matched'),FALSE:l('Chưa thỏa','Not matched'),UNKNOWN:l('Chưa đủ dữ liệu','Insufficient data')})[state]||t(state||'UNKNOWN');
const reasonLabel=reason=>({missing_measurement:l('Chưa có số đo','No measurement'),ambiguous_measurement_source:l('Có nhiều nguồn đo, cần xác định nguồn','Competing measurement sources'),fresh_verified_measurement_required:l('Cần số đo mới và đã xác minh','Fresh verified measurement required'),unit_mismatch:l('Đơn vị không khớp','Unit mismatch'),evaluated:l('Đã đánh giá','Evaluated')})[reason]||reason||'—';

export function ruleEvaluation(ui,result){
  const {div,e,p,table,badge}=ui;
  const names=id=>ui.state.fleet.devices.find(d=>d.id===id)?.name||id;
  return div('stack rule-evaluation',
    div('rule-result-heading',icon('shield'),div('stack gap-sm',e('strong',stateLabel(result.condition_state)),p(l('Chạy thử · không gửi lệnh thiết bị','Dry run · no equipment commands'),'field-help'))),
    p(result.evaluated_at?date(result.evaluated_at):'—','field-help'),
    table([l('Thiết bị / thông số','Equipment / metric'),l('Giá trị','Value'),l('Kết quả','Result'),l('Giải thích','Explanation')],(result.conditions||[]).map(c=>[
      div('stack gap-sm',e('b',names(c.device_id)),e('span',t(c.metric))),number(c.value),badge(stateLabel(c.state),c.state==='TRUE'?'good':'gray'),reasonLabel(c.reason)])),
    p(l('Hành động đề xuất: ','Proposed actions: ')+(result.proposed_actions||[]).length+' · '+l('Thực thi tự động vẫn tắt.','Automatic dispatch remains off.'),'notice'));
}

// Inspection and local dry runs share the existing /rules owner. Never activates a rule.
export function ruleOverview(ui,rules){
  const {div,e,p,card,field,input,btn,table,api}=ui;
  const search=input('search'),list=div('rule-directory'),detail=div('stack'),evaluation=div('stack');
  let selected=rules[0]?.id,version=0;
  const names=id=>ui.state.fleet.devices.find(d=>d.id===id)?.name||id||'—';
  const comparison={lt:'<',lte:'≤',gt:'>',gte:'≥',eq:'='};
  const draw=()=>{
    const rows=rules.filter(r=>(r.name+' '+(r.description||'')).toLocaleLowerCase().includes(search.value.toLocaleLowerCase()));
    if(!rows.some(r=>r.id===selected))selected=rows[0]?.id;
    const rule=rows.find(r=>r.id===selected);version++;evaluation.replaceChildren();
    list.replaceChildren(...rows.map(r=>{
      const choice=btn('',()=>{selected=r.id;draw();},'rule-directory-item');choice.setAttribute('aria-pressed',String(r.id===selected));
      choice.append(e('b',r.name),e('span',ui.siteName(r.site_id)),e('small',`${r.conditions.length} ${l('điều kiện','conditions')} · ${r.actions.length} ${l('đề xuất','proposals')}`));return choice;
    }));
    if(!rows.length)list.append(p(l('Chưa có quy tắc phù hợp. Tạo bản nháp để bắt đầu.','No matching rules. Create a draft to get started.'),'field-help'));
    detail.replaceChildren(e('h3',rule?.name||l('Chưa chọn quy tắc','No rule selected')),
      p(rule?.description||l('Chọn quy tắc để xem điều kiện và hành động đề xuất.','Choose a rule to inspect its conditions and proposed actions.'),'field-help'));
    const stages=div('rule-stages');
    stages.append(div('rule-stage',icon('clock'),e('b',l('Đánh giá','Evaluate')),p(l('Khi chạy thử hoặc bật theo dõi.','On dry run or when monitoring is enabled.'),'field-help')),
      div('rule-stage',icon('activity'),e('b',l('Tất cả điều kiện','All conditions')),p(l('Cùng đúng · số đo mới · đúng đơn vị','All match · fresh readings · exact units'),'field-help')),
      div('rule-stage',icon('bolt'),e('b',l('Đề xuất','Propose')),p(l('Không tự gửi lệnh.','No automatic commands.'),'field-help')));
    detail.append(stages,table([l('Điều kiện phải cùng đúng','Conditions must all match'),l('Số giây tối đa','Maximum age (s)')],(rule?.conditions||[]).map(c=>[
      div('stack gap-sm',e('b',names(c.device_id)),e('span',`${t(c.metric)} ${comparison[c.comparison]||c.comparison} ${number(c.threshold)} ${c.unit}`)),c.max_age_seconds??300])),
      table([l('Thiết bị nhận đề xuất','Proposal target'),l('Thay đổi','Change')],(rule?.actions||[]).map(a=>[names(a.device_id),t(a.intent)])));
    const run=btn(l('Đánh giá dữ liệu hiện tại','Evaluate current readings'),async()=>{
      const current=version;run.disabled=true;evaluation.replaceChildren(p(l('Đang đánh giá…','Evaluating…')));
      try {const result=await api('/rules/'+encodeURIComponent(rule.id)+'/evaluate',{});if(current===version)evaluation.replaceChildren(ruleEvaluation(ui,result));}
      catch(error){if(current===version)evaluation.replaceChildren(p(error.message,'bad'));}
      finally {if(current===version){run.disabled=false;evaluation.append(run);}}
    },'primary');
    run.disabled=!rule||!ui.operator();
    evaluation.append(p(l('Chạy thử trên các số đo hiện có; không sinh dữ liệu mô phỏng. Kết quả thiếu dữ liệu vẫn được giữ là chưa xác định.','Evaluate existing readings without generating simulated observations. Missing data remains unknown.'),'field-help'),run);
  };
  search.oninput=draw;draw();
  const root=div('rule-reference-layout',card(l('Danh sách quy tắc vận hành','Operating rule directory'),field(l('Tìm quy tắc','Find a rule'),search),list),
    card(l('Chi tiết quy tắc','Rule details'),detail),card(l('Kiểm tra an toàn & chạy thử','Safety & dry run'),p(l('Điều khiển vật lý đang khóa','Physical dispatch is locked'),'notice'),evaluation));
  return root;
}
