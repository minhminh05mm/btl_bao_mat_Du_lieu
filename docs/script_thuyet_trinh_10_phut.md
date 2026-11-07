# Script thuyết trình 10 phút theo PowerPoint 8 slide

Chủ đề: Kiến trúc Zero Trust cho kho tài liệu và cơ chế thu hồi quyền truy cập khi tài khoản bị khóa.

Sử dụng cùng [PowerPoint hiện tại](../trinh_chieu/Slide_ThuyetTrinh_BMDL_Nhom03_PhongCachSteam.pptx) và giao diện web đã cập nhật. Chỉ đọc các đoạn lời nói. Các dòng *Thao tác* dành cho người trình bày. Thời gian đã bao gồm thao tác và chuyển slide.

## Lịch trình

| Slide | Nội dung | Thời gian |
|---|---|---|
| 1 | Bài toán thu hồi quyền truy cập | 0:00–0:45 |
| 2 | Tham chiếu Microsoft và Google | 0:45–2:00 |
| 3 | Kiến trúc và công nghệ sử dụng | 2:00–2:50 |
| 4 | Vai trò và phân loại tài liệu | 2:50–3:10 |
| 5 | Luồng xử lý một yêu cầu truy cập | 3:10–5:15 |
| 6 | So sánh ba cách kiểm tra trạng thái | 5:15–6:00 |
| 7 | Demo khóa tài khoản và thu hồi phiên | 6:00–8:30 |
| 8 | Kết quả kiểm tra và phạm vi áp dụng | 8:30–10:00 |

## Chuẩn bị trước khi trình bày

- Khởi động web theo [hướng dẫn nhanh](huong_dan_nhanh.md), rồi mở PowerPoint ở chế độ trình chiếu và mở sẵn web tại <http://localhost:8088>. Dùng sơ đồ ở slide 3 và slide 5 để giải thích, không cần mở Word trong lúc nói.
- Trong Tài khoản và thiết bị, chọn người thực hiện là Quản trị đối tác · An toàn thông tin. Chọn Nhân viên đối tác rồi mở khóa tài khoản và khôi phục thiết bị. Nhấn Khôi phục mặc định trong phần thử mất thông báo hoặc mất kết nối.
- Trong Thử truy cập, chọn Nhân viên đối tác · Kinh doanh, Thiết bị đã đăng ký của tài khoản đang chọn và tài liệu Quy trình tiếp nhận yêu cầu báo giá · Nội bộ. Chọn thao tác Tải tài liệu. Trình thử sử dụng tài khoản mẫu, không cần gõ mật khẩu.
- Để sẵn kết quả kiểm tra tự động đã chạy. Không chạy tất cả tình huống giữa lúc demo thủ công vì bộ kiểm tra có thay đổi trạng thái tài khoản mẫu.
- Slide 5: nhấp một lần để viền sáng chạy qua 10 bước. Chờ chạy xong rồi chỉ từng ô khi giải thích, tránh nhấp thêm làm chuyển slide. Hiệu ứng minh họa luồng xử lý, không gửi yêu cầu thật hoặc đo thời gian từng bước.
- Slide 7: nút Mở web demo mở trình duyệt. Kết thúc demo, quay lại PowerPoint và chuyển sang slide 8.
- Ba cách kiểm tra chỉ khác cách cập nhật trạng thái tài khoản và thiết bị. Cả ba dùng cùng quy tắc truy cập tài liệu, vì vậy cần giữ nguyên người dùng, thiết bị và tài liệu khi so sánh.

## Slide 1 — Bài toán thu hồi quyền truy cập (0:00–0:45)

Kính thưa thầy, bài trình bày tập trung vào tình huống một đơn vị quản lý tài khoản và thiết bị, còn một đơn vị khác quản lý kho tài liệu.

Nhân viên đã đăng nhập, có quyền với tài liệu và được kho cấp một phiên truy cập. Sau đó, tài khoản bị khóa ở bên quản lý tài khoản, nhưng phiên tại kho vẫn còn hạn. Nếu kho chỉ kiểm tra khi đăng nhập, người đó vẫn có thể dùng phiên cũ để tải tài liệu.

Bài toán cần giải quyết là làm cho kho nhận biết thay đổi này và dừng những yêu cầu tiếp theo. Đồng thời, mỗi bên vẫn giữ quyền quản lý riêng: một bên quản lý người và thiết bị, bên còn lại quản lý tài liệu.

