# Hướng dẫn nhanh web demo

Cập nhật tài liệu ngày 25/10/2026. Dữ liệu và tài khoản đều dùng cho nguyên mẫu cục bộ.

## 1. Bật và tắt

Chạy trong PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File "E:\btl_bao_mat_Du_lieu\Start-Demo.ps1" -OpenBrowser
```

Mở [web demo](http://localhost:8088/#guide); nhấn **Ctrl + F5** nếu giao diện chưa cập nhật. Tắt toàn bộ container và WSL để giải phóng RAM:

```powershell
powershell -ExecutionPolicy Bypass -File "E:\btl_bao_mat_Du_lieu\Stop-Demo.ps1"
```

Tắt/bật không xóa dữ liệu. **Đặt lại dữ liệu lab** và bộ kiểm chứng chuẩn là thao tác khác, có thể thay tài liệu/grant/lịch sử bằng dữ liệu mẫu; tài khoản tự thêm được giữ lại.

## 2. Chọn đúng màn hình

| Mục trên thanh bên | Dùng khi nào? |
|---|---|
| Bắt đầu có hướng dẫn | Muốn hiểu hệ thống qua từng bài thử có sẵn |
| Tài liệu | Thêm tệp, sửa tên/nâng nhãn, cấp hoặc thu hồi quyền Hạn chế |
| Nhân viên | Tạo tài khoản, chọn vai trò/phòng ban, khóa/mở truy cập |
| Tự thử yêu cầu | Tự chọn người, việc cần làm, tài liệu rồi kiểm tra phản hồi |
| Nhật ký và cảnh báo | Xem lịch sử yêu cầu và sự kiện cần xử lý |
| Kiểm chứng tự động | Chạy bộ chuẩn hoặc bộ tình huống JSON tự soạn |
| Công cụ nâng cao → Điều khiển lab | Chuẩn bị thiết bị, lưu giữ/bảo toàn, mô phỏng lỗi, sao lưu và phục hồi |

## 3. Tạo nhân viên để thử

Vào **Nhân viên → Thêm nhân viên**, nhập họ tên, tên đăng nhập, mật khẩu, vai trò và phòng ban, rồi **Tạo nhân viên**.

- Tên đăng nhập: 3–32 ký tự thường, số hoặc `_`, bắt đầu bằng chữ. Mật khẩu: 8–128 ký tự.
- Nhân viên/Trưởng phòng thuộc Kinh doanh hoặc Vận hành; Kiểm toán/Quản trị an toàn thuộc An toàn thông tin.
- Tài khoản Keycloak và chứng thư được tạo thật, xuất hiện trong các ô chọn trên web.
- Bấm **Chỉnh sửa → Lưu quyền** để đổi vai trò/phòng ban hoặc bật/tắt **Cho phép truy cập hệ thống**. **Thử bằng tài khoản này** chuyển sang gửi yêu cầu.

Tài khoản mới đăng nhập bằng mật khẩu đã nhập. Tài khoản mẫu gồm alice, anna, adam, bob, bea, brian, auditor, secadmin; xem mật khẩu mẫu bằng `Show-Credentials.ps1 -ShowPassword`. adam/brian là trưởng phòng; auditor đọc audit/cảnh báo; secadmin quản lý phê duyệt và trạng thái, không mặc nhiên đọc nội dung.

## 4. Thêm tài liệu và chọn nhãn

Vào **Tài liệu → Thêm tài liệu**. Chọn TXT/CSV/PDF có nội dung, tối đa **1 MiB**, nhập tên hoặc để trống để lấy tên tệp; không cần gõ đuôi tệp. Chọn chủ sở hữu, nhãn rồi lưu.

| Nhãn | Người được tải trong B1, khi các điều kiện chung hợp lệ |
|---|---|
| Nội bộ | Nhân viên hoặc trưởng phòng cùng phòng |
| Mật | Nhân viên sở hữu tài liệu; trưởng phòng cùng phòng |
| Hạn chế | Trưởng phòng cùng phòng có grant đúng người, tài liệu, phiên bản và còn hạn |

**Thêm Hạn chế:** chọn **adam → Hạn chế → người phê duyệt secadmin → 15 phút → Thêm tài liệu**. Người tạo nhận quyền tải và sửa có thời hạn ngay khi lưu. Nhân viên như alice không được thêm Hạn chế. Lỗi chỉ rõ ô cần sửa và giữ dữ liệu đã nhập.

Phê duyệt tạo/nâng nhãn được sử dụng thành công một lần. Grant tải được dùng cho nhiều yêu cầu trong thời hạn, nếu các điều kiện khác vẫn đúng. Đây là hai loại hiệu lực khác nhau.

Ở **Tự thử yêu cầu**, biểu mẫu thêm nhanh chỉ có Nội bộ/Mật. Muốn thêm Hạn chế và chọn người phê duyệt, dùng mục **Tài liệu**.

## 5. Sửa và cấp quyền Hạn chế

1. Tìm tài liệu, bấm **Chỉnh sửa**, chọn **Người thực hiện**.
2. Sửa tên hoặc nâng nhãn rồi **Lưu thay đổi**. Người sửa phải có quyền tải tài liệu hiện tại. Nâng lên Hạn chế cần trưởng phòng và phê duyệt mới.
3. Ở tài liệu Hạn chế, xuống **Quyền tải và sửa tài liệu Hạn chế**; chọn người nhận, người phê duyệt và thời hạn, rồi **Cấp quyền tải và sửa**.
4. Chọn người phê duyệt và bấm **Thu hồi** ở các dòng grant còn hiệu lực của người cần kiểm tra cho tài liệu đó. Khi không còn grant hợp lệ, tải/sửa ở yêu cầu tiếp theo sẽ bị chặn; cấp lại quyền thì thử lại được.
5. Bấm **Thử truy cập** để chuyển sang tải bằng người thực hiện đang chọn.

Một người có thể có nhiều grant cho cùng tài liệu. Thu hồi một dòng chưa chặn được nếu còn dòng hợp lệ khác. Xem metadata chưa đủ để tải/sửa. Chức danh trưởng phòng chưa đủ khi sai phòng hoặc thiếu grant. Tài khoản, chứng thư, tuân thủ, rủi ro và độ mới tín hiệu vẫn được kiểm tra.

Không hạ nhãn tại màn hình này. Đổi nhãn tăng phiên bản, làm grant cũ không còn dùng được; đổi tên giữ phiên bản kiểm soát tài liệu. Sửa là sửa thông tin, chưa thay nội dung tệp. Hạn lưu giữ và bảo toàn chỉ để xem; chuẩn bị hai thuộc tính này trong Điều khiển lab bằng quyền người vận hành.

## 6. Tự thử yêu cầu và đọc kết quả

| Trường | Cách hiểu/cách chọn |
|---|---|
| Dùng danh tính nào? | Chọn tài khoản để thử nhiều người, hoặc dùng phiên Keycloak đã đăng nhập |
| Ai thực hiện? | Tài khoản gửi yêu cầu |
| Muốn làm gì? | Xem danh sách, xem metadata, tải, thêm, xóa logic, đọc audit/cảnh báo hoặc gọi API tùy chỉnh |
| Tài liệu nào? | Tài nguyên cụ thể; metadata là thông tin mô tả, download là nội dung đầy đủ |
| Chính sách áp dụng | Mặc định B1; B0 chỉ dùng đối chứng quyền đọc tĩnh |
| Thiết bị gửi yêu cầu — chứng thư | Mặc định đúng người; đổi khi muốn thử sai chứng thư hoặc không có chứng thư |
| Header bổ sung | Thường giữ `{}`; không nhập token/cookie |

Bấm **Gửi yêu cầu và xem kết quả**. Đọc kết quả tiếng Việt; mở **Xem HTTP, Request ID và JSON** khi cần bằng chứng. Nếu được tải, bấm **Lưu nội dung đã được cấp**. Tùy chỉnh đơn giản: GET `/me`, body `{}`, không thêm `/api` vào đường dẫn.

**B1** dùng chính sách đề xuất và trạng thái hiện tại. **B0** dùng thuộc tính đối chứng `b0_role`/`b0_department` trong JWT cho quyền đọc; chọn B0 không bỏ qua kiểm tra B1 khi sửa. Đổi quyền ở Nhân viên không tự đồng bộ các thuộc tính đối chứng trong Keycloak; đăng nhập lại không bảo đảm cập nhật B0. Giải thích mã và thuật ngữ: [giai_thich_ky_hieu.md](giai_thich_ky_hieu.md).

## 7. Đăng nhập và xử lý lỗi

Console là công cụ người vận hành cục bộ, cho phép chọn danh tính để thử. Đăng nhập Keycloak dùng tài khoản thật của demo. Khi có phiên, thêm/sửa tại mục Tài liệu dùng người đang đăng nhập. Ở Tự thử yêu cầu, chọn nguồn danh tính theo việc cần kiểm tra. Phê duyệt là yêu cầu riêng bằng tài khoản quản trị đã chọn; chưa có hàng đợi duyệt nhiều người độc lập.

| Thông báo | Cách xử lý |
|---|---|
| Chưa có quyền tải và sửa | Cấp lại grant đúng người/tài liệu/phiên bản ở phần quyền, kiểm tra hạn và thu hồi |
| Tài khoản bị khóa | Kích hoạt tại Nhân viên hoặc chọn người khác |
| Thiết bị sai người/không phù hợp/quá hạn | Chọn đúng chứng thư; kiểm tra thiết bị và tín hiệu tại Điều khiển lab |
| Thiếu người phê duyệt | Chọn quản trị an toàn đang hoạt động |
| Phiên hết hạn | Tải lại trang hoặc đăng nhập Keycloak lại |
| Dịch vụ chưa sẵn sàng | Kiểm tra Tổng quan trong Công cụ nâng cao và khởi động/khôi phục dịch vụ |

Audit/cảnh báo qua quyền người dùng cần auditor hoặc secadmin; trưởng phòng không tự có quyền này. HTTP 200 với danh sách rỗng nghĩa là chưa có bản ghi phù hợp. Màn hình nhật ký của console dùng quyền người vận hành. Sau lỗi ghi nhận thay đổi, làm mới danh sách trước khi gửi lại để tránh tạo trùng.

## 8. Trình diễn và kiểm chứng

Xem [các ca trình diễn và mục báo cáo tương ứng](huong-dan-trinh-dien-va-doi-chieu-bao-cao.md). Có thể bắt đầu với: thêm Hạn chế bằng adam/secadmin → tải/sửa thành công → thu hồi mọi grant còn hiệu lực của adam cho tài liệu → tải/sửa bị chặn → cấp lại. Muốn thử hết hạn, thu hồi các grant còn hạn khác trước, cấp 1 phút, rồi làm mới dữ liệu sau khi thời hạn kết thúc.

Các bài có hướng dẫn có thể dừng dịch vụ thật hoặc xóa logic rồi hoàn tác. Đọc phần thay đổi trước khi chạy. Xóa logic tạo tombstone, không xóa ngay snapshot. Phục hồi dùng DB/KMS cô lập, không thay hệ thống chính.

[Chỉ mục kết quả](ket_qua_kiem_chung.md) phân biệt lượt chuẩn ngày 19/10 với kiểm tra chức năng mới ngày 21/10; không cộng số mục hoặc coi bằng chứng cũ là kết quả của mọi lần chạy. [Mục lục](muc_luc.md) hướng dẫn thứ tự đọc toàn bộ tài liệu.
