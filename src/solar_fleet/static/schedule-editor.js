import { l, t } from './i18n.js';
import { icon } from './icons.js';
import { scheduleWeekGrid } from './schedule-week-grid.js';

const modes=['self_use','charge','discharge','hold'];
const minutes=value=>/^(?:[01]\d|2[0-3]):[0-5]\d$|^24:00$/.test(value||'')?Number(value.slice(0,2))*60+Number(value.slice(3)):NaN;
const time=value=>String(Math.floor(value/60)).padStart(2,'0')+':'+String(value%60).padStart(2,'0');
const clone=slots=>slots.map(slot=>({...slot}));

export function validateDraftSlots(slots) {
  if(!slots.length||slots.length>168)throw new Error(l('Lịch cần từ 1 đến 168 khung giờ.','A schedule needs 1–168 time slots.'));
  for(const slot of slots) {
    if(!Number.isInteger(slot.day)||slot.day<0||slot.day>6||!modes.includes(slot.mode)||
       !Number.isFinite(minutes(slot.start))||!Number.isFinite(minutes(slot.end))||minutes(slot.start)>=minutes(slot.end))
      throw new Error(l('Chọn ngày, chế độ và giờ kết thúc sau giờ bắt đầu. Lịch qua đêm cần tách tại 24:00.','Choose a day, mode and an end time after the start. Split overnight periods at 24:00.'));
    if(slot.target_soc!=null&&(!Number.isInteger(slot.target_soc)||slot.target_soc<0||slot.target_soc>100))
      throw new Error(l('Mức pin phải là số nguyên từ 0 đến 100%.','Battery target must be a whole percentage from 0 to 100.'));
    if(slot.power_kw!=null&&(!Number.isFinite(slot.power_kw)||slot.power_kw<0||slot.power_kw>1000000))
      throw new Error(l('Công suất phải là số từ 0 đến 1.000.000 kW.','Power must be between 0 and 1,000,000 kW.'));
  }
  const sorted=[...slots].sort((a,b)=>a.day-b.day||minutes(a.start)-minutes(b.start));
  if(sorted.some((slot,i)=>i&&sorted[i-1].day===slot.day&&minutes(slot.start)<minutes(sorted[i-1].end)))
    throw new Error(l('Các khung giờ đang chồng lấn. Bản nháp chưa thay đổi; hãy chọn giờ khác.','Time slots overlap. The draft is unchanged; choose another time.'));
  return sorted;
}

