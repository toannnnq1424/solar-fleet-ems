import { l } from './i18n.js';

// Field definitions contain labels/constraints only, never example observations.
const n=(key,vi,en,unit='',min=null,max=null)=>({key,vi,en,unit,min,max});
const pct=(key,vi,en)=>({...n(key,vi,en,'%',0,100),ratio:true});
const choice=(key,vi,en,options)=>({key,vi,en,options});
const yesno=(key,vi,en)=>({...choice(key,vi,en,[['true','Có','Yes'],['false','Không','No']]),boolean:true});
const text=(key,vi,en,optional=false)=>({key,vi,en,type:'text',optional});
const time=(key,vi,en)=>({...text(key,vi.replace(' (ISO 8601 có múi giờ)',''),en.replace(' (ISO 8601 with timezone)',''),true),type:'datetime-local',timestamp:true});
const group=(key,vi,en,fields)=>({key,vi,en,fields});
const sequence=(key,vi,en,fields,max)=>({...group(key,vi,en,fields),repeated:true,max});
const specs=[n('rated_power_kw','Công suất định mức','Rated power','kW',0),pct('min_loading_ratio','Tải tối thiểu','Minimum loading'),pct('optimal_loading_ratio','Tải tối ưu','Optimal loading'),pct('max_loading_ratio','Tải tối đa','Maximum loading'),
  n('fuel_idle_liters_per_hour','Nhiên liệu không tải','Idle fuel consumption','L/h',0),n('fuel_slope_liters_per_kwh','Nhiên liệu theo điện phát','Fuel per generated energy','L/kWh',0),
  ...[['warmup_time_seconds','Thời gian làm nóng','Warm-up'],['crank_time_seconds','Thời gian đề máy','Cranking'],['cooldown_time_seconds','Thời gian làm mát','Cool-down'],['min_run_time_seconds','Thời gian chạy tối thiểu','Minimum runtime']].map(([key,vi,en])=>({...n(key,vi,en,'s',0),integer:true})),
  n('auto_start_soc_threshold','Mức pin để khởi động','Start battery level','%',0,100),n('auto_stop_soc_threshold','Mức pin để dừng','Stop battery level','%',0,100)];
const voltageCurve=()=>[n('nominal_voltage_v','Điện áp danh định','Nominal voltage','V',0),...[1,2,3,4].map(i=>n('v'+i+'_v','Ngưỡng điện áp '+i,'Voltage threshold '+i,'V',0))];
const chargerFields=[text('id','Mã trạm sạc','Charger ID'),text('name','Tên trạm sạc','Charger name'),text('vehicle_id','Mã xe (nếu có)','Vehicle ID (if connected)',true),
  {...n('soc_pct','Mức pin hiện tại','Current battery level','%',0,100),optional:true},n('target_soc_pct','Mức pin mong muốn','Target battery level','%',0,100),
  choice('mode','Chế độ sạc','Charging mode',[['off','Tắt','Off'],['now','Sạc ngay','Charge now'],['min_pv','Sạc tối thiểu và dùng điện mặt trời','Minimum charge plus solar'],['pv','Chỉ điện mặt trời','Solar only']]),
  {...n('priority','Mức ưu tiên (1 cao nhất)','Priority (1 highest)','',1,5),integer:true},n('min_current_amps','Dòng sạc tối thiểu','Minimum charging current','A',0,1000),n('max_current_amps','Dòng sạc tối đa','Maximum charging current','A',0,1000),n('voltage_per_phase_v','Điện áp mỗi pha','Voltage per phase','V',0,1000),
  {...choice('phases','Số pha đã cấu hình','Configured phases',[['1','Một pha','Single phase'],['3','Ba pha','Three phase']]),numeric:true},time('observed_at','Thời điểm đo trạm sạc (ISO 8601 có múi giờ)','Charger observation time (ISO 8601 with timezone)')];

