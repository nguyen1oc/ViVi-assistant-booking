# Calculator Tool

## Mô tả (Description)
Tính toán các biểu thức toán học một cách an toàn bằng cách phân tích cú pháp AST (Abstract Syntax Tree), thay vì sử dụng hàm `eval()` vốn tiềm ẩn nhiều rủi ro bảo mật. 
Công cụ này hỗ trợ Agent giải quyết các câu hỏi yêu cầu tính toán số học chính xác.

## Hỗ trợ các phép toán
* Phép cộng (`+`)
* Phép trừ (`-`)
* Phép nhân (`*`)
* Phép chia (`/`)
* Phép chia lấy nguyên (`//`)
* Phép chia lấy dư (`%`)
* Phép lũy thừa (`**`)
* Dấu ngoặc đơn `()` để thay đổi thứ tự ưu tiên

## Tham số đầu vào (Arguments)
* `expression` (str): Biểu thức toán học dạng chuỗi cần tính toán (ví dụ: `"2 * (3 + 4)"`).

## Kết quả trả về (Returns)
* `str`: Kết quả tính toán dưới dạng chuỗi số, hoặc thông báo lỗi nếu biểu thức không hợp lệ hoặc chứa các phép toán không được hỗ trợ.

## Ví dụ sử dụng (Usage Examples)
```python
from src.agents.tools import calculate

result = calculate.invoke({"expression": "2 * (3 + 4) - 5"})
print(result)
# Output: "9"
```
