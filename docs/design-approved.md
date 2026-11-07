# Các quyết định thiết kế

## Mục tiêu

Thiết kế tập trung vào hiệu lực truy cập giữa hai bên quản lý độc lập. Khi bên quản lý tài khoản khóa người dùng hoặc thu hồi thiết bị, kho cần cập nhật quyết định với phiên đang còn hạn. Quyền với tài liệu vẫn do kho quản lý.

Microsoft Zero Trust cung cấp khung xác định trách nhiệm bảo vệ. BeyondCorp cung cấp tham chiếu cho cổng truy cập theo danh tính, thiết bị và việc thực thi tại ứng dụng. [Tài liệu tham chiếu](ke_thua.md) giải thích phần được áp dụng và cơ chế tích hợp.

## Lựa chọn và đánh đổi

| Quyết định | Lý do | Giới hạn hoặc đánh đổi |
|---|---|---|
| Tách dữ liệu tài khoản, phiên và tài liệu theo tài khoản dịch vụ | Giữ trách nhiệm quản trị và giới hạn việc đọc chéo dữ liệu | Các cơ sở dữ liệu vẫn dùng chung một máy chủ |
| Dùng cổng xác minh thiết bị và kiểm tra danh tính ở dịch vụ | Ràng buộc yêu cầu với người, thiết bị đã đăng ký | Chứng thư không tự chứng minh thiết bị an toàn |
| Cấp phiên riêng tại kho | Theo dõi và thu hồi hiệu lực truy cập độc lập với thông tin đăng nhập | Cần cơ chế cập nhật thay đổi vào phiên |
| Trạng thái, thông báo có chữ ký và liên kết đã đăng ký | Kiểm tra nguồn gửi, nội dung và đối tượng của thông tin | Chưa bảo vệ trước chính nguồn có thẩm quyền bị chiếm quyền |
| Thu hồi theo thông báo, bổ sung tự hỏi lại | Xử lý thay đổi bình thường và phát hiện thông báo bị mất | Có thời gian truyền, xử lý và lập lịch |
| Giới hạn thời gian dùng trạng thái đã kiểm tra | Ngăn tiếp tục dựa vào trạng thái cũ khi không xác nhận lại được | Người hợp lệ có thể tạm thời chưa truy cập được khi mất kết nối |
| Giữ cùng quyền tài liệu trong ba cách kiểm tra | So sánh tác dụng của cơ chế cập nhật trạng thái | Kết quả chỉ áp dụng cho cấu hình và tình huống đã thử |
| Đọc quyền, nhãn và thời hạn hiện tại tại kho | Thay đổi quyền có hiệu lực với yêu cầu tiếp theo | Không lấy lại tệp đã tải về máy |
| Quyền Hạn chế theo tài liệu, phiên bản và thời hạn | Giới hạn người nhận và phạm vi dùng nội dung nhạy cảm | Cần phân biệt phê duyệt tạo với quyền sử dụng tài liệu |
| Mã hóa bằng OpenBao, lưu bản mã trong PostgreSQL | Tách nơi lưu nội dung khỏi dịch vụ giữ khóa | Dịch vụ có quyền giải mã vẫn là thành phần cần bảo vệ |
| Ghi nhật ký bắt buộc và kiểm tra phiên trước khi hoàn tất | Có bằng chứng và giảm khoảng đua trước trả nội dung | Không loại bỏ mọi lịch xử lý đồng thời sau kiểm tra cuối |
| Vô hiệu hóa phiên cũ sau khởi động dịch vụ phiên | Tránh sử dụng lại phiên từ bản sao dữ liệu cũ | Người dùng cần đăng nhập lại sau khởi động |

## Phạm vi chức năng

Web có Thử truy cập, Tài khoản và thiết bị, Kết quả kiểm tra, Quản lý tài liệu, Nhân viên và quyền. Người vận hành có thể tự bổ sung dữ liệu, thay đổi quyền, tạo phiên và gửi yêu cầu bằng phiên đang dùng.

Tài liệu hỗ trợ TXT, CSV và PDF tối đa 1 MiB. Thêm Hạn chế cần trưởng phòng và quản trị an toàn phê duyệt. Sửa thông tin yêu cầu quyền tải hiện tại; nâng nhãn tăng phiên bản, không cho hạ nhãn.

Công cụ cục bộ có thể chọn nhiều danh tính để dựng bài thử. Quy trình phê duyệt chưa phải hàng đợi nhiều người dùng độc lập. Kết quả sử dụng được kiểm tra bằng phản hồi và nhật ký của API, không suy ra chỉ từ nút đang hiển thị.

## Cách kiểm tra lựa chọn

Ba cấu hình lần lượt là Kiểm tra khi đăng nhập, Thu hồi theo thông báo, Thu hồi theo thông báo và tự kiểm tra lại. Tình huống khóa tài khoản, mất thông báo và mất kết nối chỉ ra tác dụng của từng cơ chế. Các tình huống còn lại kiểm tra quyền tài liệu, chữ ký, thiết bị, đọc chéo dữ liệu, lỗi dịch vụ và khôi phục phiên.

Xem [ma trận kiểm tra](test-matrix.md), [kết quả](ket_qua_kiem_chung.md) và [quy tắc phối hợp](implementation-contract.md). Mỗi kết quả cần gắn với thời điểm, phiên bản mã và môi trường đã thực hiện.
