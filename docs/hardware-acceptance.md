# Quy trình nghiệm thu phần cứng và Commissioning 6 bài test điện lực

Trạng thái hiện tại: **CHƯA NGHIỆM THU TRÊN THỰC ĐỊA**. Bằng chứng từ giao diện web hoặc tài liệu API chỉ xác nhận metadata/khung lệnh của thiết bị, không chứng minh khả năng thực thi lệnh ghi và phản hồi điện an toàn trên lưới thực tế. Quy chuẩn kỹ thuật dưới đây là tiêu chuẩn bắt buộc cho đợt nghiệm thu thực địa, tuân thủ nghiêm ngặt **IEC 62446-1:2018** (Grid-connected PV systems), **IEC 62109-1/2** (Safety of power converters), **IEEE 1547-2018** (Interconnection standard) và **Thông tư 39/2015/TT-BCT & 30/2019/TT-BCT** của Bộ Công Thương Việt Nam.

---

## 1. Hồ sơ kỹ thuật bắt buộc trước khi cấp nguồn (Pre-requisites)

Mỗi trạm solar/BMS trước khi bắt đầu quy trình Commissioning phải có đầy đủ hồ sơ định danh duy nhất:
1. **Device Identification Sheet:** Exact Inverter Model, Logger/Gateway Model, Battery/BMS Model, Serial Number độc lập từng module, Phiên bản Firmware (Main MCU, HMI, Communication Board), Phiên bản giao thức Modbus/CAN.
2. **Electrical Single Line Diagram (SLD):** Sơ đồ nguyên lý 1 sợi chi tiết vị trí máy biến dòng (CT/Meter), chiều mũi tên đo lường (Arrow to Grid / Arrow to Inverter), vị trí MCB/MCCB AC, SPD Type 1+2 DC/AC, cọc tiếp địa bảo vệ (PE) và tiếp địa lặp lại.
3. **API & Connectivity Profile:** Tài khoản installer chính thức được hãng ủy quyền, hạn ngạch API (quota limits) xác nhận bằng văn bản, địa chỉ Endpoint Data Center chính xác (tránh nhầm lẫn US/EU/Global/China cluster).
4. **Physical Safety Isolation:** Công tắc cách ly DC Isolator, nút dừng khẩn cấp (E-Stop) độc lập phần cứng, rơ le bảo vệ mất pha và bảo vệ điện áp lưới độc lập ngoài inverter.

---

## 2. Chi tiết 6 bài kiểm tra điện lực chuyên sâu (Six-Step Commissioning Protocol)

Hệ thống EMS Solar Fleet tích hợp trực tiếp quy trình kiểm định 6 bước vào giao diện Commissioning để ghi nhận dữ liệu đo lường trực tiếp, ngăn chặn tình trạng phê duyệt hình thức.

```
       [BƯỚC 1]                     [BƯỚC 2]                     [BƯỚC 3]
Insulation Resistance &      Polarity & String Matching     Grid Synchronization &
Continuity Test (DC & PE)        (Voc / Isc Alignment)      Anti-Islanding Protection
   R_iso >= 1.0 MOhm              Delta Voc <= 5%               Trip Time <= 2.0s
          │                            │                             │
          └────────────────────────────┼─────────────────────────────┘
                                       ▼
       [BƯỚC 4]                     [BƯỚC 5]                     [BƯỚC 6]
  Active Power Control &       Reactive Power Q(U) &       BMS Safety Interlock &
   Zero-Export Response          Cos(phi) Grid Code            Emergency Cut-off
      t_resp < 5.0s               EVN Circular 39/30             t_trip < 100ms
```

### Bài test 1: Điện trở cách điện (Insulation Resistance) & Tính liên tục tiếp địa (Ground Continuity)
- **Tiêu chuẩn áp dụng:** IEC 62446-1 Section 5.4.3, TCVN 7447-6.
- **Phương pháp đo:**
  - Ngắt toàn bộ công tắc AC và DC. Đo điện áp hở mạch trước khi cắm máy đo để đảm bảo an toàn.
  - Sử dụng đồng hồ đo cách điện (Megohmmeter Fluke 1587 hoặc Kyoritsu 3005A) đặt điện áp thử nghiệm $1000\text{V DC}$.
  - Đo giữa cực dương DC (+) và Ground (PE); giữa cực âm DC (-) và Ground (PE).
