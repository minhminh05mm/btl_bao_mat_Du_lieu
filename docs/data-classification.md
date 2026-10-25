# Dữ liệu nghiệp vụ tổng hợp và căn cứ phân loại

Cập nhật tài liệu ngày 25/10/2026. [Mục lục](muc_luc.md) · [Thêm/sửa tài liệu trên web](huong_dan_nhanh.md) · [Kiến trúc và quyền](architecture.md)

## 1. Mục đích và nguồn tạo dữ liệu

Bộ dữ liệu business-v1 mô tả kho tài liệu của doanh nghiệp mô phỏng BMDL, gồm phòng Kinh doanh (A) và phòng Vận hành (B). Nội dung được nhóm tạo tổng hợp từ các tình huống nghiệp vụ giả định; không thu thập hồ sơ, dữ liệu khách hàng hoặc thông tin cá nhân thực. Các tên dự án Mây Xanh, Bình Minh, mã tài nguyên, số tiền và mốc thời gian đều phục vụ minh họa. Dữ liệu không đại diện cho hoạt động của một doanh nghiệp thực.

Tập khởi tạo gồm 20 tài liệu TXT mã hóa UTF-8. Đây là bộ nền để tái lập, không phải số tài liệu cố định trên web; tài liệu người vận hành thêm được lưu riêng trong trạng thái hiện tại. Mỗi phòng có năm tài liệu nội bộ, ba tài liệu mật và hai tài liệu hạn chế. Kích thước thực tế từ 15.624 đến 16.202 byte, tổng cộng 316.279 byte. Cấu trúc mỗi tài liệu gồm mục đích, nội dung nghiệp vụ, trách nhiệm, căn cứ phân loại, 24 hạng mục theo dõi và giới hạn sử dụng. Không sử dụng chuỗi ký tự ngẫu nhiên để làm nội dung hoặc tăng kích thước.

Định dạng của tài liệu khởi tạo là TXT; định dạng được phép tải lên qua API vẫn là TXT, CSV và PDF, với giới hạn 1 MiB (1.048.576 byte). Loại nghiệp vụ như biên bản, báo giá hoặc kế hoạch không đồng nhất với định dạng tệp.

## 2. Phương pháp xác định mức nhạy cảm

Phân loại là quyết định thủ công của chủ sở hữu dữ liệu, dựa trên nội dung, phạm vi sử dụng và hậu quả khi tiết lộ. Ba tên nhãn dưới đây là giả định nghiệp vụ của nguyên mẫu; không phải cấp độ bí mật nhà nước hoặc kết quả phân loại theo một quy định pháp lý. Các quy tắc chỉ áp dụng cho tập tình huống nghiên cứu, chưa được đánh giá như chính sách phân loại dùng chung cho doanh nghiệp.

| Nhãn | Căn cứ nội dung và hậu quả | Phạm vi đọc trong B1 |
|---|---|---|
| Nội bộ | Quy trình, lịch phối hợp, biên bản công việc và số liệu tổng hợp. Không chứa giá chào riêng, phương án đàm phán hoặc điểm yếu chưa khắc phục. Chia sẻ sai phạm vi có thể gây nhầm lẫn công việc. | Nhân viên và trưởng phòng cùng phòng ban, khi các điều kiện chung hợp lệ. |
| Mật | Chi tiết riêng chưa công bố của dự án, báo giá, dự toán hoặc phân tích sự cố. Tiết lộ có thể làm giảm lợi thế thương mại hoặc làm lộ chi tiết vận hành của dự án. | Nhân viên sở hữu tài liệu cùng phòng; trưởng phòng trong phạm vi phòng. |
| Hạn chế | Giới hạn nhượng bộ, ngân sách chưa duyệt, điểm yếu chưa khắc phục hoặc kế hoạch phục hồi trọng yếu. Hậu quả có thể vượt một hồ sơ đơn lẻ, nên cần phê duyệt giới hạn. | Trưởng phòng cùng phòng được xem metadata; tải nội dung cần grant đúng người nhận, tài liệu, phiên bản, hành động và thời hạn, với người duyệt khác người nhận. |