## Slide 2 — Tham chiếu Microsoft và Google (0:45–2:00)

*Thao tác: Chỉ Microsoft bên trái, Google bên phải rồi dải đỏ phía dưới. Kết thúc phần này mới chuyển sang slide 3.*

Microsoft Zero Trust cung cấp khung bảo vệ trên sáu miền: danh tính, thiết bị, ứng dụng, dữ liệu, hạ tầng và mạng. Bài này sử dụng khung đó để xác định các trách nhiệm bảo vệ. Trong tình huống đặt ra, bên quản lý tài khoản chịu trách nhiệm về vòng đời tài khoản và tình trạng thiết bị, tương ứng với vai trò của Entra ID và Intune trong hệ sinh thái Microsoft.

Google BeyondCorp cung cấp tham chiếu cho cách truy cập ứng dụng qua cổng kiểm soát. Người dùng phải được xác minh cùng thiết bị, rồi ứng dụng tiếp tục kiểm tra quyền với dữ liệu. Việc đang ở trong mạng nội bộ không tự tạo ra quyền truy cập.

Trong kiến trúc này, bên quản lý tài khoản xác nhận người và thiết bị còn đủ điều kiện. Kho tài liệu quyết định người đó được tải tài liệu nào. Bộ điều phối nối hai trách nhiệm này, theo dõi phiên và xử lý thu hồi khi có thay đổi.

Phần được thiết kế và kiểm tra là cơ chế phối hợp giữa hai bên quản trị độc lập. Các tham chiếu giúp xác định trách nhiệm và cách kiểm soát truy cập. Kết quả thử nghiệm đánh giá cơ chế phối hợp đã triển khai trong nguyên mẫu.

## Slide 3 — Kiến trúc và công nghệ sử dụng (2:00–2:50)

*Thao tác: Chỉ hàng trên gồm người dùng, Keycloak và cổng truy cập. Sau đó chỉ ba khối bên dưới: bên quản lý tài khoản, bộ điều phối và kho tài liệu. Dải cuối slide liệt kê công nghệ, không cần đọc tất cả phiên bản.*

Ở hàng trên, Keycloak cung cấp chức năng đăng nhập. Cổng truy cập dùng NGINX xác minh thiết bị rồi chuyển thông tin đã kiểm tra vào hệ thống.

Ở hàng dưới, bên quản lý tài khoản theo dõi người dùng và thiết bị. Bộ điều phối theo dõi các phiên, nhận thông báo thay đổi và tự kiểm tra lại khi cần. Kho tài liệu kiểm tra quyền rồi mới cấp nội dung.

FastAPI xử lý yêu cầu, OPA đánh giá quy tắc truy cập, PostgreSQL lưu dữ liệu và OpenBao bảo vệ khóa mã hóa. Các thành phần có tài khoản cơ sở dữ liệu và khóa ký riêng theo trách nhiệm.

Nguyên mẫu chạy trên một máy và dùng chung dịch vụ đăng nhập. Các công cụ miễn phí mô phỏng trách nhiệm của hai bên, chưa kết nối trực tiếp dịch vụ đám mây Microsoft hoặc Google.

## Slide 4 — Vai trò và phân loại tài liệu (2:50–3:10)

*Thao tác: Chỉ bảng vai trò bên trái rồi bảng nhãn bên phải.*

RBAC xét vai trò của người dùng. ABAC xét thêm phòng ban, nhãn tài liệu và thời hạn. Người quản lý tài khoản không tự có quyền quản trị kho.

Tài liệu có ba nhãn: Nội bộ, Mật và Hạn chế. Với Hạn chế, người tải cần quyền truy cập có thời hạn được cấp qua phê duyệt.

## Slide 5 — Luồng xử lý một yêu cầu truy cập (3:10–5:15)

*Thao tác: Nhấp một lần để chạy hiệu ứng. Đọc đoạn giới thiệu khi viền sáng chạy, sau đó chỉ theo mũi tên: hàng trên từ trái sang phải, hàng dưới từ phải sang trái. Tên và số bước dưới đây trùng sơ đồ.*

Luồng gồm hai giai đoạn. Bốn bước đầu tạo phiên truy cập. Sáu bước sau kiểm tra mỗi yêu cầu tải bằng phiên đó.

