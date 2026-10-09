import { l, t } from './i18n.js';
import { schemaControl } from './schema-form.js';

// Drafts only. A schema does not grant dispatch permission or hardware acceptance.
export function ruleActionFields(ui, capability, initial) {
  const {div, field, p}=ui, constraints=capability?.constraints;
  if(!capability || !constraints || typeof constraints!=='object') throw new Error(l('Chưa có hồ sơ cho chức năng này.','No profile is available for this action.'));
  const keys=Object.keys(constraints);
  if(initial && Object.keys(initial).some(key=>!keys.includes(key))) throw new Error(l('Bản nháp có tham số không còn trong hồ sơ. Giữ nguyên để kỹ thuật viên rà soát.','This draft contains parameters missing from the profile. Preserve it for technical review.'));
  if(!keys.length && !['ENABLE_GRID_CHARGE','DISABLE_GRID_CHARGE'].includes(capability.intent) && capability.state!=='VERIFIED') throw new Error(l('Chưa xác minh cấu trúc tham số; chưa thể nhập giá trị an toàn.','The parameter contract is unverified; safe value entry is unavailable.'));
  const controls=keys.map(key=>{
    const c=constraints[key];
    const schema=c.json_schema || (c.enum ? {enum:c.enum} : {type:'number',minimum:c.min,maximum:c.max,multipleOf:c.step});
    const control=schemaControl(schema,ui,0,{blank:true,initial:initial?.[key]});
    const title=key==='value'?l('Giá trị đề xuất','Proposed value'):t(key);
    return {key,...control,label:schema.title||title,unit:c.unit};
  });
  return {node:div('stack rule-profile-fields',...controls.map(c=>field(c.label+(c.unit?' ('+c.unit+')':''),c.node)),
    !controls.length?p(l('Hành động này không cần nhập giá trị.','This action takes no parameters.'),'field-help'):null),
    read:()=>Object.fromEntries(controls.map(c=>[c.key,c.read()]))};
}
