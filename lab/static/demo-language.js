"use strict";

const DemoLanguage = (() => {
  const modes = {
    F0: {name: "Kiểm tra khi đăng nhập", help: "Kho kiểm tra tài khoản khi đăng nhập. Nếu tài khoản bị khóa sau đó, phiên đã tạo vẫn có thể dùng đến khi hết hạn."},
    F1: {name: "Thu hồi theo thông báo", help: "Khi nhận được thông báo khóa tài khoản, kho thu hồi phiên đang dùng. Nếu thông báo bị mất, phiên cũ vẫn có thể dùng."},
    F2: {name: "Thu hồi theo thông báo và tự kiểm tra lại", help: "Kho nhận thông báo và tự hỏi lại bên quản lý tài khoản. Nếu chưa xác nhận được trạng thái khi thông tin đã lưu hết hạn, kho dừng yêu cầu."},
  };
  const roles = {staff: "Nhân viên", manager: "Trưởng phòng", partner_admin: "Quản trị đối tác", security_admin: "Quản trị an toàn", auditor: "Kiểm toán"};
  const departments = {A: "Kinh doanh", B: "Vận hành", OPS: "An toàn thông tin"};
  const organizations = {P: "Bên quản lý tài khoản", R: "Kho tài liệu"};
  const labels = {internal: "Nội bộ", confidential: "Mật", restricted: "Hạn chế"};
  const actions = {me: "Xem tài khoản", list: "Xem danh sách tài liệu", metadata: "Xem thông tin tài liệu", read: "Tải tài liệu", download: "Tải tài liệu", upload: "Thêm tài liệu", create: "Thêm tài liệu", update: "Sửa tài liệu", delete: "Xóa tài liệu", audit: "Đọc nhật ký", alert: "Đọc cảnh báo", admin: "Thay đổi quyền", raise_label: "Nâng mức bảo vệ", grant: "Cấp hoặc thu hồi quyền", login: "Đăng nhập", session: "Tạo phiên truy cập"};
  const messages = {
    ALLOW: "Yêu cầu đã hoàn tất.",
    RESOURCE_SESSION_CREATED: "Đã đăng nhập. Có thể gửi yêu cầu bằng phiên vừa tạo.",
    SOURCE_VERIFIED: "Kho đã kiểm tra lại trạng thái tài khoản và thiết bị.",
    SESSION_VALID: "Phiên vẫn dùng được với tài khoản, thiết bị và cách kiểm tra đã chọn.",
    APPLIED: "Kho đã xử lý thông báo thay đổi.",
    OPERATOR_INVALIDATION: "Người quản lý đã thu hồi phiên truy cập.",
    SOURCE_ACCOUNT_DISABLED: "Bên quản lý tài khoản đã khóa tài khoản này. Đăng nhập lại sau khi tài khoản được mở khóa.",
    SOURCE_DEVICE_REVOKED: "Thiết bị đã bị thu hồi. Khôi phục thiết bị rồi đăng nhập lại.",
    DEVICE_REVOKED: "Thiết bị đã bị thu hồi.",
    SOURCE_DEVICE_NONCOMPLIANT: "Thiết bị chưa đáp ứng yêu cầu an toàn.",
    NONCOMPLIANT: "Thiết bị chưa đáp ứng yêu cầu an toàn.",
    SOURCE_DEVICE_RISK: "Thiết bị đang được đánh dấu có rủi ro cao.",
    RISK_HIGH: "Thiết bị đang được đánh dấu có rủi ro cao.",
    SOURCE_STATE_CHANGED: "Trạng thái tài khoản hoặc thiết bị đã thay đổi. Đăng nhập lại khi cả hai đủ điều kiện.",
    SOURCE_OBSERVATION_STALE: "Thông tin về thiết bị đã quá hạn. Cập nhật trạng thái thiết bị rồi thử lại.",
    MISSING_OR_STALE: "Chưa có thông tin thiết bị còn hiệu lực.",
    SOURCE_UNAVAILABLE: "Kho chưa xác nhận được trạng thái tài khoản và thiết bị. Vui lòng thử lại sau.",
    SOURCE_CONTEXT_EXPIRED: "Thông tin đã kiểm tra về tài khoản và thiết bị đã hết hạn.",
    SOURCE_PROOF_INVALID: "Kho không xác minh được thông tin trạng thái vừa nhận.",
    RESOURCE_SESSION_REQUIRED: "Chọn tài khoản và thiết bị rồi bấm Đăng nhập và tạo phiên trước khi gửi yêu cầu.",
    RESOURCE_SESSION_EXPIRED: "Phiên đã hết hạn. Đăng nhập lại để tiếp tục.",
    SESSION_SERVICE_RESTARTED: "Dịch vụ vừa khởi động lại. Đăng nhập để tạo phiên mới.",
    RECOVERY_REAUTH_REQUIRED: "Hệ thống đã phục hồi. Đăng nhập để tạo phiên mới.",
    OPERATOR_SESSION_REVOKED: "Phiên truy cập đã bị thu hồi. Đăng nhập lại để tiếp tục.",
    RESOURCE_SESSION_INVALID: "Phiên truy cập không dùng được. Đăng nhập để tạo phiên mới.",
    SESSION_MODE_MISMATCH: "Phiên được tạo với cách kiểm tra khác. Đăng nhập với cách kiểm tra đang chọn.",
    COORDINATOR_UNAVAILABLE: "Kho chưa kiểm tra được phiên truy cập. Vui lòng thử lại sau.",
    DEVICE_MISMATCH: "Thiết bị không khớp với tài khoản hoặc phiên đang dùng. Chọn đúng thiết bị đã đăng ký.",
    SOURCE_SELF_LOCK_FORBIDDEN: "Người quản lý không thể tự khóa tài khoản đang dùng. Chọn một tài khoản khác.",
    IDENTITY_LOGIN_FAILED: "Đăng nhập chưa thành công. Kiểm tra xem tài khoản có đang hoạt động không.",
    IDENTITY_UNAVAILABLE: "Chưa kết nối được dịch vụ đăng nhập. Vui lòng thử lại sau.",
    PARTNER_ADMIN_REQUIRED: "Người thực hiện cần có quyền quản lý tài khoản và thiết bị của đối tác.",
    PARTNER_OBJECT_NOT_FOUND: "Không tìm thấy tài khoản hoặc thiết bị thuộc bên quản lý tài khoản.",
    INACTIVE: "Tài khoản này đang bị ngừng quyền truy cập kho.",
    ROLE: "Vai trò hiện tại chưa có quyền thực hiện thao tác này.",
    DEPARTMENT: "Tài liệu thuộc phòng ban khác với phòng ban được cấp quyền.",
    RESTRICTED_GRANT: "Cần quyền truy cập còn hạn cho đúng người, tài liệu, phiên bản và thao tác.",
    OWNER_OR_LABEL: "Tài khoản chưa có quyền theo chủ sở hữu hoặc mức bảo vệ của tài liệu.",
    RETENTION_ACTIVE: "Tài liệu còn trong thời hạn lưu giữ nên chưa thể xóa.",
    RETENTION_EXPIRED: "Tài liệu đã hết thời hạn lưu giữ và không còn được cấp để đọc.",
    LEGAL_HOLD: "Tài liệu đang được giữ để bảo toàn nên chưa thể xóa.",
    NOT_FOUND: "Không tìm thấy tài liệu hoặc thông tin được yêu cầu.",
    KMS_UNAVAILABLE: "Kho chưa giải mã được tài liệu. Vui lòng thử lại sau.",
    PDP_UNAVAILABLE: "Kho chưa kiểm tra được quyền truy cập. Vui lòng thử lại sau.",
    PDP_INVALID: "Kho chưa xác nhận được kết quả kiểm tra quyền. Vui lòng thử lại sau.",
    AUDIT_UNAVAILABLE: "Kho chưa ghi được nhật ký nên đã dừng yêu cầu.",
    LEDGER_UNAVAILABLE: "Kho chưa ghi nhận xong thay đổi. Làm mới danh sách trước khi thử lại.",
    REGISTRY_UNAVAILABLE: "Kho chưa lấy được thông tin quyền hiện tại. Vui lòng thử lại sau.",
    INTEGRITY_FAILURE: "Kho chưa xác nhận được nội dung còn nguyên vẹn nên đã dừng yêu cầu.",
    INVALID_TOKEN: "Thông tin đăng nhập không còn hợp lệ. Đăng nhập lại để tiếp tục.",
    TRANSPORT_BLOCKED: "Không kết nối được. Kiểm tra thiết bị đã chọn và trạng thái dịch vụ.",
    TRANSPORT_ERROR: "Chưa gửi hoặc nhận được yêu cầu. Kiểm tra kết nối và thử lại.",
    SERVICE_UNAVAILABLE: "Dịch vụ chưa sẵn sàng. Vui lòng thử lại sau.",
  };

  function lookup(values, key, fallback) {
    return Object.hasOwn(values, key) ? values[key] : fallback;
  }

  function person(record) {
    if (record?.display_name?.trim() && record.display_name !== record.username) return record.display_name;
    const login = record?.username || record?.id || "";
    return login.replace(/^[pr]_/, "").replace(/[_.-]+/g, " ").trim()
      .replace(/(^|\s)\p{L}/gu, letter => letter.toLocaleUpperCase("vi")) || "Tài khoản chưa rõ";
  }

  function documentName(record) {
    const title=record?.title?.trim().replace(/\.(txt|csv|pdf)$/i, "") || "Tài liệu chưa rõ tên";
    const generated=/^restricted-demo-[0-9a-f]{6}$/i.test(title)?"Tài liệu thử quyền Hạn chế":
      /^federation-verification-[0-9a-f]{8}$/i.test(title)?"Tài liệu thử tải và thu hồi phiên":"";
    if(!generated) return title;
    const created=record.created_at;
    const date=new Date(typeof created==='number'?created*1000:created);
    return Number.isNaN(date.getTime())?generated:`${generated} · ${date.toLocaleString('vi-VN')}`;
  }

  function modeOptions(select) {
    for (const option of select.options) option.textContent = lookup(modes, option.value)?.name || option.textContent;
  }

  return {modes, modeOptions, person, documentName,
    mode: value => lookup(modes, value)?.name || "Cách kiểm tra chưa rõ",
    role: value => lookup(roles, value, "Vai trò chưa rõ"),
    department: value => lookup(departments, value, ""),
    organization: value => lookup(organizations, value, "Đơn vị chưa rõ"),
    label: value => lookup(labels, value, "Chưa rõ mức bảo vệ"),
    action: value => lookup(actions, value, "Thao tác khác"),
    reason: (value, fallback = "Chưa thể hoàn tất yêu cầu. Mở chi tiết kỹ thuật để kiểm tra.") => lookup(messages, value, fallback),
  };
})();
