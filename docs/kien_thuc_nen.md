# Kiến thức nền để hiểu báo cáo và web demo

Cập nhật tài liệu ngày 25/10/2026 theo mã và bằng chứng đã có; lần cập nhật này không chạy lại demo. [Mục lục tài liệu](muc_luc.md).

Đọc nhanh phần đầu để nắm ý chính; các phần sau giải thích từng khái niệm và đi qua một yêu cầu cụ thể. Khi cần thao tác, xem [hướng dẫn nhanh](huong_dan_nhanh.md). Khi gặp mã viết tắt, xem [giải thích ký hiệu](giai_thich_ky_hieu.md).

## Đọc trong một phút

Nhóm xây dựng một kho tài liệu giả lập để nghiên cứu cách bảo vệ dữ liệu. Website là nơi tạo tình huống và quan sát kết quả; phần cần đánh giá là các lớp kiểm soát phía sau.

- Đăng nhập trả lời câu hỏi người gửi là ai. Quyền truy cập trả lời người đó có được làm việc đang yêu cầu hay không.
- Một người đã đăng nhập vẫn có thể bị chặn vì tài liệu thuộc người khác, khác phòng, nhãn cao hơn quyền, quyền bị thu hồi hoặc thiết bị không phù hợp.
- Trước mỗi yêu cầu mới, B1 lấy trạng thái hiện tại từ máy chủ để kiểm tra. Token còn hạn không giữ nguyên mọi quyền lúc đăng nhập.
- Nội dung được lưu dưới dạng bản mã. Chỉ khi yêu cầu hợp lệ, hệ thống mới giải mã để trả nội dung và ghi dấu vết tương ứng.
- B0 là cấu hình đối chứng giản lược do nhóm đặt. B1 là cấu hình chính sách đề xuất trong kiến trúc của nhóm. B0/B1 không phải tên hai kiến trúc của Google và Microsoft.
- Google BeyondCorp, Microsoft Zero Trust cùng các mô hình tham chiếu cung cấp căn cứ thiết kế. Nhóm cụ thể hóa chúng cho một kho tài liệu; kết quả demo không phải kết quả thử nghiệm hệ thống của Google hoặc Microsoft.

Ví dụ xuyên suốt: alice và anna cùng phòng Kinh doanh. A-C02 là tài liệu Mật do anna sở hữu. alice đăng nhập đúng vẫn chưa đủ quyền tải tài liệu đó trong B1.

## 1. Bài tiểu luận đang giải quyết việc gì?

Câu hỏi nghiên cứu là: làm thế nào tổ chức các thành phần để một kho tài liệu chỉ xử lý dữ liệu khi yêu cầu đáp ứng điều kiện bảo vệ, đồng thời kiểm soát được lưu trữ, nhật ký và phục hồi?

Đầu ra gồm bốn phần có liên hệ:

| Đầu ra | Vai trò |
|---|---|
| Quy chuẩn và chính sách | Xác định dữ liệu nào nhạy cảm, ai được dùng, khi nào quyền hết hiệu lực |
| Kiến trúc | Xác định điểm nhận yêu cầu, nguồn danh tính/thuộc tính, nơi quyết định, nơi thực thi và các đường dữ liệu |
| Nguyên mẫu | Hiện thực các thành phần, giao dịch, mã hóa, audit và công cụ vận hành |
| Kiểm chứng | Tạo ca được phép, bị chặn, thay đổi quyền và lỗi thành phần; đối chiếu phản hồi với kỳ vọng |

Đây là lý do báo cáo cần mô tả dữ liệu, thành phần, luồng và bằng chứng. Chỉ có một giao diện đẹp hoặc một danh sách điều kiện cho phép/từ chối chưa đủ để thể hiện thiết kế kiến trúc.

Ba mục tiêu bảo vệ dữ liệu được dùng như sau:

| Mục tiêu | Ý nghĩa trong bài | Cơ chế tiêu biểu |
|---|---|---|
| Bí mật | Người ngoài phạm vi không được nhận dữ liệu | Quyền theo tài liệu, nhãn, phòng ban, grant; mã hóa và giới hạn đường truy cập |
| Toàn vẹn | Phát hiện nội dung không còn đúng bản đã lưu | Mật mã, đối chiếu SHA-256, giao dịch và dấu vết thay đổi |
| Khả dụng | Dữ liệu có thể sử dụng và khôi phục trong điều kiện đã xác định | Dịch vụ, sao lưu phối hợp dữ liệu/khóa và diễn tập phục hồi |

Các mục tiêu có đánh đổi. Khi dịch vụ quyết định quyền hoặc khóa không sẵn sàng, nguyên mẫu dừng yêu cầu nhạy cảm. Cách xử lý bảo vệ dữ liệu nhưng làm người dùng hợp lệ cũng tạm thời không sử dụng được.

## 2. Hệ thống có dữ liệu và người dùng nào?

Bộ khởi tạo `business-v1` có 20 tài liệu nghiệp vụ tổng hợp và tám tài khoản. Đây là số của bộ mẫu; số đang hiển thị có thể tăng khi thêm tài liệu và nhân viên.

