import { l } from './i18n.js';

export function registerReadingsEditor(ui,onChange=()=>{}) {
  const {e,div,p,btn,input,select,field}=ui;
  const rows=[],list=div('stack'),root=div('register-readings-editor stack');
  const empty=p(l('Chưa nhập số đo thanh ghi. Chỉ thêm giá trị đã đọc từ đúng thiết bị.','No register observations supplied. Add only values read from the identified equipment.'),'field-help');
  const add=btn(l('Thêm thanh ghi','Add register'),()=>{
    if(rows.length>=1000)return;
    const fn=select([['',l('Chọn hàm đọc','Choose read function')],['3','FC03 · Holding'],['4','FC04 · Input']],'');fn.required=true;
    const address=input('number',''),value=input('number','');
    for(const control of [address,value]){control.min='0';control.max='65535';control.step='1';control.required=true;}
    const item=div('register-reading-row'),row={fn,address,value,item};
    item.append(field(l('Hàm đọc','Read function'),fn),field(l('Địa chỉ thanh ghi','Register address'),address),field(l('Giá trị đã đọc','Observed register value'),value),btn(l('Xóa','Remove'),()=>{rows.splice(rows.indexOf(row),1);item.remove();empty.hidden=!!rows.length;add.disabled=false;onChange();}));
    list.append(item);rows.push(row);empty.hidden=true;add.disabled=rows.length>=1000;onChange();
  });
  root.append(e('h3',l('Nhập số đo thanh ghi','Supply register observations')),empty,list,add);
  root.addEventListener('input',onChange);root.addEventListener('change',onChange);
  return {root,read:()=>rows.map(({fn,address,value})=>{
    for(const control of [fn,address,value])if(!control.reportValidity())throw new Error(l('Kiểm tra hàm đọc, địa chỉ và giá trị.','Check read function, address and value.'));
    return {function:Number(fn.value),address:Number(address.value),value:Number(value.value)};
  })};
}