export const calculationSchemas={
  '/thermal/heat-pump-cop':[n('ambient_temp_c','Nhiệt độ môi trường','Ambient temperature','°C',-273.14),n('supply_temp_c','Nhiệt độ cấp','Supply temperature','°C',-273.14),n('required_thermal_kw','Nhu cầu nhiệt','Required heat','kW',0),pct('carnot_efficiency','Hiệu suất Carnot','Carnot efficiency'),n('min_electric_kw','Công suất điện tối thiểu','Minimum electric power','kW',0),n('max_electric_kw','Công suất điện tối đa','Maximum electric power','kW',0)],
  '/thermal/sg-ready-evaluate':[n('pv_surplus_kw','Điện mặt trời dư','Solar surplus','kW',0),n('grid_price','Giá điện khai báo (cùng đơn vị với mô hình)','Declared electricity price (model units)'),yesno('is_grid_peak_lock','Đang khóa trong giờ cao điểm','Peak-time lock active'),n('surplus_threshold_kw','Ngưỡng dư để tăng nhiệt','Surplus threshold','kW',0),n('forced_surplus_kw','Ngưỡng dư để chạy cưỡng bức','Forced surplus threshold','kW',0),n('tank_temp_c','Nhiệt độ bồn hiện tại','Current tank temperature','°C',-273.14),n('min_temp_c','Nhiệt độ tối thiểu','Minimum temperature','°C',-273.14),n('normal_setpoint_c','Nhiệt độ mục tiêu thường','Normal target temperature','°C',-273.14),n('boost_setpoint_c','Nhiệt độ mục tiêu tăng cường','Boost target temperature','°C',-273.14)],
  '/grid-code/evaluate':[group('', 'Số đo hiện tại','Current observations',[n('voltage_v','Điện áp','Voltage','V',0),n('frequency_hz','Tần số','Frequency','Hz',0),n('current_power_kw','Công suất hiện tại','Current power','kW',0)]),
    group('volt_watt','Đường cong điện áp – công suất','Voltage–active power curve',[...voltageCurve(),n('p_rated_kw','Công suất định mức','Rated active power','kW',0),{...pct('min_power_ratio','Tỷ lệ công suất tối thiểu','Minimum power ratio'),max:50}]),
    group('volt_var','Đường cong điện áp – phản kháng','Voltage–reactive power curve',[...voltageCurve(),pct('q_max_ratio','Tỷ lệ phản kháng tối đa','Maximum reactive ratio'),n('rated_kva','Công suất biểu kiến định mức','Rated apparent power','kVA',0)]),
    group('freq_watt','Đáp ứng tần số','Frequency response',[n('nominal_freq_hz','Tần số danh định','Nominal frequency','Hz',0),n('over_freq_threshold_hz','Ngưỡng quá tần','Over-frequency threshold','Hz',0),n('under_freq_threshold_hz','Ngưỡng thấp tần','Under-frequency threshold','Hz',0),n('droop_pct','Độ dốc điều chỉnh','Droop','%',0,100),n('p_rated_kw','Công suất định mức','Rated active power','kW',0)]),
    group('protection','Ngưỡng bảo vệ để tính tham khảo','Advisory protection thresholds',[n('v_min_trip_v','Ngắt khi điện áp thấp','Low-voltage trip','V',0),n('v_max_trip_v','Ngắt khi điện áp cao','High-voltage trip','V',0),n('f_min_trip_hz','Ngắt khi tần số thấp','Low-frequency trip','Hz',0),n('f_max_trip_hz','Ngắt khi tần số cao','High-frequency trip','Hz',0)])],
  '/phase-balancer/dispatch':[group('measurement','Số đo ba pha','Three-phase measurements',['v','i','p','q'].flatMap((prefix)=>[1,2,3].map(i=>n(prefix+'_l'+i,({v:'Điện áp',i:'Dòng điện',p:'Công suất tác dụng',q:'Công suất phản kháng'})[prefix]+' L'+i,({v:'Voltage',i:'Current',p:'Active power',q:'Reactive power'})[prefix]+' L'+i,({v:'V',i:'A',p:'kW',q:'kvar'})[prefix],['v','i'].includes(prefix)?0:null)))),
    group('limits','Giới hạn thiết bị đã xác nhận','Confirmed equipment limits',[n('max_total_kw','Tổng công suất tối đa','Maximum total power','kW',0),n('max_phase_kw','Công suất tối đa mỗi pha','Maximum power per phase','kW',0),n('max_phase_kvar','Phản kháng tối đa mỗi pha','Maximum reactive power per phase','kvar',0),n('battery_max_charge_kw','Công suất sạc pin tối đa','Maximum battery charging power','kW',0),n('battery_max_discharge_kw','Công suất xả pin tối đa','Maximum battery discharging power','kW',0),yesno('allows_independent_phases','Thiết bị hỗ trợ điều chỉnh độc lập từng pha','Equipment supports independent phase control')])],
  '/ev-fleet/optimize-dlm':[group('', 'Thông số công trình','Site inputs',[n('site_breaker_limit_kw','Giới hạn Aptomat tổng trạm','Main Breaker Limit','kW',0,100000),n('available_solar_surplus_kw','Điện mặt trời dư thừa','Solar Surplus Available','kW',0,100000),n('building_base_load_kw','Phụ tải cơ sở tòa nhà','Base Building Load','kW',0,100000),time('observed_at','Thời điểm đo site (ISO 8601 có múi giờ)','Site observation time (ISO 8601 with timezone)')]),sequence('chargers','Trạm sạc','Chargers',chargerFields,100)],
  '/genset/evaluate-dispatch':[group('specs','Thông số máy phát','Generator specifications',specs),group('', 'Điều kiện tính toán','Calculation conditions',[
    choice('initial_state','Trạng thái ban đầu','Initial state',[['off','Tắt','Off'],['cranking','Đang đề máy','Cranking'],['warmup','Làm nóng','Warm-up'],['running_loaded','Đang chạy có tải','Running with load'],['cooldown','Làm mát','Cool-down'],['fault','Lỗi','Fault'],['locked_out','Bị khóa','Locked out']]),
    ...[['elapsed_in_state_seconds','Thời gian trong trạng thái hiện tại','Time in current state'],['cumulative_run_seconds','Thời gian chạy tích lũy','Cumulative runtime'],['dt_seconds','Bước thời gian tính toán','Calculation time step']].map(([key,vi,en])=>({...n(key,vi,en,'s',0),integer:true})),
    n('microgrid_load_kw','Phụ tải vi lưới','Microgrid load','kW',0),n('battery_soc_pct','Mức pin hiện tại','Current battery level','%',0,100),yesno('is_grid_available','Có điện lưới','Grid available'),n('battery_max_charge_kw','Công suất sạc pin tối đa','Maximum battery charging power','kW',0),n('battery_max_discharge_kw','Công suất xả pin tối đa','Maximum battery discharging power','kW',0)])],
  '/genset/black-start-sequence':[group('specs','Thông số máy phát','Generator specifications',specs),sequence('observations','Các bước quan sát theo thứ tự','Ordered observation steps',[n('bus_voltage_v','Điện áp thanh cái','Bus voltage','V',0),n('pv_frequency_hz','Tần số điện mặt trời','PV frequency','Hz',0,100),n('critical_load_kw','Phụ tải ưu tiên','Critical load','kW',0)],7)],
};

