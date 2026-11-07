# Quy chuẩn phân loại và quyền với tài liệu

## Nguồn dữ liệu

Bộ dữ liệu nền mô phỏng kho tài liệu của hai phòng Kinh doanh và Vận hành. Nội dung, tên dự án và số liệu được tạo tổng hợp, không lấy từ hồ sơ khách hàng hoặc doanh nghiệp thực.

Bộ nền có 20 tài liệu TXT, mỗi phòng gồm năm tài liệu Nội bộ, ba tài liệu Mật và hai tài liệu Hạn chế. Đây là số của bộ khởi tạo; số hiện có có thể tăng khi người vận hành bổ sung dữ liệu. Mỗi tài liệu có tên, chủ sở hữu, phòng ban, nhãn, phiên bản và thuộc tính vòng đời.

TXT, CSV và PDF là các định dạng có thể thêm qua web, tối đa 1 MiB cho mỗi tệp. Định dạng không quyết định mức nhạy cảm.

## Căn cứ phân loại

Nhãn được lựa chọn thủ công theo nội dung, phạm vi sử dụng và hậu quả tiết lộ. Ba nhãn là quy ước của bài toán nghiên cứu, không phải cấp độ bí mật nhà nước hoặc một kết luận pháp lý.

| Nhãn | Căn cứ nội dung và hậu quả | Phạm vi nội dung khi các điều kiện chung hợp lệ |
|---|---|---|
| Nội bộ | Quy trình, lịch phối hợp, biên bản và số liệu tổng hợp; không chứa giá riêng, phương án đàm phán hoặc điểm yếu chưa khắc phục | Nhân viên và trưởng phòng cùng phòng ban |
| Mật | Thông tin riêng chưa công bố của dự án, báo giá, dự toán hoặc phân tích sự cố; tiết lộ có thể ảnh hưởng lợi thế thương mại hoặc vận hành | Nhân viên sở hữu tài liệu cùng phòng; trưởng phòng cùng phòng |
| Hạn chế | Giới hạn nhượng bộ, ngân sách chưa duyệt, điểm yếu chưa khắc phục hoặc kế hoạch phục hồi trọng yếu; hậu quả có thể vượt một hồ sơ đơn lẻ | Trưởng phòng cùng phòng được xem thông tin tài liệu; tải nội dung cần quyền có thời hạn, đúng người, tài liệu, phiên bản và thao tác |

Thời hạn lưu giữ mẫu lần lượt là 180, 90 và 30 ngày. Đây là tham số thử nghiệm, không phải thời hạn tối ưu hoặc nghĩa vụ pháp lý. Tài khoản, thiết bị, phiên, quyền tham gia kho và thời hạn tài liệu vẫn phải đáp ứng điều kiện kiểm tra.

## Danh mục tài liệu mẫu

Tên và nhãn dưới đây là trạng thái khởi tạo. Sau khi nâng nhãn, quyết định truy cập sử dụng nhãn hiện tại trong cơ sở dữ liệu. Mã nội bộ giúp tìm bản ghi và đối chiếu bằng chứng, không được dùng thay cho quyền.

