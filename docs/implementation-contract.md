# Quy tắc phối hợp giữa các thành phần

Tài liệu này dành cho việc đối chiếu mã nguồn và giải thích ranh giới tin cậy. [Kiến trúc](architecture.md) mô tả cùng luồng bằng ngôn ngữ sử dụng thông thường.

## Quyền quản lý dữ liệu

| Chủ thể | Dữ liệu và quyền quản lý |
|---|---|
| Bên quản lý tài khoản | Tài khoản, thiết bị, lịch sử thay đổi và hàng đợi thông báo trong cơ sở dữ liệu `bmdl_partner` |
| Bộ điều phối | Liên kết danh tính, phiên, dạng băm của bí mật phiên, trạng thái đã xác minh và dấu vết xử lý trong `bmdl_coordinator` |
| Kho tài liệu | Thành viên, vai trò, nhãn, quyền có thời hạn, bản mã và nhật ký trong `bmdl` |

Quyền quản trị đối tác được kiểm tra tại dữ liệu của đối tác. Vai trò quản trị ở kho không tạo quyền quản trị tài khoản đối tác. Kho cung cấp nguồn trạng thái có chữ ký riêng cho nhân viên do kho tự quản lý.

## Đầu vào và kiểm tra danh tính

Cổng NGINX xác minh chứng thư và ghi đè các thông tin thiết bị, cách kiểm tra do người gửi tự khai. API chỉ tin thuộc tính xác minh khi yêu cầu đi qua cổng và có bí mật xác nhận cổng phù hợp.

Khi tạo phiên, API và bộ điều phối kiểm tra thông tin đăng nhập có chữ ký từ Keycloak. Bộ điều phối chọn đúng bên quản lý bằng liên kết đã đăng ký giữa nơi phát hành và định danh người dùng. Tên đăng nhập hoặc tên đơn vị do phía gửi đưa vào không đủ để lựa chọn nguồn trạng thái.

API kết nối bộ điều phối bằng thông tin xác thực dịch vụ riêng. Bộ điều phối xác thực các yêu cầu tạo và kiểm tra phiên; mã phiên công khai không thay được bí mật phiên.

## Trạng thái và thông báo có chữ ký

Nguồn trạng thái ký bằng RS256. Bộ điều phối kiểm tra thuật toán, nơi phát hành, bên nhận, loại thông tin, thời hạn, đúng người, đúng thiết bị, đúng bên quản lý và đúng lượt hỏi.

Mỗi lượt hỏi có giá trị ngẫu nhiên riêng; phản hồi phải chứa đúng giá trị đó. Thời điểm ký không thay thế thời điểm thực sự quan sát thiết bị. Thông tin quan sát quá hạn không được làm hợp lệ chỉ bằng cách ký lại.

Thông báo thay đổi có mã riêng và số phiên bản theo đối tượng. Bản trùng hoặc cũ không ghi đè trạng thái mới hơn. Bộ đếm thu hồi tăng khi có thay đổi quản trị giúp phát hiện khóa rồi mở giữa hai lần hỏi lại. Mở khóa không khôi phục phiên đã thu hồi.

Khóa ký riêng của bên quản lý tài khoản không được cấp cho API tài liệu hoặc bộ điều phối. Thông tin xác thực và khóa sinh trên từng máy nằm trong `runtime/`, ngoài phần mã công khai.

## Kênh truyền và lưu trữ

Kết nối khách đến cổng dùng TLS xác thực hai chiều bằng chứng thư, thường gọi là mTLS. Các kênh giữa nguồn trạng thái và bộ điều phối, giữa API và bộ điều phối dùng HTTPS kiểm tra cơ quan cấp chứng thư cùng thông tin xác thực dịch vụ có phạm vi.

