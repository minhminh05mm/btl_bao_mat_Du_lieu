# Cài và tái lập môi trường thử nghiệm

## Điều kiện

Sử dụng Windows đã bật WSL 2 và PowerShell. Đặt dự án tại `E:\btl_bao_mat_Du_lieu`; một số công cụ vận hành còn giả định vị trí này. Lần cài đầu cần Internet. Chương trình kiểm tra tối thiểu 10 GB trống trên ổ C và 8 GB trên ổ E trước khi tiếp tục.

Dùng bản mã nguồn và các tệp khóa phiên bản cùng nhau. Để chương trình sinh mật khẩu, chứng thư và khóa riêng trên máy mới; không chép `.env` hoặc `runtime/` từ máy khác.

## Khởi động

```powershell
Set-Location -LiteralPath 'E:\btl_bao_mat_Du_lieu'
powershell -ExecutionPolicy Bypass -File .\Start-Demo.ps1 -OpenBrowser
```

Lần đầu chương trình chuẩn bị môi trường Linux, Docker, cấu hình dịch vụ, dữ liệu, chứng thư và khóa; sau đó đăng ký liên kết tài khoản. Những lần sau giữ dữ liệu và thực hiện đăng ký lại theo cách không tạo trùng.

Nếu thay đổi mã nguồn chạy trong ảnh ứng dụng, khởi động bằng tùy chọn dựng lại:

```powershell
powershell -ExecutionPolicy Bypass -File .\Start-Demo.ps1 -Rebuild -OpenBrowser
```

Mở [web](http://localhost:8088) và làm theo [hướng dẫn nhanh](huong_dan_nhanh.md). Không cần dịch vụ đám mây Microsoft hoặc Google để tái lập.

## Chạy bộ kiểm tra hiện tại

Trên web chọn Kết quả kiểm tra rồi Chạy tất cả tình huống. Hoặc dùng PowerShell sau khi các dịch vụ đã sẵn sàng:

```powershell
wsl -d bmdl-demo -u root -- docker exec bmdl-lab-1 python -m federation.verify
wsl -d bmdl-demo -u root -- docker exec bmdl-lab-1 python -m pytest tests/test_federation_proofs.py tests/test_auth_verifier.py tests/test_scenario_harness.py -q
wsl -d bmdl-demo -u root -- docker exec bmdl-opa-1 /opa test /policies
```

Ba lệnh có phạm vi riêng: các tình huống sử dụng thực tế, kiểm tra mã Python và kiểm tra quy tắc Rego. Không cộng ba số kết quả thành số tình huống sử dụng thực tế.

Bộ kiểm tra chủ động đổi trạng thái mẫu và thử lỗi, vì vậy không trình diễn thủ công đồng thời. Khi kết thúc, bộ kiểm tra khôi phục cấu hình, thu hồi các phiên do nó tạo và giữ tài liệu thử. Tình huống khôi phục sử dụng cơ sở dữ liệu riêng, không khôi phục đè lên cơ sở dữ liệu đang dùng.

Có thể gọi bộ tình huống hiện tại bằng `powershell -ExecutionPolicy Bypass -File .\Run-Tests.ps1`. Lệnh này gọi `federation.verify`, tương đương bộ kiểm tra trên web. Tham số `-Benchmark` vẫn dành riêng cho phép đo hiệu năng của nguyên mẫu trước; kết quả đó không thuộc 19 tình huống hiện tại. Không chạy đồng thời các bộ kiểm tra.

## Đọc và lưu kết quả

Mở `results/federation-latest.html` hoặc các tệp JSON, CSV cùng tên. Mỗi lần chạy còn tạo bản mang dấu thời gian. Đối chiếu [ma trận kiểm tra](test-matrix.md) và [cách đọc bằng chứng](ket_qua_kiem_chung.md).

Khởi động tạo bản kiểm kê `results/federation-environment.json`. Khi lưu một lượt để đưa vào báo cáo, giữ kết quả và bản môi trường tương ứng cùng nhau. Không suy ra kết quả máy mới từ các tệp có sẵn trong kho mã.

Mật khẩu thủ công có thể xem trên máy cài bằng:

```powershell
.\Show-Credentials.ps1
```

## Dừng sau khi sử dụng

```powershell
.\Stop-Demo.ps1
```

Lệnh dừng container và môi trường Linux riêng, giữ dữ liệu. Lần khởi động tiếp theo vô hiệu hóa phiên từ lần chạy trước; tạo phiên mới khi tiếp tục thử.

Các ảnh và kết quả cũ được giữ theo ngày để truy vết. Bản lưu dùng trong báo cáo ngày 02/11/2026 nằm ở [thư mục bằng chứng](../results/report-20261102/).
