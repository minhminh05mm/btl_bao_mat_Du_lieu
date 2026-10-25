# Ma trận kiểm chứng theo chức năng hiện hành

Cập nhật tài liệu: 25/10/2026. [Mục lục tài liệu](muc_luc.md) · [Tái lập](reproduction.md) · [Đánh giá bằng chứng](verification-review.md).

## 1. Các tầng kiểm tra

| Tầng | Nguồn | Phạm vi |
|---|---|---|
| Quy tắc | [bmdl_test.rego](../policies/bmdl_test.rego) | Hàm quyết định OPA thật: quyền, grant, biên TTL, B0/B1 |
| Xác thực và hợp đồng kiểm thử | [tests/](../tests) | JWT verifier dùng RSA/JWKS thử nghiệm; cấu trúc oracle, runner, fixture và hash |
| Bộ tích hợp chuẩn | [scenarios.py](../tests/scenarios.py), [cases.json](../fixtures/cases.json) | Yêu cầu qua JWT, mTLS, gateway, API, OPA, PostgreSQL và OpenBao thật |
| Cập nhật thêm/sửa Hạn chế | [validate_restricted.py](../results/restricted-management-20261021/validate_restricted.py) | API nghiệp vụ và màn hình quản lý: phê duyệt tạo/nâng nhãn, quyền tải/sửa, cấp/thu hồi/hết hạn và giao dịch |
| Thao tác theo từng bước | [lessons.py](../lab/lessons.py) | Bài hướng dẫn trên web; xuất bước và bằng chứng theo lượt |

Kỳ vọng phải được chốt từ chính sách trước khi chạy; không lấy phản hồi quan sát làm đáp án. Một lỗi dịch vụ HTTP 503 không thay cho denial 403 được kỳ vọng. Kiểm thử đơn vị không thay bằng chứng đầu cuối; một mục tổng hợp chứa nhiều test không được cộng hai lần.

## 2. Oracle và case tự soạn

Oracle chuẩn có 40 case, gồm 20 allow và 20 deny. Tệp có `schema_version` và mảng `cases`; mỗi case gồm `id`, `group`, `name`, `username`, `method`, `path`, `mode`, `expected`, cùng `device`, `json`, `headers`, `checks`, `setup` khi cần.

`expected.allow`, `expected.statuses` và `expected.reason` xác định kết quả cần đối chiếu. `checks` có thể kiểm tra tập ID hoặc SHA-256; `setup` chuẩn bị principal/device/document/grant. Trình sửa JSON nằm tại Kiểm chứng tự động. Không chạy lại `tests/make_oracle.py` sau khi sửa case vì công cụ này tái tạo bộ gốc.

B0 chạy cùng kỳ vọng bảo vệ B1 để quan sát chênh lệch; không sửa expected thành allow cho các phép đối chứng cố ý yếu. Sai tập metadata phải được báo riêng với false allow/deny boolean. B0 chỉ đối chứng quyền đọc; không được bỏ qua quyền B1 khi sửa tài liệu.

## 3. Ma trận bộ chuẩn

| Nhóm | Phạm vi và bằng chứng chính |
|---|---|
| O-A01–O-A20, O-D01–O-D20 | Quyền tài liệu, danh sách, grant, vai trò, thiết bị, vòng đời và upload Nội bộ/Mật |
| T01–T06 | Nội bộ/mật, owner, trưởng phòng, sai phòng; sở hữu không vượt nhãn Hạn chế; tải đúng hash |
| T07–T09 | Grant đúng người/tài liệu/phiên bản/hành động/thời hạn, không tự cấp; tách nghiệp vụ/kiểm toán/quản trị |
| T10–T12 | JWT bị sửa/thiếu, mTLS sai/thiếu, giả header, tự nâng quyền; claim có chữ ký hợp lệ được kiểm tra riêng bằng verifier |
| T13–T16 | Thiết bị/risk/TTL, thu hồi khi JWT còn hạn, nâng nhãn và đối chứng B0 |
| T17–T18 | OPA dừng thật, lỗi phản hồi/registry mô phỏng, audit lỗi; không trả bản rõ hoặc commit upload khi audit thất bại |
| T19–T20 | Retention, legal hold, xóa logic/tombstone; năm deny trong 60 giây, cảnh báo và phản ứng vận hành |
| T21–T22 | Bản mã, quyền KMS, vật liệu khóa, hash độc lập; sửa ciphertext gây lỗi toàn vẹn |
| T23 | Backup DB/KMS thật, restore cô lập và đối chiếu ledger; primary không được thay thế; kiểm tra mode sau restart |
| T24 | TCP thật từ mạng client tới dịch vụ nội bộ, KMS dừng/khôi phục, giả mode header không đổi B1 thành B0 |

