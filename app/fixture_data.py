"""Reviewed business fixtures; no external data, random padding, or live secrets.

The catalog describes the baseline dataset for the trusted experiment console.
It is not an authorization source. Current labels and ownership come from SQL.
"""
import hashlib

DATASET_VERSION = "business-v1"
DEPARTMENTS = {"A": "Phòng Kinh doanh", "B": "Phòng Vận hành"}
CLASSIFICATION_RULES = {
    "internal": {
        "name": "Nội bộ",
        "criterion": "Quy trình, lịch làm việc hoặc số liệu tổng hợp phục vụ phối hợp trong phòng; không có giá chào riêng, phương án đàm phán hay điểm yếu chưa xử lý.",
        "consequence": "Phát tán sai phạm vi có thể gây nhầm lẫn công việc; chưa trực tiếp làm lộ bí quyết giao dịch hoặc phương án bảo vệ trọng yếu.",
        "access": "Nhân viên và trưởng phòng cùng phòng ban được đọc khi danh tính, thiết bị và thời hạn hợp lệ.",
        "retention_days": 180,
    },
    "confidential": {
        "name": "Mật",
        "criterion": "Chi tiết chưa công bố của một dự án, báo giá, phân tích sự cố hoặc dự toán; chủ sở hữu và trưởng phòng cần sử dụng theo nhiệm vụ.",
        "consequence": "Tiết lộ có thể làm giảm lợi thế thương mại hoặc làm lộ chi tiết vận hành của một dự án.",
        "access": "Nhân viên chỉ đọc tài liệu do mình sở hữu trong cùng phòng; trưởng phòng đọc trong phạm vi phòng.",
        "retention_days": 90,
    },
    "restricted": {
        "name": "Hạn chế",
        "criterion": "Ngưỡng quyết định ngoại lệ, phân bổ ngân sách chưa duyệt, điểm yếu chưa khắc phục hoặc kế hoạch phục hồi trọng yếu cần phê duyệt giới hạn theo người nhận, tài liệu, phiên bản, hành động và thời hạn.",
        "consequence": "Tiết lộ có thể làm mất giới hạn thương lượng hoặc tăng khả năng gây gián đoạn dịch vụ; chỉ quyền sở hữu chưa đủ để tải nội dung.",
        "access": "Trưởng phòng cùng phòng chỉ tải khi có grant đúng người, tài liệu, phiên bản, hành động và thời hạn; người duyệt khác người nhận.",
        "retention_days": 30,
    },
}

