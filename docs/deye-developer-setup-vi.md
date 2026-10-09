# Đăng ký ứng dụng Deye cho SolarOne

Kiểm tra trực tiếp cổng Deye ngày **04/10/2026**. Đây là hướng dẫn chuẩn bị và hỏi xác nhận quyền, **không phải xác nhận Deye đã duyệt mô hình nhiều khách hàng**. Không gửi mật khẩu, App Secret hoặc token qua chat, email hỗ trợ hay GitHub.

## 1. Hiểu đúng tài khoản và khóa

- **Tài khoản A — quản trị ứng dụng:** email riêng để đăng ký/quản lý ứng dụng SolarOne, giữ App ID và App Secret ở máy chủ.
- **Tài khoản B — khách hàng:** tài khoản DeyeCloud đang được cấp quyền xem các nhà máy của khách hàng. Khách hàng không cần biết khóa của ứng dụng.
- Luồng mong muốn: khóa ứng dụng A + xác thực của B → token riêng của B → chỉ danh sách nhà máy B được phép xem. Không chuyển quyền sở hữu nhà máy sang A.

Quick Start chính thức mô tả App ID/App Secret và email/password là các đầu vào riêng, có cả tài khoản cá nhân và business member. Tuy nhiên, tài liệu đã đọc **chưa nói rõ app do A tạo có thể dùng cho B không liên quan**, hoặc A có bắt buộc sở hữu nhà máy khi xét duyệt ứng dụng không. Việc biểu mẫu đăng ký tài khoản cá nhân không hỏi nhà máy không chứng minh ứng dụng đa khách hàng sẽ được duyệt. Cần Deye xác nhận và một lần kiểm thử read-only có sự cho phép của chủ tài khoản.

## 2. Tạo tài khoản DeyeCloud

