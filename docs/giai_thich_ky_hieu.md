# Giải thích ký hiệu trong báo cáo và web

Cập nhật tài liệu ngày 25/10/2026. Các mã do nhóm đặt phục vụ nguyên mẫu; không phải tên kiến trúc bắt buộc của Google, Microsoft hay một tiêu chuẩn.

Bắt đầu sử dụng tại [hướng dẫn nhanh](huong_dan_nhanh.md). Danh mục 20 tài liệu khởi tạo nằm trong [quy chuẩn dữ liệu](data-classification.md).

## 1. Những mã dễ nhầm nhất

| Ký hiệu | Nghĩa |
|---|---|
| `B1` | Chính sách đề xuất, xét quyền và điều kiện hiện tại cho yêu cầu |
| `B0` | Đối chứng quyền đọc tĩnh do nhóm tạo để so sánh với B1 |
| `A`, `B` trong phòng ban | A = Kinh doanh; B = Vận hành |
| `OPS` | Nhóm An toàn thông tin, gồm kiểm toán và quản trị an toàn |
| `A-I01` | Tài liệu khởi tạo: phòng A, nhóm Nội bộ, số 01 |
| `B-R02` | Tài liệu khởi tạo: phòng B, nhóm Hạn chế, số 02 |
| `O-A01` | Ca oracle có kỳ vọng cho phép: O = oracle, A = allow |
| `O-D01` | Ca oracle có kỳ vọng từ chối: D = deny |
| `T15c` | Bước c trong nhóm tình huống T15; dùng JWT cũ sau thu hồi quyền |
| `U-...` | ID do máy chủ sinh cho tài liệu mới thêm |

- `A-I01` có chữ I viết hoa, không phải số 1 hoặc chữ l.
- `O-A01` bắt đầu bằng chữ O, không phải số 0. Đây là ca kiểm thử, không phải tài liệu.
- `A0` hoặc `A01` đứng riêng không phải ID trong bộ 20 tài liệu chuẩn. Cần phân biệt với `A-I01` và `O-A01`.
- Chữ B trong B0/B1 không chỉ phòng Vận hành. Cả hai phòng đều được thử với hai cấu hình.
- Số 01 trong ID chỉ là thứ tự. Phiên bản tài liệu là trường `version` riêng.

ID không cấp quyền. I/C/R thể hiện nhãn ban đầu của tài liệu mẫu; sau khi nâng nhãn, ID có thể vẫn giữ nguyên. API dùng `label` hiện tại trong cơ sở dữ liệu.

## 2. B0 và B1 khác nhau ở đâu?

| Điều kiện ở đường đọc | B0 | B1 |
|---|---|---|
| JWT hợp lệ, chứng thư hợp lệ và khớp tài khoản | Có | Có |
| Vai trò, phòng ban | Thuộc tính đối chứng trong JWT, do Keycloak phát từ cấu hình tài khoản | Trạng thái hiện tại tại máy chủ |
| Tài khoản bị khóa sau đăng nhập | Không dùng trạng thái active hiện tại để thu hẹp đường đọc | Yêu cầu mới bị chặn |
| Chủ sở hữu và nhãn hiện tại | Không dùng để thu hẹp đường đọc | Có |
| Tuân thủ, thu hồi thiết bị, rủi ro, độ mới tín hiệu | Không dùng để thu hẹp đường đọc | Có |
| Grant tải Hạn chế | Không bắt buộc ở đường đọc đối chứng | Bắt buộc với trưởng phòng cùng phòng |
| Tài liệu tồn tại, chưa xóa, chưa hết hạn đọc | Có | Có |
| Mã hóa, giải mã và audit | Có | Có |

Đường đọc gồm danh sách, metadata, download; thông tin bản thân `me` cũng có cấu hình đối chứng. B0 là cấu hình thử có chủ ý, không phải toàn bộ hệ thống bỏ bảo mật hoặc một kiến trúc vượt B1.

Hai thuộc tính đối chứng được đặt trong Keycloak khi chuẩn bị môi trường hoặc tạo tài khoản. Đổi vai trò/phòng ban trong registry không tự đồng bộ chúng; đăng nhập lại cũng không bảo đảm nhận quyền registry mới trong B0.

Thao tác sửa thông tin luôn kiểm tra quyền tải theo B1, kể cả khi gọi qua đường B0. Chọn B0 không bỏ qua quyền thêm, quản trị hoặc điều kiện sửa.

Ví dụ với trạng thái chuẩn, thiết bị hợp lệ và dịch vụ sẵn sàng: alice xem metadata A-C02 của anna → B1 trả `403 OWNER_OR_LABEL`; cùng yêu cầu qua B0 → `200 ALLOW`. Khác biệt này minh họa điều kiện owner/nhãn, không chứng minh toàn diện hiệu quả mọi kiến trúc.

