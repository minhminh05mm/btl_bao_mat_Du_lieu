# Kho tài liệu Zero Trust

Hệ thống thử nghiệm cách thu hồi quyền truy cập kho khi tài khoản hoặc thiết bị không còn hợp lệ. Bên quản lý tài khoản theo dõi người dùng và thiết bị; kho tài liệu quản lý quyền và nội dung; bộ điều phối theo dõi phiên truy cập giữa hai bên.

Nguyên mẫu tham chiếu Microsoft Zero Trust và Google BeyondCorp, chạy bằng công cụ miễn phí trên máy cá nhân. Các dịch vụ cục bộ mô phỏng trách nhiệm của hai bên quản lý độc lập.

## Khởi động và dừng

Máy cần Windows đã bật WSL 2, ổ E có thể ghi và tối thiểu 10 GB trống trên ổ C, 8 GB trên ổ E. Nếu đã cài Git, mở PowerShell và tải dự án:

```powershell
Set-Location -LiteralPath 'E:\'
git clone https://github.com/minhminh05mm/btl_bao_mat_Du_lieu.git
```

Hoặc chọn Code → Download ZIP trên GitHub, giải nén để `Start-Demo.ps1` nằm trực tiếp trong `E:\btl_bao_mat_Du_lieu`. Không chép cấu hình bí mật từ máy khác. Sau khi tải, chạy:

```powershell
Set-Location -LiteralPath 'E:\btl_bao_mat_Du_lieu'
powershell -ExecutionPolicy Bypass -File .\Start-Demo.ps1 -OpenBrowser
```

