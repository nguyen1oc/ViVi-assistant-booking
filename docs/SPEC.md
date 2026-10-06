# ViVi - Bản đặc tả tính năng theo khái niệm

**Tài liệu mô tả đầy đủ các tính năng của dự án**

- **Mã dự án:** P-053
- **Nhóm thực hiện:** Du lịch Hà Nội
- **Phiên bản tài liệu:** 2.0 - Bản đặc tả theo khái niệm
- **Ngày hoàn tất:** 31/08/2026
- **Tài liệu nền:** [Tài liệu yêu cầu sản phẩm chính thức](PRD.md)
- **Phạm vi:** Trang thông tin công khai, quy trình đặt và quản lý lịch lái thử, ViVi chăm sóc sau xác nhận, đường dẫn dành cho người lái, cổng vận hành showroom và các công cụ kiểm tra nội bộ.

---

## 0. Mục đích và cách đọc tài liệu

Nhóm em viết tài liệu này để mô tả toàn bộ tính năng đang có trong dự án bằng ngôn ngữ thông dụng. Mỗi tính năng được trình bày theo giá trị mà người dùng nhận được, thay vì mô tả cách lập trình hoặc tên công nghệ phía sau. Một người không làm công nghệ vẫn có thể đọc tài liệu và hiểu sản phẩm có những phần nào, ai được sử dụng và điều gì phải xảy ra khi tính năng hoạt động đúng.

Đây là bản đặc tả theo khái niệm. Tài liệu không quy định màu sắc, kích thước nút, vị trí từng điểm ảnh hoặc cách tổ chức mã nguồn. Những chi tiết đó có thể thay đổi trong quá trình hoàn thiện giao diện, nhưng mục đích, quyền sử dụng và quy tắc của mỗi tính năng phải được giữ nguyên.

Nhóm em đã đối chiếu tài liệu yêu cầu sản phẩm với trang web công khai, quy trình đặt lịch, phần gửi thư điện tử, đường dẫn dành cho người lái, cổng vận hành showroom và công cụ đánh giá nội bộ. Một số phần đã có đầy đủ trong sản phẩm, một số phần đã có nền tảng nhưng vẫn cần thêm dữ liệu hoặc cấu hình trước khi dùng với khách hàng thật. Tài liệu ghi rõ sự khác biệt này để người đọc không hiểu nhầm bản trình diễn là một hệ thống đã sẵn sàng vận hành chính thức.

### 0.1 Cách hiểu mức hoàn thiện

| Mức hoàn thiện | Cách hiểu |
|---|---|
| Đã có trong sản phẩm | Người dùng đã có thể nhìn thấy hoặc thực hiện tính năng trong phiên bản hiện tại. |
| Đã có nền tảng, cần hoàn thiện | Phần xử lý chính đã có nhưng vẫn cần bổ sung dữ liệu, cấu hình, kiểm tra thực tế hoặc hoàn thiện giao diện trước khi dùng chính thức. |
| Chỉ dùng trong nội bộ | Tính năng phục vụ nhân viên, người quản lý hoặc người đánh giá; khách hàng không nhìn thấy phần này. |
| Chỉ dùng để trình diễn | Tính năng giúp nhóm giới thiệu hành trình mẫu và không tạo lịch thật cho khách hàng. |

### 0.2 Các nhóm người sử dụng

| Nhóm người sử dụng | Vai trò trong sản phẩm |
|---|---|
| Người xem xe | Người dùng xem thông tin xe, giá tham khảo, màu sắc, hình ảnh, thông tin sạc và hậu mãi. |
| Người đặt lịch | Người dùng chọn xe, showroom và thời gian; người này có quyền quản lý lịch sau khi xác minh. |
| Người lái | Người trực tiếp lái thử. Người lái có thể là người đặt hoặc là một người khác được mời. |
| Nhân viên showroom | Nhân viên xem những lịch được giao và chuẩn bị đón khách trong phạm vi công việc của mình. |
| Quản lý showroom | Người quản lý lịch, nhân sự và xe thử tại một showroom được cấp quyền. |
| Người quản trị vận hành | Người quản lý dữ liệu và hoạt động trên toàn bộ hệ thống. |
| Người đánh giá nội bộ | Người kiểm tra độ đúng, mức an toàn và chất lượng câu trả lời bằng bộ tình huống riêng. |

---

## 1. Trang thông tin công khai và khám phá xe

### 1.1 Bảng đặc tả tính năng

| Mã | Tên tính năng | Người sử dụng | Mô tả theo khái niệm | Quy tắc quan trọng | Mức hoàn thiện |
|---|---|---|---|---|---|
| WEB-01 | Điều hướng chung | Người xem xe | Trang web cung cấp thanh điều hướng để người dùng đi tới danh mục xe, ViVi, công nghệ, hệ sinh thái, hậu mãi, pin và trạm sạc. | Nút đặt lịch phải luôn dẫn tới đúng quy trình đặt lịch. Nếu người dùng đang xem một mẫu xe, hệ thống phải giữ lại mẫu xe đó khi mở trang đặt lịch. | Đã có trong sản phẩm |
| WEB-02 | Trình đơn dành cho điện thoại | Người xem xe | Trang web chuyển thanh điều hướng thành một trình đơn gọn khi màn hình hẹp, để người dùng vẫn truy cập được đầy đủ nội dung. | Người dùng phải mở, đóng và di chuyển trong trình đơn bằng thao tác chạm hoặc bàn phím. | Đã có trong sản phẩm |
| WEB-03 | Giới thiệu thương hiệu trên trang chủ | Người xem xe | Trang chủ giới thiệu định hướng thương hiệu, dải sản phẩm, nhà máy, hệ sinh thái sử dụng xe và lời mời đăng ký lái thử. | Nội dung thương hiệu không được che khuất lối vào danh mục xe hoặc lối đặt lịch. | Đã có trong sản phẩm |
| WEB-04 | Câu chuyện bằng hình ảnh và chuyển động | Người xem xe | Trang chủ sử dụng phim, hình ảnh chuyển động, phần giới thiệu Lạc Hồng và hành trình ViVi để tạo trải nghiệm trực quan. | Người dùng có quyền giảm chuyển động. Khi thiết bị yếu hoặc tệp hình ảnh chưa tải được, nội dung chữ và đường dẫn chính vẫn phải dùng được. | Đã có trong sản phẩm |
| WEB-05 | Danh mục theo nhóm sản phẩm | Người xem xe | Người dùng có thể chuyển giữa xe cá nhân và dòng xe dịch vụ để giảm số mẫu xe phải xem cùng lúc. | Mỗi mẫu xe chỉ xuất hiện trong nhóm phù hợp với dữ liệu danh mục. | Đã có trong sản phẩm |
| WEB-06 | Thẻ tóm tắt mẫu xe | Người xem xe | Mỗi thẻ xe hiển thị tên, nhóm xe, hình ảnh, giá tham khảo và một số thông tin nổi bật để người dùng so sánh nhanh. | Nếu một dữ liệu chưa được công bố, trang web phải nói rằng thông tin đang được cập nhật thay vì tự điền một con số. | Đã có trong sản phẩm |
| WEB-07 | Xem trước màu xe trong danh mục | Người xem xe | Khi dữ liệu màu có sẵn, người dùng có thể xem nhanh các màu ngoại thất ngay trên thẻ xe. | Màu được hiển thị phải đi cùng đúng hình ảnh của mẫu xe. | Đã có trong sản phẩm |
| WEB-08 | Trang chi tiết mẫu xe | Người xem xe | Mỗi mẫu xe có một trang riêng để trình bày tổng quan, giá, điểm nổi bật, hình ảnh, màu sắc, thông số và lối đặt lịch. | Trang chi tiết phải lấy đúng dữ liệu của mẫu xe trong đường dẫn và phải báo rõ khi mẫu xe không tồn tại. | Đã có trong sản phẩm |
| WEB-09 | Giá theo phiên bản | Người xem xe | Trang chi tiết có thể trình bày nhiều mức giá tương ứng với từng phiên bản của cùng một mẫu xe. | Giá phải ghi rõ tính chất tham khảo và không được biến thành lời cam kết bán hàng. | Đã có trong sản phẩm |
| WEB-10 | Bộ chọn màu ngoại thất | Người xem xe | Người dùng chọn một màu để xem hình ảnh xe thay đổi theo màu đã chọn. | Trang web chỉ hiển thị màu có tên và hình ảnh hợp lệ. Khi chưa đủ dữ liệu, trang web phải hiển thị trạng thái đang cập nhật. | Đã có trong sản phẩm |
| WEB-11 | Thư viện hình ảnh và phim về xe | Người xem xe | Trang chi tiết sắp xếp hình ảnh ngoại thất, nội thất, công nghệ và phim giới thiệu thành các phần dễ theo dõi. | Hình ảnh phải thuộc đúng mẫu xe và phải có nội dung thay thế để người dùng không nhìn thấy hình vẫn hiểu được. | Đã có trong sản phẩm |
| WEB-12 | Mô hình xe ba chiều | Người xem xe | Một số mẫu xe có mô hình để người dùng xoay và quan sát từ nhiều góc. Trang thông tin sạc cũng có thể hiển thị mô hình trụ sạc. | Tính năng chỉ xuất hiện khi dự án có tệp mô hình hợp lệ. Hình ảnh tĩnh phải thay thế được mô hình nếu thiết bị không hỗ trợ. | Đã có nền tảng, cần hoàn thiện |
| WEB-13 | Thông số và tài liệu xe | Người xem xe | Trang chi tiết trình bày các nhóm thông số quan trọng và tên tài liệu nguồn để người dùng biết thông tin đến từ đâu. | Trang web không được tạo thông số còn thiếu. Tên tài liệu phải nói rõ khi nguồn đang được cập nhật. | Đã có nền tảng, cần hoàn thiện |
| WEB-14 | Điều hướng sang mẫu xe tiếp theo | Người xem xe | Cuối trang chi tiết, người dùng có thể chuyển sang một mẫu xe khác mà không phải quay lại đầu danh mục. | Mẫu xe tiếp theo phải có trong danh mục đang hoạt động. | Đã có trong sản phẩm |
| WEB-15 | Trang pin và trạm sạc | Người xem xe | Trang này cung cấp thông báo dịch vụ, mạng lưới sạc, đơn giá, các loại trụ, thiết bị sạc tại nhà, nguyên tắc sử dụng pin và đầu mối hỗ trợ. | Thông tin chính sách và đơn giá phải lấy từ nội dung còn hiệu lực. Tài liệu nguồn phải mở được khi người dùng cần kiểm tra. | Đã có trong sản phẩm |
| WEB-16 | Trang hậu mãi | Người xem xe | Trang này trình bày phạm vi bảo hành, bảo hành pin, phụ tùng, trường hợp loại trừ, câu hỏi thường gặp và đầu mối dịch vụ khách hàng. | Nội dung phải nêu rõ điều kiện áp dụng và không được thay thế xác nhận chính thức của hãng. | Đã có trong sản phẩm |
| WEB-17 | Đầu mối hỗ trợ trực tiếp | Người xem xe | Người dùng có thể gọi số hỗ trợ hoặc gửi thư điện tử từ trang pin, trạm sạc và hậu mãi. | Trang web phải dùng đầu mối chính thức và không tự tạo yêu cầu chuyển tiếp cho nhân viên. | Đã có trong sản phẩm |
| WEB-18 | Ghi nhớ vị trí đang xem | Người xem xe | Khi người dùng mở trang chi tiết rồi quay lại trang chủ, trang web đưa họ về gần đúng vị trí đã rời đi. | Việc khôi phục vị trí không được giành quyền cuộn khi người dùng đã bắt đầu thao tác. | Đã có trong sản phẩm |
| WEB-19 | Đi tới phần nội dung theo đường dẫn | Người xem xe | Một đường dẫn có tên phần có thể đưa người dùng tới đúng khu vực như danh mục xe, công nghệ hoặc hệ sinh thái. | Trang web phải chờ nội dung tải xong trước khi cuộn tới phần được yêu cầu. | Đã có trong sản phẩm |
| WEB-20 | Nút trở về đầu trang | Người xem xe | Sau khi người dùng cuộn qua phần đầu của trang chủ, một nút xuất hiện để đưa trang về đầu. | Nút không được che các hành động quan trọng trên trang chi tiết hoặc trang đặt lịch. | Đã có trong sản phẩm |
| WEB-21 | Cảnh báo mất kết nối | Tất cả người dùng công khai | Trang web kiểm tra định kỳ xem dịch vụ đặt lịch có hoạt động hay không và hiển thị cảnh báo khi kết nối bị gián đoạn. | Nội dung giới thiệu còn tải được vẫn phải hiển thị. Các thao tác cần dữ liệu thật phải tạm khóa và có nút thử lại. | Đã có trong sản phẩm |
| WEB-22 | Trang báo đường dẫn không tồn tại | Người xem xe | Khi người dùng mở một địa chỉ không có trong trang web, hệ thống giải thích tình trạng và cung cấp đường quay về trang chủ. | Trang web không được để người dùng nhìn thấy một trang trắng. | Đã có trong sản phẩm |
| WEB-23 | Màn hình phục hồi khi giao diện gặp lỗi | Tất cả người dùng công khai | Nếu một phần giao diện không thể hiển thị, trang web cung cấp thông báo và nút tải lại. | Thông báo phải phân biệt lỗi hiển thị với lỗi kết nối dịch vụ đặt lịch. | Đã có trong sản phẩm |
| WEB-24 | Hỗ trợ nhiều kích thước màn hình | Tất cả người dùng công khai | Trang web điều chỉnh bố cục cho điện thoại, máy tính bảng, máy tính xách tay và màn hình lớn. | Nội dung, nút bấm và biểu mẫu phải đọc được mà không yêu cầu người dùng phóng to thủ công. | Đã có trong sản phẩm |
| WEB-25 | Hỗ trợ bàn phím và giảm chuyển động | Người dùng cần hỗ trợ tiếp cận | Người dùng có thể đi tới nội dung chính, đóng cửa sổ, di chuyển qua biểu mẫu và sử dụng các hành động quan trọng bằng bàn phím. | Trạng thái đang chọn, lỗi biểu mẫu và nội dung thay đổi phải được thông báo rõ. Chuyển động phải giảm khi thiết bị yêu cầu. | Đã có trong sản phẩm |

