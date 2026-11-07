# Kiến thức cần đọc để hiểu bài tiểu luận

## Tóm tắt

Bài tiểu luận giải quyết tình huống một người đã đăng nhập vào kho tài liệu, sau đó bị khóa tài khoản ở bên quản lý tài khoản nhưng phiên tại kho vẫn còn hạn. Kho cần biết thay đổi này để chặn các lượt truy cập tiếp theo.

Kiến trúc có ba phần: bên quản lý tài khoản theo dõi người và thiết bị; kho tài liệu quản lý quyền, nhãn và nội dung; bộ điều phối theo dõi phiên và xử lý thu hồi giữa hai bên. Microsoft Zero Trust cung cấp khung xác định trách nhiệm bảo vệ. Google BeyondCorp cung cấp tham chiếu cho đường truy cập ứng dụng qua cổng kiểm tra danh tính và thiết bị.

Web cho thử ba cách: Kiểm tra khi đăng nhập; Thu hồi theo thông báo; Thu hồi theo thông báo và tự kiểm tra lại. Tất cả dùng cùng quy tắc truy cập tài liệu. Chúng cho thấy điều gì xảy ra khi tài khoản bị khóa, thông báo bị mất hoặc bên quản lý tài khoản không phản hồi.

Để hiểu toàn bộ bài, cần phân biệt đăng nhập, phiên truy cập, quyền với tài liệu và tình trạng thiết bị. Phần dưới giải thích lần lượt các khái niệm này, công nghệ sử dụng và cách kiến trúc phối hợp.

## Mục đích và đầu ra

Mục đích là thiết kế, triển khai và kiểm tra cơ chế phối hợp giữa hai bên quản trị có trách nhiệm riêng. Thành công cần thể hiện cả yêu cầu hợp lệ được xử lý đúng và yêu cầu không còn đủ điều kiện bị dừng đúng lý do.

| Đầu ra | Nội dung cần thể hiện |
|---|---|
| Quy chuẩn dữ liệu | Phân biệt Nội bộ, Mật, Hạn chế bằng nội dung và hậu quả tiết lộ |
| Kiến trúc | Ai quản lý tài khoản, ai quản lý tài liệu, ai cấp và thu hồi phiên |
| Nguyên mẫu | Đăng nhập, xác minh thiết bị, quyền hiện tại, mã hóa, nhật ký và quản lý dữ liệu |
| Kiểm tra | Khóa tài khoản, mất thông báo, mất kết nối, sai quyền, lỗi thành phần và phục hồi phiên |

Đối tượng nghiên cứu là cơ chế phối hợp đã triển khai. Nguyên mẫu sử dụng công cụ miễn phí và dữ liệu tổng hợp để tái lập trên máy cá nhân.

## Bốn khái niệm quan trọng nhất

### Đăng nhập

Đăng nhập xác nhận người đang sử dụng tài khoản. Keycloak kiểm tra tài khoản và cấp thông tin đăng nhập có chữ ký. API kiểm tra thông tin này để nhận diện người gửi.

Đăng nhập thành công chưa xác định người đó được tải tài liệu nào. Một thông tin đăng nhập còn thời hạn cũng chưa chứng minh tài khoản vẫn được phép hoạt động ở thời điểm sau đó.

### Phiên truy cập tại kho

Sau khi xác minh người, thiết bị và trạng thái, bộ điều phối cấp phiên riêng cho kho. Phiên gắn với đúng người, thiết bị, cách kiểm tra và thời hạn. Các yêu cầu tiếp theo sử dụng phiên này.

Thu hồi phiên làm phiên cũ không còn dùng được. Mở khóa tài khoản không tự mở lại phiên đã thu hồi; người dùng cần đăng nhập để nhận phiên mới.

### Quyền với tài liệu

Quyền tài liệu trả lời người này được thực hiện thao tác nào với tài liệu này. Kho quản lý vai trò, phòng ban, nhãn, chủ sở hữu và các quyền truy cập có thời hạn.

Ví dụ, nhân viên cùng phòng có thể đọc tài liệu Nội bộ. Với tài liệu Mật, nhân viên còn cần là chủ sở hữu; trưởng phòng cùng phòng có phạm vi phù hợp với vai trò. Với Hạn chế, tải nội dung cần thêm quyền còn hạn cho đúng tài liệu và phiên bản.

