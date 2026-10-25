# Hợp đồng API và điều kiện thực thi

Cập nhật tài liệu ngày 25/10/2026, đối chiếu `app/main.py`, `policies/bmdl.rego`, `lab/web.py` và `lab/management.py`. [Mục lục](muc_luc.md) · [Kiến trúc](architecture.md) · [Hướng dẫn web](huong_dan_nhanh.md)

## 1. Hai lớp giao diện

- API nghiệp vụ: qua gateway B1 `https://localhost:8443/api/` hoặc B0 `https://localhost:8444/api/`. Gateway yêu cầu mTLS; các route nghiệp vụ xác thực JWT. `/health` chỉ kiểm tra sẵn sàng, không thực hiện logic xác thực JWT của route nghiệp vụ. Các đường dưới đây được ghi tương đối với `/api/`.
- API console: `/lab/...` trên `http://localhost:8088`, chỉ dành cho người vận hành cục bộ. Thay đổi cần cookie phiên/CSRF và nguồn hợp lệ; quyền operator không phải quyền của tài khoản nghiệp vụ.

B0 chỉ nới một số điều kiện đọc theo snapshot vai trò/phòng ban. Thêm, sửa và quản trị vẫn kiểm tra điều kiện B1 tương ứng. Client không đổi B1 thành B0 bằng header gửi vào đường B1.

## 2. API tài liệu và định danh

| Phương thức và đường | Body hoặc kết quả chính | Điều kiện |
|---|---|---|
| `GET /health` | Trạng thái dịch vụ, mode | Endpoint kiểm tra sẵn sàng |
| `GET /me` | Danh tính, vai trò/phòng ban hiện tại, thiết bị và mode | Xác thực và điều kiện truy cập |
| `GET /documents` | `{items: [...]}` metadata được phép | Lọc từng tài liệu theo quyền metadata |
| `GET /documents/{id}/metadata` | Metadata của một tài liệu | Quyền xem thông tin mô tả |
| `GET /documents/{id}/download` | Nội dung nhị phân đã giải mã | Quyền tải, hash hợp lệ, audit thành công |
| `POST /documents` | Body upload; trả metadata mới | Quyền thêm; Hạn chế cần `approval_id` hợp lệ |
| `PUT /documents/{id}` | Body sửa thông tin; trả metadata | Quyền tải hiện tại B1, không hạ nhãn/lạm dụng quyền vòng đời |
| `DELETE /documents/{id}` | ID và trạng thái tombstone | Quyền hủy, qua thời hạn, không legal hold |

Metadata trả về gồm `id`, `title`, `owner_id`, `department`, `label`, `version`, `retention_until`, `legal_hold`. Yêu cầu nghiệp vụ bị từ chối không trả thuộc tính tài liệu ngoài quyền. Catalog trong console là nguồn mô tả tập mẫu của operator, không cấp quyền nghiệp vụ.

### 2.1. Thêm tài liệu

```json
{
  "title": "tai_lieu.txt",
  "label": "restricted",
  "content_b64": "...",
  "approval_id": "..."
}
```

- Tên 1–200 ký tự, đuôi TXT/CSV/PDF, không có dấu phân cách đường dẫn hoặc ký tự điều khiển bị cấm; nội dung có dữ liệu, tối đa 1.048.576 byte sau giải mã Base64.
- `label`: `internal`, `confidential` hoặc `restricted`. API gán chủ sở hữu và phòng ban theo principal của yêu cầu, không nhận hai thuộc tính này từ client.
- Nội bộ/Mật: staff hoặc manager theo điều kiện chung. Hạn chế: manager và phê duyệt tạo chưa dùng, đúng người/phòng ban/mục đích, còn hạn và người duyệt còn quyền.
- Tạo Hạn chế lưu tài liệu ở phiên bản 1, grant ban đầu và consumed trong cùng giao dịch. Phê duyệt `create` được dùng thành công một lần; grant tải có thể dùng nhiều lần khi còn hiệu lực.

### 2.2. Sửa thông tin

```json
{
  "title": "ten_moi.txt",
  "label": "restricted",
  "legal_hold": false,
  "retention_until": 1800000000,
  "approval_id": "..."
}
```

`legal_hold` và `retention_until` phải giữ trạng thái hiện có; đây không phải quyền chỉnh vòng đời. API bỏ qua sai khác dưới 60 giây do độ chính xác nhập ngày và giữ thời hạn cũ; đổi trạng thái bảo toàn hoặc đổi thời hạn từ 60 giây trở lên bị chặn. UI hai trường này chỉ để tra cứu.

