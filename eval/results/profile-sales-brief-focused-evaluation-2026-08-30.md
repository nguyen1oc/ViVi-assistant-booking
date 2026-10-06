# Focused Evaluation — Post-booking Profile → Sales Brief

## Phạm vi

Bộ đánh giá riêng gồm 10 case, không thay đổi và không cộng vào baseline 61 case chính thức. Mỗi case chạy trên database cô lập theo đúng chuỗi:

`confirmed booking → chat post-booking → update_post_booking_signals → signal trong DB → portal generate_sales_brief → brief lưu DB`

Một case chỉ pass khi đồng thời đạt:

1. chọn đúng skill/tool;
2. payload chứa các field nghiệp vụ bắt buộc;
3. signal đúng tồn tại hoặc không tồn tại trong DB;
4. Sales Brief chứa đủ dữ kiện đúng;
5. Sales Brief không giữ dữ kiện đã sửa/rút lại và không suy diễn thêm vai trò.

Không dùng LLM judge. Tất cả kết quả được chấm bằng trace tool, truy vấn DB và assertion nội dung brief.

## Kết quả

- Strict end-to-end success: **1/10 = 10%**.
- Regression success: **1/3 = 33,33%**; challenge success: **0/7 = 0%**.
- Intent và skill accuracy: **10/10 = 100%** cho từng metric.
- Tool selection: **9/10 = 90%**.
- Required argument match và exact match: **5/10 = 50%**; mean field F1 **0,55**.
- Response requirement pass: **7/10 = 70%**.
- Toàn bộ assertion DB + brief: **2/10 = 20%**; xét riêng từng assertion là **17/33 = 51,52%**.
- Clean execution: **9/10 = 90%**; first expected-tool outcome: **8/10 = 80%**; retry và unexpected-tool-error cùng **1/10 = 10%**.
- P50 latency: **9.789,10 ms**; P95: **15.192,99 ms**; P99: **16.188,12 ms**.
- Token của 10 prediction cuối được chấm: **184.632**.
- Estimated agent cost của 10 prediction cuối: **$0.03964450**; không gồm judge/hạ tầng.

## Cách tính metric

### Nguyên tắc chung

- Mẫu số của metric tỷ lệ chỉ gồm case có kết quả chấm xác định; case `not_run` hoặc check có giá trị `null` không bị đổi thành fail.
- Công thức chung: `Rate = số case pass / số case được chấm`.
- Mỗi case dùng database SQLite cô lập. Evidence lấy trực tiếp từ tool-call trace, payload tool, trạng thái signal trong DB và Sales Brief đã lưu trong `booking_profile_summaries`.
- Không dùng LLM-as-judge hoặc đánh giá cảm tính trong bộ này. Việc chuẩn hóa chuỗi chỉ phục vụ so khớp không phân biệt hoa/thường và dấu câu; không tự cho điểm vì hai câu “có vẻ giống nhau”.

### 1. Strict end-to-end task success

Với mỗi case:

`Case pass = Intent ∧ Skill ∧ Tool ∧ Required arguments ∧ Response requirements ∧ Action error ∧ Clean execution ∧ All DB/Brief assertions`

Nếu case khai báo forbidden behavior hoặc groundedness thì các check đó cũng phải pass. Chỉ cần một thành phần fail là cả case fail, không cộng điểm từng phần.

`Strict task success = số case pass toàn bộ / số case được chấm = 1/10 = 10%`

Khoảng tin cậy Wilson 95% được tính với `n=10`, `success=1`, `z=1,96`, cho kết quả **1,79%–40,42%**. Khoảng rộng vì mẫu chỉ có 10 case; không được diễn giải 10% là độ chính xác sản xuất tuyệt đối.

Hai nhóm được báo riêng để case dễ không che case khó:

- `Regression success = regression case pass / regression case được chấm = 1/3 = 33,33%`.
- `Challenge success = challenge case pass / challenge case được chấm = 0/7 = 0%`.

### 2. Intent accuracy và skill accuracy

- `Intent accuracy = số case có functional intent quan sát được bằng expected intent / 10 = 10/10 = 100%`.
- `Skill accuracy = số case route đúng skill post_booking / 10 = 10/10 = 100%`.
- Independent classifier route cũng đạt **10/10**, bằng cách so `outer_intent=domain` và `sub_intent` với tập route post-booking được chấp nhận.

Bộ này chỉ tập trung post-booking nên 100% ở intent/skill cho biết route đúng trong phạm vi hẹp, không chứng minh classifier tốt trên toàn bộ intent của sản phẩm.

### 3. Tool selection accuracy

Một case pass khi expected tool xuất hiện trong tool trace; tool gọi thất bại vẫn được kiểm tra riêng ở execution metric.

`Tool accuracy = số case có expected tool / số case được chấm = 9/10 = 90%`

### 4. Argument accuracy

Evaluator chuẩn hóa key/value rồi so payload của lần gọi expected tool cuối cùng với golden contract. Field được tính là matched khi key đúng và value đúng; field được khai báo `allowed_extra_arguments` không bị phạt.

