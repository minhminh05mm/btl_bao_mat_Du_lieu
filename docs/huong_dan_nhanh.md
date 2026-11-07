# Hướng dẫn nhanh

Web dùng để thử quyền với tài liệu và quan sát kho xử lý thế nào khi tài khoản hoặc thiết bị thay đổi. Điểm chính cần xem là gửi lại yêu cầu bằng phiên đang dùng sau khi tài khoản đã bị khóa.

## Bật và tắt web

Mở PowerShell:

```powershell
Set-Location -LiteralPath 'E:\btl_bao_mat_Du_lieu'
powershell -ExecutionPolicy Bypass -File .\Start-Demo.ps1 -OpenBrowser
```

Mở [localhost:8088](http://localhost:8088). Lần đầu cần WSL 2, Internet, tối thiểu 10 GB trống trên ổ C và 8 GB trên ổ E. Chương trình tự kiểm tra dung lượng. Các công cụ sử dụng miễn phí, không cần tài khoản dịch vụ đám mây.

Khi không sử dụng:

```powershell
.\Stop-Demo.ps1
```

Lệnh dừng giữ tài liệu, tài khoản và kết quả. Lần khởi động sau cần tạo phiên truy cập mới.

## Các mục trên web

| Mục | Dùng để làm gì? |
|---|---|
| Thử truy cập | Chọn người, thiết bị, cách kiểm tra và tài liệu; tạo phiên rồi gửi yêu cầu |
| Tài khoản và thiết bị | Khóa, mở khóa tài khoản đối tác hoặc thay đổi tình trạng thiết bị |
| Kết quả kiểm tra | Xem kết quả đã lưu hoặc chạy các tình huống tự động |
| Quản lý tài liệu | Thêm tài liệu, chọn nhãn, sửa thông tin và cấp quyền tài liệu Hạn chế |
| Nhân viên và quyền | Thêm nhân viên, đặt vai trò, phòng ban và quyền tham gia kho |

Tự động làm mới chỉ cập nhật màn hình. Bỏ chọn mục này không dừng việc kiểm tra lại trạng thái ở máy chủ. Làm mới trạng thái lấy thông tin hiện tại để hiển thị.

## Tải một tài liệu

1. Trong Thử truy cập, chọn Nhân viên đối tác · Kinh doanh.
2. Giữ Thiết bị đã đăng ký của tài khoản đang chọn.
3. Chọn Thu hồi theo thông báo và tự kiểm tra lại.
4. Nhấn Đăng nhập và tạo phiên, chờ thông báo thành công.
5. Chọn Quy trình tiếp nhận yêu cầu báo giá · Nội bộ và thao tác Tải tài liệu.
6. Nhấn Gửi yêu cầu bằng phiên hiện tại.
7. Nếu kết quả là Được tải tài liệu, nhấn Lưu tài liệu về máy để nhận tệp.

Mỗi cách kiểm tra có phiên riêng. Đổi cách kiểm tra không tự tạo phiên mới. Hệ thống cần cả trạng thái tài khoản, thiết bị và quyền với tài liệu phù hợp.

## Ba cách kiểm tra khác nhau thế nào?

| Cách kiểm tra | Khi nào kho biết tài khoản đã bị khóa? |
|---|---|
| Kiểm tra khi đăng nhập | Kiểm tra lúc tạo phiên; phiên cũ có thể còn dùng được đến khi hết hạn |
| Thu hồi theo thông báo | Nhận thông báo khóa thì thu hồi phiên; có thể bỏ lỡ thay đổi nếu thông báo bị mất |
| Thu hồi theo thông báo và tự kiểm tra lại | Nhận thông báo và chủ động hỏi lại; nếu thông tin cũ hết hạn mà chưa xác nhận lại được thì dừng yêu cầu |

Cả ba dùng cùng quy tắc truy cập tài liệu. Giữ nguyên người, thiết bị và tài liệu khi so sánh.

## Thử khóa tài khoản khi phiên còn hạn

1. Khi tài khoản còn hoạt động, tạo phiên và tải thành công ở cả ba cách kiểm tra.
2. Mở Tài khoản và thiết bị. Chọn Người thực hiện là Quản trị đối tác · An toàn thông tin và Tài khoản cần thay đổi là Nhân viên đối tác.
3. Nhấn Khóa tài khoản; chờ kho ghi nhận thu hồi.
4. Quay lại Thử truy cập, lần lượt chọn từng cách rồi nhấn Gửi yêu cầu bằng phiên hiện tại. Giữ nguyên phiên, không đăng nhập lại.
5. Cách chỉ kiểm tra khi đăng nhập vẫn có thể tải. Hai cách nhận thông báo dừng yêu cầu.
6. Mở khóa tài khoản. Với phiên đã thu hồi, gửi lại vẫn bị chặn. Đăng nhập mới để tiếp tục.

Khóa tài khoản không xóa tài liệu. Tài khoản đối tác bị khóa và quyền tham gia kho bị tắt là hai trạng thái khác nhau, được chỉnh ở hai mục tương ứng.

## Thử mất thông báo

1. Giữ tài khoản hoạt động, thiết bị dùng được và khôi phục thiết lập mặc định.
2. Tạo phiên mới ở Thu hồi theo thông báo và Thu hồi theo thông báo và tự kiểm tra lại.
3. Trong phần Thử khi mất thông báo hoặc mất kết nối, bật Làm mất các thông báo mới, nhấn Áp dụng tình huống thử.
4. Khóa tài khoản. Chờ kho hỏi lại trạng thái rồi gửi bằng hai phiên cũ.
5. Cách chỉ chờ thông báo có thể tiếp tục tải; cách tự kiểm tra lại phát hiện tài khoản đã khóa và thu hồi phiên.
6. Nhấn Khôi phục mặc định và mở khóa tài khoản khi kết thúc.

## Thử bên quản lý tài khoản không phản hồi

1. Tạo phiên có tự kiểm tra lại khi mọi dịch vụ hoạt động bình thường.
2. Bật Giả lập bên quản lý tài khoản không phản hồi và nhấn Áp dụng tình huống thử.
3. Chờ quá thời gian ở ô Thông tin đã kiểm tra dùng được bao lâu (giây), sau đó gửi bằng phiên hiện tại.
4. Kho tạm dừng yêu cầu vì chưa xác nhận lại được trạng thái.
5. Nhấn Khôi phục mặc định. Tạo phiên mới nếu phiên trước đã bị thu hồi hoặc hết hạn.

Mặc định thông tin đã kiểm tra được dùng tối đa 5 giây, kho hỏi lại mỗi 5 giây. Đây là cấu hình thử nghiệm, không phải cam kết chặn trong đúng 5 giây dưới mọi điều kiện.

## Thêm nhân viên và tài liệu để tự thử

Trong Nhân viên và quyền, chọn Thêm nhân viên. Nhập họ tên, tên đăng nhập chưa dùng, mật khẩu, bên quản lý tài khoản, vai trò trong kho và phòng ban. Tài khoản đối tác được đăng ký thêm ở dịch vụ quản lý tài khoản; nhân viên do kho tự quản lý không được thêm vào cơ sở dữ liệu của đối tác. Ô Cho phép truy cập kho tài liệu điều khiển quyền tham gia kho.

Trong Quản lý tài liệu, chọn Thêm tài liệu. Dùng tệp TXT, CSV hoặc PDF tối đa 1 MiB; chọn chủ sở hữu và nhãn. Tên để trống sẽ dùng tên tệp. Với Hạn chế, chọn trưởng phòng làm người thực hiện, quản trị an toàn làm người phê duyệt và thời hạn quyền tải, sửa. Phê duyệt và quyền ban đầu được lưu cùng tài liệu.

Sửa thông tin tài liệu cần quyền tải nội dung hiện tại. Với Hạn chế, quyền phải còn hạn và đúng phiên bản. Chỉ xem được thông tin tài liệu chưa đủ để sửa hoặc tải. Nếu có nhiều quyền còn hạn phù hợp, thu hồi một dòng chưa làm mất quyền từ các dòng khác.

## Đọc nhật ký, cảnh báo và yêu cầu tùy chỉnh

- Chọn Kiểm toán kho hoặc vai trò kiểm toán phù hợp để Đọc nhật ký.
- Chọn Quản trị kho hoặc vai trò quản trị an toàn phù hợp để Đọc cảnh báo; kiểm toán cũng có quyền đọc cảnh báo theo quy tắc hiện tại.
- Tạo phiên trước khi gửi yêu cầu. Chức năng này không yêu cầu chọn một tài liệu cụ thể.
- Gửi yêu cầu kỹ thuật tùy chỉnh dùng cùng tài khoản, thiết bị, cách kiểm tra và phiên hiện tại. Chỉ dùng khi cần gọi một địa chỉ API cụ thể.

Nếu cần đăng nhập Keycloak thủ công, dùng tài khoản thực trong danh sách và mật khẩu đã tạo trên máy; có thể xem qua `Show-Credentials.ps1`. Tài khoản quản trị dịch vụ đăng nhập khác với các tài khoản nghiệp vụ của kho.

## Kiểm tra tự động

Chọn Kết quả kiểm tra rồi nhấn Chạy tất cả tình huống. Giữ nguyên môi trường trong lúc chạy. Bộ kiểm tra gửi yêu cầu thật, thay đổi trạng thái mẫu, thử lỗi dịch vụ và khôi phục thiết lập khi kết thúc. Các tài liệu thử được giữ lại; các phiên do bộ kiểm tra tạo được thu hồi.

Tải bằng chứng kỹ thuật hoặc mở `results/federation-latest.html`. JSON và CSV tương ứng nằm cùng thư mục. [Kết quả đã lưu](ket_qua_kiem_chung.md) giải thích số liệu dùng trong báo cáo.

## Nếu gặp lỗi, sửa ở đâu?

| Thông báo hoặc hiện tượng | Cần kiểm tra |
|---|---|
| Chưa có phiên, hết hạn hoặc dịch vụ vừa khởi động lại | Đăng nhập và tạo phiên mới |
| Tài khoản đã bị khóa | Mở khóa ở Tài khoản và thiết bị, sau đó tạo phiên mới |
| Phiên cũ đã bị thu hồi | Giữ tài khoản, thiết bị hợp lệ rồi đăng nhập lại |
| Thiết bị không khớp hoặc không đủ điều kiện | Chọn đúng thiết bị; khôi phục tình trạng thiết bị ở Tài khoản và thiết bị |
| Chưa có quyền với phòng ban, vai trò hoặc tài liệu | Kiểm tra Nhân viên và quyền, nhãn, chủ sở hữu và quyền Hạn chế |
| Thêm Hạn chế bị chặn | Kiểm tra trưởng phòng, phòng ban, người phê duyệt và thời hạn |
| Tệp hoặc tên không hợp lệ | Sửa trường được đánh dấu trong biểu mẫu |
| Chưa xác nhận được trạng thái hoặc dịch vụ chưa sẵn sàng | Khôi phục thiết lập thử; kiểm tra các dịch vụ đã chạy |
| Tài khoản mới chưa đăng ký xong | Chạy lại `Start-Demo.ps1` để hoàn tất đăng ký |
| Lỗi sau khi lưu thay đổi | Làm mới danh sách và đối chiếu trước khi gửi lại, vì một phần ghi nhận có thể đã hoàn tất |

Mở Xem chi tiết kỹ thuật và mã yêu cầu khi cần đối chiếu phản hồi với nhật ký. Trang điều khiển dành cho người vận hành tin cậy trên máy cá nhân; danh mục nhìn thấy tại đây không chứng minh mọi tài khoản đều có quyền đọc nội dung.
