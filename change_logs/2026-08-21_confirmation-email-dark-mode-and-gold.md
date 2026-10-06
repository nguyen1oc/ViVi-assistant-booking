# 2026-08-21 - Thư xác nhận: chế độ sáng/tối, chống rớt chữ, làm bật màu vàng

## Vấn đề gặp phải khi mở thư trên điện thoại

1. Máy để chế độ SÁNG: logo VinFast biến mất hoàn toàn.
2. Máy để chế độ TỐI: nền đen bị lật thành trắng, thư nhìn nham nhở.
3. Rớt chữ: "PHIẾU XÁC NHẬN LỊCH HẸN" rớt chữ HẸN, "THÔNG TIN NHÂN VIÊN HỖ TRỢ
   CỦA BẠN" rớt chữ BẠN.
4. Lưới ảnh 3 ô một hàng, mỗi ô còn khoảng 110px, nhìn không ra cái gì.
5. Màu vàng không nổi, không làm bật được thư.

## Điều cốt lõi

Ứng dụng mail KHÔNG đảo màu bên trong ảnh, nó chỉ đảo màu khai báo bằng CSS.
Thứ gì bắt buộc phải nhìn thấy ở mọi chế độ thì nướng sẵn nền vào trong ảnh.

## Bốn lớp khoá màu, xếp từ chắc nhất

1. **Nền là ô ảnh lát lặp, không phải `background-color`.** Hai ô màu đặc 24x24
   (`#121212` nền thư, `#1E1E1E` nền card, 91 byte mỗi ô) lát kín bề mặt, đính kèm
   dạng `cid:`. Ảnh không bị đảo màu nên bề mặt luôn tối. Nhờ vậy **logo giữ nguyên
   file gốc chữ trắng nền trong suốt** mà vẫn luôn nổi. Luôn giữ `bgcolor` song
   song làm lớp đỡ. Sinh bằng `scripts/make_email_assets.py`.
   Kèm theo: bỏ mọi khai báo màu thừa ở các ô con, để nền lát của khung ngoài
   xuyên qua. Càng ít chỗ khai màu thì càng ít chỗ bị lật.
2. **Vàng đặc làm khối, không làm chữ mảnh.** Thanh tên khách và hai nút là mảng
   vàng đặc chữ đen; mảng màu trung tính cỡ lớn sống sót qua mọi kiểu đảo màu.
3. **`color-scheme: dark only`** — Apple Mail đọc và thôi không tự đổi màu.
4. **Lớp đè `[data-ogsc]` / `[data-ogsb]`** cho Outlook điện thoại. Mọi phần tử có
   màu đều mang một lớp `bg-*` / `t-*` để lớp đè với tới được.

Một số phiên bản Gmail điện thoại không đọc ảnh nền tham chiếu qua `cid:`; ở đó
thư rơi về lớp đỡ `bgcolor`, tức là bằng hiện trạng cũ chứ không tệ hơn. Cách chắc
chắn duy nhất nếu vẫn không ưng: đổi sang nền sáng.

**Đã thử và bỏ:** nướng nền vàng thẳng vào ảnh logo. Cách đó khoá được logo thật,
nhưng đổi màu nền của logo là đụng vào nhận diện thương hiệu nên không dùng.

## Quy tắc màu vàng, sửa nguyên nhân "vàng không nổi"

    Vàng làm NỀN  ->  #D4AF37, chữ trên nó là #121212
    Vàng làm CHỮ  ->  #F3E5AB (Champagne)

`#D4AF37` có độ sáng trung bình: đổ mảng lớn thì đầy đặn và sang, nhưng bóp xuống
cỡ chữ 12px trên nền đen thì xỉn lại thành màu ô liu, nhìn như chữ bị mờ. Bản
trước dùng `#D4AF37` cho cả nhãn nhỏ, đó là lý do vàng trông không nổi.

## Chống rớt chữ

