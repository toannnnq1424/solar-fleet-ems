import { l } from './i18n.js';
import { icon } from './icons.js';

const regionNames=()=>({eu:l('EMEA / APAC','EMEA / APAC'),am:l('Châu Mỹ','Americas'),india:l('Ấn Độ','India')});

export async function deyeConnectionDialog(ui, {advanced, existing=null}={}) {
  const {e,div,p,btn,field,input,select,notice,form,api,showDialog,closeDialog,refresh,toast}=ui;
  const options=await api('/connections/deye/options');
  const available=options.applications.filter(a=>a.enabled);
  const region=select(options.applications.map(a=>[a.region,regionNames()[a.region]+(a.enabled?'':l(' · Chưa thiết lập',' · Not configured'))]),
    existing?.region||(available.length===1?available[0].region:''));
  if(!existing&&available.length!==1){const choice=e('option',l('Chọn khu vực tài khoản Deye','Choose your Deye account region'));choice.value='';region.prepend(choice);region.value='';}
  region.disabled=!!existing;
  const content=div('stack');
  const root=div('stack deye-connect-dialog',div('connection-guide-heading',div('metric-icon blue',icon('cloud')),
    div('',e('h3',l('Liên kết Deye Cloud','Link Deye Cloud')),p(l('Email và mật khẩu của tài khoản Deye, không phải mật khẩu Gmail hay SolarOne.','Use your Deye account email and password, not your Gmail or SolarOne password.')))),
    field(l('Khu vực tài khoản','Account region'),region),content);
  function draw(){
    const application=available.find(a=>a.region===region.value);
    if(!application){content.replaceChildren(notice(
      region.value?'Quản trị viên chưa thiết lập kết nối ứng dụng Deye cho khu vực này. Bạn chưa cần nhập mật khẩu.':'Chọn đúng khu vực đang dùng trong ứng dụng Deye. Không tự thử mật khẩu trên nhiều khu vực.',
      region.value?'Your administrator has not configured the Deye application for this region. Do not enter your password yet.':'Select the region used in your Deye app. Passwords are not tried across regions.'),
      btn(l('Thiết lập ứng dụng · quản trị viên','Application setup · administrator'),()=>deyeApplicationDialog(ui,()=>deyeConnectionDialog(ui,{advanced,existing}))),
      advanced?btn(l('Kết nối API nâng cao','Advanced API connection'),advanced):null);return;}
    const email=input('email',existing?.account||''),password=input('password');
    email.required=password.required=true;email.maxLength=254;password.maxLength=4096;
    email.autocomplete='section-deye email';password.autocomplete='section-deye new-password';email.disabled=!!existing;
    email.name='deye-account';password.name='deye-password';
    const fields=e('fieldset','','deye-login-fields');fields.append(field(l('Email Deye','Deye email'),email),field(l('Mật khẩu Deye','Deye password'),password));
    const f=form(async()=>{
      region.disabled=fields.disabled=true;
      try {
        await api('/connections/deye',{region:application.region,application_revision:application.revision,
          email:email.value.trim(),password:password.value,integration_id:existing?.id||null});
        closeDialog();await refresh();toast(l('Deye đã xác thực tài khoản. Danh mục chưa được đồng bộ; chưa cấp quyền điều khiển.','Deye authenticated the account. Inventory has not been synchronized; control is not enabled.'));
      } finally {password.value='';fields.disabled=false;region.disabled=!!existing;}
    },l('Xác thực & liên kết','Authenticate & link'));
    f.autocomplete='off';
    f.finish(notice('Khóa ứng dụng do quản trị viên quản lý trên máy chủ. Liên kết chỉ cấp đường đọc; không gửi lệnh thiết bị.','Application keys are managed on the server. Linking establishes read access only; it sends no equipment commands.'),fields);
    content.replaceChildren(f,advanced?btn(l('Kết nối API nâng cao','Advanced API connection'),advanced):p(''));
  }
  region.onchange=draw;draw();showDialog(l('Kết nối Deye','Connect Deye'),root);
}

export async function deyeApplicationDialog(ui, back=null) {
  const {e,div,p,btn,field,input,select,notice,form,api,showDialog,toast}=ui;
  const data=await api('/connections/deye/options');
  const region=select(data.applications.map(a=>[a.region,regionNames()[a.region]]),'eu'),body=div('stack');
  const root=div('stack deye-application-dialog',notice('Chỉ dành cho quản trị viên. Khóa ứng dụng được mã hóa trên máy chủ và không được trả lại giao diện. Cần khóa được Deye cấp cho ứng dụng và phạm vi sử dụng của bạn.','Administrator setup only. Application keys are encrypted on the server and never returned to this screen. Obtain Deye-issued keys authorized for your application and use.'),
    field(l('Khu vực ứng dụng','Application region'),region),body,
    btn(l('Tải lại trạng thái','Reload status'),()=>deyeApplicationDialog(ui,back)),back?btn(l('Quay lại kết nối tài khoản','Back to account connection'),back):null);
  function draw(){
    const current=data.applications.find(a=>a.region===region.value);
    const id=input('password'),secret=input('password'),ack=input('checkbox');
    id.required=secret.required=ack.required=true;id.maxLength=secret.maxLength=4096;id.autocomplete=secret.autocomplete='off';
    const fields=e('fieldset','','deye-login-fields');fields.append(field('App ID',id),field('App Secret',secret),
      field(l('Tôi hiểu thay khóa hoặc tắt ứng dụng sẽ tạm dừng các tài khoản phụ thuộc và yêu cầu liên kết lại.','I understand replacing keys or disabling the application pauses dependent accounts and requires reconnection.'),ack));
    const f=form(async()=>{
      region.disabled=fields.disabled=true;
      try {const result=await api('/admin/deye-applications/'+current.region,{revision:current.revision,app_id:id.value,app_secret:secret.value});
        toast(l('Đã lưu cấu hình, chưa xác minh với Deye. Tài khoản tạm dừng: ','Configuration saved, not verified with Deye. Paused accounts: ')+result.suspended_accounts);
        await deyeApplicationDialog(ui,back);
      } finally {id.value=secret.value='';region.disabled=fields.disabled=false;}
    },l('Lưu cấu hình ứng dụng','Save application configuration'));
    f.finish(fields);
    const disable=btn(l('Tắt ứng dụng ở khu vực này','Disable application in this region'),async()=>{
      if(!ack.checked){ack.reportValidity();return;}
      disable.disabled=region.disabled=true;
      try {await api('/admin/deye-applications/'+current.region+'/disable',{revision:current.revision});await deyeApplicationDialog(ui,back);}
      finally {disable.disabled=region.disabled=false;}
    },'danger');
    body.replaceChildren(p(current.enabled?l('Đã cấu hình · quyền truy cập từng tài khoản chưa được xác minh.','Configured · individual account access has not been verified.'):l('Chưa bật kết nối cho người dùng ở khu vực này.','User connections are not enabled for this region.')),
      f,current.enabled?disable:p(''));
  }
  region.onchange=draw;draw();showDialog(l('Ứng dụng Deye · quản trị viên','Deye application · administrator'),root);
}
