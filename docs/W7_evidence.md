# W7 Capstone Hackathon Evidence Pack

## 1. Cover
- **Group ID:** G13
- **Member Names:** Kiet, Phuc
- **Live URL:** https://d39sr1v8scwccx.cloudfront.net
- **GitHub Repo:** [Link to your repo]

## 2. Domain & Use Case
- **Domain:** FinTech (Domain B)
- **Use Case:** "AI Money Coach" - Ứng dụng tự động đọc sao kê (CSV/PDF dạng ảnh), dùng Bedrock AI để phân loại giao dịch, theo dõi chi phí, và đưa ra các lời khuyên dưới dạng bảng phân tích.
- **Target Users:** Cá nhân muốn quản lý chi tiêu thông minh mà không mất thời gian nhập liệu thủ công.
- **Market Reasoning:** Quản lý tài chính cá nhân là nhu cầu thiết yếu. Việc nhập tay gây nhàm chán và dễ bỏ cuộc. AI giúp tự động hóa khâu khó nhất này.
- **Named Real-world Parallel:** Cleo AI, Rocket Money.

## 3. Architecture & Trade-offs
*(Xem thêm sơ đồ kiến trúc tại `docs/architecture.png`)*
- **Service Decision Table:**
  - Compute: Lambda (arm64, On-Demand, Private Subnets, No-NAT)
  - DB: DynamoDB (PAY_PER_REQUEST)
  - Storage: S3
  - AI/ML: Bedrock (Claude 4.5 Haiku qua Interface Endpoint), Textract (qua Interface Endpoint)
  - Frontend: S3 Static + CloudFront OAC
- **3 Trade-off Justifications:**
  1. *DynamoDB vs RDS:* Chọn DynamoDB để scale-to-zero tiết kiệm chi phí, đánh đổi việc query dữ liệu quan hệ phức tạp.
  2. *No NAT Gateway vs NAT Gateway:* Chấp nhận setup VPC Interface Endpoints phức tạp để gọi AI, đổi lại tiết kiệm được 100% chi phí duy trì NAT Gateway (~$32/tháng).
  3. *Single-file Lambda vs Microservices:* Gộp chung logic vào 1 function để ship nhanh trong 48h, đánh đổi sự dễ dàng khi maintain dự án lớn.

## 4. Cost Evidence & Drivers
> Ghi chú: Chụp 3 ảnh màn hình và lưu vào thư mục `docs/images/` rồi thay link ở dưới nhé.
- **Ảnh cuối Day 1 EOD:** `[Chèn ảnh Cost Explorer Day 1]`
- **Ảnh cuối Day 2 EOD:** `[Chèn ảnh Cost Explorer Day 2]`
- **Ảnh sáng Demo Day:** `[Chèn ảnh Cost Explorer Sáng Demo]`
- **Top 3 Cost Drivers:**
  1. Amazon Bedrock (Token inference).
  2. KMS (Phí gọi API mã hóa/giải mã).
  3. VPC Endpoints (Hourly fee).

## 5. Security (IAM / KMS)
- **IAM Role List:** Lambda sử dụng role giới hạn quyền (Least-Privilege), chỉ cấp quyền read/write đúng ARN của DynamoDB table và S3 bucket.
- **KMS Key ARN:** Sử dụng Customer Managed Key (`aws_kms_key.s3_key`) để mã hóa S3. 
- **MFA Confirmed:** Tài khoản root đã được bật MFA bảo vệ.

## 6. Monitoring
- **Dashboard Screenshot:** `[Chụp ảnh CloudWatch Dashboard nếu có]`
- **Alarm Config:** Đã thiết lập Metric Alarm gửi SNS khi Lambda Error > 0. Budget Alarm kích hoạt ở mức 80% của $10. Cost Anomaly Detection đã được bật.
- **Log Insights Query:** Đã thiết lập Retention 14 ngày.

## 6.5 Measurement & Decisions ★
```text
DECISION: Sử dụng Claude 4.5 Haiku thay vì Claude 3.5 Sonnet cho tác vụ phân loại giao dịch (Categorization).

ALTERNATIVES CONSIDERED:
- Claude 3.5 Sonnet — eliminated because: Phí token quá cao (gấp ~15 lần Haiku) không phù hợp với giới hạn $100 của Hackathon.
- Amazon Titan — eliminated because: Khả năng xử lý tiếng Việt và hiểu context hóa đơn của thị trường Việt Nam còn kém.

MEASUREMENT:
- Cost/1M Tokens = $0.25 (Haiku) vs $3.00 (Sonnet) — Theo bảng giá AWS Bedrock.
- Latency = ~1.5s/request (Haiku) — Đo đạc thực tế trên CloudWatch Logs.

EVIDENCE:
- [Tham khảo logs thời gian thực thi trong CloudWatch]

TRADE-OFF ACCEPTED:
- Chấp nhận khả năng suy luận phức tạp giảm một chút (Sonnet thông minh hơn), nhưng với bài toán phân loại danh mục chi tiêu, Haiku vẫn đáp ứng độ chính xác >90% trong khi chi phí rẻ hơn 15 lần.
```

## 7. Lessons Learned (~200 chữ)
Trong quá trình 48h hackathon, thách thức lớn nhất là việc cấu hình Lambda gọi AI từ Private Subnets mà không có NAT Gateway. Việc thiếu NAT đòi hỏi nhóm phải tìm hiểu sâu về VPC Endpoints. Điều này ban đầu gây ra lỗi kết nối "Timeout" liên tục, nhưng sau khi cài đặt thành công Interface Endpoint cho Bedrock và Textract, chúng tôi đã tiết kiệm được hoàn toàn chi phí đắt đỏ của NAT Gateway trong khi vẫn giữ bảo mật cấp doanh nghiệp. 
Bên cạnh đó, việc quản lý quyền IAM đôi khi rất tốn thời gian debug, nhưng nó giúp chúng tôi thực sự nhận ra tầm quan trọng của nguyên tắc Least-Privilege. Trong tương lai, chúng tôi sẽ xem xét việc đóng gói và triển khai tự động CI/CD cho frontend và backend thay vì chạy script thủ công.
