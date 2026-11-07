# Kịch bản trình diễn và liên hệ với báo cáo

Tài liệu hỗ trợ chọn tình huống trình diễn. Lời thuyết trình theo thời gian nằm trong [script 10 phút](script_thuyet_trinh_10_phut.md). Cách bật web và xử lý lỗi nằm trong [hướng dẫn nhanh](huong_dan_nhanh.md).

## Chuẩn bị

Khởi động web, mở khóa Nhân viên đối tác, khôi phục thiết bị và thiết lập mặc định. Chọn tài liệu Nội bộ mà người dùng có quyền, chẳng hạn Quy trình tiếp nhận yêu cầu báo giá. Không đặt lại toàn bộ dữ liệu để chuẩn bị buổi trình bày.

Để sẵn kết quả đã chạy ở mục Kết quả kiểm tra. Không chạy tất cả tình huống đồng thời với demo thủ công. Khi so sánh, giữ người, thiết bị, tài liệu và quyền giống nhau; chỉ thay cách kiểm tra trạng thái.

## Tình huống chính: khóa tài khoản khi phiên còn hạn

1. Tạo phiên và tải thành công bằng Kiểm tra khi đăng nhập, rồi bằng Thu hồi theo thông báo và tự kiểm tra lại.
2. Dùng Quản trị đối tác · An toàn thông tin khóa Nhân viên đối tác tại Tài khoản và thiết bị.
3. Chờ kho ghi nhận thay đổi, gửi lại bằng hai phiên cũ. Không đăng nhập lại.
4. Cách chỉ kiểm tra khi đăng nhập có thể tiếp tục tải; cách có nhận thông báo và tự kiểm tra lại bị từ chối.
5. Mở khóa. Phiên đã thu hồi vẫn bị chặn; đăng nhập mới khi đủ điều kiện thì tải được.

Liên hệ báo cáo: bài toán hiệu lực truy cập sau đăng nhập, trách nhiệm hai bên, bộ điều phối và kết quả thu hồi. Đây là tình huống nên ưu tiên trong phần trình bày ngắn.

## Tình huống bổ sung: mất thông báo

1. Khôi phục mặc định, giữ tài khoản và thiết bị hợp lệ.
2. Tạo phiên cho Thu hồi theo thông báo và Thu hồi theo thông báo và tự kiểm tra lại.
3. Bật Làm mất các thông báo mới và áp dụng, sau đó khóa tài khoản.
4. Chờ kho hỏi lại rồi gửi bằng hai phiên cũ. Cách chỉ chờ thông báo còn giữ phiên, cách tự kiểm tra lại phát hiện và thu hồi.
5. Khôi phục mặc định và mở khóa khi kết thúc.

Liên hệ báo cáo: cơ chế hỏi lại bổ sung cho thông báo. Nếu ít thời gian, chỉ mở hàng Thông báo khóa tài khoản bị mất trong kết quả đã lưu.

## Tình huống bổ sung: không xác nhận lại được trạng thái

Tạo phiên có tự kiểm tra lại khi hệ thống bình thường. Bật Giả lập bên quản lý tài khoản không phản hồi rồi áp dụng. Chờ quá thời gian thông tin đã kiểm tra còn dùng được và gửi bằng phiên hiện tại. Kho tạm dừng, không cấp nội dung. Khôi phục mặc định sau khi thử.

Liên hệ báo cáo: giới hạn sử dụng thông tin cũ và đánh đổi giữa bảo vệ dữ liệu với khả dụng khi mất kết nối. Phân biệt từ chối vì tài khoản đã khóa với tạm dừng do chưa xác nhận lại được trạng thái.

## Tình huống tự thêm nhân viên và tài liệu

Trong Nhân viên và quyền, tạo nhân viên bằng tên chưa dùng, chọn bên quản lý, vai trò và phòng ban. Trong Quản lý tài liệu, thêm tệp nhỏ dưới nhãn Nội bộ hoặc Mật rồi thử bằng tài khoản phù hợp.

Với Hạn chế, chọn trưởng phòng làm người tạo và quản trị an toàn phê duyệt thời hạn. Thử tải, sửa khi quyền còn hiệu lực; thu hồi các quyền phù hợp rồi thử lại. Chỉ xem thông tin tài liệu không đủ để sửa hoặc tải nội dung.

Liên hệ báo cáo: dữ liệu và quy chuẩn phân loại, RBAC và ABAC, phê duyệt riêng theo phiên bản. Các tài khoản và tài liệu có thể bổ sung, không chỉ sử dụng mẫu điền sẵn.

## Theo dõi một yêu cầu trên sơ đồ

Trong PowerPoint, dùng slide 3 giải thích các thành phần, slide 5 giải thích 10 bước và slide 7 chuyển sang web. Sau khi gửi yêu cầu, chỉ vùng Kết quả truy cập để xác định bước được tiếp tục hoặc bị dừng.

Sơ đồ 10 bước mô tả đầy đủ hơn các nhóm bước trên web. Hai phần cùng mô tả việc xác minh tài khoản, thiết bị, phiên, quyền, giải mã và kiểm tra trước trả nội dung; số ô hiển thị không phải số lần gọi mạng.

| Nội dung cần giải thích | Tài liệu và bằng chứng |
|---|---|
| Vấn đề và căn cứ tham chiếu | [Tham chiếu Microsoft và Google](ke_thua.md) |
| Thành phần, dữ liệu riêng và đường đi yêu cầu | [Kiến trúc](architecture.md) |
| Vai trò và ba nhãn | [Phân loại dữ liệu](data-classification.md) |
| Khóa tài khoản, mất thông báo, mất kết nối | [Ma trận kiểm tra](test-matrix.md) |
| Kết quả và phạm vi kết luận | [Kết quả](ket_qua_kiem_chung.md), [rà soát bằng chứng](verification-review.md) |

Các liên hệ dựa vào chủ đề, không gắn cứng với số trang hoặc số mục có thể thay đổi khi dàn trang báo cáo.

## Kết thúc buổi thử

Mở khóa tài khoản mẫu, khôi phục thiết bị và thiết lập đã thay đổi. Lưu phản hồi, mã yêu cầu và ảnh cần dùng; tránh chụp mật khẩu hoặc bí mật phiên. Nếu không tiếp tục sử dụng, chạy `Stop-Demo.ps1` để giảm tài nguyên máy.