| Tài liệu | Chủ sở hữu mẫu | Nhãn ban đầu và căn cứ |
|---|---|---|
| Quy trình tiếp nhận yêu cầu báo giá | Alice, Kinh doanh | Nội bộ: hướng dẫn chung, không chứa mức giá riêng |
| Lịch phối hợp tư vấn tháng 10 | Anna, Kinh doanh | Nội bộ: lịch theo vai trò, không có thông tin liên hệ thật hoặc nội dung thương lượng |
| Hướng dẫn cập nhật cơ hội bán hàng | Adam, Kinh doanh | Nội bộ: quy ước cập nhật, không chứa giá hoặc cam kết riêng |
| Báo cáo tổng hợp lượt tư vấn tháng 10 | Alice, Kinh doanh | Nội bộ: số lượt theo nhóm, không gắn hồ sơ khách hàng |
| Biên bản họp điều phối kinh doanh | Anna, Kinh doanh | Nội bộ: công việc chung, không chứa giới hạn thương lượng |
| Dự thảo báo giá dự án Mây Xanh | Alice, Kinh doanh | Mật: có đơn giá và cấu phần chào bán chưa công bố |
| Kế hoạch đàm phán dự án Bình Minh | Anna, Kinh doanh | Mật: có ưu tiên và điều kiện trao đổi riêng |
| Dự toán doanh thu theo cơ hội quý IV | Adam, Kinh doanh | Mật: có giá trị dự kiến theo từng cơ hội |
| Ngưỡng chiết khấu ngoại lệ dự án Mây Xanh | Alice, Kinh doanh | Hạn chế: có giới hạn nhượng bộ chưa công bố |
| Phương án phân bổ ngân sách kinh doanh | Adam, Kinh doanh | Hạn chế: có mức dự phòng và thứ tự ưu tiên chưa duyệt |
| Quy trình bàn giao ca vận hành | Bob, Vận hành | Nội bộ: công việc chung, không chứa phương án ứng phó trọng yếu |
| Lịch bảo trì dịch vụ nội bộ | Bea, Vận hành | Nội bộ: lịch phối hợp, không có địa chỉ thật hoặc cấu hình đặc quyền |
| Hướng dẫn ghi nhận sự cố | Brian, Vận hành | Nội bộ: biểu mẫu chung, không mô tả sự cố riêng |
| Báo cáo tổng hợp yêu cầu hỗ trợ | Bob, Vận hành | Nội bộ: số lượng tổng hợp, không lộ hồ sơ riêng |
| Biên bản họp cải tiến vận hành | Bea, Vận hành | Nội bộ: cải tiến chung, không có điểm yếu chưa khắc phục |
| Kế hoạch triển khai dịch vụ dự án Mây Xanh | Bob, Vận hành | Mật: trình tự và nguồn lực riêng chưa công bố |
| Biên bản phân tích sự cố dự án Bình Minh | Bea, Vận hành | Mật: diễn biến, ảnh hưởng và giả thuyết nguyên nhân của sự cố mô phỏng |
| Dự toán chi phí vận hành quý IV | Brian, Vận hành | Mật: chi phí và phương án sử dụng nguồn lực chưa công bố |
| Phương án xử lý điểm yếu chưa khắc phục | Bob, Vận hành | Hạn chế: tình trạng chưa khắc phục và thứ tự giảm thiểu |
| Kế hoạch phục hồi dịch vụ trọng yếu | Brian, Vận hành | Hạn chế: thứ tự phục hồi và điều kiện chuyển sang phục vụ |

Ví dụ, quy trình tiếp nhận báo giá, dự thảo báo giá và ngưỡng chiết khấu cùng liên quan bán hàng nhưng có mức tác động khi tiết lộ khác nhau. Việc phân loại dựa trên thông tin thực sự có trong nội dung. Chủ sở hữu là nhân viên không tự có quyền đọc một tài liệu Hạn chế chỉ vì đứng tên sở hữu.

## Vai trò và quyền

| Vai trò | Quyền chính |
|---|---|
| Nhân viên | Dùng tài liệu theo phòng ban, nhãn và chủ sở hữu |
| Trưởng phòng | Dùng tài liệu trong phạm vi phòng; tải Hạn chế cần quyền riêng còn hạn |
| Quản trị đối tác | Quản lý trạng thái tài khoản, thiết bị của đối tác; không tự quản trị dữ liệu kho |
| Quản trị an toàn tại kho | Quản lý quyền an toàn và phê duyệt; đọc nhật ký, cảnh báo theo quyền |
| Kiểm toán | Đọc nhật ký, cảnh báo; không mặc nhiên tải nội dung nghiệp vụ |

Quyền tham gia kho và trạng thái tài khoản ở bên quản lý là hai thuộc tính riêng. Các thay đổi quyền tại kho được đọc khi xử lý yêu cầu, không lấy vai trò tự khai từ biểu mẫu làm quyết định cuối.

