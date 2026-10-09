import { l, t } from './i18n.js';
import { measurementChart } from './measurement-chart.js';

// Display assignments are explicitly chosen, never persisted as a canonical mapping.
export function observationPanels(ui,channels,eligible,native){
  const {div,p,card,select,field}=ui,root=div('device-mini-charts'),updates=[];
  const definitions=[
    {id:'ac',title:l('Điện AC · các kênh pha','AC electricity · phase channels'),units:['V','A'],hint:l('Chọn đúng kênh đã xác định là pha AC. Chưa có mapping thì không tự đặt tên pha A/B/C.','Choose a channel identified as an AC phase. Phase A/B/C labels are not guessed without a mapping.')},
    {id:'dc',title:l('Điện DC · các chuỗi PV','DC electricity · PV strings'),units:['V','A'],hint:l('Chọn kênh điện áp hoặc dòng của chuỗi PV để đối chiếu. Đơn vị V/A không đủ để xác định chuỗi hay MPPT.','Choose a PV string voltage or current channel to inspect. V/A units alone do not identify a string or MPPT.')},
    {id:'battery',title:l('Pin · sạc, xả và mức pin','Battery · charge, discharge and level'),units:['W','%'],hint:l('Sạc và xả giữ nguyên chiều của từng kênh; không tự đảo dấu hay cộng gộp nguồn.','Charge and discharge retain each channel’s direction; sources are not sign-inverted or aggregated.'),metrics:['battery_charge_w','battery_discharge_w','soc_pct']},
    {id:'latency',title:l('Độ trễ truyền thông','Communication latency'),units:['ms'],hint:l('Chỉ dùng số đo độ trễ đã ghi nhận. Không lấy khoảng cách giữa hai mẫu để giả làm độ trễ.','Use recorded latency observations only. Time between samples is not a latency measurement.')},
  ];
  for(const definition of definitions){
    const unit=select(definition.units.map(v=>[v,v]),definition.units[0]),pick=select([['',l('Chọn kênh đã xác định','Choose an identified channel')]],''),compare=select([['',l('Không so sánh','No comparison')]],'');
    const plot=div('device-mini-plot'),note=p('','field-help');
    const label=s=>t(s.metric)+' · '+s.unit+' · '+t(s.source||'UNKNOWN')+' · '+(s.binding_id||'—')+' · '+(s.device_id||'—');
    const choices=()=>channels.map((ss,i)=>({ss,i})).filter(({ss})=>ss[0].unit===unit.value&&(!definition.metrics||definition.metrics.includes(ss[0].metric)));
    const draw=()=>{
      const peers=choices().filter(({i})=>String(i)!==pick.value),previous=compare.value;
      compare.replaceChildren(new Option(l('Không so sánh','No comparison'),''),...peers.map(({ss,i})=>new Option(label(ss[0]),String(i))));
      compare.value=peers.some(({i})=>String(i)===previous)?previous:'';compare.disabled=pick.value===''||!peers.length;
      const main=pick.value===''?[]:channels[Number(pick.value)].filter(eligible),other=compare.value===''?[]:channels[Number(compare.value)].filter(eligible);
      plot.replaceChildren(measurementChart(main,definition.title,unit.value,{compact:true,comparison:other,allowUnverified:native()}));
      note.textContent=pick.value===''?l('Chưa chọn kênh. Lựa chọn ở đây chỉ để xem, không xác minh mapping hoặc nâng chất lượng dữ liệu.','No channel selected. Display choices do not verify mappings or upgrade data quality.'):l('Kênh chính: ','Primary channel: ')+label(channels[Number(pick.value)][0]);
    };
    const reset=()=>{
      const available=choices();pick.replaceChildren(new Option(l('Chọn kênh đã xác định','Choose an identified channel'),''),...available.map(({ss,i})=>new Option(label(ss[0]),String(i))));
      pick.value='';pick.disabled=!available.length;compare.value='';draw();
    };
    unit.onchange=reset;pick.onchange=()=>{compare.value='';draw();};compare.onchange=draw;reset();updates.push(draw);
    const panel=card(definition.title,p(definition.hint,'field-help'),field(definition.title+' · '+l('Đơn vị','Unit'),unit),
      field(definition.title+' · '+l('Kênh chính','Primary channel'),pick),field(definition.title+' · '+l('So sánh','Compare'),compare),plot,note);
    panel.dataset.observationPanel=definition.id;root.append(panel);
  }
  return {root,update:()=>updates.forEach(update=>update())};
}
