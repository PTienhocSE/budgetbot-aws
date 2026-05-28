# W7 — Bản đồ Đáp ứng Yêu cầu (Must-Haves Mapping)

> Giám khảo (Mentor) sẽ dựa vào danh sách này để chấm điểm. Hãy học thuộc lòng cách nhóm mình giải quyết từng bài toán để trả lời phỏng vấn (Grill) thật trôi chảy.

---

## 1. Ứng dụng AI vào Thực tiễn (FinTech)
**Yêu cầu:** Tích hợp AI một cách ý nghĩa (Anti-đối phó), giải quyết bài toán thực tế.
**Giải pháp của nhóm:**
- Xây dựng hệ thống **AI Money Coach** (Trợ lý Tài chính).
- Sử dụng **AWS Textract** để tự động "đọc" ảnh chụp/PDF hóa đơn chuyển khoản (tránh việc user phải nhập tay nhàm chán).
- Gọi **Amazon Bedrock (Claude Haiku)** để:
  1. Phân loại giao dịch (Ăn uống, Giải trí, Hóa đơn...).
  2. Phân tích chi tiêu và tạo ra các **Actionable Items** (Ví dụ: "Bạn đã tiêu quá nhiều cho ăn ngoài tuần này, hãy thử nấu ăn ở nhà").

---

## 2. Tối ưu Chi phí (Cost Optimization)
**Yêu cầu:** Chứng minh được sự hiểu biết về cách AWS tính tiền và các chiến thuật tối ưu.
**Giải pháp của nhóm:**
- **Chuyển đổi sang Serverless 100%:** Dùng Lambda thay vì ECS Fargate. Hệ thống tự động **Scale to Zero** khi không có ai dùng, giúp chi phí ban đêm = $0.
- **Sử dụng chip ARM64:** Thay vì chip x86 truyền thống, Lambda của nhóm chạy trên kiến trúc `arm64` (Graviton2), mang lại hiệu năng cao hơn và giá rẻ hơn 20%.
- **VPC Endpoints (No-NAT):** Không dùng NAT Gateway (thứ "đốt" $32/tháng dù không xài). Thay vào đó, dùng `Interface Endpoints` để gọi Bedrock/Textract bảo mật, rẻ hơn rất nhiều.
- **DynamoDB On-Demand:** Chuyển Database sang chế độ Pay-per-request.

---

## 3. Vận hành & Giám sát (Operations & Monitoring)
**Yêu cầu:** Đảm bảo hệ thống có thể theo dõi và tự động báo động khi có lỗi hoặc tốn quá nhiều tiền.
**Giải pháp của nhóm:**
- **AWS Budgets:** Đã cấu hình khóa ngân sách ở mức $10. Khi đạt 80% sẽ tự động bắn cảnh báo qua Email/SMS.
- **Cost Anomaly Detection:** Bật radar quét các khoản phí bất thường.
- **CloudWatch Alarms:** Cấu hình chuông báo động (`Errors > 0`) cho Backend Lambda. Bất cứ khi nào app bị sập (lỗi 5xx), lập tức gửi tin nhắn về SNS Topic để réo tên Developer.
- **Giảm Log Retention:** Ép thời gian lưu trữ CloudWatch Logs xuống còn 14 ngày (thay vì vĩnh viễn) để đỡ tốn tiền ổ cứng.

---

## 4. Bảo mật & Quản lý Quyền (Security & IAM)
**Yêu cầu:** Tuân thủ nguyên tắc Least Privilege (Quyền tối thiểu) và bảo vệ dữ liệu khách hàng.
**Giải pháp của nhóm:**
- **IAM Role:** Lambda Role chỉ được cấp quyền đọc/ghi vào ĐÚNG bảng DynamoDB và Bucket S3 của nhóm, không có quyền với các tài nguyên khác. (Tuyệt đối không dùng dấu `*` ở mục Resource).
- **KMS (Mã hóa):** Tạo chìa khóa Customer Managed Key (CMK) để mã hóa toàn bộ hình ảnh hóa đơn mà user upload lên S3. Bảo vệ dữ liệu nhạy cảm của FinTech.
- **Auto-Remediation (Tự động vá lỗi):** 
  - Admin lỡ tay mở Public Bucket S3.
  - EventBridge nhận diện sự kiện qua CloudTrail.
  - Kích hoạt Lambda "Bảo vệ".
  - Lambda lập tức gọi lệnh `PutPublicAccessBlock` đóng Bucket lại trong vòng 3 giây!

---

## 5. Đo lường & Lựa chọn Trade-off (Measurement & Decisions)
**Yêu cầu:** Mọi quyết định thiết kế đều phải dựa trên số liệu thực tế, không đoán mò.
**Giải pháp của nhóm:**
- **Lựa chọn AI Model:**
  - *Quyết định:* Dùng `Claude 3.5 Haiku`.
  - *Phương án bị loại:* `Claude 3.5 Sonnet` (vì giá token đắt gấp 15 lần Haiku, dễ vượt ngân sách $100). `Amazon Titan` (vì khả năng xử lý tiếng Việt kém).
  - *Đo lường:* Cost/1M Token (Haiku $0.25 vs Sonnet $3.00). Latency ~1.5s/request (rất mượt).
  - *Trade-off chấp nhận:* Khả năng suy luận phức tạp giảm một chút, nhưng dư sức đáp ứng bài toán Categorization của FinTech với độ chuẩn >90%.

---
**💡 Chốt hạ:** Đọc kỹ 5 mục này, kết hợp với các hình vẽ trong Evidence, bạn có thể "cân" mọi câu hỏi Grill khó nhằn nhất từ Ban Giám Khảo!