1. Chuẩn bị một email riêng do bạn kiểm soát lâu dài. Email này là tài khoản quản trị ứng dụng, không phải nơi gom nhà máy khách hàng.
2. Mở [Quick Start](https://developer.deyecloud.com/start), chọn **Create an account on DeyeCloud**. Liên kết hiện tại dẫn đến [trang đăng ký](https://eu1.deyecloud.com/reg/0?language=en).
3. Trang đầu hiện có **Registered owner** và **Registered business** (Installation O&M Provider / Dealer / Manufacturer). Chọn đúng tư cách thực tế; không khai là nhà sản xuất/đơn vị lắp đặt nếu không đúng. Với cá nhân phát triển ứng dụng nhưng không sở hữu nhà máy, nên hỏi Deye bằng thư bên dưới để xác nhận loại tài khoản phù hợp; chữ “owner” không phải bằng chứng chấp thuận mô hình developer-only.
4. Nếu Deye chấp nhận đăng ký cá nhân: chọn **Registered owner → Europe Data Center → Next**. Tài liệu hiện hướng dẫn Europe cho Europe/Africa/Asia Pacific, và hộp chọn developer ghi **EMEA, APAC**, có ví dụ Vietnam. Tài khoản khách hàng đã có phải dùng đúng vùng đã đăng ký, không đổi vùng chỉ theo vị trí hiện tại.
5. Nhập **Please enter E-mail**, bấm **Send**, lấy mã email và nhập **Please enter verification code**. Tự tạo mật khẩu mạnh, nhập lại ở **Please enter the password again**. Không dùng lại mật khẩu email.
6. Tự đọc điều khoản/chính sách quyền riêng tư, tự đánh dấu chấp thuận nếu đồng ý, rồi **Done**. Nếu có CAPTCHA hoặc xác minh bổ sung, tự hoàn tất. Mình chưa tạo tài khoản hay chấp thuận điều khoản thay bạn.

## 3. Đăng nhập developer và tạo Application

1. Mở [Application](https://developer.deyecloud.com/app), bấm **Sign In**.
2. Chọn đúng data center; với tài khoản vừa tạo ở Europe, chọn **EMEA, APAC → Confirm**.
3. Hệ thống chuyển sang đăng nhập DeyeCloud. Tự đăng nhập bằng tài khoản A và xử lý điều khoản nếu được hỏi.
4. Vào mục **Application**, mở biểu mẫu tạo ứng dụng theo hướng dẫn của Quick Start. Mình chưa đăng nhập tài khoản thật nên **chưa xác minh tên nút và toàn bộ trường trong biểu mẫu sau đăng nhập**; không có căn cứ để bịa chuỗi nút “xin quyền” hoặc thời gian duyệt.
5. Nội dung đề nghị nếu biểu mẫu có các trường tương ứng:
   - Tên ứng dụng: `SolarOne`.
   - Mô tả: `A multi-vendor solar monitoring application in development. Customers connect their own authorized DeyeCloud accounts. Initial use is read-only station/device discovery, current measurements and historical data. No ownership transfer or equipment control is requested for the initial pilot.`
   - Người liên hệ: tên/email thật của bạn; công ty chỉ điền nếu thực sự có.
   - Website/callback/IP: chỉ điền giá trị thật mà bạn kiểm soát nếu được yêu cầu. Chưa có môi trường công khai thì xin hướng dẫn sandbox/development; không lấy GitHub làm callback và không dựng domain giả.
6. Theo Quick Start, khi tạo ứng dụng, App ID/App Secret được cấp; README chính thức chỉ chỗ lấy tại Application. Nếu tài khoản hiện tại bị yêu cầu duyệt hoặc không tạo được, dùng kênh hỗ trợ bước 4. **Có khóa không đồng nghĩa đã được quyền thương mại, truy cập mọi khách hàng hoặc điều khiển thiết bị.**

## 4. Xác nhận quyền nhiều khách hàng

Kênh hỗ trợ API do [repository chính thức Deye](https://github.com/DeyeCloudDevelopers/deye-openapi-client-sample-code) công bố: **cloudservice@deye.com.cn**. Đây là kênh hỏi API, chưa được xác minh là một quy trình phê duyệt/form bắt buộc riêng. Bạn tự gửi mẫu sau, thay phần trong ngoặc vuông bằng thông tin thật; không đính kèm secrets.

**Subject:** DeyeCloud OpenAPI — developer-only account and multi-customer authorization for SolarOne

```text
Hello DeyeCloud API team,

I am developing SolarOne, a multi-vendor solar monitoring application in Vietnam.
I would like to use a dedicated DeyeCloud account solely to own the application
credentials. This developer account will have no stations or devices.

Customers will retain their own DeyeCloud accounts and station permissions.
With each customer's explicit consent, SolarOne would use its application
credentials together with that customer's supported authentication flow to
obtain a separate token and read only the stations accessible to that customer.
We do not intend to transfer customer stations to the developer account.
The initial pilot is read-only; we are not requesting equipment control.

Please confirm:
1. Can an account with no stations create and own this application? Which
   registration category should an independent software developer choose?
2. Can App ID/App Secret owned by account A be used with an unrelated customer's
   account B at /v1.0/account/token, or is separate partner approval required?
3. What customer authorization/revocation mechanism is required? Is a hosted
   authorization/OAuth flow available, or is email/password authentication the
   supported approach? Are personal and business-member accounts both supported?
4. Can monitoring-only permissions be enforced by Deye? How are Company IDs,
   station sharing and organizational roles handled for business members?
5. Are separate applications/approvals needed for EU/APAC, Americas and India?
   What are the current quotas, polling limits, costs and production requirements?
6. If an application or partner review is required, please provide the official
   form and the required documents, URLs, security or privacy information.

Developer account email: [your developer account email]
Application name / App ID if already created: [SolarOne / App ID]
Legal entity or independent developer status: [truthful status]
Expected pilot size and polling interval: [your realistic pilot plan, or TBD]

Thank you,
[your name]
```

Thứ tự đề nghị: **xác nhận loại tài khoản nếu chưa rõ → tạo tài khoản → tạo ứng dụng → xác nhận quyền cross-account và các thủ tục phát sinh → cấp quyền/pilot theo hướng dẫn Deye**. Có thể gửi thư ngay trước khi tạo tài khoản, để tránh xin sai loại quyền. Không có bằng chứng về thời hạn phê duyệt nên không hứa số ngày.

## 5. Sau khi được cấp quyền

- Nhập App ID/App Secret một lần trong phần cấu hình ứng dụng Deye dành cho quản trị viên SolarOne; không đưa xuống mã frontend/Git.
- Bạn tự nhập tài khoản B vào màn kết nối. Lượt đầu chỉ xác thực, khám phá nhà máy/thiết bị và đối chiếu số đo/thời điểm với app Deye. Không đổi TOU, sạc/xả, firmware hoặc thông số lưới.
- Cần kiểm tra phân tách quyền bằng các tài khoản được bạn cho phép; không thăm dò nhà máy ngoài phạm vi. Đọc đúng dữ liệu của một tài khoản chưa chứng minh SaaS đa tenant an toàn.
- Hiện code SolarOne đã tách form email/password khỏi khóa ứng dụng nhưng thao tác liên kết vẫn dành cho quản trị viên toàn tổ chức. **Khách hàng tự đăng ký/tự liên kết và cách ly đa tenant chưa hoàn thiện.** Việc Deye cho phép cross-account không tự hoàn thành phần này.
- Nếu tài khoản sử dụng Deye qua nền tảng khác, không mặc định email/password đó là tài khoản DeyeCloud OpenAPI tương thích.

## Nguồn và giới hạn

- [Quick Start](https://developer.deyecloud.com/start): đọc bản render ngày 04/10/2026, trang ghi cập nhật 31/03/2025. Có personal/business token flow và Company ID.
- [Application](https://developer.deyecloud.com/app): trang công khai yêu cầu đăng nhập; đã xác minh bộ chọn data center và bước chuyển đăng nhập, chưa đọc form tạo app sau đăng nhập.
- [Đăng ký DeyeCloud](https://eu1.deyecloud.com/reg/0?language=en): kiểm tra luồng Registered owner, chọn data center và các trường email/mã xác minh/mật khẩu; không nộp form.
- [Mã mẫu chính thức](https://github.com/DeyeCloudDevelopers/deye-openapi-client-sample-code): prerequisites, vị trí khóa, email hỗ trợ.
- Portal đang thông báo kế hoạch metering/quota/rate limit và sẽ công bố chi tiết sau; cần hỏi giới hạn đang áp dụng thay vì mặc định API miễn phí/không giới hạn.
