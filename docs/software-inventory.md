# Môi trường và phiên bản phần mềm

## Môi trường thử nghiệm

Nguyên mẫu chạy trên Windows với WSL 2, môi trường Linux tên `bmdl-demo`, Docker Engine và Docker Compose. Web mở trên máy tại `http://localhost:8088`; không cần GPU hoặc Docker Desktop.

Dự án đặt tại `E:\btl_bao_mat_Du_lieu`. Hồ sơ vận hành và ổ đĩa của môi trường Linux được đặt trong phần `runtime/` của dự án. Dữ liệu container còn tồn tại sau khi dừng; kết quả kiểm tra nằm trong `results/`.

## Bộ phiên bản dùng trong bằng chứng đã lưu

| Thành phần | Phiên bản |
|---|---|
| Python | 3.12.15 |
| FastAPI | 0.143.1 |
| Uvicorn | 0.54.0 |
| HTTPX | 0.28.1 |
| PyJWT | 2.15.1 |
| psycopg | 3.3.6 |
| cryptography | 50.0.2 |
| Keycloak | 26.8.0 |
| OPA | 1.21.2 |
| OpenBao | 2.7.1 |
| PostgreSQL | 17.11 |
| NGINX | 1.30.6 |
| Docker Engine | 29.8.2 |
| Docker Compose | 5.1.4 |

Bảng phản ánh bộ phiên bản ghi trong dự án và lượt bằng chứng đã lưu, không phải tuyên bố về phiên bản mới nhất trên Internet hoặc trạng thái dịch vụ đang chạy hôm nay. Khi tái lập trên máy khác, đối chiếu bản kiểm kê của lượt mới.

[Danh sách thư viện đã ghim](../requirements.lock.txt), [ảnh dịch vụ đã ghim](../infra/images.lock.json) và [cấu hình khóa ảnh](../compose.lock.yaml) xác định bộ cài. Ảnh hạ tầng được cố định bằng mã băm, không chỉ bằng tên phiên bản.

[Bản kiểm kê dùng cho báo cáo](../results/report-20261102/federation-environment.json) ghi môi trường, phiên bản dịch vụ, ảnh container và dấu vân tay mã nguồn ở thời điểm thu thập. [Bản kiểm kê gần nhất](../results/federation-environment.json) có thể được thay khi khởi động lại môi trường. Hai tệp có thể thuộc hai thời điểm khác nhau.

## Dịch vụ và giới hạn tài nguyên

| Dịch vụ | Vai trò | Giới hạn bộ nhớ cấu hình |
|---|---|---|
| `postgres` | Lưu ba cơ sở dữ liệu được phân quyền riêng | 512 MiB |
| `keycloak` | Dịch vụ đăng nhập dùng chung | 1 GiB |
| `opa` | Đánh giá quy tắc truy cập | 256 MiB |
| `openbao` | Mã hóa, giải mã và quản lý khóa | 512 MiB |
| `api` | Xử lý yêu cầu tài liệu | 768 MiB |
| `gateway` | Cổng xác minh thiết bị | 128 MiB |
| `partner` | Quản lý tài khoản và thiết bị đối tác | 256 MiB |
| `coordinator` | Quản lý phiên và thu hồi | 256 MiB |
| `lab` | Web và công cụ thử nghiệm | 1 GiB |

Đây là chín dịch vụ của bản hiện tại. `api-baseline` thuộc cấu hình nguyên mẫu cũ, không tham gia so sánh ba cách cập nhật trạng thái. Giới hạn cấu hình không phải lượng bộ nhớ luôn sử dụng thực tế.

Tình huống khôi phục dữ liệu phiên tạo thêm cơ sở dữ liệu tạm và container bộ điều phối tạm, rồi dọn các tài nguyên do lượt kiểm tra tạo. Thời gian chạy bộ kiểm tra không phải độ trễ xử lý một yêu cầu hoặc số đo chịu tải doanh nghiệp.

## Khi cần mô tả môi trường trong báo cáo

Ghi hệ điều hành, WSL, tài nguyên máy, phiên bản dịch vụ và ngày chạy từ bản kiểm kê tương ứng. Phân biệt cấu hình giới hạn với tài nguyên quan sát. Nếu mã hoặc phiên bản thay đổi, cần một lượt kiểm tra và bản kiểm kê mới trước khi dùng kết quả để kết luận.

[Bản kiểm kê máy chủ](../results/report-20261102/host-reference.json) được thu thập ngày 19/10/2026 và dùng làm thông tin tham chiếu về máy thử. Tệp này không thay thế bản kiểm kê dịch vụ của lượt ngày 02/11.