- **Tiêu chí Đạt (PASS):**
  - Điện trở cách điện $R_{iso} \ge 1.0\text{ M}\Omega$ (với hệ thống $\le 1000\text{V}$) hoặc $\ge 0.5\text{ M}\Omega$ (với hệ thống $\le 600\text{V}$).
  - Điện trở liên tục dây tiếp địa bảo vệ khung giàn $R_{pe} < 0.2\Omega$ từ mọi tấm pin đến cọc đồng tiếp địa.

### Bài test 2: Cực tính & Kiểm tra hở mạch DC (Polarity & MPPT String Matching)
- **Tiêu chuẩn áp dụng:** IEC 62446-1 Section 5.4.2.
- **Phương pháp đo:**
  - Dùng vôn kế DC đo điện áp hở mạch $V_{oc}$ của từng chuỗi (string) trong điều kiện bức xạ $G \ge 400\text{ W/m}^2$.
  - Kiểm tra cực tính: que đỏ que đen vôn kế phải hiển thị dấu dương ($+$). Tuyệt đối cấm điện áp âm (đấu ngược cực).
  - So sánh $V_{oc}$ giữa các string trong cùng 1 dàn MPPT hoặc song song.
- **Tiêu chí Đạt (PASS):**
  - Tuyệt đối $100\%$ không có string nào bị đảo cực.
  - Sai lệch điện áp giữa các string tương đương: $\Delta V_{oc} = \frac{|V_{oc,max} - V_{oc,min}|}{V_{oc,avg}} \times 100\% \le 5.0\%$.

### Bài test 3: Hòa đồng bộ & Bảo vệ chống đảo lưới (Grid Synchronization & Anti-Islanding)
- **Tiêu chuẩn áp dụng:** IEC 62116, IEEE 1547 Clause 8.2, TT 39/2015/TT-BCT.
- **Phương pháp đo:**
  - Cho inverter hòa lưới và phát công suất danh định $P \ge 50\% P_{nom}$.
  - Ngắt MCCB cấp nguồn AC chính (mô phỏng mất điện lưới EVN).
  - Dùng thiết bị đo chất lượng điện năng (Power Quality Analyzer) ghi nhận sóng hài và thời gian cắt điện của inverter.
- **Tiêu chí Đạt (PASS):**
  - Thời gian cắt hòa lưới (Trip Time) $t \le 2.0\text{ giây}$ kể từ thời điểm ngắt MCCB AC.
  - Inverter phải lập tức dừng phát xung PWM, chuyển trạng thái sang `Grid Loss Alarm` hoặc `Waiting for Grid`.
  - Khi đóng lại MCCB AC, inverter phải duy trì thời gian đếm lùi tái kết nối (Reconnection Timer) tối thiểu $60\text{ giây}$ trước khi hòa lưới trở lại.

### Bài test 4: Điều khiển hạn chế phát lưới & Thời gian đáp ứng Zero-Export (Zero-Export Step Response)
- **Tiêu chuẩn áp dụng:** EN 50549-1, IEC 62446-1.
- **Phương pháp đo:**
  - Kích hoạt tính năng Zero-Export / Dynamic Export Limit trên EMS Controller và Smart Meter/CT.
  - Đột ngột ngắt tải tiêu thụ nội bộ (từ $100\text{ kW}$ giảm xuống $10\text{ kW}$) trong khi PV đang phát $80\text{ kW}$.
  - Ghi nhận đường đặc tính công suất phát lên lưới tại điểm đo Meter EVN.
- **Tiêu chí Đạt (PASS):**
  - Thời gian phản hồi điều tiết công suất $t_{resp} \le 5.0\text{ giây}$.
  - Công suất phát ngược ra lưới không vượt quá $0.0\text{ kW}$ (hoặc ngưỡng bù tải danh định $< 100\text{W}$ trong thời gian quá độ $< 3\text{ giây}$).
  - Sai số bám tải tĩnh $\le 2.0\% P_{rated}$.