## 3. Nhãn, vai trò và tài khoản

| Nhãn | Mã | Quyền trong B1 khi các điều kiện chung hợp lệ |
|---|---|---|
| Nội bộ | I / `internal` | Nhân viên và trưởng phòng cùng phòng được tải |
| Mật | C / `confidential` | Nhân viên tải tài liệu mình sở hữu; trưởng phòng tải trong phòng |
| Hạn chế | R / `restricted` | Trưởng phòng cùng phòng xem metadata; tải và sửa cần grant hợp lệ |

Các nhãn là quy ước nghiệp vụ trên dữ liệu tổng hợp. Nội bộ không có nghĩa công khai; Hạn chế không phải cấp bí mật nhà nước. Không có chức năng tự phân loại nội dung.

| Vai trò | Tài khoản khởi tạo | Phạm vi |
|---|---|---|
| `staff` – Nhân viên | alice, anna ở A; bob, bea ở B | Đọc/sửa theo quyền tải; thêm Nội bộ/Mật |
| `manager` – Trưởng phòng | adam ở A; brian ở B | Đọc theo phòng/nhãn; xử lý Hạn chế cần phê duyệt phù hợp |
| `auditor` – Kiểm toán | auditor | Đọc nhật ký và cảnh báo; không đọc nội dung tài liệu |
| `security_admin` – Quản trị an toàn | secadmin | Quản lý trạng thái, nhãn và phê duyệt; không mặc nhiên đọc/sửa nội dung |

Đây là tám tài khoản khởi tạo. Web cho tạo thêm người; vai trò và phòng ban có thể thay đổi. Xem trạng thái hiện tại tại **Nhân viên** hoặc **Điều khiển lab**.

## 4. Phê duyệt tạo khác grant tải như thế nào?

| Khái niệm | Mục đích và hiệu lực |
|---|---|
| Phê duyệt tạo/nâng nhãn, `restricted_approvals` | Quản trị an toàn duyệt cho trưởng phòng, gắn người, phòng, tài liệu dự kiến, phiên bản, mục đích và hạn. Chỉ được dùng thành công một lần |
| `purpose=create` / `purpose=upgrade` | Phân biệt thêm tài liệu mới với nâng nhãn tài liệu đã có; không dùng chéo |
| Grant tải, `grants` | Quyền dùng tài liệu đã lưu; gắn người nhận, tài liệu, phiên bản, action download và thời hạn. Có thể dùng cho nhiều yêu cầu khi còn hiệu lực |
| `approver` | Người cấp quyền; phải khác người nhận |
| `consumed=true` | Phê duyệt tạo/nâng nhãn đã được sử dụng thành công |
| `revoked=true` | Grant hoặc thiết bị đã bị thu hồi, tùy đối tượng đang xem |
| `version` / `doc_version` | Phiên bản kiểm soát tài liệu / phiên bản mà grant ràng buộc |

Khi thêm trực tiếp Hạn chế, tài liệu, grant ban đầu và trạng thái dùng phê duyệt được lưu trong cùng giao dịch. Khi sửa Hạn chế, API kiểm tra grant tải hiện tại. Metadata được xem mà chưa có grant không cho phép sửa hoặc tải nội dung.

Một người có thể có nhiều grant cho cùng tài liệu/phiên bản. Thu hồi một dòng hoặc chờ một grant hết hạn chưa chặn được khi còn grant khác hợp lệ.

Đổi tên không tăng phiên bản kiểm soát tài liệu. Nâng nhãn và xóa logic làm tăng phiên bản; với nâng nhãn, làm grant phiên bản cũ không còn phù hợp. Quyền tải/sửa không cho thay đổi hạn lưu giữ hoặc trạng thái bảo toàn.

## 5. Thiết bị, chứng thư và danh tính

| Tên/trường | Cách hiểu |
|---|---|
| `dev-alice` | ID bản ghi thiết bị; tiền tố dev là device |
| Chứng thư client | Chứng nhận khóa của phía gửi, dùng trong mTLS |
| `cert_serial` | Số sê-ri của chứng thư; máy chủ đối chiếu với registry thiết bị |
| `subject_id`, JWT `sub` | Định danh Keycloak để tra chủ thể; không phải ID thiết bị hoặc tài liệu |
| JWT `iss`, `aud`, `exp` | Nơi phát hành, đối tượng nhận và thời điểm token hết hạn |
| `b0_role`, `b0_department` | Vai trò/phòng ban đối chứng cấu hình trong Keycloak và phát trong JWT; tách khỏi quyền hiện tại ở registry |
| `compliant` | Trạng thái tuân thủ giả lập của thiết bị |
| `risk=NORMAL/HIGH` | Tín hiệu rủi ro bình thường/cao |
| `observed_at`, `risk_at` | Thời điểm đánh giá tuân thủ/rủi ro |
| `auto_refresh` | Bật/tắt làm mới tín hiệu giả lập, chu kỳ 20 giây |
| `rogue` / `bad` / `none` | Chứng thư CA lab nhưng chưa đăng ký / CA không tin cậy / không gửi chứng thư |