- Quyền tải hiện tại theo B1 là điều kiện bắt buộc, kể cả gọi API B0. Với Hạn chế phải có grant đúng người, tài liệu, phiên bản, action `download`, còn hạn và chưa thu hồi.
- Chức năng sửa chỉ đổi tên/nâng nhãn, chưa thay thế nội dung tệp. Đổi tên không tăng phiên bản kiểm soát tài liệu.
- Hạ nhãn bị từ chối. Đổi nhãn tăng phiên bản và giữ lưu giữ không dài hơn giới hạn của nhãn mới.
- Nâng Nội bộ/Mật lên Hạn chế cần thêm phê duyệt `upgrade` cho đúng ID và phiên bản kế tiếp. API kiểm tra quyền tải tài liệu hiện tại trước nâng, rồi tạo grant cho phiên bản mới cùng giao dịch.

## 3. API quản trị nghiệp vụ

Các endpoint cần `security_admin` và điều kiện B1. Có grant không tự biến người nhận sai vai trò/phòng ban thành người được đọc.

| Endpoint | Body | Hành vi |
|---|---|---|
| `POST /admin/restricted-approvals` | `principal_id`, `doc_id` tùy chọn, `ttl_seconds` | Tạo phê duyệt `create` nếu không có doc_id; `upgrade` nếu có. Người nhận phải là manager đang hoạt động; nâng nhãn cần cùng phòng với tài liệu |
| `POST /admin/grants` | `principal_id`, `doc_id`, `ttl_seconds` | Cấp grant `download` cho phiên bản Hạn chế hiện tại; không tự duyệt cho chính mình |
| `DELETE /admin/grants/{id}` | Không có | Đánh dấu grant đã thu hồi |
| `POST /admin/documents/{id}/raise-label` | `label` | Nâng nhãn, tăng phiên bản, giới hạn lưu giữ; không hạ nhãn. Luồng quản trị này không tự cấp grant tải |
| `PUT /admin/principals/{id}` | Một số trường active/role/department | Cập nhật registry; không tự đổi role/department, không cấp vai trò security_admin qua endpoint này |
| `PUT /admin/devices/{id}` | Một số trường trạng thái/tín hiệu thiết bị | Cập nhật hồ sơ thiết bị có audit |
| `GET /admin/state` | Không có | Trạng thái phục vụ quản trị, không trả title/nội dung/bản mã/bí mật |
| `POST /alerts/{id}/ack` | Không có | Xác nhận cảnh báo |

`ttl_seconds` của phê duyệt mới: mặc định 900, lớn hơn 0 và không quá 3600. Grant tải: mặc định 300, cùng giới hạn API. Có thể có nhiều grant cùng người/tài liệu/phiên bản; thu hồi một ID chỉ vô hiệu hóa grant đó. API chọn grant phù hợp còn hạn nếu vẫn có, nên phép thử từ chối phải làm mọi grant phù hợp không còn hiệu lực. UI tạo Hạn chế chọn 5–60 phút; bảng quyền tải/sửa chọn 1–60 phút. Wrapper quản lý còn kiểm tra người nhận active, role manager và cùng phòng; API grant trực tiếp kiểm tra người nhận tồn tại nhưng quyền sử dụng vẫn phải vượt chính sách đọc/sửa.

`GET /audit` và `GET /alerts` cần auditor hoặc security_admin. Auditor đọc sự kiện đã lọc bí mật; security_admin đọc phạm vi sự kiện vận hành do API quy định. Danh sách rỗng với HTTP 200 là kết quả thành công.

## 4. API quản lý trên console

| Endpoint | Vai trò trong web |
|---|---|
| `GET /lab/bootstrap` | CSRF, danh tính phiên, danh sách tài khoản hiện có |
| `GET /lab/state` | Trạng thái an toàn phục vụ giao diện operator |
| `GET /lab/dataset` | Danh mục/căn cứ phân loại bộ mẫu, không nội dung tệp |
| `POST /lab/employees` | Tạo tài khoản Keycloak, chứng thư và bản ghi nhân viên |
| `PUT /lab/employees/{id}` | Đổi tên/vai trò/phòng ban/active theo đặc quyền operator |
| `POST /lab/documents` | Thêm từ biểu mẫu; chuyển phê duyệt và upload qua API nghiệp vụ |
| `PUT /lab/documents/{id}` | Sửa tên/nâng nhãn bằng người thực hiện qua API nghiệp vụ |
| `POST /lab/documents/{id}/grants` | Chọn người nhận, người phê duyệt và thời hạn; gọi API grant |
| `DELETE /lab/documents/{id}/grants/{grant_id}` | Thu hồi bằng danh tính quản trị được chọn |
| `POST /lab/request` | Chuyển yêu cầu tự thử qua gateway, trả phản hồi và bằng chứng |