Hai phòng được ký hiệu A = Kinh doanh và B = Vận hành. Mỗi tài liệu có chủ sở hữu, phòng ban, nhãn, phiên bản và thuộc tính vòng đời. Nhãn được lựa chọn thủ công theo nội dung và hậu quả tiết lộ:

| Nhãn | Ví dụ nội dung | Phạm vi tải trong B1 khi các điều kiện chung hợp lệ |
|---|---|---|
| Nội bộ | Quy trình và lịch phối hợp chung | Nhân viên hoặc trưởng phòng cùng phòng |
| Mật | Báo giá, dự toán, kế hoạch riêng chưa công bố | Nhân viên sở hữu tài liệu hoặc trưởng phòng cùng phòng |
| Hạn chế | Giới hạn thương lượng, điểm yếu chưa khắc phục, kế hoạch phục hồi trọng yếu | Trưởng phòng cùng phòng có grant tải phù hợp và còn hạn |

Nội bộ không có nghĩa công khai. Hạn chế là nhãn nghiệp vụ do nhóm quy ước, không phải mức bí mật nhà nước. Đuôi TXT/PDF không quyết định mức nhạy cảm. Nguyên mẫu không tự phân loại nội dung bằng AI.

Các vai trò chính:

- Nhân viên: dùng tài liệu theo phạm vi phòng ban, nhãn và chủ sở hữu.
- Trưởng phòng: có phạm vi nghiệp vụ rộng hơn trong phòng; chức danh này vẫn chưa đủ để tải Hạn chế khi thiếu grant.
- Kiểm toán: đọc nhật ký và cảnh báo, không mặc nhiên đọc nội dung.
- Quản trị an toàn: quản lý trạng thái, nhãn và phê duyệt; quyền quản trị không tự biến thành quyền đọc nội dung.

Một tài liệu Hạn chế có thể do nhân viên sở hữu trong bộ mẫu để chứng minh rằng sở hữu không tự vượt nhãn. Chi tiết căn cứ từng tài liệu nằm ở [quy chuẩn dữ liệu](data-classification.md).

## 3. Đăng nhập khác cấp quyền như thế nào?

### 3.1. Xác thực danh tính

Khi đăng nhập, Keycloak kiểm tra tài khoản và phát token có chữ ký. API xác minh token để nhận diện chủ thể gửi yêu cầu.

Ví dụ: đăng nhập thành công cho biết người gửi được xác thực là alice. Nó chưa trả lời alice có được tải A-C02 hay không.

### 3.2. Cấp quyền cho một hành động

Đối với yêu cầu tải A-C02, hệ thống còn xét vai trò và phòng của alice, chủ sở hữu và nhãn của tài liệu, thiết bị, thời hạn cùng các trạng thái liên quan.

A-C02 là Mật, thuộc anna. alice là nhân viên cùng phòng nhưng không sở hữu tài liệu, nên B1 từ chối. Trưởng phòng adam cùng phòng có thể được tải khi các điều kiện khác hợp lệ.

### 3.3. Ghi nhận để kiểm toán

Sau đó, audit ghi lại yêu cầu, quyết định và lý do. Request ID liên kết phản hồi với sự kiện nhật ký.

Ba việc này phục vụ ba câu hỏi khác nhau:

| Câu hỏi | Cơ chế trả lời |
|---|---|
| Ai gửi yêu cầu? | Xác thực danh tính |
| Có được làm hành động này với tài liệu này ở thời điểm này không? | Cấp quyền |
| Hệ thống đã xử lý yêu cầu ra sao? | Audit và bằng chứng |

### 3.4. Trình duyệt, máy chủ và API

Trình duyệt hiển thị biểu mẫu; máy chủ xử lý dữ liệu và kiểm tra quyền. API là cách các thành phần gửi yêu cầu có cấu trúc cho nhau. Chẳng hạn, tải tài liệu là gửi yêu cầu tới một địa chỉ API, thay vì chỉ đọc một dòng đang hiển thị trên trang.

HTTP mô tả cách yêu cầu và phản hồi được trao đổi. GET thường dùng để đọc, POST để tạo hoặc thực hiện một thao tác, PUT để cập nhật. Mã 200 cho biết yêu cầu thành công; 401 là lỗi xác thực; 403 là không được phép; 503 là chức năng hoặc dịch vụ cần thiết chưa sẵn sàng. Cần đọc cả mã trạng thái và lý do cụ thể.

Giao diện có thể kiểm tra đầu vào để người dùng dễ sửa, nhưng máy chủ vẫn phải kiểm tra lại. Việc sửa HTML hoặc tự gửi HTTP không được tạo ra quyền mới.

### 3.5. RBAC, ABAC và Zero Trust

RBAC là phân quyền theo vai trò. Ví dụ, kiểm toán có chức năng đọc nhật ký. ABAC là xét thêm thuộc tính của người, tài nguyên, hành động và ngữ cảnh. Ví dụ, nhân viên chỉ tải tài liệu Mật khi cùng phòng và là chủ sở hữu; trưởng phòng tải Hạn chế còn cần grant hợp lệ.

Chính sách B1 phối hợp vai trò và các thuộc tính. B0 là đối chứng đã được nhóm giản lược, không đại diện cho mọi thiết kế RBAC; một hệ thống RBAC thực tế vẫn có thể kiểm tra quyền mới tại máy chủ.