Web mở tại [localhost:8088](http://localhost:8088). Lần đầu cần Internet để tải các thành phần. Chương trình yêu cầu tối thiểu 10 GB trống trên ổ C và 8 GB trên ổ E. Không cần Docker Desktop hoặc tài khoản đám mây trả phí.

Khi không sử dụng:

```powershell
.\Stop-Demo.ps1
```

Dữ liệu được giữ lại. Khi dịch vụ phiên khởi động lại, người dùng phải đăng nhập để tạo phiên mới.

## Thử tình huống chính

1. Chọn Nhân viên đối tác · Kinh doanh, thiết bị đã đăng ký của tài khoản và cách Thu hồi theo thông báo và tự kiểm tra lại.
2. Nhấn Đăng nhập và tạo phiên; chờ thành công.
3. Chọn Quy trình tiếp nhận yêu cầu báo giá · Nội bộ, chọn Tải tài liệu, nhấn Gửi yêu cầu bằng phiên hiện tại.
4. Mở Tài khoản và thiết bị. Dùng Quản trị đối tác · An toàn thông tin khóa Nhân viên đối tác.
5. Quay lại và gửi bằng phiên hiện tại. Kho dừng yêu cầu dù phiên chưa hết hạn.
6. Mở khóa tài khoản. Phiên đã thu hồi vẫn không dùng lại được; đăng nhập mới để tiếp tục.

Web có ba cách kiểm tra: Kiểm tra khi đăng nhập; Thu hồi theo thông báo; Thu hồi theo thông báo và tự kiểm tra lại. Cả ba dùng cùng quy tắc truy cập tài liệu. Khác biệt nằm ở cách kho nhận biết thay đổi của tài khoản và thiết bị.

## Bắt đầu đọc ở đâu

| Mục đích | Mở tài liệu |
|---|---|
| Đọc báo cáo nghiên cứu đầy đủ | [Báo cáo chính 38 trang](docs/bao_cao/BaoCao_BMDL_Nhom03_ZeroTrust_DaSua.docx) |
| Đọc bản tóm tắt có hình và luồng xử lý | [Tóm tắt 10 trang](docs/bao_cao/BaoCao_TomTat_10Trang_TheoChuong.docx) |
| Hiểu nhanh bài toán và cơ chế | [Kiến thức nền](docs/kien_thuc_nen.md), rồi [kiến trúc và luồng 10 bước](docs/architecture.md) |
| Chạy và thử sản phẩm | [Hướng dẫn nhanh](docs/huong_dan_nhanh.md) |
| Chuẩn bị thuyết trình | [Slide 8 trang](trinh_chieu/Slide_ThuyetTrinh_BMDL_Nhom03_PhongCachSteam.pptx) và [lời thuyết trình 10 phút](docs/script_thuyet_trinh_10_phut.md) |
| Tìm toàn bộ tài liệu theo nhu cầu | [Mục lục](docs/muc_luc.md) |

Word và PowerPoint cần tải về để mở đầy đủ; GitHub không hiển thị trực tiếp nội dung hai định dạng này.

## Tài liệu tra cứu

- [Mục lục và thứ tự đọc](docs/muc_luc.md).
- [Hướng dẫn sử dụng nhanh](docs/huong_dan_nhanh.md).
- [Kiến thức nền và mục đích bài](docs/kien_thuc_nen.md).
- [Kiến trúc và luồng xử lý từng bước](docs/architecture.md).
- [Tham chiếu Microsoft và Google](docs/ke_thua.md).
- [Script thuyết trình 10 phút](docs/script_thuyet_trinh_10_phut.md) và [PowerPoint 8 slide](trinh_chieu/Slide_ThuyetTrinh_BMDL_Nhom03_PhongCachSteam.pptx).

## Cấu trúc thư mục

| Thư mục | Nội dung |
|---|---|
| `docs/` | Hướng dẫn, kiến trúc, quy tắc dữ liệu, kiểm chứng và báo cáo chính trong `bao_cao/` |
| `trinh_chieu/` | PowerPoint hiện hành; lời nói theo từng slide ở `docs/` |
| `app/`, `federation/`, `policies/` | Kho tài liệu, bên quản lý tài khoản, bộ điều phối và chính sách quyền |
| `lab/` | Giao diện web và công cụ vận hành |
| `infra/`, `scripts/`, `tests/`, `fixtures/` | Triển khai, chuẩn bị môi trường, bộ kiểm tra và dữ liệu mẫu |
| `results/` | Bằng chứng theo ngày; số liệu báo cáo trong `report-20261102/`, ảnh web mới trong `report-20261107-ui/` |

Báo cáo chính và bản tóm tắt trong `docs/bao_cao/` thống nhất kiến trúc và cách gọi hiện hành. Dùng các liên kết ở trên để đọc báo cáo, thuyết trình và thử sản phẩm.

## Kiểm tra sau khi khởi động

```powershell
powershell -ExecutionPolicy Bypass -File .\Run-Tests.ps1
```

Lệnh chạy 19 tình huống của kiến trúc hiện tại và xuất kết quả vào `results/`. Xem [cách tái lập](docs/reproduction.md) để chạy riêng kiểm tra Python và Rego. Bộ kiểm tra có thay đổi trạng thái mẫu; chờ chạy xong rồi mới thử thủ công.

## Kết quả và phạm vi thử nghiệm

Mục Kết quả kiểm tra trên web hiển thị các tình huống và kết quả đã lưu. Lượt dùng trong báo cáo ngày 02/11/2026 đạt 19/19 tình huống sử dụng thực tế. Các tập kiểm tra mã xử lý và quy tắc truy cập có phạm vi riêng; xem [kết quả kiểm tra](docs/ket_qua_kiem_chung.md).

Nút Chạy tất cả tình huống gửi yêu cầu thật và chủ động thay đổi trạng thái mẫu. Bộ kiểm tra khôi phục cấu hình, thu hồi các phiên do nó tạo và giữ tài liệu thử để xem lại. Kết quả mới nằm trong `results/federation-latest.*`; các bản theo thời gian vẫn được giữ.

Nguyên mẫu dùng chung máy chủ và dịch vụ đăng nhập, chưa kết nối trực tiếp Microsoft Entra, Intune hoặc Google Cloud. Trang điều khiển dành cho người vận hành tin cậy trên máy cá nhân. Kho kiểm soát các yêu cầu tiếp theo sau khi ghi nhận thu hồi; tệp đã tải về máy nằm ngoài phạm vi thu hồi phiên.

Mật khẩu và khóa được tạo riêng cho mỗi máy. Nếu cần đăng nhập thủ công, xem bằng `Show-Credentials.ps1` trên máy cài. Giữ `.env` và `runtime/` ngoài kho mã công khai.