ID thiết bị và số sê-ri chứng thư là hai giá trị khác nhau. Đăng nhập alice nhưng dùng chứng thư anna bị chặn vì không khớp người. Chứng thư hợp lệ không chứng minh thiết bị sạch mã độc hoặc tự tạo quyền đọc.

**Chọn tài khoản** dùng quyền người vận hành cục bộ để thử danh tính. **Tài khoản đang đăng nhập** dùng phiên Keycloak đã xác minh. Riêng thao tác thêm/sửa tại Tài liệu dùng danh tính phiên khi đã đăng nhập; đổi username trong body không thay được người này. Console là công cụ thử tin cậy, chưa phải cổng nhiều người dùng với hàng đợi duyệt độc lập.

## 6. Thời gian, vòng đời và phản hồi

| Ký hiệu | Nghĩa |
|---|---|
| TTL | Thời gian hiệu lực; 300 giây = 5 phút |
| TTL tín hiệu 60 giây | Khác thời hạn grant; tín hiệu quá cũ/thiếu không hợp lệ |
| `expires_at` | Thời điểm quyền/phê duyệt hết hạn |
| `retention_until` | Mốc hết hạn lưu giữ/đọc của tài liệu |
| `legal_hold` | Bảo toàn tài liệu, chặn xóa; không cấp quyền đọc |
| `deleted`, tombstone | Trạng thái xóa logic và dấu vết giúp phục hồi không làm sống lại tài liệu đã hủy |
| `active` | Trạng thái hoạt động của tài khoản |
| `permission_version` | Bộ đếm trạng thái quyền, khác B0/B1 và phiên bản tài liệu |
| `true`, `false`, `null` | Đúng/bật, sai/tắt, chưa có giá trị; null không mặc nhiên là false |
| Unix epoch | Số giây từ 01/01/1970 UTC; web đổi thành giờ dễ đọc |
| Request ID | Mã liên kết phản hồi với nhật ký của cùng yêu cầu |
| `event_id` | Mã một sự kiện; một yêu cầu có thể có nhiều sự kiện |
| `policy_version=bmdl-v1` | Nhãn khai báo của quy tắc, không tự tăng khi sửa mã; cần hash nguồn/manifest để xác định đúng bản. Không phải tên chế độ B1 |
| SHA-256 | Mã băm kiểm tra nội dung; không phải khóa hay mật khẩu |
| Base64 / `content_b64` | Cách biểu diễn byte để truyền, không phải mã hóa bảo mật |
| `ciphertext` / `plaintext` | Bản mã / bản rõ |
| `latency_ms` | Độ trễ mili giây; riêng nó không chứng minh an toàn |
| `client_delivery_confirmed=false` | Máy chủ chưa xác nhận client nhận trọn file; không kết luận tải chắc chắn thất bại |

## 7. Đọc kết quả và mã lỗi

Luôn đọc HTTP cùng lý do. `200 ALLOW` là thành công; `403` là bị chặn; `401` là lỗi xác thực; `404` là không tìm thấy; `409` là xung đột; `422` là trường nhập chưa hợp lệ; `503` thường là phụ thuộc/chức năng bắt buộc chưa sẵn sàng. Lỗi biểu mẫu chỉ rõ ô cần sửa.