### Tình trạng thiết bị

Chứng thư giúp cổng xác minh thiết bị sở hữu khóa đã đăng ký và đối chiếu thiết bị với tài khoản. Hồ sơ trạng thái cho biết thiết bị đã bị thu hồi, có đáp ứng yêu cầu an toàn, có rủi ro cao và thông tin kiểm tra còn dùng được hay không.

Chứng thư đúng chưa bảo đảm máy không có mã độc. Các tín hiệu an toàn trong demo được mô phỏng để tạo tình huống; trình duyệt không tự quét máy tính đang dùng.

## RBAC, ABAC và Zero Trust

RBAC là phân quyền theo vai trò. Kiểm toán có quyền đọc nhật ký; trưởng phòng có phạm vi nghiệp vụ của trưởng phòng. ABAC xét thêm thuộc tính như phòng ban, nhãn, chủ sở hữu, thời hạn và tình trạng thiết bị.

Zero Trust yêu cầu xác minh phù hợp trước khi sử dụng tài nguyên. Trong nguyên mẫu, cổng kiểm tra thiết bị, bộ điều phối kiểm tra phiên và trạng thái, kho kiểm tra quyền với tài liệu. Người đã đăng nhập hoặc ở mạng nội bộ vẫn chịu các kiểm tra này.

Quy tắc cuối cùng có thể được viết bằng điều kiện logic. Phần kiến trúc cần xác định điều kiện lấy từ đâu, có đáng tin không, thành phần nào kiểm tra, thành phần nào thực thi và xử lý ra sao khi nguồn thông tin lỗi.

## Dữ liệu và người dùng

Kho sử dụng hai phòng nghiệp vụ: Kinh doanh và Vận hành. Bộ dữ liệu nền có 20 tài liệu tổng hợp; người vận hành có thể bổ sung nhân viên và tài liệu, nên số hiện trên web có thể lớn hơn số khởi tạo.

| Nhãn | Ví dụ | Điều kiện nội dung chính |
|---|---|---|
| Nội bộ | Quy trình, lịch phối hợp, báo cáo tổng hợp | Nhân viên hoặc trưởng phòng cùng phòng |
| Mật | Báo giá, dự toán, kế hoạch riêng chưa công bố | Nhân viên sở hữu cùng phòng hoặc trưởng phòng cùng phòng |
| Hạn chế | Giới hạn thương lượng, điểm yếu chưa khắc phục, kế hoạch phục hồi trọng yếu | Trưởng phòng cùng phòng, có quyền truy cập phù hợp và còn hạn |

Các điều kiện trên áp dụng cùng trạng thái tài khoản, thiết bị, phiên và thời hạn tài liệu. Ba nhãn là quy ước của bài toán, không phải cấp độ bí mật nhà nước. Nhãn được chọn thủ công; hệ thống chưa tự đọc nội dung để xác định mức nhạy cảm.

Quản trị đối tác quản lý tài khoản và thiết bị của đối tác. Quản trị kho quản lý an toàn và phê duyệt tại kho. Kiểm toán kho đọc nhật ký, cảnh báo. Quyền quản trị không tự tạo quyền đọc mọi tài liệu.

## Kiến trúc đã triển khai

| Thành phần | Công việc |
|---|---|
| Bên quản lý tài khoản | Trả thông tin trạng thái có chữ ký, ghi và gửi thông báo thay đổi |
| Bộ điều phối | Liên kết tài khoản với đúng nguồn trạng thái, cấp và kiểm tra phiên, nhận thông báo, hỏi lại và thu hồi |
| Kho tài liệu | Đọc quyền hiện tại, kiểm tra tài liệu, thực thi quyết định, mã hóa hoặc giải mã và ghi nhật ký |

Cơ sở dữ liệu và khóa ký được tách theo trách nhiệm. Kho không đọc trực tiếp cơ sở dữ liệu tài khoản của đối tác để bỏ qua cơ chế phối hợp. Nhân viên kho được xác minh bằng nguồn trạng thái nội bộ của kho.

