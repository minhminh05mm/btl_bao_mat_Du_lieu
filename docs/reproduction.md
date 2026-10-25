# Tái lập kiểm chứng và ghi nhận môi trường

Cập nhật tài liệu: 25/10/2026. [Mục lục tài liệu](muc_luc.md) · [Hướng dẫn sử dụng web](huong_dan_nhanh.md) · [Ma trận kiểm chứng](test-matrix.md).

## 1. Chọn đúng loại kiểm tra

| Mục đích | Công cụ | Tác động dữ liệu |
|---|---|---|
| Tự kiểm tra một yêu cầu | Tài liệu / Tự thử yêu cầu trên web | Thao tác ghi thay đổi dữ liệu; đọc tạo audit |
| Theo dõi từng bước | Bắt đầu có hướng dẫn | Có chuẩn bị và hoàn tác thuộc tính; audit, snapshot và bằng chứng được giữ; một số bài dừng dịch vụ thật |
| Chạy bộ chuẩn hoặc case JSON | Kiểm chứng tự động / `Run-Tests.ps1` | Có reset fixture trước/sau nhóm; không dùng trên tài liệu cần giữ |
| Đo B0/B1 | `Run-Tests.ps1 -Benchmark` | Chạy oracle/reset và đo riêng; không phải thời gian chạy suite |
| Kiểm tra thêm/sửa Hạn chế | Script bổ sung trong `results/restricted-management-20261021/` | Tạo tài liệu, thay grant, thử lỗi audit; không phải thao tác chỉ đọc |

Reset đưa tài liệu và lịch sử về bộ mẫu. Tài liệu tự tải lên có thể bị loại khỏi dữ liệu hoạt động; tài khoản tự thêm được phục hồi với vai trò, phòng ban và trạng thái đã lưu. Không đồng nhất việc giữ tài khoản với giữ toàn bộ dữ liệu. Sao lưu hoặc xuất tài liệu cần giữ và đọc hộp xác nhận trước khi chạy bộ chuẩn. Không chạy hai bộ kiểm tra trạng thái hoặc sửa dữ liệu đồng thời.

## 2. Chuẩn bị và bật môi trường

Thư mục dự án là `E:\btl_bao_mat_Du_lieu`, engine chạy trong WSL riêng `bmdl-demo`. Dùng môi trường đã cài; chỉ tải/build lại khi thực sự cần. Script kiểm tra tối thiểu 10 GiB trống trên C và 8 GiB trên E, dừng nếu không đủ.

```powershell
Set-Location -LiteralPath 'E:\btl_bao_mat_Du_lieu'
.\Start-Demo.ps1
```

Chốt mã nguồn, cấu hình, dữ liệu và trạng thái trước phép thử. Ghi nhận các tài khoản/tài liệu đã thêm. Tập chuẩn là business-v1 với 20 tài liệu và tám tài khoản mẫu; số trên web có thể lớn hơn. Một người vận hành thực hiện; tải nền của Windows chưa được kiểm soát hoàn toàn.

## 3. Thu bản môi trường trước và sau

```powershell
$captureId = 'capture-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
.\scripts\Capture-Environment.ps1 -RunId $captureId -Phase before
$beforeManifest = Join-Path $PWD ('results\' + $captureId + '\environment.before.json')
```

Chỉ dùng bản `before` khi `validation.complete` là true. Công cụ không tự khởi động engine, bootstrap hay reset. Bản trước đối chiếu dữ liệu hiện hành với catalog chuẩn; dữ liệu custom hoặc fixture đã đổi có thể làm kiểm tra này không đạt. Không reset chỉ để xóa thông báo khi còn tài liệu cần giữ. `-Phase draft` dùng cho bản kiểm kê nháp, không thay thế bản trước của một lượt chuẩn.

Sau khi chủ động chuẩn bị dữ liệu phù hợp và thu bản trước hợp lệ:

```powershell
.\Run-Tests.ps1
$latestRun = Get-Content -LiteralPath '.\results\latest.json' -Raw | ConvertFrom-Json
$runId = $latestRun.run_id
.\scripts\Capture-Environment.ps1 -RunId $runId -Phase after -BeforeManifest $beforeManifest
```

Mỗi lượt chuẩn xuất `results.json`, `results.csv`, `report.html`, `opa-tests.txt`, `identity-tests.txt`. Lệnh thu bản sau tạo thêm `host.after.json` và `environment.after.json`, liên kết hash bản trước và `results.json` của đúng run ID. Không sửa mã, chính sách hoặc image giữa hai bản thu.

```powershell
wsl.exe -d bmdl-demo -u root -- docker exec bmdl-lab-1 python -B /project/scripts/check_environment_manifest.py "/project/results/$runId/environment.after.json"
```

`comparison.source_unchanged` và `comparison.service_images_unchanged` giúp kiểm tra ổn định nguồn/image. Trạng thái dữ liệu có thể đổi do tình huống thử. Giá trị chưa quan sát được phải giữ unknown cùng cảnh báo, không điền theo cấu hình mặc định. Manifest không phải bằng chứng host không thay đổi ở mọi thời điểm giữa hai mốc.

## 4. Kiểm tra nhỏ và bộ bổ sung

Các lệnh sau chỉ chạy kiểm thử đơn vị, không chạy chuỗi reset/lỗi dịch vụ:

```powershell
wsl.exe -d bmdl-demo -u root -- docker exec bmdl-opa-1 /opa test /policies -v
wsl.exe -d bmdl-demo -u root -- docker exec bmdl-lab-1 python -m pytest -q -p no:cacheprovider tests/test_fixture_seed.py tests/test_auth_verifier.py
```

Nguồn kiểm tra chức năng thêm/sửa Hạn chế ngày 21/10 là [validate_restricted.py](../results/restricted-management-20261021/validate_restricted.py). Bộ này tách khỏi runner chuẩn và không được `Run-Tests.ps1` gọi tự động. Nó không reset toàn bộ lab nhưng có tạo tài liệu, cấp/thu hồi/làm hết hạn grant và tiêm lỗi ghi audit. Nếu chạy lại, chủ động chọn thời điểm không có thao tác khác, giữ bản `validation.json` trước đó và đọc script; script ghi kết quả vào cùng đường dẫn. Kết quả mới phải mang thời điểm và phạm vi riêng, không dùng lại nhãn kết quả 21/10.

Các lệnh `python -m tests.run_smoke --groups ...` cũng có reset qua helper; chúng không phải lựa chọn giữ nguyên dữ liệu chỉ vì chạy ít nhóm hơn.

## 5. Đo hiệu năng và lưu bằng chứng

`Run-Tests.ps1 -Benchmark` chạy phép đo B0/B1 riêng. Tạo bản môi trường trước mới, lấy run ID benchmark từ kết quả in ra, rồi thu bản sau bằng run ID đó. Benchmark không cập nhật `results/latest.json` của suite.

Đọc số request, warmup, số lần lặp, tài liệu, concurrency và cách tính percentile từ `summary.method` của chính lượt đo. Giữ `latency-samples.csv`, `performance-summary.csv` và manifest; không lấy mặc định mã nguồn thay cho tham số đã ghi. Không suy rộng số đo một host thành hiệu năng Google/Microsoft hoặc hệ thống doanh nghiệp.

Không đưa `.env`, token, mật khẩu, khóa riêng, URL DB hoặc bản rõ vào bằng chứng. Không xuất toàn bộ `docker inspect`/biến môi trường. Khi dùng xong:

```powershell
.\Stop-Demo.ps1
```

Dừng giữ dữ liệu và giải phóng tài nguyên WSL; khác với reset dữ liệu.