Thời hạn 180, 90 và 30 ngày tương ứng ba nhãn là tham số thử nghiệm. Đây không phải kết luận về thời hạn lưu giữ tối ưu hoặc nghĩa vụ pháp lý. Grant có thể được sử dụng ở nhiều yêu cầu trong khoảng còn hiệu lực, nếu mọi điều kiện khác vẫn đúng; nguyên mẫu không áp dụng cơ chế grant dùng một lần. Một người có thể có nhiều grant; thu hồi hoặc hết hạn một grant không loại bỏ quyền từ grant phù hợp khác.

## 3. Danh mục tài liệu và lý do phân loại

Trong bảng, I, C và R lần lượt tương ứng nhãn internal, confidential và restricted trong mã nguồn. Tài khoản sở hữu là danh tính thử nghiệm. Chủ sở hữu không mặc nhiên có quyền đọc mọi mức nhạy cảm.

| Mã và chủ sở hữu | Tài liệu và loại nghiệp vụ | Căn cứ nhãn ban đầu |
|---|---|---|
| A-I01, alice | Quy trình tiếp nhận yêu cầu báo giá; quy trình nghiệp vụ | Hướng dẫn thao tác chung, không chứa giá riêng của từng khách hàng. |
| A-I02, anna | Lịch phối hợp tư vấn tháng 10; lịch phối hợp | Lịch theo vai trò, không có thông tin liên hệ thật hoặc nội dung thương lượng. |
| A-I03, adam | Hướng dẫn cập nhật cơ hội bán hàng; hướng dẫn sử dụng | Quy ước cập nhật trạng thái, không chứa giá hoặc cam kết riêng. |
| A-I04, alice | Báo cáo tổng hợp lượt tư vấn tháng 10; báo cáo tổng hợp | Số lượt theo nhóm dịch vụ, không gắn hồ sơ giao dịch hoặc khách hàng cụ thể. |
| A-I05, anna | Biên bản họp điều phối kinh doanh; biên bản phối hợp | Công việc chung và trách nhiệm theo vai trò, không chứa giới hạn thương lượng. |
| A-C01, alice | Dự thảo báo giá dự án Mây Xanh; dự thảo thương mại | Có đơn giá và cấu phần chào bán chưa công bố của dự án. |
| A-C02, anna | Kế hoạch đàm phán dự án Bình Minh; kế hoạch đàm phán | Có thứ tự ưu tiên và điều kiện trao đổi riêng của hồ sơ chưa công bố. |
| A-C03, adam | Dự toán doanh thu theo cơ hội quý IV; dự toán kinh doanh | Có giá trị dự kiến của từng cơ hội, thuộc thông tin quản trị nội bộ chưa công bố. |
| A-R01, alice | Ngưỡng chiết khấu ngoại lệ dự án Mây Xanh; phương án thương mại ngoại lệ | Có giới hạn nhượng bộ chưa công bố; lộ nội dung có thể làm mất giới hạn thương lượng. |
| A-R02, adam | Phương án phân bổ ngân sách kinh doanh; ngân sách chưa duyệt | Có mức dự phòng và thứ tự ưu tiên chưa duyệt, tác động vượt một hồ sơ dự án. |
| B-I01, bob | Quy trình bàn giao ca vận hành; quy trình vận hành | Hướng dẫn việc chung theo vai trò, không có sơ đồ hệ thống hoặc phương án ứng phó trọng yếu. |
| B-I02, bea | Lịch bảo trì dịch vụ nội bộ; lịch bảo trì | Khung phối hợp và nhóm công việc, không có địa chỉ thật hoặc cấu hình đặc quyền. |
| B-I03, brian | Hướng dẫn ghi nhận sự cố; hướng dẫn nghiệp vụ | Biểu mẫu và quy ước chung, không có nguyên nhân kỹ thuật của hệ thống cụ thể. |
| B-I04, bob | Báo cáo tổng hợp yêu cầu hỗ trợ; báo cáo tổng hợp | Số lượng theo nhóm và thời gian xử lý tổng hợp, không lộ hồ sơ riêng. |
| B-I05, bea | Biên bản họp cải tiến vận hành; biên bản phối hợp | Cải tiến quy trình chung, không chứa điểm yếu hoặc thứ tự phục hồi trọng yếu. |
| B-C01, bob | Kế hoạch triển khai dịch vụ dự án Mây Xanh; kế hoạch dự án | Có trình tự và nhu cầu nguồn lực riêng chưa công bố của dự án. |
| B-C02, bea | Biên bản phân tích sự cố dự án Bình Minh; phân tích sự cố | Có diễn biến, ảnh hưởng và giả thuyết nguyên nhân riêng của sự cố mô phỏng. |
| B-C03, brian | Dự toán chi phí vận hành quý IV; dự toán vận hành | Có chi phí theo nhóm dịch vụ và phương án sử dụng nguồn lực chưa công bố. |
| B-R01, bob | Phương án xử lý điểm yếu chưa khắc phục; phương án bảo vệ trọng yếu | Nêu tình trạng chưa khắc phục và thứ tự giảm thiểu; không có mã khai thác hoặc bí mật thật. |
| B-R02, brian | Kế hoạch phục hồi dịch vụ trọng yếu; kế hoạch phục hồi | Có thứ tự phục hồi và điều kiện chuyển sang phục vụ, cần hạn chế người nhận và thời hạn sử dụng. |