---

## 2. Đặt lịch lái thử

### 2.1 Bảng đặc tả tính năng

| Mã | Tên tính năng | Người sử dụng | Mô tả theo khái niệm | Quy tắc quan trọng | Mức hoàn thiện |
|---|---|---|---|---|---|
| BOK-01 | Mở đặt lịch từ mẫu xe đang xem | Người đặt lịch | Người dùng có thể bắt đầu đặt lịch từ trang chủ hoặc trang chi tiết. Nếu họ mở từ một mẫu xe cụ thể, mẫu xe đó được chọn sẵn. | Người dùng vẫn phải có quyền đổi sang mẫu xe khác trước khi giữ chỗ. | Đã có trong sản phẩm |
| BOK-02 | Chọn mục đích bắt đầu | Người đặt lịch | Màn hình đầu hỏi người dùng muốn đặt cho chính mình, đặt hộ người khác, tra cứu lịch cũ hay xem hành trình trình diễn. | Hệ thống phải hỏi lựa chọn này trước khi thu thập thông tin cá nhân. | Đã có trong sản phẩm |
| BOK-03 | Đặt lịch cho chính mình | Người đặt lịch đồng thời là người lái | Hệ thống hiểu rằng người đặt và người lái là cùng một người, nhờ đó người dùng không phải nhập cùng một thông tin hai lần. | Quyền quản lý lịch thuộc về người đã xác minh địa chỉ thư điện tử dùng để đặt. | Đã có trong sản phẩm |
| BOK-04 | Đặt hộ người khác | Người đặt hộ | Hệ thống tạo phần thông tin riêng cho người đặt và người trực tiếp lái thử. | Hệ thống không được tự gộp hai người chỉ vì họ dùng chung một địa chỉ liên hệ. | Đã có trong sản phẩm |
| BOK-05 | ViVi đồng hành cùng giao diện lựa chọn | Người đặt lịch | ViVi giải thích bước hiện tại, trả lời câu hỏi và mở đúng khu vực chọn xe, showroom hoặc thời gian khi người dùng cần. | Các dữ liệu cần chính xác vẫn phải được chọn bằng trường và nút rõ ràng. ViVi không được biến quy trình thành một chuỗi câu hỏi dài. | Đã có trong sản phẩm |
| BOK-06 | Chọn và đổi mẫu xe | Người đặt lịch | Người dùng chọn mẫu xe muốn lái thử và có thể đổi xe trong quá trình đặt. | Khi đổi xe, hệ thống phải xóa khung giờ, showroom và chỗ giữ cũ để không hiển thị dữ liệu của xe trước. | Đã có trong sản phẩm |
| BOK-07 | Nhập khu vực hoặc địa chỉ | Người đặt lịch | Người dùng có thể nhập tỉnh, thành phố, quận, huyện, phường, xã hoặc địa chỉ cụ thể để tìm showroom phù hợp. | Khi thông tin quá rộng, hệ thống phải hỏi thêm khu vực nhỏ hơn thay vì đoán một địa điểm. | Đã có trong sản phẩm |
| BOK-08 | Dùng vị trí hiện tại | Người đặt lịch | Người dùng có thể cho phép trình duyệt dùng vị trí hiện tại để tìm showroom gần mình. | Hệ thống chỉ dùng vị trí sau khi người dùng đồng ý. Nếu người dùng từ chối, họ vẫn có thể nhập địa chỉ bằng tay. | Đã có trong sản phẩm |
| BOK-09 | Tìm showroom có đúng xe | Người đặt lịch | Hệ thống tìm những showroom có mẫu xe người dùng muốn thử và có khả năng mở lịch. | Showroom có xe phù hợp phải được ưu tiên trước khoảng cách. Hệ thống không được giới thiệu một showroom không có dữ liệu phục vụ. | Đã có trong sản phẩm |
| BOK-10 | Bản đồ showroom | Người đặt lịch | Người dùng xem các showroom phù hợp trên bản đồ, chọn một địa điểm và xem khoảng cách cùng địa chỉ. | Bản đồ chỉ hỗ trợ lựa chọn. Dữ liệu có xe và khung giờ phải đến từ hệ thống đặt lịch, không đến từ vị trí ghim trên bản đồ. | Đã có nền tảng, cần hoàn thiện |
| BOK-11 | Danh sách showroom thay cho bản đồ | Người đặt lịch | Khi bản đồ không tải được hoặc người dùng không muốn dùng bản đồ, hệ thống vẫn cho phép chọn showroom từ danh sách. | Mọi showroom trong danh sách phải dùng cùng nguồn dữ liệu với lịch lái thử. | Đã có trong sản phẩm |
| BOK-12 | Lịch theo tuần | Người đặt lịch | Người dùng xem khung giờ theo từng ngày trong tuần và có thể chuyển sang tuần trước, tuần hiện tại hoặc tuần sau. | Lịch chỉ cho phép xem trong khoảng thời gian đặt trước mà hệ thống cho phép. | Đã có trong sản phẩm |
| BOK-13 | Phân biệt giờ còn xe và giờ không thể chọn | Người đặt lịch | Mỗi ô thời gian cho biết khung giờ còn xe, đã kín, đã qua hoặc showroom chưa mở lịch. | Khi lịch chưa tải đủ, hệ thống phải nói rõ rằng ô trống chưa chắc là hết lịch. | Đã có trong sản phẩm |
| BOK-14 | Làm mới lịch theo dữ liệu thật | Người đặt lịch | Sau khi chọn showroom, hệ thống tải lại toàn bộ lịch để giảm nguy cơ dùng một danh sách đã cũ. | Dữ liệu tải sau cùng phải là dữ liệu được dùng để quyết định khung giờ còn trống. | Đã có trong sản phẩm |
| BOK-15 | Xác nhận khung giờ trước khi giữ chỗ | Người đặt lịch | Khi người dùng chọn một giờ, hệ thống mở phần tóm tắt xe, showroom và thời gian để người dùng kiểm tra trước khi giữ. | Người dùng có thể quay lại mà chưa làm thay đổi dữ liệu đặt lịch. | Đã có trong sản phẩm |
| BOK-16 | Giữ chỗ tạm thời | Người đặt lịch | Sau khi người dùng xác nhận giờ, hệ thống tạm dành đúng xe và khung giờ cho người đó trong một khoảng thời gian. | Giữ chỗ chưa phải lịch đã xác nhận. Hệ thống phải từ chối nếu xe hoặc giờ vừa được người khác giữ trước. | Đã có trong sản phẩm |
| BOK-17 | Đồng hồ giữ chỗ | Người đặt lịch | Màn hình hiển thị thời gian còn lại để người dùng hoàn tất thông tin và xác minh. | Khi hết thời gian, hệ thống phải trả lại chỗ và mời người dùng chọn lại mà không nói nhầm rằng một lịch đã xác nhận bị hủy. | Đã có trong sản phẩm |
| BOK-18 | Trả chỗ khi đổi lựa chọn hoặc rời quy trình | Người đặt lịch | Hệ thống trả chỗ cũ khi người dùng đổi xe, đổi showroom, đổi khung giờ hoặc làm mới hành trình. | Hệ thống phải có khả năng nhận cùng một yêu cầu trả chỗ nhiều lần mà không gây lỗi. | Đã có trong sản phẩm |
| BOK-19 | Thu thập thông tin người đặt | Người đặt lịch | Biểu mẫu yêu cầu tên và thư điện tử của người đặt; số điện thoại được thu thập khi cần phục vụ liên hệ. | Biểu mẫu phải kiểm tra định dạng và giải thích lỗi ngay tại trường liên quan. | Đã có trong sản phẩm |
| BOK-20 | Thu thập thông tin người lái riêng | Người đặt hộ | Khi đặt hộ, biểu mẫu yêu cầu tên người lái và cho phép nhập địa chỉ liên hệ riêng của người đó. | Thư và hướng dẫn dành cho người lái phải đi đúng địa chỉ mà người đặt đã cung cấp. | Đã có trong sản phẩm |
| BOK-21 | Chọn dùng chung liên hệ | Người đặt hộ | Người đặt có thể xác nhận rằng người lái dùng chung thư điện tử và số điện thoại với mình. | Hệ thống chỉ dùng chung thông tin khi người đặt chủ động chọn. | Đã có trong sản phẩm |
| BOK-22 | Xác nhận người lái có giấy phép phù hợp | Người đặt lịch | Trước khi tiếp tục, người dùng xác nhận rằng người lái có giấy phép lái xe phù hợp. | Đây là lời xác nhận ban đầu. Showroom vẫn phải kiểm tra giấy phép bản gốc khi khách tới và hệ thống không lưu ảnh giấy phép. | Đã có trong sản phẩm |
| BOK-23 | Lựa chọn nhận thông tin tiếp thị | Người đặt lịch | Người dùng có thể chọn có nhận thông tin ưu đãi, khuyến mãi và sự kiện hay không. | Việc từ chối thông tin tiếp thị không được làm người dùng mất quyền đặt lịch. | Đã có trong sản phẩm |
| BOK-24 | Phiếu kiểm tra trước khi đặt | Người đặt lịch | Trước bước xác nhận cuối, hệ thống trình bày lại người đặt, người lái, xe, showroom và thời gian trong một phiếu rõ ràng. | Người dùng phải có đường quay lại chỉnh thông tin hoặc đổi lựa chọn trước khi xác nhận. | Đã có trong sản phẩm |
| BOK-25 | Gửi mã xác minh qua thư điện tử | Người đặt lịch | Hệ thống gửi một mã có thời hạn tới thư điện tử của người đặt để chứng minh người đó kiểm soát địa chỉ đã cung cấp. | Mã không được hiển thị trên giao diện khi dùng với khách hàng thật. Mã sai, hết hạn hoặc đã dùng phải bị từ chối. | Đã có nền tảng, cần hoàn thiện |
| BOK-26 | Nhập mã xác minh sáu chữ số | Người đặt lịch | Người dùng nhập mã vào sáu ô, có thể dán toàn bộ mã và nhận thông báo nếu mã chưa đúng. | Nút xác nhận chỉ hoạt động khi người dùng đã nhập đủ mã. | Đã có trong sản phẩm |
| BOK-27 | Xác nhận lịch và sinh mã lịch | Người đặt lịch | Sau khi mã xác minh hợp lệ, hệ thống kiểm tra lại chỗ giữ rồi tạo một mã lịch chính thức. | Mã lịch chỉ được tạo một lần. Một yêu cầu gửi lại do mạng chậm không được tạo thêm lịch trùng. | Đã có trong sản phẩm |
| BOK-28 | Phân công nhân viên phụ trách | Người đặt lịch và showroom | Khi có nhân viên phù hợp, hệ thống gắn người phụ trách vào lịch và hiển thị thông tin này trên phiếu xác nhận. | Nhân viên phải thuộc đúng showroom, có ca làm phù hợp và chưa bị xếp trùng công việc. | Đã có trong sản phẩm |
| BOK-29 | Màn hình xác nhận thành công | Người đặt lịch | Màn hình thành công hiển thị mã lịch, xe, showroom, ngày giờ, người tham gia và trạng thái đã xác nhận. | Trang web, thư điện tử và cổng showroom phải hiển thị cùng một trạng thái. | Đã có trong sản phẩm |
| BOK-30 | Phần trình bày xe sau xác nhận | Người đặt lịch | Sau khi xác nhận thành công, giao diện có thể dùng hình ảnh hoặc mô hình xe để tạo một khoảnh khắc hoàn tất dễ nhận biết. | Phần trình bày không được làm chậm hoặc cản người dùng xem mã lịch và hướng dẫn tiếp theo. | Đã có trong sản phẩm |
| BOK-31 | Ba việc cần chuẩn bị | Người đặt lịch và người lái | Hệ thống nhắc người lái mang giấy phép bản gốc, cung cấp thông tin đã đăng ký tại quầy và có mặt sớm trước giờ hẹn. | Hướng dẫn phải dùng dữ liệu thật của lịch và không tự đặt ra một thủ tục chưa được duyệt. | Đã có trong sản phẩm |
| BOK-32 | Thêm lịch vào ứng dụng lịch | Người đặt lịch | Người dùng có thể mở sự kiện trên Google Calendar hoặc tải một tệp lịch cho thiết bị. | Đây là thao tác thêm một chiều. Sản phẩm không được gọi tính năng này là đồng bộ lịch hai chiều. | Đã có trong sản phẩm |
| BOK-33 | Đặt thêm một mẫu xe khác | Người đặt lịch | Sau khi đã có lịch, người dùng có thể giữ lịch hiện tại và bắt đầu đặt thêm một mẫu xe khác. | Lịch cũ không được thay đổi khi người dùng bắt đầu hành trình mới. | Đã có trong sản phẩm |
| BOK-34 | Tiếp tục phiên chưa hoàn tất | Người đặt lịch | Nếu người dùng quay lại trong cùng trình duyệt, hệ thống hỏi họ muốn tiếp tục bước đang dở hay bắt đầu lại. | Hệ thống không được lưu mã xác minh hoặc thông tin nhạy cảm trong phần khôi phục giao diện. | Đã có trong sản phẩm |
| BOK-35 | Tách ViVi và khu vực thao tác trên điện thoại | Người đặt lịch | Trên điện thoại, người dùng có thể chuyển giữa cuộc trò chuyện và khu vực chọn xe, bản đồ, lịch hoặc phiếu đặt. | Việc chuyển khu vực chỉ thay đổi phần đang nhìn thấy và không được làm mất bước hiện tại. | Đã có trong sản phẩm |
| BOK-36 | Chế độ trình diễn hành trình chuẩn | Người xem sản phẩm | Hệ thống có thể tự chạy một hành trình mẫu từ chọn xe đến phiếu hoàn tất để nhóm giới thiệu sản phẩm. | Chế độ này phải được gắn nhãn rõ, dùng hồ sơ mẫu và không được tạo lịch thật. | Chỉ dùng để trình diễn |
| BOK-37 | Điều khiển phần trình diễn | Người thuyết trình | Người thuyết trình có thể chạy tiếp, tạm dừng, quay lại, thu gọn bảng điều khiển hoặc thoát phần trình diễn. | Thoát phần trình diễn phải trả giao diện về trạng thái an toàn và trả mọi chỗ mô phỏng đang giữ. | Chỉ dùng để trình diễn |

