# W7 — Hướng dẫn Console từ A đến Z (Cho người mất gốc)

> Tài liệu này lấy bảng tổng hợp **Service Settings** của nhóm làm xương sống, rồi **mổ xẻ từng dòng** thành hướng dẫn bấm nút trên AWS Console.
> Mọi thứ nhóm mình đã code bằng Terraform — nhưng hiểu được cách bấm tay sẽ giúp bạn **làm chủ hệ thống** và trả lời Grill tự tin.

---

## Mục lục

1. [Amazon VPC (Mạng ảo)](#1-amazon-vpc-mạng-ảo)
2. [VPC Gateway Endpoints (S3 & DynamoDB)](#2-vpc-gateway-endpoints-s3--dynamodb)
3. [VPC Interface Endpoints (Bedrock & Textract)](#3-vpc-interface-endpoints-bedrock--textract)
4. [AWS Lambda (Backend)](#4-aws-lambda-backend)
5. [Amazon Bedrock (AI)](#5-amazon-bedrock-ai)
6. [AWS IAM (Quyền hạn)](#6-aws-iam-quyền-hạn)
7. [Amazon S3 (Lưu trữ)](#7-amazon-s3-lưu-trữ)
8. [AWS KMS (Mã hóa)](#8-aws-kms-mã-hóa)
9. [Amazon DynamoDB (Database)](#9-amazon-dynamodb-database)
10. [AWS Backup (Sao lưu)](#10-aws-backup-sao-lưu)
11. [Amazon API Gateway (Cổng API)](#11-amazon-api-gateway-cổng-api)
12. [Amazon CloudFront (CDN)](#12-amazon-cloudfront-cdn)
13. [AWS Budgets (Ngân sách)](#13-aws-budgets-ngân-sách)
14. [CloudWatch & SNS (Giám sát)](#14-cloudwatch--sns-giám-sát)
15. [Amazon EventBridge (Tự động hóa)](#15-amazon-eventbridge-tự-động-hóa)

---

## 1. Amazon VPC (Mạng ảo)

### Nhóm đã cấu hình gì?
| Cấu hình | Giá trị |
|----------|---------|
| CIDR Block | `10.0.0.0/16` |
| Private Subnets | 2 subnets ở 2 AZ khác nhau (Multi-AZ) |
| NAT Gateway | **KHÔNG dùng** |

### Lợi ích
- Đạt độ sẵn sàng cao (High Availability) — nếu 1 phòng máy AWS chết, phòng máy còn lại vẫn chạy.
- Cô lập mạng hoàn toàn theo chuẩn Enterprise.
- Tiết kiệm 100% chi phí NAT Gateway (~$32.40/tháng).

### Cách mở trên Console (từng bước)
1. Đăng nhập AWS Console → Thanh tìm kiếm trên cùng → gõ **VPC** → bấm vào dịch vụ **VPC**.
2. Ở menu bên trái, bấm **Your VPCs**.
3. Bạn sẽ thấy 1 VPC tên kiểu `budgetbot-hackathon-vpc` với IPv4 CIDR là `10.0.0.0/16`.
4. Để xem Subnets: bấm **Subnets** ở menu trái.
   - Lọc theo VPC vừa tìm → thấy 2 private subnets (tên có chữ `private`).
   - Cột **Availability Zone** sẽ hiển thị 2 AZ khác nhau (ví dụ `us-east-1a` và `us-east-1b`).
5. Để xác nhận **KHÔNG có NAT Gateway**: bấm **NAT gateways** ở menu trái → phải thấy danh sách **trống** (hoặc không có NAT nào thuộc VPC này).

---

## 2. VPC Gateway Endpoints (S3 & DynamoDB)

### Nhóm đã cấu hình gì?
| Cấu hình | Giá trị |
|----------|---------|
| Endpoint cho S3 | Loại `Gateway`, gắn vào Route Table của Private Subnets |
| Endpoint cho DynamoDB | Loại `Gateway`, gắn vào Route Table của Private Subnets |

### Lợi ích
- Lambda gọi S3/DynamoDB qua đường nội bộ AWS (không ra Internet).
- **Hoàn toàn miễn phí** — $0 phí duy trì, $0 Data Transfer.

### Cách mở trên Console (từng bước)
1. Vẫn ở trang **VPC** → menu trái bấm **Endpoints**.
2. Lọc theo VPC của nhóm → bạn sẽ thấy 2 endpoints loại `Gateway`:
   - `com.amazonaws.us-east-1.s3` — Type: **Gateway**
   - `com.amazonaws.us-east-1.dynamodb` — Type: **Gateway**
3. Bấm vào 1 endpoint bất kỳ → tab **Route Tables** → xác nhận nó đã được gắn vào Route Table của Private Subnets.
4. Cột **Status** phải hiện `Available`.

> 💡 **Mẹo phân biệt:** Gateway Endpoint = miễn phí, chỉ dùng cho S3 và DynamoDB. Interface Endpoint = có phí, dùng cho mọi dịch vụ còn lại.

---

## 3. VPC Interface Endpoints (Bedrock & Textract)

### Nhóm đã cấu hình gì?
| Cấu hình | Giá trị |
|----------|---------|
| Endpoint cho Bedrock | Loại `Interface`, Service: `com.amazonaws.us-east-1.bedrock-runtime` |
| Endpoint cho Textract | Loại `Interface`, Service: `com.amazonaws.us-east-1.textract` |
| Private DNS | **Bật** (Enable) |
| Security Group | Cho phép Inbound HTTPS (port 443) từ Lambda SG |

### Lợi ích
- Lambda trong Private Subnet gọi được AI/ML mà không cần Internet.
- Loại bỏ rủi ro rò rỉ dữ liệu tài chính ra ngoài.
- Rẻ hơn NAT Gateway rất nhiều.

### Cách mở trên Console (từng bước)
1. Vẫn ở trang **VPC** → **Endpoints** → lọc theo VPC.
2. Tìm 2 endpoints loại `Interface`:
   - `com.amazonaws.us-east-1.bedrock-runtime` — Type: **Interface**
   - `com.amazonaws.us-east-1.textract` — Type: **Interface**
3. Bấm vào endpoint Bedrock:
   - Tab **Subnets**: Xác nhận đã chọn 2 Private Subnets.
   - Tab **Security Groups**: Xác nhận có 1 Security Group cho phép **Inbound Rule** với Port `443` (HTTPS).
   - Tab **Details**: Dòng **Private DNS names enabled** phải là `Yes`.
4. Lặp lại kiểm tra cho endpoint Textract.

> 💡 **Tại sao cần Private DNS?** Khi bật Private DNS, Lambda gọi `bedrock-runtime.us-east-1.amazonaws.com` sẽ tự động đi qua đường nội bộ (Interface Endpoint) thay vì đi ra Internet. Code Python không cần thay đổi gì cả.

---

## 4. AWS Lambda (Backend)

### Nhóm đã cấu hình gì?
| Cấu hình | Giá trị |
|----------|---------|
| Architecture | `arm64` (Graviton2 chip) |
| Timeout | 30 giây |
| Memory | 256 MB |
| VPC Config | Gắn vào 2 Private Subnets + Security Group |
| Runtime | Python 3.11 |

### Lợi ích
- ARM64: Tăng 19% hiệu năng, giảm 20% chi phí tính toán.
- VPC Config: Đảm bảo Lambda chỉ truy cập tài nguyên bên trong VPC.
- Scale to Zero: Khi không có request → $0.

### Cách mở trên Console (từng bước)
1. Thanh tìm kiếm → gõ **Lambda** → bấm vào dịch vụ **Lambda**.
2. Bấm **Functions** ở menu trái.
3. Tìm function tên `budgetbot-hackathon-backend` → bấm vào.
4. **Kiểm tra Architecture:**
   - Tab **Configuration** → mục **General configuration** → xem dòng **Architecture**: phải ghi `arm64`.
5. **Kiểm tra Timeout:**
   - Cùng mục **General configuration** → dòng **Timeout**: phải ghi `0 min 30 sec`.
6. **Kiểm tra VPC:**
   - Tab **Configuration** → bấm **VPC** ở menu trái.
   - Phải thấy VPC ID, 2 Subnet IDs (Private), và 1 Security Group ID.
   - Nếu mục này trống → Lambda đang KHÔNG nằm trong VPC → đó là lỗi cần sửa.
7. **Kiểm tra Environment Variables:**
   - Tab **Configuration** → **Environment variables**.
   - Phải thấy các biến như `DYNAMODB_TABLE_NAME`, `S3_BUCKET_NAME`, `BEDROCK_MODEL_ID`.

---

## 5. Amazon Bedrock (AI)

### Nhóm đã cấu hình gì?
| Cấu hình | Giá trị |
|----------|---------|
| Model | Claude 4.5 Haiku (Cross-Region Inference Profile) |
| Model ID | `us.anthropic.claude-haiku-4-5-20251001-v1:0` |

### Lợi ích
- Model thế hệ mới nhất (2026), tránh lỗi Legacy của Claude 3/3.5.
- Cross-Region Inference đảm bảo băng thông cao, giảm timeout.

### Cách mở trên Console (từng bước)
1. Thanh tìm kiếm → gõ **Bedrock** → bấm **Amazon Bedrock**.
2. **Kiểm tra quyền truy cập Model:**
   - Menu trái → **Bedrock configurations** → **Model access**.
   - Tìm dòng **Anthropic** → **Claude 4.5 Haiku**.
   - Cột **Access status** phải ghi **Access granted** (✅).
   - ⚠️ Nếu chưa có: Bấm **Modify model access** → tick chọn Claude Haiku → bấm **Next** → **Submit**. Đợi 1-2 phút để AWS duyệt.
3. **Thử gọi Model (tùy chọn):**
   - Menu trái → **Playgrounds** → **Chat**.
   - Chọn model Claude Haiku → gõ câu hỏi thử → bấm **Run**.
   - Nếu trả lời được → Model đã sẵn sàng.

> ⚠️ **LƯU Ý QUAN TRỌNG:** Bước bật Model Access này **PHẢI làm bằng tay** trên Console. Terraform không tự động cấp quyền model Bedrock được.

---

## 6. AWS IAM (Quyền hạn)

### Nhóm đã cấu hình gì?
| Cấu hình | Giá trị |
|----------|---------|
| Nguyên tắc | Least-privilege (không dùng `*` trong Resource) |
| Managed Policy | `AWSLambdaVPCAccessExecutionRole` |
| Custom Permissions | `dynamodb:PutItem`, `dynamodb:GetItem`, `s3:GetObject`, `s3:PutObject`, `bedrock:InvokeModel`, `textract:DetectDocumentText` |

### Lợi ích
- Giới hạn tối đa phạm vi ảnh hưởng nếu bị tấn công.
- Lambda hoạt động trơn tru bên trong VPC.

### Cách mở trên Console (từng bước)
1. Thanh tìm kiếm → gõ **IAM** → bấm **IAM**.
2. Menu trái → **Roles** → tìm role tên chứa `budgetbot-hackathon-backend`.
3. Bấm vào role đó:
   - Tab **Permissions** → xem danh sách Policy đã gắn.
   - Bấm vào từng Policy → bấm **{} JSON** để xem nội dung.
   - **Kiểm tra:** Không có dòng nào ghi `"Resource": "*"` (trừ policy `AWSLambdaVPCAccessExecutionRole` do AWS quản lý).
   - Các Action phải chỉ định rõ ràng: `dynamodb:PutItem`, `s3:GetObject`...
   - Resource phải trỏ đúng ARN cụ thể (ví dụ: `arn:aws:dynamodb:us-east-1:123456:table/budgetbot-*`).

> 💡 **Mẹo Grill:** Khi Mentor hỏi *"Tại sao không dùng `*`?"* → Trả lời: *"Nếu code bị lỗi hoặc bị hack, kẻ tấn công chỉ truy cập được đúng bảng DynamoDB của mình, không phải toàn bộ tài khoản AWS."*

---

## 7. Amazon S3 (Lưu trữ)

### Nhóm đã cấu hình gì?
| Cấu hình | Giá trị |
|----------|---------|
| Block Public Access | **100%** (bật cả 4 ô) |
| Lifecycle Rules | Chuyển sang `STANDARD_IA` sau 30 ngày, xóa hẳn sau 90 ngày |
| Server-Side Encryption | SSE-KMS (dùng chìa khóa CMK riêng) |

### Lợi ích
- Tuyệt đối bảo mật dữ liệu sao kê tài chính.
- Tiết kiệm >80% chi phí lưu trữ file rác dài hạn.

### Cách mở trên Console (từng bước)
1. Thanh tìm kiếm → gõ **S3** → bấm **S3**.
2. Tìm bucket tên chứa `uploads` → bấm vào.
3. **Kiểm tra Block Public Access:**
   - Tab **Permissions** → mục **Block public access (bucket settings)**.
   - Phải thấy cả **4 ô đều bật ON** (Block all public access: **On**).
4. **Kiểm tra Lifecycle Rules:**
   - Tab **Management** → mục **Lifecycle rules**.
   - Phải thấy 1 rule với:
     - Transition: `STANDARD_IA` after `30 days`.
     - Expiration: `90 days`.
5. **Kiểm tra Encryption:**
   - Tab **Properties** → cuộn xuống mục **Default encryption**.
   - Encryption type: `Server-side encryption with AWS KMS keys (SSE-KMS)`.
   - KMS key ARN: Phải trỏ đến key CMK riêng (không phải `aws/s3` mặc định).

> 💡 **Ý nghĩa Lifecycle:** Hóa đơn upload lên, sau 30 ngày tự động chuyển sang ổ cứng rẻ tiền hơn (IA = Infrequent Access). Sau 90 ngày tự động xóa luôn → không tốn phí lưu trữ vĩnh viễn.

---

## 8. AWS KMS (Mã hóa)

### Nhóm đã cấu hình gì?
| Cấu hình | Giá trị |
|----------|---------|
| Key Type | Customer Managed Key (CMK) |
| Alias | `alias/budgetbot-s3-key` (hoặc tương tự) |
| Dùng cho | Mã hóa S3 Uploads Bucket + AWS Backup |

### Lợi ích
- Mã hóa dữ liệu tĩnh theo tiêu chuẩn quân sự (AES-256).
- Mọi lần dùng chìa khóa đều được ghi lại trên CloudTrail → dễ kiểm toán.

### Cách mở trên Console (từng bước)
1. Thanh tìm kiếm → gõ **KMS** → bấm **Key Management Service**.
2. Menu trái → **Customer managed keys**.
3. Tìm key có Alias chứa `budgetbot` hoặc `s3` → bấm vào.
4. **Kiểm tra:**
   - Tab **General configuration**: Key spec `SYMMETRIC_DEFAULT`, Status `Enabled`.
   - Tab **Key policy**: Xem ai có quyền dùng key này (phải có Lambda role ARN).
   - Tab **Key rotation**: Kiểm tra xem có bật xoay khóa tự động không (Automatic rotation).

---

## 9. Amazon DynamoDB (Database)

### Nhóm đã cấu hình gì?
| Cấu hình | Giá trị |
|----------|---------|
| Billing Mode | `PAY_PER_REQUEST` (On-Demand) |
| Point-In-Time Recovery | **Bật** (`enabled = true`) |
| Encryption | SSE với KMS CMK |

### Lợi ích
- Không tốn phí duy trì khi không có lưu lượng.
- Khôi phục dữ liệu về bất kỳ giây nào trong 35 ngày qua.

### Cách mở trên Console (từng bước)
1. Thanh tìm kiếm → gõ **DynamoDB** → bấm **DynamoDB**.
2. Menu trái → **Tables** → tìm bảng `budgetbot-transactions` (hoặc tên tương tự) → bấm vào.
3. **Kiểm tra Billing Mode:**
   - Tab **Additional settings** → mục **Read/write capacity settings**.
   - Phải ghi **On-demand**.
4. **Kiểm tra PITR (Point-In-Time Recovery):**
   - Tab **Backups** → mục **Point-in-time recovery (PITR)**.
   - Status phải ghi **Enabled** (✅).
   - Nếu chưa bật: Bấm **Edit** → tick **Enable point-in-time recovery** → **Save changes**.
5. **Kiểm tra Tags:**
   - Tab **Additional settings** → cuộn xuống **Tags**.
   - Phải thấy các tag: `Project=BudgetBot`, `Environment=hackathon`...

> 💡 **PITR nghĩa là gì?** Nếu ai đó vô tình xóa hết dữ liệu giao dịch của khách hàng lúc 3:00 PM, bạn có thể "quay ngược thời gian" và khôi phục lại dữ liệu đúng ở trạng thái 2:59 PM.

---

## 10. AWS Backup (Sao lưu)

### Nhóm đã cấu hình gì?
| Cấu hình | Giá trị |
|----------|---------|
| Backup Vault | `budgetbot-backup-vault` (mã hóa bằng KMS CMK) |
| Backup Plan | Chụp bản sao lưu tự động lúc **2:00 AM mỗi đêm** |
| Retention | Giữ bản sao lưu trong **7 ngày** |

### Lợi ích
- Kế hoạch sao lưu doanh nghiệp tự động 100%.
- Bảo vệ dữ liệu trước mọi thảm họa.

### Cách mở trên Console (từng bước)
1. Thanh tìm kiếm → gõ **AWS Backup** → bấm **AWS Backup**.
2. **Kiểm tra Backup Vault:**
   - Menu trái → **Backup vaults** → tìm vault tên `budgetbot-backup-vault`.
   - Bấm vào → xác nhận Encryption key là CMK của nhóm (không phải `aws/backup` mặc định).
3. **Kiểm tra Backup Plan:**
   - Menu trái → **Backup plans** → tìm plan tên chứa `budgetbot`.
   - Bấm vào → xem **Backup rule**:
     - Schedule: `cron(0 2 * * ? *)` → nghĩa là 2:00 AM UTC mỗi ngày.
     - Lifecycle: Delete after `7 days`.
4. **Kiểm tra Resource đã được gắn:**
   - Trong Backup plan → tab **Resource assignments** → phải thấy DynamoDB table ARN.
5. **Xem lịch sử sao lưu:**
   - Menu trái → **Jobs** → xem danh sách các bản backup đã chạy thành công.

---

## 11. Amazon API Gateway (Cổng API)

### Nhóm đã cấu hình gì?
| Cấu hình | Giá trị |
|----------|---------|
| API Type | HTTP API (v2) |
| Throttling Rate Limit | `10 requests/giây` |
| Throttling Burst Limit | `20 requests` |
| CORS | Chỉ cho phép CloudFront Domain |

### Lợi ích
- Lớp bảo vệ đầu tiên chống Spam/DDoS (Denial of Wallet attack).
- CORS chặt chẽ ngăn website lạ gọi API.

### Cách mở trên Console (từng bước)
1. Thanh tìm kiếm → gõ **API Gateway** → bấm **API Gateway**.
2. Tìm API tên `budgetbot-hackathon-api` → bấm vào.
3. **Kiểm tra Routes (Đường dẫn):**
   - Menu trái → **Routes**.
   - Phải thấy các route: `POST /api/transactions`, `GET /api/transactions`, `POST /api/upload`, `POST /api/coach`...
4. **Kiểm tra Throttling:**
   - Menu trái → **Stages** → bấm vào stage `$default`.
   - Mục **Route throttling** hoặc **Default route settings**:
     - Rate: `10 requests per second`.
     - Burst: `20 requests`.
5. **Kiểm tra CORS:**
   - Menu trái → **CORS**.
   - Allow Origins: Phải ghi đúng URL CloudFront (`https://d39sr1v8scwccx.cloudfront.net`).
   - Allow Methods: `GET, POST, OPTIONS`.
   - Allow Headers: `Authorization, Content-Type`.
6. **Kiểm tra Integration (kết nối Lambda):**
   - Menu trái → **Integrations**.
   - Phải thấy mỗi route trỏ đến Lambda function `budgetbot-hackathon-backend`.

> 💡 **Denial of Wallet là gì?** Kẻ tấn công không cần hack hệ thống. Chúng chỉ cần gửi hàng triệu request giả → Lambda chạy liên tục → AWS tính tiền cho bạn → bạn "cháy ví". Throttling 10 req/s ngăn chặn điều này.

---

## 12. Amazon CloudFront (CDN)

### Nhóm đã cấu hình gì?
| Cấu hình | Giá trị |
|----------|---------|
| Origin Access | S3 Origin Access Control (OAC) |
| Viewer Protocol Policy | `redirect-to-https` |
| Custom Error Response | 403/404 → trả về `index.html` (cho React Router) |
| Price Class | `PriceClass_100` (Chỉ dùng edge servers ở Bắc Mỹ & Châu Âu → rẻ nhất) |

### Lợi ích
- Chặn truy cập trực tiếp vào S3 Frontend, bắt buộc qua CDN.
- Mã hóa đường truyền HTTPS chống nghe lén.
- React Router hoạt động bình thường.

### Cách mở trên Console (từng bước)
1. Thanh tìm kiếm → gõ **CloudFront** → bấm **CloudFront**.
2. Tìm Distribution có Domain Name `d39sr1v8scwccx.cloudfront.net` → bấm vào.
3. **Kiểm tra Origin (Nguồn dữ liệu):**
   - Tab **Origins** → bấm vào origin S3.
   - Dòng **Origin access**: Phải ghi `Origin access control settings`.
   - Dòng **Origin access control**: Phải hiện tên OAC (ví dụ `budgetbot-frontend-oac`).
4. **Kiểm tra HTTPS:**
   - Tab **Behaviors** → bấm vào behavior `Default (*)`.
   - Dòng **Viewer protocol policy**: Phải ghi `Redirect HTTP to HTTPS`.
5. **Kiểm tra Custom Error Pages (cho React Router):**
   - Tab **Error pages**.
   - Phải thấy 2 dòng:
     - HTTP Error Code `403` → Response Page Path `/index.html` → Response Code `200`.
     - HTTP Error Code `404` → Response Page Path `/index.html` → Response Code `200`.
   - Nếu không có → React Router sẽ bị lỗi trắng trang khi user gõ thẳng URL `/chat` hoặc `/limits` trên trình duyệt.

> 💡 **Tại sao 403/404 trả về index.html?** Vì React là Single Page Application (SPA). Khi user gõ `yourdomain.com/chat`, CloudFront tìm file `/chat` trên S3 → không thấy → trả 404. Nhưng nếu ta cấu hình trả về `index.html`, React Router sẽ tự xử lý URL `/chat` bên trong trình duyệt.

---

## 13. AWS Budgets (Ngân sách)

### Nhóm đã cấu hình gì?
| Cấu hình | Giá trị |
|----------|---------|
| Budget Amount | `$10/tháng` |
| Alert Threshold | Cảnh báo khi đạt **80%** (cả thực tế lẫn dự báo) |
| Alert Action | Gửi thông báo qua SNS Topic |

### Lợi ích
- "Phanh khẩn cấp" kiểm soát chi tiêu hackathon.
- Tự động réo tên Developer qua email/SMS khi ngân sách sắp cạn.

### Cách mở trên Console (từng bước)
1. Thanh tìm kiếm → gõ **Billing** → bấm **Billing and Cost Management**.
2. Menu trái → **Budgets**.
3. Tìm budget tên `budgetbot-hackathon-monthly` → bấm vào.
4. **Kiểm tra:**
   - Budgeted amount: `$10.00`.
   - Alert thresholds: `80% of budgeted amount`.
   - Notification: Trỏ đến SNS Topic ARN.
5. **Xem tình hình chi tiêu:**
   - Biểu đồ trên trang sẽ hiện chi tiêu thực tế (Actual) vs ngân sách (Budgeted).
   - Nếu thanh màu đỏ chạm đến vạch 80% → email cảnh báo đã được gửi đi.

---

## 14. CloudWatch & SNS (Giám sát)

### Nhóm đã cấu hình gì?
| Cấu hình | Giá trị |
|----------|---------|
| CloudWatch Alarm | Giám sát metric `Errors` của Lambda, báo khi `>= 1` |
| Log Retention | **14 ngày** (thay vì vĩnh viễn) |
| SNS Topic | Topic `alerts` nhận cảnh báo từ Alarm + Budget |

### Lợi ích
- Kịp thời phát hiện sự cố hệ thống.
- Loại bỏ rác log gây tốn tiền vô lý.

### Cách mở trên Console (từng bước)

#### A. CloudWatch Alarms
1. Thanh tìm kiếm → gõ **CloudWatch** → bấm **CloudWatch**.
2. Menu trái → **Alarms** → **All alarms**.
3. Tìm alarm tên chứa `budgetbot-backend-errors` → bấm vào.
4. **Kiểm tra:**
   - Metric: `AWS/Lambda` → `Errors` → Function `budgetbot-hackathon-backend`.
   - Condition: `Errors >= 1`.
   - Actions: Khi ở trạng thái **In alarm** → Gửi notification đến SNS Topic `alerts`.
   - State: Nên là `OK` (màu xanh). Nếu `INSUFFICIENT_DATA` (màu xám) → cần gọi API vài lần để Lambda có metric.

#### B. Log Retention
1. Vẫn ở **CloudWatch** → menu trái → **Logs** → **Log groups**.
2. Tìm log group `/aws/lambda/budgetbot-hackathon-backend` → bấm vào.
3. Dòng **Retention setting**: Phải ghi **14 days** (không phải `Never expire`).
4. Nếu ghi `Never expire` → bấm **Actions** → **Edit retention setting** → chọn `14 days` → **Save**.

#### C. SNS Topic
1. Thanh tìm kiếm → gõ **SNS** → bấm **Simple Notification Service**.
2. Menu trái → **Topics** → tìm topic `budgetbot-hackathon-alerts`.
3. Bấm vào → tab **Subscriptions** → xác nhận có ít nhất 1 subscription (Email/SMS).
4. Status phải ghi `Confirmed`. Nếu `Pending confirmation` → kiểm tra email và bấm link xác nhận.

---

## 15. Amazon EventBridge (Tự động hóa)

### Nhóm đã cấu hình gì?
| Cấu hình | Giá trị |
|----------|---------|
| Self-Healing Rule | Lắng nghe CloudTrail event `DeletePublicAccessBlock` trên S3 → tự động gọi Lambda khóa lại |
| Cost Guard Schedule | Cron-job chạy Lambda kiểm tra chi phí hàng ngày |

### Lợi ích
- Tự động vá lỗ hổng bảo mật trong vài giây mà không cần con người can thiệp.
- Tự động hóa đánh giá chi phí.

### Cách mở trên Console (từng bước)

#### A. S3 Auto-Remediation Rule
1. Thanh tìm kiếm → gõ **EventBridge** → bấm **Amazon EventBridge**.
2. Menu trái → **Rules** → chọn Event bus: `default`.
3. Tìm rule tên chứa `s3-remediation` hoặc `security-guard` → bấm vào.
4. **Kiểm tra Event Pattern:**
   ```json
   {
     "source": ["aws.s3"],
     "detail-type": ["AWS API Call via CloudTrail"],
     "detail": {
       "eventName": ["DeletePublicAccessBlock", "PutBucketPublicAccessBlock"]
     }
   }
   ```
5. **Kiểm tra Target:**
   - Target type: `Lambda function`.
   - Function: `budgetbot-s3-remediation` (hoặc tên tương tự).
6. **Cách test thử (Demo cho Mentor):**
   - Vào S3 → Uploads bucket → Tab **Permissions** → **Edit** Block public access → **Tắt bớt 1 ô** → Save.
   - Đợi 5-10 giây → Quay lại kiểm tra → **4 ô đã tự động bật lại** ← Đây chính là Auto-Remediation!
   - Vào CloudTrail → **Event history** → tìm event `PutPublicAccessBlock` do Lambda thực thi → Đây là bằng chứng.

#### B. Cost Guard Schedule (nếu có)
1. Vẫn ở **EventBridge** → menu trái → **Schedules** (hoặc **Rules** nếu dùng cron expression).
2. Tìm schedule tên chứa `cost-guard`.
3. Kiểm tra:
   - Schedule expression: `cron(0 8 * * ? *)` (chạy lúc 8:00 AM UTC mỗi ngày).
   - Target: Lambda function `budgetbot-cost-guard`.

---

## 📋 Bảng Tổng Hợp Nhanh (Quick Reference)

| Dịch vụ AWS | Cấu hình đặc biệt | Lợi ích |
|:---|:---|:---|
| **Amazon VPC** | CIDR `10.0.0.0/16`, 2 Private Subnets (Multi-AZ), **No NAT** | HA + Cô lập mạng + Tiết kiệm $32/tháng |
| **VPC Gateway Endpoints** | Gateway cho S3 và DynamoDB | Truy xuất nội bộ, **miễn phí 100%** |
| **VPC Interface Endpoints** | Interface cho Bedrock Runtime và Textract, Private DNS bật, SG port 443 | Lambda gọi AI an toàn không qua Internet |
| **AWS Lambda** | `arm64`, VPC config, timeout 30s | +19% hiệu năng, -20% giá, Scale to Zero |
| **Amazon Bedrock** | Claude 4.5 Haiku via Cross-Region Inference | Model mới nhất, throughput cao |
| **AWS IAM** | Least-privilege, không dùng `*` | Giảm thiểu rủi ro bị hack |
| **Amazon S3** | Block Public 100%, Lifecycle 30d→IA / 90d→Delete, SSE-KMS | Bảo mật + Tiết kiệm >80% storage |
| **AWS KMS** | CMK riêng cho S3 + Backup | Mã hóa AES-256 + Audit Trail |
| **Amazon DynamoDB** | PAY_PER_REQUEST, PITR bật | $0 khi rảnh + Khôi phục đến từng giây |
| **AWS Backup** | Vault + Daily Plan 2:00 AM, giữ 7 ngày | Sao lưu tự động 100% |
| **API Gateway** | HTTP API, Throttle 10/s burst 20, CORS chặt | Chống DDoS / Denial of Wallet |
| **CloudFront** | OAC, redirect-to-https, 403/404→index.html | Bảo mật CDN + React Router hoạt động |
| **AWS Budgets** | $10/tháng, cảnh báo 80% | Phanh khẩn cấp chi tiêu |
| **CloudWatch & SNS** | Alarm Errors>=1, Log 14 ngày, SNS alerts topic | Phát hiện sự cố + Tiết kiệm log |
| **EventBridge** | Self-Healing rule cho S3, Cost Guard cron | Auto-Remediation + Tự động kiểm chi phí |
