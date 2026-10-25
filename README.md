# Web demo kho tài liệu Zero Trust

Nguyên mẫu thiết kế và triển khai kiến trúc an toàn cho kho tài liệu nội bộ, có quản lý nhân viên, phân loại tài liệu, kiểm soát từng yêu cầu và kiểm chứng theo tình huống.

## Đọc tài liệu

- Bắt đầu tại [mục lục và thứ tự đọc](docs/muc_luc.md).
- Muốn hiểu bài trước: [kiến thức nền](docs/kien_thuc_nen.md).
- Muốn dùng web: [hướng dẫn nhanh](docs/huong_dan_nhanh.md).
- Muốn xem kết quả đã chạy: [kết quả kiểm chứng](docs/ket_qua_kiem_chung.md).

## Bật và tắt web

Điều kiện: Windows đã bật WSL 2, có kết nối Internet, ổ C còn tối thiểu 10 GB và ổ E còn tối thiểu 8 GB. Giải nén hoặc clone mã nguồn đúng vào `E:\btl_bao_mat_Du_lieu` vì bản hiện tại còn sử dụng đường dẫn này trong chức năng khôi phục. Lần chạy đầu tải môi trường và các container; không cần cài Docker Desktop riêng.

Mở PowerShell và chạy:

```powershell
Set-Location -LiteralPath 'E:\btl_bao_mat_Du_lieu'
powershell -ExecutionPolicy Bypass -File .\Start-Demo.ps1 -OpenBrowser
```

Địa chỉ: [web demo](http://localhost:8088/#guide). Dừng container và môi trường WSL khi không dùng:

```powershell
.\Stop-Demo.ps1
```

Bật/tắt giữ dữ liệu. Đặt lại dữ liệu hoặc chạy bộ kiểm chứng chuẩn có thể thay tài liệu và lịch sử bằng bộ mẫu; đọc [hướng dẫn](docs/huong_dan_nhanh.md) trước khi thực hiện.

Toàn bộ hướng dẫn nằm trong `docs/`; mã nguồn và kết quả gốc giữ trong các thư mục tương ứng. Cập nhật tài liệu ngày 25/10/2026.

## Dữ liệu riêng trên từng máy

Mật khẩu, chứng thư, khóa, dữ liệu vận hành và môi trường WSL không được đưa lên GitHub. Chúng được tạo khi khởi động lần đầu. Chạy `.\Show-Credentials.ps1` tại máy cài đặt để xem tài khoản của máy đó. Kết quả và ảnh trong `results/` là bằng chứng thử nghiệm đã có, không phải dữ liệu đang chạy trên máy mới.