---

## 3. Tra cứu, cập nhật, đổi và hủy lịch

### 3.1 Bảng đặc tả tính năng

| Mã | Tên tính năng | Người sử dụng | Mô tả theo khái niệm | Quy tắc quan trọng | Mức hoàn thiện |
|---|---|---|---|---|---|
| MGT-01 | Lối vào quản lý lịch | Người đặt lịch | Người dùng có thể mở phần tra cứu từ trang chủ, chân trang, trang đặt lịch hoặc đường dẫn dành riêng cho tra cứu. | Lối vào phải dễ tìm và không yêu cầu người dùng bắt đầu một lịch mới. | Đã có trong sản phẩm |
| MGT-02 | Xác minh người quản lý lịch | Người đặt lịch | Người dùng nhập thư điện tử đã dùng khi đặt và nhận mã xác minh trước khi xem hoặc thay đổi lịch. | Hệ thống không được tiết lộ một thư điện tử có lịch hay không trước khi hoàn tất bước bảo vệ cần thiết. | Đã có nền tảng, cần hoàn thiện |
| MGT-03 | Gửi lại mã có thời gian chờ | Người đặt lịch | Khi chưa nhận được mã, người dùng có thể yêu cầu gửi lại sau một khoảng chờ. | Hệ thống phải giới hạn số lần gửi để tránh làm phiền người nhận và tránh bị lợi dụng. | Đã có nền tảng, cần hoàn thiện |
| MGT-04 | Danh sách lịch thuộc cùng người đặt | Người đặt lịch | Sau khi xác minh, người dùng xem các lịch hợp lệ gắn với địa chỉ liên hệ của mình. | Danh sách chỉ được chứa lịch thuộc đúng người đã xác minh. | Đã có trong sản phẩm |
| MGT-05 | Xem chi tiết lịch | Người đặt lịch | Người dùng xem mã lịch, xe, showroom, thời gian, người đặt, người lái và trạng thái hiện tại. | Dữ liệu hiển thị phải được đọc lại từ nguồn chính thay vì dùng bản sao cũ trên trình duyệt. | Đã có trong sản phẩm |
| MGT-06 | Cập nhật thông tin người đặt và người lái | Người đặt lịch | Người dùng có thể sửa những thông tin liên hệ được phép thay đổi sau khi đã xác minh. | Hệ thống phải tiếp tục tách người đặt và người lái. Việc sửa không được mở rộng quyền của người lái. | Đã có trong sản phẩm |
| MGT-07 | Hiển thị đúng hành động được phép | Người đặt lịch | Mỗi lịch chỉ hiển thị các hành động phù hợp với trạng thái và mục đích xác minh, chẳng hạn xem, sửa, đổi hoặc hủy. | Một quyền dùng để xem hoặc đổi lịch không được tự động cho phép hủy nếu hệ thống chưa cấp quyền đó. | Đã có trong sản phẩm |
| MGT-08 | Xác nhận trước khi hủy | Người đặt lịch | Trước khi hủy, hệ thống hiển thị lại mã lịch, xe, showroom, thời gian và người tham gia để người dùng kiểm tra. | Người dùng phải có lựa chọn giữ lại lịch. Hệ thống chỉ hủy lịch đang ở trạng thái cho phép. | Đã có trong sản phẩm |
| MGT-09 | Hủy lịch và dừng lời nhắc | Người đặt lịch | Sau khi người dùng xác nhận hủy, hệ thống đóng lịch, trả xe và khung giờ, đồng thời dừng các lời nhắc chưa gửi. | Hệ thống không được tiếp tục chăm sóc hoặc gửi thư nhắc cho một lịch đã hủy. | Đã có trong sản phẩm |
| MGT-10 | Tìm lựa chọn đổi lịch | Người đặt lịch | Người dùng có thể tìm showroom và khung giờ khác cho đúng mẫu xe của lịch hiện tại. | Hệ thống phải kiểm tra lại xe, showroom, khung giờ và nhân sự giống như khi đặt mới. | Đã có trong sản phẩm |
| MGT-11 | Hiểu yêu cầu đổi ngày giờ viết bằng câu thông thường | Người đặt lịch | Khi người dùng nói muốn đổi sang một ngày hoặc giờ cụ thể, ViVi có thể nhận ra thời gian mong muốn và mở phần lựa chọn phù hợp. | Nếu câu nói chưa đủ rõ, hệ thống phải yêu cầu người dùng chọn lại trên lịch thay vì tự đoán. | Đã có nền tảng, cần hoàn thiện |
| MGT-12 | Giữ chỗ mới trước khi đổi | Người đặt lịch | Hệ thống giữ khung giờ mới trong một khoảng thời gian để người dùng kiểm tra trước khi đổi lịch cũ. | Lịch cũ vẫn phải còn hiệu lực trong lúc người dùng chưa xác nhận khung giờ mới. | Đã có trong sản phẩm |
| MGT-13 | Xác nhận đổi lịch | Người đặt lịch | Khi người dùng xác nhận, hệ thống tạo lịch thay thế và đóng lịch cũ bằng trạng thái đã đổi. | Nếu bước xác nhận lịch mới thất bại, hệ thống phải giữ nguyên lịch cũ. | Đã có trong sản phẩm |
| MGT-14 | Dẫn người dùng tới mã lịch mới | Người đặt lịch | Sau khi đổi thành công, hệ thống hiển thị thông tin và mã của lịch mới. | Đường dẫn, lời nhắc và phần chăm sóc của lịch cũ phải hết hiệu lực. | Đã có trong sản phẩm |
| MGT-15 | Giữ dữ liệu khi thao tác gặp lỗi | Người đặt lịch | Khi mất kết nối, hết chỗ hoặc mã hết hạn, giao diện giữ lại những thông tin an toàn để người dùng không phải nhập lại từ đầu. | Hệ thống không được giữ mã xác minh, quyền truy cập hoặc dữ liệu bí mật trong phần lưu tạm của trình duyệt. | Đã có trong sản phẩm |