## 4. Quan hệ giữa nội dung, nhãn và quyền

Nội dung A-I01 hướng dẫn tiếp nhận yêu cầu, trong khi A-C01 chứa một mức giá dự thảo và A-R01 chứa một giới hạn chiết khấu ngoại lệ. Ba tài liệu cùng thuộc hoạt động báo giá nhưng có hậu quả tiết lộ khác nhau. Phân loại vì vậy được giải thích bằng thông tin thực sự có trong tài liệu và mức tác động của việc tiết lộ, thay vì chỉ dựa vào tên tệp.

Tương tự, B-I03 mô tả biểu mẫu ghi nhận sự cố; B-C02 ghi diễn biến một sự cố cụ thể; B-R01 đề cập tình trạng chưa khắc phục của tài nguyên mô phỏng. Nội dung không cung cấp địa chỉ truy cập thật, mã khai thác, token, mật khẩu hoặc vật liệu khóa.

Chủ sở hữu A-R01 là alice và B-R01 là bob được giữ để kiểm chứng rằng sở hữu tài liệu không đủ để vượt nhãn hạn chế. Nhân viên vẫn bị chặn đối với mức hạn chế. Trưởng phòng tải tài liệu hạn chế cần grant hợp lệ và vẫn chịu kiểm tra phòng ban, thiết bị, rủi ro, thời hạn cùng trạng thái hiện tại.

Nhãn được khởi tạo từ danh mục đã duyệt. Với tài liệu tải lên, nhân viên hoặc trưởng phòng được chọn Nội bộ/Mật; thêm trực tiếp Hạn chế yêu cầu trưởng phòng và quản trị an toàn phê duyệt. Máy chủ gán chủ sở hữu và phòng ban từ danh tính thực thi. Phê duyệt tạo mới gắn với người nhận, phòng ban, ID dự kiến, phiên bản, mục đích và thời hạn; chỉ sử dụng thành công một lần. Tài liệu Hạn chế, grant ban đầu và trạng thái đã dùng phê duyệt được lưu cùng giao dịch. Nâng lên Hạn chế cần phê duyệt mục đích upgrade cho đúng tài liệu/phiên bản mới. Nâng nhãn tăng phiên bản và có audit; đổi tên giữ phiên bản kiểm soát tài liệu. Sửa thông tin hiện tại cần quyền tải B1; xem được metadata một mình chưa đủ để sửa. Với Hạn chế, grant đúng tài liệu/phiên bản phải còn hạn và chưa thu hồi. Phê duyệt tạo dùng một lần khác với grant tải dùng ở nhiều yêu cầu trong thời hạn. Quyền nội dung không cho thay đổi lưu giữ/bảo toàn hoặc hạ nhãn. Máy chủ không tự phân tích nội dung để phát hiện hoặc suy ra nhãn. Một nhãn đã thay đổi sau khi khởi tạo phải được đọc từ registry; lý do nhãn ban đầu trong danh mục không thay thế nhãn hiện hành.

## 5. Hiện thực và tái lập