Zero Trust là nguyên tắc tổ chức bảo vệ: không tự cấp quyền chỉ vì một người đã ở mạng nội bộ hoặc đã đăng nhập. Yêu cầu phải có đủ bằng chứng phù hợp trước khi xử lý. Trong bài, ba nguyên tắc được cụ thể hóa là xác minh rõ ràng, quyền tối thiểu và giả định có xâm nhập. Phần 4 cho thấy chúng được triển khai qua thành phần nào; phần 14 nêu các bảo đảm nguyên mẫu chưa có.

## 4. Một yêu cầu tải tài liệu đi qua đâu?

Xét alice yêu cầu tải A-C02, sử dụng chứng thư đúng người và các dịch vụ đang sẵn sàng.

| Bước | Thành phần thực hiện | Việc diễn ra |
|---|---|---|
| 1 | Thành phần khách của demo | Gửi yêu cầu tải với JWT và chứng thư client |
| 2 | NGINX gateway | Xác minh chứng thư trong kết nối mTLS, chuyển yêu cầu và thông tin đã xác minh tới API |
| 3 | FastAPI | Kiểm tra token và ánh xạ danh tính; đọc quyền, thiết bị, tài liệu và trạng thái từ nguồn máy chủ |
| 4 | OPA/Rego | Đánh giá bộ quy tắc với các thuộc tính được cung cấp |
| 5 | FastAPI | Kiểm tra kết quả và điều kiện bắt buộc; thực thi hoặc dừng thao tác |
| 6 | PostgreSQL và audit | Ghi dấu vết thích hợp; phản hồi có Request ID để đối chiếu |

Trong trường hợp này, điều kiện chủ sở hữu/nhãn không đạt. B1 trả `403 OWNER_OR_LABEL`; không giải mã rồi gửi nội dung A-C02 cho alice.

Đổi người thành adam, nếu quyền, thiết bị và tài liệu hợp lệ, yêu cầu có thể được cho phép. API lúc đó lấy bản mã, gọi OpenBao Transit để giải mã, kiểm tra tính toàn vẹn, ghi audit bắt buộc và chuẩn bị phản hồi chứa bản rõ.

Điểm cần chú ý là API lấy nhãn và chủ sở hữu đã lưu từ cơ sở dữ liệu. Người gửi không thể tự ghi header rằng mình có quyền hoặc tài liệu là Nội bộ để thay thế các thuộc tính này. Lúc tạo tài liệu, nhãn người dùng chọn là đầu vào đề xuất; máy chủ vẫn kiểm tra trước khi lưu.

Sơ đồ đầy đủ và các miền tin cậy nằm trong [kiến trúc](architecture.md).

## 5. Công nghệ nào đảm nhiệm việc gì?

Không cần nhớ tên tất cả thư viện trước khi hiểu hệ thống. Có thể đọc stack theo công việc:

| Công nghệ | Công việc trong nguyên mẫu | Không nên hiểu thành |
|---|---|---|
| HTML/CSS/JavaScript | Hiển thị biểu mẫu, lựa chọn và phản hồi trên web | Nơi quyết định quyền cuối cùng chỉ bằng ẩn/hiện nút |
| Python, FastAPI, Uvicorn | Xử lý API và công cụ điều khiển demo | Chỉ là giao diện danh sách tài liệu |
| Keycloak | Cung cấp danh tính, đăng nhập OIDC và token có chữ ký | Cấp sẵn mọi quyền đọc tài liệu cho người đăng nhập |
| JWT | Mang thông tin xác thực và các claim cần thiết | Một phiếu bảo đảm người dùng giữ mọi quyền tới lúc hết hạn |
| NGINX, TLS và mTLS | Kiểm soát đường vào, bảo vệ kênh và xác minh chứng thư client | Tự quyết định được người này có quyền với tài liệu nào |
| OPA và Rego | Đánh giá quy tắc chính sách | Toàn bộ kiến trúc Zero Trust hoặc toàn bộ PDP |
| PostgreSQL | Lưu quyền hiện tại, metadata, bản mã, phê duyệt, grant và audit | Chỉ chứa danh sách tên tệp |
| OpenBao Transit | Cung cấp chức năng mã hóa/giải mã bằng khóa được quản lý | Cơ sở dữ liệu tài liệu hoặc hệ thống đăng nhập |
| Docker và Compose trong WSL | Chạy, nối mạng và quản lý các dịch vụ cục bộ | Bản thân một container đã đủ làm dữ liệu an toàn |
| restic | Lưu repository sao lưu mã hóa | Công cụ tự bảo đảm mọi trạng thái sau phục hồi đều đúng |

Có tám dịch vụ Compose vì API B1 và API B0 chạy riêng. restic là công cụ phục vụ sao lưu, không phải dịch vụ thứ chín.

Bộ phiên bản được ghim và những phiên bản đã quan sát nằm trong [danh mục phần mềm](software-inventory.md). Ngày sửa tài liệu không đồng nghĩa mọi thành phần đã được nâng lên phiên bản mới nhất.

### PDP và PEP cần hiểu đến mức nào?