Biểu mẫu tài liệu nhận `filename`, `title`, `owner_id`, `label`, `content_b64`; khi Hạn chế có `approver_id`, `ttl_seconds`. Sửa nhận `actor_id`, tên/nhãn và trạng thái vòng đời hiện tại, kèm thông tin phê duyệt khi nâng lên Hạn chế. Nếu có phiên Keycloak, máy chủ thay `owner_id`/`actor_id` bằng người trong phiên và dùng token phiên.

Biểu mẫu nhân viên nhận `username`, `display_name`, `password`, `role`, `department`, `active`. Role là staff/manager/auditor/security_admin; staff/manager ở A/B, auditor/security_admin ở OPS. Tên đăng nhập 3–32 ký tự, bắt đầu bằng chữ thường; mật khẩu 8–128 ký tự. Đây là cấp danh tính trong môi trường kiểm thử bởi operator, tách với endpoint quản trị principal nghiệp vụ hạn chế đặc quyền.

Các chức năng `/lab/lessons`, job, test cases, fault, backup/restore và chỉnh trạng thái được mô tả ở [hướng dẫn web](huong_dan_nhanh.md), [kịch bản trình diễn](huong-dan-trinh-dien-va-doi-chieu-bao-cao.md) và [tái lập](reproduction.md). Chỉ một tác vụ thay đổi môi trường chạy tại một thời điểm; reset/bộ chuẩn có thể thay bộ tài liệu và lịch sử.

## 5. Phản hồi, lỗi và tính nhất quán

Lỗi nghiệp vụ có dạng `{detail:{reason,request_id}}`; phản hồi có `X-Request-ID`, `X-Policy-Reason`, `X-Policy-Version`, `X-Policy-Mode` khi thích hợp. Lỗi biểu mẫu quản lý có `{detail:{message,fields,...}}` để đánh dấu đúng ô. Không nhập token, cookie hoặc host tùy ý qua phần Header bổ sung.

| Nhóm lý do | Ý nghĩa |
|---|---|
| `INACTIVE`, `ROLE`, `DEPARTMENT`, `OWNER_OR_LABEL` | Danh tính/quyền/phạm vi không đáp ứng |
| `DEVICE_MISMATCH`, `DEVICE_REVOKED`, `NONCOMPLIANT`, `RISK_HIGH`, `MISSING_OR_STALE` | Chứng thư, thiết bị hoặc tín hiệu không đáp ứng |
| `RESTRICTED_ROLE`, `RESTRICTED_APPROVAL`, `RESTRICTED_GRANT` | Sai vai trò, phê duyệt tạo/nâng hoặc grant sử dụng Hạn chế |
| `LABEL_DOWNGRADE`, `LIFECYCLE_ADMIN_REQUIRED` | Hạ nhãn hoặc dùng quyền nội dung để đổi vòng đời |
| `RETENTION_EXPIRED`, `LEGAL_HOLD`, `RETENTION_ACTIVE` | Điều kiện đọc/hủy theo vòng đời |
| `PDP_UNAVAILABLE`, `PDP_INVALID`, `KMS_UNAVAILABLE`, `AUDIT_UNAVAILABLE`, `REGISTRY_UNAVAILABLE` | Phụ thuộc kiểm soát lỗi, không cấp bản rõ |
| `LEDGER_UNAVAILABLE` | Ghi DB có thể đã commit nhưng ghi nhận đối chiếu chưa hoàn tất; kiểm tra trạng thái trước khi thử lại |

HTTP thường gặp: 400/422 đầu vào, 401 xác thực, 403 chính sách, 404 tài nguyên, 409 xung đột console, 503 phụ thuộc. Chứng thư bị chặn ở TLS có thể không tạo phản hồi từ API. Luôn đọc cả HTTP và reason.

Giao dịch giữ khóa trạng thái cần thiết và kiểm tra thời hạn trước commit. Mã hóa và OPA là lời gọi dịch vụ ngoài PostgreSQL, không được mô tả như giao dịch phân tán nguyên tử. Hủy giao dịch thêm không lưu tài liệu dở dang; lỗi ledger sau commit có ngữ nghĩa khác và phải được đối chiếu. Nhật ký và kết quả thử không chứa token, private key hoặc bản rõ tài liệu.

## Ghi chú về hiệu lực phê duyệt và phiên bản

Phê duyệt tạo/nâng nhãn được tiêu thụ một lần khi giao dịch PostgreSQL commit. Nếu ledger lỗi sau commit, HTTP có thể báo lỗi dù tài liệu/grant/trạng thái đã dùng đã được lưu; cần làm mới trạng thái trước khi gửi lại. Trường version là phiên bản kiểm soát tài liệu: nâng nhãn và xóa logic làm tăng; đổi tên hiện không tăng. Nhãn policy_version không thay thế hash mã nguồn của lượt kiểm chứng.
