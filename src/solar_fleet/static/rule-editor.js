import { l, t } from './i18n.js';
import { icon } from './icons.js';
import { ruleActionFields } from './rule-action-fields.js';

// One draft editor for both EMS entry points; this module never activates or dispatches.
export function openRuleEditor(ui, existing=null) {
  const {state,e,div,p,btn,card,input,select,field,notice,form,api,siteSelect,showDialog,closeDialog,refresh}=ui;
  const name=input('text',existing?.name||''),site=siteSelect(existing?.site_id),description=e('textarea');
  name.required=true;name.maxLength=120;site.disabled=!!existing;description.maxLength=2000;description.value=existing?.description||'';
  const conditions=[],actions=[],conditionList=div('stack rule-condition-list'),actionList=div('stack rule-action-list'),review=div('rule-draft-summary');
  const deviceOptions=()=>[['',l('Chọn thiết bị','Choose equipment')],...state.fleet.devices.filter(d=>d.site_id===site.value).map(d=>[d.id,d.name||d.vendor_id])];
  let addConditionButton,addActionButton;
  const summary=()=>{
    review.replaceChildren(icon('shield'),e('strong',l('Bản nháp · chưa tự điều khiển','Draft · no automatic control')),
      p(`${conditions.length} ${l('điều kiện cùng đúng','conditions must all match')} · ${actions.length} ${l('hành động đề xuất','proposed actions')}`));
    if(addConditionButton)addConditionButton.disabled=conditions.length>=12;
    if(addActionButton)addActionButton.disabled=actions.length>=12;
  };
  function addCondition(value={}){
    if(conditions.length>=12)return;
    const device=select(deviceOptions(),value.device_id||''),metric=input('text',value.metric||''),unit=input('text',value.unit||'');
    metric.required=unit.required=device.required=true;metric.maxLength=160;unit.maxLength=40;
    const observed=select([['',l('Chọn thiết bị trước','Choose equipment first')]],''),help=p('','field-help'),manual=input('checkbox');
    manual.checked=!!value.metric;observed.disabled=manual.checked;
    const expert=e('details','','rule-advanced');expert.open=manual.checked;
    expert.append(e('summary',l('Nhập thông số thủ công · kỹ thuật','Manual metric · advanced')),field(l('Tôi biết chính xác tên thông số và đơn vị','I know the exact metric name and unit'),manual),
      div('form-grid',field(l('Tên thông số','Metric name'),metric),field(l('Đơn vị','Unit'),unit)));
    const comparison=select([['',l('Chọn phép so sánh','Choose a comparison')],...['lt','lte','gt','gte','eq'].map((v,i)=>[v,[l('Nhỏ hơn','Less than'),l('Không lớn hơn','At most'),l('Lớn hơn','Greater than'),l('Không nhỏ hơn','At least'),l('Bằng','Equal to')][i]])],value.comparison||'');
    const threshold=input('number',value.threshold??''),age=input('number',value.max_age_seconds??'');
    threshold.required=comparison.required=true;threshold.step='any';age.min='1';age.max='300';age.step='1';
    const row=div('rule-builder-entry');let generation=0,samples=[];
    const toggle=()=>{metric.disabled=unit.disabled=!manual.checked;observed.disabled=manual.checked||!samples.length;};
    manual.onchange=()=>{if(!manual.checked){metric.value=unit.value='';observed.value='';}toggle();};
    observed.onchange=()=>{const s=observed.value===''?null:samples[Number(observed.value)];metric.value=s?.metric||'';unit.value=s?.unit||'';help.textContent=s?l('Đơn vị: ','Unit: ')+s.unit+' · '+t(s.quality||'UNKNOWN')+' · '+l('Chưa xác minh sẽ chặn đánh giá.','Unverified data blocks evaluation.') : '';};
    async function load(){
      const version=++generation,id=device.value;samples=[];observed.disabled=true;
      if(!manual.checked)metric.value=unit.value='';
      observed.replaceChildren(new Option(l('Chưa có thông số để chọn','No observed metrics to select'),''));help.textContent='';
      if(!id)return;
      try {
        const result=await api('/devices/'+encodeURIComponent(id));if(version!==generation||!conditions.includes(entry))return;
        const unique=new Map();for(const s of result.latest?.samples||[])if(s.metric&&s.unit)unique.set(JSON.stringify([s.metric,s.unit]),s);
        samples=[...unique.values()];
        observed.replaceChildren(new Option(l('Chọn thông số đã ghi nhận','Choose an observed metric'),''),...samples.map((s,i)=>new Option(t(s.metric)+' · '+s.unit+' · '+t(s.quality||'UNKNOWN'),String(i))));
        help.textContent=samples.length?'':l('Chưa nhận được thông số có đơn vị. Đồng bộ dữ liệu hoặc nhờ kỹ thuật kiểm tra; không tự đặt tên đoán.','No metric with a unit has been received. Synchronize readings or ask technical support; do not guess metric names.');toggle();
      }catch(error){if(version===generation)help.textContent=error.message;}
    }
    device.onchange=load;
    const entry={device,metric,unit,comparison,threshold,age};conditions.push(entry);
    const remove=btn(l('Bỏ điều kiện','Remove condition'),()=>{generation++;conditions.splice(conditions.indexOf(entry),1);row.remove();summary();},'text-button');remove.prepend(icon('trash'));
    row.append(field(l('Thiết bị theo dõi','Monitored equipment'),device),field(l('Thông số đã ghi nhận','Observed metric'),observed),help,
      div('form-grid',field(l('So sánh','Comparison'),comparison),field(l('Ngưỡng theo đơn vị đã chọn','Threshold in selected unit'),threshold)),
      field(l('Số giây tối đa kể từ lúc đo (tùy chọn)','Maximum reading age in seconds (optional)'),age),p(l('Để trống dùng giới hạn 300 giây của bộ đánh giá.','Leave blank to use the evaluator’s 300-second limit.'),'field-help'),expert,remove);
    conditionList.append(row);toggle();summary();load();
  }
  function addAction(value={}){
    if(actions.length>=12)return;
    const device=select(deviceOptions(),value.device_id||''),intent=select([['',l('Chọn thiết bị trước','Choose equipment first')]],'');
    device.required=intent.required=true;intent.disabled=true;
    const fields=div('stack'),help=p('','field-help'),row=div('rule-builder-entry');
    help.setAttribute('role','status');
    let generation=0,capabilities=[],editor=null,unchanged=!!value.intent,loading=false;
    const entry={device,intent,read:()=>{
      if(loading)throw new Error(l('Đợi tải hồ sơ thiết bị.','Wait for the equipment profile.'));
      if(unchanged && device.value===value.device_id && intent.value===value.intent)return structuredClone(value.parameters||{});
      if(!editor)throw new Error(l('Chọn chức năng có cấu trúc tham số rõ ràng.','Choose an action with a defined parameter contract.'));
      return editor.read();
    }};
    actions.push(entry);
    function render(initial){
      editor=null;fields.replaceChildren();
      const capability=capabilities.find(c=>c.intent===intent.value);
      help.textContent=capability?l('Trạng thái hồ sơ: ','Profile state: ')+t(capability.state)+' · '+(capability.reason||''):l('Chọn chức năng theo hồ sơ thiết bị.','Choose an action from the equipment profile.');
      if(!intent.value)return;
      try{
        editor=ruleActionFields(ui,capability,initial);
        fields.append(editor.node);
        editor.node.addEventListener('input',()=>{unchanged=false;});
        editor.node.addEventListener('change',()=>{unchanged=false;});
        editor.node.addEventListener('click',event=>{if(event.target.closest('button'))unchanged=false;});
      }catch(error){
        help.textContent=error.message;
        if(unchanged)fields.append(p(l('Giữ nguyên hành động đã lưu. Muốn thay đổi, hãy chọn lại thiết bị/chức năng có hồ sơ đầy đủ.','The saved action will be preserved unchanged. To change it, choose equipment and an action with a complete profile.'),'notice'));
      }
    }
    async function load(preserve=false){
      const version=++generation,id=device.value;loading=!!id;editor=null;capabilities=[];
      intent.disabled=true;fields.replaceChildren();help.textContent=id?l('Đang đọc hồ sơ thiết bị…','Loading equipment profile…'):l('Chọn thiết bị để xem chức năng và giới hạn.','Choose equipment to see its actions and limits.');
      intent.replaceChildren(new Option(l('Chọn thay đổi đề xuất','Choose a proposed change'),''));
      if(!id)return;
      try{
        const info=await api('/devices/'+encodeURIComponent(id));
        if(version!==generation||!actions.includes(entry))return;
        capabilities=info.capabilities||[];
        intent.replaceChildren(new Option(l('Chọn thay đổi đề xuất','Choose a proposed change'),''),...capabilities.map(c=>new Option(t(c.intent)+' · '+t(c.state),c.intent)));
        if(preserve && value.intent && !capabilities.some(c=>c.intent===value.intent))intent.append(new Option(t(value.intent)+' · '+l('Hồ sơ không còn khả dụng','Profile unavailable'),value.intent));
        intent.disabled=!capabilities.length&&!preserve;
        intent.value=preserve?value.intent||'':'';
        loading=false;render(preserve?value.parameters:undefined);
        if(!capabilities.length&&!preserve)help.textContent=l('Thiết bị chưa có chức năng được khai báo. Không tự suy chức năng từ hãng.','No actions are declared for this equipment. Actions are not inferred from its brand.');
      }catch(error){
        if(version!==generation||!actions.includes(entry))return;
        loading=false;help.textContent=error.message;
        if(preserve){intent.append(new Option(t(value.intent),value.intent));intent.value=value.intent;fields.append(p(l('Không tải được hồ sơ; chỉ giữ nguyên hành động cũ.','Profile unavailable; the existing action can only be preserved unchanged.'),'notice'));}
      }
    }
    device.onchange=()=>{unchanged=false;load();};
    intent.onchange=()=>{unchanged=false;render();};
    const remove=btn(l('Bỏ hành động','Remove action'),()=>{generation++;actions.splice(actions.indexOf(entry),1);row.remove();summary();},'text-button');remove.prepend(icon('trash'));
    row.append(field(l('Thiết bị đề xuất thay đổi','Target equipment'),device),field(l('Thay đổi đề xuất','Proposed change'),intent),help,fields,
      p(l('Đây là bản nháp. Trạng thái hồ sơ không mở quyền tự động điều khiển; mọi lệnh vẫn cần kiểm tra và xác nhận riêng.','This is a draft. Profile status does not enable automatic control; commands still require separate checks and confirmation.'),'field-help'),remove);
    actionList.append(row);summary();load(!!value.intent);
  }
  addConditionButton=btn(l('+ Điều kiện','+ Condition'),()=>addCondition());addActionButton=btn(l('+ Hành động','+ Action'),()=>addAction());
  function reset(){conditions.splice(0);actions.splice(0);conditionList.replaceChildren();actionList.replaceChildren();addCondition();addAction();}
  site.onchange=reset;
  for(const row of existing?.conditions||[{}])addCondition(row);
  for(const row of existing?.actions||[{}])addAction(row);
  const f=form(async()=>{
    if(!conditions.length||!actions.length)throw new Error(l('Thêm ít nhất một điều kiện và một hành động đề xuất.','Add at least one condition and one proposed action.'));
    if(!name.value.trim())throw new Error(l('Nhập tên quy tắc.','Enter a rule name.'));
    if(conditions.some(r=>!r.metric.value.trim()||!r.unit.value.trim()))throw new Error(l('Chọn thông số đã ghi nhận có đơn vị cho từng điều kiện.','Choose an observed metric with a unit for every condition.'));
    const data={site_id:site.value,name:name.value.trim(),description:description.value,
      conditions:conditions.map(r=>({device_id:r.device.value,metric:r.metric.value.trim(),unit:r.unit.value.trim(),comparison:r.comparison.value,threshold:Number(r.threshold.value),max_age_seconds:r.age.value===''?300:Number(r.age.value)})),
      actions:actions.map(r=>({device_id:r.device.value,intent:r.intent.value,parameters:r.read()}))};
    await api(existing?'/rules/'+encodeURIComponent(existing.id)+'/edit':'/rules',existing?{id:existing.id,revision:existing.revision||1,data}:data);
    closeDialog();await refresh();
  },l('Lưu bản nháp','Save draft'));
  f.classList.add('rule-builder');
  f.finish(notice('Tất cả điều kiện phải đúng với số đo mới, đã xác minh và đúng đơn vị. Lưu không bật theo dõi hoặc gửi lệnh. Chỉnh sửa tạm dừng theo dõi quy tắc cũ.','All conditions require fresh verified readings and exact units. Saving does not enable monitoring or send commands. Editing pauses the old rule’s monitoring.'),
    div('rule-builder-grid',card(l('1. Thông tin quy tắc','1. Rule details'),field(t('name'),name),field(t('plants'),site),field(l('Mô tả','Description'),description),review),
      card(l('2. Khi tất cả điều kiện đúng','2. When all conditions match'),conditionList,addConditionButton),
      card(l('3. Đề xuất thay đổi','3. Proposed changes'),actionList,addActionButton)));
  showDialog(l('Soạn quy tắc EMS','EMS rule editor'),f);
}
