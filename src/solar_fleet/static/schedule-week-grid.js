import { l, t } from './i18n.js';

// Structural hour bands are a time axis, never fabricated schedule slots.
export function scheduleWeekGrid(ui, slots, days, edit, options = {}) {
  const {e, div, btn} = ui;
  const minute = value => typeof value === 'string' && /^(?:[01]\d|2[0-3]):[0-5]\d$|^24:00$/.test(value)
    ? Number(value.slice(0,2))*60+Number(value.slice(3)) : NaN;
  const valid=slots.filter(s=>Number.isInteger(s.day)&&s.day>=0&&s.day<7&&minute(s.start)<minute(s.end));
  const bounds=[...new Set(valid.length ? [0,1440,...valid.flatMap(s=>[minute(s.start),minute(s.end)])] : [0,240,480,720,960,1200,1440])].sort((a,b)=>a-b);
  const time=m=>String(Math.floor(m/60)).padStart(2,'0')+':'+String(m%60).padStart(2,'0');
  const grid=e('table','','schedule-week-grid');
  grid.setAttribute('aria-label',l('Lịch sạc và xả pin theo tuần','Weekly battery schedule'));
  const head=e('tr');
  [l('Thời gian','Time'),...days].forEach(label=>{const h=e('th',label);h.scope='col';head.append(h);});
  const thead=e('thead');thead.append(head);grid.append(thead);
  const body=e('tbody');
  let draggedIndex=null;
  bounds.slice(0,-1).forEach((start,i)=>{
    const end=bounds[i+1],tr=e('tr'),th=e('th',time(start)+'–'+time(end));th.scope='row';tr.append(th);
    days.forEach((day,d)=>{
      const td=e('td');
      td.dataset.day=d;td.dataset.start=time(start);td.dataset.end=time(end);
      const found=valid.filter(s=>s.day===d&&minute(s.start)<=start&&minute(s.end)>=end);
      if (found.length===1) {
        const s=found[0],content=div('week-slot mode-'+(['charge','discharge','hold','self_use'].includes(s.mode)?s.mode:'unknown'),
          e('b',t(s.mode)),e('small',s.target_soc==null?l('Chưa đặt mức pin','No battery target'):l('Mức pin ','Battery level ')+s.target_soc+'%'));
        td.append(content);
      } else td.append(e('span',found.length?l('Khung giờ chồng lấn','Overlapping slots'):'—','week-empty'));
      if (edit) {
        const slotIndex=found.length===1?slots.indexOf(found[0]):-1;
        const context={day:d,start:time(start),end:time(end),slotIndex};
        const action=btn('',()=>edit(context),'week-edit');
        action.setAttribute('aria-label',`${day} ${time(start)}–${time(end)} · ${l('Chỉnh lịch nháp','Edit draft')}`);
        action.dataset.day=d;action.dataset.start=time(start);action.dataset.slotIndex=slotIndex;
        if(options.onMove) {
          action.draggable=slotIndex>=0;
          action.ondragstart=event=>{draggedIndex=slotIndex;event.dataTransfer.effectAllowed='move';event.dataTransfer.setData('text/plain','schedule-draft-slot');};
          action.ondragover=event=>{if(draggedIndex!=null){event.preventDefault();event.dataTransfer.dropEffect='move';action.classList.add('drop-target');}};
          action.ondragleave=()=>action.classList.remove('drop-target');
          action.ondragend=()=>{draggedIndex=null;grid.querySelectorAll('.drop-target').forEach(n=>n.classList.remove('drop-target'));};
          action.ondrop=event=>{event.preventDefault();action.classList.remove('drop-target');const index=draggedIndex;draggedIndex=null;if(index!=null)options.onMove({...context,slotIndex:index});};
        }
        action.append(...td.childNodes);td.append(action);
        if(options.onResize&&slotIndex>=0) {
          const slot=slots[slotIndex];
          for(const boundary of ['start','end']) {
            if(minute(slot[boundary])!==(boundary==='start'?start:end))continue;
            const label=`${day} · ${l('Đổi giờ ','Resize ')}${boundary==='start'?l('bắt đầu','start'):l('kết thúc','end')}`;
            const handle=btn('',()=>{},'week-resize resize-'+boundary);
            handle.setAttribute('aria-label',label);handle.title=l('Kéo hoặc dùng phím lên/xuống để đổi 15 phút','Drag or use Up/Down to change by 15 minutes');
            handle.dataset.boundary=boundary;handle.dataset.slotIndex=slotIndex;
            let pointer=null,candidate=null;
            const cancel=()=>{pointer=null;candidate=null;handle.classList.remove('resizing');handle.removeAttribute('data-preview');};
            handle.onpointerdown=event=>{
              if(event.button!==0)return;
              event.preventDefault();handle.focus({preventScroll:true});pointer=event.pointerId;candidate=null;
              handle.setPointerCapture(pointer);handle.classList.add('resizing');
            };
            handle.onpointermove=event=>{
              if(pointer!==event.pointerId)return;
              const cell=document.elementFromPoint(event.clientX,event.clientY)?.closest('td[data-day]');
              if(!cell||!grid.contains(cell)||Number(cell.dataset.day)!==slot.day){candidate=null;return;}
              const box=cell.getBoundingClientRect(),lo=minute(cell.dataset.start),hi=minute(cell.dataset.end);
              candidate=time(Math.max(0,Math.min(1440,Math.round((lo+(hi-lo)*(event.clientY-box.top)/box.height)/15)*15)));
              handle.dataset.preview=candidate;
            };
            handle.onpointerup=event=>{
              if(pointer!==event.pointerId)return;
              const next=candidate;cancel();
              if(handle.hasPointerCapture(event.pointerId))handle.releasePointerCapture(event.pointerId);
              if(next&&next!==slot[boundary])options.onResize({slotIndex,boundary,time:next});
            };
            handle.onpointercancel=handle.onlostpointercapture=cancel;
            handle.onkeydown=event=>{
              if(event.key==='Escape'&&pointer!=null){event.preventDefault();event.stopPropagation();cancel();return;}
              if(!['ArrowUp','ArrowDown'].includes(event.key))return;
              event.preventDefault();const value=minute(slot[boundary])+(event.key==='ArrowUp'?-15:15);
              if(value>=0&&value<=1440)options.onResize({slotIndex,boundary,time:time(value)});
            };
            td.append(handle);
          }
        }
      }
      tr.append(td);
    });
    body.append(tr);
  });
  grid.append(body);return div('table-scroll weekly-schedule-scroll',grid);
}