Ngắt dòng SẴN bằng `<br>` ở ba chỗ, chấp nhận trên màn rộng cũng thành hai dòng:
`PHIẾU XÁC NHẬN / LỊCH HẸN`, `ViVi gửi bạn / thông tin lịch hẹn`,
`THÔNG TIN NHÂN VIÊN / HỖ TRỢ CỦA BẠN`. Chân thư cắt thành ba câu ngắn.

## Lưới ảnh dựng lại

Một ô lớn tràn ngang + các hàng đôi, thay cho 3 ô một hàng. Ô rộng gần 180px trên
điện thoại thay vì 110px. Mỗi ô có viền mảnh để đọc ra là khung ảnh. Lưới co theo
số ảnh có được: 5 ảnh -> 1+2+2, 4 ảnh -> 1+2, không có ảnh -> bỏ hẳn lưới.

Ô lớn BẮT BUỘC là ảnh có nền thật; ảnh cutout nền đen đặt vào đó thì xe trôi lơ
lửng giữa mảng đen.

## Lỗi dữ liệu ảnh phát hiện được

Kho ảnh trong máy và kho trên CDN KHÔNG giống nhau. `VF3/3..jpg`, `VF5/1..webp`,
`VF5/5..webp` có trong `data/media` nhưng CDN trả 404. Đã curl kiểm từng đường dẫn
trong `_EMAIL_PHOTOS_BY_MODEL` và chỉ giữ đường dẫn trả 200. Phép kiểm tra file
lúc chạy chỉ tra kho nội bộ nên KHÔNG bắt được lỗi này, phải đối chiếu tay.

VF3 và VF5 trên CDN chỉ còn ảnh cutout, không có ảnh ngoại thất chụp ngoài đời.
Cần bổ sung ảnh có nền cho hai mẫu này.

## Mười tình huống người nhận đã liệt kê và xử lý

Chế độ sáng/tối · chặn ảnh · Outlook Windows · màn 320px · tên xe và showroom dài
ngắn khác nhau · chưa phân công nhân viên · người đặt hộ · mẫu xe thiếu ảnh · tắt
hiệu ứng chuyển động · máy đọc màn hình. Chi tiết ghi trong chú thích đầu file
`docs/mockups/email-phieu-xac-nhan-awe.html`.

## File đổi

- `scripts/make_email_watermarks.py` -> `scripts/make_email_assets.py`, sinh thêm
  hai tấm logo.
- `assets/email-logo-gold.png`, `assets/email-logo-dark.png` (mới).
- `email_templates.py`: dựng lại toàn bộ phần thư xác nhận.
- `docs/mockups/email-phieu-xac-nhan-awe.html`: bản đối chiếu, sửa cùng lúc.
- Thêm kiểm tra trong test: hai cid logo, `color-scheme`, `[data-ogsc]`, hai chỗ
  ngắt dòng sẵn.

## Test

`pytest`: 345 passed, 6 skipped. `ruff check` và `mypy` sạch.

---

## Bổ sung cuối ngày 21/08

### Logo bị chìm: tìm ra nguyên nhân thật

`assets/vinfast-logo.png` là bản logo **màu đen `#231F20`**, dựng cho nền sáng.
Bản thư nền sáng cũ dùng đúng, nhưng bê nguyên sang thư nền tối thì chìm nghỉm.
Không phải lỗi nền, là lỗi chọn sai bản logo.

Đã thêm `_logo_band()` trong `make_email_assets.py`: lấy khuôn từ kênh alpha của
chính file gốc rồi tô **trắng**, hình dạng không đổi một pixel. Dải rộng đúng
600px bằng bề ngang thư, nền tối nướng sẵn — khi thư hiện đúng màu thì dải tan
vào nền, khi bị lật màu thì nó đọc ra là một dải header cố ý chứ không phải ô
chữ nhật lạc lõng. Sinh ra `email-logo-band.png` và `email-logo-band-small.png`.

### Lớp khoá màu thứ năm

`_lock_colors()` gắn `!important` vào mọi khai báo `color` và `background-color`
nội tuyến. Ứng dụng nào đảo màu bằng cách chèn CSS đè lên thư thì khai báo nội
tuyến có `!important` thắng được. Không ăn thua với mọi ứng dụng nhưng không tốn gì.

