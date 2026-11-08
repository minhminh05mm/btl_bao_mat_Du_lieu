# Mục lục tài liệu

Tài liệu hiện hành mô tả bên quản lý tài khoản, bộ điều phối và kho tài liệu. Tên thành phần, ba cách kiểm tra và thao tác sử dụng thống nhất với giao diện web và PowerPoint hiện tại.

## Bộ tài liệu hiện hành

| Tài liệu | Công dụng |
|---|---|
| [Báo cáo chính](bao_cao/BaoCao_BMDL_Nhom03_ZeroTrust_DaSua.docx) | Nghiên cứu đầy đủ 38 trang, kiến trúc tham chiếu, thiết kế, luồng xử lý và kết quả |
| [Tóm tắt báo cáo 10 trang](bao_cao/BaoCao_TomTat_10Trang_TheoChuong.docx) | Bốn chương rút gọn, 7 hình, 9 bảng, kiến trúc và luồng truy cập 10 bước |
| [PowerPoint 8 slide](../trinh_chieu/Slide_ThuyetTrinh_BMDL_Nhom03_PhongCachSteam.pptx) | Thuyết trình bài toán, kiến trúc, luồng và demo |
| [Script 10 phút](script_thuyet_trinh_10_phut.md) | Lời thuyết trình và thao tác tương ứng với slide |
| [Ảnh web ngày 07/11/2026](../results/report-20261107-ui/) | Minh họa giao diện và các phản hồi hiện hành |

Tải Word và PowerPoint về máy để đọc. Bản tóm tắt 10 trang đã được cập nhật theo báo cáo chính và cách gọi hiện hành.

## Đọc nhanh để hiểu và trình bày

1. Đọc phần tóm tắt trong [Kiến thức nền](kien_thuc_nen.md) để hiểu mục đích bài.
2. Xem [Kiến trúc](architecture.md) để theo dõi một yêu cầu từ đăng nhập đến trả kết quả.
3. Làm theo [Hướng dẫn nhanh](huong_dan_nhanh.md) để thử khóa tài khoản, mất thông báo và mất kết nối.
4. Đọc [Tham chiếu Microsoft và Google](ke_thua.md) để giải thích căn cứ và phần tích hợp.
5. Dùng [Script 10 phút](script_thuyet_trinh_10_phut.md) cùng [PowerPoint 8 slide](../trinh_chieu/Slide_ThuyetTrinh_BMDL_Nhom03_PhongCachSteam.pptx).

## Tra cứu theo nhu cầu

| Cần tìm | Tài liệu |
|---|---|
| Bật, tắt, gửi yêu cầu và sửa lỗi thường gặp | [Hướng dẫn nhanh](huong_dan_nhanh.md) |
| Mục đích, kiến thức nền và công nghệ | [Kiến thức nền](kien_thuc_nen.md) |
| Sơ đồ, tạo phiên, tải tài liệu và thu hồi | [Kiến trúc](architecture.md) |
| Căn cứ tham chiếu và cơ chế tích hợp | [Tham chiếu Microsoft và Google](ke_thua.md) |
| Ý nghĩa các trường và cách gọi trên web | [Giải thích cách gọi và tính năng](giai_thich_ky_hieu.md) |
| Vai trò, nhãn và căn cứ phân loại 20 tài liệu mẫu | [Phân loại dữ liệu](data-classification.md) |
| Lý do chọn từng cơ chế và đánh đổi | [Quyết định thiết kế](design-approved.md) |
| Ai tin ai, kênh truyền, đầu vào và lỗi | [Quy tắc phối hợp giữa các thành phần](implementation-contract.md) |
| Trình diễn từng tình huống và liên hệ báo cáo | [Kịch bản trình diễn](huong-dan-trinh-dien-va-doi-chieu-bao-cao.md) |
| Điều kiện đạt của 19 tình huống | [Ma trận kiểm tra](test-matrix.md) |
| Mở kết quả, ảnh và bằng chứng đã lưu | [Kết quả kiểm tra](ket_qua_kiem_chung.md) |
| Đọc bằng chứng và giới hạn kết luận | [Rà soát bằng chứng](verification-review.md) |
| Phiên bản công nghệ và môi trường | [Danh mục phần mềm](software-inventory.md) |
| Cài trên máy khác, chạy kiểm tra và tái lập | [Tái lập môi trường](reproduction.md) |

Tên tệp `giai_thich_ky_hieu.md` được giữ để các liên kết cũ tiếp tục mở được. Nội dung giải thích bằng tên đầy đủ đang dùng trên web.

## Đối chiếu mã nguồn

| Nội dung | Tệp chính |
|---|---|
| Trạng thái tài khoản và thiết bị của đối tác | [Dịch vụ quản lý tài khoản](../federation/partner.py) |
| Phiên, thông báo thay đổi và kiểm tra lại | [Bộ điều phối](../federation/coordinator.py) |
| Kết nối kho với bộ điều phối | [Thành phần kết nối tại kho](../app/federated.py) |
| Kiểm tra yêu cầu và quy tắc quyền | [Kiểm soát tại kho](../app/security.py), [quy tắc OPA](../policies/bmdl.rego) |
| Tên và giải thích trên web | [Cách gọi dùng chung](../lab/static/demo-language.js) |
| Bộ kiểm tra sử dụng thực tế | [Các tình huống kiểm tra](../federation/verify.py) |