Cổng đến API và một số kênh nội bộ đến OPA, OpenBao chạy trong mạng Docker của nguyên mẫu. Không coi mọi kênh nội bộ là mTLS. Nội dung tài liệu được mã hóa bằng OpenBao Transit; PostgreSQL lưu bản mã và thông tin quản lý cần thiết. Bộ điều phối chỉ giữ dạng băm của bí mật phiên; công cụ điều khiển giữ bí mật trong bộ nhớ để gửi yêu cầu.

## Quy tắc tiếp tục hoặc dừng yêu cầu

- Cả ba cách kiểm tra dùng cùng quy tắc quyền tài liệu tại kho.
- Cách Kiểm tra khi đăng nhập không cập nhật thay đổi nguồn vào phiên đang dùng.
- Cách Thu hồi theo thông báo thu hồi khi nhận và xác minh thông báo thay đổi.
- Cách Thu hồi theo thông báo và tự kiểm tra lại còn hỏi lại định kỳ và khi thông tin đã lưu hết hạn. Nếu chưa nhận được trạng thái hợp lệ mới, không cấp nội dung.
- Khi không kiểm tra được quyền, chưa ghi được nhật ký bắt buộc, giải mã lỗi hoặc nội dung không toàn vẹn, không trả nội dung như một yêu cầu thành công.
- Trước khi hoàn tất giao dịch tài liệu, kiểm tra lại phiên và các thời hạn áp dụng. Vẫn tồn tại khoảng đua sau lần kiểm tra cuối.

Thời hạn phiên mặc định 900 giây; thời gian dùng trạng thái đã xác minh tối đa 5 giây; hỏi lại mỗi 5 giây; tuổi quan sát thiết bị tối đa 60 giây. Không dùng chu kỳ hỏi lại để thay cho giới hạn sử dụng thông tin cũ trên đường xử lý yêu cầu.

## Khởi động và khôi phục

Khi dịch vụ phiên khởi động lại, phiên từ lần chạy trước không còn hợp lệ. Tình huống khôi phục cơ sở dữ liệu phiên từ bản sao kiểm tra việc này bằng cơ sở dữ liệu tạm và dịch vụ tạm, không phục hồi đè lên hệ thống đang dùng.

Bài kiểm tra đó xác nhận hành vi của phiên sau khôi phục; không phải diễn tập khôi phục đầy đủ dịch vụ danh tính, thiết bị, dữ liệu tài liệu và hạ tầng của cả hai bên.

## Trường kỹ thuật cần đối chiếu

| Trường trong phản hồi hoặc dữ liệu | Nghĩa |
|---|---|
| `request_id` | Mã nối yêu cầu với nhật ký và dấu vết kiểm tra |
| `nonce` | Giá trị ngẫu nhiên gắn phản hồi với đúng lượt hỏi trạng thái |
| `observed_at` | Thời điểm thực sự quan sát trạng thái thiết bị |
| `issued_at`, `iat` | Thời điểm phát hành hoặc ký thông tin |
| `valid_until` | Thời điểm cuối được sử dụng trạng thái đang giữ |
| `state_version` | Phiên bản trạng thái, dùng nhận biết bản cũ |
| `subject_epoch`, `device_epoch` | Bộ đếm thay đổi quản trị cần thu hồi phiên của người hoặc thiết bị |
| `event_id` | Mã thông báo riêng, dùng phát hiện xử lý lặp |

Các tên trường này phục vụ kiểm tra mã, không phải cách gọi trong phần thuyết trình.

## Giới hạn tin cậy

Nguyên mẫu dùng chung Keycloak, máy chủ, cụm PostgreSQL và Docker Engine. Công cụ điều khiển có quyền vận hành, quyền truy cập Docker và dữ liệu phục hồi; nó thuộc môi trường đáng tin cậy. Chủ máy hoặc nguồn trạng thái có thẩm quyền đã bị chiếm quyền nằm ngoài phạm vi đối thủ được kiểm tra.

Chưa có đồng bộ tài khoản doanh nghiệp tự động, tự đăng ký công khai, thu hồi tệp đã tải về hoặc cách ly vật lý giữa hai bên. Xem [đánh giá bằng chứng](verification-review.md).