### Vẫn chưa khoá được, và đường đi tiếp

Người dùng báo trên điện thoại thư VẪN bị đổi màu sau bốn lớp trước. Hai nguyên
nhân đã loại trừ được:

- Backend công khai `vinfastbooking-api-latest.onrender.com` KHÔNG phục vụ
  `/media` (trả 404), nên không có nơi nào đặt ô nền bằng URL https.
- `cid:` trong `background-image` không phải ứng dụng nào cũng đọc; Gmail thường
  bỏ qua. Đó gần như chắc chắn là lý do lớp khoá nền không ăn.

Hai đường còn lại, cần người quyết:

1. **Đẩy hai ô nền lên R2 rồi trỏ bằng URL https.** Gmail có tải ảnh nền qua
   https, nên lớp khoá nền sẽ ăn. Rủi ro: nếu Gmail vẫn lật màu CHỮ trong khi nền
   bị khoá cứng thì chữ tối trên nền tối, đọc không ra — tệ hơn hiện tại.
2. **Đổi sang nền sáng** (kem hoặc trắng, chữ đen, nhấn vàng, khối đen làm điểm
   nhấn). Thiết kế nền sáng gần như không bị đảo màu đụng tới. Đây là cách duy
   nhất bảo đảm thư giữ đúng một bộ màu ở mọi máy.

### Header một hàng, chống rớt chữ bằng số đo thật

Logo và khẩu hiệu xếp trên cùng một hàng. Khẩu hiệu khoá `white-space:nowrap` nên
không bao giờ rớt chữ; đổi lại cỡ chữ và bề ngang logo phải tự tính cho luôn vừa.

**Số đo lấy bằng Arial Black, không phải Oswald.** Gmail và Outlook bỏ qua Google
Fonts nên chữ rơi về Arial Black, rộng hơn Oswald khoảng 13%. Đo bằng Oswald là
tràn ở máy thật.

| Bề ngang | Cỡ chữ | Logo | Khe | Tổng (Arial Black) | Chỗ có |
|---|---|---|---|---|---|
| 600px | 24px | 190 | 20 | 507 | 552 |
| 390px | 15px | 135 | 14 | 338 | 358 |
| 320px | 13px | 112 | 10 | 287 | 296 |

Thêm ngưỡng `max-width: 360px` cho máy hẹp (iPhone SE). Ở đó mọi dòng đã ngắt sẵn
bằng `<br>` đều phải co thêm một nấc, nếu không nó lại tự xuống dòng lần nữa:
`PHIẾU XÁC NHẬN` 30px→26px (297px vượt 288px chỗ có), `THÔNG TIN LỊCH HẸN`
20px→18px (247px so với 250px chỗ có, sát quá).

Đã kiểm bằng cách nạp thư vào iframe ở 390 / 360 / 320px, cả bản có Oswald lẫn bản
cắt Google Fonts để giả lập Gmail: `scrollWidth` bằng đúng bề ngang khung ở mọi
trường hợp, không tràn ngang, không rớt chữ.

Logo header đổi từ dải tràn ngang sang ô vừa khít (`email-logo-tile.png`), vẫn giữ
chữ trắng và nền tối nướng sẵn. Chân thư giữ dải tràn ngang.

---

## Đợt sửa thứ ba (21/08, sau khi pull code mới)

### Header chỉ còn logo

Bỏ hẳn khẩu hiệu "MÃNH LIỆT / TINH THẦN VIỆT NAM". Header là một dải logo tràn
ngang, chữ VinFast to lên 240px. Kéo theo: bỏ luôn `.hdr-*`, `.h-tagline` và
ngưỡng `max-width:360px` vì không còn gì để co.

### Giới hạn vùng tối đúng bằng bề ngang thư

Khung ngoài cùng trước đây lát nền tối phủ 100% bề ngang cửa sổ, nên trên màn rộng
thư thành một dải nội dung hẹp nằm giữa một biển đen. Nay khung ngoài để trong
suốt, chỉ khung 600px mới có nền tối — tức là vùng tối rộng đúng bằng thanh vàng
mang tên khách.