Ba cơ sở dữ liệu vẫn dùng chung máy chủ PostgreSQL và môi trường chạy. Việc tách ở đây là tách quyền quản lý, tài khoản dịch vụ và khóa, chưa phải tách hạ tầng vật lý của hai doanh nghiệp.

## Một yêu cầu tải đi qua đâu?

1. Đăng nhập: Keycloak xác minh tài khoản.
2. Kiểm tra thiết bị: cổng xác minh chứng thư đã đăng ký.
3. Ghép đúng người: API và bộ điều phối kiểm tra tài khoản, thiết bị và bên quản lý có khớp.
4. Cấp phiên truy cập: bộ điều phối xác minh trạng thái có chữ ký rồi tạo phiên.
5. Kiểm tra phiên: kho xác nhận phiên còn dùng được; hỏi lại trạng thái nếu thông tin đã lưu quá hạn và cách kiểm tra yêu cầu việc này.
6. Kiểm tra quyền: OPA xét vai trò, phòng ban, nhãn, thời hạn và quyền riêng của tài liệu.
7. Quyết định: tiếp tục khi đủ điều kiện, dừng và nêu lý do khi không đạt.
8. Chuẩn bị tài liệu: lấy bản mã, giải mã và kiểm tra nội dung.
9. Kiểm tra lần cuối: ghi nhật ký, kiểm tra lại phiên và thời hạn trước khi hoàn tất.
10. Trả kết quả: gửi tệp hoặc lý do dừng yêu cầu.

Bốn bước đầu tạo phiên; các lần tải bằng phiên đó lặp lại bước 5–10 và vẫn đi qua kết nối đã xác minh thiết bị. Xem sơ đồ tại [kiến trúc](architecture.md).

## Ba cách kiểm tra giúp đánh giá điều gì?

| Cách kiểm tra | Sau khi tài khoản bị khóa | Nếu mất thông báo khóa |
|---|---|---|
| Kiểm tra khi đăng nhập | Phiên cũ có thể tiếp tục dùng đến hết hạn | Chưa phát hiện thay đổi trong phiên cũ |
| Thu hồi theo thông báo | Thu hồi sau khi nhận và xử lý thông báo | Có thể tiếp tục giữ phiên cũ |
| Thu hồi theo thông báo và tự kiểm tra lại | Thu hồi theo thông báo hoặc sau khi hỏi lại | Hỏi lại để phát hiện thay đổi; tạm dừng khi thông tin cũ hết hạn mà chưa xác nhận lại được |

Giữ nguyên người dùng, tài liệu, thiết bị và quyền tại kho khi so sánh. Nhờ đó kết quả phản ánh cơ chế cập nhật trạng thái. So sánh diễn ra trong một nguyên mẫu, không đánh giá khả năng tổng quát của Microsoft hay Google.

## Công nghệ sử dụng

| Công nghệ | Vai trò |
|---|---|
| HTML, CSS, JavaScript | Hiển thị biểu mẫu, kết quả và hướng dẫn lỗi |
| Python, FastAPI, Uvicorn | Xử lý yêu cầu và chạy các dịch vụ của nguyên mẫu |
| Keycloak | Đăng nhập và cung cấp thông tin danh tính có chữ ký |
| NGINX | Cổng truy cập, bảo vệ kết nối và xác minh chứng thư thiết bị |
| OPA, Rego | Đánh giá bộ quy tắc truy cập tài liệu |
| PostgreSQL | Lưu tài khoản, phiên, quyền, thông tin tài liệu, bản mã và nhật ký theo cơ sở dữ liệu được phân quyền |
| OpenBao Transit | Thực hiện mã hóa, giải mã với khóa được quản lý |
| Docker Compose trong WSL 2 | Chạy chín dịch vụ cục bộ và quản lý mạng, dữ liệu của chúng |

[Danh mục phần mềm](software-inventory.md) ghi phiên bản dùng trong lượt kiểm tra. Dịch vụ mã hóa và cơ sở dữ liệu có chức năng khác nhau: OpenBao xử lý mật mã, PostgreSQL giữ bản mã cùng thông tin quản lý.

## Thông tin tài liệu, phê duyệt và quyền có thời hạn