---

## 4. Chăm sóc sau xác nhận và đường dẫn dành cho người lái

### 4.1 Bảng đặc tả tính năng

| Mã | Tên tính năng | Người sử dụng | Mô tả theo khái niệm | Quy tắc quan trọng | Mức hoàn thiện |
|---|---|---|---|---|---|
| CAR-01 | Lời chào sau xác nhận | Người đặt lịch | Sau khi lịch được xác nhận, ViVi nói rõ rằng showroom đã nhận lịch và tiếp tục đồng hành trong giai đoạn chuẩn bị. | ViVi chỉ được nói lịch đã xác nhận khi dữ liệu thật đang ở trạng thái đã xác nhận. | Đã có trong sản phẩm |
| CAR-02 | Gợi ý câu hỏi tiếp theo | Người đặt và người lái | Sau một câu trả lời phù hợp, ViVi có thể gợi ý tối đa hai câu hỏi tiếp theo liên quan tới việc chuẩn bị hoặc trải nghiệm xe. | Gợi ý chỉ xuất hiện sau phần chăm sóc, không xuất hiện trong lúc một thao tác đặt lịch đang chờ hoàn tất. | Đã có trong sản phẩm |
| CAR-03 | Hướng dẫn chuẩn bị buổi lái thử | Người đặt và người lái | ViVi giúp người dùng xác định giấy tờ, thời gian nên tới, nội dung cần trao đổi và các điểm nên chú ý khi lái. | Hướng dẫn chung phải đến từ nội dung đã được kiểm tra. | Đã có nền tảng, cần hoàn thiện |
| CAR-04 | Trả lời theo mẫu xe và thị trường | Người đặt và người lái | ViVi tìm nội dung phù hợp với mẫu xe, phiên bản, năm sản xuất và thị trường khi các dữ liệu đó có sẵn. | ViVi không được dùng thông tin của mẫu xe hoặc thị trường khác để trả lời như một sự thật của lịch hiện tại. | Đã có nền tảng, cần hoàn thiện |
| CAR-05 | Dùng nội dung có nguồn và ngày xem lại | Người đặt và người lái | Mỗi nội dung quan trọng có nguồn, phạm vi áp dụng, trạng thái duyệt và ngày cần xem lại. | Nội dung bị từ chối, hết hiệu lực hoặc đã được thay thế không được dùng để trả lời khách hàng. | Đã có nền tảng, cần hoàn thiện |
| CAR-06 | Nhận biết câu hỏi cần dữ liệu đang thay đổi | Người đặt và người lái | ViVi nhận biết những câu hỏi như giá hiện hành hoặc khuyến mãi cần kiểm tra nguồn đang còn hiệu lực. | Khi không có nguồn phù hợp, ViVi phải nói rõ chưa thể xác nhận và đưa đầu mối showroom. | Đã có nền tảng, cần hoàn thiện |
| CAR-07 | Ghi nhận nhu cầu chuẩn bị | Người đặt và người lái | ViVi có thể ghi nhận nhu cầu sử dụng xe, người đi cùng, điều người lái muốn trải nghiệm và nội dung cần trao đổi tại showroom. | ViVi chỉ hỏi thông tin thật sự giúp chuẩn bị buổi lái thử và không được hỏi dồn nhiều câu trong một lượt. | Đã có trong sản phẩm |
| CAR-08 | Ghi rõ ai cung cấp thông tin | Người đặt, người lái và nhân viên showroom | Mỗi thông tin chuẩn bị được gắn với người đặt, người lái hoặc nguồn hướng dẫn chính thức. | Lời kể của người đặt về người lái không được ghi thành lời xác nhận trực tiếp của người lái. | Đã có trong sản phẩm |
| CAR-09 | Hồ sơ được nối tiếp sau khi xác minh | Người dùng quay lại | Sau khi người dùng xác minh địa chỉ liên hệ hoặc xác nhận lịch, hệ thống có thể nối cuộc trò chuyện hiện tại với hồ sơ đúng người. | Hệ thống không được nối hai hồ sơ chỉ dựa trên suy đoán. Danh tính đã xác minh phải được ưu tiên. | Đã có trong sản phẩm |
| CAR-10 | Thư mời riêng cho người lái | Người đặt hộ và người lái | Khi người lái khác người đặt và có thư điện tử riêng, hệ thống có thể gửi một lời mời để người lái xem phần chuẩn bị của mình. | Hệ thống không cần gửi lời mời nếu người đặt cũng là người lái. | Đã có nền tảng, cần hoàn thiện |
| CAR-11 | Đường dẫn riêng có thời hạn | Người lái được mời | Người lái mở một đường dẫn riêng để xem thông tin tối thiểu của buổi hẹn và bắt đầu trò chuyện với ViVi. | Đường dẫn phải hết hạn và phải ngừng hoạt động khi lịch bị hủy hoặc được thay bằng lịch khác. | Đã có nền tảng, cần hoàn thiện |
| CAR-12 | Lời chào dành riêng cho người lái | Người lái được mời | ViVi gọi đúng tên người lái, mẫu xe và showroom trong lời chào để người lái hiểu mình đang chuẩn bị cho lịch nào. | Lời chào chỉ được dùng dữ liệu tối thiểu của chính lịch được mời. | Đã có trong sản phẩm |
| CAR-13 | Người lái trò chuyện trong phạm vi chuẩn bị | Người lái được mời | Người lái có thể hỏi về cách chuẩn bị, điểm cần trải nghiệm và điều cần trao đổi với nhân viên. | Người lái không được đổi, hủy hoặc xem toàn bộ thông tin quản lý của người đặt qua đường dẫn này. | Đã có trong sản phẩm |
| CAR-14 | Bản tóm tắt dành cho nhân viên | Nhân viên và quản lý showroom | Cổng vận hành có thể tạo bản tóm tắt về người đặt, người lái, nhu cầu và lịch sử được phép xem để nhân viên chuẩn bị tốt hơn. | Bản tóm tắt phải phân biệt dữ liệu chắc chắn, dữ liệu do từng người cung cấp và phần còn thiếu. | Đã có nền tảng, cần hoàn thiện |
| CAR-15 | Phương án thay thế khi ViVi không hoạt động | Người đặt và người lái | Khi ViVi tạm ngưng, người dùng vẫn xem được phiếu lịch, danh sách chuẩn bị cố định và đầu mối showroom. | Lỗi của phần trò chuyện không được làm mất quyền xem, đổi hoặc hủy lịch. | Đã có trong sản phẩm |

