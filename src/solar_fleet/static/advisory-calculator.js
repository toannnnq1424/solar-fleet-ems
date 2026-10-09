import { l, number } from './i18n.js';
import { calculationFields } from './calculation-fields.js';

const titles={
  'Grid response estimate':['Ước tính đáp ứng lưới','Grid response estimate'],
  'Heat pump estimate':['Ước tính hiệu suất bơm nhiệt','Heat pump estimate'],
  'SG-ready recommendation':['Khuyến nghị vận hành bơm nhiệt','SG-ready recommendation'],
  'Genset dispatch estimate':['Ước tính vận hành máy phát','Genset dispatch estimate'],
  'Black-start scenario':['Kịch bản khôi phục nguồn điện','Black-start scenario'],
};
export function advisoryCalculator(ui,title,endpoint) {
  const {div,e,p,btn,card,notice,table}=ui;
  const output=div('stack calculation-result');output.setAttribute('aria-live','polite');
  const fields=calculationFields(ui,endpoint,()=>output.replaceChildren());
  const value=(v,unit='')=>v==null?'—':number(v)+(unit?' '+unit:'');
  const run=btn(l('Tính toán từ thông số','Calculate supplied inputs'),async()=>{
    output.replaceChildren();
    let body;
    try{body=fields.read();}catch(err){output.append(p(err.message,'bad'));return;}
    fields.root.disabled=run.disabled=clear.disabled=true;
    try {
      const result=await ui.api(endpoint,body),rows=[];
      if(result.allow_inverter_run!==undefined)rows.push(
        [l('Đề xuất theo mô hình','Model recommendation'),result.allow_inverter_run?l('Cho phép chạy','Allow running'):l('Ngắt bảo vệ','Protection trip')],
        [l('Công suất tác dụng mục tiêu','Target active power'),value(result.target_p_kw,'kW')],
        [l('Công suất phản kháng mục tiêu','Target reactive power'),value(result.target_q_kvar,'kvar')],
        [l('Giảm theo điện áp','Voltage curtailment'),value(result.volt_watt_curtailment_kw,'kW')],
        [l('Giảm theo tần số','Frequency curtailment'),value(result.freq_watt_curtailment_kw,'kW')]);
      if(result.cop!==undefined)rows.push([l('Hệ số hiệu quả nhiệt (COP)','Coefficient of performance (COP)'),value(result.cop)],[l('Công suất điện','Electric power'),value(result.electric_power_kw,'kW')],[l('Công suất nhiệt','Thermal power'),value(result.thermal_power_kw,'kW')]);
      if(result.sg_ready_state!==undefined)rows.push([l('Trạng thái đề xuất SG-Ready','Proposed SG-ready state'),({1:l('Tạm khóa','Locked'),2:l('Bình thường','Normal'),3:l('Tăng nhiệt từ điện dư','Surplus heating'),4:l('Tăng nhiệt cưỡng bức','Forced heating')})[result.sg_ready_state]||'—'],[l('Nhiệt độ mục tiêu','Target temperature'),value(result.target_tank_temp_c,'°C')]);
      if(result.dispatch)rows.push([l('Công suất máy phát đề xuất','Proposed generator power'),value(result.dispatch.output_power_kw,'kW')],[l('Kết quả','Result'),l('Đã tính kịch bản; xem chi tiết kỹ thuật bên dưới.','Scenario calculated; see technical details below.')]);
      if(Array.isArray(result.event_log))rows.push([l('Số bước trong kịch bản','Scenario steps'),String(result.event_log.length)],[l('Phạm vi kết quả','Result scope'),l('Chỉ mô phỏng; không có thiết bị được khởi động.','Simulation only; no equipment was started.')]);
      const details=e('details','','raw-details');details.append(e('summary',l('Chi tiết kỹ thuật của phép tính','Calculation technical details')),e('pre',JSON.stringify(result,null,2),'code-block'));
      output.append(notice('Ước tính từ thông số bạn nhập; không xác nhận tuân thủ, không gửi lệnh thiết bị.','Estimate from supplied inputs; not compliance verification, no equipment commands.'),table([l('Chỉ số','Metric'),l('Kết quả','Result')],rows),details);
    }catch(err){output.replaceChildren(p(err.message,'bad'));}
    finally{fields.root.disabled=run.disabled=clear.disabled=false;}
  },'primary');
  const clear=btn(l('Xóa trắng','Clear'),()=>{
    fields.root.querySelectorAll('input,select').forEach(c=>{c.value='';});output.replaceChildren();
  });
  const root=card(l(...(titles[title]||[title,title])),
    p(l('Nhập số đo và thông số đã xác nhận. Không có giá trị mẫu được điền sẵn. Đây là công cụ kỹ thuật tham khảo, không cài đặt cho thiết bị.','Supply confirmed observations and equipment specifications. No example values are prefilled. This is a technical advisory tool, not a device configuration.')),
    fields.root,div('form-actions',run,clear),output);
  root.classList.add('advisory-calculator');root.dataset.calculator=endpoint;
  return root;
}
