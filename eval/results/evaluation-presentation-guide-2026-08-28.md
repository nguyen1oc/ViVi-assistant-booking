# Phần Evaluation — nội dung cho 2 slide

Ngày chốt số liệu: **28/08/2026**

Ngày trình bày: **____/____/2026**

Thời lượng đề xuất: **3–4 phút**

## Slide 1 — Phương pháp Evaluation

### Nội dung đưa lên slide

**Phạm vi kiểm thử**

- **61** behavioral cases: 49 regression + 12 challenge.
- **16** negative fixtures: auth, OTP, cross-customer, double booking.
- **10** booking E2E để đo completion, token và cost.
- Chạy toàn bộ 61 case **3 lần** để đo độ ổn định.

**Cách đo**

- Mỗi case chạy trên **database snapshot cô lập**.
- Lưu classifier, tool call, arguments, tool result, response, DB assertion, token và latency.
- Deterministic checks cho nghiệp vụ/an toàn; LLM judge cho groundedness/hallucination.

**10 metric chính**

`Task success` · `Intent` · `Tool` · `Arguments` · `Slot availability`

`Double booking` · `Hallucination` · `Auth/OTP` · `P95 latency` · `Cost/booking`

### Lời thuyết trình

“Evaluation không chỉ kiểm tra câu trả lời cuối mà theo dõi toàn bộ quá trình từ hiểu yêu cầu đến hoàn tất booking. Bộ chính gồm 61 case, có thêm 16 negative fixture cho bảo mật và xung đột, cùng 10 workflow booking E2E để đo chi phí thực tế.

Mỗi case chạy trên database snapshot cô lập. Evaluator lưu classifier route, tool, arguments, tool result, response, trạng thái database, token và latency. Những rule xác định được bằng code sẽ chấm deterministic; groundedness và hallucination dùng LLM judge dựa trên evidence. Toàn bộ 61 case được chạy ba lần để tránh kết luận từ một lần chạy may mắn.”

### Nếu cần giải thích nhanh cách tính metric

- **Task success:** case đạt đồng thời intent, tool, argument, response, DB/policy và clean execution chia 61 case.
- **Intent:** classifier route đúng chia 44 case ngôn ngữ tự nhiên có thể chấm độc lập.
- **Tool/Argument:** đúng tool và đúng các field trong golden contract.
- **Slot:** slot hợp lệ theo DB và slot được hold phải xuất hiện trong kết quả search.
- **Hallucination:** case bị judge xác định không grounded chia case có judge evidence.
- **Cost:** tổng agent cost của 10 booking hoàn tất chia đúng 10; không tính judge và hạ tầng.

---

## Slide 2 — Kết quả và kết luận

### Nội dung đưa lên slide

| Chỉ số | Kết quả |
|---|---:|
| Booking Task Success | **59/61 = 96,72%** |
| Challenge / Tool selection | **12/12 / 61/61** |
| Intent accuracy | **43/44 = 97,73%** |
| Slot precision / selected recall | **306/306 / 10/10** |
| Hallucination / Auth-OTP violation | **0/20 / 0/8** |
| Completed booking | **10/10** |
| P95 latency | **10.236,37 ms** |
| Cost/completed booking | **$0.001587** |
| Stability: mean / pass-all-3 | **96,72% / 95,08%** |
| Backend tests | **634/634 pass** |

**Hallucination fix:** `POSTBOOK-KNOWLEDGE-001` từ fail 3/3 → **pass 3/3**; hallucination từ **5% → 0%**.

**Còn lại:** profile signal fail 3/3; hai case search/multi-turn chưa ổn định; human review và browser E2E **NOT_RUN**.

### Lời thuyết trình

“Baseline hiện đạt 59 trên 61 case, tương đương 96,72%. Tool selection đạt 100%, intent đạt 97,73%, toàn bộ 306 slot được trả về đều hợp lệ và 10 trên 10 slot được booking đã xuất hiện trong search. Mười workflow đều hoàn tất trong database.

Chi phí được tính bằng tổng agent cost 0,01586620 đô chia cho 10 booking hoàn tất, bằng 0,001586620 đô, làm tròn 0,001587 đô mỗi booking. P95 latency là khoảng 10,24 giây.

Lỗi hallucination cũ đến từ việc model thêm điều khoản ngoài knowledge evidence. Sau khi ưu tiên fact đúng model/topic, khóa phần factual response theo provenance và bổ sung trusted server context cho judge, case này pass ba trên ba lần; hallucination toàn bộ tập được chấm giảm từ 5% xuống 0%.

Tuy nhiên, kết quả chưa đủ để tuyên bố production-ready: còn một lỗi profile signal ổn định, hai case search/multi-turn chưa ổn định, chưa có human review và browser E2E. Vì vậy 96,72% là baseline trên bộ synthetic 61 case, không phải accuracy của toàn bộ traffic production.”

### Câu kết

> “Evaluation hiện đủ khách quan để làm baseline kỹ thuật: có mẫu số, evidence và stability rõ ràng; kết quả là 96,72%, hallucination 0/20 và 10/10 booking hoàn tất, nhưng các failure và phần NOT_RUN vẫn được giữ nguyên để định hướng công việc tiếp theo.”

## Ba câu trả lời dự phòng

**61 case có phủ toàn bộ không?**

Không. Đây là synthetic regression baseline; chưa phủ mọi hội thoại dài, lỗi provider, tải production và hành vi người dùng thật.

**Cost có đúng là trung bình 10 booking không?**

Đúng: `$0.01586620 / 10 = $0.001586620` mỗi booking; không gồm judge và hạ tầng.

**Hallucination 0% có nghĩa là không bao giờ bịa không?**

Không. Nó chỉ có nghĩa 0/20 case có judge evidence bị phát hiện hallucination trong benchmark và ba run hiện tại.