---

## 5. Thư điện tử và lời nhắc

### 5.1 Bảng đặc tả tính năng

| Mã | Tên tính năng | Người nhận | Mô tả theo khái niệm | Quy tắc quan trọng | Mức hoàn thiện |
|---|---|---|---|---|---|
| MSG-01 | Thư chứa mã xác minh | Người đặt lịch | Hệ thống gửi mã có thời hạn để xác minh địa chỉ thư điện tử trước khi xác nhận hoặc quản lý lịch. | Thư phải nói rõ thời hạn và không được gửi mã tới một kênh ngoài phạm vi chính thức. | Đã có nền tảng, cần hoàn thiện |
| MSG-02 | Thư xác nhận đặt lịch | Người đặt lịch | Sau khi lịch được xác nhận, hệ thống gửi mã lịch, xe, showroom, thời gian, người tham gia và hướng dẫn tiếp theo. | Nội dung thư phải khớp với trạng thái mới nhất của lịch. | Đã có nền tảng, cần hoàn thiện |
| MSG-03 | Thư dành riêng cho người lái | Người lái được mời | Người lái nhận thư riêng có thông tin cần thiết và đường dẫn chuẩn bị có thời hạn. | Thư của người lái không được chứa quyền quản lý lịch của người đặt. | Đã có nền tảng, cần hoàn thiện |
| MSG-04 | Lời nhắc trước 24 giờ | Người tham gia phù hợp | Hệ thống lên lịch gửi lời nhắc trước buổi hẹn khoảng 24 giờ. | Trước khi gửi, hệ thống phải kiểm tra lịch vẫn còn hiệu lực. | Đã có nền tảng, cần hoàn thiện |
| MSG-05 | Lời nhắc trước 2 giờ | Người tham gia phù hợp | Hệ thống lên lịch gửi lời nhắc gần giờ hẹn để giảm nguy cơ người dùng quên lịch. | Lời nhắc phải dừng nếu lịch đã hủy, đã đổi hoặc không còn ở trạng thái cho phép. | Đã có nền tảng, cần hoàn thiện |
| MSG-06 | Thư cập nhật thông tin | Người đặt và người lái liên quan | Khi thông tin được phép thay đổi, hệ thống có thể gửi thư báo nội dung mới. | Mỗi người chỉ nhận phần thông tin cần thiết cho vai trò của mình. | Đã có nền tảng, cần hoàn thiện |
| MSG-07 | Thư đổi lịch | Người đặt và người lái liên quan | Sau khi đổi lịch thành công, hệ thống gửi thông tin của lịch mới và làm rõ lịch cũ không còn hiệu lực. | Thư chỉ được gửi sau khi lịch mới đã được xác nhận. | Đã có nền tảng, cần hoàn thiện |
| MSG-08 | Thư hủy lịch | Người đặt và người lái liên quan | Khi lịch bị hủy, hệ thống gửi xác nhận hủy để các bên không tiếp tục chuẩn bị nhầm. | Thư phải dùng trạng thái mới nhất và không kèm lời nhắc tham gia. | Đã có nền tảng, cần hoàn thiện |
| MSG-09 | Hàng chờ gửi thư | Nhóm vận hành | Các thư xác nhận và lời nhắc được lưu thành công việc chờ gửi để việc đặt lịch không phải chờ quá lâu. | Nếu dịch vụ gửi thư tạm lỗi, hệ thống phải ghi nhận, thử lại có giới hạn và không làm mất lịch. | Đã có trong sản phẩm |
| MSG-10 | Theo dõi kết quả gửi | Nhóm vận hành | Hệ thống lưu trạng thái đang chờ, đã gửi hoặc gửi thất bại để người vận hành biết thư nào cần xử lý. | Hệ thống không được ghi nguyên mã xác minh hoặc dữ liệu riêng tư vào nhật ký lỗi. | Đã có trong sản phẩm |

---

## 6. Cổng vận hành showroom

### 6.1 Bảng đặc tả tính năng