app/fixture_data.py chứa định nghĩa nghiệp vụ và hàm tạo payload tất định. Ngày minh họa, thứ tự mục và nội dung được cố định, không phụ thuộc đồng hồ hệ thống hoặc bộ sinh số ngẫu nhiên. Hàm fixture_payload tiếp tục được xuất qua app.db để các kiểm chứng lưu trữ và benchmark dùng cùng nội dung chuẩn. fixtures/dataset-manifest.json ghi phiên bản, tiêu đề, loại nghiệp vụ, lý do nhãn, chủ sở hữu, kích thước và SHA-256 của từng tài liệu.

Mỗi tài liệu được mã hóa bằng OpenBao Transit trước khi seed vào PostgreSQL; cơ sở dữ liệu lưu bản mã và hash, không lưu toàn văn rõ. Metadata cần thiết như tên, chủ sở hữu và nhãn vẫn ở dạng rõ có kiểm soát. Tài liệu hạn chế được seed ở phiên bản 2 kèm sự kiện tăng nhãn phục vụ minh họa nguồn gốc trạng thái.

Khởi động lại dịch vụ không tự ghi đè dữ liệu đang tồn tại. Đặt lại dữ liệu hoặc chạy bộ kiểm chứng chuẩn đưa tài liệu/lịch sử về bộ mẫu, có thể loại tài liệu tự thêm khỏi trạng thái hoạt động. Tài khoản tự thêm được khôi phục theo hồ sơ vận hành; không cần reset chỉ để dùng giao diện mới. Kết quả cũ trên bộ payload kỹ thuật không được trình bày như kết quả của business-v1.

## 6. Trình bày trên giao diện và ranh giới bảo vệ

Phần Tự thử yêu cầu hiển thị loại tài liệu, chủ hồ sơ, nhãn hiện tại và căn cứ nhãn ban đầu khi chọn tài liệu. Khối giải thích ba mức nhạy cảm cho biết tiêu chí và phạm vi sử dụng. Đây là mô tả tập mẫu trong giao diện người vận hành tin cậy, không phải endpoint metadata dành cho một người dùng nghiệp vụ không được cấp quyền.

GET /lab/dataset chỉ trả danh mục và quy tắc của bộ mẫu, không trả nội dung, đoạn ví dụ nghiệp vụ chứa giá trị riêng hoặc bản mã. Nội dung đầy đủ được lấy qua yêu cầu download đến API, sau JWT, chứng thư, PEP/PDP, kiểm tra trạng thái và audit. Danh mục không được dùng làm nguồn quyết định quyền; trạng thái hiện hành trong cơ sở dữ liệu mới có thẩm quyền.

## 7. Kiểm chứng và giới hạn

tests/test_fixture_data.py kiểm tra danh mục 20 mã, phân bố nhãn và chủ sở hữu theo hợp đồng; tính hợp lệ UTF-8, cấu trúc nghiệp vụ, kích thước, ví dụ nội dung, hash theo manifest và tính tất định giữa hai tiến trình. Kiểm thử còn xác nhận danh mục giao diện không chứa đoạn nội dung riêng và việc sửa bản mô tả nhận được không thay đổi định nghĩa phía máy chủ.

tests/test_fixture_seed.py gọi hàm seed thực với bộ ghi nhận SQL và spy ở ranh giới Transit để phát hiện việc ghi bản rõ vào trường lưu trữ. Đây là kiểm thử đơn vị, không chứng minh thuật toán mật mã. Các trường hợp T21 và T23 của bộ tích hợp vẫn phải chạy với OpenBao, PostgreSQL và phục hồi thực để kiểm tra dữ liệu mã hóa và khả năng khôi phục. Kiểm thử metadata và endpoint danh mục kiểm tra thêm việc loại nội dung/bản mã khỏi phản hồi và ràng buộc truy cập cục bộ của giao diện.

Tập mẫu hỗ trợ nghiên cứu tính đúng đắn của chính sách và phối hợp kiểm soát trên các tình huống đã xác lập. Nó chưa chứng minh chất lượng phân loại tự động, mức bảo đảm của dữ liệu doanh nghiệp thực hoặc tính đúng đắn của mọi chính sách phân loại ngoài phạm vi giả định.
