# Chỉ mục bằng chứng kiểm chứng

Cập nhật chỉ mục ngày 25/10/2026. Các kết quả bên dưới được giữ theo ngày và phạm vi thực hiện; đây không phải kết quả vừa chạy ngày cập nhật tài liệu. [Mục lục](muc_luc.md).

## 1. Chức năng web hiện hành, kiểm tra ngày 21/10

Bản bổ sung quyền Hạn chế đã đạt **39/39 kiểm tra tích hợp**: thêm trực tiếp có phê duyệt; tải và sửa; sai vai trò/phòng ban; thu hồi/hết hạn; phê duyệt sai người, sai mục đích hoặc đã dùng; lỗi audit hủy giao dịch; nâng nhãn và giới hạn lưu giữ. OPA có 31 kiểm thử đạt; 18 kiểm thử Python hồi quy được chạy riêng. Không cộng các số này vào bộ chuẩn ngày 19/10.

- [Kết quả 39 kiểm tra](../results/restricted-management-20261021/validation.json).
- [Phạm vi triển khai và kiểm tra](bang_chung/20261021-quyen-han-che.md).
- [Mã kiểm tra tích hợp bổ sung](../results/restricted-management-20261021/validate_restricted.py).
- [Giao diện cấp quyền](../results/restricted-management-20261021/restricted-permissions.png), [từ chối sửa sau thu hồi](../results/restricted-management-20261021/restricted-revoked.png).
- [Đối chiếu mã đã triển khai](../results/restricted-management-20261021/deployed-source-check.json).
- [Thay đổi báo cáo](../results/restricted-management-20261021/report-changes.json), [kiểm tra dàn trang](../results/restricted-management-20261021/report-qa.json).

Bản quản lý tài liệu/nhân viên và giao diện hướng dẫn trước đó có bằng chứng riêng tại [management-ui-20261021](bang_chung/20261021-quan-ly-web.md) và [guided-ui-20261021](bang_chung/20261021-huong-dan-web.md). Chúng mô tả thời điểm tương ứng, có thể có chức năng đã được thay thế ở bản Hạn chế mới.

## 2. Lượt chuẩn ngày 19/10/2026

Lượt `run-20261019-084335-960c43` ghi nhận **127/127 mục tổng hợp đạt** trên `business-v1`: 20 tài liệu TXT UTF-8, gồm 10 nội bộ, 6 mật, 4 hạn chế. 125 mục tích hợp gồm 40 oracle và 85 mục trạng thái/lỗi/vận hành. Hai mục tổng hợp còn lại xác nhận 31 kiểm thử Rego và 32 kiểm thử Python của lượt đó. Không quan sát cho phép sai trong 73 ca cần từ chối hoặc từ chối sai trong 42 ca cần cho phép; các kiểm chứng lưu trữ/phục hồi dùng tiêu chí riêng.

- [JSON](../results/run-20261019-084335-960c43/results.json), [CSV](../results/run-20261019-084335-960c43/results.csv), [HTML](../results/run-20261019-084335-960c43/report.html).
- [Kiểm thử Rego](../results/run-20261019-084335-960c43/opa-tests.txt), [kiểm thử Python](../results/run-20261019-084335-960c43/identity-tests.txt).
- [Môi trường trước](../results/capture-20261019-final/environment.before.json), [môi trường sau và hash kết quả](../results/run-20261019-084335-960c43/environment.after.json).
- [Catalog và SHA-256 dữ liệu](../fixtures/dataset-manifest.json).

Ảnh của giao diện tại thời điểm này:

- [Quy chuẩn phân loại](../results/revision-20261019/screenshots/01-data-classification.png).
- [Tổng hợp kết quả và T15](../results/revision-20261019/screenshots/02-full-suite-and-t15.png).
- [B1 chặn người không sở hữu](../results/revision-20261019/screenshots/03-b1-owner-denied.png), [B0 cho phép cùng tài liệu](../results/revision-20261019/screenshots/04-b0-same-document-allowed.png).
- [Quyền hiện tại bị thu hồi](../results/revision-20261019/screenshots/05-current-right-revoked.png), [chứng thư sai người](../results/revision-20261019/screenshots/06-device-binding-denied.png), [OPA dừng](../results/revision-20261019/screenshots/07-opa-outage-denied.png).

## 3. Cách dùng kết quả

Đối chiếu ngày, tập dữ liệu, mã nguồn và phạm vi từng lượt trước khi sử dụng số liệu. Các thư mục `before/`, bản nháp báo cáo và benchmark trước ngày 19/10 là lịch sử; không phải hướng dẫn web hiện hành hoặc bằng chứng hiệu năng của bản mới.

Kết quả chỉ áp dụng cho dữ liệu tổng hợp, tín hiệu thiết bị giả lập và cấu hình một máy. B0 là đối chứng do nhóm xây dựng; phục hồi là diễn tập DB/KMS cô lập. Không suy rộng thành bảo đảm doanh nghiệp, khả năng thu hồi bản rõ đã cấp hoặc kết luận tải đồng thời.

Đọc tiếp: [hướng dẫn web](huong_dan_nhanh.md), [ma trận kiểm chứng](test-matrix.md), [quy trình tái lập](reproduction.md), [đánh giá phạm vi](verification-review.md).