Thông tin tài liệu gồm tên, nhãn, chủ sở hữu, phiên bản và thời hạn. Xem được các thông tin này chưa đồng nghĩa được tải nội dung. Với Hạn chế, trưởng phòng cùng phòng có thể xem thông tin nhưng vẫn cần quyền riêng để tải và sửa.

Phê duyệt tạo hoặc nâng nhãn cho phép lưu tài liệu Hạn chế ở một phiên bản xác định và chỉ sử dụng thành công một lần. Quyền truy cập có thời hạn cho phép tải, sửa tài liệu phù hợp ở nhiều yêu cầu khi còn hiệu lực. Hai loại cấp phép này có mục đích khác nhau.

Thêm trực tiếp Hạn chế cần trưởng phòng và quản trị an toàn phê duyệt. Tài liệu, quyền ban đầu và trạng thái đã dùng phê duyệt được ghi cùng giao dịch. Sửa hiện tại là sửa thông tin hoặc nâng nhãn, chưa thay thế nội dung tệp; không cho hạ nhãn. Xem [quy chuẩn dữ liệu](data-classification.md).

## Mã hóa, nhật ký và xử lý lỗi

Nội dung tài liệu được mã hóa trước khi lưu. API chỉ lấy và giải mã nội dung sau khi điều kiện truy cập đạt. Mã băm được dùng để kiểm tra nội dung tải về còn nguyên vẹn; mã băm không phải khóa giải mã.

Nhật ký lưu người yêu cầu, thao tác, quyết định và lý do. Mã yêu cầu nối phản hồi với bản ghi để kiểm tra lại. Nhật ký không cần chứa mật khẩu, bí mật phiên hay nội dung tài liệu.

Khi chưa kiểm tra được quyền, chưa ghi được nhật ký bắt buộc hoặc chưa giải mã được nội dung, hệ thống dừng cấp nội dung. Đây là đánh đổi: bảo vệ dữ liệu có thể khiến người hợp lệ tạm thời chưa sử dụng được dịch vụ.

## Phần tham chiếu, phần hiện thực và giới hạn

Microsoft Zero Trust giúp xác định các trách nhiệm bảo vệ. BeyondCorp cung cấp căn cứ cho đường truy cập theo danh tính và thiết bị. Phần tích hợp cụ thể là liên kết tài khoản, trao đổi trạng thái có chữ ký, thu hồi phiên và tự hỏi lại khi thiếu thông tin. [Tài liệu tham chiếu](ke_thua.md) giải thích từng phần và vị trí triển khai.

Đăng nhập, chứng thư, chữ ký, kiểm tra quyền, truy vấn cơ sở dữ liệu và mã hóa được thực thi bằng dịch vụ thật trong môi trường cục bộ. Doanh nghiệp, nội dung nghiệp vụ và tín hiệu an toàn thiết bị là giả định thử nghiệm. Một số lỗi được tạo có kiểm soát để quan sát cách hệ thống dừng yêu cầu.

Nguyên mẫu chưa kết nối trực tiếp dịch vụ đám mây Microsoft hoặc Google, chưa kiểm tra chịu tải doanh nghiệp và chưa triển khai cách ly vật lý giữa hai bên. Công cụ điều khiển có đặc quyền vận hành trên máy thử. Tệp đã tải về máy nằm ngoài phạm vi thu hồi phiên.

## Đọc tiếp và tự kiểm tra hiểu bài

Nếu giải thích được bốn câu sau thì đã nắm phần cốt lõi:

1. Tại sao tài khoản bị khóa nhưng phiên còn hạn có thể gây rủi ro?
2. Bên quản lý tài khoản, kho tài liệu và bộ điều phối quyết định những việc gì?
3. Khi thông báo bị mất hoặc bên quản lý tài khoản không phản hồi, cách tự kiểm tra lại xử lý ra sao?
4. Vì sao phiên hợp lệ vẫn có thể bị từ chối với một tài liệu cụ thể?

Tiếp theo đọc [hướng dẫn nhanh](huong_dan_nhanh.md), [sơ đồ](architecture.md), [ma trận kiểm tra](test-matrix.md) và [kết quả đã lưu](ket_qua_kiem_chung.md). Khi chuẩn bị trình bày, dùng [script 10 phút](script_thuyet_trinh_10_phut.md).
