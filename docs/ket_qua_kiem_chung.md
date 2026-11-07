# Kết quả kiểm tra và nơi mở bằng chứng

## Kết quả dùng trong báo cáo

Lượt ngày 02/11/2026 có ba tập kết quả riêng:

| Tập kiểm tra | Kết quả | Phạm vi |
|---|---|---|
| Tình huống sử dụng thực tế | 19/19 đạt | Đăng nhập, phiên, quyền tài liệu, thu hồi, lỗi thành phần và khôi phục phiên |
| Mã xử lý Python | 42/42 đạt | Các phần kiểm tra thông tin trạng thái, xác thực và bộ chạy tình huống được chọn |
| Quy tắc truy cập Rego | 31/31 đạt | Điều kiện quyền của chính sách tài liệu |

Không cộng ba số này thành số tình huống sử dụng thực tế. Ngày sửa hướng dẫn không phải ngày chạy lại kiểm tra.

Bản lưu cố định nằm trong [thư mục bằng chứng ngày 02/11/2026](../results/report-20261102/): [JSON chi tiết](../results/report-20261102/federation-latest.json), [CSV](../results/report-20261102/federation-latest.csv), [HTML](../results/report-20261102/federation-latest.html), [kết quả Python](../results/report-20261102/federation-python-tests.txt), [kết quả Rego](../results/report-20261102/federation-policy-tests.txt) và [môi trường](../results/report-20261102/federation-environment.json).

## Ba quan sát chính

| Tình huống | Kiểm tra khi đăng nhập | Thu hồi theo thông báo | Thu hồi theo thông báo và tự kiểm tra lại |
|---|---|---|---|
| Tài khoản, thiết bị và quyền đều hợp lệ | Cho phép | Cho phép | Cho phép |
| Tài khoản bị khóa, phiên còn hạn, thông báo đến được | Có thể tiếp tục tải | Thu hồi và từ chối | Thu hồi và từ chối |
| Thông báo khóa bị mất | Có thể tiếp tục tải | Có thể tiếp tục tải | Hỏi lại, phát hiện và thu hồi |
| Không hỏi lại được khi thông tin trạng thái đã hết hạn | Có thể tiếp tục tải | Có thể tiếp tục tải nếu chưa nhận thay đổi | Tạm dừng, không trả nội dung |

Quyền với tài liệu giữ nguyên giữa ba cách. Sự khác nhau cho thấy tác dụng của thông báo, việc tự hỏi lại và giới hạn thời gian dùng thông tin cũ.

## Khôi phục cơ sở dữ liệu phiên

Tình huống khôi phục tạo bản sao thật của cơ sở dữ liệu phiên và khởi động dịch vụ bộ điều phối tạm trên bản đó. Bằng chứng có kích thước, mã băm của bản sao, trạng thái phiên trước khởi động và phản hồi kiểm tra sau khởi động.

Phiên cũ không dùng lại được sau khi dịch vụ khởi động trên bản sao. Cơ sở dữ liệu tạm được tách khỏi dữ liệu đang dùng. Kết quả này chưa xác nhận việc khôi phục đầy đủ Keycloak, thiết bị, dữ liệu tài liệu và hạ tầng của cả hai bên.

## Kết quả gần nhất trên web

Mục Kết quả kiểm tra hiển thị tên tình huống, Đạt hoặc Không đạt, giải thích và thời điểm. Mở Tải bằng chứng kỹ thuật để lấy dữ liệu chi tiết.

Các tệp [JSON gần nhất](../results/federation-latest.json), [CSV gần nhất](../results/federation-latest.csv) và [HTML gần nhất](../results/federation-latest.html) có thể được thay khi chạy lại. Mỗi lượt còn lưu tệp mang dấu thời gian. Khi dẫn kết quả, giữ đúng lượt, ngày, bộ mã và bản kiểm kê môi trường.

Ảnh trong thư mục bằng chứng phản ánh giao diện tại thời điểm chụp. Một số ảnh lịch sử có cách gọi cũ; dùng tên hiện tại trên web và trong [script](script_thuyet_trinh_10_phut.md) khi trình bày. Kết quả của nguyên mẫu trước khi bổ sung bộ điều phối không được tính vào 19 tình huống hiện tại.

Xem [ma trận kiểm tra](test-matrix.md) và [giới hạn diễn giải](verification-review.md).

## Ảnh minh họa hiện hành

[Ảnh web ngày 07/11/2026](../results/report-20261107-ui/) được dùng trong [báo cáo chính](bao_cao/BaoCao_BMDL_Nhom03_ZeroTrust_DaSua.docx). Ảnh minh họa thao tác và phản hồi, không thay ngày hoặc số liệu của bộ kiểm tra cố định ngày 02/11/2026.
