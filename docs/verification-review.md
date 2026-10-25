# Đánh giá bằng chứng và giới hạn của demo

Cập nhật tài liệu: 25/10/2026. Đây là tổng hợp từ mã và tệp kết quả đã lưu; lần sửa tài liệu này không chạy lại suite hoặc mô phỏng lỗi. [Mục lục tài liệu](muc_luc.md) · [Ma trận kiểm chứng](test-matrix.md) · [Tái lập](reproduction.md).

## 1. Kết quả phải gắn với lượt và thời điểm

| Lượt | Kết quả đã lưu | Phạm vi diễn giải |
|---|---|---|
| [run-20261019-084335-960c43](../results/run-20261019-084335-960c43/results.json), ngày 19/10 | 127/127 mục, 0 lỗi; `false_allow=0`, `false_deny=0` trong tập kỳ vọng đã xác định | 125 mục oracle/trạng thái/vận hành và hai mục tổng hợp OPA/Python; không phải 127 test HTTP độc lập |
| Native trong lượt 19/10 | [31 Rego](../results/run-20261019-084335-960c43/opa-tests.txt); [32 Python đạt, một integration deselected](../results/run-20261019-084335-960c43/identity-tests.txt) | Các test con đã nằm trong hai mục tổng hợp, không cộng thêm vào 127 |
| [Cập nhật quyền ngày 21/10](../results/restricted-management-20261021/validation.json) | 39/39 kiểm tra tích hợp đạt | Bộ riêng cho thêm/sửa Hạn chế, grant, phê duyệt và giao dịch; không cộng vào lượt 19/10 |
| Hồi quy trong cập nhật 21/10 | 31/31 Rego và 18 Python đạt, được ghi trong [biên bản cập nhật](bang_chung/20261021-quyen-han-che.md) | 18 test xác thực/fixture được chọn để hồi quy, khác phạm vi 32 test của lượt 19/10 |

Manifest [sau lượt 19/10](../results/run-20261019-084335-960c43/environment.after.json) liên kết bản trước, hash kết quả, nguồn và image. Không coi ngày sửa tài liệu là một lần đo mới. Các kết quả cũ khác trong `results/` là lịch sử của phiên bản và bộ dữ liệu tương ứng.

## 2. Những điểm đã có bằng chứng

- API nghiệp vụ qua JWT và mTLS; chứng thư phải ánh xạ đúng chủ thể. Header tự khai không đổi quyền hoặc chuyển đường B1 sang B0.
- B1 dùng trạng thái hiện tại để kiểm tra tài liệu, phòng ban, owner, grant và thiết bị. Thu hồi có hiệu lực ở yêu cầu mới; không thu hồi byte đã được client nhận.
- Web mới thêm trực tiếp Hạn chế khi trưởng phòng có phê duyệt; giao dịch lưu tài liệu/grant/trạng thái approval cùng nhau. Approval chỉ sử dụng thành công một lần; grant còn hạn cho phép nhiều yêu cầu hợp lệ.
- Sửa thông tin dùng quyền tải hiện tại theo B1. Xem metadata chưa đủ để sửa; khi không còn grant hợp lệ khác, thu hồi hoặc hết hạn grant chặn cả tải và sửa. Quyền tải không cho phép hạ nhãn, sửa bảo toàn hoặc kéo dài lưu giữ.
- T21/T22 kết hợp kiểm tra lưu trữ, quyền token KMS, hash và sửa bản mã. Tiền tố ciphertext hoặc một lần download thành công riêng lẻ không đủ chứng minh bảo vệ lưu trữ.
- Lỗi audit trong kiểm tra thêm Hạn chế làm giao dịch không lưu tài liệu dở dang. Tuy nhiên, lỗi chuyển ledger sau commit có thể trả lỗi dù thay đổi đã commit; cần làm mới và đối chiếu trước khi gửi lại.

Các phát biểu trên giới hạn ở trường hợp đã thử. Chưa kiểm chứng mọi lịch xen kẽ đồng thời, mọi trạng thái hỏng hoặc tính đúng đắn hình thức của kiến trúc.

## 3. Console và phạm vi quyền