- `Required match của một case = matched required fields = total required fields`.
- `Exact match của một case = required match và không có unexpected extra field`.
- `Field precision = matched fields / actual fields được chấm`.
- `Field recall = matched fields / expected fields`.
- `Field F1 = 2 × precision × recall / (precision + recall)`; báo cáo lấy trung bình F1 của các case.

Kết quả: required match **5/10 = 50%**, exact match **5/10 = 50%**, mean field F1 **0,55**. Metric này phát hiện các alias hoặc schema sai như `primary_use_case`, `custom.family_attendee_count` và `guest_context`, kể cả khi backend có thể tự cứu dữ liệu cuối.

### 5. Response requirement pass rate

Mỗi case khai báo các cụm bắt buộc phải xuất hiện trong output cuối. Sau khi chuẩn hóa văn bản:

`Response pass = tất cả required terms đều xuất hiện`

`Response requirement rate = số case pass toàn bộ required terms / 10 = 7/10 = 70%`

Đây là kiểm tra nội dung tối thiểu, không thay thế kiểm tra DB và không tự chứng minh rằng toàn bộ brief đúng.

### 6. Database và Sales Brief assertions

Sau từng case, evaluator truy vấn DB thật trong môi trường cô lập để kiểm tra:

- profile signal phải tồn tại hoặc không được tồn tại;
- booking signal theo đúng `booking_id`, `subject`, `key`, `value`;
- Sales Brief đã được lưu;
- brief chứa đủ required terms, không chứa forbidden terms và không lặp quá giới hạn khai báo.

Primary metric chấm ở cấp case và không cho partial credit:

`DB + Brief pass rate = số case pass toàn bộ assertion / số case có assertion = 2/10 = 20%`

Chỉ số chẩn đoán ở cấp assertion là:

`Individual assertion pass rate = số assertion pass / tổng assertion = 17/33 = 51,52%`

Con số **20%** là release-gate chính; **51,52%** chỉ dùng xác định case đã đúng một phần ở đâu.

### 7. Execution quality

- `Clean execution`: không có unexpected tool error và không gọi lặp cùng một tool trong cùng turn. Kết quả **9/10 = 90%**.
- `First expected-tool outcome accuracy`: lần gọi expected tool đầu tiên thành công, hoặc chỉ trả lỗi đã được golden dự kiến. Kết quả **8/10 = 80%**.
- `Same-turn retry rate = case có cùng tool bị gọi nhiều hơn một lần trong một turn / 10 = 1/10 = 10%`.
- `Unexpected tool-error case rate = case có tool error ngoài expected contract / 10 = 1/10 = 10%`.
- `Top-level error rate = case kết thúc bằng lỗi không tạo được prediction / 10 = 0/10 = 0%`.

Vì một case có thể phục hồi sau tool error nên top-level error có thể bằng 0 nhưng clean execution vẫn fail.

### 8. Latency

Latency của một case là wall-clock từ lúc bắt đầu chuẩn bị fixture sau khi reset DB đến khi hoàn tất các turn, tool persistence, portal brief generation và lưu brief. Không tính thời gian tổng hợp report.

Với dãy latency đã sắp tăng dần, percentile dùng nội suy tuyến tính tại:

`rank = (n - 1) × percentile`

Kết quả trên 10 case:

- `P50 = 9.789,10 ms`: 50% case không chậm hơn mức này.
- `P95 = 15.192,99 ms`: 95% case không chậm hơn mức này theo phép nội suy.
- `P99 = 16.188,12 ms`.
- Median turn count **2**, P95 turn count **3**.

### 9. Token và cost

Token được cộng từ usage metadata thực tế của tất cả model call trong 10 prediction cuối được chọn, gồm classifier/agent và bước sinh Sales Brief:

- Input: **180.051 token**.
- Output: **4.581 token**.
- Tổng: `180.051 + 4.581 = 184.632 token`.

Cost tính riêng theo từng model:

`Model cost = input_tokens × input_rate / 1.000.000 + output_tokens × output_rate / 1.000.000`

- `gpt-4o-mini`: `29.338 × $0,15/M + 660 × $0,60/M = $0.00479670`.
- `gpt-5.6-luna`: `150.713 × $0,20/M + 3.921 × $1,20/M = $0.03484780`.
- `Total estimated agent cost = $0.00479670 + $0.03484780 = $0.03964450`.
- `Average cost per executed focused workflow = $0.03964450 / 10 = $0.00396445`.

Do 10/10 case đều chạy được bước tạo brief, `$0.00396445` cũng là chi phí trung bình cho một brief trong benchmark tập trung này. Đây **không phải** cost từ đầu booking đến Sales Profile vì fixture bắt đầu từ booking đã confirmed. Không lấy `$0.03964450 / 1 strict pass` làm chi phí kinh doanh. Cost không gồm LLM judge, DB/Redis/hosting, notification và nhân sự; đây là ước tính token nhân đơn giá cấu hình, không phải hóa đơn provider.

### 10. Metric không đo trong bộ focused này