| Mã | Tên tính năng | Người sử dụng | Mô tả theo khái niệm | Quy tắc quan trọng | Mức hoàn thiện |
|---|---|---|---|---|---|
| OPS-01 | Đăng nhập cổng nội bộ | Nhân viên, quản lý và người quản trị vận hành | Người dùng nội bộ đăng nhập bằng tài khoản được cấp riêng. | Dự án không có tài khoản hoặc mật khẩu mặc định. Phiên làm việc phải hết hạn và có thể bị thu hồi. | Chỉ dùng trong nội bộ |
| OPS-02 | Phân quyền theo vai trò | Người dùng nội bộ | Nhân viên, quản lý showroom và người quản trị vận hành nhìn thấy các khu vực khác nhau theo trách nhiệm. | Việc ẩn nút trên giao diện không thay thế kiểm tra quyền. Mọi yêu cầu phải được kiểm tra lại trước khi thực hiện. | Chỉ dùng trong nội bộ |
| OPS-03 | Giới hạn dữ liệu theo showroom | Nhân viên và quản lý showroom | Mỗi người chỉ xem dữ liệu thuộc showroom hoặc phần việc được giao. | Nhân viên không được tự mở rộng phạm vi. Quản lý chỉ được quản lý một showroom đã cấp. | Chỉ dùng trong nội bộ |
| OPS-04 | Bảng tổng quan theo vai trò | Người dùng nội bộ | Trang tổng quan hiển thị các con số phù hợp với từng vai trò, như lịch hôm nay, lịch sắp tới, xe sẵn sàng, nhân viên trực và số buổi hoàn tất. | Mỗi con số phải được tính trong đúng phạm vi của người đang đăng nhập. | Chỉ dùng trong nội bộ |
| OPS-05 | Biểu đồ lịch lái thử trong 14 ngày | Quản lý và người quản trị vận hành | Cổng vận hành trình bày số lịch đang xử lý, đã hoàn tất, vắng mặt và đã hủy theo từng ngày. | Biểu đồ không được gộp dữ liệu ngoài phạm vi được cấp. | Chỉ dùng trong nội bộ |
| OPS-06 | Theo dõi công suất bảy ngày tới | Quản lý và người quản trị vận hành | Cổng vận hành so sánh số khung giờ đã đặt, số khung giờ bị khóa và tổng khả năng phục vụ. | Khung giờ bị khóa không được tính là khả năng còn có thể nhận khách. | Chỉ dùng trong nội bộ |
| OPS-07 | Phân bố trạng thái lịch | Quản lý và người quản trị vận hành | Cổng vận hành cho biết số lịch ở từng trạng thái để người quản lý nhận ra chỗ ùn tắc. | Trạng thái phải dùng cùng cách gọi với hệ thống đặt lịch. | Chỉ dùng trong nội bộ |
| OPS-08 | Danh sách lịch mới và thay đổi gần đây | Người dùng nội bộ | Trang tổng quan hiển thị các lịch gần nhất trong phạm vi của người dùng. Người quản trị toàn hệ thống còn xem được thay đổi vận hành gần đây. | Dữ liệu phải được làm mới định kỳ và khi người dùng quay lại cửa sổ. | Chỉ dùng trong nội bộ |
| OPS-09 | Trung tâm thông báo nội bộ | Người dùng nội bộ | Cổng vận hành kiểm tra thông báo mới, hiển thị số chưa đọc và cho phép đánh dấu từng thông báo hoặc tất cả thông báo là đã đọc. | Mở một thông báo về lịch phải đưa người dùng tới khu vực quản lý lịch. | Chỉ dùng trong nội bộ |
| OPS-10 | Danh sách lịch theo phạm vi | Nhân viên, quản lý và người quản trị vận hành | Nhân viên xem lịch được giao; quản lý xem lịch của showroom; người quản trị xem lịch toàn hệ thống. | Nhân viên chỉ có quyền xem đối với phần lớn dữ liệu và không được tự thay đổi lịch. | Chỉ dùng trong nội bộ |
| OPS-11 | Lọc danh sách lịch | Quản lý và người quản trị vận hành | Người dùng có thể lọc theo trạng thái, ngày, showroom, nhân viên phụ trách và xe thử. | Bộ lọc chỉ thu hẹp dữ liệu mà người dùng đã có quyền xem. | Chỉ dùng trong nội bộ |
| OPS-12 | Xem chi tiết lịch | Người dùng nội bộ có quyền | Cổng vận hành hiển thị xe, showroom, thời gian, người phụ trách, ghi chú và trạng thái của một lịch. | Thông tin cá nhân phải được giới hạn theo vai trò và mục đích công việc. | Chỉ dùng trong nội bộ |
| OPS-13 | Phân biệt người đặt và người lái | Người dùng nội bộ có quyền | Phần chi tiết trình bày người đặt và người lái thành hai thẻ riêng khi họ không phải cùng một người. | Không được dùng liên hệ của người đặt như thể đó là liên hệ của người lái. | Chỉ dùng trong nội bộ |
| OPS-14 | Hồ sơ và lịch sử khách hàng | Quản lý và người quản trị vận hành | Cổng vận hành cho biết số lần đặt, số lần hoàn tất, số lần hủy hoặc vắng mặt và các mẫu xe từng quan tâm trong phạm vi được phép. | Lịch sử chỉ được hiển thị khi người dùng nội bộ có quyền xem các lịch liên quan. | Chỉ dùng trong nội bộ |
| OPS-15 | Bản chuẩn bị dành cho nhân viên | Quản lý và người quản trị vận hành | Cổng vận hành có thể tạo bản tóm tắt dễ đọc để nhân viên biết ai tham gia và điều gì cần chuẩn bị. | Bản tóm tắt chỉ được tạo từ dữ liệu có nguồn và phải được làm mới khi thông tin của lịch thay đổi. | Đã có nền tảng, cần hoàn thiện |
| OPS-16 | Phân công nhân viên phụ trách | Quản lý showroom và người quản trị vận hành | Người quản lý chọn một nhân viên phù hợp để chịu trách nhiệm cho lịch. | Nhân viên phải thuộc đúng showroom, đang hoạt động và không bị xếp trùng. | Chỉ dùng trong nội bộ |
| OPS-17 | Kiểm tra giấy phép bản gốc | Quản lý showroom và người quản trị vận hành | Khi khách tới, người có quyền ghi nhận giấy phép bản gốc hợp lệ hoặc từ chối kèm lý do. | Hệ thống chỉ lưu kết quả kiểm tra, không lưu ảnh hoặc số giấy phép. Lịch phải có người phụ trách trước khi kiểm tra. | Chỉ dùng trong nội bộ |
| OPS-18 | Ghi nhận khách có mặt | Quản lý showroom và người quản trị vận hành | Sau khi giấy phép hợp lệ, người có quyền chuyển lịch từ đã xác nhận sang đã có mặt. | Hệ thống không được ghi nhận có mặt nếu chưa hoàn tất bước kiểm tra giấy phép bắt buộc. | Chỉ dùng trong nội bộ |
| OPS-19 | Hoàn tất buổi lái thử | Quản lý showroom và người quản trị vận hành | Sau khi buổi lái thử kết thúc, người có quyền đóng lịch bằng trạng thái đã hoàn tất. | Chỉ lịch đã ghi nhận có mặt mới được chuyển sang đã hoàn tất. | Chỉ dùng trong nội bộ |
| OPS-20 | Ghi nhận khách vắng mặt | Quản lý showroom và người quản trị vận hành | Khi khách không tới sau khoảng chờ quy định, người có quyền đánh dấu lịch là vắng mặt. | Thao tác phải có bước xác nhận và chỉ áp dụng cho lịch đang ở trạng thái phù hợp. | Chỉ dùng trong nội bộ |
| OPS-21 | Hủy lịch từ cổng vận hành | Quản lý showroom và người quản trị vận hành | Người có quyền có thể hủy lịch trong trường hợp vận hành cần thiết. | Thao tác phải được xác nhận, ghi lý do và tạo lịch sử thay đổi. | Chỉ dùng trong nội bộ |
| OPS-22 | Danh sách nhân viên showroom | Nhân viên, quản lý và người quản trị vận hành | Cổng vận hành hiển thị nhân viên thuộc showroom, mã nhân viên, vai trò và trạng thái hoạt động. | Nhân viên chỉ xem trong phạm vi của mình; quản lý chỉ xem showroom được giao. | Chỉ dùng trong nội bộ |
| OPS-23 | Tạo và chỉnh ca làm | Quản lý showroom và người quản trị vận hành | Người quản lý tạo ca, sửa thời gian hoặc hủy ca của nhân viên. | Ca làm không được nằm ngoài showroom của nhân viên và không được xung đột với khoảng không khả dụng. | Chỉ dùng trong nội bộ |
| OPS-24 | Ghi nhận thời gian nhân viên không khả dụng | Quản lý showroom và người quản trị vận hành | Người quản lý ghi thời gian nghỉ, đào tạo hoặc lý do khác khiến nhân viên không thể nhận lịch. | Hệ thống phải xử lý các ca làm bị trùng và không tiếp tục phân công nhân viên trong khoảng này. | Chỉ dùng trong nội bộ |
| OPS-25 | Nhân viên xem lịch làm việc của mình | Nhân viên showroom | Nhân viên xem ca làm và thời gian không khả dụng của chính mình. | Nhân viên không được sửa lịch làm việc hoặc xem lịch của người khác. | Chỉ dùng trong nội bộ |
| OPS-26 | Danh sách xe lái thử | Quản lý showroom và người quản trị vận hành | Cổng vận hành hiển thị mã xe, mẫu xe, phiên bản, showroom, biển số, mức pin và trạng thái vận hành. | Xe chỉ xuất hiện trong đúng showroom hiện tại của nó. | Chỉ dùng trong nội bộ |
| OPS-27 | Lọc đội xe | Quản lý showroom và người quản trị vận hành | Người dùng có thể lọc xe theo showroom, mẫu, phiên bản và trạng thái. | Người quản lý showroom không được lọc hoặc xem xe ngoài showroom của mình. | Chỉ dùng trong nội bộ |
| OPS-28 | Cập nhật trạng thái xe | Quản lý showroom và người quản trị vận hành | Người có quyền chuyển xe giữa sẵn sàng, đang sử dụng, đang sạc, bảo trì hoặc ngừng phục vụ. | Các trạng thái bảo trì và ngừng phục vụ phải có bước xác nhận vì chúng ảnh hưởng tới lịch còn trống. | Chỉ dùng trong nội bộ |
| OPS-29 | Theo dõi mức pin tối thiểu | Quản lý showroom và người quản trị vận hành | Cổng vận hành hiển thị mức pin hiện tại và mức tối thiểu cần có để nhận lịch. | Xe không đạt mức pin hoặc không ở trạng thái sẵn sàng không được mở cho lịch mới. | Chỉ dùng trong nội bộ |
| OPS-30 | Quản lý giờ hoạt động showroom | Quản lý showroom và người quản trị vận hành | Người quản lý đặt giờ mở, giờ đóng hoặc ngày đóng cửa cho từng ngày trong tuần. | Khung giờ lái thử phải nằm trong giờ hoạt động còn hiệu lực. | Chỉ dùng trong nội bộ |
| OPS-31 | Khóa xe theo khoảng thời gian | Quản lý showroom và người quản trị vận hành | Người quản lý tạm khóa một xe trong khoảng thời gian vì bảo trì, sự kiện hoặc lý do vận hành. | Hệ thống phải chặn các khung giờ trống liên quan và phải kiểm tra xung đột với lịch đã có. | Chỉ dùng trong nội bộ |
| OPS-32 | Gỡ khoảng khóa xe | Quản lý showroom và người quản trị vận hành | Khi xe có thể phục vụ trở lại, người quản lý gỡ khoảng khóa để mở lại các khung giờ còn hợp lệ. | Việc gỡ khóa không được tự mở một khung giờ đã bị lịch khác chiếm. | Chỉ dùng trong nội bộ |
| OPS-33 | Tạo và cập nhật showroom | Người quản trị vận hành | Người quản trị thêm showroom mới hoặc sửa tên, địa chỉ, vị trí và đầu mối liên hệ. | Mã showroom không được thay đổi tùy ý sau khi đã được sử dụng. | Chỉ dùng trong nội bộ |
| OPS-34 | Kích hoạt hoặc ngừng showroom | Người quản trị vận hành | Người quản trị có thể cho một showroom ngừng nhận hoạt động mới hoặc kích hoạt lại. | Hệ thống không xóa hẳn showroom đang được lịch, xe hoặc nhân viên tham chiếu. | Chỉ dùng trong nội bộ |
| OPS-35 | Quản lý mẫu xe | Người quản trị vận hành | Người quản trị tạo mẫu xe, khai báo loại xe, số chỗ và yêu cầu giấy phép, sau đó có thể bật hoặc ngừng mẫu xe. | Mẫu xe đã được tham chiếu không được xóa hẳn khỏi lịch sử. | Chỉ dùng trong nội bộ |
| OPS-36 | Quản lý phiên bản xe | Người quản trị vận hành | Người quản trị tạo phiên bản với dung lượng pin, tầm hoạt động và thời lượng lái thử mặc định. | Phiên bản phải thuộc một mẫu xe hợp lệ và có thể được ngừng mà không làm mất dữ liệu cũ. | Chỉ dùng trong nội bộ |
| OPS-37 | Điều chuyển xe giữa showroom | Người quản trị vận hành | Người quản trị chọn xe, showroom đích và thời điểm hiệu lực để chuyển xe. | Hệ thống phải từ chối nếu xe đang được giữ hoặc có lịch sắp tới bị ảnh hưởng. | Chỉ dùng trong nội bộ |
| OPS-38 | Xem lịch sử điều chuyển | Người quản trị vận hành | Cổng vận hành lưu và hiển thị nơi đi, nơi đến, thời điểm và trạng thái của mỗi lần điều chuyển. | Lịch sử phải được giữ lại để giải thích xe đã thuộc showroom nào tại từng thời điểm. | Chỉ dùng trong nội bộ |
| OPS-39 | Tạo tài khoản nội bộ | Người quản trị vận hành | Người quản trị tạo tài khoản nhân viên, quản lý showroom hoặc người quản trị khác. | Nhân viên phải nối với một hồ sơ nhân viên đang hoạt động. Quản lý phải được cấp đúng một showroom. | Chỉ dùng trong nội bộ |
| OPS-40 | Lọc và xem tài khoản | Người quản trị vận hành | Người quản trị lọc tài khoản theo vai trò, showroom và trạng thái hoạt động. | Mật khẩu không bao giờ được hiển thị lại trong danh sách. | Chỉ dùng trong nội bộ |
| OPS-41 | Thay đổi vai trò và phạm vi | Người quản trị vận hành | Người quản trị có thể đổi tên hiển thị, vai trò, showroom hoặc hồ sơ nhân viên liên kết. | Khi quyền thay đổi, các phiên đăng nhập cũ phải bị thu hồi. Hệ thống phải giữ lại ít nhất một người quản trị toàn hệ thống đang hoạt động. | Chỉ dùng trong nội bộ |
| OPS-42 | Khóa và mở tài khoản | Người quản trị vận hành | Người quản trị có thể ngăn một tài khoản đăng nhập hoặc cho phép tài khoản hoạt động trở lại. | Tài khoản của nhân viên đã ngừng hoạt động không được tiếp tục đăng nhập. | Chỉ dùng trong nội bộ |
| OPS-43 | Đặt lại mật khẩu và thu hồi phiên | Người quản trị vận hành | Người quản trị đặt mật khẩu mới hoặc đăng xuất tài khoản khỏi mọi thiết bị. | Mật khẩu mới phải đạt độ dài tối thiểu và thao tác phải được ghi lại. | Chỉ dùng trong nội bộ |
| OPS-44 | Nhật ký vận hành | Quản lý showroom và người quản trị vận hành | Cổng vận hành lưu ai đã làm gì, với dữ liệu nào, trong showroom nào và vào thời điểm nào. | Quản lý chỉ xem nhật ký của showroom mình. Người quản trị được xem toàn hệ thống. | Chỉ dùng trong nội bộ |