Console cục bộ là công cụ của người vận hành tin cậy, có Docker socket, DB quản trị, vật liệu phục hồi và khả năng chọn tài khoản để thử. Cookie, Host/Origin và CSRF bảo vệ đường console; chúng không biến console thành cổng doanh nghiệp cho người dùng không tin cậy.

Thêm/sửa tài liệu đi qua yêu cầu nghiệp vụ bằng người thực hiện; khi đã có phiên Keycloak, máy chủ dùng danh tính phiên. Phê duyệt trên console là yêu cầu riêng bằng tài khoản quản trị được chọn. Hiện chưa có hàng đợi duyệt nhiều người dùng độc lập. Danh sách dữ liệu của operator không đồng nhất với metadata được API cấp cho từng tài khoản.

Các bài Bắt đầu có hướng dẫn tách bước chuẩn bị bằng operator với bước gửi yêu cầu qua gateway. Các thao tác trực tiếp trong Điều khiển lab là thiết lập thí nghiệm, không phải chứng minh một nhân viên có quyền vận hành. Kiểm toán và quản trị an toàn không được đọc nội dung chỉ vì có vai trò quản trị.

## 4. Phục hồi và tính sẵn sàng

T23 kiểm tra PostgreSQL và OpenBao phục hồi trên mạng cô lập, đối chiếu hash và ledger của quyền thu hồi/tombstone. `primary_replaced=false`: không promote bản phục hồi, không chuyển lưu lượng, không khôi phục đầy đủ Keycloak/PKI/host. Các yêu cầu T23c–e tới primary không phải kiểm tra API mở từ DB cô lập. Mã hiện hành còn loại bỏ approval tạo/nâng nhãn đang chờ trong bản phục hồi cô lập. Đây là hành vi được đối chiếu từ mã sau cập nhật, chưa được lượt T23 ngày 19/10 xác nhận riêng; bộ 39 ca ngày 21/10 cũng không kiểm tra phục hồi. Ledger không chứa bản mã để tái tạo tài liệu thêm sau snapshot, nên không thể coi đối chiếu ledger là phục hồi đầy đủ mọi dữ liệu mới nhất.

OPA/OpenBao bị dừng trong một số tình huống là lỗi container thật. `opa_response_invalid`, `registry_unavailable`, `audit_write_failure` là fault do operator tiêm; lỗi phản hồi OPA mô phỏng chưa đồng nghĩa một OPA giả phát JSON sai qua mạng. Fail closed bảo vệ điều kiện bắt buộc nhưng làm giảm khả dụng khi phụ thuộc lỗi.

## 5. Giới hạn khi trình bày báo cáo

- Dữ liệu tổng hợp, một host; chứng thư lab chứng minh sở hữu khóa, tín hiệu tuân thủ/risk là giả lập, chưa phải MDM/EDR hoặc attestation phần cứng.
- Một số kết nối nội bộ dùng HTTP; chưa có mTLS giữa mọi dịch vụ, HA hoặc đo tải đồng thời đủ để kết luận ở quy mô doanh nghiệp.
- Metadata, audit và ledger chưa được bảo vệ trước người chiếm host/controller. Các nguồn bí mật không được sao chép vào báo cáo, ảnh hoặc gói nguồn công khai.
- Xóa logic/tombstone không xóa ngay mọi backup. Không có lịch `forget/prune` tự động; dữ liệu, backup và vật liệu phục hồi cùng ổ E chưa chống mất toàn bộ ổ.
- B0 là đối chứng quyền đọc tĩnh có chủ ý của nhóm, không phải hệ thống Google/Microsoft hoặc đại diện cho mọi cách phân quyền đơn giản. So sánh không tách riêng đóng góp của từng cơ chế.
- Số đo hiệu năng cũ trong `results/benchmark-*` là phép đo riêng của nguyên mẫu. Không dùng thời gian chạy suite làm độ trễ API; không suy rộng p95 của một máy thành kết luận nhà cung cấp hay SLA.

Khi thay đổi mã hoặc chính sách, cần lượt kiểm chứng và bản môi trường mới. Bằng chứng lịch sử vẫn được giữ để truy vết, không sửa expected hoặc JSON cũ để làm phù hợp phiên bản mới.