# id, owner, title, document type, classification rationale, substantive example,
# and the four work items used in its deterministic business appendix.
_DEFINITIONS = (
    ("A-I01", "alice", "Quy trình tiếp nhận yêu cầu báo giá.txt", "Quy trình nghiệp vụ",
     "Hướng dẫn thao tác chung trong phòng, không chứa báo giá của từng khách hàng hoặc mức chiết khấu riêng.",
     "Yêu cầu mới được gán mã cơ hội, kiểm tra đủ mô tả nhu cầu rồi chuyển người phụ trách; số tiền được lập trong hồ sơ báo giá riêng.",
     ("Kiểm tra mô tả nhu cầu", "Gán mã cơ hội giả lập", "Chuyển yêu cầu đúng nhóm", "Ghi nhận lịch phản hồi")),
    ("A-I02", "anna", "Lịch phối hợp tư vấn tháng 10.txt", "Lịch phối hợp",
     "Lịch phân ca theo vai trò để dùng trong phòng; không có thông tin liên hệ cá nhân hoặc nội dung đàm phán của khách hàng.",
     "Các khung tư vấn được chia theo buổi và nhóm sản phẩm; khi đổi lịch, nhóm nhận việc xác nhận lại mốc phản hồi trên sổ phối hợp.",
     ("Rà soát khung tư vấn", "Phân công vai trò hỗ trợ", "Xác nhận ca thay thế", "Tổng hợp lịch đã nhận")),
    ("A-I03", "adam", "Hướng dẫn cập nhật cơ hội bán hàng.txt", "Hướng dẫn sử dụng",
     "Quy ước cập nhật trạng thái cơ hội, không bao gồm mức giá, xác suất trúng thầu riêng hoặc cam kết thương mại chưa công bố.",
     "Một cơ hội đi qua các trạng thái tiếp nhận, làm rõ, dự thảo và đóng; mọi thay đổi cần có mô tả công việc đã hoàn thành.",
     ("Kiểm tra trạng thái cơ hội", "Chuẩn hóa mô tả công việc", "Rà soát mốc dự kiến", "Đóng mục đã hoàn thành")),
    ("A-I04", "alice", "Báo cáo tổng hợp lượt tư vấn tháng 10.txt", "Báo cáo tổng hợp",
     "Chỉ chứa số lượt theo nhóm dịch vụ, không gắn khách hàng cụ thể, giá bán hoặc hồ sơ giao dịch.",
     "Bảng tổng hợp chia lượt tư vấn thành triển khai mới, mở rộng và hỗ trợ lựa chọn; các chỉ số chỉ phục vụ cân đối nguồn lực trong phòng.",
     ("Gom lượt theo nhóm dịch vụ", "Đối chiếu tổng số lượt", "Kiểm tra không có hồ sơ riêng", "Lập nhận xét nguồn lực")),
    ("A-I05", "anna", "Biên bản họp điều phối kinh doanh.txt", "Biên bản phối hợp",
     "Ghi nhận việc chung và trách nhiệm theo vai trò; không ghi giá chào hoặc giới hạn thương lượng của hợp đồng.",
     "Cuộc họp mô phỏng thống nhất cách tiếp nhận công việc, lịch rà soát hằng tuần và cơ chế chuyển yêu cầu quá hạn cho trưởng phòng.",
     ("Tổng hợp việc tồn", "Thống nhất lịch rà soát", "Phân công người theo dõi", "Xác nhận kết luận họp")),
    ("A-C01", "alice", "Dự thảo báo giá dự án Mây Xanh.txt", "Dự thảo thương mại",
     "Có đơn giá và cấu phần chào bán chưa công bố của một dự án; chia sẻ rộng có thể làm lộ lợi thế thương mại.",
     "Dự án mô phỏng MX-01 gồm 12 gói tư vấn, đơn giá dự thảo 4.800.000 đồng/gói; đây là số giả lập, chưa phải giá đã cam kết với khách hàng.",
     ("Đối chiếu phạm vi chào bán", "Kiểm tra đơn giá dự thảo", "Rà soát điều kiện thanh toán", "Trình trưởng phòng xem xét")),
    ("A-C02", "anna", "Kế hoạch đàm phán dự án Bình Minh.txt", "Kế hoạch đàm phán",
     "Có thứ tự ưu tiên và điều kiện trao đổi riêng của dự án chưa công bố; chỉ chủ hồ sơ và trưởng phòng cần dùng.",
     "Hồ sơ mô phỏng BM-02 ưu tiên làm rõ thời gian bàn giao và phạm vi hỗ trợ trước khi thương lượng lịch thanh toán; không có thông tin người liên hệ thật.",
     ("Làm rõ yêu cầu dự án", "Xếp thứ tự nội dung trao đổi", "Kiểm tra điều kiện dự thảo", "Ghi nhận phương án trình duyệt")),
    ("A-C03", "adam", "Dự toán doanh thu theo cơ hội quý IV.txt", "Dự toán kinh doanh",
     "Có giá trị và dự kiến chuyển đổi theo từng cơ hội; đây là thông tin quản trị chưa công bố của phòng.",
     "Ba cơ hội mô phỏng CH-01, CH-02 và CH-03 có doanh thu dự kiến 180, 240 và 120 triệu đồng; các con số không phản ánh doanh nghiệp thực.",
     ("Rà soát giá trị từng cơ hội", "Đối chiếu mốc dự kiến", "Kiểm tra giả định chuyển đổi", "Tổng hợp phương án doanh thu")),
    ("A-R01", "alice", "Ngưỡng chiết khấu ngoại lệ dự án Mây Xanh.txt", "Phương án thương mại ngoại lệ",
     "Có giới hạn nhượng bộ và mức chấp thuận ngoại lệ chưa công bố; lộ nội dung có thể làm mất giới hạn thương lượng, nên cần grant giới hạn theo người nhận, tài liệu, phiên bản, hành động và thời hạn.",
     "Phương án mô phỏng MX-01 xem xét chiết khấu ngoại lệ tối đa 7 phần trăm khi thay đổi phạm vi hỗ trợ; mọi quyết định cuối cùng phải được phê duyệt riêng.",
     ("Kiểm tra điều kiện ngoại lệ", "Đối chiếu giới hạn nhượng bộ", "Xác định thẩm quyền phê duyệt", "Rà soát hiệu lực phương án")),
    ("A-R02", "adam", "Phương án phân bổ ngân sách kinh doanh.txt", "Phương án ngân sách chưa duyệt",
     "Có mức dự phòng và thứ tự ưu tiên ngân sách chưa được duyệt; tác động vượt một hồ sơ dự án, nên giới hạn người sử dụng bằng phê duyệt có thời hạn.",
     "Phương án mô phỏng phân bổ 360 triệu đồng cho quý IV, gồm dự phòng 60 triệu đồng; số liệu chỉ minh họa một quyết định chưa được thông qua.",
     ("Đối chiếu hạn mức dự kiến", "Rà soát khoản dự phòng", "Kiểm tra thứ tự ưu tiên", "Ghi nhận điều kiện thông qua")),
    ("B-I01", "bob", "Quy trình bàn giao ca vận hành.txt", "Quy trình vận hành",
     "Hướng dẫn bàn giao việc chung theo vai trò, không chứa sơ đồ hệ thống hoặc phương án ứng phó trọng yếu.",
     "Ca trực ghi việc đã hoàn thành, việc còn theo dõi và đầu mối theo vai trò; mọi dịch vụ trong ví dụ đều là đối tượng mô phỏng.",
     ("Đối chiếu sổ ca", "Kiểm tra việc còn theo dõi", "Xác nhận vai trò tiếp nhận", "Ghi thời điểm bàn giao")),
    ("B-I02", "bea", "Lịch bảo trì dịch vụ nội bộ.txt", "Lịch bảo trì",
     "Chỉ mô tả khung phối hợp và nhóm công việc; không có địa chỉ hệ thống, cấu hình đặc quyền hoặc điểm yếu chưa khắc phục.",
     "Lịch mô phỏng dành khung cuối ngày cho kiểm tra định kỳ, thông báo trước thay đổi và ghi nhận hoàn thành; không công bố thông số truy cập dịch vụ.",
     ("Xác nhận khung bảo trì", "Thông báo vai trò liên quan", "Kiểm tra điều kiện bàn giao", "Ghi nhận hoàn thành lịch")),
    ("B-I03", "brian", "Hướng dẫn ghi nhận sự cố.txt", "Hướng dẫn nghiệp vụ",
     "Biểu mẫu và quy ước ghi nhận chung, không bao gồm nguyên nhân kỹ thuật hoặc lỗ hổng của từng hệ thống.",
     "Một phiếu sự cố cần mã phiếu, thời điểm, ảnh hưởng theo nhóm dịch vụ và vai trò tiếp nhận; chi tiết kỹ thuật được lưu trong hồ sơ riêng có nhãn phù hợp.",
     ("Kiểm tra trường bắt buộc", "Gán nhóm ảnh hưởng", "Xác nhận vai trò tiếp nhận", "Theo dõi thời điểm cập nhật")),
    ("B-I04", "bob", "Báo cáo tổng hợp yêu cầu hỗ trợ.txt", "Báo cáo tổng hợp",
     "Chỉ có số lượng yêu cầu theo nhóm và thời gian xử lý tổng hợp, không lộ hồ sơ riêng hoặc thông số hạ tầng.",
     "Báo cáo mô phỏng gom yêu cầu thành hướng dẫn sử dụng, kiểm tra định kỳ và phối hợp thay đổi; không có dữ liệu của người dùng thật.",
     ("Gom yêu cầu theo nhóm", "Đối chiếu số đã xử lý", "Kiểm tra số liệu tổng hợp", "Ghi nhận nhận xét quy trình")),
    ("B-I05", "bea", "Biên bản họp cải tiến vận hành.txt", "Biên bản phối hợp",
     "Nêu việc cải tiến quy trình chung, không mô tả điểm yếu hoặc thứ tự khôi phục dịch vụ trọng yếu.",
     "Nhóm mô phỏng thống nhất cách đặt mã phiếu, cập nhật sổ bàn giao và rà soát yêu cầu tồn; thay đổi kỹ thuật cần hồ sơ phê duyệt riêng.",
     ("Tổng hợp vướng mắc quy trình", "Thống nhất mẫu ghi nhận", "Phân công vai trò rà soát", "Xác nhận công việc tiếp theo")),
    ("B-C01", "bob", "Kế hoạch triển khai dịch vụ dự án Mây Xanh.txt", "Kế hoạch triển khai dự án",
     "Có trình tự và nhu cầu nguồn lực riêng của dự án chưa công bố; chia sẻ rộng có thể làm lộ chi tiết vận hành.",
     "Dự án mô phỏng MX-01 triển khai theo ba đợt chuẩn bị, kiểm tra và bàn giao; các mã tài nguyên MP-01 và MP-02 không tham chiếu hệ thống thực.",
     ("Đối chiếu phạm vi triển khai", "Rà soát nguồn lực dự án", "Kiểm tra điều kiện nghiệm thu", "Ghi nhận mốc bàn giao")),
    ("B-C02", "bea", "Biên bản phân tích sự cố dự án Bình Minh.txt", "Phân tích sự cố dự án",
     "Có diễn biến và ảnh hưởng của một sự cố mô phỏng riêng; hồ sơ do chủ phụ trách và trưởng phòng sử dụng để xử lý.",
     "Phiếu mô phỏng SC-BM-02 mô tả gián đoạn 18 phút do một cấu hình kiểm tra không phù hợp; không chứa địa chỉ thật hoặc hướng dẫn khai thác hệ thống.",
     ("Đối chiếu diễn biến sự cố", "Rà soát phạm vi ảnh hưởng", "Kiểm tra giả thuyết nguyên nhân", "Ghi nhận việc phòng ngừa")),
    ("B-C03", "brian", "Dự toán chi phí vận hành quý IV.txt", "Dự toán vận hành",
     "Có chi phí dự kiến theo nhóm dịch vụ và phương án sử dụng nguồn lực chưa công bố của phòng.",
     "Dự toán mô phỏng dành 90 triệu đồng cho kiểm tra định kỳ, 75 triệu đồng cho hỗ trợ và 45 triệu đồng cho thử nghiệm phục hồi; không phải số liệu thực.",
     ("Đối chiếu hạng mục chi phí", "Kiểm tra giả định nguồn lực", "Rà soát mốc sử dụng", "Tổng hợp phương án chi phí")),
    ("B-R01", "bob", "Phương án xử lý điểm yếu chưa khắc phục.txt", "Phương án bảo vệ trọng yếu",
     "Nêu tình trạng chưa khắc phục và thứ tự giảm thiểu của tài nguyên mô phỏng; lộ nội dung có thể tăng nguy cơ gián đoạn, nên chỉ tải bằng grant hợp lệ.",
     "Tài nguyên mô phỏng MP-03 cần rà soát phân quyền trước đợt bàn giao; hồ sơ chỉ nêu việc kiểm tra và trách nhiệm, không có mã khai thác hoặc bí mật truy cập.",
     ("Xác nhận phạm vi cần rà soát", "Ưu tiên biện pháp giảm thiểu", "Kiểm tra trách nhiệm phê duyệt", "Ghi nhận điều kiện kết thúc")),
    ("B-R02", "brian", "Kế hoạch phục hồi dịch vụ trọng yếu.txt", "Kế hoạch phục hồi trọng yếu",
     "Có thứ tự phục hồi và điều kiện chuyển sang phục vụ của dịch vụ trọng yếu; cần kiểm soát người nhận và thời hạn phê duyệt riêng.",
     "Phương án mô phỏng DV-01 yêu cầu xác minh bản sao, kiểm tra trạng thái thu hồi rồi mới phê duyệt mở lại; không chứa khóa, mật khẩu hoặc vị trí sao lưu thật.",
     ("Đối chiếu bản sao được chọn", "Kiểm tra dữ liệu khôi phục", "Rà soát quyền đã thu hồi", "Xác nhận điều kiện mở lại")),
)


