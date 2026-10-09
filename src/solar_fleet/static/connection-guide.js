import { l } from './i18n.js';
import { icon } from './icons.js';

// A setup guide, not authentication. No credentials are collected until prerequisites are explicit.
export function goodweConnectionGuide(ui, proceed, semsPlus) {
  const {e,div,p,btn,card,field,select,showDialog,closeDialog}=ui;
  const platform=select([
    ['',l('Chọn ứng dụng đang dùng','Choose the app you use')],
    ['sems','SEMS Portal'],['sems_plus','SEMS+'],['unknown',l('Tôi chưa rõ','I am not sure')],
  ],'');
  const details=div('stack');
  const next=btn(l('Tôi đã có thông tin kết nối','I have the connection details'),()=>platform.value==='sems_plus'?semsPlus():proceed(),'primary');
  function draw(){
    next.disabled=platform.value!=='sems'&&!(platform.value==='sems_plus'&&semsPlus);
    details.replaceChildren(platform.value==='sems'
      ? card(l('Bạn cần chuẩn bị','What to prepare'),
        div('connection-prerequisite',icon('user'),div('',e('b',l('Tài khoản SEMS của bạn','Your SEMS account')),p(l('Email/tên tài khoản và mật khẩu đang dùng trên SEMS. Không nhập mật khẩu hộp thư Gmail.','The email/username and password you use for SEMS. Do not enter your Gmail mailbox password.')))),
        div('connection-prerequisite',icon('plant'),div('',e('b',l('ID nhà máy được phép xem','Authorized plant IDs')),p(l('Kết nối hiện tại chưa tự lấy danh sách nhà máy. Cần ID nhà máy SEMS (không phải số sê-ri biến tần), tối đa 100 ID. Nếu chưa biết ID, cần kiểm tra thông tin nhà máy trong SEMS hoặc nhờ đơn vị lắp đặt xác nhận.','The current connector does not discover your plant list. Supply SEMS plant IDs, not inverter serial numbers, up to 100 IDs. If unknown, check the plant information in SEMS or ask your installer to identify it.')))),
        p(l('Không cần App ID/App Secret trong form GoodWe hiện tại. Lưu cấu hình, kiểm tra quyền đọc và đồng bộ danh mục là các bước riêng.','The current GoodWe form does not require an App ID/App Secret. Saving configuration, checking read access and importing inventory are separate steps.'),'notice'))
      : platform.value==='sems_plus'
        ? card(l('SEMS+: đăng nhập hãng và kết nối SolarOne là hai bước khác nhau','SEMS+: portal sign-in and SolarOne connection are separate'),
          div('connection-prerequisite',icon('user'),div('',e('b',l('1. Tài khoản trên trang GoodWe','1. Account on the GoodWe portal')),p(l('Dùng email và mật khẩu SEMS+ trên trang chính thức của hãng. Bước này không yêu cầu bạn tự xin App ID/App Secret và không tự kết nối tài khoản vào SolarOne.','Use your SEMS+ email and password on the official vendor portal. This step does not require your own App ID/App Secret and does not connect the account to SolarOne.')))),
          div('connection-prerequisite',icon('plant'),div('',e('b',l('2. Kiểm tra nhà máy và thiết bị','2. Review plants and equipment')),p(l('Đối chiếu danh sách, thời gian cập nhật và khu vực máy chủ. Không gửi mật khẩu, cookie hoặc token trong chat. Không đổi cấu hình thiết bị trong bước kiểm tra chỉ đọc.','Check the inventory, update time and server region. Do not share passwords, cookies or tokens in chat. Do not change device settings during the read-only review.')))),
          div('connection-prerequisite',icon('cloud'),div('',e('b',l('3. Kết nối thử nghiệm trong SolarOne','3. Experimental connection in SolarOne')),p(l('Luồng SEMS+ riêng nhận email, mật khẩu và máy chủ tài khoản, sau khi bạn xác nhận quyền đọc và điều khoản. Tự lấy ID nhà máy; không dùng form SEMS cũ. Chưa nghiệm thu dữ liệu tài khoản thật.','The separate SEMS+ flow accepts email, password and account server after your read-access and terms confirmation. It discovers plant IDs without using the old SEMS form. Live-account data acceptance is still pending.')))),
          p(l('Đăng nhập portal thành công không xác nhận kết nối SolarOne hay mở quyền điều khiển.','Successful portal sign-in does not verify the SolarOne connection or unlock controls.'),'notice warning'))
        : card(l('Xác định đúng ứng dụng trước','Confirm the app first'),p(l('Xem tên đầy đủ của ứng dụng trên điện thoại. Tên hãng GoodWe chưa đủ để xác định nền tảng đăng nhập.','Check the full app name on your phone. The GoodWe brand alone does not identify the login platform.'))));
  }
  platform.onchange=draw;draw();
  showDialog(l('Trước khi kết nối GoodWe','Before connecting GoodWe'),div('stack connection-guide',
    div('connection-guide-heading',div('metric-icon blue',icon('cloud')),div('',e('h3',l('Kết nối đúng tài khoản GoodWe','Connect the right GoodWe account')),p(l('Kiểm tra thông tin cần thiết trước khi nhập mật khẩu.','Check what is needed before entering your password.')))),
    p(l('SEMS Portal và SEMS+ dùng hai cách kết nối khác nhau. Chọn đúng ứng dụng; SEMS+ có luồng thử nghiệm chỉ đọc riêng, còn SEMS Portal chỉ dành cho cấu hình cũ đã được xác nhận.','SEMS Portal and SEMS+ use different connections. Choose the right app: SEMS+ has a separate experimental read-only flow; SEMS Portal is only for confirmed legacy configurations.'),'notice warning'),
    field(l('Ứng dụng GoodWe đang dùng','Your GoodWe app'),platform),details,
    div('form-actions',btn(l('Để sau','Not now'),closeDialog),next)));
}
