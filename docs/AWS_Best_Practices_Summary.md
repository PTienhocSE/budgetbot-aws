# Tổng hợp Kiến trúc AWS & Best Practices (W1-W6)

Tài liệu này tổng hợp toàn bộ các tính năng, kỹ thuật và "Best Practices" được đúc kết từ dự án tham chiếu Kicks Shoes (Tuần 1 đến Tuần 6) và đã được **áp dụng thành công** vào hệ thống **BudgetBot**.

---

## 🎯 Tuần 1: Căn bản & Quản lý Chi phí (Cost Guard & Billing)
- **AWS Budgets (Cảnh báo ngân sách):** Đã cấu hình `aws_budgets_budget` với giới hạn 10$/tháng. Khi chi phí thực tế hoặc dự báo vượt 80%, hệ thống tự động bắn cảnh báo qua SNS (Cost Guard).
- **Phân tách Log hợp lý:** Cấu hình CloudWatch Logs Retention giảm xuống còn 14 ngày (thay vì vĩnh viễn) để ngăn chặn phát sinh phí rác từ ổ cứng lưu trữ Log.

## 🎯 Tuần 2: Mạng Máy Tính & Tối ưu Hiệu Năng Compute
- **Serverless Compute (Lambda):** Loại bỏ gánh nặng duy trì server 24/7 (EC2 hay Fargate). Hàm Lambda của BudgetBot tự động "Scale to Zero" (Tắt hoàn toàn) lúc không có ai truy cập.
- **ARM64 Architecture (Graviton2):** Chuyển đổi kiến trúc xử lý của Lambda từ `x86_64` truyền thống sang `arm64`. Vi xử lý ARM64 mang lại **hiệu năng cao hơn ~19%** và **chi phí tính toán thấp hơn 20%**.

## 🎯 Tuần 3: Dữ liệu Cơ sở & Mạng (Database & Networking)
- **Tối ưu Hóa VPC (Cost vs Security - No-NAT):** Đáp ứng yêu cầu bảo mật nghiêm ngặt, hàm Lambda được thiết lập để chạy trong các Private Subnets phân bổ trên 2 Availability Zones khác nhau (Multi-AZ). Đặc biệt, hệ thống **không sử dụng NAT Gateway** (tiết kiệm 100% phí NAT ~$32/tháng) mà thay vào đó sử dụng các **VPC Endpoints** để kết nối trực tiếp đến các dịch vụ AWS nội bộ.
- **VPC Gateway & Interface Endpoints:** Định tuyến dữ liệu từ DynamoDB và S3 thông qua các Gateway Endpoints miễn phí, và gọi Bedrock Runtime API qua Interface Endpoint. Việc này giúp dữ liệu giao dịch và thông tin đăng nhập/đăng ký được truyền hoàn toàn trong mạng nội bộ AWS, loại bỏ phí truyền tải qua Internet và NAT Gateway.
- **On-Demand DynamoDB:** Thiết lập Capacity Mode của DynamoDB là `PAY_PER_REQUEST`. Đây là chiến lược hoàn hảo cho ứng dụng mới khởi nghiệp vì chỉ trả tiền khi có giao dịch, chịu được tải tăng đột biến (spiky workloads).
- **Least-Privilege IAM Roles:** Gỡ bỏ các quyền Wildcard (`*`) dễ dãi. IAM Role của Lambda được thiết lập để chỉ có thể truy xuất đúng ARN của bảng DynamoDB và Bucket S3 được chỉ định.

## 🎯 Tuần 4 & Tuần 5: Serverless API & Bảo Vệ Dữ Liệu (API & Data Protection)
- **Bảo vệ Dữ liệu Cấp Doanh Nghiệp (Backup & PITR):** Kích hoạt tính năng khôi phục liên tục (PITR) của DynamoDB cho phép tua lại dữ liệu ở bất kỳ giây nào trong 35 ngày. Đồng thời, triển khai **AWS Backup Vault & Plan** để tự động chụp bản sao toàn bộ hệ thống vào lúc 2:00 AM mỗi đêm và lưu giữ an toàn trong 7 ngày.
- **API Gateway Throttling:** Bật bộ giới hạn lưu lượng (Rate Limit = 10, Burst = 20) ngay tại API Gateway. Đây là lớp khiên đầu tiên chống lại các cuộc tấn công DDoS nhỏ hoặc hành vi SPAM làm cạn kiệt túi tiền (Denial of Wallet).
- **CloudFront CDN:** Phân phối nội dung tĩnh toàn cầu với độ trễ thấp và chặn đứng truy cập HTTP thuần (Ép buộc chuyển hướng sang HTTPS).