- PDP là chức năng ra quyết định chính sách.
- PEP là chức năng thực thi quyết định tại nơi xử lý yêu cầu.
- OPA đánh giá quy tắc Rego. FastAPI thu thập thuộc tính, xác minh phản hồi, kiểm tra thời hạn/giao dịch và thực thi.

Vì vậy, câu nói ngắn API hỏi OPA rồi cho phép hoặc chặn là cách mô tả một đoạn luồng. Để hiểu kiến trúc phải xem thêm danh tính đến từ đâu, thuộc tính có đáng tin không, có đường bỏ qua API không và điều gì xảy ra khi thành phần lỗi.

## 6. Chứng thư thiết bị khác token và tín hiệu thiết bị

TLS bảo vệ kênh và giúp phía khách kiểm tra máy chủ. Với mTLS, máy chủ còn yêu cầu phía khách chứng minh có khóa tương ứng với chứng thư client. CA là bên ký chứng thư được môi trường tin cậy; khóa riêng là bí mật dùng để chứng minh quyền sở hữu, không phải mật khẩu đăng nhập.

Trong nguyên mẫu, thành phần khách của console giữ và gửi chứng thư lab để dựng ca thử. Chọn chứng thư trên web không có nghĩa trình duyệt vừa đo được trạng thái an toàn của máy vật lý đang dùng. API đối chiếu số sê-ri với thiết bị/người trong registry, còn sức khỏe thiết bị dùng nguồn tín hiệu giả lập được mô tả bên dưới.

Ba thứ này bổ sung cho nhau:

| Thành phần | Điều nó hỗ trợ xác minh |
|---|---|
| Token JWT | Danh tính đã được nhà cung cấp định danh xác nhận |
| Chứng thư client | Phía gửi sở hữu khóa tương ứng với chứng thư; máy chủ đối chiếu chứng thư với tài khoản/thiết bị |
| Hồ sơ thiết bị hiện tại | Thiết bị có bị thu hồi, có tuân thủ, mức rủi ro và tín hiệu còn mới hay không |

Ví dụ, JWT là alice nhưng chứng thư thuộc anna thì yêu cầu bị chặn vì không khớp người. Ngược lại, chứng thư đúng alice vẫn không đủ nếu thiết bị bị đánh dấu rủi ro HIGH hoặc tín hiệu quá hạn.

Trong demo, chứng thư, xác minh chữ ký và mTLS được thực thi thật. Các giá trị compliant và risk là tín hiệu giả lập phía máy chủ để tạo tình huống. Hệ thống không đang quét máy của người dùng để phát hiện mã độc.

Tín hiệu có TTL 60 giây, bộ giả lập làm mới mỗi 20 giây khi được bật. Chu kỳ này khác thời hạn token và thời hạn grant.

## 7. B0 và B1 được dùng để chứng minh điều gì?

### 7.1. Tên gọi cần nhớ

Kiến trúc đề xuất của nhóm gồm nhiều thành phần đã trình bày. Trên web, B1 là nhãn ngắn cho cấu hình chính sách đề xuất đang được triển khai trong kiến trúc đó.

B0 là cấu hình đối chứng do nhóm dựng trên cùng hạ tầng. Nó giản lược một gói kiểm tra ở đường đọc để tạo mốc so sánh. B0 không phải phương án được đề xuất tốt hơn B1, cũng không phải một kiến trúc tham chiếu bên ngoài mà nhóm tìm ra lỗi.

### 7.2. Hai khác biệt phải tách rõ

| Nội dung | B0 đối chứng | B1 đề xuất |
|---|---|---|
| Vai trò/phòng ban khi đọc | Dùng thuộc tính đối chứng b0_role/b0_department trong JWT | Dùng giá trị hiện tại trong registry phía máy chủ |
| Trạng thái active hiện tại | Không dùng để thu hẹp đường đọc đối chứng | Tài khoản bị khóa bị chặn ở yêu cầu mới |
| Nhãn và chủ sở hữu | Không dùng để thu hẹp đường đọc | Có kiểm tra |
| Sức khỏe, rủi ro và độ mới tín hiệu | Được giản lược ở đường đọc | Có kiểm tra |
| Grant tải Hạn chế | Không bắt buộc ở đường đọc đối chứng | Bắt buộc với đối tượng phù hợp |
| JWT và liên kết chứng thư với người | Vẫn kiểm tra | Vẫn kiểm tra |
| Tài liệu tồn tại/chưa xóa và chưa hết hạn đọc | Vẫn kiểm tra | Vẫn kiểm tra |
| Mã hóa và audit | Cùng hạ tầng | Cùng hạ tầng |

Các thuộc tính đối chứng do Keycloak phát từ cấu hình lúc chuẩn bị môi trường hoặc tạo tài khoản. Chúng tách khỏi quyền hiện tại trong registry. Đổi vai trò/phòng ban ở màn hình Nhân viên cập nhật registry và hồ sơ của nguyên mẫu, không tự đồng bộ hai thuộc tính đối chứng này trong Keycloak. Vì vậy, không được hiểu rằng đăng nhập lại chắc chắn chụp quyền SQL mới vào B0.

Như vậy, B0/B1 khác cả nguồn thuộc tính dùng để xác định vai trò/phòng ban, lẫn các điều kiện bổ sung. Không nên diễn giải mọi khác biệt kết quả chỉ đến từ một điều kiện.

