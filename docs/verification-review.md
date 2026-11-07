# Rà soát bằng chứng và giới hạn kết luận

## Bằng chứng của kiến trúc hiện tại

[Lượt dùng trong báo cáo ngày 02/11/2026](../results/report-20261102/) ghi 19/19 tình huống sử dụng thực tế, 42/42 kiểm tra Python và 31/31 kiểm tra Rego đạt. Ba tập có phạm vi khác nhau. [Kết quả kiểm tra](ket_qua_kiem_chung.md) chỉ rõ tệp và cách đọc.

Các kết quả khẳng định hành vi của các tình huống đã thử với bộ mã và môi trường tương ứng. Sửa tài liệu, đổi tên trên giao diện hoặc khởi động lại dịch vụ không tự tạo bằng chứng kiểm tra mới cho mọi chức năng.

## Cần đối chiếu những gì?

| Nội dung | Bằng chứng cần xem |
|---|---|
| Yêu cầu hợp lệ | Nội dung trả về, mã băm và phản hồi thành công |
| Tài khoản bị khóa | Thời điểm thay đổi, thông báo hoặc lượt hỏi lại, phiên bị thu hồi và yêu cầu tiếp theo bị chặn |
| Mất thông báo | Thiết lập mất thông báo và kết quả khác nhau giữa cách chỉ chờ thông báo với cách tự kiểm tra lại |
| Bên quản lý không phản hồi | Thời điểm thông tin cũ hết hạn, lỗi xác nhận trạng thái và việc không trả nội dung |
| Đúng người, đúng thiết bị | Liên kết đã đăng ký và phản hồi khi dùng thông tin không khớp |
| Quyền riêng của hai bên | Phản hồi từ chối quản trị hoặc đọc cơ sở dữ liệu ngoài phạm vi |
| Phục hồi phiên | Bản sao cơ sở dữ liệu, mã băm, trạng thái trước và sau khởi động dịch vụ tạm |
| Quyền tài liệu Hạn chế | Phê duyệt, đúng người và phiên bản, thời hạn, kết quả tải hoặc sửa |

Lỗi mạng không rõ nguyên nhân không đủ chứng minh từ chối đúng quyền. Hiệu ứng sơ đồ chỉ diễn giải luồng; nhật ký và phản hồi thật là căn cứ kiểm tra. Thời gian chạy bộ kiểm tra không phải độ trễ từng thành phần.

## Ranh giới của công cụ điều khiển

Web trên máy cá nhân là công cụ của người vận hành tin cậy, có khả năng chọn danh tính, chuẩn bị dữ liệu và tạo tình huống lỗi. Việc công cụ nhìn thấy một danh mục hoặc có thể chuẩn bị một trạng thái không chứng minh nhân viên nghiệp vụ có cùng quyền.

Để đánh giá quyền, gửi yêu cầu bằng đúng tài khoản, thiết bị và phiên qua cổng. Phân biệt khóa tài khoản ở bên quản lý với tắt quyền tham gia kho; phân biệt người phê duyệt với người nhận quyền sử dụng tài liệu.

Nguyên mẫu chưa có hàng đợi phê duyệt giữa nhiều người dùng đăng nhập độc lập. Việc chọn người phê duyệt trên công cụ thử tạo một yêu cầu riêng bằng danh tính đó trong môi trường vận hành tin cậy.

## Các giới hạn cần nêu khi trình bày

- Hai bên quản lý có dữ liệu và khóa riêng nhưng dùng chung máy chủ, Keycloak và hạ tầng container.
- Trạng thái an toàn của thiết bị được mô phỏng; chứng thư không thay cho đo lường an toàn của máy thực.
- Thu hồi có độ trễ truyền, xử lý và lập lịch. Kiểm tra cuối không loại bỏ mọi lịch xử lý đồng thời.
- Một số kênh nội bộ chạy trong mạng Docker riêng, chưa triển khai xác thực hai chiều trên mọi kết nối.
- Các kiểm tra chưa đánh giá chịu tải doanh nghiệp, sẵn sàng cao hoặc khả năng chống người chiếm toàn bộ máy chủ.
- Tệp đã tải về máy nằm ngoài phạm vi thu hồi phiên. Xóa logic cũng không xóa ngay mọi bản sao lưu.
- Tình huống phục hồi mới chỉ kiểm tra dữ liệu phiên và việc yêu cầu đăng nhập lại, không xác nhận phục hồi đầy đủ cả hai bên.

## Bằng chứng khi thay đổi hệ thống

Nếu thay mã hoặc công nghệ, cần chạy lại phần bị ảnh hưởng và lưu bằng chứng mới cùng bản kiểm kê môi trường tương ứng. Không chỉnh sửa kết quả gốc để làm phù hợp thiết kế mới. Xem [cách tái lập](reproduction.md).
