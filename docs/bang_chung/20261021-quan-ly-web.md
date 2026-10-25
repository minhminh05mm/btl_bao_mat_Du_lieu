# Kiểm tra trang quản lý tài liệu và nhân viên

Biên bản lịch sử ngày 21/10/2026, chuyển vị trí tài liệu ngày 25/10/2026. Các mô tả giao diện trong biên bản phản ánh đúng thời điểm đó. [Mục lục](../muc_luc.md) · [Tệp kết quả và ảnh gốc](../../results/management-ui-20261021/).

Ngày thực hiện: 21/10/2026. Địa chỉ: http://localhost:8088.

Bản này mô tả giao diện trước cập nhật quyền Hạn chế cùng ngày. Chức năng sửa bằng đặc quyền người vận hành và luồng thêm Mật rồi nâng nhãn đã được thay thế; xem [biên bản quyền Hạn chế](20261021-quyen-han-che.md) và [hướng dẫn hiện hành](../huong_dan_nhanh.md).

## Đã triển khai

- Trang Tài liệu: tìm kiếm, thêm tệp, chọn chủ sở hữu và một trong ba nhãn; sửa tên, nhãn, hạn lưu giữ và trạng thái bảo toàn.
- Tên nhập không cần có đuôi tệp; hệ thống giữ đuôi của tệp đã chọn. Cả trang Tài liệu và phần Tự thử yêu cầu đã được kiểm tra.
- Trang Nhân viên: tạo tài khoản Keycloak, chứng thư và danh tính nghiệp vụ; sửa vai trò, phòng ban, trạng thái truy cập; chuyển sang thử bằng tài khoản vừa chọn.
- Các ô tài khoản, thiết bị, chủ sở hữu và phê duyệt đọc từ dữ liệu hiện tại, không cố định ở tám tài khoản ban đầu.
- Phản hồi thông thường chỉ trình bày kết quả, nguyên nhân và cách xử lý. Bỏ câu bình luận về kết quả mong đợi của bài thử trong vùng phản hồi này.
- Lỗi biểu mẫu đánh dấu ô cần sửa, giữ các giá trị còn lại và đưa con trỏ đến ô lỗi.
- Thông tin vai trò/phòng ban của phép đối chứng B0 được khai báo trong Keycloak với quyền sửa chỉ dành cho quản trị.

## Kết quả

### Kiểm tra tích hợp

Tệp `validation.json` ghi nhận 24/24 kiểm tra đạt, gồm:

1. Trường thông tin tài khoản và tài liệu không hợp lệ trả lỗi đúng vị trí.
2. Tạo nhân viên và trưởng phòng mới; xác thực qua JWT, chứng thư và gateway thật.
3. Tên đăng nhập trùng bị từ chối; danh tính đã có vẫn sử dụng được.
4. Tải tài liệu Nội bộ và Hạn chế với tên nhập không có đuôi tệp.
5. Tải lại tài liệu có nội dung trùng với tệp gửi lên.
6. Đổi nhãn và trạng thái bảo toàn; phiên bản tài liệu tăng khi đổi nhãn.
7. Nhân viên khác bị chặn đọc tài liệu Mật, trưởng phòng cùng phòng được đọc.
8. Tài liệu Hạn chế yêu cầu phê duyệt; cấp phê duyệt cho tài khoản mới rồi tải thành công.
9. Khóa/mở truy cập có hiệu lực với yêu cầu tiếp theo.
10. Đổi sang Kiểm toán làm quyền đọc audit có hiệu lực và quyền tải tài liệu nghiệp vụ bị chặn.
11. Dữ liệu đã có được giữ; các dịch vụ hoạt động bình thường sau kiểm tra.

`additional-validation.json` có sáu kiểm tra đạt về cấu trúc đầu vào và tài khoản được tạo sau khi đăng ký thuộc tính Keycloak. `b0-validation.json` xác nhận hai tài khoản mới tải đúng phạm vi trong B0; tài khoản mới sau đó cũng được kiểm tra thành công ở cả B0 và B1.

### Kiểm tra qua giao diện

- Gửi biểu mẫu nhân viên trống: lỗi hiện ở họ tên, tên đăng nhập và mật khẩu.
- Không chọn tệp: đánh dấu ô tệp.
- Tệp vượt 1 MiB: từ chối trước khi gửi nội dung.
- Tên chứa dấu `/`: đánh dấu ô tên và yêu cầu sửa.
- Sửa tên thành hợp lệ: tài liệu được thêm và xuất hiện trong danh sách.
- Đổi nhãn bằng ô chọn và lưu thành công.
- Khóa nhân viên, gửi yêu cầu và nhận lý do tài khoản bị khóa; sau đó mở lại tài khoản.
- Vùng phản hồi không còn dòng bình luận phụ như ảnh người dùng phản ánh.
- Thêm tài liệu từ phần Tự thử yêu cầu với tên không có đuôi tệp: thành công.
- Bố cục được kiểm tra tại cửa sổ hẹp và desktop; trang không tràn ngang.

### Hồi quy và đặt lại dữ liệu

Đã chạy `tests/test_fixture_seed.py` và `tests/test_auth_verifier.py`: 18 kiểm tra đạt. Có một cảnh báo tương thích từ thư viện kiểm thử; không phát sinh lỗi kiểm tra.

Khôi phục tài khoản tự thêm sau khi đặt lại được kiểm tra bằng bảng PostgreSQL tạm. Các tài khoản giữ đúng vai trò, phòng ban và trạng thái; chạy lại thao tác không tạo trùng. Không đặt lại các bảng dữ liệu thật trong phép kiểm tra này.

## Dữ liệu và giới hạn

Ba nhãn được dùng theo chính sách hiện có: Nội bộ, Mật, Hạn chế. Nhãn được chọn và thay đổi trực tiếp; chưa thêm loại nhãn tùy ý ngoài chính sách. Tệp được hỗ trợ gồm TXT, CSV và PDF, tối đa 1 MiB.

Các màn hình quản lý dùng quyền người vận hành của môi trường cục bộ. Truy cập và thêm nội dung đi qua API nghiệp vụ; tạo tài liệu Hạn chế dùng API nâng nhãn. Sửa thuộc tính trên màn hình quản lý dùng quyền người vận hành cục bộ. Không thay chính sách Rego hay loại bỏ kiểm tra JWT, chứng thư, mã hóa và nhật ký.

Tài liệu và tài khoản tổng hợp tạo trong kiểm tra được giữ để có thể dùng tiếp. Mật khẩu không được đưa vào tệp kết quả. Mã nguồn trước khi sửa nằm trong `before/`.