Các thao tác sửa thông tin tài liệu vẫn kiểm tra B1. Chọn B0 không tạo đường bỏ qua quyền sửa hoặc quản trị.

### 7.3. Case alice và anna

Với A-C02 của anna, alice cùng phòng A:

- B0 có thể cho phép vì các thuộc tính vai trò/phòng ban đối chứng trong token phù hợp.
- B1 từ chối vì tài liệu Mật không thuộc alice.
- JWT và chứng thư của alice vẫn hợp lệ trong cả hai yêu cầu.

Ca này cho thấy điều kiện owner/nhãn làm thay đổi quyết định đối với cùng một yêu cầu. Nó chưa chứng minh B1 vượt mọi hệ thống RBAC hoặc vượt hệ thống của Google/Microsoft.

### 7.4. Case bị khóa khi token còn hạn

Dùng tài liệu Nội bộ A-I01 mà alice vốn được phép đọc, để không bị lẫn với lỗi owner của A-C02:

1. alice đăng nhập và nhận JWT còn thời hạn.
2. alice gửi yêu cầu tải A-I01: được phép khi điều kiện ban đầu hợp lệ.
3. Quản trị an toàn khóa alice bằng thay đổi trạng thái active.
4. alice gửi yêu cầu mới bằng chính JWT còn hạn đó.
5. B1 nhận ra active hiện tại đã đổi và trả `403 INACTIVE`. Đường đọc B0 có thể vẫn cho phép theo cấu hình đối chứng.

Token vẫn xác thực được người gửi là alice. Điều bị thu hồi là quyền sử dụng hiện tại, không phải chữ ký token tự nhiên trở thành sai.

B1 kiểm tra active ở mỗi yêu cầu mới; không chờ token hết hạn hoặc chờ chu kỳ 20 giây làm mới tín hiệu thiết bị. Demo không chứng minh khả năng lấy lại những byte đã tải hợp lệ trước lúc bị khóa.

## 8. Metadata khác nội dung tài liệu

Metadata là thông tin mô tả: ID, tên, nhãn, chủ sở hữu, phiên bản hoặc mốc lưu giữ. Nội dung là các byte thực sự của tệp.

Với Hạn chế, trưởng phòng cùng phòng có thể được biết tài liệu tồn tại và đọc metadata, nhưng tải nội dung còn cần grant. Do đó có thể thấy tình huống:

| Cùng người và cùng tài liệu Hạn chế | Kết quả khi chưa có grant tải, các điều kiện khác hợp lệ |
|---|---|
| Xem metadata | Được phép với trưởng phòng cùng phòng |
| Tải nội dung | Bị chặn |
| Sửa tên/nhãn | Bị chặn vì API sửa yêu cầu quyền tải hiện tại |

Màn hình Tài liệu của console có thể hiển thị toàn bộ danh mục để người vận hành dựng bài thử. Điều đó không chứng minh API nghiệp vụ cho mọi nhân viên xem toàn bộ tài liệu. Cần gửi yêu cầu bằng đúng danh tính ở Tự thử yêu cầu để kiểm tra quyền nghiệp vụ.

## 9. Thêm Hạn chế, grant và sửa tài liệu

Có hai loại cấp phép khác nhau:

| Loại | Dùng vào việc gì? | Có dùng lại được không? |
|---|---|---|
| Phê duyệt tạo/nâng nhãn | Quản trị an toàn cho phép trưởng phòng tạo mới hoặc nâng lên Hạn chế, gắn người, phòng, tài liệu, phiên bản, mục đích và thời hạn | Chỉ sử dụng một lần khi giao dịch cơ sở dữ liệu được commit |
| Grant tải | Cho người nhận phù hợp sử dụng một tài liệu đã lưu, đúng phiên bản và hành động trong thời hạn | Có thể phục vụ nhiều yêu cầu khi còn hiệu lực |

Luồng thêm hiện tại: chọn trưởng phòng sở hữu, nhãn Hạn chế, quản trị an toàn phê duyệt và thời hạn. API kiểm tra phê duyệt rồi mã hóa, lưu trực tiếp nhãn Hạn chế, grant ban đầu và trạng thái đã dùng phê duyệt trong cùng giao dịch. Không lưu tạm bản Mật rồi mới nâng nhãn.

Nếu DB đã commit nhưng bước ghi ledger sau đó lỗi, phản hồi có thể báo lỗi trong khi tài liệu và trạng thái đã dùng phê duyệt đã được lưu. Cần làm mới và đối chiếu trước khi gửi lại; không hiểu dùng một lần là chỉ khi trình duyệt nhận HTTP thành công.

Người tạo sau đó dùng grant ban đầu để tải/sửa trong thời hạn, nhưng vẫn phải đáp ứng vai trò, phòng ban, thiết bị và điều kiện chung. Người phê duyệt khác người nhận; có tên trong ô chủ sở hữu không tự tạo quyền đối với nhãn Hạn chế.

Sửa hiện tại là sửa thông tin tài liệu, chưa thay thế nội dung tệp:

- API yêu cầu người sửa có quyền tải hiện tại theo B1.
- Đổi tên giữ phiên bản kiểm soát tài liệu.
- Nâng nhãn tăng phiên bản; nâng lên Hạn chế cần phê duyệt đúng mục đích upgrade và cấp grant cho phiên bản mới.
- Không được hạ nhãn qua API sửa.
- Quyền tải không cho thay đổi hạn lưu giữ hoặc bảo toàn.

Thu hồi hoặc hết hạn grant làm yêu cầu mới bị chặn nếu không còn grant phù hợp nào khác. Một người có thể có nhiều grant cho cùng tài liệu; thu hồi một dòng không mặc nhiên vô hiệu hóa những dòng còn hiệu lực.

## 10. Dữ liệu được bảo vệ sau khi cấp quyền ra sao?

### 10.1. Kênh truyền và dữ liệu lưu

TLS bảo vệ kênh truyền của đường vào. OpenBao Transit bảo vệ nội dung lưu trữ bằng mã hóa. Đây là hai phạm vi khác nhau.

PostgreSQL lưu bản mã tài liệu; OpenBao cung cấp thao tác mật mã theo quyền của API. Khóa không được đưa cho trình duyệt để người dùng tự giải mã. Token ứng dụng có phạm vi encrypt/decrypt, không mặc nhiên có quyền quản trị hoặc xuất khóa.

Một bản dump PostgreSQL riêng lẻ vì thế không tự cung cấp khả năng đọc toàn văn nếu thiếu KMS và quyền giải mã tương ứng. Tuy nhiên, API đang có quyền decrypt bị chiếm vẫn là rủi ro cần xét; mã hóa không làm mọi thành phần miễn nhiễm với xâm nhập.

Metadata phục vụ quyết định vẫn ở dạng rõ có kiểm soát. Không khẳng định toàn bộ mọi trường trong DB đã được mã hóa.

### 10.2. Hash và tính toàn vẹn

SHA-256 là mã băm để so sánh nội dung. Mã băm không thay thế mã hóa và không phải khóa giải mã.

Trong các ca kiểm chứng, nội dung tải hợp lệ được đối chiếu với hash chuẩn; phục hồi cũng cần xác minh nội dung. Việc nhìn thấy chuỗi giống bản mã riêng lẻ chưa đủ để kết luận toàn bộ cơ chế bảo vệ đã đúng.

### 10.3. Lưu giữ, bảo toàn và xóa

Thời hạn mẫu 180/90/30 ngày tương ứng Nội bộ/Mật/Hạn chế là giả định của bài toán. Hết hạn chặn đọc; không có nghĩa ngay lúc đó mọi bản sao tự biến mất.

Legal hold là trạng thái bảo toàn, ngăn xóa ngay cả khi đã qua lưu giữ. Xóa hợp lệ trong demo là xóa logic và tạo tombstone. Bản sao lưu cũ có thể còn bản mã; hệ thống không tuyên bố xóa tức thời mọi snapshot.

### 10.4. Sao lưu và phục hồi

Muốn phục hồi dữ liệu mã hóa phải có cặp dữ liệu và trạng thái khóa phù hợp. Nguyên mẫu sao lưu PostgreSQL cùng trạng thái OpenBao, giữ trong repository restic mã hóa.

Khi diễn tập, hệ thống dựng DB/KMS riêng, kiểm tra hash và đối chiếu ledger thay đổi mới hơn snapshot. Nếu một tài liệu đã bị xóa hoặc quyền đã bị thu hồi sau lúc chụp bản sao, không được coi việc giải nén thành công là đã phục hồi đúng trạng thái an toàn.

Ledger ghi thay đổi quyền và trạng thái; nó không chứa bản mã để tái tạo tài liệu được thêm sau snapshot. Những tài liệu mới đó không tự được phục hồi chỉ bằng đối chiếu ledger. Mã hiện hành còn loại bỏ phê duyệt tạo/nâng nhãn đang chờ trong bản phục hồi; hành vi này chưa được lượt T23 ngày 19/10 hay bộ bổ sung 39 ca kiểm chứng riêng.

Phục hồi trong demo là diễn tập cô lập, không thay thế hệ thống chính. Repository và dữ liệu cùng ổ E chưa bảo vệ trước mất toàn bộ ổ vật lý.

## 11. Tại sao còn cần audit và thử lỗi?

Một quyết định cho phép chỉ có nghĩa hệ thống đã cho yêu cầu đi tiếp tại điểm kiểm soát đó. Nó chưa chứng minh client đã nhận trọn tệp hoặc dữ liệu sẽ luôn an toàn sau khi được nhận.

Audit giúp trả lời ai yêu cầu gì, lúc nào, kết quả ra sao, lý do nào và dùng phiên bản chính sách nào. Request ID nối sự kiện với phản hồi. Không cần đưa mật khẩu, token hoặc nội dung tài liệu vào nhật ký để thực hiện việc này.

Cảnh báo mẫu được tạo khi cùng tài khoản có năm lần từ chối trong 60 giây. Cảnh báo hỗ trợ điều tra; không tự thực hiện việc thu hồi.

Thử lỗi kiểm tra hệ thống làm gì khi không đủ điều kiện bảo vệ:

| Tình huống với yêu cầu vốn hợp lệ | Điều cần kiểm tra |
|---|---|
| OPA không sẵn sàng | Không được biến lỗi thành cho phép |
| OpenBao không sẵn sàng | Không có bản rõ để trả từ đường giải mã bắt buộc |
| Audit bắt buộc ghi thất bại | Không trả bản rõ như một yêu cầu đã hoàn tất bình thường |
| Bản mã bị sửa | Không trả nội dung như thể toàn vẹn |

Đây là phần thể hiện sự phối hợp kiến trúc khi gặp lỗi. Một demo chỉ có ca cho phép thường chưa cho thấy các hành vi này.

## 12. Vậy hệ thống có phải chỉ là if/else không?

Quy tắc cấp quyền cuối cùng có thể được biểu diễn bằng các điều kiện logic. Viết bằng if/else hoặc Rego không tự quyết định chất lượng thiết kế.

Giá trị cần chứng minh là điều kiện đó được đặt đúng nơi và dùng dữ liệu đáng tin cậy:

| Câu hỏi kiến trúc | Nguyên mẫu xử lý thế nào? |
|---|---|
| Ai xác nhận người gửi? | Keycloak và xác minh JWT tại API |
| Thiết bị có đúng người không? | Chứng thư tại gateway và registry phía máy chủ |
| Quyền có bị cũ theo token không? | B1 đọc quyền hiện tại ở yêu cầu mới |
| Có thể bỏ qua nút trên web để gọi API trực tiếp không? | API vẫn thực thi kiểm tra; giao diện không phải điểm cấp quyền cuối |
| Chính sách do đâu đánh giá? | Quy tắc tập trung tại OPA; API kiểm tra và thực thi |
| Nếu quyết định hoặc phụ thuộc bị lỗi? | Không chuyển lỗi thành cho phép |
| Nội dung lưu có đọc trực tiếp được không? | Lưu bản mã, giải mã qua dịch vụ khóa có quyền giới hạn |
| Sau khi phục hồi có sống lại quyền cũ không? | Diễn tập đối chiếu trạng thái mới hơn snapshot |
| Làm sao giải thích kết quả? | Request ID, audit, trạng thái và bằng chứng kiểm tra |

Vì vậy, một tập điều kiện đơn giản vẫn có thể được hiện thực trong kiến trúc phù hợp. Ngược lại, dùng nhiều sản phẩm và container nhưng để lộ đường bỏ qua hoặc tin thuộc tính tự khai vẫn chưa đạt yêu cầu.

## 13. Nhóm kế thừa gì từ Google và Microsoft?

Google BeyondCorp cung cấp cách tổ chức danh tính, kiểm kê thiết bị và đường truy cập qua proxy. Microsoft Zero Trust cung cấp cách xem xét phối hợp các miền như danh tính, thiết bị, dữ liệu, ứng dụng, mạng và hạ tầng. NIST hỗ trợ thuật ngữ và mô hình chức năng; SABSA hỗ trợ truy vết từ yêu cầu tới kiểm soát.

Nhóm không triển khai lại toàn bộ hệ thống của hai nhà cung cấp. Phần cụ thể hóa gồm chính sách ba nhãn, quan hệ chủ sở hữu/phòng ban, grant theo phiên bản, phê duyệt tạo Hạn chế, phối hợp công nghệ và bộ kiểm chứng cho kho tài liệu.

B0 được nhóm tạo để làm đối chứng, không lấy từ Google hoặc Microsoft. Quan sát B0 cho phép trong khi B1 từ chối không chứng minh nhóm vừa sửa một nhược điểm của Google/Microsoft.

Cách trình bày phù hợp là: nhóm vận dụng các nguyên lý tham chiếu và kiểm chứng những lựa chọn của mình trong phạm vi nguyên mẫu. Xem phần [kế thừa và đóng góp của nhóm](ke_thua.md) để biết rõ nguồn nào cung cấp ý tưởng gì.

## 14. Phần nào chạy thật, phần nào giả lập?

| Nội dung | Mức hiện thực |
|---|---|
| Đăng nhập Keycloak, ký/xác minh JWT | Thực thi thật |
| TLS/mTLS và đối chiếu chứng thư | Thực thi thật với PKI của môi trường thử |
| OPA đánh giá quy tắc; API truy vấn và cập nhật DB | Thực thi thật |
| OpenBao thực hiện mã hóa/giải mã; PostgreSQL lưu bản mã, audit và grant | Thực thi thật |
| Dừng OPA/OpenBao trong bài thử | Dừng dịch vụ thật |
| Doanh nghiệp, tài khoản mẫu, nội dung hồ sơ | Dữ liệu tổng hợp |
| Tín hiệu compliant/risk của thiết bị | Giả lập có thời hạn phía máy chủ |
| Một số lỗi audit/registry/phản hồi PDP | Tiêm lỗi có kiểm soát |
| Lựa chọn nhiều danh tính/người duyệt trên console | Đặc quyền người vận hành để dựng và quan sát bài thử |

Thực thi thật không đồng nghĩa đã sẵn sàng sản xuất. Console có đặc quyền quản trị môi trường và chưa phải cổng nhiều người dùng không tin cậy. Phê duyệt bằng tài khoản được chọn là yêu cầu riêng có xác thực; chưa có quy trình hàng đợi duyệt độc lập giữa nhiều người.