export function calculationFields(ui,endpoint,onChange=()=>{}) {
  const {e,div,field,input,select,btn,p}=ui;
  const root=e('fieldset','','calculation-fields');
  root.addEventListener('input',onChange);root.addEventListener('change',onChange);
  function build(specs,parent,path='') {
    const reads=[];
    for(const s of specs) {
      const label=l(s.vi,s.en)+(s.unit?' ('+s.unit+')':'');
      const keyPath=path+(s.key? s.key+'.':'');
      if(s.fields) {
        const section=div('calculation-section',e('h3',label));parent.append(section);
        if(s.repeated) {
          const rows=[],list=div('stack'),empty=p(l('Chưa có mục nào. Thêm và nhập thông số của bạn.','No entries. Add an entry and supply your own values.'),'field-help');
          const add=btn(l('Thêm mục','Add entry'),()=>{
            if(rows.length>=s.max)return;
            const node=div('calculation-entry'),grid=div('form-grid');
            const row={node,read:build(s.fields,grid,keyPath)};
            const remove=btn(l('Xóa mục','Remove entry'),()=>{rows.splice(rows.indexOf(row),1);node.remove();empty.hidden=!!rows.length;add.disabled=false;onChange();});
            node.append(div('card-head',e('h3',label),remove),grid);list.append(node);rows.push(row);empty.hidden=true;add.disabled=rows.length>=s.max;onChange();
          });
          section.append(empty,list,add);
          reads.push(result=>{if(!rows.length)throw new Error(l('Cần thêm ít nhất một mục: ','Add at least one entry: ')+label);result[s.key]=rows.map(r=>r.read());});
        } else {
          const grid=div('form-grid');section.append(grid);const read=build(s.fields,grid,keyPath);
          reads.push(result=>{if(s.key)result[s.key]=read();else Object.assign(result,read());});
        }
      } else {
        const c=s.options?select([['',l('Chọn…','Choose…')],...s.options.map(([v,vi,en])=>[v,l(vi,en)])],''):input(s.type||'number','');
        c.dataset.inputPath=keyPath.slice(0,-1);c.required=!s.optional;
        if(!s.options&&!s.type){c.step=s.integer?'1':'any';if(s.min!=null)c.min=s.min;if(s.max!=null)c.max=s.max;}
        if(s.timestamp)c.step='1';
        const wrapper=field(label,c);parent.append(wrapper);
        if(s.timestamp)wrapper.append(p(l('Giờ trên máy của bạn: ','Your computer timezone: ')+Intl.DateTimeFormat().resolvedOptions().timeZone+l('. Bỏ trống nếu chưa biết.','. Leave blank if unknown.'),'field-help'));
        reads.push(result=>{
          if(!c.reportValidity())throw new Error(l('Kiểm tra trường: ','Check field: ')+label);
          const value=c.value.trim();if(!value&&s.optional){result[s.key]=null;return;}
          if(s.timestamp&&value&&!Number.isFinite(Date.parse(value)))throw new Error(l('Thời điểm không hợp lệ: ','Invalid observation time: ')+label);
          result[s.key]=s.timestamp?new Date(value).toISOString():s.boolean?value==='true':s.type?value:s.options&&!s.numeric?value:Number(value)/(s.ratio?100:1);
        });
      }
    }
    return ()=>{const result={};reads.forEach(read=>read(result));return result;};
  }
  const schema=calculationSchemas[endpoint];if(!schema)throw new Error('Unknown calculation schema');
  const read=build(schema,root);
  return {root,read};
}