### Bài test 5: Tuân thủ chế độ công suất phản kháng $Q(U)$ và $\cos\varphi(P)$ (Reactive Power Grid Code)
- **Tiêu chuẩn áp dụng:** Thông tư 39/2015/TT-BCT, Thông tư 30/2019/TT-BCT, VDE-AR-N 4105.
- **Phương pháp đo:**
  - Gửi lệnh điều khiển hệ số công suất $\cos\varphi = 0.95\text{ Inductive}$ (tiêu thụ Q) và $\cos\varphi = 0.95\text{ Capacitive}$ (phát Q).
  - Đo kiểm công suất tác dụng $P$ và công suất phản kháng $Q$ tại đầu ra AC bằng máy phân tích công suất Fluke 435.
- **Tiêu chí Đạt (PASS):**
  - Sai số điều chỉnh $\cos\varphi \le \pm 0.02$.
  - Đường cong đáp ứng $Q(U)$ tự động tăng bù $Q$ khi điện áp lưới tụt thấp và giảm $Q$ khi điện áp dâng cao đúng dải cài đặt.

### Bài test 6: Vòng khóa liên động an toàn BMS và Ngắt khẩn cấp (BMS Safety Interlock & E-Stop)
- **Tiêu chuẩn áp dụng:** UL 9540A, IEC 62619, NFPA 855.
- **Phương pháp đo:**
  - Cho hệ thống lưu trữ sạc/xả ở dòng định mức $0.5C$.
  - Kích hoạt ngắt khẩn cấp (nhấn nút E-Stop) hoặc mô phỏng lỗi BMS (ngắt cáp truyền thông CAN/RS485 giữa Inverter và Battery BMS).
- **Tiêu chí Đạt (PASS):**
  - Thời gian cắt dòng tải điện DC (Trip time) $t < 100\text{ ms}$ thông qua Contactor DC chuyên dụng.
  - Tuyệt đối không sinh hồ quang điện nguy hiểm ngoài buồng dập hồ quang.
  - Inverter lập tức ghi nhận lỗi `BMS Comm Fault` hoặc `E-Stop Active`, chuyển sang trạng thái dừng an toàn (Quarantine Lock).

---

## 3. Điều kiện tiên quyết để mở khóa quyền điều khiển từ xa (Write Permission Gate)

Hệ thống Solar Fleet EMS áp dụng cơ chế bảo vệ nghiêm ngặt: **Mặc định toàn bộ lệnh ghi từ xa (Remote Control / Schedule Write) bị KHÓA CỨNG (Locked 409)**.

Quyền điều khiển chỉ được cấp phát khi hội đủ 4 điều kiện:
1. **Hoàn thành 6/6 bài test:** Tất cả các kết quả đo lường thực tế phải được kỹ thuật viên nhập đầy đủ dữ liệu đo (V, A, MOhm, s), có file log xuất từ máy đo Fluke/Kyoritsu đính kèm.
2. **Ký số biên bản nghiệm thu (Digitally Signed Acceptance Sheet):** Có xác nhận họ tên, số chứng chỉ an toàn điện và chữ ký số của Kỹ sư vận hành (Commissioning Engineer).
3. **Hardware Profile Binding:** Hệ thống tự động gán nhãn `COMMISSIONED_VERIFIED` duy nhất cho cặp `(Station_ID, Device_Serial, Firmware_Version, Logger_MAC)`. Bất kỳ thay đổi nào về phần cứng hoặc cập nhật firmware sẽ tự động thu hồi nhãn này và đưa thiết bị về trạng thái `RE-COMMISSIONING_REQUIRED`.
4. **Idempotency & Readback Verification:** Mọi lệnh điều khiển sau khi được mở khóa đều phải đi qua luồng: `Capability Check -> Pre-execution Snapshot -> Command Dispatch -> Independent Post-write Telemetry Readback -> Audit Logging`. Nếu đọc lại không khớp trong vòng 30s, hệ thống lập tức rollback và đưa thiết bị vào chế độ cách ly an toàn (Safety Quarantine).

