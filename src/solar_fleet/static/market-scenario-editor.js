import { l } from './i18n.js';
import { icon } from './icons.js';
import { metricTiles } from './ui-visuals.js';

// Explicit advisory inputs for the existing calculator, never exchange orders.
export function marketScenarioEditor(ui) {
  const {div,e,p,input,select,field,btn,notice,api}=ui;
  const root=div('stack market-scenario-editor'),fields=e('fieldset','','market-scenario-fields');
  const capacity=input('number');capacity.min='0';capacity.max='100000';capacity.step='any';
  const rows=div('stack market-bid-list'),result=div('stack'),error=p('','bad');error.setAttribute('role','alert');
  const changed=p('','field-help');changed.setAttribute('role','status');
  let bids=[],nextId=1,calculated=false;
  const invalidate=()=>{
    if(calculated){result.replaceChildren();changed.textContent=l('Đầu vào đã thay đổi. Hãy tính lại để xem kết quả mới.','Inputs changed. Calculate again for an updated result.');calculated=false;}
    error.textContent='';
  };
  fields.addEventListener('input',invalidate);fields.addEventListener('change',invalidate);
  const empty=p(l('Chưa có phương án mua / bán. Thêm một dòng để bắt đầu.','No buy / sell scenarios yet. Add a row to begin.'),'market-bid-empty');
  const add=btn(l('Thêm phương án','Add scenario'),()=>{
    if(bids.length>=1000)return;
    invalidate();
    const index=nextId++,box=e('fieldset','','market-bid-row'),label=e('legend',l('Phương án ','Scenario ')+index);
    const name=input('text'),hour=select([['',l('Chọn giờ','Choose an hour')],...Array.from({length:24},(_,h)=>[String(h),String(h).padStart(2,'0')+':00'])],'');
    const market=select([['',l('Chọn thị trường','Choose a market')],['day_ahead',l('Ngày hôm sau','Day ahead')],['intraday',l('Trong ngày','Intraday')]],'');
    const direction=select([['',l('Chọn mục đích','Choose a direction')],['buy_charge',l('Mua điện để sạc','Buy to charge')],['sell_discharge',l('Bán điện từ pin','Sell from battery')]],'');
    const quantity=input('number'),price=input('number'),clearing=input('number');
    quantity.min='0.01';quantity.max='100000';[quantity,price,clearing].forEach(n=>n.step='any');
    const row={name,hour,market,direction,quantity,price,clearing,box};
    const remove=btn(l('Bỏ phương án','Remove scenario'),()=>{invalidate();bids=bids.filter(r=>r!==row);box.remove();empty.hidden=!!bids.length;add.disabled=false;});remove.prepend(icon('trash'));
    box.append(label,div('market-bid-fields',field(l('Tên phương án','Scenario name'),name),field(l('Thị trường','Market'),market),
      field(l('Mục đích','Direction'),direction),field(l('Giờ giao dịch','Delivery hour'),hour),
      field(l('Công suất (MW)','Quantity (MW)'),quantity),field(l('Giá đề nghị (EUR/MWh)','Bid price (EUR/MWh)'),price),
      field(l('Giá thị trường giả định (EUR/MWh)','Assumed market price (EUR/MWh)'),clearing)),remove);
    bids.push(row);rows.append(box);empty.hidden=true;add.disabled=bids.length>=1000;name.focus();
  });add.prepend(icon('plus'));
  fields.append(field(l('Tổng công suất tham gia (MW)','Available capacity (MW)'),capacity),
    p(l('Đơn vị của bộ tính là MW và EUR/MWh, không phải kW hay giá điện VND. Giờ 00–23 chỉ thuộc kịch bản; chưa gắn ngày, múi giờ hoặc thị trường thật.','This calculator uses MW and EUR/MWh, not kW or VND tariffs. Hours 00–23 belong only to this scenario, without a real date, timezone or exchange.')),
    p(l('Nhập giá giả định cho mỗi giờ giao dịch. Các phương án cùng giờ phải dùng cùng một giá thị trường. Cho phép giá 0 hoặc âm khi bạn chủ động nhập.','Supply an assumed price for each trading hour. Scenarios sharing an hour must use the same market price. Explicit zero or negative prices are allowed.')),
    rows,empty,add);
  function read() {
    const value=(node,label)=>{
      if(!node.value.trim()||!Number.isFinite(Number(node.value)))throw new Error(l('Cần nhập số hợp lệ: ','Enter a valid number: ')+label);
      return Number(node.value);
    };
    const total=value(capacity,l('tổng công suất','available capacity'));
    if(total<=0||total>100000)throw new Error(l('Tổng công suất phải lớn hơn 0 và không quá 100.000 MW.','Capacity must be greater than 0 and at most 100,000 MW.'));
    if(!bids.length)throw new Error(l('Thêm ít nhất một phương án mua hoặc bán.','Add at least one buy or sell scenario.'));
    const ids=new Set(),prices={},quantities={};
    const payload=bids.map((row,i)=>{
      const id=row.name.value.trim();
      if(!id||ids.has(id))throw new Error(l('Mỗi phương án cần tên riêng, không để trống hoặc trùng tên.','Each scenario needs a unique, non-empty name.'));ids.add(id);
      if(!row.market.value||!row.direction.value||row.hour.value==='')throw new Error(l('Chọn thị trường, mục đích và giờ cho phương án ','Choose a market, direction and hour for scenario ')+(i+1));
      const hour=Number(row.hour.value),quantity=value(row.quantity,l('công suất','quantity')),
        price=value(row.price,l('giá đề nghị','bid price')),clearing=value(row.clearing,l('giá thị trường giả định','assumed market price'));
      if(quantity<0.01||quantity>100000)throw new Error(l('Công suất mỗi phương án phải từ 0,01 đến 100.000 MW.','Each quantity must be between 0.01 and 100,000 MW.'));
      if(Object.hasOwn(prices,hour)&&prices[hour]!==clearing)throw new Error(l('Các phương án cùng giờ phải dùng cùng giá thị trường giả định.','Scenarios sharing an hour must use the same assumed market price.'));
      prices[hour]=clearing;quantities[hour]=(quantities[hour]||0)+quantity;
      if(quantities[hour]>total)throw new Error(l('Tổng công suất các phương án cùng giờ vượt công suất tham gia.','Combined quantities in an hour exceed available capacity.'));
      return {id,market:row.market.value,direction:row.direction.value,delivery_hour:hour,quantity_mw:quantity,price_eur_per_mwh:price};
    });
    return {fleet_capacity_mw:total,bids:payload,clearing_prices:prices};
  }
  const calculate=btn(l('Tính kịch bản từ dữ liệu nhập','Calculate supplied market scenario'),async()=>{
    error.textContent='';
    try {
      const payload=read();fields.disabled=true;calculate.disabled=true;root.setAttribute('aria-busy','true');
      result.replaceChildren();calculated=false;changed.textContent=l('Đang tính ước tính…','Calculating estimate…');
      const response=await api('/market-trader/submit-and-clear',payload);
      result.replaceChildren(metricTiles(ui,[['coins',l('Giá trị ròng ước tính (EUR)','Estimated net value (EUR)'),response.net_market_settlement_eur],
        ['check',l('Phương án có thể khớp','Estimated cleared bids'),response.cleared_bids],
        ['alert',l('Phương án không khớp','Estimated rejected bids'),response.rejected_bids],
        ['fileText',l('Số phương án đã nhập','Input bids'),response.total_bids]]));
      calculated=true;changed.textContent=l('Đã tính từ đầu vào bạn nhập. Không có giao dịch thật.','Calculated from supplied inputs. No real trade occurred.');
    } catch(err){error.textContent=err.message;changed.textContent='';}
    finally {fields.disabled=false;calculate.disabled=false;root.removeAttribute('aria-busy');}
  },'primary');
  root.append(notice('Chỉ ước tính theo dữ liệu bạn nhập; không gửi lệnh ra thị trường, không thanh toán hoặc điều khiển thiết bị.','Estimates supplied inputs only; no exchange order, settlement or equipment control.'),
    fields,error,calculate,changed,result);
  return root;
}
