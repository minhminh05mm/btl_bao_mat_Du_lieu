# Kế thừa BeyondCorp và Microsoft Zero Trust trong thiết kế

Cập nhật tài liệu ngày 25/10/2026. Tài liệu giải thích nguồn tham chiếu, cách áp dụng vào web demo và căn cứ để phân biệt kế thừa, thiết kế cụ thể và cải tiến đã được chứng minh.

[Mục lục tài liệu](muc_luc.md) · [Hướng dẫn web](huong_dan_nhanh.md) · [Kiến trúc chi tiết](architecture.md)

## 1. Hiểu ngắn gọn trước

- **Google BeyondCorp:** nhóm tham chiếu cách tổ chức đường truy cập theo người dùng, thiết bị, proxy và chính sách theo ngữ cảnh.
- **Microsoft Zero Trust:** nhóm vận dụng nguyên tắc và cách phối hợp bảo vệ qua nhiều miền: danh tính, thiết bị, ứng dụng, dữ liệu, mạng và hạ tầng.
- **Nhóm tự thiết kế:** quy tắc nghiệp vụ của kho tài liệu, cách phối hợp các phần mềm miễn phí và các tình huống kiểm chứng.

Các công nghệ đang dùng như Keycloak, NGINX, FastAPI, OPA, PostgreSQL và OpenBao là công cụ hiện thực các chức năng. Chúng không phải mã nguồn BeyondCorp hoặc bộ sản phẩm Microsoft Zero Trust.

Thiết kế hiện tại chưa chứng minh được một điểm yếu của BeyondCorp hoặc Microsoft Zero Trust đã được nhóm khắc phục. Vì vậy, không có căn cứ mô tả công việc là chọn phần tốt của hai bên rồi loại bỏ phần chưa tốt để tạo kiến trúc vượt trội. Cách định vị phù hợp là thiết kế và triển khai kiến trúc cho kho tài liệu dựa trên các mô hình tham chiếu.

Một phương án triển khai do nhóm thiết kế không tự động là một đóng góp kiến trúc mới về mặt khoa học. Giá trị hiện có nằm ở việc chuyển yêu cầu thành thành phần, chính sách và tình huống kiểm chứng có thể truy vết.

## 2. BeyondCorp gồm những gì và mình áp dụng ở đâu?