### Bỏ webfont: đây là nguyên nhân lỗi font trên điện thoại

Google Fonts phục vụ font theo `unicode-range`. Ứng dụng mail trên điện thoại nạp
được bộ ký tự Latin nhưng KHÔNG nạp bộ tiếng Việt, nên chữ có dấu rơi sang font
khác từng ký tự một, ra một dòng lẫn hai kiểu chữ. Mở bằng trình duyệt thì nạp đủ
nên không thấy — đúng hiện tượng "xem trên máy tính ổn, xem trên điện thoại hỏng".

Đã bỏ `<link>` Google Fonts, chuyển sang font hệ thống. Chữ giống nhau ở mọi nơi.
Đổi lại mất dáng chữ hẹp của Oswald, bù bằng chữ hoa, nét đậm và giãn chữ.

Hệ quả tốt: font hệ thống hẹp hơn Arial Black nên các dòng ngắt sẵn dư chỗ hẳn
(`PHIẾU XÁC NHẬN` ở 320px rộng 269px so với 288px chỗ có), bỏ được cả một ngưỡng
media query.

### Một màu vàng duy nhất: #F5C542

| Màu | Độ sáng | Tương phản trên card | Vấn đề |
|---|---|---|---|
| `#D4AF37` | 0.45 | 7.9 | Ở cỡ chữ 12px xỉn lại như màu ô liu |
| `#F3E5AB` | 0.78 | 13.2 | Sáng quá, máy bật chế độ tối lật thành màu tối rồi chìm |
| **`#F5C542`** | **0.60** | **10.3** | Sáng hơn `#D4AF37` rõ, vẫn giữa dải nên chịu đảo màu tốt |

Gộp hai màu vàng thành một, dùng chung cho cả mảng nền lẫn chữ.

### Mockup nay được SINH RA, không viết tay nữa

Thêm `backend/scripts/preview_confirmation_email.py`. Trước đây bản mockup là file
HTML riêng chép tay song song với `email_templates.py`; sửa một bên quên bên kia
là lệch, và đã lệch thật vài lần. Nay hai file trong `docs/mockups/` được sinh từ
chính bộ render của backend nên không thể lệch. Đừng sửa tay chúng nữa.

---

## Đợt sửa thứ tư: dựng lại toàn bộ các template thư còn lại

Lấy thư xác nhận làm chuẩn, đưa mọi thư khác về chung một bộ khung.

### Tách khung dùng chung

Ba mảnh mới trong `email_templates.py`, mọi thư nền tối đều dựng từ đây nên font,
màu, khoảng cách và cách xuống dòng luôn giống nhau:

- `_dark_document()` — đầu thư, thanh nav, tiêu đề, thanh vàng, ruột, chân thư
- `_card_block()` — card viền vàng có ảnh chìm
- `_para_row()`, `_gold_text()`, `_gold_row()`, `_gold_button()`

Thêm loại thư mới thì viết thêm nội dung, KHÔNG chép lại khung.

### Năm loại thư lịch hẹn dùng chung một bộ render

`render_booking_dark_email()` phục vụ cả năm, khác nhau đúng bốn chỗ gói trong
`_DarkCopy`: tiêu đề, đoạn mở đầu, đoạn nhắc trong card, và nút.

| Loại | Tiêu đề |
|---|---|
| `booking_confirmation` | Phiếu xác nhận lịch hẹn |
| `reminder` / `reminder_24h` / `reminder_2h` | Nhắc bạn lịch lái thử |
| `reschedule_confirmation` | Lịch hẹn đã đổi giờ |
| `booking_update` | Lịch hẹn vừa cập nhật |
| `cancellation_confirmation` | Lịch hẹn đã huỷ |

Thư huỷ lịch KHÔNG kèm đoạn giới thiệu xe và lưới ảnh: khách vừa huỷ xong mà thư
còn khoe xe thì đọc ra rất vô duyên.

Đoạn mở đầu thư nhắc lịch theo đúng câu chủ dự án đưa:

