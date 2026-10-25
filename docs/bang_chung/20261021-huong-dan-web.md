# Kiểm tra bản giao diện có hướng dẫn

Biên bản lịch sử ngày 21/10/2026, chuyển vị trí tài liệu ngày 25/10/2026. Các mô tả giao diện trong biên bản phản ánh đúng thời điểm đó. [Mục lục](../muc_luc.md) · [Tệp kết quả và ảnh gốc](../../results/guided-ui-20261021/).

Ngày kiểm tra: 21/10/2026. Địa chỉ: http://localhost:8088.

## Thay đổi đã triển khai

- Trang đầu gồm 7 bài thử có điều kiện, kết quả mong đợi và từng bước thực thi.
- Tách bước chuẩn bị của người vận hành khỏi yêu cầu qua gateway.
- Giải thích phản hồi bằng tiếng Việt; HTTP, JSON, Request ID và hash có thể mở rộng.
- Giữ phần tự gửi yêu cầu, chứng thư, B0, kiểm chứng tự động và điều khiển lab.
- Cấp phê duyệt tạm thời có ô chọn người nhận, tài liệu và thời gian.
- Gắn nhãn tài khoản hiện đang bị thu hồi quyền.
- Giữ lịch sử bài thử; tải lại trang theo dõi được đúng bài đang chạy.
- Có bằng chứng tải về. Bài thử khôi phục các thuộc tính đã thay đổi và giữ audit, cảnh báo, snapshot cùng bộ đếm phiên bản.

## Kết quả thực thi

| Bài | Kết quả | Số bước ghi nhận | Thuộc tính thử nghiệm được khôi phục |
|---|---|---:|---|
| Quyền đọc theo chủ sở hữu | Đạt, gồm đối chứng B0 | 5 | Có |
| Thu hồi quyền với cùng token | Đạt, gồm đối chứng B0 | 6 | Có |
| Grant, chứng thư và rủi ro thiết bị | Đạt, gồm đối chứng B0 | 8 | Có |
| Mã hóa và dừng OpenBao | Đạt | 8 | Có |
| Audit và cảnh báo | Đạt, tìm đủ 5 Request ID | 11 | Có |
| Lưu giữ, legal hold và xóa logic | Đạt | 7 | Có |
| Sao lưu, phục hồi và đối chiếu thu hồi | Đạt, xác minh 20 tài liệu | 6 | Có |

Các bước bao gồm chuẩn bị, yêu cầu, kiểm tra và hoàn tác; số bước không đồng nghĩa số HTTP request. Tệp `validation-summary.json` chứa mã tác vụ và thời gian từng bài.

Đã chạy lại bài quyền đọc và bài phục hồi qua giao diện. Khi tải lại trang lúc phục hồi đang chạy, trang tiếp tục theo dõi đúng bài và hoàn thành thành công. Bài phục hồi dùng PostgreSQL/OpenBao cô lập, không thay thế hệ thống chính và đã dọn tài nguyên tạm.

## Kiểm tra giao diện và đầu vào

- Nhân viên Anna tải A-C01: bị chặn theo chủ sở hữu; giải thích xuất hiện trong kết quả.
- Trưởng phòng Adam tải cùng tài liệu: được cấp nội dung và hiện nút lưu file.
- Auditor đọc audit: thành công và hiện số sự kiện.
- Secadmin đọc cảnh báo: thành công và hiện số cảnh báo.
- Secadmin gọi GET /me tùy chỉnh: hiện đúng danh tính đã xác minh.
- Grant mới có ô chọn; trước khi áp dụng có mô tả thay đổi dự kiến. Không gửi thêm grant từ màn hình này trong phép kiểm tra giao diện.
- JSON phản hồi mặc định thu gọn; không đưa token vào bằng chứng.
- `compare` sai kiểu: HTTP 422; bài không tồn tại: HTTP 404; thiếu CSRF với phiên cookie mới: HTTP 403.
- Kiểm tra bố cục ở chiều rộng 1440 và cửa sổ gốc 639; trang không tràn ngang. Đã trả kích thước cửa sổ về mặc định.
- Không ghi nhận lỗi JavaScript trong các thao tác đã kiểm tra.

## Trạng thái và phạm vi kiểm chứng

Đối chiếu trước/sau: giữ 8 danh tính, 20 tài liệu và các thuộc tính quyền/thiết bị/nhãn/thời hạn/trạng thái xóa. Grant bài tạo được thu hồi. Dấu thời gian tín hiệu có thể tăng do tự làm mới; dấu thời gian cập nhật nghiệp vụ và phiên bản được giữ để phản ánh lịch sử thao tác. Alice bị thu hồi quyền trước khi kiểm tra và được giữ nguyên trạng thái này sau bài.

Không chạy lại toàn bộ bộ chuẩn có reset dữ liệu trong lần sửa giao diện này. Kết quả 7/7 ở trên chỉ áp dụng cho các bài hướng dẫn đã thực thi. Các chính sách nghiệp vụ, thành phần xác thực, mã hóa và Compose không được thay đổi trong lần sửa này.

Mã nguồn cũ được lưu tại `before/`. Kết quả bài riêng nằm ở `results/lesson-.../results.json`; lịch sử tác vụ ở `runtime/lab-results/`.