---

## 7. Độ tin cậy, quyền riêng tư và an toàn

### 7.1 Bảng đặc tả tính năng

| Mã | Tên tính năng | Đối tượng được bảo vệ | Mô tả theo khái niệm | Quy tắc quan trọng | Mức hoàn thiện |
|---|---|---|---|---|---|
| SAF-01 | Ngăn hai lịch giữ cùng một xe và một giờ | Khách hàng và showroom | Hệ thống kiểm tra xung đột trong cùng lần lưu dữ liệu để chỉ một yêu cầu được giữ chỗ. | Hai yêu cầu tới gần như cùng lúc không được tạo hai lịch hợp lệ trên cùng nguồn lực. | Đã có trong sản phẩm |
| SAF-02 | Kiểm tra xe sẵn sàng | Khách hàng và showroom | Trước khi hiển thị hoặc xác nhận giờ, hệ thống kiểm tra xe thuộc đúng showroom, không bị khóa và đủ điều kiện vận hành. | Xe đang bảo trì, ngừng phục vụ hoặc không đạt mức pin không được dùng cho lịch mới. | Đã có trong sản phẩm |
| SAF-03 | Kiểm tra nhân viên có thể phục vụ | Khách hàng và showroom | Hệ thống chỉ phân công nhân viên có ca làm phù hợp và không có công việc trùng. | Khi không tìm được nhân viên hợp lệ, hệ thống không được khẳng định rằng lịch đã có người phụ trách. | Đã có trong sản phẩm |
| SAF-04 | Kiểm tra lại trước xác nhận | Người đặt lịch | Hệ thống kiểm tra lại chỗ giữ, xe, giờ và phiên bản dữ liệu ngay trước khi tạo mã lịch. | Một chỗ từng còn trống nhưng đã hết hạn hoặc không còn hợp lệ phải bị từ chối ở bước cuối. | Đã có trong sản phẩm |
| SAF-05 | Chống tạo trùng khi người dùng bấm lại | Người đặt lịch và showroom | Mỗi thao tác quan trọng có dấu nhận biết riêng để hệ thống trả lại kết quả cũ khi nhận đúng yêu cầu lần nữa. | Việc bấm hai lần hoặc gửi lại do mạng chậm không được tạo lịch, hủy lịch hoặc đổi lịch hai lần. | Đã có trong sản phẩm |
| SAF-06 | Phát hiện dữ liệu đã thay đổi | Người đặt lịch và showroom | Hệ thống dùng số phiên bản để biết một người đang sửa trên dữ liệu đã cũ. | Khi có xung đột, hệ thống phải yêu cầu tải lại thay vì ghi đè thay đổi mới hơn. | Đã có trong sản phẩm |
| SAF-07 | Mã xác minh có thời hạn và giới hạn lần thử | Người đặt lịch | Mã xác minh hết hiệu lực sau một khoảng thời gian và bị khóa sau quá nhiều lần nhập sai. | Hệ thống chỉ lưu dạng đã được bảo vệ của mã và không lưu nguyên mã để người vận hành đọc lại. | Đã có trong sản phẩm |
| SAF-08 | Quyền truy cập theo mục đích | Người đặt lịch | Sau khi xác minh, người dùng chỉ nhận những quyền cần cho việc đang làm như xem, sửa, đổi hoặc hủy. | Quyền không được tự mở rộng sang một thao tác khác hoặc một lịch của người khác. | Đã có trong sản phẩm |
| SAF-09 | Che dữ liệu nhạy cảm trong kết quả và nhật ký | Tất cả người dùng | Trước khi trả kết quả hoặc ghi nhật ký, hệ thống che mã bí mật, quyền truy cập và các trường riêng tư không cần thiết. | Nhật ký không được chứa nguyên mã xác minh, khóa truy cập hoặc toàn bộ nội dung riêng tư của khách hàng. | Đã có trong sản phẩm |
| SAF-10 | Kiểm tra nội dung người dùng gửi | Tất cả người dùng công khai | Hệ thống giới hạn độ dài, cấu trúc và nội dung bất thường trước khi chuyển yêu cầu tới phần xử lý. | Nội dung cố lấy quy tắc bí mật, làm sai quyền hoặc chứa cấu trúc quá lớn phải bị chặn bằng lời giải thích dễ hiểu. | Đã có trong sản phẩm |
| SAF-11 | Giới hạn số yêu cầu | Tất cả người dùng và hệ thống | Hệ thống giới hạn số lượt trò chuyện, thao tác đặt lịch và yêu cầu mã theo người dùng và theo khoảng thời gian. | Khi vượt giới hạn, hệ thống phải nói người dùng cần chờ bao lâu và không được làm mất lịch đang có. | Đã có trong sản phẩm |
| SAF-12 | Cảnh báo và khóa tạm thời hành vi lạm dụng | Tất cả người dùng | Hệ thống ghi nhận vi phạm rõ ràng, cảnh báo số lần và có thể khóa tạm thời khi một nguồn lặp lại hành vi nguy hiểm. | Việc khóa phải có thời hạn và không được dựa vào một câu thông thường vô hại. | Đã có trong sản phẩm |
| SAF-13 | Giới hạn quyền của từng nhóm chức năng | Tất cả người dùng | Phần đặt lịch, phần chăm sóc và cổng nội bộ chỉ được dùng những hành động đã cho phép trong đúng phạm vi. | Phần chăm sóc không được tự hủy, đổi hoặc xác nhận lịch nếu chưa có hành động rõ ràng của người có quyền. | Đã có trong sản phẩm |
| SAF-14 | Kiểm tra câu trả lời trước khi gửi | Người trò chuyện với ViVi | Hệ thống kiểm tra độ dài, dữ liệu bí mật và sự phù hợp của trạng thái trước khi gửi câu trả lời. | Câu trả lời không được nói một trạng thái khác với dữ liệu thật của lịch. | Đã có trong sản phẩm |
| SAF-15 | Tiếp tục hoạt động khi một phần gặp lỗi | Tất cả người dùng | Đặt lịch bằng nút và trường lựa chọn vẫn có thể hoạt động khi phần trò chuyện tạm ngưng. Nội dung công khai vẫn có thể xem khi phần đặt lịch tạm lỗi. | Mỗi phần phải báo đúng tình trạng và không được giả lập một kết quả thành công. | Đã có trong sản phẩm |
| SAF-16 | Lưu bản tạm để tăng tốc nhưng không che dữ liệu mới | Người xem xe | Trang web có thể giữ bản tạm của danh mục và nội dung để mở nhanh hơn. | Khi nguồn chính có phiên bản mới, trang web phải dùng dữ liệu mới. Kiểm tra tình trạng dịch vụ không được dùng bản tạm. | Đã có trong sản phẩm |
| SAF-17 | Nhập dữ liệu có kiểm tra | Người quản trị vận hành | Hệ thống có công cụ nhập danh mục showroom và dữ liệu vận hành từ tệp có cấu trúc. | Chỉ người quản trị toàn hệ thống được thực hiện. Tài khoản, phiên đăng nhập và dữ liệu bảo mật không được nhập qua chức năng này. | Chỉ dùng trong nội bộ |
| SAF-18 | Bảo toàn lịch sử thay vì xóa dữ liệu đang dùng | Showroom và nhóm vận hành | Showroom, mẫu xe và phiên bản đã được lịch cũ sử dụng sẽ được ngừng hoạt động thay vì xóa hoàn toàn. | Báo cáo và lịch sử cũ phải tiếp tục giải thích được dữ liệu tại thời điểm phát sinh. | Đã có trong sản phẩm |

---

## 8. Công cụ kiểm tra và đánh giá nội bộ

### 8.1 Bảng đặc tả tính năng