> Xin chào bạn, ViVi nhắc bạn có lịch hẹn với ViVi tại {showroom} vào {when} để
> lái thử xe {model}. ViVi gửi lại toàn bộ thông tin chi tiết của lịch hẹn ngay
> bên dưới, bạn xem qua giúp ViVi nhé.

### Thư mã xác thực

Dựng lại trên cùng khung. Ba điểm riêng:

- Thanh vàng mang chính MÃ XÁC THỰC chứ không phải tên khách, cỡ chữ 30px. Đây là
  thứ duy nhất người nhận cần đọc nên đặt vào chỗ đập vào mắt nhất thư.
- Ảnh chìm là xe **Lạc Hồng**, không gắn với mẫu xe nào, vì lúc gửi mã thì khách
  còn chưa chọn xe. Sinh từ `lac-hong-900lx/spin-2.webp` bằng cùng công thức với
  ảnh chìm xe, ra `data/media/email/lac-hong-watermark.jpg`.
- Không có lưới ảnh, không có đoạn giới thiệu xe.

Bản OTP nền sáng cũ đã gỡ.

### Hai lỗi thật test bắt được

1. **Tên xe nhân đôi tiền tố.** `vehicle_models.name` KHÔNG nhất quán giữa các
   nguồn: bản seed thật ghi `VF 9`, dữ liệu test ghi sẵn `VinFast VF 6`. Ghép
   tiền tố vô điều kiện là khách nhận được `VinFast VinFast VF 6`. Nay chỉ ghép
   khi tên chưa có sẵn.
2. **Tin nhắn SMS mượn tiêu đề thư.** Tiêu đề viết cho mắt nhìn trên mảng lớn
   ("Phiếu xác nhận lịch hẹn"), nhét vào SMS thì cụt nghĩa. Thêm trường `sms_lead`
   riêng cho từng loại.

### Một chỗ chỉnh nhỏ

Giờ hẹn nay có hai cách viết: bản có dấu chấm giữa (`09:00 · Thứ 6, 21/08/2026`)
dùng trong BẢNG nơi nó đứng một mình, và bản văn xuôi (`09:00 Thứ 6, ngày
21/08/2026`) dùng khi giờ hẹn nằm giữa câu, ở đó dấu chấm giữa đọc rất cợn.

### Bản xem trước

`preview_confirmation_email.py` nay sinh sáu file trong `docs/mockups/`: một bản
mẫu còn `{{biến}}` cộng bản đã điền dữ liệu giả cho từng loại thư.

### Test

Thêm `test_reminder_email_is_personalised`, `test_otp_email_uses_same_shell` và
`test_lac_hong_watermark_asset_exists` (bài cuối là thứ duy nhất bắt được việc ai
đó xoá hay đổi tên ảnh chìm, vì lúc chạy thật thư chỉ lặng lẽ bỏ ảnh).

`pytest`: 347 passed, 6 skipped. `ruff` và `mypy` sạch.

---

## Đợt sửa thứ năm: phân hoá từng loại thư

Bốn loại thư lịch hẹn trước đó dùng chung khung nhưng nhìn giống hệt nhau, và thư
huỷ lịch đọc ra như thư mời. Đợt này mỗi loại có hình dạng riêng.

### Thư huỷ lịch: thư báo việc, không phải thư mời

| Trước | Sau |
|---|---|
| Mảng vàng rực mang tên khách | Thanh **xám** `#2A2A2A` mang **mã lịch** để đối chiếu |
| Có nút "Kiểm tra thông tin lịch của bạn" | Bỏ, vì không còn lịch nào để kiểm |
| Câu chữ nài kéo "ViVi vẫn ở đây và rất mong được gặp bạn" | Nói đúng việc, một lối quay lại, để khách tự quyết |

Đổ một mảng vàng rực lên đầu thư báo huỷ đọc ra như đang ăn mừng.

### Thư đổi giờ: làm nổi bật giờ mới

