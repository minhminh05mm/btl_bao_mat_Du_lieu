# Tham chiếu Microsoft và Google

## Bối cảnh và mục đích tích hợp

Bài toán đặt trong bối cảnh hai đơn vị quản trị độc lập. Bên quản lý tài khoản xác nhận nhân viên và thiết bị có còn hợp lệ. Kho tài liệu quản lý quyền đối với dữ liệu và cấp phiên truy cập riêng.

Khi tài khoản bị khóa sau lúc đăng nhập, phiên tại kho có thể vẫn còn hạn. Thiết kế cần chuyển thay đổi ở bên quản lý tài khoản thành quyết định thu hồi tại kho, đồng thời giữ quyền quản trị riêng của mỗi bên.

## Microsoft Zero Trust cung cấp căn cứ gì?

Khung Microsoft Zero Trust tổ chức bảo vệ theo sáu miền: danh tính, thiết bị, ứng dụng, dữ liệu, hạ tầng và mạng. Các nguyên tắc gồm xác minh rõ ràng, cấp quyền tối thiểu và giả định có xâm nhập.

Trong tình huống nghiên cứu, trách nhiệm quản lý vòng đời tài khoản và tình trạng thiết bị tương ứng với vai trò của Entra ID và Intune trong hệ sinh thái Microsoft. Nguyên mẫu cụ thể hóa trách nhiệm này bằng dịch vụ quản lý tài khoản cục bộ và cơ sở dữ liệu riêng.

Sáu miền giúp xác định phạm vi bảo vệ; chính sách là cơ chế phối hợp việc kiểm tra, không phải tên một miền thay cho ứng dụng. Việc chọn thời điểm kiểm tra, cách truyền thay đổi và nơi lưu phiên vẫn cần thiết kế cụ thể.

## Google BeyondCorp cung cấp căn cứ gì?

BeyondCorp cung cấp tham chiếu cho đường truy cập ứng dụng dựa trên danh tính và thiết bị qua cổng kiểm soát. Vị trí ở mạng nội bộ không tự tạo quyền dùng ứng dụng hoặc dữ liệu.

Nguyên mẫu sử dụng cổng NGINX xác minh thiết bị, liên kết tài khoản với thiết bị đã đăng ký và thực thi quyền ở kho. Kho có phiên riêng và tiếp tục kiểm tra quyền trên từng yêu cầu tài liệu.

Đường truy cập tham chiếu BeyondCorp và khung sáu miền Microsoft có phần giao nhau. Vai trò của chúng trong bài là cung cấp căn cứ tổ chức trách nhiệm và đường kiểm soát, không phải chia toàn bộ chức năng bảo vệ thành hai nửa loại trừ nhau.

## Cơ chế phối hợp được triển khai

| Lựa chọn trong kiến trúc | Mục đích cụ thể | Vị trí thực hiện |
|---|---|---|
| Bên quản lý tài khoản giữ quyền quyết định trạng thái | Tránh để kho tự quyết định thay vòng đời tài khoản, thiết bị của đối tác | Dịch vụ quản lý tài khoản và dữ liệu riêng |
| Kho giữ quyền quyết định tài liệu | Trạng thái tài khoản hợp lệ chưa đồng nghĩa được đọc mọi tài liệu | Quyền tại kho, OPA và API tài liệu |
| Liên kết người, thiết bị và bên quản lý đã đăng ký | Tránh tin tên đơn vị hoặc thiết bị do người gửi tự khai | Sổ liên kết và bộ điều phối |
| Thông tin trạng thái và thông báo có chữ ký | Kiểm tra nguồn gửi, nội dung và phạm vi của thông tin nhận được | Hai nguồn trạng thái và bộ điều phối |
| Phiên truy cập riêng, thu hồi theo thông báo | Chặn phiên còn hạn khi tài khoản hoặc thiết bị không còn hợp lệ | Bộ điều phối và bước kiểm tra phiên tại kho |
| Hỏi lại định kỳ, giới hạn thời gian dùng trạng thái cũ | Phát hiện thông báo bị mất; dừng khi chưa xác nhận lại được trạng thái | Bộ điều phối, cả tác vụ định kỳ và đường xử lý yêu cầu |
| Kiểm tra phiên trước khi trả nội dung | Giảm khoảng thời gian có thể dùng trạng thái đã thay đổi trong lúc xử lý | API tài liệu và bộ điều phối |

Phần tích hợp có thể kiểm tra được nằm ở liên kết danh tính, trao đổi trạng thái và quản lý hiệu lực phiên giữa hai bên. Những cơ chế này giải quyết tình huống cụ thể của nguyên mẫu. Chúng không tạo cơ sở để kết luận một nhà cung cấp không thể cung cấp giải pháp tương đương.

## Cách đánh giá

Kiểm tra khi đăng nhập là mốc quan sát khi chưa cập nhật thay đổi vào phiên đang dùng. Thu hồi theo thông báo cho thấy tác dụng của thông báo. Thu hồi theo thông báo và tự kiểm tra lại cho thấy tác dụng bổ sung khi mất thông báo hoặc mất kết nối.

Cả ba giữ cùng quyền tài liệu. So sánh này giúp xác định tác dụng của từng cơ chế cập nhật trạng thái trong một nguyên mẫu; không xếp hạng kiến trúc hoặc sản phẩm của Microsoft và Google.

## Mức hiện thực và nguồn tham khảo

Keycloak cung cấp dịch vụ đăng nhập dùng chung. NGINX, OPA, PostgreSQL và OpenBao thực thi các chức năng trong môi trường cục bộ. Dịch vụ quản lý tài khoản và bộ điều phối trao đổi bằng hợp đồng định nghĩa trong mã nguồn. Nguyên mẫu chưa kết nối trực tiếp Entra ID, Intune hoặc Google Cloud và chưa triển khai đầy đủ giao thức sự kiện của nhà cung cấp.

Các nguồn nền tảng để đọc tiếp:

- [Microsoft Zero Trust adoption framework](https://learn.microsoft.com/en-us/security/zero-trust/adopt/zero-trust-adoption-overview).
- [Ward và Beyer, BeyondCorp](https://www.usenix.org/system/files/login/articles/login_dec14_02_ward.pdf).
- [Google Cloud: Workforce Identity Federation với IAP](https://docs.cloud.google.com/iap/docs/use-workforce-identity-federation).
- [NIST SP 800-207](https://csrc.nist.gov/pubs/sp/800/207/final).

Sơ đồ nguyên mẫu mô tả thành phần đã triển khai trong dự án, không phải sơ đồ triển khai chính thức của Google hoặc Microsoft. Xem [kiến trúc](architecture.md) và [giới hạn bằng chứng](verification-review.md).
