# Kịch bản trình diễn và đối chiếu báo cáo

Cập nhật tài liệu ngày 25/10/2026 theo web có quản lý Tài liệu, Nhân viên và quyền Hạn chế. Đây là kịch bản để người vận hành thực hiện khi thuyết trình; các kết quả dưới đây là kỳ vọng trong điều kiện đã nêu.

[Hướng dẫn sử dụng](huong_dan_nhanh.md) · [Giải thích ký hiệu](giai_thich_ky_hieu.md) · [Ma trận kiểm chứng](test-matrix.md)

## 1. Chuẩn bị trước buổi trình diễn

1. Bật bằng `Start-Demo.ps1`, mở [web](http://localhost:8088), nhấn Ctrl + F5.
2. Nếu dùng ô chọn tài khoản để đóng nhiều vai, chọn **Chọn tài khoản** ở Tự thử yêu cầu. Khi thêm/sửa tại Tài liệu mà đã đăng nhập Keycloak, hệ thống dùng người của phiên; đăng xuất trước nếu muốn chọn các vai thử khác nhau.
3. Kiểm tra tài khoản dùng cho bài đang hoạt động, vai trò/phòng ban đúng; thiết bị đúng người, chưa thu hồi, tuân thủ và có rủi ro NORMAL/tín hiệu mới. Các dịch vụ phải sẵn sàng.
4. Chuẩn bị một tệp TXT nhỏ, nội dung tổng hợp, không có dữ liệu thật. Chọn tên dễ tìm như `Ho so trinh dien.txt`.
5. Với ca mẫu, kiểm tra A-C02 vẫn thuộc anna, nhãn Mật, chưa xóa và còn hạn. Nếu đã đổi trạng thái, khôi phục đúng từng thuộc tính bằng Điều khiển lab hoặc dùng bài **Bắt đầu có hướng dẫn** tương ứng.

**Không bấm Đặt lại dữ liệu lab hoặc Chạy bộ kiểm chứng đầy đủ chỉ để chuẩn bị buổi diễn.** Các thao tác này có reset bộ dữ liệu; tài liệu tự thêm và lịch sử có thể mất khỏi bộ hoạt động. Các ca dưới không đòi hỏi reset toàn hệ thống. Những thay đổi do người vận hành thử cần được ghi nhớ và hoàn tác phù hợp.

Bảng tài liệu và nhật ký của console thuộc quyền người vận hành. Muốn chứng minh quyền nghiệp vụ, phải gửi yêu cầu ở **Tự thử yêu cầu**, xem phản hồi API và Request ID.

## 2. Tạo nhân viên và thêm tài liệu thông thường

**Mục tiêu:** chứng minh dữ liệu/người dùng có thể tự bổ sung, không chỉ dùng lựa chọn điền sẵn.

- Vào **Nhân viên → Thêm nhân viên**. Nhập tên và username chưa dùng, mật khẩu tự chọn, vai trò Nhân viên, phòng Kinh doanh.
- Bấm **Tạo nhân viên**, chọn người vừa tạo rồi **Thử bằng tài khoản này**. Tài khoản được tạo thật trong Keycloak, kèm danh tính nghiệp vụ và chứng thư.
- Vào **Tài liệu → Thêm tài liệu**, chọn tệp, tên, chủ sở hữu mới và nhãn Nội bộ; bấm **Thêm tài liệu**.
- Chọn tài liệu, dùng người thực hiện là chủ sở hữu, bấm **Thử truy cập → Gửi yêu cầu và xem kết quả**.

**Kỳ vọng:** thêm thành công; download trả `200 ALLOW`; nút **Lưu nội dung đã được cấp** xuất hiện. Không cần tự gõ đuôi tệp. Username trùng hoặc đầu vào sai phải được chỉ rõ tại ô tương ứng.

**Đối chiếu:** báo cáo mục 3.1 về dữ liệu/chủ thể; 3.3 về thành phần và luồng kiểm tra; 4.4 về kiểm chứng bổ sung.

## 3. Thêm trực tiếp tài liệu Hạn chế

**Mục tiêu:** phân biệt người dùng nội dung với người phê duyệt; chứng minh quyền không đến từ sở hữu đơn thuần.

1. **Tài liệu → Thêm tài liệu**: cùng tệp, chọn chủ sở hữu alice và nhãn Hạn chế, gửi.
2. Đổi chủ sở hữu thành adam, giữ Người phê duyệt chưa chọn, gửi lại.
3. Chọn Người phê duyệt secadmin, thời hạn 15 phút, bấm **Thêm tài liệu**.
4. Chọn người thực hiện adam, sửa tên rồi **Lưu thay đổi**.
5. Bấm **Thử truy cập** và gửi yêu cầu tải.

| Bước | Kết quả cần quan sát |
|---|---|
| alice thêm Hạn chế | Bị chặn; lỗi ở Chủ sở hữu, yêu cầu trưởng phòng |
| adam chưa có người phê duyệt | Bị chặn; lỗi ở Người phê duyệt |
| adam + secadmin + thời hạn | Lưu trực tiếp nhãn Hạn chế, có grant ban đầu |
| adam sửa và tải khi grant còn hạn | Sửa thành công; download `200 ALLOW` |

Ở **Quyền tải và sửa tài liệu Hạn chế**, chỉ ra người nhận, phiên bản, thời hạn và trạng thái. Nhãn Hạn chế, tài liệu và grant được lưu trong cùng giao dịch. Phê duyệt tạo dùng thành công một lần; grant tải có thể dùng cho nhiều yêu cầu khi còn hiệu lực.

**Đối chiếu:** 3.1 về quy chuẩn Hạn chế; 3.3 về phê duyệt/PDP/PEP; 3.4 về lưu dữ liệu và quyền; 4.4 về các ca bổ sung ngày 21/10/2026.

## 4. Xem metadata khác quyền tải/sửa; thu hồi và hết hạn

Dùng tài liệu vừa tạo trong ca 3, không dùng một ID cố định từ buổi diễn trước.

1. Chọn secadmin trong Người phê duyệt ở phần quyền, bấm **Thu hồi** tại dòng grant đang còn hạn.
2. Ở **Tự thử yêu cầu**, chọn adam, B1, chứng thư đúng người và hành động **Xem thông tin mô tả tài liệu**.
3. Giữ nguyên người/tài liệu, đổi sang **Tải nội dung tài liệu**.
4. Quay lại Tài liệu, chọn Người thực hiện adam, thử sửa tên và lưu.
5. Cấp lại quyền cho adam trong phần quyền; thử tải/sửa lại.
6. Để minh họa hết hạn, cấp quyền thời hạn 1 phút rồi đợi hết. Thu hồi các grant khác còn hiệu lực của cùng người/tài liệu trước ca này; nếu còn một grant hợp lệ, yêu cầu vẫn có thể được phép. Làm mới và thử lại.

| Trạng thái | Kỳ vọng B1 |
|---|---|
| Trưởng phòng cùng phòng, không có grant | Metadata `200 ALLOW` |
| Không có grant tải/sửa còn hạn | Download và sửa bị chặn, thường `403 RESTRICTED_GRANT` |
| Grant mới còn hạn | Tải/sửa được phép khi điều kiện khác đúng |
| Tất cả grant phù hợp đã hết hạn/thu hồi | Tải/sửa bị chặn lại |

Thử chọn brian sửa/tải tài liệu phòng A để thấy vai trò trưởng phòng không vượt phạm vi phòng ban. Hạn lưu giữ và bảo toàn chỉ tra cứu ở màn hình này; quyền tải không cho thay đổi hai thuộc tính đó.

**Đối chiếu:** 3.3 về ràng buộc grant và kiểm tra hiện tại; 3.4 về tách quyền vòng đời; 4.4 về thu hồi/hết hạn. Sửa ở đây là sửa thông tin, không thay thế nội dung tệp đã lưu.

## 5. So sánh B0 và B1 trên cùng yêu cầu đọc

**Điều kiện:** A-C02 còn ở trạng thái mẫu, thuộc anna và nhãn Mật; alice hoạt động, ở phòng A, thiết bị hợp lệ.

1. Mở **Tự thử yêu cầu**, chọn alice, **Xem thông tin mô tả tài liệu**, A-C02.
2. Mở **Thay thiết bị, chính sách đối chứng hoặc header**, chọn B1, gửi.
3. Chỉ đổi chính sách sang B0, gửi lại; giữ nguyên người, tài liệu, hành động và thiết bị.
4. Mở **Xem HTTP, Request ID và JSON** để đối chiếu hai phản hồi.

**Kỳ vọng:** B1 `403 OWNER_OR_LABEL`; B0 `200 ALLOW`.

Điều kiện nhãn/chủ sở hữu của B1 thu hẹp quyền theo nhu cầu nghiệp vụ. B0 do nhóm tạo làm đối chứng quyền đọc tĩnh; hai chế độ dùng cùng TLS, chứng thư, mã hóa và audit. Chọn B0 ở Tự thử yêu cầu không đổi chế độ của màn hình sửa: API sửa luôn kiểm tra quyền tải theo B1. Việc không vượt quyền sửa qua đường B0 đã có trong [kiểm tra bản cập nhật](bang_chung/20261021-quyen-han-che.md).

**Đối chiếu:** 3.3 về chính sách đọc; 4.2–4.4 về phương pháp đối chứng và kết quả. Kết quả này không phải phép đo trên Google hoặc Microsoft.

## 6. Chứng thư thiết bị phải đúng người

**Điều kiện:** alice và A-I01 còn trạng thái mẫu hợp lệ.

1. Tại **Tự thử yêu cầu**, chọn alice, **Tải nội dung tài liệu**, A-I01, B1.
2. Giữ mặc định **Thiết bị của người đang thử**, gửi: dự kiến `200 ALLOW`.
3. Trong phần nâng cao, đổi **Thiết bị gửi yêu cầu — chứng thư** thành thiết bị của anna, gửi: dự kiến `403 DEVICE_MISMATCH`.
4. Trả về mặc định trước ca tiếp theo.

Có thể thay bằng bài **Bắt đầu có hướng dẫn → Có phê duyệt nhưng thiết bị không phù hợp** để xem thêm grant hợp lệ nhưng rủi ro cao vẫn bị chặn. Bài sẽ chuẩn bị trạng thái, có thể tạo grant tạm rồi thu hồi khi kết thúc; đọc phần thay đổi trước khi chạy.

**Đối chiếu:** 3.3 về liên kết danh tính/chứng thư và tín hiệu; 4.3 về lỗi chứng thư; 4.4 về yêu cầu bảo vệ.

## 7. Nhật ký chứng minh yêu cầu nào đã bị chặn

1. Trong ca 5 hoặc 6, ghi lại Request ID của một phản hồi bị chặn.
2. Mở **Nhật ký và cảnh báo**, nhập Request ID vào ô lọc. Đối chiếu người, tài nguyên/hành động, quyết định và lý do.
3. Muốn kiểm tra quyền nghiệp vụ, quay lại **Tự thử yêu cầu**: chọn auditor, **Đọc nhật ký bằng quyền người dùng**, chứng thư đúng người; dự kiến `200 ALLOW`. Chọn alice cho cùng hành động: dự kiến `403 ROLE`.
4. Để minh họa cảnh báo, dùng bài **Bắt đầu có hướng dẫn → Ai ghi nhận các lần truy cập bị chặn?**. Bài gửi năm yêu cầu thật và đối chiếu ngưỡng cảnh báo; nhật ký và cảnh báo phát sinh được giữ lại.

Cảnh báo không tự thu hồi quyền. Một yêu cầu có thể tạo nhiều sự kiện nên số dòng audit không bằng số HTTP request. Danh sách cảnh báo rỗng với HTTP 200 là kết quả hợp lệ.

**Đối chiếu:** 3.4 về vận hành/audit; 4.4 về bằng chứng. Console đọc nhật ký bằng đặc quyền người vận hành; không dùng việc bảng này hiển thị dữ liệu để kết luận mọi nhân viên có quyền đọc audit.

## 8. Kết thúc và lưu bằng chứng

- Giữ ảnh phản hồi và Request ID; xuất JSON ở các bài có hỗ trợ. Không chụp mật khẩu, token hoặc private key.
- Ghi rõ tài liệu, người, thiết bị, chế độ và trạng thái trước/sau. Không dùng lại số đo lịch sử như kết quả vừa chạy.
- Các bài hướng dẫn hoàn tác thuộc tính tạm theo thiết kế; đọc bước khôi phục cuối. Nếu có lỗi khôi phục, xử lý trước bài tiếp theo.
- Không cần chạy bộ chuẩn để hoàn tất các ca trên. Chỉ chạy **Kiểm chứng tự động** khi chủ động chấp nhận reset dữ liệu.
- Nếu muốn diễn thêm vòng đời hoặc phục hồi, dùng bài tương ứng ở **Bắt đầu có hướng dẫn**. Phục hồi dựng DB/KMS cô lập, có thể tạm dừng API lúc sao lưu và tiêu thụ thêm tài nguyên; không thay hệ thống chính.
- Khi không dùng web, chạy `Stop-Demo.ps1` để dừng container và môi trường WSL, giữ dữ liệu.

Báo cáo hiện hành phân biệt lượt chuẩn 19/10/2026 với kiểm tra bổ sung 21/10/2026. Ánh xạ ở đây theo số mục, không dựa vào số trang để tránh sai khi dàn trang lại.