Slot availability, double-booking, OTP/authorization, booking conversion, human rating, formal hallucination rate và cost per completed booking được ghi `NOT_RUN`, không đổi thành 0. Các metric đó thuộc bộ 61 case, negative suite hoặc cost workflow riêng. Bộ focused này chỉ dùng deterministic forbidden/required assertions để bắt suy diễn sai trong Sales Brief.

## Kết quả từng case

| Case | Strict | Dữ liệu/brief quan sát được |
|---|---:|---|
| Durable household only | Pass | Lưu `household_size=5`; không biến thành số người tham dự; brief đúng. |
| Whole family attends | Fail contract | DB và brief đúng 5 người, nhưng model gửi `custom.family_attendee_count` thay vì core keys; backend phải tự cứu payload. |
| Husband + two-year-old child | Fail brief | DB bắt đúng 2 người đi cùng và tổng 3 người, nhưng brief tự gợi ý người đi cùng cũng lái dù user không nói. |
| Household 6, only husband + child attend | Fail | LLM gửi guest count 2 đúng nhưng normalizer ghi đè thành 5; brief báo sai tổng 6 người tham dự. Có một tool retry do key/schema sai. |
| Correct attendance from 6 to 3 | Fail partial | Booking guest count được sửa đúng thành 2, nhưng câu “cả nhà 6 người” không được lưu thành durable household fact nên brief thiếu dữ kiện gia đình. |
| Child no longer attends | Fail | Guest count sửa về 1 nhưng context vẫn chứa “bé 2 tuổi không tham dự”; heuristic lại tái tạo child fact và brief tiếp tục chuẩn bị ghế trẻ em. |
| Husband drives instead of booker | Fail | LLM gửi `booker_will_drive=false` đúng; normalizer ghi đè thành `true` và brief nói booker vẫn trực tiếp lái. |
| Colloquial primary use | Fail contract | Nội dung đưa đón con/đi làm/nội thành có trong brief, nhưng lưu bằng alias `primary_use_case` thay vì canonical `primary_use`. |
| Newly licensed + parking concern | Fail partial | Bắt được “mới có bằng” nhưng bỏ mất lo ngại đỗ xe lớn; brief cũng bỏ mất concern này. |
| Hypothetical child | Fail safety/quality | Câu giả định bị normalizer biến thành fact thật `Trẻ em 2 tuổi đi cùng`; brief hiển thị và đề nghị mang ghế trẻ em. |

## Nguyên nhân chính

### 1. Tool boundary dùng regex theo từ khóa, chưa hiểu phủ định và giả định

- Thấy `em bé + đi cùng` là lưu fact, kể cả câu bắt đầu bằng “nếu giả sử”.
- Thấy `chồng + lái thử` là ép booker cũng lái, kể cả câu “chồng lái thay tôi”.
- Thấy household size và một cụm attendance trong cùng câu là dùng household size làm attendance total, dù câu nói chỉ một phần gia đình tham dự.

### 2. Canonical schema chưa đủ

Model sinh `custom.family_attendee_count`, `primary_use_case`, `guest_context` hoặc category/key không hợp contract. Một số alias được backend cứu, một số bị lỗi/retry hoặc không được Sales Brief hiểu ổn định.

### 3. Correction/retraction chưa có semantic operation chắc chắn

Model thường dùng `revise` với một câu chứa phủ định thay vì `retract` fact cũ rồi add fact mới. Brief renderer chỉ nhìn từ khóa trong text nên vẫn hiểu câu phủ định như dữ kiện dương.

### 4. Brief renderer suy diễn bằng keyword trên toàn bộ văn bản

Điều kiện kiểu “có từ chồng ở một chỗ và từ lái ở một chỗ khác” tạo gợi ý chồng sẽ lái. Tương tự, chỉ cần thấy “bé/2 tuổi” — kể cả trong câu “bé không đi” — là sinh chuẩn bị ghế trẻ em.

## Hướng sửa ưu tiên

1. Thay regex bổ sung signal bằng parser ngữ nghĩa có scope: `asserted`, `negated`, `hypothetical`, `corrected`.
2. Không để normalizer ghi đè một core signal hợp lệ model đã gửi; chỉ canonicalize alias và reject mâu thuẫn rõ ràng.
3. Định nghĩa registry canonical cho các profile keys thường dùng, tối thiểu `household_size`, `primary_use`, `driving_experience`, `parking_concern`.
4. Với correction/retraction, cập nhật theo key/subject bằng operation rõ ràng; không lưu câu phủ định vào positive context.
5. Brief chỉ tạo recommendation từ typed values, không tìm từ khóa trên chuỗi ghép toàn bộ facts.
6. Giữ bộ 10 case này làm release gate riêng; không thay thế điểm baseline 61 case.

## Artifact

- Dataset: `eval/golden/profile_sales_brief_cases.json`
- Final merged predictions: `artifacts/agent-evaluation/profile-sales-brief-focused-final-predictions.json`
- Machine-readable report: `artifacts/agent-evaluation/profile-sales-brief-focused-report.json`
- Generated report: `artifacts/agent-evaluation/profile-sales-brief-focused-report.md`
