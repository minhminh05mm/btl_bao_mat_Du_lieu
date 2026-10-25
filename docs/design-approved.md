# Quyết định thiết kế hiện hành

Cập nhật tài liệu ngày 25/10/2026. Tài liệu này tóm tắt các quyết định đang được hiện thực, thay cho đề xuất và phân công triển khai cũ. [Mục lục](muc_luc.md) · [Kiến trúc chi tiết](architecture.md) · [Sử dụng web](huong_dan_nhanh.md)

## 1. Bài toán và căn cứ

Đề tài thiết kế và triển khai kiến trúc Zero Trust bảo vệ kho tài liệu nội bộ. Nhóm sử dụng hai phòng ban, ba nhãn và dữ liệu tổng hợp để kiểm chứng quan hệ giữa danh tính, quyền hiện tại, thiết bị, dữ liệu, mật mã, nhật ký và phục hồi.

Kiến trúc kế thừa khái niệm từ BeyondCorp, Microsoft Zero Trust và NIST; dùng SABSA rút gọn để nối yêu cầu với kiểm soát và bằng chứng. Phần nhóm thiết kế là chính sách kho tài liệu, luồng phối hợp, quy tắc phê duyệt/grant và cách kiểm chứng. Không xác lập kiến trúc mới hoàn toàn hoặc mức bảo đảm tương đương hệ thống của nhà cung cấp.

## 2. Quyết định và đánh đổi

| Quyết định | Lý do | Điều kiện hoặc giới hạn |
|---|---|---|
| Gateway xác minh mTLS; API xác minh JWT và thực thi quyền với OPA | Liên kết yêu cầu với danh tính và khóa thiết bị, tách đánh giá quy tắc | Chứng thư không chứng minh thiết bị sạch mã độc; một số kết nối nội bộ còn HTTP |
| Đọc quyền/metadata hiện tại ở mỗi yêu cầu B1 | Thu hồi và đổi trạng thái tác động tới yêu cầu mới | Không lấy lại được bản rõ đã phát; phải kiểm tra thời hạn trong giao dịch |
| Phân loại thủ công Nội bộ/Mật/Hạn chế | Có căn cứ nội dung và hậu quả tiết lộ rõ ràng | Chưa tự phát hiện người dùng gán nhãn thấp hơn nội dung |
| Nội dung mã hóa Transit, khóa tách khỏi DB | Hạn chế khả năng giải mã chỉ từ bản sao DB | API có quyền decrypt vẫn là thành phần nhạy cảm; metadata chưa mã hóa toàn bộ |
| Thêm Hạn chế bằng trưởng phòng và phê duyệt riêng | Không lưu trung gian dưới nhãn thấp; người tạo được cấp quyền ban đầu có thời hạn | Console chọn danh tính quản trị là công cụ operator, chưa có hàng đợi duyệt nhiều người |
| Sửa thông tin yêu cầu quyền tải B1 hiện tại | Không tồn tại đường sửa vượt điều kiện đọc nội dung | Chưa hỗ trợ thay thế tệp; quyền sửa không bao gồm lưu giữ/bảo toàn |
| Grant theo tài liệu, phiên bản, hành động và thời hạn | Giới hạn phạm vi sử dụng, thu hồi có thể kiểm tra | Grant còn hạn không bỏ qua vai trò, phòng ban và thiết bị |
| Audit bắt buộc và mặc định từ chối khi kiểm soát lỗi | Yêu cầu không nhận bản rõ khi thiếu kiểm soát/bằng chứng | Giảm tính sẵn sàng khi PDP/KMS/audit lỗi |
| Backup cặp DB/KMS, phục hồi cô lập và đối chiếu ledger | Kiểm tra được nội dung và trạng thái an toàn sau snapshot | Chưa chuyển hệ thống chính; các bản sao cùng ổ E chưa chống mất ổ |
| B0 làm đối chứng quyền đọc tĩnh | Minh họa tác động của gói điều kiện B1 | Không phải kiến trúc Google/Microsoft; không dùng B0 bỏ qua điều kiện sửa/quản trị |

## 3. Phạm vi chức năng đã hiện thực

- Web có Bắt đầu có hướng dẫn, Tài liệu, Nhân viên, Tự thử yêu cầu, Nhật ký và cảnh báo, Kiểm chứng tự động; Tổng quan/Điều khiển lab nằm trong công cụ nâng cao.
- Người vận hành thêm nhân viên thật trong Keycloak, tạo chứng thư, đặt vai trò/phòng ban, khóa/mở truy cập. Tài khoản tự thêm xuất hiện trong các ô chọn; không cố định ở tám tài khoản khởi tạo.
- Thêm TXT/CSV/PDF tối đa 1 MiB; chủ sở hữu/phòng ban do API gán theo danh tính thực thi. Hạn chế cần quản trị an toàn phê duyệt cho trưởng phòng.
- Phê duyệt tạo/nâng nhãn chỉ được sử dụng thành công một lần. Tài liệu, grant ban đầu và trạng thái đã dùng được lưu cùng giao dịch. Grant sử dụng được ở nhiều yêu cầu còn hiệu lực.
- Sửa tên hoặc nâng nhãn kiểm tra quyền tải tại API; không hạ nhãn. Nâng nhãn tăng phiên bản và giới hạn lưu giữ; đổi tên giữ phiên bản kiểm soát tài liệu.
- Bảng quyền Hạn chế cho phép chọn người nhận, người phê duyệt, thời hạn và thu hồi. Một người có thể còn grant khác hợp lệ sau khi thu hồi một dòng; chỉ kết luận bị chặn vì thiếu grant khi không còn grant phù hợp. Xem metadata một mình không đủ để tải/sửa.
- Lỗi biểu mẫu nêu nguyên nhân và đánh dấu trường cần sửa; kết quả nghiệp vụ có Request ID và bằng chứng kỹ thuật.

## 4. Miền vận hành và điều kiện bàn giao

Console cục bộ là thành phần của người vận hành tin cậy, có quyền chuẩn bị dữ liệu, quản lý môi trường và chọn danh tính để kiểm thử. Khi dùng phiên Keycloak để thêm/sửa tài liệu, máy chủ gắn thao tác với người đang đăng nhập. Quản trị nghiệp vụ qua gateway phải được phân biệt với đặc quyền operator tạo tài khoản, chỉnh trạng thái lab hoặc dừng dịch vụ.

Bộ `business-v1` khởi tạo 20 tài liệu và tám tài khoản; đó là trạng thái nền để tái lập, không phải giới hạn hoặc số hiện có. Đặt lại dữ liệu/bộ kiểm chứng chuẩn có thể thay tài liệu và lịch sử thử; tài khoản tự thêm được khôi phục theo hồ sơ vận hành.

Đầu ra bàn giao gồm mã nguồn/cấu hình, web, [quy chuẩn dữ liệu](data-classification.md), [hợp đồng API](implementation-contract.md), [ma trận kiểm chứng](test-matrix.md), [hướng dẫn tái lập](reproduction.md) và kết quả có ngày, phạm vi, mã lượt. Kết quả lịch sử giữ nguyên; thay đổi chức năng phải có bằng chứng bổ sung riêng.