| Lý do | Cách hiểu hoặc xử lý |
|---|---|
| `OWNER_OR_LABEL` | Không đủ quyền theo chủ sở hữu/nhãn |
| `DEPARTMENT` | Khác phòng ban của tài liệu |
| `ROLE`, `RESTRICTED_ROLE` | Sai vai trò; Hạn chế yêu cầu trưởng phòng phù hợp |
| `RESTRICTED_APPROVAL` | Thiếu, hết hạn, đã dùng hoặc sai phạm vi/mục đích phê duyệt tạo/nâng nhãn |
| `RESTRICTED_GRANT` | Grant tải/sửa chưa hợp lệ; cấp lại đúng người, tài liệu, phiên bản |
| `INACTIVE` | Tài khoản bị khóa |
| `DEVICE_MISMATCH` | Chứng thư không khớp chủ thể hoặc chưa có ánh xạ hợp lệ |
| `DEVICE_REVOKED`, `NONCOMPLIANT`, `RISK_HIGH` | Thiết bị bị thu hồi, chưa tuân thủ hoặc rủi ro cao |
| `MISSING_OR_STALE` | Tín hiệu thiếu, quá cũ hoặc thời điểm không hợp lệ |
| `LABEL_DOWNGRADE` | Không được hạ nhãn qua API sửa |
| `LIFECYCLE_ADMIN_REQUIRED` | Quyền tải không đủ để đổi lưu giữ/bảo toàn |
| `RETENTION_EXPIRED` | Tài liệu đã hết hạn đọc |
| `RETENTION_ACTIVE`, `LEGAL_HOLD` | Chưa được xóa vì còn hạn hoặc đang bảo toàn |
| `PDP_UNAVAILABLE`, `PDP_INVALID` | OPA không sẵn sàng hoặc trả quyết định không hợp lệ |
| `KMS_UNAVAILABLE`, `AUDIT_UNAVAILABLE` | Mã hóa/giải mã hoặc ghi audit bắt buộc chưa thực hiện được |
| `LEDGER_UNAVAILABLE` | Chưa hoàn tất ghi nhận thay đổi; làm mới trước khi gửi lại |
| `INTEGRITY_FAILURE` | Bản mã/nội dung không vượt qua kiểm tra toàn vẹn |

Các mã có thể được hiện thành lời tiếng Việt ở giao diện. Mở **Xem HTTP, Request ID và JSON** để đối chiếu chi tiết.

## 8. Thuật ngữ kiến trúc và kết quả thử

| Ký hiệu | Nghĩa trong nguyên mẫu |
|---|---|
| JWT / OIDC / PKCE | Token xác thực / giao thức đăng nhập / bảo vệ trao đổi mã đăng nhập |
| `state`, `nonce` | Giá trị ràng buộc lượt đăng nhập và phản hồi, được kiểm tra phía máy chủ |
| CSRF | Cơ chế ràng buộc yêu cầu thay đổi với phiên console để hạn chế yêu cầu giả từ trang khác |
| TLS / mTLS / CA | Kênh mã hóa / xác thực chứng thư hai phía / đơn vị ký chứng thư |
| PDP / PEP | Quyết định chính sách / thực thi chính sách. OPA đánh giá quy tắc, API thu thập thuộc tính và thực thi |
| KMS / Transit | Dịch vụ quản lý khóa / chức năng mã hóa, giải mã OpenBao |
| RBAC / ABAC | Điều kiện theo vai trò / theo thuộc tính; chính sách phối hợp nhiều yếu tố |
| NIST SP 800-207 | Tài liệu tham chiếu về Zero Trust Architecture được dùng trong báo cáo |
| SABSA | Phương pháp kiến trúc bảo mật được vận dụng rút gọn để nối nhu cầu, rủi ro, kiểm soát và bằng chứng |
| CIA | Bí mật, toàn vẹn và khả dụng; ba góc nhìn đánh giá yêu cầu bảo vệ dữ liệu |
| IDPRR trong báo cáo | Nhóm hoạt động nhận diện, phát hiện, bảo vệ, ứng phó và phục hồi; không phải tên endpoint |
| Oracle | Kỳ vọng đã xác lập trước để đối chiếu kết quả thực |
| `expected`, `actual`, `passed` | Kỳ vọng, phản hồi quan sát và việc đối chiếu có đạt hay không |
| `false_allow`, `false_deny` | Cho phép khi phải chặn / chặn khi phải cho phép trong tập có kỳ vọng |
| `run-...`, `lesson-...` | ID một lượt kiểm chứng hoặc bài hướng dẫn |
| `business-v1` | Phiên bản tập 20 tài liệu khởi tạo; không phải tổng số file hiện tại |
| RTO / RPO | Mục tiêu thời gian phục hồi / mốc dữ liệu có thể phục hồi. Trong output lab, thời gian diễn tập và tuổi snapshot là số đo có phạm vi riêng, chưa phải cam kết doanh nghiệp hoặc lượng dữ liệu mất |
| `mean`, `p50`, `p95` | Trung bình, trung vị và phân vị 95% của độ trễ trong lượt benchmark |
| HA | Tính sẵn sàng cao; nguyên mẫu chưa triển khai cụm dự phòng |
| MDM / EDR / attestation | Quản lý thiết bị / giám sát, phản ứng tại thiết bị / xác nhận trạng thái đáng tin cậy; chưa phải nguồn tín hiệu thực của demo |

`127/127`, `39/39`, `31/31` hoặc `18/18` thuộc các lượt và phạm vi khác nhau. Không cộng chúng thành số yêu cầu HTTP hoặc coi là trạng thái luôn đúng. Xem [tổng hợp bằng chứng](ket_qua_kiem_chung.md) và [ma trận kiểm chứng](test-matrix.md).