Các nhóm chuẩn có reset và thao tác lỗi; lỗi setup/cleanup phải được ghi fail. T15-time là cửa sổ quan sát từ yêu cầu đổi quyền đến phản hồi từ chối, không phải SLA hay thời điểm commit chính xác. T23c–e gọi primary, không phải HTTP của bản phục hồi cô lập.

## 4. Ma trận bổ sung cho web mới

Nguồn và kết quả: [script ngày 21/10](../results/restricted-management-20261021/validate_restricted.py), [validation.json](../results/restricted-management-20261021/validation.json). Các tên trong cột đầu là nhóm diễn giải, không phải mã T mới.

| Nhóm kiểm tra | Điều kiện và kết quả cần quan sát |
|---|---|
| Thêm Hạn chế | Nhân viên bị chặn tại Chủ sở hữu; trưởng phòng thiếu người duyệt bị chặn; API không có approval từ chối; không lưu tài liệu khi yêu cầu bị từ chối |
| Phê duyệt hợp lệ | secadmin xác thực tạo approval đúng trưởng phòng/phòng/tài liệu dự kiến/phiên bản/mục đích/thời hạn; lưu trực tiếp Hạn chế và grant ban đầu, người tạo tải đúng nội dung ngay sau lưu |
| Sửa theo quyền tải | Trưởng phòng có grant sửa được; nhân viên, sai phòng, kiểm toán và quản trị an toàn không được sửa nội dung nghiệp vụ; xem metadata không tạo quyền tải/sửa |
| Thu hồi và hết hạn | Khi không còn grant hợp lệ khác, thu hồi chặn GET download và PUT sửa; cấp lại khôi phục sử dụng; hết hạn trả lỗi ở Người thực hiện; gọi PUT qua B0 vẫn không vượt quyền |
| Ràng buộc approval | Sai người, hết hạn, đã sử dụng thành công hoặc sai mục đích create/upgrade đều bị chặn; approval dùng một lần khác grant tải nhiều yêu cầu |
| Giao dịch | Lỗi audit làm upload thất bại, không để tài liệu dở dang; approval chưa commit được dùng lại cho lần thử thành công; sau thành công không replay được |
| Nhãn và vòng đời | Không hạ nhãn; quyền tải không đổi hold hoặc kéo dài lưu giữ; nâng nhãn tạo phiên bản/grant mới và rút thời hạn theo mức Hạn chế |
| Dữ liệu nền | Upload thường còn dùng được; tài liệu đã có không bị reset bởi bộ bổ sung |

Bộ bổ sung được chạy riêng, chưa tự tích hợp vào `lab.runner`. Nó có thay đổi dữ liệu và lỗi audit, ghi đè `validation.json` khi chạy lại; không gọi đây là kiểm tra chỉ đọc hoặc bản cập nhật tự động của bằng chứng cũ.

Một người có thể có nhiều grant cho cùng tài liệu/phiên bản. Trước ca thu hồi hoặc hết hạn trên web, kiểm tra mọi dòng quyền của người đó: thu hồi tất cả grant còn hợp lệ, hoặc dùng tài liệu mới chỉ có một grant. API vẫn cho phép khi còn một grant khác đúng điều kiện; đó không phải lỗi thu hồi.

## 5. Bài hướng dẫn và đọc kết quả

Bắt đầu có hướng dẫn gồm quyền tài liệu của Anna, thu hồi, thiết bị và grant, mã hóa, audit/cảnh báo, vòng đời, phục hồi. Bài chuẩn bị thuộc tính bằng quyền operator rồi gửi yêu cầu nghiệp vụ thật; xem từng bước để phân biệt hai loại thao tác. Việc hoàn tác thuộc tính không xóa toàn bộ audit/snapshot hoặc reset lab.

Lượt runner chuẩn xuất record có `expected`, `actual`, `passed`, Request ID và bằng chứng, cùng JSON/CSV/HTML. Bằng chứng tải nên ghi hash/độ dài thay cho bản rõ; không ghi token hoặc khóa. Lượt 19/10 đạt 127 mục tổng hợp; cập nhật 21/10 đạt 39 kiểm tra tích hợp riêng. Xem [đánh giá bằng chứng](verification-review.md) để tránh cộng sai số lượng.

Lệnh chạy an toàn theo phạm vi và cảnh báo reset nằm tại [quy trình tái lập](reproduction.md). Không chạy đồng thời hai phép thử có trạng thái.
