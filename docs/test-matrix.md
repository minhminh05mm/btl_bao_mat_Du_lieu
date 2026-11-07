# Ma trận kiểm tra

## Nguyên tắc so sánh

Tất cả yêu cầu tài liệu dùng cùng quy tắc quyền tại kho. Ba cách kiểm tra chỉ khác cơ chế cập nhật trạng thái tài khoản, thiết bị. Khi so sánh, giữ nguyên người dùng, thiết bị, tài liệu và quyền tại kho.

Bộ kiểm tra đối chiếu phản hồi, lý do, mã yêu cầu, nội dung tải hợp lệ và mã băm. Lỗi kết nối không rõ nguyên nhân không được tính như một lần từ chối đúng chính sách.

## Các tình huống

Tên tình huống thống nhất với phần Kết quả kiểm tra trên web. Số thứ tự chỉ giúp tra bảng; mã trong tệp kết quả kỹ thuật được giữ để đối chiếu mã nguồn.

| Thứ tự | Tình huống | Điều kiện đạt |
|---|---|---|
| 1 | Tải tài liệu khi mọi điều kiện đều hợp lệ | Cả ba cách kiểm tra trả đúng nội dung và mã băm |
| 2 | Tải tài liệu ngoài phạm vi được cấp | Cả ba đều chặn yêu cầu ngoài phòng ban được cấp |
| 3 | Khóa tài khoản khi phiên vẫn còn hạn | Cách chỉ kiểm tra khi đăng nhập còn dùng phiên; hai cách có nhận thông báo thu hồi phiên liên quan; ghi nhận thông tin đăng nhập và phiên chưa hết hạn |
| 4 | Mở khóa tài khoản sau khi thu hồi phiên | Phiên đã thu hồi vẫn bị chặn; đăng nhập mới khi đủ điều kiện thì tải được |
| 5 | Thu hồi thiết bị đã đăng ký | Hai cách có nhận thông báo thu hồi phiên gắn với đúng thiết bị; cách chỉ kiểm tra khi đăng nhập giữ phiên cũ |
| 6 | Thông báo khóa tài khoản bị mất | Cách chỉ chờ thông báo còn giữ phiên; cách tự kiểm tra lại phát hiện tài khoản khóa và thu hồi |
| 7 | Bên quản lý tài khoản không phản hồi | Cách tự kiểm tra lại dừng yêu cầu khi thông tin cũ hết hạn và chưa xác nhận lại được; không trả nội dung |
| 8 | Thông báo giả, trùng hoặc đến sai thứ tự | Thông báo giả bị loại; thông báo trùng không gây xử lý sai; thông báo cũ không khôi phục phiên đã thu hồi |
| 9 | Khôi phục cơ sở dữ liệu từ bản sao | Bản sao có phiên đang hoạt động; dịch vụ khởi động trên bản sao vô hiệu hóa phiên cũ và yêu cầu đăng nhập lại |
| 10 | Thử dùng thông tin đăng nhập hoặc thiết bị không khớp | Không thể thay bí mật phiên bằng thông tin đăng nhập đơn thuần, dùng chứng thư khác hoặc đổi cách kiểm tra để vượt liên kết phiên |
| 11 | Thử quản lý dữ liệu thuộc bên còn lại | Quản trị đối tác không tự quản trị kho; quản trị kho không tự quản trị tài khoản, thiết bị đối tác |
| 12 | Thử đọc cơ sở dữ liệu của bên còn lại | Tài khoản dịch vụ không kết nối được cơ sở dữ liệu ngoài phạm vi được cấp |
| 13 | Thử dùng thông tin thiết bị đã quá hạn | Ký lại thông tin không biến quan sát thiết bị cũ thành mới; không tạo phiên bằng quan sát quá hạn |
| 14 | Khóa rồi mở tài khoản giữa hai lần kiểm tra | Bộ đếm thay đổi giúp cách tự kiểm tra lại phát hiện và thu hồi phiên cũ dù tài khoản đã hoạt động trở lại |
| 15 | Kiểm tra thông tin có thuộc đúng yêu cầu hay không | Phản hồi phải khớp đúng người, bên quản lý, thiết bị và lượt hỏi trạng thái |
| 16 | Gặp lỗi khi kiểm tra quyền, ghi nhật ký hoặc giải mã | Dừng trước khi trả nội dung; phân biệt dịch vụ lỗi với từ chối do quyền nghiệp vụ |
| 17 | Thông tin trạng thái bị sửa trái phép | Không tạo phiên khi chữ ký không hợp lệ |
| 18 | Quản lý tài liệu Hạn chế, nhật ký và cảnh báo | Tạo, sửa, tải Hạn chế và đọc nhật ký, cảnh báo hoạt động bằng người có quyền phù hợp |
| 19 | Thêm nhân viên kho và đổi quyền đang dùng | Nhân viên kho không được thêm vào cơ sở dữ liệu đối tác; đổi phòng ban tác động đến yêu cầu tiếp theo bằng cùng phiên |

## Phạm vi kết luận

Các tình huống kiểm tra tính đúng đắn trong môi trường cục bộ với dữ liệu tổng hợp. Tình huống khôi phục chỉ kiểm tra cơ sở dữ liệu phiên và hành vi sau khởi động, không phải phục hồi đầy đủ hạ tầng của hai bên. Đây không phải bộ kiểm tra chịu tải doanh nghiệp hoặc phép đánh giá dịch vụ đám mây thật.

Xem [kết quả đã lưu](ket_qua_kiem_chung.md), [cách tái lập](reproduction.md) và [rà soát bằng chứng](verification-review.md).