// This editor only uses the existing draft endpoints. No compilation or command sends.
export function openScheduleEditor(ui, existing=null, initial=null) {
  const {state,e,div,p,btn,card,input,select,field,notice,form,api,siteSelect,showDialog,closeDialog,refresh,toast}=ui;
  if(!state.fleet.sites.length){toast(l('Thêm nhà máy trước khi tạo lịch.','Add a plant before creating a schedule.'));return;}
  const days=[l('Thứ 2','Monday'),l('Thứ 3','Tuesday'),l('Thứ 4','Wednesday'),l('Thứ 5','Thursday'),l('Thứ 6','Friday'),l('Thứ 7','Saturday'),l('Chủ nhật','Sunday')];
  let slots=clone(existing?.slots||[]),history=[],active=null,pending=false,conflict=false,moveIndex=null;
  const name=input('text',existing?.name||''),site=siteSelect(existing?.site_id);
  name.required=true;name.maxLength=120;site.disabled=!!existing;
  const matrix=div('schedule-editor-matrix'),inspector=div('schedule-slot-inspector'),message=p('','schedule-editor-message');
  message.setAttribute('role','status');
  const count=e('span','','muted'),zone=e('span','','muted');
  const zoneText=()=>{zone.textContent=l('Múi giờ: ','Timezone: ')+(existing?.timezone||state.fleet.sites.find(s=>s.id===site.value)?.timezone||l('Chưa khai báo','Not recorded'));};
  site.onchange=zoneText;zoneText();
  function announce(text,bad=false){message.textContent=text;message.classList.toggle('bad',bad);}
  function attempt(action){try{action();}catch(error){announce(error.message,true);}}
  function commit(next,text){history.push(clone(slots));slots=clone(next);pending=false;active=null;moveIndex=null;draw();announce(text);}
  const undo=btn(l('Hoàn tác','Undo'),()=>{if(!history.length)return;slots=history.pop();pending=false;active=null;moveIndex=null;draw();announce(l('Đã hoàn tác trên bản nháp.','Draft change undone.'));});undo.prepend(icon('refresh'));
  function selectSlot(context={day:0,start:'',end:'',slotIndex:-1}) {
    if(pending){announce(l('Cập nhật hoặc hủy khung đang chỉnh trước khi chọn khung khác.','Update or cancel the current slot before selecting another.'),true);return;}
    active=context.slotIndex>=0?context.slotIndex:-1;
    const value=active>=0?slots[active]:context;
    const day=select(days.map((label,i)=>[String(i),label]),String(value.day));
    const start=input('time',value.start||''),end=input('text',value.end||'');end.placeholder='24:00';
    const mode=select([['',l('Chọn chế độ','Choose a mode')],...modes.map(m=>[m,t(m)])],value.mode||'');
    const soc=input('number',value.target_soc??''),power=input('number',value.power_kw??'');
    soc.min='0';soc.max='100';soc.step='1';power.min='0';power.max='1000000';power.step='any';
    [day,start,end,mode,soc,power].forEach(n=>{n.oninput=()=>{pending=true;};});
    pending=active<0;
    const apply=btn(l('Cập nhật vào lịch nháp','Update draft slot'),()=>attempt(()=>{
      const slot={day:Number(day.value),start:start.value,end:end.value,mode:mode.value,
        target_soc:soc.value===''?null:Number(soc.value),power_kw:power.value===''?null:Number(power.value)};
      const next=clone(slots);if(active>=0)next[active]=slot;else next.push(slot);
      validateDraftSlots(next);commit(next,l('Đã cập nhật bản nháp; chưa lưu.','Draft updated; not saved.'));
    }),'primary');
    const remove=active>=0?btn(l('Xóa khung giờ','Remove time slot'),()=>commit(slots.filter((_,i)=>i!==active),l('Đã bỏ khung giờ khỏi bản nháp. Có thể hoàn tác.','Slot removed from draft. Undo is available.')),'danger'):null;
    const relocate=active>=0?btn(l('Chọn ô để chuyển khung này','Choose a cell to move this slot'),()=>{
      if(pending){announce(l('Cập nhật hoặc hủy thay đổi trước khi chuyển khung.','Update or cancel changes before moving the slot.'),true);return;}
      moveIndex=active;draw();announce(l('Chạm hoặc chọn ô đích bằng bàn phím. Chỉ thay đổi bản nháp.','Tap or keyboard-select a destination cell. Only the draft changes.'));
    }):null;
    inspector.replaceChildren(card(active>=0?l('Chỉnh khung giờ','Edit time slot'):l('Thêm khung giờ','Add time slot'),
      field(l('Ngày','Day'),day),div('form-grid',field(l('Từ','From'),start),field(l('Đến','To'),end)),field(l('Chế độ','Mode'),mode),
      field(l('Mức pin mục tiêu (%)','Target battery level (%)'),soc),field(l('Công suất (kW)','Power (kW)'),power),
      p(l('Mức pin và công suất có thể để trống. 24:00 là cuối ngày; các giá trị là yêu cầu của bản nháp, chưa phải thiết lập trên máy.','Battery target and power are optional. 24:00 ends the day; values are draft requests, not device settings.')),
      div('stack',apply,relocate,remove,btn(l('Hủy chỉnh khung','Cancel slot edit'),()=>{pending=false;active=null;draw();announce('');}))));
    if(matchMedia('(max-width:1100px)').matches)requestAnimationFrame(()=>inspector.scrollIntoView({block:'nearest'}));
  }
  function move(context){attempt(()=>{
    if(pending)throw new Error(l('Hoàn tất khung đang chỉnh trước khi kéo lịch.','Finish the current edit before moving a slot.'));
    const slot=slots[context.slotIndex];if(!slot)return;
    const end=minutes(context.start)+minutes(slot.end)-minutes(slot.start);
    if(end>1440)throw new Error(l('Khung giờ vượt qua nửa đêm. Chọn vị trí sớm hơn hoặc tách lịch.','The slot would cross midnight. Choose an earlier position or split it.'));
    const next=clone(slots);next[context.slotIndex]={...slot,day:context.day,start:context.start,end:time(end)};
    validateDraftSlots(next);commit(next,l('Đã chuyển khung giờ trên bản nháp; chưa lưu.','Slot moved in draft; not saved.'));
  });}
  function resize(context){attempt(()=>{
    if(pending)throw new Error(l('Hoàn tất khung đang chỉnh trước khi đổi độ dài.','Finish the current edit before resizing.'));
    const next=clone(slots);if(!next[context.slotIndex])return;
    next[context.slotIndex][context.boundary]=context.time;
    validateDraftSlots(next);commit(next,l('Đã đổi độ dài khung trên bản nháp; chưa lưu.','Slot resized in draft; not saved.'));
    matrix.querySelector(`.week-resize[data-slot-index="${context.slotIndex}"][data-boundary="${context.boundary}"]`)?.focus();
  });}
  const from=select(days.map((day,i)=>[String(i),day]),'0'),targets=days.map((day,i)=>{
    const control=input('checkbox');return {control,element:field(day,control),day:i};
  });
  const replace=input('checkbox');
  const copy=btn(l('Sao chép ngày đã chọn','Copy selected day'),()=>attempt(()=>{
    if(pending)throw new Error(l('Hoàn tất khung đang chỉnh trước khi sao chép.','Finish the current edit before copying.'));
    const selected=targets.filter(r=>r.control.checked).map(r=>r.day),source=slots.filter(s=>s.day===Number(from.value));
    if(!source.length)throw new Error(l('Ngày nguồn chưa có lịch. Không có dữ liệu để sao chép.','The source day has no slots to copy.'));
    if(!selected.length||selected.includes(Number(from.value)))throw new Error(l('Chọn ngày đích khác ngày nguồn.','Select target days other than the source day.'));
    const next=replace.checked?slots.filter(s=>!selected.includes(s.day)):clone(slots);
    selected.forEach(day=>source.forEach(s=>next.push({...s,day})));validateDraftSlots(next);
    commit(next,l('Đã sao chép vào bản nháp; chưa lưu.','Copied to draft; not saved.'));
  }));copy.prepend(icon('copy'));
  const copyDetails=e('details','','schedule-copy-panel');
  copyDetails.append(e('summary',l('Sao chép lịch từ một ngày','Copy a day’s schedule')),
    field(l('Ngày nguồn','Source day'),from),div('schedule-copy-days',...targets.map(r=>r.element)),
    field(l('Thay toàn bộ lịch ở những ngày đích đã chọn','Replace all slots on the selected target days'),replace),
    p(l('Mặc định chỉ thêm khung không chồng lấn. Chọn thay toàn bộ chỉ khi muốn bỏ lịch cũ của ngày đích.','By default only non-overlapping slots are added. Replacement removes existing slots on the selected days.')),copy);
  function draw(){
    undo.disabled=!history.length;count.textContent=slots.length+' '+l('khung giờ trong bản nháp','draft slots');
    matrix.replaceChildren(scheduleWeekGrid(ui,slots,days,context=>moveIndex==null?selectSlot(context):move({...context,slotIndex:moveIndex}),{onMove:move,onResize:resize}));
    if(moveIndex!=null){
      inspector.replaceChildren(card(l('Chọn vị trí mới','Choose a destination'),icon('move'),
        p(l('Chọn ô ở ngày và giờ muốn chuyển đến. Giữ nguyên độ dài, chế độ, mức pin và công suất. Khung chồng lấn sẽ bị từ chối.','Choose the destination day and start time. Duration, mode, battery target and power stay unchanged. Overlaps are rejected.')),
        btn(l('Hủy chuyển khung','Cancel move'),()=>{moveIndex=null;active=null;draw();announce('');})));
      return;
    }
    inspector.replaceChildren(card(l('Chỉnh lịch trong tuần','Edit the week'),icon('calendar'),
      p(l('Chọn ô để thêm hoặc sửa. Kéo khung trên máy tính, hoặc chọn “Chọn ô để chuyển khung này” để dùng cảm ứng/bàn phím. Kéo mép trên/dưới để đổi độ dài; phím lên/xuống đổi 15 phút.','Select a cell to add or edit. Drag on desktop, or use “Choose a cell to move this slot” with touch/keyboard. Drag the top/bottom edge to resize; Up/Down changes 15 minutes.')),
      btn(l('+ Thêm khung giờ','+ Add slot'),()=>selectSlot(), 'secondary')));
  }
  const f=form(async()=>{
    if(conflict)throw new Error(l('Đóng và mở lại lịch để tải phiên bản mới trước khi lưu.','Close and reopen the schedule to load its latest revision before saving.'));
    if(pending)throw new Error(l('Cập nhật hoặc hủy khung đang chỉnh trước khi lưu lịch.','Update or cancel the current slot before saving the schedule.'));
    if(moveIndex!=null)throw new Error(l('Chọn ô đích hoặc hủy chuyển khung trước khi lưu.','Choose a destination or cancel the move before saving.'));
    const data={name:name.value.trim(),site_id:site.value,slots:validateDraftSlots(slots)};
    if(!data.name)throw new Error(l('Nhập tên lịch.','Enter a schedule name.'));
    try {await api(existing?`/schedules/${existing.id}/edit`:'/schedules',existing?{id:existing.id,revision:existing.revision||1,data}:data);}
    catch(error){if(/revision|changed|conflict|stale/i.test(error.message))conflict=true;throw error;}
    closeDialog();await refresh();
  },l('Lưu bản nháp','Save draft'));
  f.classList.add('schedule-editor');
  f.finish(div('form-grid',field(t('name'),name),field(t('plants'),site)),
    notice('Chỉ lưu lịch nháp. Không tự bật EMS, điều khiển thiết bị hoặc thay đổi lịch đang chạy.','Saves a draft only. Does not enable EMS, command equipment or change a running schedule.'),
    div('schedule-editor-toolbar',zone,count,undo),message,
    div('schedule-editor-layout',div('stack',matrix,copyDetails),inspector));
  draw();if(initial)selectSlot(initial);
  showDialog(existing?l('Chỉnh lịch sạc / xả','Edit charge / discharge schedule'):l('Tạo lịch sạc / xả','Create charge / discharge schedule'),f);
}
