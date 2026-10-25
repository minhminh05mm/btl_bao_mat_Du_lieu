# Phần mềm và nguồn phiên bản

Cập nhật tài liệu: 25/10/2026. [Mục lục tài liệu](muc_luc.md) · [Tái lập kiểm chứng](reproduction.md).

## 1. Phân biệt cấu hình ghim và phép quan sát

| Nguồn trong dự án | Ý nghĩa |
|---|---|
| [infra/images.lock.json](../infra/images.lock.json) | Digest image/nguyên liệu được ghi từ lần kiểm kê 15/10/2026; không phải phép đo lại ngày cập nhật tài liệu |
| [compose.lock.yaml](../compose.lock.yaml) và [infra/Dockerfile](../infra/Dockerfile) | Tham chiếu bất biến dùng khi khởi chạy/build |
| [requirements.lock.txt](../requirements.lock.txt) | 36 gói Python, kể cả phụ thuộc gián tiếp, được ghim từ image đã đo ngày 15/10 |
| [environment.after.json ngày 19/10](../results/run-20261019-084335-960c43/environment.after.json) | Quan sát host, container, thư viện và hash gắn với đúng lượt kiểm chứng ngày 19/10 |
| [deployed-source-check.json ngày 21/10](../results/restricted-management-20261021/deployed-source-check.json) | Đối chiếu mã đã triển khai với bản chuẩn bị của cập nhật quyền; không thay thế kiểm kê môi trường đầy đủ |

Mã được bind mount nên image ID riêng lẻ không định danh toàn bộ thí nghiệm. Build lại có thể tạo image ID mới dù phụ thuộc giữ nguyên. Dùng manifest trước/sau cho mỗi lượt mới; không đổi ngày của kết quả cũ thành ngày hiện tại.

## 2. Bộ phiên bản đã ghi nhận

Các giá trị dưới đây có trong kiểm kê/manifest đã lưu, cùng bộ tham chiếu ghim của dự án; không tuyên bố là phiên bản mới nhất trên Internet.

| Thành phần | Phiên bản ghi nhận | Nguồn chính |
|---|---|---|
| WSL riêng | Alpine Linux 3.24.2; kernel 6.18.54.1-microsoft-standard-WSL2 | Manifest môi trường 19/10 |
| Docker Engine / Compose | 29.8.2 / 5.1.4 | Manifest 19/10 và image lock |
| Image ứng dụng | Debian GNU/Linux 13.7; linux/amd64; CPython 3.12.15 | Manifest 19/10, Dockerfile |
| FastAPI / Uvicorn / HTTPX | 0.143.1 / 0.54.0 / 0.28.1 | requirements.lock.txt, manifest 19/10 |
| psycopg / PyJWT / cryptography | 3.3.6 / 2.15.1 / 50.0.2 | requirements.lock.txt, manifest 19/10 |
| PostgreSQL | 17.11 | Image lock, manifest 19/10 |
| Keycloak | 26.8.0 | Image lock, Compose lock |
| OPA | 1.21.2, Rego v1 | Image lock, manifest 19/10 |
| OpenBao | 2.7.1 | Image lock, manifest 19/10 |
| NGINX | 1.30.6 | Image lock, manifest 19/10 |
| restic | 0.19.1 | Dockerfile, image lock, manifest 19/10 |

Gói khác như Docker SDK, pytest, Jinja2 và psutil xem đầy đủ trong tệp khóa; không duy trì thêm một bản sao danh sách 36 gói ở đây.

## 3. Phạm vi sử dụng miễn phí và giấy phép

Demo dùng bản nguồn mở, chạy trên máy sẵn có, không cần Docker Desktop, cloud, API trả phí hoặc trial. Windows/WSL và tài nguyên máy là môi trường sẵn có; điện, mạng và dung lượng vẫn là chi phí vận hành tại chỗ.

Các tệp khóa xác định phiên bản, không thay thế giấy phép đi kèm gói/image. Khi sao chép hoặc phân phối lại, giữ thông báo bản quyền của bản phân phối. Các nguồn giấy phép chính thức đã được liên kết trong hồ sơ dự án:

| Thành phần | Giấy phép / nguồn chính thức |
|---|---|
| Docker Engine/Moby, Compose, Keycloak, OPA | Apache 2.0: [Moby](https://github.com/moby/moby/blob/master/LICENSE), [Compose](https://github.com/docker/compose/blob/main/LICENSE), [Keycloak](https://github.com/keycloak/keycloak/blob/main/LICENSE.txt), [OPA](https://github.com/open-policy-agent/opa/blob/main/LICENSE) |
| OpenBao | [MPL 2.0](https://github.com/openbao/openbao/blob/main/LICENSE) |
| NGINX / restic | BSD 2-Clause: [NGINX](https://nginx.org/LICENSE), [restic](https://github.com/restic/restic/blob/master/LICENSE) |
| PostgreSQL | [PostgreSQL License](https://www.postgresql.org/about/licence/) |
| Python | [PSF và thông báo đi kèm Python](https://docs.python.org/3.12/license.html) |
| FastAPI / PyJWT / pytest | MIT: [FastAPI](https://github.com/fastapi/fastapi/blob/master/LICENSE), [PyJWT](https://github.com/jpadilla/pyjwt/blob/master/LICENSE), [pytest](https://github.com/pytest-dev/pytest/blob/main/LICENSE) |
| psycopg | [LGPL 3; chú ý thông báo của bản binary](https://github.com/psycopg/psycopg/blob/master/LICENSE.txt) |
| cryptography | [Apache 2.0 hoặc BSD](https://github.com/pyca/cryptography/blob/main/LICENSE) |

## 4. Cách ghi nhận lại

Dùng [quy trình tái lập](reproduction.md) để thu phiên bản bằng các truy vấn chỉ đọc, image ID/RepoDigest, thư viện và hash nguồn. Không pull image hoặc rebuild chỉ để đọc phiên bản. Không in toàn bộ `.env`, thông tin container hoặc biến môi trường vì có thể chứa bí mật.

Image/volume của demo nằm trong VHD `runtime/wsl` trên E, không dùng kho Docker Desktop trên C. `Start-Demo.ps1` kiểm dung lượng trước khi chuẩn bị môi trường. Không khẳng định Windows/WSL tuyệt đối không sử dụng tài nguyên ở ổ C.