- Thanh trên đầu mang **giờ mới**, không phải tên khách.
- Tiêu đề thư có luôn giờ mới: `Lịch lái thử VF 8 đã đổi sang 09:00 Thứ 6, ngày 21/08/2026`.
- Trong card thêm hàng **"Giờ trước đây"** màu xám gạch ngang, ngay trên hàng
  **"Giờ hẹn mới"**. Mắt lướt qua là biết dòng nào đã cũ.
- Đoạn mở đầu tô vàng giờ mới.

Lấy được giờ cũ nhờ `bookings.rescheduled_from_booking_id` — lịch mới trỏ ngược về
lịch cũ. Đã bổ sung hai `LEFT JOIN` vào câu SELECT của `_render_notification`.
Không phải lúc nào cũng tra được (lịch cũ có thể đã bị xoá) nên hàng này có điều
kiện, thiếu thì bỏ hẳn.

### Thư nhắc lịch: khác hẳn thư xác nhận

Người nhận thư này đã đọc thư xác nhận rồi, họ chỉ cần liếc một cái là biết mấy
giờ và cần cầm theo gì. Vì vậy:

- Thanh trên đầu mang **giờ hẹn**, không phải tên khách.
- **Bỏ** đoạn giới thiệu xe và lưới ảnh. Thư ngắn hẳn.
- Đoạn nhắc dài thay bằng **ba dòng dặn mang theo** có dấu đầu dòng vàng.

### Thư mã xác thực: trả về đơn giản

Bê nguyên bố cục thư lịch hẹn sang là sai: thư này chỉ có một việc là đưa sáu chữ
số cho người ta chép, mà thanh nav, bảng năm hàng và lưới ảnh thì chôn mất cái mã.

Nay chỉ còn: logo, tiêu đề, một câu, **một khối mã** (chữ số 44px màu vàng, giãn
10px cho khỏi nhầm 0 với O, có ảnh chìm Lạc Hồng), một đoạn nhắc bảo mật, chân thư.
Không thanh nav, không thanh trên đầu, không nút. Font, màu và khung vẫn lấy
nguyên từ thư xác nhận nên vẫn cùng một nhà.

### Nút vàng nổi lên

Trước đây nút và thanh tên khách dùng **cùng một màu vàng**; mảng vàng lớn của
thanh hút hết mắt nên nút chìm nghỉm. Nay tách hai sắc độ:

| Vai trò | Màu |
|---|---|
| Thanh trên đầu | `#F5C542` |
| **Nút** | **`#FFD24A`** + mép trên `#FFE9A8`, đệm rộng hơn |

Nút thành chỗ sáng nhất thư và tự nhảy ra trước.

### Kiểm tra

Năm bản xem trước, đo ở 390px và 320px: `scrollWidth` bằng đúng bề ngang khung ở
cả mười trường hợp, không tràn ngang. `pytest` 347 passed. `ruff` và `mypy` sạch.

---

## Đợt sửa thứ sáu: chốt câu chữ và thống nhất thanh trên đầu

### Thanh trên đầu luôn mang TÊN KHÁCH

Đợt trước cho thanh mang giờ hẹn ở thư nhắc lịch và thư đổi giờ, mang mã lịch ở
thư huỷ. Bỏ cách đó: mỗi thư một kiểu thì mở ra không biết đang nhìn cái gì. Tên
khách ở đúng một chỗ cố định thì thư nào cũng đọc ra ngay là "thư này gửi cho
mình". Chỉ còn SẮC ĐỘ thanh là đổi: vàng cho thư báo tin, xám cho thư huỷ.

Gỡ luôn trường `bar_value` vì chỉ còn một giá trị.

### Thư nhắc lịch

- Tiêu đề `ViVi nhắc bạn / lịch lái thử`, thêm chữ ViVi ở đầu.
- Đoạn mở đầu **tô vàng giờ hẹn**. Vì thanh trên đầu nay mang tên khách nên giờ
  hẹn cần được nhấn ở chỗ khác. Đoạn này có hai chỗ tô vàng (giờ hẹn và tên xe),
  nhiều hơn quy ước một chỗ mỗi thư, nhưng thư nhắc lịch thì cả hai đều đáng nhớ.
