import { l } from './i18n.js';
import { icon } from './icons.js';

export function goodweConnectionDialog(ui,{existing=null}={}) {
  const {e,div,p,field,input,select,form,api,showDialog,closeDialog,refresh,toast}=ui;
  const region=select([
    ['',l('Chọn máy chủ trong app SEMS+','Choose the server used in SEMS+')],
    ['hk',l('Quốc tế','International')],['eu',l('Châu Âu','Europe')],
    ['au',l('Úc','Australia')],['us',l('Châu Mỹ','Americas')],['cn',l('Trung Quốc','China')],
  ],existing?.region||'');
  region.required=true;region.disabled=!!existing;
  const email=input('email',existing?.account||''),password=input('password'),consent=input('checkbox');
  email.required=password.required=consent.required=true;
  email.maxLength=254;password.maxLength=4096;email.disabled=!!existing;
  email.autocomplete='section-goodwe email';password.autocomplete='section-goodwe new-password';
  email.name='goodwe-account';password.name='goodwe-password';
  const fields=e('fieldset','','deye-login-fields');
  fields.append(field(l('Máy chủ tài khoản','Account server'),region),
    field(l('Email SEMS+','SEMS+ email'),email),field(l('Mật khẩu SEMS+','SEMS+ password'),password),
    field(l('Tôi đã đọc và chấp thuận điều khoản GoodWe trên portal hãng; cho phép SolarOne lưu tài khoản mã hóa và đọc các nhà máy tôi có quyền truy cập.','I have read and accepted GoodWe terms on its portal; I authorize SolarOne to store this account encrypted and read plants I can access.'),consent));
  const message=div('notice warning');message.setAttribute('role','status');
  const f=form(async()=>{
    fields.disabled=true;message.textContent=l('Đang xác thực với máy chủ bạn đã chọn…','Authenticating with your selected server…');
    try {
      await api('/connections/goodwe',{region:region.value,email:email.value.trim(),password:password.value,
        vendor_terms_accepted:consent.checked,integration_id:existing?.id||null,revision:existing?.connection_revision??null});
      closeDialog();await refresh();toast(l('Đã xác thực SEMS+. Đã bật đọc định kỳ; mở Kiểm tra kết nối để đối chiếu dữ liệu. Chưa mở điều khiển.','SEMS+ authenticated. Periodic reads are enabled; open Check connection to review the data. Controls remain locked.'));
    } catch(error) {
      message.textContent=l('Chưa liên kết được. Kiểm tra đúng máy chủ và tài khoản SEMS+; nếu bị giới hạn hãy chờ rồi thử lại. Không tự thử nhiều vùng.','Not linked. Check the SEMS+ server and account; if rate-limited, wait before retrying. Do not try multiple regions automatically.');
      throw error;
    } finally {password.value='';fields.disabled=false;region.disabled=email.disabled=!!existing;}
  },l('Xác thực & liên kết chỉ đọc','Authenticate & link read-only'));
  f.autocomplete='off';
  const portal=e('a',l('Mở portal GoodWe để xem điều khoản','Open the GoodWe portal to review terms'));
  portal.href='https://semsplus.goodwe.com/';portal.target='_blank';portal.rel='noopener noreferrer';
  f.finish(fields,portal,message);
  showDialog(l('Kết nối GoodWe SEMS+','Connect GoodWe SEMS+'),div('stack connection-guide',
    div('connection-guide-heading',div('metric-icon blue',icon('cloud')),div('',e('h3',l('Tài khoản của bạn, kết nối chỉ đọc','Your account, read-only connection')),p(l('Dùng mật khẩu SEMS+, không phải mật khẩu hộp thư Gmail. Không cần App ID, App Secret hoặc nhập ID nhà máy.','Use your SEMS+ password, not your Gmail mailbox password. No App ID, App Secret or manual plant ID is required.')))),
    p(l('Kết nối thử nghiệm qua giao thức SEMS+. Sau liên kết, SolarOne tự đọc định kỳ các nhà máy bạn được phép xem. Số đo chưa rõ thời gian hoặc ánh xạ được ghi là chưa xác minh, không điền dữ liệu mẫu.','Experimental SEMS+ connection. After linking, SolarOne periodically reads plants you can access. Readings with unknown time or mapping stay unverified; no sample data is inserted.'),'notice'),
    f));
}