Nguồn chính của báo cáo là bài BeyondCorp năm 2014. Bảng dưới ghép các thành phần liên quan để dễ đối chiếu; phần chuyển đổi hệ thống được tách khỏi đường kiểm soát truy cập. [Nguồn Google/USENIX](https://www.usenix.org/system/files/login/articles/login_dec14_02_ward.pdf).

| Thành phần tham chiếu | Hiện thực trong demo | Vì sao lựa chọn và giới hạn |
|---|---|---|
| Danh bạ người dùng/nhóm và SSO | Keycloak cấp token; bảng `principals` giữ vai trò, phòng ban và trạng thái hiện tại | Cần biết ai thực hiện yêu cầu. Xác thực có thật; demo chưa yêu cầu MFA trong luồng đang sử dụng |
| Kiểm kê thiết bị | Bảng `devices` liên kết thiết bị với chủ thể, chứng thư và trạng thái | Cần đối chiếu thiết bị đã đăng ký; chưa có hệ thống kiểm kê nhiều nguồn trong doanh nghiệp |
| Định danh thiết bị bằng chứng thư | Chứng thư client, NGINX xác minh mTLS, API đối chiếu serial với registry | Ngăn dùng chứng thư của người khác. Chứng thư chứng minh sở hữu khóa lab, chưa chứng minh máy sạch mã độc hoặc khóa được bảo vệ bằng phần cứng |
| Suy luận độ tin cậy và luồng cung cấp thuộc tính | `compliant`, `risk`, thời điểm tín hiệu và nguồn SQL hiện tại | Giữ được đầu vào để kiểm tra chính sách. Tình trạng máy là giả lập; cập nhật timestamp không phải đo lại sức khỏe thiết bị |
| Access proxy | NGINX làm cổng truy cập; kiểm tra JWT và quyền được phối hợp với API | Tập trung đường vào và xác minh chứng thư. Chưa có proxy phân tán, năng lực chống tấn công và dự phòng tương đương triển khai lớn |
| Bộ quyết định truy cập | FastAPI thu thập trạng thái và thực thi; OPA đánh giá Rego | Quyền được kiểm tra cho yêu cầu mới, không chỉ khi đăng nhập. Đây là ánh xạ chức năng ở mức nguyên mẫu |
| Mạng không được mặc nhiên tin cậy, 802.1X/RADIUS/VLAN | Mạng container tách luồng; yêu cầu vẫn cần xác thực và quyền | Chỉ hiện thực phần giới hạn kết nối. Chưa triển khai xác thực truy cập mạng dây/Wi-Fi hay VLAN động |
| Công bố ứng dụng và DNS | Chỉ mở đường vào trên máy cục bộ | Ngoài phạm vi truy cập từ nhiều địa điểm; chưa kiểm chứng trải nghiệm truy cập doanh nghiệp từ mọi mạng |
| Phân tích luồng công việc và chuyển đổi hệ thống cũ | Không có quy trình chuyển đổi doanh nghiệp trong demo | Kho tài liệu được tạo mới. Thiếu quy trình chuyển đổi không phải bằng chứng quy trình ấy thừa khi một tổ chức có nhiều ứng dụng đang chạy |

### Đường kế thừa nhìn thấy ngay trên hệ thống

```text
Người dùng + chứng thư thiết bị
              ↓
NGINX xác minh chứng thư
              ↓
API xác minh token, lấy quyền và trạng thái hiện tại
              ↓
OPA đánh giá chính sách → API thực thi hoặc từ chối
```

Ví dụ: alice đăng nhập đúng nhưng gửi bằng chứng thư anna sẽ bị chặn. Khi quyền bị thu hồi trong B1, yêu cầu mới bị chặn dù token chưa hết hạn. Chứng thư đúng người vẫn chưa đủ nếu thiết bị bị thu hồi, tín hiệu không hợp lệ hoặc tài liệu ngoài quyền.

Điểm kế thừa ở đây là quan hệ giữa các thành phần và cách sử dụng thuộc tính. Không có khẳng định NGINX riêng lẻ thay thế toàn bộ access proxy của Google hoặc bộ giả lập trạng thái thay thế một hệ thống quản lý thiết bị thật.

## 3. Microsoft gồm những gì và mình áp dụng ở đâu?

Khung Microsoft được báo cáo sử dụng có ba nguyên tắc: xác minh rõ ràng, quyền tối thiểu và giả định có xâm nhập. Các nguyên tắc được phối hợp qua sáu miền, cùng chính sách và giám sát. Đây là khung tổ chức bảo vệ, không phải một danh sách sản phẩm bắt buộc. [Nguồn Microsoft](https://learn.microsoft.com/en-us/security/zero-trust/adopt/zero-trust-adoption-overview).

| Miền bảo vệ | Cơ chế trong demo | Mục đích và phần còn thiếu |
|---|---|---|
| Danh tính | Keycloak, JWT, vai trò, phòng ban, trạng thái tài khoản | Xác định người thực hiện và quyền hiện tại; chưa có toàn bộ kiểm soát danh tính doanh nghiệp |
| Thiết bị đầu cuối | Registry, chứng thư, tín hiệu tuân thủ/rủi ro có thời hạn | Quyết định xét cả thiết bị. Tín hiệu đang giả lập, chưa được thu từ MDM/EDR hoặc xác nhận trạng thái phần cứng |
| Ứng dụng | API kiểm tra xem, tải, thêm, sửa và xóa | Thực thi quyền tại thao tác nghiệp vụ; phạm vi mới có một ứng dụng |
| Dữ liệu | Nhãn, chủ sở hữu, grant theo phiên bản, mã hóa, lưu giữ và bảo toàn | Bảo vệ từng tài liệu và vòng đời. Chưa có phân loại tự động hay kiểm soát bản rõ sau khi tải ra ngoài |
| Mạng | Gateway, TLS/mTLS ở đường vào, mạng container riêng | Giới hạn kết nối; chưa có mTLS cho mọi liên kết nội bộ hoặc phân đoạn doanh nghiệp nhiều địa điểm |
| Hạ tầng | Tách bí mật, giới hạn quyền KMS của ứng dụng, sao lưu và phục hồi cô lập | Hạn chế quyền dịch vụ và kiểm tra khả năng phục hồi; chưa có cụm dự phòng hoặc các miền quản trị độc lập |

Audit và cảnh báo giúp quan sát yêu cầu giữa các miền; quy tắc cảnh báo hiện tại còn đơn giản, chưa phải hệ thống phân tích đe dọa đa nguồn.

### Ba nguyên tắc thể hiện bằng quyết định nào?

| Nguyên tắc | Quyết định trong kho tài liệu |
|---|---|
| Xác minh rõ ràng | Mỗi yêu cầu B1 xét danh tính, chứng thư, trạng thái thiết bị, quyền và tài nguyên hiện tại |
| Quyền tối thiểu | Giới hạn theo phòng, chủ sở hữu, nhãn; tài liệu Hạn chế dùng grant đúng tài liệu/phiên bản và thời hạn |
| Giả định có xâm nhập | Không cấp quyền chỉ vì ở mạng nội bộ; tách quyền dịch vụ, ghi audit và kiểm tra hành vi khi phụ thuộc lỗi |

Các cơ chế như JWT, mã hóa, phân đoạn và audit được nhiều mô hình bảo mật sử dụng. Không thể gán chúng thành công nghệ riêng của Microsoft. Căn cứ vận dụng nằm ở cách các miền phối hợp, không chỉ ở việc đặt tên sáu ô trong sơ đồ.

Ví dụ: adam là trưởng phòng nhưng khác phòng với tài liệu thì bị chặn; cùng phòng nhưng thiếu grant vẫn không tải/sửa được Hạn chế; grant hợp lệ nhưng thiết bị rủi ro cao vẫn bị chặn. Quản trị an toàn được phê duyệt nhưng không mặc nhiên đọc nội dung nghiệp vụ.

Việc tập trung trình bày BeyondCorp theo đường truy cập và Microsoft theo các miền không có nghĩa Google thiếu bảo vệ dữ liệu hay Microsoft không có proxy. Hai tài liệu tham chiếu được dùng ở mức mô tả khác nhau.

## 4. Những gì do nhóm tự cụ thể hóa

| Quyết định của nhóm | Lý do trong bài toán |
|---|---|
| Hai phòng ban A/B và ba nhãn Nội bộ/Mật/Hạn chế | Có tập dữ liệu và phạm vi chia sẻ đủ rõ để kiểm chứng |
| Nhân viên tải Mật do mình sở hữu; trưởng phòng tải trong phòng | Phân biệt nhu cầu sử dụng theo vai trò và quan hệ với hồ sơ |
| Grant theo người, tài liệu, phiên bản, hành động và thời hạn | Giới hạn quyền sử dụng Hạn chế và kiểm tra được việc hết hạn/thu hồi |
| Phê duyệt tạo/nâng nhãn dùng thành công một lần | Tách việc cho phép tạo trạng thái nhạy cảm khỏi grant sử dụng nhiều yêu cầu |
| Sửa thông tin phải có quyền tải B1 hiện tại | Xem metadata chưa đủ để sửa; không tạo đường sửa vượt quyền nội dung |
| Lưu giữ 180/90/30 ngày, legal hold và tombstone | Kiểm chứng vòng đời theo giả định của bài toán |
| Đối chiếu ledger khi phục hồi cô lập | Kiểm tra bản sao cũ không làm sống lại quyền đã thu hồi hoặc tài liệu đã hủy |
| B0 đối chứng quyền đọc tĩnh | Minh họa khác biệt của gói điều kiện B1; không đại diện Google hay Microsoft |

Không nguồn tham chiếu nào được dùng để khẳng định Google/Microsoft quy định chính xác các nhãn, thời hạn hoặc luật nghiệp vụ trên. Khái niệm PDP/PEP còn được đối chiếu với NIST; việc truy vết yêu cầu vận dụng SABSA rút gọn. Đóng góp của nhóm là cụ thể hóa, phối hợp và kiểm chứng trong phạm vi kho tài liệu, chưa chứng minh tính mới hoàn toàn của kiến trúc.

## 5. Nếu nhóm lấy phần tốt, bỏ phần chưa tốt thì vì sao Google/Microsoft vẫn giữ?

### 5.1. Tiền đề cần sửa

Câu hỏi này yêu cầu chứng minh việc cải tiến mô hình gốc. Nếu nhóm nói đã ghép ưu điểm và loại bỏ nhược điểm, nhóm phải nêu được phần bị loại là gì, nhược điểm được xác định theo tiêu chí nào và kết quả nào chứng minh phương án thay thế tốt hơn.

Đối với hệ thống hiện tại, chưa có chuỗi bằng chứng đó. Nhóm chưa triển khai hai mô hình gốc trong cùng điều kiện để so sánh, chưa xác định một cơ chế gốc có thể loại bỏ mà vẫn giữ các bảo đảm tương ứng. Do đó, không thể giải thích rằng Google/Microsoft đang giữ phần kém mà nhóm đã khắc phục được. Đây là giới hạn của lập luận trước đó, không phải kết luận về chất lượng kiến trúc của hai hãng.

### 5.2. Một thành phần có chi phí không có nghĩa là thành phần kém

Kiến trúc thường phải cân bằng nhiều mục tiêu: mức bảo vệ, khả năng phục vụ, độ trễ, chi phí vận hành và khả năng quản lý. Một cơ chế có thể tăng chi phí ở tiêu chí này nhưng đem lại lợi ích cần thiết ở tiêu chí khác. Chỉ gọi là tốt hơn khi nêu rõ mục tiêu, điều kiện và phần đánh đổi.

Ví dụ, proxy giúp kiểm soát đường truy cập thống nhất nhưng tạo thêm một tầng phụ thuộc. Bỏ proxy có thể giảm một tầng xử lý; đồng thời, phải chứng minh nơi nào thực hiện các kiểm tra tương đương và làm sao ngăn đường truy cập bỏ qua kiểm soát. Trong mô tả BeyondCorp, proxy còn cung cấp nhiều chức năng dùng chung. Nguồn này không đưa ra căn cứ để kết luận proxy là phần chưa tốt mà nhóm có thể bỏ để tăng an toàn. [BeyondCorp, mục Internet-Facing Access Proxy](https://www.usenix.org/system/files/login/articles/login_dec14_02_ward.pdf).

Tương tự, việc phối hợp nhiều miền trong khung Microsoft đòi hỏi công sức triển khai và quản trị. Chi phí này chưa chứng minh cách tiếp cận ấy kém hiệu quả. Hướng dẫn của Microsoft yêu cầu xác định kết quả theo rủi ro, mục tiêu của tổ chức và điều chỉnh cách triển khai cho môi trường áp dụng. [Microsoft, các giai đoạn Define strategy và Ready](https://learn.microsoft.com/en-us/security/zero-trust/adopt/zero-trust-adoption-overview).

Vì vậy, các nguồn cho thấy mục đích và lợi ích của những lựa chọn này; chúng không cho phép suy ra rằng các hãng biết một thành phần không có giá trị nhưng vẫn cố giữ. Muốn kết luận về một quyết định cụ thể phải có bằng chứng riêng cho quyết định đó.

### 5.3. Việc kết hợp hai nguồn thực chất làm gì?

Hai tài liệu được dùng ở mức mô tả khác nhau: BeyondCorp giúp tham chiếu quan hệ giữa danh tính, thiết bị, proxy và quyết định truy cập; khung Microsoft giúp kiểm tra cách phối hợp bảo vệ qua nhiều miền. Chúng có phần giao nhau, không phải hai bộ linh kiện tách biệt để chọn linh kiện tốt của bên này thay cho linh kiện hỏng của bên kia.

| Cách diễn đạt | Kết luận phù hợp với bằng chứng hiện có |
|---|---|
| Lấy kiểm soát danh tính và thiết bị của Google | Tham chiếu quan hệ các thành phần để thiết kế đường truy cập của kho tài liệu |
| Bổ sung bảo vệ dữ liệu theo Microsoft | Dùng khung nhiều miền để rà soát yêu cầu; không chứng minh BeyondCorp thiếu bảo vệ dữ liệu |
| Có chính sách đến từng tài liệu nên vượt BeyondCorp | Chưa có căn cứ: nguồn BeyondCorp đã mô tả kiểm tra từng yêu cầu và quyền khác nhau giữa các thao tác trong ứng dụng |
| Dùng Keycloak, OPA và OpenBao nên tốt hơn công nghệ của hãng | Công cụ miễn phí đáp ứng ràng buộc triển khai; chưa có so sánh bảo đảm, chi phí tổng thể hoặc hiệu năng để kết luận vượt trội |
| B1 tốt hơn B0 nên kiến trúc ghép tốt hơn Google/Microsoft | Sai đối tượng đối chứng: B0 là chính sách đọc tĩnh do nhóm xây dựng, không đại diện hai mô hình gốc |

Nguồn BeyondCorp cho phép kiểm soát khác nhau giữa xem, cập nhật và tìm kiếm trong cùng ứng dụng. Các quy tắc theo tài liệu, phiên bản và thời hạn của nhóm là sự cụ thể hóa bài toán, không phải bằng chứng đã sửa một thiếu sót về phân quyền chi tiết của Google. [BeyondCorp, mục Access Control Engine](https://www.usenix.org/system/files/login/articles/login_dec14_02_ward.pdf).

### 5.4. Muốn gọi là cải tiến thì cần chứng minh gì?

1. Xác định phương án gốc cụ thể và hạn chế quan sát được trong điều kiện áp dụng; không dùng tên hãng làm đối chứng chung chung.
2. Nêu tiêu chí đánh giá, chẳng hạn thời gian thu hồi quyền, tỷ lệ từ chối sai, độ trễ hoặc chi phí quản trị.
3. Chỉ ra cơ chế được thay đổi, lý do thay đổi và những bảo đảm phải giữ.
4. Thử hai phương án dưới cùng dữ liệu, tải và tình huống đe dọa; công bố cả kết quả bất lợi và phần đánh đổi.
5. Chỉ kết luận cải tiến theo tiêu chí và phạm vi đã kiểm chứng.

Hiện B0/B1 có thể dùng để đánh giá lợi ích của gói kiểm soát B1 so với chính sách đọc tĩnh trong chính nguyên mẫu. Cặp này chưa tách được đóng góp của từng cơ chế và không chứng minh ưu thế so với BeyondCorp hoặc Microsoft Zero Trust.

Kết luận cho câu hỏi: chưa có phần nào được chứng minh là chưa tốt trong hai mô hình rồi bị nhóm loại bỏ. Công việc hiện tại là lựa chọn cách hiện thực và cụ thể hóa yêu cầu kho tài liệu. Nếu dùng cụm từ cải tiến Google/Microsoft thì phải bổ sung nghiên cứu so sánh tương ứng; chỉ ghép các thành phần chưa đủ căn cứ.

## 6. Ví dụ để phân biệt kế thừa và giới hạn

Giả sử adam được phê duyệt tải một tài liệu Hạn chế trong 15 phút:

1. Keycloak và chứng thư giúp xác định người/khóa thiết bị. Đây là phần vận dụng quan hệ danh tính–thiết bị của mô hình truy cập.
2. API lấy phòng ban, nhãn, phiên bản, thiết bị và grant; OPA kiểm tra các điều kiện. Đây là cách nhóm hiện thực quyết định theo ngữ cảnh.
3. Grant chỉ áp dụng cho tài liệu và thời hạn cần thiết. Đây là vận dụng quyền tối thiểu vào chính sách nghiệp vụ nhóm đặt.
4. Nếu không còn grant phù hợp, yêu cầu tải/sửa mới bị chặn. Có thể có nhiều grant; thu hồi một dòng chưa đủ nếu còn dòng khác hợp lệ.
5. Nếu máy thật nhiễm mã độc nhưng simulator vẫn ghi compliant/NORMAL, demo chưa nhận biết được tình trạng nhiễm đó. Muốn bảo vệ thực tế phải bổ sung nguồn tín hiệu đáng tin cậy.

Như vậy, kiểm chứng được rằng chính sách phản ứng với một tín hiệu không đồng nghĩa đã kiểm chứng nguồn tín hiệu phản ánh đúng máy thật. Quyền trên server cũng không thu hồi được các byte đã trả cho client.

## 7. Cách nói khi thuyết trình

Nhóm thiết kế và triển khai kiến trúc an toàn cho kho tài liệu dựa trên BeyondCorp và khung Microsoft Zero Trust. BeyondCorp là nguồn tham chiếu cho đường kiểm soát truy cập theo danh tính và thiết bị; Microsoft là nguồn tham chiếu cho việc phối hợp bảo vệ qua nhiều miền. Nhóm cụ thể hóa thành quy tắc theo nhãn, phòng ban, chủ sở hữu, phiên bản và thời hạn; sau đó triển khai bằng công cụ nguồn mở và kiểm chứng qua các tình huống nghiệp vụ.

Nếu được hỏi vì sao Google/Microsoft vẫn giữ phần mà nhóm bỏ, trả lời: nhóm chưa chứng minh phần đó là điểm yếu của mô hình gốc. Việc lựa chọn thành phần cho nguyên mẫu không đồng nghĩa loại bỏ nhược điểm của hai hãng. Kết quả hiện tại chứng minh các chính sách đã chọn hoạt động trong điều kiện thử nghiệm, chưa chứng minh kiến trúc vượt trội so với hai mô hình tham chiếu.

Đề tài vẫn có nội dung thiết kế: xác định dữ liệu và yêu cầu, phân chia trách nhiệm các thành phần, thiết kế luồng quyết định, giải quyết tương tác giữa quyền và vòng đời, triển khai và đánh giá. Với yêu cầu học phần cho phép thiết kế và triển khai dựa trên kiến trúc có sẵn, hướng này phù hợp; không cần tự nhận đã tạo ra mô hình tốt hơn Google/Microsoft. Nếu yêu cầu bắt buộc có cải tiến kiến trúc mới, cần một giả thuyết và phép so sánh riêng trước khi đưa ra kết luận ấy.

## 8. Nguồn đối chiếu

### Tài liệu tham chiếu

- Ward và Beyer, 2014, [BeyondCorp: A New Approach to Enterprise Security](https://www.usenix.org/system/files/login/articles/login_dec14_02_ward.pdf): thành phần, đường truy cập và chuyển đổi.
- Microsoft, [Zero Trust adoption framework overview](https://learn.microsoft.com/en-us/security/zero-trust/adopt/zero-trust-adoption-overview): nguyên tắc, sáu miền và cách phối hợp.
- Microsoft, [Zero Trust as a security foundation](https://learn.microsoft.com/en-us/security/zero-trust/zero-trust-overview): định hướng áp dụng và lộ trình theo phạm vi/rủi ro.
- NIST, [SP 800-207](https://csrc.nist.gov/pubs/sp/800/207/final): thuật ngữ và chức năng của kiến trúc Zero Trust.

### Hiện thực của dự án

- [Kiến trúc](architecture.md), [quyết định thiết kế](design-approved.md), [hợp đồng API](implementation-contract.md).
- [Xác thực và gọi chính sách](../app/security.py), [các thao tác nghiệp vụ](../app/main.py), [mô hình dữ liệu](../app/db.py), [quy tắc Rego](../policies/bmdl.rego).
- [Cấu hình mạng/dịch vụ](../compose.yaml), [gateway](../infra/nginx.conf), [quản lý trên console](../lab/management.py).
- [Ma trận kiểm chứng](test-matrix.md), [bằng chứng theo từng lượt](ket_qua_kiem_chung.md).

Bảng ánh xạ trong tài liệu này là phân tích của nhóm dựa trên nguồn tham chiếu và mã đang có; các hãng không xác nhận nguyên mẫu tương đương kiến trúc của họ. Kết quả thực nghiệm chỉ áp dụng cho điều kiện và tình huống đã công bố.