Bước 1, đăng nhập. Người dùng đăng nhập qua Keycloak để hệ thống xác minh tài khoản.

Bước 2, kiểm tra thiết bị. Cổng xác minh chứng thư của thiết bị. Đây là thông tin xác nhận thiết bị đã đăng ký, người gửi không thể chỉ tự khai tên thiết bị để vượt qua kiểm tra.

Bước 3, ghép đúng người. Hệ thống kiểm tra tài khoản thuộc bên quản lý nào và thiết bị có gắn với đúng người đang đăng nhập hay không.

Bước 4, cấp phiên truy cập. Bộ điều phối xác minh thông tin trạng thái có chữ ký từ bên quản lý tài khoản. Khi tài khoản và thiết bị hợp lệ, bộ điều phối tạo phiên gắn với đúng người, thiết bị và thời hạn.

Từ đây, người dùng gửi yêu cầu tải bằng phiên đã cấp. Khi phiên bị thu hồi, hệ thống yêu cầu đăng nhập lại.

Bước 5, kiểm tra phiên. Kho kiểm tra phiên còn hạn, đúng thiết bị và chưa bị thu hồi. Với cách có tự kiểm tra lại, thông tin đã lưu quá hạn phải được xác nhận lại trước khi tiếp tục.

Bước 6, kiểm tra quyền. OPA xét vai trò, phòng ban, nhãn hiện tại và thời hạn. Tài liệu Hạn chế cần thêm quyền truy cập còn hạn, đúng người và đúng phiên bản tài liệu.

Bước 7, quyết định. Yêu cầu chỉ tiếp tục khi cả điều kiện phiên và quyền tài liệu đều đáp ứng. Nếu một điều kiện không đạt, kho dừng yêu cầu và nêu lý do.

Bước 8, chuẩn bị tài liệu. Kho lấy nội dung đã mã hóa, gọi OpenBao giải mã và kiểm tra nội dung có bị thay đổi hay không. Lúc này tệp vẫn chưa được gửi cho người dùng.

Bước 9, kiểm tra lần cuối. Hệ thống ghi nhật ký và kiểm tra lại phiên cùng các thời hạn trước khi hoàn tất.

Bước 10, trả kết quả. Hệ thống hoàn tất xử lý rồi mới gửi tệp. Nếu bị chặn ở bước trước, người dùng nhận lý do từ chối.

Như vậy, một lần đăng nhập thành công chưa đủ để tải mọi tài liệu. Kho tiếp tục kiểm tra từng yêu cầu trước khi trả nội dung.

## Slide 6 — So sánh ba cách kiểm tra trạng thái (5:15–6:00)

*Thao tác: Chỉ ba tên ở bên phải, sau đó chỉ các hàng tương ứng trong bảng bên trái. Chưa mở web.*

Nguyên mẫu cho phép so sánh ba cách kiểm tra.

Kiểm tra khi đăng nhập chỉ xác nhận trạng thái lúc tạo phiên. Nếu tài khoản bị khóa sau đó, phiên cũ có thể tiếp tục dùng đến khi hết hạn.

Thu hồi theo thông báo bổ sung thông báo có chữ ký. Kho nhận thông báo khóa thì thu hồi phiên, nhưng có thể bỏ lỡ thay đổi nếu thông báo bị mất.

Thu hồi theo thông báo và tự kiểm tra lại còn chủ động hỏi lại trạng thái. Cách này phát hiện thay đổi bị bỏ lỡ. Nếu không hỏi lại được khi thông tin đã lưu hết hạn, kho tạm dừng yêu cầu.

Quyền tài liệu giữ nguyên trong cả ba cách. Sự khác biệt trong bảng đến từ cách cập nhật trạng thái tài khoản và thiết bị.

## Slide 7 — Demo khóa tài khoản và thu hồi phiên (6:00–8:30)

*Thao tác: Chỉ ảnh Tài khoản đã bị khóa và ba thao tác bên phải, rồi nhấn Mở web demo. Thực hiện phần dưới trên web.*

### 6:00–6:35 — Tạo phiên và tải thành công