export function collectionEditor(ui,kind,devices,profile,fieldIds,onValidated) {
  const {e,div,p,btn,input,select,field,card,form,api}=ui;
  const fields=new Map(),layout=div('form-grid'),feedback=div('stack');
  const add=(key,vi,en,type='text',min=null,max=null,optional=false)=>{
    const control=input(type,'');control.required=!optional;
    if(type==='number'){control.step='1';if(min!==null)control.min=min;if(max!==null)control.max=max;}
    fields.set(key,control);layout.append(field(l(vi,en),control));return control;
  };
  add('agent_id','Mã bộ thu thập đã đăng ký','Registered collector ID');
  add('reviewed_by','Người kiểm tra cấu hình','Configuration reviewer');
  add('evidence_reference','Tài liệu hoặc biên bản đối chiếu','Evidence or review reference');
  const targets=()=>select([['',l('Chọn thiết bị đã lưu','Choose recorded equipment')],...devices.map(d=>[d.id,d.name||d.serial||d.id])],'');
  let target,transport,logger,bindings=[];
  const extra=div('stack');
  if(kind==='model') {
    target=targets();target.required=true;layout.append(field(l('Thiết bị đích','Target equipment'),target));
    transport=select([['',l('Chọn giao thức','Choose protocol')],['modbus_tcp','Modbus TCP'],['solarman_v5','SOLARMAN V5']],'');transport.required=true;
    layout.append(field(l('Giao thức kết nối','Connection protocol'),transport));
    add('address','Địa chỉ IP nội bộ của thiết bị','Equipment private IP address');
    add('port','Cổng kết nối đã xác nhận','Confirmed connection port','number',1,65535);
    add('unit_id','Địa chỉ thiết bị trên đường truyền','Device bus address','number',1,247);
    logger=add('logger_serial','Số sê-ri logger SOLARMAN V5','SOLARMAN V5 logger serial','number',1,4294967295,true);
    transport.onchange=()=>{logger.required=transport.value==='solarman_v5';logger.disabled=transport.value!=='solarman_v5';logger.closest('.field').hidden=logger.disabled;feedback.replaceChildren();};transport.onchange();
    for(const [key,vi,en] of [['inverter_model','Model biến tần','Inverter model'],['inverter_firmware','Phiên bản phần mềm biến tần','Inverter firmware'],['logger_model','Model bộ thu thập','Collector model'],['logger_firmware','Phiên bản phần mềm bộ thu thập','Collector firmware']])add(key,vi,en);
    extra.append(p(l('Hồ sơ model và thông số đã chọn: ','Selected model and parameters: ')+profile.name+' · '+fieldIds.length,'field-help'));
  }else{
    add('base_url','Địa chỉ máy chủ Home Assistant nội bộ','Local Home Assistant server address');
    add('max_age_seconds','Tuổi dữ liệu tối đa (giây)','Maximum observation age (seconds)','number',1,86400);
    const list=div('stack'),empty=p(l('Thêm cảm biến cần đọc và chọn thiết bị nhận dữ liệu.','Add a sensor and choose the equipment receiving its readings.'),'field-help');
    const addBinding=btn(l('Thêm cảm biến','Add sensor'),()=>{
      if(bindings.length>=100)return;
      const entity=input(),unit=input(),device=targets();entity.required=true;device.required=true;entity.pattern='sensor\\.[a-z0-9_]{1,90}';unit.maxLength=40;
      const item=div('collection-binding'),row={entity,unit,device,item};
      item.append(div('form-grid',field(l('Mã cảm biến Home Assistant','Home Assistant sensor ID'),entity),field(l('Thiết bị nhận dữ liệu','Receiving equipment'),device),field(l('Đơn vị đúng như cảm biến (bỏ trống nếu không có)','Exact sensor unit (leave blank if absent)'),unit)),btn(l('Xóa cảm biến','Remove sensor'),()=>{bindings=bindings.filter(r=>r!==row);item.remove();empty.hidden=!!bindings.length;addBinding.disabled=false;feedback.replaceChildren();}));
      bindings.push(row);list.append(item);empty.hidden=true;addBinding.disabled=bindings.length>=100;feedback.replaceChildren();
    });extra.append(e('h3',l('Cảm biến cần thu thập','Sensors to collect')),empty,list,addBinding);
  }
  const f=form(async()=>{
    const payload={};fields.forEach((control,key)=>{if(!control.disabled)payload[key]=control.type==='number'?(control.value===''?null:Number(control.value)):control.value.trim();});
    if(kind==='model')Object.assign(payload,{device_id:target.value,transport:transport.value,profile_id:profile.id,profile_digest:profile.profile_digest,field_ids:fieldIds});
    else {
      if(!bindings.length)throw new Error(l('Thêm ít nhất một cảm biến.','Add at least one sensor.'));
      payload.bindings=bindings.map(r=>({entity_id:r.entity.value.trim(),device_id:r.device.value,expected_unit:r.unit.value.trim()||null}));
    }
    const value=await api('/local-collection/'+kind+'/validate',payload);
    feedback.replaceChildren(p(l('Cấu trúc và phạm vi truy cập hợp lệ. Chưa thử kết nối thiết bị.','Structure and access scope validated. Device connectivity has not been tested.')));
    onValidated(value.config);
  },l('Kiểm tra và tải cấu hình','Validate and download configuration'));
  f.finish(layout,extra,feedback);f.querySelector('.form-actions button[type="button"]')?.remove();
  f.addEventListener('input',()=>feedback.replaceChildren());f.addEventListener('change',()=>feedback.replaceChildren());
  return card(l('Cấu hình thu thập tại chỗ','Local collection configuration'),p(l('Dành cho kỹ thuật viên. Chỉ điền thông tin đã xác nhận; không cần soạn JSON. Token được đặt trên bộ thu thập, không nhập ở đây.','For technicians. Supply confirmed details using these fields; no JSON editing. Tokens belong on the collector, not in this form.'),'field-help'),f);
}