## Thêm và sửa tài liệu Hạn chế

1. Chọn trưởng phòng cùng phạm vi nghiệp vụ làm người tạo, chọn nhãn Hạn chế.
2. Quản trị an toàn khác người nhận phê duyệt cho đúng người, phòng ban, tài liệu, phiên bản, mục đích và thời hạn.
3. API xác minh phê duyệt rồi mã hóa và lưu tài liệu, quyền ban đầu, trạng thái đã dùng phê duyệt trong cùng giao dịch.
4. Người nhận tải hoặc sửa khi quyền còn hạn và mọi điều kiện khác vẫn hợp lệ.

Phê duyệt tạo hoặc nâng nhãn chỉ sử dụng thành công một lần. Quyền truy cập có thời hạn có thể dùng ở nhiều yêu cầu. Một người có thể có nhiều quyền phù hợp; thu hồi một quyền chưa loại bỏ những quyền khác còn hiệu lực.

Sửa thông tin cần quyền tải nội dung hiện tại. Đổi tên giữ phiên bản kiểm soát; nâng nhãn tăng phiên bản và có nhật ký. Nâng lên Hạn chế cần phê duyệt cho phiên bản mới. Không cho hạ nhãn hoặc dùng quyền tải để thay đổi thời hạn lưu giữ, trạng thái bảo toàn. Chức năng sửa chưa thay thế nội dung tệp.

Hệ thống chưa tự phân tích nội dung để phát hiện người dùng gán nhãn thấp. Chủ sở hữu và phòng ban được máy chủ xác định theo danh tính thực thi; các giá trị trong biểu mẫu phải qua kiểm tra trước khi lưu.

## Lưu giữ, bảo toàn và xóa

Hết thời hạn lưu giữ làm tài liệu không còn được cấp để đọc theo quy tắc hiện tại. Trạng thái bảo toàn ngăn xóa ngay cả khi đã hết thời gian lưu giữ. Yêu cầu xóa còn chịu kiểm tra quyền, chủ sở hữu và điều kiện vòng đời.

Xóa hợp lệ là xóa logic: hệ thống ghi trạng thái tài liệu đã xóa để các yêu cầu tiếp theo không nhận nội dung. Thao tác này không xóa ngay mọi bản sao lưu. Quyền tải hoặc sửa thông tin không tự cho phép thay đổi thời hạn lưu giữ và bảo toàn.

## Lưu trữ, tái lập và bằng chứng

[Định nghĩa dữ liệu](../app/fixture_data.py) tạo nội dung nền tất định. [Bản kê bộ dữ liệu](../fixtures/dataset-manifest.json) lưu tiêu đề, căn cứ nhãn, chủ sở hữu, kích thước và mã băm. PostgreSQL giữ bản mã nội dung; tên, nhãn và thông tin quản lý cần thiết vẫn ở dạng rõ có kiểm soát.

Khởi động bình thường giữ dữ liệu hiện có. Bộ kiểm tra phối hợp hai bên hiện tại tạo tài liệu thử riêng và giữ lại để xem kết quả, không đặt lại toàn bộ kho. Các công cụ đặt lại dữ liệu của nguyên mẫu cũ có phạm vi khác; không dùng chúng chỉ để chuẩn bị trình diễn.

Danh mục trên trang điều khiển dành cho người vận hành tin cậy. Muốn chứng minh quyền của một nhân viên, gửi yêu cầu bằng phiên và thiết bị của nhân viên đó. Danh sách nhìn thấy trên trang điều khiển không thay thế quyết định của API.

[Ma trận kiểm tra](test-matrix.md) có tình huống thêm, sửa, tải Hạn chế và đọc nhật ký, cảnh báo. Những kết quả này không chứng minh chất lượng phân loại tự động hoặc sự phù hợp của chính sách với dữ liệu doanh nghiệp thực.