## 🎯 Tuần 6: Vận Hành Nâng Cao & Tự Động Hóa (Ops & Cost-Aware Cloud)
- **Cost Allocation Tags (Truy vết chi phí):** Gắn bộ nhãn chuẩn doanh nghiệp (`Owner`, `CostCenter`, `Application`, `Environment`) lên 100% tài nguyên được tạo bởi Terraform. Giúp kế toán hoặc kỹ sư dễ dàng xem bảng giá theo phòng ban/dự án trong AWS Cost Explorer.
- **S3 Lifecycle Rules (Tối ưu Storage):** Tự động chuyển các file Excel/CSV báo cáo tài chính sang lớp lưu trữ rẻ hơn (Standard-IA) sau 30 ngày và xóa vĩnh viễn sau 90 ngày. Cắt giảm 80% lãng phí lưu trữ (Storage Waste).
- **Khóa Mã hóa CMK (Customer Managed Key):** Triển khai AWS KMS tự quản lý (CMK) để mã hóa S3 và AWS Backup. Điểm đáng giá nhất là tính năng này giúp CloudTrail lưu lại lịch sử (Audit Trail) chính xác ai/ứng dụng nào đã giải mã file.
- **Cơ chế Tự Động Phục Hồi S3 (Self-Healing Auto-Remediation):** Cấu hình một EventBridge Rule lắng nghe trực tiếp luồng sự kiện của CloudTrail. Nếu phát hiện lệnh API `DeleteBucketPublicAccessBlock` được gọi (cố tình hay vô ý làm tắt tính năng bảo mật), hệ thống sẽ lập tức kích hoạt một hàm Lambda S3-Remediation để chạy lệnh `PutBucketPublicAccessBlock` ép bật lên lại trong thời gian tính bằng giây!
- **CloudWatch Metric Alarms:** Đặt chuông báo động (Alarm) vào SNS nếu hàm Lambda phát sinh lỗi (Error Rate > 0).

## 🎯 Tuần 7 (Capstone): Xử Lý Tài Liệu Tiên Tiến & AI Money Coach
- **Xử lý Hóa đơn / Sao kê (AWS Textract):** Tích hợp AWS Textract để trích xuất văn bản từ tệp hình ảnh (hóa đơn, sao kê PDF dạng ảnh). Hệ thống tự động phân loại sử dụng thư viện xử lý truyền thống (PyPDF) hoặc Textract tùy theo định dạng file upload.
- **Tối ưu Hóa VPC Endpoint (Textract):** Triển khai thêm VPC Interface Endpoint cho AWS Textract. Đảm bảo toàn bộ luồng dữ liệu hình ảnh nhạy cảm của người dùng được phân tích hoàn toàn trong môi trường mạng kín nội bộ (Private Network) thay vì truyền ra Internet.
- **Advanced AI Money Coach:** Tận dụng dữ liệu giao dịch kết hợp với Amazon Bedrock để đưa ra các phân tích chi tiêu sâu sắc, đồng thời sinh ra các Actionable Items (gợi ý hành động) giúp người dùng quản lý tài chính tốt hơn.

---

## 🛠️ Danh sách các Dịch vụ AWS (Services) & Cấu hình Đặc biệt (Special Configs)

Để đạt được kiến trúc tối ưu trên, hệ thống sử dụng các dịch vụ AWS với những tinh chỉnh cấu hình đặc thù như sau:

| Dịch vụ AWS | Cấu hình đặc biệt (Special Configurations) đã áp dụng | Ý nghĩa / Lợi ích mang lại |
| :--- | :--- | :--- |
| **Amazon VPC** | - Thiết lập dải IP `10.0.0.0/16`. <br> - Phân bổ 2 Private Subnets độc lập trên 2 Availability Zones khác nhau (Multi-AZ) để chạy Lambda. <br> - Không sử dụng NAT Gateway (No-NAT). | - Đạt độ sẵn sàng cao (High Availability), phòng ngừa thảm họa phòng máy AWS. <br> - Cô lập mạng hoàn toàn theo chuẩn Enterprise. <br> - Tiết kiệm 100% chi phí thuê NAT Gateway (~$32.40/tháng). |
| **VPC Gateway Endpoints** | - Thiết lập Gateway Endpoints cho **S3** và **DynamoDB** trực tiếp trong Route Table. | - Truy xuất dữ liệu tốc độ cao qua mạng nội bộ AWS. <br> - Hoàn toàn miễn phí, không tốn phí Data Transfer qua Internet/NAT. |
| **VPC Interface Endpoint** | - Thiết lập Interface Endpoints cho **Bedrock Runtime** và **Textract**. <br> - Kích hoạt Private DNS để tự động phân giải tên miền. <br> - Gắn Security Group riêng cho phép truy cập HTTPS (port 443) nội bộ từ Lambda. | - Cho phép Lambda trong Private Subnets gọi AI/ML API an toàn mà không cần kết nối ra ngoài Internet. <br> - Loại bỏ rủi ro rò rỉ dữ liệu tài chính của người dùng. <br> - Chi phí rất rẻ so với NAT Gateway. |
| **AWS Lambda** | - `architectures = ["arm64"]` (Graviton2 chip) <br> - Kích hoạt `vpc_config` để liên kết với các Private Subnets và Security Group của Lambda. | - Tăng 19% hiệu năng, giảm 20% chi phí tính toán. <br> - Đảm bảo chỉ chạy và truy cập được các tài nguyên trong VPC. <br> - Scale to Zero (0$ khi không có request). |
| **Amazon Bedrock** | - Gọi model qua Cross-Region Inference Profile: **`us.anthropic.claude-haiku-4-5-20251001-v1:0`** (Claude 4.5 Haiku). | - Sử dụng model thế hệ mới hoạt động tốt trong năm 2026 (tránh lỗi Legacy của Claude 3/3.5). <br> - Đảm bảo băng thông (throughput) và giảm thiểu lỗi nghẽn/timeout của API. |
| **AWS IAM** | - Áp dụng chính sách Least-privilege (không dùng `*` trong policy). <br> - Lambda được cấp role `AWSLambdaVPCAccessExecutionRole` và quyền gọi `textract:DetectDocumentText`. | - Giới hạn tối đa phạm vi ảnh hưởng nếu mã nguồn hoặc API bị tấn công. <br> - Đảm bảo Lambda hoạt động trơn tru bên trong môi trường VPC. |
| **Amazon S3** | - Kích hoạt **Block Public Access 100%**. <br> - Cấu hình **Lifecycle Rules**: Tự động chuyển dữ liệu sang `STANDARD_IA` sau 30 ngày và xóa hẳn sau 90 ngày. | - Tuyệt đối bảo mật, không cho phép truy cập tệp sao kê từ ngoài internet. <br> - Tiết kiệm >80% chi phí lưu trữ các tệp rác dài hạn. |
| **AWS KMS** | - Tạo khóa KMS CMK riêng (`aws_kms_key.s3_key`) để mã hóa S3 Bucket và AWS Backup. | - Mã hóa dữ liệu tĩnh an toàn theo tiêu chuẩn quân sự. <br> - Lưu vết Audit Trail chi tiết vào CloudTrail giúp kiểm toán an toàn thông tin dễ dàng. |
| **Amazon DynamoDB** | - `billing_mode = "PAY_PER_REQUEST"` (On-Demand). <br> - Bật **Point-In-Time Recovery** (`point_in_time_recovery { enabled = true }`). | - Không tốn phí duy trì khi không có lưu lượng truy cập. <br> - Khôi phục dữ liệu về bất kỳ thời điểm nào (chính xác đến từng giây) trong 35 ngày qua để chống xóa nhầm. |
| **AWS Backup** | - Cấu hình Vault và Daily Backup Plan. <br> - Chụp bản sao lưu DynamoDB tự động vào 2:00 AM hàng đêm, lưu giữ trong 7 ngày. | - Kế hoạch sao lưu doanh nghiệp tự động hóa 100%, bảo vệ an toàn dữ liệu người dùng trước mọi thảm họa. |
| **Amazon API Gateway** | - Cấu hình giới hạn tần suất: `throttling_rate_limit = 10` và `burst_limit = 20`. <br> - Cấu hình CORS chặt chẽ chỉ cho phép CloudFront Domain truy cập. | - Lớp bảo vệ đầu tiên ngăn chặn tấn công Spam/DDoS làm cạn kiệt ví tài khoản AWS (Denial of Wallet). |
| **Amazon CloudFront** | - Sử dụng **S3 Origin Access Control (OAC)** để bảo mật cổng vào S3 Frontend. <br> - Ép buộc điều hướng HTTP sang HTTPS (`redirect-to-https`). <br> - Cấu hình điều hướng React Router (chuyển hướng lỗi 403/404 về `index.html`). | - Chặn người dùng truy cập trực tiếp vào S3 Bucket Frontend, bắt buộc qua CloudFront CDN. <br> - Mã hóa đường truyền chống nghe lén. <br> - Giúp các router ảo của React (như `/chat`, `/limits`) hoạt động bình thường mà không bị lỗi trang. |
| **AWS Budgets** | - Đặt Budget ở mức cứng 10$/tháng. <br> - Đặt cảnh báo vượt ngưỡng 80% thực tế hoặc dự báo. | - "Phanh khẩn cấp" giúp kiểm soát chi tiêu hackathon, tự động gửi cảnh báo qua SNS khi ngân sách sắp cạn. |
| **AWS CloudWatch & SNS** | - Cấu hình Alarms gửi cảnh báo đến SNS Topic `alerts` khi Lambda phát sinh lỗi (`Errors > 0`). <br> - Giới hạn **Log Retention là 14 ngày** thay vì vô hạn. | - Kịp thời phát hiện sự cố hệ thống. <br> - Loại bỏ rác lưu trữ log gây tốn tiền vô lý. |
| **Amazon EventBridge** | - Cấu hình **Self-Healing Rule**: Lắng nghe sự kiện CloudTrail và tự động kích hoạt Lambda để bật lại S3 Block Public Access nếu có ai vô tình tắt đi. <br> - Thiết lập lịch trình Cron-job chạy Cost Guard hàng ngày. | - Tự động hóa khắc phục sự cố bảo mật trong vòng vài giây mà không cần sự can thiệp của con người. <br> - Tự động hóa đánh giá chi phí. |

---
*Generated by Antigravity AI.*