| Mã | Tên tính năng | Người sử dụng | Mô tả theo khái niệm | Quy tắc quan trọng | Mức hoàn thiện |
|---|---|---|---|---|---|
| QUA-01 | Bộ kiểm tra tình huống đã biết | Nhóm phát triển | Dự án chạy lại các tình huống từng dùng trong quá trình phát triển để phát hiện lỗi quay lại. | Kết quả trên bộ này chỉ chứng minh độ ổn định với tình huống đã biết. | Chỉ dùng trong nội bộ |
| QUA-02 | Bộ tình huống hoàn toàn mới | Nhóm phát triển | Dự án dùng một bộ tình huống được giữ kín trước lần chạy chính thức để đo khả năng xử lý cách nói mới. | Một bộ đã dùng để sửa lỗi không được tiếp tục gọi là bộ hoàn toàn mới trong lần đánh giá sau. | Chỉ dùng trong nội bộ |
| QUA-03 | Kiểm tra quyền và hành vi nguy hiểm | Nhóm phát triển | Dự án có các trường hợp thử việc lộ dữ liệu, dùng lại mã, truy cập chéo, tạo lịch trùng và làm sai quy tắc. | Một trường hợp vi phạm nghiêm trọng phải làm lần kiểm tra thất bại. | Chỉ dùng trong nội bộ |
| QUA-04 | Kiểm tra độ ổn định qua nhiều lần chạy | Nhóm phát triển | Cùng một bộ tình huống được chạy nhiều lần để phát hiện kết quả thay đổi thất thường. | Nhóm em phải công bố số tình huống, số lần chạy và phạm vi kết luận. | Chỉ dùng trong nội bộ |
| QUA-05 | Cổng đánh giá riêng | Người đánh giá nội bộ | Người đánh giá đăng nhập vào một cổng tách biệt để chấm phản hồi mà không có quyền xem lịch khách hàng hoặc cổng showroom. | Tài khoản đánh giá không được dùng chung với tài khoản vận hành. | Chỉ dùng trong nội bộ |
| QUA-06 | Hàng đợi tình huống cần chấm | Người đánh giá nội bộ | Cổng đánh giá hiển thị các tình huống chưa chấm, đã chấm, tất cả tình huống hoặc các trường hợp có bất đồng. | Mỗi người đánh giá chỉ nhìn thấy kết quả chấm của mình trong lúc thực hiện đánh giá độc lập. | Chỉ dùng trong nội bộ |
| QUA-07 | Tìm kiếm tình huống | Người đánh giá nội bộ | Người đánh giá tìm theo mã tình huống hoặc nội dung yêu cầu để mở đúng trường hợp cần xem. | Tìm kiếm không được làm thay đổi dữ liệu chấm. | Chỉ dùng trong nội bộ |
| QUA-08 | Xem yêu cầu, phản hồi và bằng chứng | Người đánh giá nội bộ | Mỗi tình huống trình bày yêu cầu của người dùng, câu trả lời, hành động đã thực hiện và kết quả dùng để đối chiếu. | Dữ liệu riêng tư và mã bí mật phải được che trước khi hiển thị. | Chỉ dùng trong nội bộ |
| QUA-09 | Hướng dẫn chấm thống nhất | Người đánh giá nội bộ | Cổng đánh giá giải thích cách quyết định tình huống đạt hay không và cách dùng thang điểm từ một đến năm. | Người đánh giá phải đọc bằng chứng trước khi dựa vào kết quả kiểm tra tự động. | Chỉ dùng trong nội bộ |
| QUA-10 | Chấm năm tiêu chí | Người đánh giá nội bộ | Người đánh giá chấm tính đúng, mức liên quan, mức có căn cứ, mức an toàn và mức hài lòng. | Mỗi tiêu chí phải được chấm riêng; một câu trả lời lịch sự không tự động được xem là đúng. | Chỉ dùng trong nội bộ |
| QUA-11 | Ghi nhận hành vi không được phép | Người đánh giá nội bộ | Người đánh giá có thể ghi nhãn khi quan sát thấy hành vi như bịa dữ liệu hoặc làm lộ thông tin của người khác. | Người đánh giá chỉ ghi nhãn khi có bằng chứng cụ thể. | Chỉ dùng trong nội bộ |
| QUA-12 | Tự lưu bản chấm chưa hoàn tất | Người đánh giá nội bộ | Cổng đánh giá giữ tạm lựa chọn của người đánh giá trên thiết bị để họ không mất công việc khi chuyển tình huống. | Bản chưa hoàn tất không được tính vào kết quả chính thức. | Chỉ dùng trong nội bộ |
| QUA-13 | Yêu cầu chấm đủ trước khi nộp | Người đánh giá nội bộ | Cổng đánh giá chỉ cho nộp khi đã chọn kết quả đạt hoặc không đạt và hoàn tất đủ năm nhóm điểm. | Ghi chú có thể bổ sung nhưng không được thay cho các trường bắt buộc. | Chỉ dùng trong nội bộ |
| QUA-14 | Theo dõi tiến độ và bất đồng | Nhóm đánh giá | Cổng đánh giá hiển thị số trường hợp mỗi người đã chấm, số trường hợp đủ hai người và số trường hợp có kết luận khác nhau. | Bất đồng phải được phân xử độc lập, không được sửa điểm chỉ để làm kết quả trông đồng nhất. | Chỉ dùng trong nội bộ |
| QUA-15 | Xuất kết quả đánh giá | Nhóm đánh giá | Người có quyền có thể tải kết quả chấm thành tệp để đưa vào báo cáo tổng hợp. | Tệp chỉ chứa dữ liệu đánh giá được phép xuất và không được chứa thông tin bí mật của hệ thống. | Chỉ dùng trong nội bộ |

---

## 9. Những phần không được xem là tính năng của phiên bản chính thức

Một số tệp hoặc nhánh xử lý vẫn còn trong kho mã để phục vụ thử nghiệm cũ, chuyển đổi dữ liệu hoặc phát triển nội bộ. Nhóm em không xem những phần này là tính năng đã cam kết với người dùng.

| Hạng mục | Cách hiểu chính thức |
|---|---|
| Gửi thông báo qua Zalo hoặc tin nhắn điện thoại | Phiên bản chính thức chỉ dùng thư điện tử. Những phần cũ liên quan tới kênh khác không thuộc phạm vi sản phẩm hiện tại. |
| Mua xe, đặt cọc và thanh toán | Sản phẩm dừng ở việc tổ chức buổi lái thử và không xử lý giao dịch mua bán. |
| Vay, bảo hiểm, đổi xe cũ và đàm phán giá | ViVi không cam kết hoặc thực hiện các nghiệp vụ tài chính và bán hàng này. |
| Tự động chuyển cuộc trò chuyện cho nhân viên | ViVi chỉ hiển thị đầu mối showroom để người dùng chủ động liên hệ. |
| Lịch ưu tiên đặc biệt hoặc duyệt tay từng giờ | Hệ thống dùng dữ liệu xe, nhân sự và khung giờ có thật; phiên bản hiện tại không có nhánh ưu tiên riêng. |
| Đồng bộ lịch hai chiều | Người dùng chỉ có thể thêm sự kiện vào lịch cá nhân. Sản phẩm không đọc hoặc tự cập nhật lịch cá nhân của họ. |
| Lưu ảnh hoặc số giấy phép lái xe | Showroom chỉ kiểm tra giấy phép bản gốc và lưu kết quả kiểm tra. |
| Tự động bán hàng sau khi lái thử | Phiên bản hiện tại kết thúc khi buổi lái thử được hoàn tất hoặc ghi nhận vắng mặt. |
| Tư vấn chọn xe tổng quát trước khi đặt | ViVi có thể giải thích thông tin trong phạm vi, nhưng không thay thế toàn bộ quá trình chọn xe bằng một cuộc trò chuyện dài. |
| Mở rộng thêm phim hoặc mô hình ba chiều | Dự án giữ những nội dung trực quan đã có, nhưng không xem việc mở rộng chúng là ưu tiên của quy trình đặt lịch hiện tại. |
| Màn quản trị cũ dùng trong phát triển | Cổng vận hành DriveOps là cổng nội bộ chính thức. Màn quản trị cũ chỉ còn để hỗ trợ một số công việc phát triển và không nằm trong sản phẩm nộp cuối. |

---

## 10. Các nguyên tắc chung của toàn bộ tính năng

Thứ nhất, nhóm em dùng giao diện có cấu trúc cho xe, showroom, ngày, giờ, thông tin người tham gia và các hành động quản lý. ViVi chỉ hướng dẫn, giải thích và chăm sóc; ViVi không được thay các lựa chọn chính xác bằng một cuộc trò chuyện kéo dài.

Thứ hai, mọi phần của sản phẩm phải dùng cùng một trạng thái lịch. Khi lịch đang giữ chỗ, người dùng không được nhìn thấy thông báo đã xác nhận. Khi lịch đã hủy hoặc đã đổi, lời nhắc và đường dẫn cũ phải dừng hoạt động.

Thứ ba, người đặt và người lái là hai vai trò riêng khi một người đặt hộ người khác. Hệ thống chỉ chia sẻ lượng thông tin tối thiểu cần thiết và không trao quyền đổi hoặc hủy lịch cho người lái được mời.

Thứ tư, hệ thống chỉ tạo một lịch khi xe, showroom, khung giờ, người phụ trách và bước xác minh đều hợp lệ. Nếu một điều kiện thay đổi trước bước cuối, hệ thống phải từ chối an toàn và đưa người dùng quay lại lựa chọn phù hợp.

Thứ năm, nội dung về giá, chính sách, giấy tờ, sạc và sản phẩm phải có nguồn cùng phạm vi áp dụng. Khi chưa có nội dung đã duyệt, ViVi phải nói rõ giới hạn và hiển thị đầu mối showroom.

Thứ sáu, hệ thống thu thập lượng dữ liệu tối thiểu để tổ chức buổi lái thử. Hệ thống không lưu ảnh hoặc số giấy phép lái xe, không công khai mã xác minh và không ghi dữ liệu bí mật vào nhật ký.

Thứ bảy, một phần gặp lỗi không được làm hỏng toàn bộ hành trình. Khi ViVi tạm ngưng, người dùng vẫn quản lý được lịch. Khi đặt lịch tạm ngưng, người dùng vẫn xem được thông tin công khai còn khả dụng.

---

## 11. Kết luận

Bản đặc tả này cho thấy ViVi không chỉ là một khung trò chuyện. Dự án là một hệ thống hoàn chỉnh gồm trang khám phá xe, quy trình đặt lịch có giữ chỗ và xác minh, phần tự quản lý lịch, chăm sóc sau xác nhận, đường dẫn riêng cho người lái và cổng vận hành showroom.

Các tính năng công khai giúp người dùng chuyển từ tìm hiểu xe sang một lịch lái thử có trạng thái rõ ràng. Các tính năng nội bộ giúp showroom chuẩn bị đúng xe, đúng nhân viên và đóng lại kết quả của từng buổi hẹn. Các lớp bảo vệ và công cụ đánh giá giúp nhóm em kiểm tra rằng sản phẩm không tạo lịch trùng, không chia sẻ sai dữ liệu và không công bố một kết quả tốt hơn bằng chứng thực tế.

Tài liệu này được dùng làm bản mô tả tính năng theo khái niệm. Khi nhóm em thay đổi phạm vi hoặc thêm một tính năng mới, nhóm em phải cập nhật cả bản đặc tả này và tài liệu yêu cầu sản phẩm để hai tài liệu luôn thống nhất.
