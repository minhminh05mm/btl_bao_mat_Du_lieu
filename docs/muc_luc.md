# Mục lục và thứ tự đọc tài liệu

Cập nhật ngày 25/10/2026. Toàn bộ hướng dẫn và biên bản cần đọc được tập trung trong `docs/`. Bắt đầu từ kiến thức nền, sau đó sử dụng web và đối chiếu kiến trúc. [Trang đầu dự án](../README.md).

## 1. Đọc theo thứ tự nào để hiểu bài?

| Bước | Đọc ở đâu? | Đọc để trả lời được |
|---|---|---|
| 1 | [Kiến thức nền](kien_thuc_nen.md), phần tóm tắt trước, phần chi tiết sau | Bài này làm gì, bảo vệ cái gì, các thành phần phối hợp ra sao? |
| 2 | [Hướng dẫn nhanh](huong_dan_nhanh.md) | Bật web, thêm tài liệu/nhân viên, cấp và thu hồi quyền như thế nào? |
| 3 | [Kiến trúc nhóm](architecture.md) | Một yêu cầu đi qua đâu, ai xác minh, ai đánh giá và ai thực thi? |
| 4 | [Kế thừa Google/Microsoft](ke_thua.md) | Nhóm lấy ý tưởng nào, áp dụng vào đâu, đóng góp và giới hạn nằm ở đâu? |
| 5 | [Dữ liệu và phân loại](data-classification.md) | Vì sao một tài liệu là Nội bộ, Mật hoặc Hạn chế; ai được dùng? |
| 6 | [Kết quả kiểm chứng](ket_qua_kiem_chung.md) rồi [giới hạn bằng chứng](verification-review.md) | Đã thử những gì, kết quả chứng minh được đến đâu? |

Không cần đọc mã nguồn hoặc hợp đồng API trước khi nắm được sáu bước trên. Khi gặp mã như B0, B1, A-C02, grant hoặc TTL, tra [Giải thích ký hiệu](giai_thich_ky_hieu.md).

## 2. Chọn tài liệu theo việc đang cần làm

### 2.1. Hiểu bài và chuẩn bị vấn đáp

| Tài liệu | Nội dung chính |
|---|---|
| [kien_thuc_nen.md](kien_thuc_nen.md) | Tóm tắt bài; kiến thức nền; tech stack; kiến trúc; B0/B1; ví dụ xuyên suốt; mục đích và giới hạn |
| [giai_thich_ky_hieu.md](giai_thich_ky_hieu.md) | Bảng tra mã tài liệu, mã ca thử, vai trò, nhãn, trường dữ liệu, HTTP và thuật ngữ |
| [ke_thua.md](ke_thua.md) | Ánh xạ BeyondCorp/Microsoft vào hệ thống; vì sao dùng hai nguồn; điều kiện để gọi một thay đổi là cải tiến |
| [data-classification.md](data-classification.md) | Bộ 20 tài liệu tổng hợp, tiêu chí ba nhãn và quan hệ giữa nội dung với quyền |

### 2.2. Dùng web và thuyết trình

| Tài liệu | Nội dung chính |
|---|---|
| [huong_dan_nhanh.md](huong_dan_nhanh.md) | Bật/tắt, tài khoản, biểu mẫu, quyền Hạn chế, cách đọc kết quả và xử lý lỗi |
| [huong-dan-trinh-dien-va-doi-chieu-bao-cao.md](huong-dan-trinh-dien-va-doi-chieu-bao-cao.md) | Chuẩn bị ca trình diễn; thao tác; điều kiện và kết quả kỳ vọng; liên hệ các mục báo cáo |

Muốn trình diễn nhanh: chọn tài liệu Hạn chế có đúng một grant còn hạn cho trưởng phòng cùng phòng → tải thành công → thu hồi grant → yêu cầu tải/sửa mới bị chặn → cấp lại và thử lại. Hướng dẫn trình diễn giải thích cả trường hợp còn nhiều grant.

### 2.3. Hiểu cách thiết kế và hiện thực

| Tài liệu | Nội dung chính |
|---|---|
| [architecture.md](architecture.md) | Sơ đồ, đường truy cập, ranh giới tin cậy, nguồn trạng thái, mật mã, audit và phục hồi |
| [design-approved.md](design-approved.md) | Quyết định thiết kế hiện hành, lý do và đánh đổi |
| [implementation-contract.md](implementation-contract.md) | API, cấu trúc yêu cầu, điều kiện thực thi, giao dịch và hợp đồng giữa các thành phần |
| [software-inventory.md](software-inventory.md) | Phiên bản đã ghi nhận, nguồn cấu hình, giấy phép và giới hạn của việc kiểm kê |