*Thao tác: Chọn Nhân viên đối tác · Kinh doanh, Thiết bị đã đăng ký của tài khoản đang chọn. Chọn Kiểm tra khi đăng nhập rồi nhấn Đăng nhập và tạo phiên. Chờ tạo phiên thành công, chọn Quy trình tiếp nhận yêu cầu báo giá · Nội bộ và Tải tài liệu, nhấn Gửi yêu cầu bằng phiên hiện tại. Lặp lại với Thu hồi theo thông báo và tự kiểm tra lại. Mỗi cách giữ một phiên riêng.*

Tài khoản và thiết bị hiện hợp lệ. Nhân viên có quyền với tài liệu nội bộ của phòng mình, nên cả hai cách đều hiện Được tải tài liệu. Nút Lưu tài liệu về máy cho phép nhận tệp thật.

### 6:35–7:25 — Khóa tài khoản và gửi lại bằng phiên cũ

*Thao tác: Trong Tài khoản và thiết bị, chọn Quản trị đối tác · An toàn thông tin làm người thực hiện, chọn Nhân viên đối tác làm tài khoản cần thay đổi, nhấn Khóa tài khoản. Chờ kho ghi nhận thu hồi. Quay lại Thử truy cập, lần lượt chọn hai cách vừa dùng rồi nhấn Gửi yêu cầu bằng phiên hiện tại. Không nhấn đăng nhập lại.*

Tài khoản vừa bị khóa, nhưng quyền tài liệu tại kho vẫn giữ nguyên. Với Kiểm tra khi đăng nhập, phiên cũ vẫn có thể tải vì kho chỉ kiểm tra trạng thái lúc tạo phiên.

Với Thu hồi theo thông báo và tự kiểm tra lại, kho đã thu hồi phiên. Yêu cầu tiếp theo hiện Tài khoản đã bị khóa và dừng trước bước cấp nội dung, như ảnh trên slide.

Điều quan sát được ở đây là tài khoản đã khóa không tiếp tục sử dụng phiên còn hạn để tải tài liệu.

### 7:25–7:55 — Mở khóa và kiểm tra phiên đã thu hồi

*Thao tác: Mở khóa Nhân viên đối tác. Giữ cách có tự kiểm tra lại, gửi bằng phiên cũ trước: web hiện Phiên cũ đã bị thu hồi. Sau đó nhấn Đăng nhập và tạo phiên, chờ thành công rồi gửi lại để tải được tài liệu.*

Mở khóa tài khoản không tự khôi phục phiên đã thu hồi. Người dùng cần đăng nhập lại để có phiên mới, dựa trên trạng thái hợp lệ hiện tại.

### 7:55–8:30 — Đối chiếu khi mất thông báo hoặc mất kết nối

*Thao tác: Mở Kết quả kiểm tra, chỉ hai hàng Thông báo khóa tài khoản bị mất và Bên quản lý tài khoản không phản hồi. Dùng kết quả đã có, không chạy lại tất cả tình huống. Sau đó quay về PowerPoint và chuyển sang slide 8.*

Khi mất thông báo khóa, cách chỉ chờ thông báo có thể giữ phiên cũ. Cách có tự kiểm tra lại phát hiện tài khoản đã khóa và thu hồi phiên.

Khi bên quản lý tài khoản không phản hồi, kho tạm dừng yêu cầu nếu thông tin đã lưu hết hạn. Kho cần xác nhận lại trạng thái trước khi cấp nội dung.

## Slide 8 — Kết quả kiểm tra và phạm vi áp dụng (8:30–10:00)

### 8:30–9:20 — Kết quả và ý nghĩa

*Thao tác: Chỉ ba kết quả 19/19, 42/42 và 31/31, rồi cột Bằng chứng ở bên phải.*

Lượt kiểm tra đưa vào báo cáo đạt 19 trên 19 tình huống sử dụng thực tế. Ngoài tải hợp lệ và khóa tài khoản, bộ kiểm tra còn thử thiết bị không khớp, thông tin trạng thái bị sửa, thông báo trùng hoặc đến sai thứ tự và việc tách quyền quản trị giữa hai bên.

Khi mở khóa tài khoản, phiên đã thu hồi vẫn bị từ chối. Khi khôi phục cơ sở dữ liệu phiên từ bản sao, hệ thống cũng vô hiệu hóa phiên cũ và yêu cầu đăng nhập lại.

Mỗi tình huống lưu phản hồi và thông tin liên quan để kiểm tra lại. Bên cạnh đó có 42 kiểm tra mã xử lý bằng Python và 31 kiểm tra quy tắc truy cập bằng Rego. Đây là ba tập kết quả riêng, không cộng thành số tình huống sử dụng thực tế.