- Ba dòng dặn mang theo đổi lại thành một đoạn văn theo đúng câu chủ dự án đưa.
  Gỡ hàm `_checklist_html()` vì không còn ai dùng.

### Thư huỷ lịch

- Thanh xám mang tên khách thay cho mã lịch.
- Câu thứ hai của đoạn mở đầu: "Thông tin của lịch vừa huỷ được ViVi gửi đến bạn
  bên dưới, để bạn đối chiếu."
- Tiêu đề card: "ViVi gửi bạn / **thông tin lịch đã huỷ**". Thêm trường
  `card_title` vào `_DarkCopy` vì thư huỷ không thể dùng chung chữ "thông tin
  lịch hẹn" như thư báo tin.
- Đoạn nhắc viết lại theo câu chủ dự án đưa, có mở lời mời quay lại.

### Thư đổi giờ

Thanh trên đầu trả về tên khách. Bố cục còn lại giữ nguyên: hàng "Giờ trước đây"
gạch ngang ngay trên hàng "Giờ hẹn mới", và giờ mới vẫn được tô vàng trong đoạn
mở đầu.

### Thư mã xác thực

"để hoàn tất bước đăng ký lái thử" đổi thành "để hoàn tất bước xác thực của bạn".

`pytest` 347 passed. `ruff` và `mypy` sạch.

---

## Đợt sửa thứ bảy: rà lại thông số xe trong đoạn giới thiệu

Chủ dự án nhìn bản mẫu và tưởng thông số bị đặt cứng. Rà xong ra ba việc.

### Việc 1: bộ render KHÔNG đặt cứng, nhưng bản mẫu làm người ta hiểu nhầm

`_vehicle_paragraph()` vẫn đọc `battery_capacity_kwh`, `estimated_range_km`,
`motor_power_kw` từ `vehicle_variants` theo đúng phiên bản khách đặt. Kiểm chứng
bằng cách dựng đoạn văn cho cả mười phiên bản trong `data/app.db`, mỗi phiên bản
ra một câu khác nhau:

    VF 3 Eco   18,4 kWh · 210 km · 32 kW
    VF 8 Plus  87,7 kWh · 447 km · 300 kW
    VF 9 Plus  123 kWh · 580 km · 300 kW

Vấn đề nằm ở `preview_confirmation_email.py`: bản MẪU điền số thật (5 chỗ, 82 kWh,
300 kW, 420 km) cạnh các ô `{{ten_model_xe}}`, nhìn vào đúng là ra vẻ đặt cứng.
Nay bản mẫu để `{{so_cho}}`, `{{pin_kwh}}`, `{{cong_suat_kw}}`, `{{quang_duong_km}}`
đúng như các ô khác. Bản xem trước thì đổi sang **số thật của VF 8 Plus lấy từ
`data/app.db`** — trước đây số ở đó cũng không khớp với cơ sở dữ liệu.

Kèm theo: `_vi_number()` nay trả nguyên xi khi gặp giá trị không phải số, để bản
mẫu truyền được chuỗi `{{...}}` và để dữ liệu bẩn không làm hỏng cả lượt gửi thư.

### Việc 2: LỖI THẬT — `seat_count` bỏ trống ở mọi mẫu xe

`seed_dev_db.py` không hề seed cột `seat_count`, nên nó `NULL` ở cả sáu mẫu. Hệ
quả: thư xác nhận **không bao giờ nói được xe mấy chỗ**, mệnh đề đó bị bỏ im lặng.
Đây là loại lỗi chỉ lộ ra khi ngồi đọc kỹ thư đã gửi.

Đã bổ sung cột vào câu INSERT và điền số chỗ, nguồn lấy từ `site_catalog.py`:
VF 3 bốn chỗ, VF 9 bảy chỗ, còn lại năm chỗ. Đã cập nhật luôn `data/app.db` đang
có sẵn để khỏi phải seed lại.

### Việc 3: khoá lại bằng test

