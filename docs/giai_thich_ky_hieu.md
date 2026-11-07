# Giải thích cách gọi và các trường trên web

Tài liệu dùng tên đầy đủ như giao diện hiện tại. Mã trong chi tiết kỹ thuật chỉ phục vụ đối chiếu nhật ký hoặc mã nguồn; không cần nhớ để sử dụng demo.

## Ba thành phần chính

| Tên | Hiểu đơn giản |
|---|---|
| Bên quản lý tài khoản | Nơi quyết định tài khoản đối tác còn hoạt động, thiết bị còn dùng được hay không |
| Bộ điều phối | Nơi theo dõi phiên tại kho và thu hồi khi nhận biết tài khoản hoặc thiết bị không còn hợp lệ |
| Kho tài liệu | Nơi quyết định người dùng được thực hiện thao tác nào với từng tài liệu |

## Ba cách kiểm tra

- Kiểm tra khi đăng nhập: kiểm tra trạng thái lúc tạo phiên. Thay đổi sau đó chưa tự làm mất hiệu lực phiên đang dùng.
- Thu hồi theo thông báo: nhận thông báo thay đổi thì thu hồi phiên liên quan. Nếu thông báo mất, kho có thể chưa biết thay đổi.
- Thu hồi theo thông báo và tự kiểm tra lại: ngoài nhận thông báo, kho còn hỏi lại trạng thái. Khi thông tin cũ hết hạn và chưa hỏi lại được, kho dừng yêu cầu.

Quy tắc truy cập tài liệu giống nhau trong cả ba cách. Các cách này là cấu hình của nguyên mẫu để kiểm tra cơ chế cập nhật trạng thái.

## Các trường trong Thử truy cập

| Trường hoặc nút | Tác dụng |
|---|---|
| Tài khoản | Người sẽ gửi yêu cầu vào kho |
| Thiết bị dùng để truy cập | Chứng thư thiết bị dùng khi kết nối; thường chọn thiết bị đã đăng ký của đúng tài khoản |
| Cách kiểm tra trạng thái tài khoản | Cách kho nhận biết thay đổi của tài khoản, thiết bị |
| Đăng nhập và tạo phiên | Xác minh trạng thái rồi tạo phiên mới cho tài khoản, thiết bị và cách kiểm tra đang chọn |
| Tài liệu | Tài liệu muốn xem hoặc tải; không cần chọn cho thao tác đọc nhật ký, cảnh báo |
| Thao tác | Việc muốn thực hiện với tài liệu hoặc hệ thống |
| Gửi yêu cầu bằng phiên hiện tại | Sử dụng lại phiên đã tạo, không đăng nhập lại |
| Xem chi tiết kỹ thuật và mã yêu cầu | Mở phản hồi gốc và mã dùng để tìm nhật ký |

## Các trường trong Tài khoản và thiết bị

Người thực hiện là người có quyền thay đổi trạng thái. Tài khoản cần thay đổi là đối tượng bị khóa hoặc mở khóa. Hai trường này có vai trò khác nhau; người quản lý không tự khóa tài khoản đang thực hiện thao tác.

Thiết bị cần thay đổi là thiết bị muốn thu hồi, khôi phục, đánh dấu rủi ro cao hoặc chưa đạt yêu cầu an toàn. Chứng thư xác nhận thiết bị trong kết nối; tình trạng an toàn do nguồn trạng thái cung cấp. Nguyên mẫu mô phỏng các tín hiệu an toàn, không tự quét máy tính đang mở trình duyệt.

Thông tin đã kiểm tra dùng được bao lâu giới hạn thời gian kho được dựa vào kết quả đã lưu. Kho hỏi lại sau mỗi bao nhiêu giây là khoảng cách lập lịch kiểm tra định kỳ. Hai tham số có mục đích khác nhau: tắt việc hỏi định kỳ không bỏ điều kiện kiểm tra lại khi thông tin hết hạn trên đường xử lý yêu cầu.

## Phiên, quyền tài liệu và phê duyệt

| Khái niệm | Ý nghĩa |
|---|---|
| Thông tin đăng nhập | Thông tin có chữ ký từ Keycloak để xác minh danh tính |
| Phiên truy cập tại kho | Quyền sử dụng một phiên gắn với người, thiết bị và thời hạn; kho có thể thu hồi riêng |
| Quyền với tài liệu | Vai trò và điều kiện quyết định người dùng được xem hoặc tải tài liệu nào |
| Quyền truy cập có thời hạn | Quyền riêng cho tài liệu Hạn chế, gắn người nhận, tài liệu, phiên bản, thao tác và thời hạn |
| Phê duyệt tạo hoặc nâng nhãn | Cho phép lưu tài liệu Hạn chế ở phiên bản xác định; chỉ sử dụng thành công một lần |
| Nhãn | Mức bảo vệ theo nội dung: Nội bộ, Mật hoặc Hạn chế |
| Thông tin tài liệu | Tên, nhãn, chủ sở hữu, phiên bản và thời hạn; khác với toàn bộ nội dung tệp |

Phiên hợp lệ chưa bảo đảm được tải mọi tài liệu. Quyền tài liệu hợp lệ cũng chưa đủ khi tài khoản hoặc thiết bị không đáp ứng điều kiện kiểm tra.

## Đọc kết quả

- Được tải tài liệu: yêu cầu đã hoàn tất; có thể lưu tệp về máy.
- Tài khoản đã bị khóa: bên quản lý tài khoản đã khóa người dùng; mở khóa rồi đăng nhập mới khi đủ điều kiện.
- Phiên cũ đã bị thu hồi: mở khóa tài khoản không làm phiên này dùng lại được.
- Chưa xác nhận được trạng thái: kho chưa kiểm tra lại được thông tin cần thiết, nên tạm dừng cấp nội dung.
- Chưa có quyền theo phòng ban, nhãn hoặc thời hạn: kiểm tra quyền ở kho và quyền riêng của tài liệu Hạn chế.

Tên và nhãn hiện tại giúp chọn tài liệu trên web. Mã tài liệu bên trong hệ thống là định danh để tra cứu, không thay thế các kiểm tra quyền. Với tài liệu mới, không cần đặt mã theo một mẫu ký tự để được cấp quyền.

Chi tiết thao tác nằm trong [hướng dẫn nhanh](huong_dan_nhanh.md). Muốn theo dõi toàn bộ đường đi của yêu cầu, xem [kiến trúc](architecture.md).
