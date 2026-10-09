import { l, t, date, number } from './i18n.js';
import { measurementChart } from './measurement-chart.js';
import { observationPanels } from './observation-panels.js';

// Display selection is not a mapping or a quality upgrade.
export function deviceHistoryPanel(ui,samples,options={}) {
  const {e,div,p,card,select,field,table}=ui;
  const quality=select([['GOOD',l('Đã xác minh','Verified only')],['native',l('Kèm dữ liệu gốc chưa xác minh','Include unverified native readings')]],'GOOD');
  const period=select([['all',l('Toàn bộ dữ liệu đã tải','All loaded observations')],['1',l('1 giờ gần đây','Last hour')],['24',l('24 giờ gần đây','Last 24 hours')],['168',l('7 ngày gần đây','Last 7 days')]],'all');
  const groups=new Map();
  for(const sample of samples) {
    if(typeof sample.value!=='number'||!Number.isFinite(sample.value)||typeof sample.unit!=='string'||!sample.unit.trim()||typeof sample.metric!=='string'||!sample.metric.trim()||!Number.isFinite(Date.parse(sample.source_timestamp))||!['GOOD','UNVERIFIED'].includes(sample.quality))continue;
    const key=JSON.stringify([sample.device_id,sample.metric,sample.unit,sample.binding_id,sample.source]);
    if(!groups.has(key))groups.set(key,[]);
    groups.get(key).push(sample);
  }
  const channels=[...groups.values()].map(ss=>ss.sort((a,b)=>Date.parse(a.source_timestamp)-Date.parse(b.source_timestamp)));
  const eligible=s=>{
    const stamp=Date.parse(s.source_timestamp),now=Date.now();
    return stamp<=now+5000&&(period.value==='all'||stamp>=now-Number(period.value)*3600000)&&(s.quality==='GOOD'||quality.value==='native');
  };
  const multipleDevices=new Set(channels.map(ss=>ss[0].device_id)).size>1;
  const name=s=>t(s.metric)+' · '+s.unit+' · '+t(s.source||'UNKNOWN')+(multipleDevices?' · '+(s.device_id||'—'):'');
  const picker=select([['',l('Chọn thông số đã ghi nhận','Choose a recorded metric')],...channels.map((ss,i)=>[String(i),name(ss[0])+(ss[0].binding_id?' · '+ss[0].binding_id:'')])],channels.length?'0':'');
  const compare=select([['',l('Không so sánh','No comparison')]],'');
  const summary=div('observation-summary'),legend=div('observation-legend'),status=p('','field-help');status.setAttribute('role','status');
  const plot=div('measurement-plot-scroll'),details=e('details','','measurement-table');
  const draw=()=>{
    const primary=picker.value===''?[]:channels[Number(picker.value)]||[],selected=primary.filter(eligible),unit=primary[0]?.unit||'—';
    const prev=compare.value,peers=channels.map((ss,i)=>({ss,i})).filter(({ss,i})=>String(i)!==picker.value&&ss[0].unit===unit);
    compare.replaceChildren(new Option(l('Không so sánh','No comparison'),''),...peers.map(({ss,i})=>new Option(name(ss[0])+' · '+(ss[0].binding_id||'—'),String(i))));
    compare.value=peers.some(({i})=>String(i)===prev)?prev:'';compare.disabled=!peers.length;
    const other=compare.value===''?[]:channels[Number(compare.value)].filter(eligible);
    plot.replaceChildren(measurementChart(selected,l('Số đo theo thời gian','Observations over time'),unit,{compact:options.compact===true,comparison:other,allowUnverified:quality.value==='native'}));
    legend.replaceChildren(...[selected,other].flatMap((ss,i)=>ss.length?[div('observation-key series-'+i,e('span','','observation-swatch'),e('span',name(ss[0])+' · '+(ss[0].binding_id||'—')))]:[]));
    const values=selected.map(s=>s.value),fact=(label,value)=>div('observation-stat',e('span',label),e('strong',value));
    summary.replaceChildren(fact(l('Số đo kênh chính','Primary observations'),String(selected.length)),fact(l('Thấp nhất','Minimum'),values.length?number(Math.min(...values))+' '+unit:'—'),fact(l('Cao nhất','Maximum'),values.length?number(Math.max(...values))+' '+unit:'—'),fact(l('Mốc đo cuối','Last observation'),selected.length?date(selected.at(-1).source_timestamp):'—'));
    status.textContent=quality.value==='native'?l('Vòng tròn rỗng là dữ liệu gốc chưa xác minh, chỉ để đối chiếu; không dùng làm căn cứ điều khiển.','Hollow markers are unverified native readings for inspection only, not control inputs.'):l('Chỉ hiển thị số đo đã xác minh trong khoảng thời gian chọn.','Only verified observations in the selected time range are shown.');
    const rows=[...selected,...other].sort((a,b)=>Date.parse(b.source_timestamp)-Date.parse(a.source_timestamp));
    details.replaceChildren(e('summary',l('Xem số đo và nguồn','View observations and sources')+' ('+rows.length+')'),p(l('Tối đa 100 dòng gần nhất trong lựa chọn.','Up to 100 latest rows in this selection.'),'field-help'),table([l('Thời điểm đo','Observed at'),l('Thông số','Metric'),l('Giá trị','Value'),l('Chất lượng','Quality'),l('Nguồn / liên kết','Source / binding')],rows.slice(0,100).map(s=>[date(s.source_timestamp),t(s.metric),number(s.value)+' '+s.unit,t(s.quality),t(s.source||'UNKNOWN')+' · '+(s.binding_id||'—')])));
  };
  picker.onchange=()=>{compare.value='';draw();};compare.onchange=draw;draw();
  const panels=observationPanels(ui,channels,eligible,()=>quality.value==='native');
  const mini=panels.root;
  quality.onchange=period.onchange=()=>{draw();panels.update();};
  return div('stack device-history',card(l('Xu hướng thông số','Measurement trends'),
    p(l('Dữ liệu lưu cục bộ đã tải. Chỉ so sánh cùng đơn vị, giữ riêng nguồn; không cộng gộp hoặc điền điểm thiếu. Chưa có mapping thì không tự gán pha hay MPPT.','Loaded local observations. Compare only same-unit channels, keeping sources separate; no aggregation or gap filling. Phase and MPPT labels require an established mapping.'),'field-help'),div('observation-controls',field(l('Khoảng thời gian','Time range'),period),field(l('Chất lượng dữ liệu','Data quality'),quality),field(l('Thông số theo dõi','Observed metric'),picker),field(l('So sánh cùng đơn vị','Compare same-unit channel'),compare)),status,summary,legend,plot,details),mini);
}