Các kết quả xác nhận hành vi trong phạm vi đã thử nghiệm. Việc đánh giá chịu tải ở quy mô doanh nghiệp cần một nghiên cứu tiếp theo.

### 9:20–10:00 — Giới hạn và kết thúc

*Thao tác: Chỉ phần Phạm vi thử nghiệm ở cuối slide và giữ slide 8 đến hết.*

Nguyên mẫu chạy trên một máy, dùng chung dịch vụ đăng nhập và mô phỏng trạng thái thiết bị. Các dịch vụ đám mây Microsoft và Google chưa được kết nối trực tiếp.

Việc thu hồi có thời gian truyền và xử lý. Kho kiểm soát các yêu cầu tiếp theo sau khi ghi nhận thu hồi. Tệp đã tải về máy nằm ngoài phạm vi này.

Kết quả chính là cơ chế phối hợp giữa bên quản lý tài khoản và kho tài liệu. Thông báo giúp chuyển thay đổi tới kho. Việc tự kiểm tra lại giúp phát hiện thông báo bị mất và dừng yêu cầu khi trạng thái chưa thể xác nhận.

Xin cảm ơn thầy đã theo dõi.

## Khi cần rút thời gian hoặc gặp lỗi trình diễn

- Ưu tiên luồng trên slide 5 và thao tác khóa tài khoản trên slide 7. Nếu thiếu thời gian, nói ngắn phần mở khóa, rồi chuyển sang kết quả ở slide 8. Sau buổi trình bày cần mở lại tài khoản mẫu.
- Nếu phiên hết hạn trước khi demo, mở khóa tài khoản và tạo phiên mới. Sau khi khóa trong phép so sánh, giữ nguyên phiên và chỉ gửi lại yêu cầu.
- Nếu web không phản hồi ngoài dự kiến, kiểm tra dịch vụ trước. Một lỗi kết nối thông thường chưa đủ để kết luận hệ thống đã từ chối đúng quyền.
- Các ô bước trên web diễn giải phản hồi của hệ thống. Dùng phản hồi và nhật ký để đối chiếu, không xem hiệu ứng chạy là phép đo thời gian thực.
- Nếu được hỏi vì sao tham chiếu cả Microsoft và Google: bài toán giữ hai bên quản trị độc lập, có cách tổ chức truy cập khác nhau. Thiết kế cụ thể hóa cách hai bên trao đổi trạng thái và thu hồi phiên tại kho. Khả năng của từng hãng rộng hơn phần được mô phỏng trong bài này.

## Thao tác mở rộng khi được hỏi

Các phần dưới nằm ngoài lịch trình 10 phút.

- Mất thông báo: khôi phục mặc định, mở khóa tài khoản và khôi phục thiết bị. Tạo phiên mới cho Thu hồi theo thông báo và Thu hồi theo thông báo và tự kiểm tra lại. Bật Làm mất các thông báo mới rồi nhấn Áp dụng tình huống thử. Khóa tài khoản, chờ lượt kiểm tra tiếp theo rồi gửi bằng hai phiên cũ. Cách chỉ chờ thông báo có thể tiếp tục tải, cách tự kiểm tra lại bị từ chối. Kết thúc bằng Khôi phục mặc định và mở khóa tài khoản.
- Mất kết nối: tạo phiên khi trạng thái bình thường, bật Giả lập bên quản lý tài khoản không phản hồi rồi áp dụng. Chờ quá thời gian thông tin đã kiểm tra còn dùng được, gửi yêu cầu bằng phiên có tự kiểm tra lại. Kho tạm dừng yêu cầu vì chưa xác nhận lại được trạng thái. Kết thúc bằng Khôi phục mặc định.
- Tài liệu Hạn chế: quyền tải phải đúng người, tài liệu, phiên bản, thao tác và thời hạn. Quyền phê duyệt của quản trị an toàn không tự tạo quyền đọc mọi nội dung.
- Thêm tình huống: dùng Quản lý tài liệu để thêm tài liệu, đặt nhãn; dùng Nhân viên và quyền để thêm nhân viên hoặc thay đổi quyền trong kho. Các thao tác này bổ sung dữ liệu thử, còn luồng kiểm tra truy cập vẫn giữ nguyên.