def _make_catalog():
    result = {}
    for doc_id, owner, title, kind, rationale, example, tasks in _DEFINITIONS:
        label = {"I": "internal", "C": "confidential", "R": "restricted"}[doc_id[2]]
        result[doc_id] = {
            "id": doc_id, "title": title, "owner_id": owner,
            "department": doc_id[0], "department_name": DEPARTMENTS[doc_id[0]],
            "baseline_label": label, "document_type": kind,
            "classification_reason": rationale, "synthetic_example": example,
            "tasks": tasks,
        }
    return result


_CATALOG = _make_catalog()


def fixture_definition(doc_id):
    """Return an independent baseline description, never current access rights."""
    if doc_id not in _CATALOG:
        raise ValueError("Unknown baseline fixture")
    return dict(_CATALOG[doc_id])


def fixture_payload(doc_id):
    doc = fixture_definition(doc_id)
    rule = CLASSIFICATION_RULES[doc["baseline_label"]]
    lines = [
        f"BMDL synthetic fixture {doc_id}; dataset {DATASET_VERSION}; no real personal data.",
        "Doanh nghiệp mô phỏng BMDL - tài liệu tổng hợp dùng cho nghiên cứu",
        doc["title"].removesuffix(".txt"),
        f"Mã tài liệu: {doc_id}",
        f"Đơn vị: {doc['department_name']} ({doc['department']})",
        f"Chủ hồ sơ thử nghiệm: {doc['owner_id']}",
        f"Loại tài liệu: {doc['document_type']}",
        f"Nhãn ban đầu: {rule['name']}",
        "Ngày lập giả định: 01/10/2026", "",
        "1. Mục đích và phạm vi",
        "Tài liệu mô tả một tình huống nghiệp vụ giả định để kiểm chứng kiểm soát truy cập. Các mã dự án, số tiền, mốc thời gian và kết quả dưới đây đều được tạo tổng hợp, không phản ánh cá nhân hoặc tổ chức thực.",
        doc["synthetic_example"], "",
        "2. Nội dung và trách nhiệm",
        *[f"2.{i}. {task}. Chủ hồ sơ kiểm tra tính đầy đủ và ghi nhận kết quả trước khi chuyển việc cho vai trò tiếp nhận." for i, task in enumerate(doc["tasks"], 1)],
        "Tài liệu chưa thay thế quyết định phê duyệt nghiệp vụ. Mỗi lần cập nhật cần mô tả nội dung đã đổi và kiểm tra lại người được phép sử dụng.", "",
        "3. Căn cứ phân loại và phạm vi sử dụng",
        doc["classification_reason"], rule["consequence"], rule["access"],
        "Nhãn được xác định từ ý nghĩa nghiệp vụ và hậu quả khi tiết lộ; hệ thống không tự suy ra nhãn bằng từ khóa. Quyền sở hữu không tự động cho phép bỏ qua nhãn, điều kiện thiết bị hoặc phê duyệt.", "",
        "4. Sổ theo dõi công việc mô phỏng",
    ]
    # Structured project records replace random padding. Fixed dates and order
    # keep the exact bytes and hash reproducible across processes and resets.
    for i in range(1, 25):
        task = doc["tasks"][(i-1) % 4]
        outcome = ("đã ghi nhận đủ mô tả và chuyển bước rà soát",
                   "cần bổ sung xác nhận của vai trò tiếp nhận",
                   "đang đối chiếu điều kiện trước khi hoàn tất")[(i-1) % 3]
        lines.extend([
            f"Hạng mục {doc_id}-HM{i:02d} - mốc giả định {1+(i-1)%20:02d}/10/2026",
            f"Công việc: {task.lower()}; mã hồ sơ liên quan MP-{i:03d}.",
            f"Người theo dõi: tài khoản thử nghiệm {doc['owner_id']}; đơn vị {doc['department_name']}.",
            f"Kết quả mô phỏng: {outcome}.",
            "Điều kiện chuyển bước: kiểm tra phạm vi công việc, người tiếp nhận và nội dung được phép chia sẻ. Nếu điều kiện chưa đầy đủ, giữ trạng thái chờ và ghi rõ lý do.", "",
        ])
    lines.extend([
        "5. Rà soát và giới hạn sử dụng",
        "Thời hạn lưu giữ áp dụng theo metadata do máy chủ quản lý; mốc minh họa trong nội dung không gia hạn quyền đọc. Thay đổi nhãn, thu hồi quyền hoặc hủy tài liệu cần được xét ở yêu cầu tiếp theo.",
        "Tất cả dữ liệu trong tài liệu là giả lập. Nội dung đã tải hợp lệ có thể được lưu ngoài hệ thống; đổi quyền sau đó không thu hồi được bản rõ đã nhận.", "",
    ])
    payload = "\n".join(lines).encode("utf-8")
    if not 12000 <= len(payload) <= 32000:
        raise ValueError("Business fixture outside reviewed size range")
    return payload


def dataset_catalog():
    """Operator-only baseline catalog; intentionally excludes document content."""
    return {
        "dataset_version": DATASET_VERSION,
        "synthetic": True,
        "scope": "20 tài liệu của doanh nghiệp mô phỏng BMDL; nhãn theo giả định nghiệp vụ, không phải cấp độ bí mật nhà nước.",
        "classification_method": "Chủ sở hữu dữ liệu xác định thủ công từ nội dung và hậu quả tiết lộ; không phân loại tự động. Nhãn hiện hành do máy chủ kiểm soát.",
        "departments": dict(DEPARTMENTS),
        "rules": {key: dict(value) for key, value in CLASSIFICATION_RULES.items()},
        "items": [{key: value for key, value in doc.items() if key not in {"tasks", "synthetic_example"}}
                  for doc in _CATALOG.values()],
    }


def dataset_manifest():
    result = dataset_catalog()
    for item in result["items"]:
        payload = fixture_payload(item["id"])
        item["size_bytes"] = len(payload)
        item["sha256"] = hashlib.sha256(payload).hexdigest()
    return result