Các giới hạn khác gồm: một số kết nối nội bộ chưa dùng mTLS; chưa thử sẵn sàng cao hoặc tải đồng thời; log chưa chống được quản trị viên đã chiếm host; chứng thư không xác nhận sức khỏe thiết bị thật; bản rõ đã cấp không thể thu hồi bằng đổi quyền. Không thể suy từ một tập ca đạt sang bảo đảm mọi tình huống đều đúng.

## 15. Đọc web và báo cáo theo thứ tự nào?

1. Hiểu dữ liệu và quyền: phần 2, 3, 8 của tài liệu này.
2. Theo một yêu cầu: phần 4, 5, 6; sau đó xem [architecture.md](architecture.md).
3. So sánh có kiểm soát: phần 7; giữ nguyên người, tài liệu và thiết bị khi chỉ đổi B0/B1.
4. Thử cập nhật quyền: thêm Hạn chế, tải/sửa, thu hồi rồi thử lại theo [hướng dẫn nhanh](huong_dan_nhanh.md).
5. Đối chiếu bằng chứng tại [kết quả kiểm chứng](ket_qua_kiem_chung.md). Mỗi số kiểm tra thuộc một lượt và phạm vi cụ thể; không cộng các lượt hoặc gọi kết quả cũ là kết quả vừa chạy.
6. Dùng [mục lục tài liệu](muc_luc.md) để tìm quy chuẩn dữ liệu, phiên bản công nghệ và hướng dẫn sâu hơn.

Nếu cần trình bày thật ngắn: nhóm thiết kế và triển khai một kho tài liệu có kiểm tra quyền ở từng yêu cầu, kết hợp danh tính, thiết bị, dữ liệu và vận hành; dùng dữ liệu tổng hợp để kiểm chứng cả ca hợp lệ, bị chặn và lỗi. B0 là mốc đối chứng giản lược, B1 là cấu hình đề xuất của nguyên mẫu.

## 16. Nên đọc nguồn chính thức nào?

Không cần đọc toàn bộ tài liệu công nghệ trước khi hiểu bài. Dùng bảng dưới để đọc đúng mục cần tra. NIST, bài BeyondCorp và RFC là nguồn nền tảng; tài liệu công nghệ được đối chiếu trực tuyến ngày 25/10/2026. Phiên bản triển khai cụ thể vẫn phải lấy từ manifest của dự án, không suy từ giao diện trang tài liệu.

| Chủ đề | Nguồn và phần nên đọc | Liên hệ với bài |
|---|---|---|
| Zero Trust và chức năng quyết định/thực thi | [NIST SP 800-207](https://csrc.nist.gov/pubs/sp/800/207/final), nguyên lý và logical components | Hiểu vì sao danh tính, nguồn thuộc tính và điểm thực thi phải phối hợp |
| Cấu trúc BeyondCorp | [Ward và Beyer, BeyondCorp](https://www.usenix.org/system/files/login/articles/login_dec14_02_ward.pdf), Major Components, Access Control Engine | Đối chiếu người dùng, kiểm kê thiết bị, chứng thư, proxy và quyết định từng yêu cầu |
| Các miền bảo vệ | [Microsoft Zero Trust adoption framework](https://learn.microsoft.com/en-us/security/zero-trust/adopt/zero-trust-adoption-overview), Principles và Functional areas | Hiểu cách rà soát yêu cầu bảo vệ và điều chỉnh triển khai theo bài toán |
| Token và claim | [RFC 7519](https://www.rfc-editor.org/rfc/rfc7519), Claims; [Keycloak OIDC](https://www.keycloak.org/securing-apps/oidc-layers), token/certificate endpoints | Hiểu chữ ký, danh tính, thời hạn và khóa dùng kiểm tra token |
| Thuộc tính đưa vào quyết định | [OPA External Data](https://www.openpolicyagent.org/docs/external-data), JWT và Overload input | Hiểu khác biệt dữ liệu trong token và dữ liệu máy chủ cung cấp cho chính sách |
| Chứng thư client | [NGINX SSL module](https://nginx.org/en/docs/http/ngx_http_ssl_module.html), ssl_verify_client | Hiểu việc xác minh chứng thư ở cổng vào |
| Mã hóa tách khỏi nơi lưu bản mã | [OpenBao Transit](https://openbao.org/docs/secrets/transit/) | Phân biệt dịch vụ thao tác mật mã với cơ sở dữ liệu lưu tài liệu |
| Container, mạng và dữ liệu bền vững | [Docker Compose application model](https://docs.docker.com/compose/intro/compose-application-model/) | Hiểu service, network, volume và cấu hình triển khai |

Muốn đối chiếu với mã của chính bài: bắt đầu ở [security.py](../app/security.py) và [bmdl.rego](../policies/bmdl.rego), rồi xem [main.py](../app/main.py), [mô hình dữ liệu](../app/db.py), [gateway](../infra/nginx.conf) và [cấu hình dịch vụ](../compose.yaml). Cách phân vai nguồn tham khảo trong tài liệu này là phân tích của nhóm, không phải xác nhận từ nhà cung cấp về nguyên mẫu.
