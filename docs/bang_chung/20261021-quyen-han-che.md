# Kết quả cập nhật quyền tài liệu Hạn chế

Biên bản lịch sử ngày 21/10/2026, chuyển vị trí tài liệu ngày 25/10/2026. Các mô tả giao diện trong biên bản phản ánh đúng thời điểm đó. [Mục lục](../muc_luc.md) · [Tệp kết quả và ảnh gốc](../../results/restricted-management-20261021/).

Ngày 21/10/2026. Phạm vi: nguyên mẫu cục bộ, dữ liệu và tài khoản tổng hợp.

## Nguyên nhân và thay đổi

API thêm cũ chỉ nhận Nội bộ/Mật. Màn hình quản lý từng thực hiện thêm Mật rồi nâng lên Hạn chế bằng tài khoản quản trị được chọn tự động; người sở hữu chưa mặc nhiên có grant tải. Màn hình sửa cũ dùng đặc quyền người vận hành để ghi metadata, chưa thực thi quyền tải của người sửa.

Đã bổ sung phê duyệt tạo/nâng nhãn Hạn chế có người nhận, phòng ban, tài liệu, phiên bản, mục đích và thời hạn. Thêm trực tiếp lưu nhãn Hạn chế, grant ban đầu và trạng thái đã dùng phê duyệt trong cùng giao dịch. Phê duyệt tạo chỉ sử dụng thành công một lần; grant tải có thể phục vụ nhiều yêu cầu khi còn hiệu lực.

API sửa kiểm tra quyền tải hiện tại theo B1 trước thay đổi. Xem metadata chưa đủ để sửa. Không dùng B0 để bỏ qua kiểm tra khi sửa; không cho hạ nhãn hoặc dùng quyền nội dung để sửa lưu giữ/bảo toàn. Nâng nhãn rút ngắn lưu giữ theo mức mới và cấp grant đúng phiên bản.

Giao diện có Người thực hiện, Người phê duyệt, thời hạn, bảng quyền cùng cấp/thu hồi. Khi có phiên Keycloak, phía máy chủ lấy danh tính phiên cho thao tác thêm/sửa. Console vẫn là công cụ người vận hành tin cậy; thao tác phê duyệt bằng tài khoản quản trị được chọn là yêu cầu riêng, chưa phải cổng nhiều người dùng với hàng đợi duyệt độc lập.

## Kiểm tra

- `validation.json`: 39/39 kiểm tra tích hợp đạt trên JWT/mTLS/gateway/API/OPA/PostgreSQL/OpenBao thật.
- OPA: 31/31 kiểm thử chính sách đạt.
- Python: 18 kiểm thử hồi quy xác thực/fixture đạt; một cảnh báo từ thư viện kiểm thử, không có lỗi kiểm thử.
- Giao diện: thêm bằng nhân viên bị chặn đúng ô; thiếu người phê duyệt báo đúng ô; trưởng phòng thêm thành công; sửa khi có quyền thành công; thu hồi làm sửa bị chặn; cấp lại khôi phục sửa. Không ghi nhận lỗi JavaScript trong các thao tác này.
- Ảnh giao diện: `restricted-permissions.png` và `restricted-revoked.png`.
- Trường hợp lỗi audit không tạo tài liệu dở dang. Phê duyệt sai người, hết hạn, đã dùng hoặc sai mục đích bị từ chối.
- Không chạy reset dữ liệu thật. Tài liệu thử được giữ lại. Các lượt đầu trong quá trình sửa có bản ghi riêng; chỉ tệp validation cuối đại diện bản cuối.

## Hướng dẫn và báo cáo

Đã thay nội dung hướng dẫn nhanh theo giao diện mới. Báo cáo cập nhật quy chuẩn tạo Hạn chế, ma trận vai trò, quan hệ quyền tải/sửa, phân biệt phê duyệt tạo với grant sử dụng và kết quả ngày 21/10. Kiến trúc lõi giữ nguyên các thành phần; cập nhật nằm ở luồng kiểm soát và nguồn trạng thái. Kết quả bổ sung không cộng vào lượt 127 mục ngày 19/10.

Báo cáo được cập nhật trường Word và kiểm tra dàn trang: 39 trang; một mục lục, hai danh mục riêng; mọi bảng nằm trên một trang. Bản trước sửa lưu trong `before/`. Xem `report-qa.json` và `report-changes.json` để đối chiếu.