- `test_vehicle_paragraph_reads_specs_per_variant` — hai phiên bản khác nhau phải
  ra hai đoạn văn khác nhau, và thông số thiếu thì bỏ hẳn mệnh đề chứ không đoán.
- `test_confirmation_email_is_personalised` thêm hai phép kiểm `5 chỗ` và
  `59,6 kWh` để bắt được nếu ai đó lại làm rơi thông số.
- `conftest.py` seed thêm `seat_count`, nếu không bài kiểm trên không chạy được.

`pytest` 348 passed. `ruff` và `mypy` sạch.

---

## Đợt sửa thứ tám: rà trường dữ liệu trên toàn bộ template

### Backend đã phủ đủ

Đối chiếu các loại thông báo hệ thống thực sự ghi vào `notification_jobs` với
`_BOOKING_COPY`: **7/7 có mặt, không thừa không thiếu**.

    booking_confirmation · booking_update · cancellation_confirmation
    reminder · reminder_24h · reminder_2h · reschedule_confirmation

### Sinh bản mẫu cho tất cả, không chỉ thư xác nhận

Trước đây chỉ thư xác nhận có bản `{{biến}}`, còn `booking_update` thì không có
bản nào. Nay mỗi loại ra hai file: `<tên>.html` giữ nguyên ô điền để đối chiếu
danh sách trường, và `<tên>.preview.html` đã điền dữ liệu giả.

### Lỗi cùng loại với chuyện thông số: giờ hẹn cũng hiện số thật

Bản mẫu in ra `09:00 · Thứ 6, 21/08/2026` thay vì `{{thoi_gian_hen}}`, y hệt
chuyện thông số xe hôm trước. Giờ hẹn không truyền thẳng chuỗi `{{...}}` vào được
vì bộ render phải phân tích ngày giờ thật để biết thứ mấy, nên `_mask_dates()`
dựng bằng ngày thật rồi thay ngược lại thành ô điền. Chuỗi để thay lấy từ chính
`_booking_facts()` chứ không gõ tay, để bản mẫu không lệch khi ai đó đổi cách viết
ngày giờ.

### Bảng đối chiếu sau khi sửa

| Trường | xác nhận | nhắc lịch | đổi giờ | cập nhật | huỷ lịch | mã xác thực |
|---|---|---|---|---|---|---|
| ho_ten_khach, ma_lich_hen, thoi_gian_hen, email_khach, sdt_khach, ten_showroom, dia_chi_showroom, ten_nv, sdt_nv, ten_model_xe | có | có | có | có | có | · |
| phien_ban, so_cho, pin_kwh, cong_suat_kw, quang_duong_km | có | · | có | có | · | · |
| gio_truoc_day | · | · | có | · | · | · |
| ma_xac_thuc, hieu_luc_phut | · | · | · | · | · | có |

Mọi khoảng trống đều có chủ ý: thư nhắc lịch và thư huỷ cố ý bỏ đoạn giới thiệu
xe nên không có thông số; thư đổi giờ có thêm giờ cũ; thư mã xác thực không nói
về lịch hẹn nào cả.

### Khoá lại bằng test

`test_every_booking_template_carries_the_same_fields` chạy cho cả bảy loại: dựng
thư bằng một hàng dữ liệu mà mỗi trường mang một chuỗi đánh dấu riêng, rồi kiểm
từng chuỗi có mặt trong HTML không. Thông số xe phải có mặt **đúng khi và chỉ khi**
`show_vehicle` bật; hàng giờ cũ phải có mặt đúng khi và chỉ khi là thư đổi giờ.

Bài này bắt được trường hợp ai đó tắt nhầm một khối và làm rơi thông tin — loại
lỗi im lặng, thư vẫn gửi đi bình thường chỉ là cụt nội dung.

Ghi chú khi viết bài kiểm: dùng chuỗi đánh dấu chứ không dùng số. Lần đầu dùng
`222` thì nó trùng với giá trị trong CSS của thư, bài kiểm báo đúng trong khi
thật ra sai.

`pytest` 355 passed. `ruff` và `mypy` sạch.