Chỉ mở `implementation-contract.md` khi cần tra endpoint hoặc đối chiếu triển khai. Danh sách phiên bản đầy đủ được duy trì ở `software-inventory.md` để tránh nhiều bản sao khác nhau.

### 2.4. Đánh giá và tái lập thực nghiệm

| Tài liệu | Nội dung chính |
|---|---|
| [test-matrix.md](test-matrix.md) | Nhóm ca thử, tầng kiểm tra, oracle và bộ bổ sung cho web |
| [ket_qua_kiem_chung.md](ket_qua_kiem_chung.md) | Điểm vào kết quả thực tế theo ngày; liên kết JSON, log, ảnh và biên bản |
| [verification-review.md](verification-review.md) | Cách diễn giải kết quả, giới hạn đối chứng, giả lập, lỗi phụ thuộc và phục hồi |
| [reproduction.md](reproduction.md) | Cách ghi nhận môi trường và chạy lại đúng phạm vi; tác động reset và thao tác có trạng thái |

## 3. Nếu giảng viên hỏi thì tra ở đâu?

| Câu hỏi | Nơi đọc |
|---|---|
| Mục đích bài và đóng góp của nhóm là gì? | `kien_thuc_nen.md` và `design-approved.md` |
| Vì sao đăng nhập đúng vẫn bị từ chối? | `kien_thuc_nen.md`, phần xác thực/phân quyền và ví dụ yêu cầu |
| Vì sao dùng cả Google và Microsoft? | `ke_thua.md`; phần tóm tắt trong `kien_thuc_nen.md` |
| B0/B1 dùng để làm gì, so sánh chứng minh gì? | `kien_thuc_nen.md`, `giai_thich_ky_hieu.md`, `verification-review.md` |
| Vì sao tài liệu mang nhãn Hạn chế? | `data-classification.md` |
| Trưởng phòng hoặc quản trị an toàn có được đọc mọi tài liệu không? | `giai_thich_ky_hieu.md` và `architecture.md` |
| Máy bị nhiễm mã độc thì demo có phát hiện được không? | `kien_thuc_nen.md`, phần thực thi thật và dữ liệu giả lập |
| Hệ thống có hơn một chuỗi if/else ở điểm nào? | `kien_thuc_nen.md`, phần kiến trúc và phân chia trách nhiệm; `architecture.md` |
| Đã kiểm tra được gì, số 127 và 39 nghĩa là gì? | `ket_qua_kiem_chung.md` và `verification-review.md` |
| Môi trường và phiên bản cụ thể là gì? | `software-inventory.md` và manifest được liên kết trong đó |

## 4. Biên bản chi tiết và kết quả gốc

Các biên bản sau được giữ theo thời điểm để truy vết, không dùng thay hướng dẫn hiện hành:

- [Cập nhật quyền Hạn chế ngày 21/10](bang_chung/20261021-quyen-han-che.md).
- [Cập nhật giao diện quản lý ngày 21/10](bang_chung/20261021-quan-ly-web.md).
- [Cập nhật luồng hướng dẫn ngày 21/10](bang_chung/20261021-huong-dan-web.md).

JSON, CSV, HTML, ảnh, log và bản môi trường gốc vẫn nằm trong [results/](../results/); các tệp này là bằng chứng thực nghiệm. Ngày sửa một tài liệu hướng dẫn không phải ngày chạy lại kiểm thử.

`scripts/summarize_results.py` chỉ tạo bản tổng hợp tự động theo lượt trong `docs/bang_chung/`. Điểm vào kết quả đã được phân loại theo phạm vi là `ket_qua_kiem_chung.md`; bản tự sinh không thay thế nó.

## 5. Quy ước sau khi sắp xếp

- `README.md` ở thư mục gốc là điểm mở đầu và cách bật/tắt nhanh; `docs/muc_luc.md` là mục lục tài liệu.
- Mỗi hướng dẫn hiện hành có một vị trí trong `docs/`. Các đường dẫn cũ của ba file hướng dẫn ở thư mục gốc đã được chuyển vào đây.
- Trang chỉ dẫn trùng và các bản Markdown nháp/trước sửa được bỏ khỏi danh sách file đang dùng. Bản trước sắp xếp được lưu trong [gói lưu trữ Markdown](luu_tru/markdown-truoc-20261025.zip), chỉ mở khi cần đối chiếu lịch sử.
- Khi cập nhật chức năng, sửa tài liệu có trách nhiệm tương ứng và cập nhật mục lục nếu thêm hoặc bỏ file. Kết quả thực nghiệm cũ giữ nguyên nội dung và ngày của lượt chạy.
