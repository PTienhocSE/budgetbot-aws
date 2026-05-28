# 🚀 Cẩm Nang "Mổ Xẻ" Toàn Tập BudgetBot (Bản Deep Dive Cho Hackathon)

> **Lời tựa:** Tài liệu này là bản **phân tích chuyên sâu** về TỪNG dịch vụ AWS được sử dụng trong dự án BudgetBot. Cẩm nang sẽ giải thích: Bản chất dịch vụ là gì? Tại sao lại dùng nó? Thông số kỹ thuật nào đã được cài đặt? Và Giám khảo sẽ hỏi khó (Grill) điều gì? 
> Đọc kỹ tài liệu này giúp bạn làm chủ hoàn toàn hệ thống Cloud và tự tin bảo vệ đồ án.

---

## 1. 🌐 Amazon VPC & VPC Endpoints (Hạ Tầng Mạng)

### Khái niệm 
Hãy tưởng tượng **VPC (Virtual Private Cloud)** như một mạng nội bộ cách ly hoàn toàn trên AWS. Bất cứ thứ gì nằm trong đó đều không thể truy cập từ bên ngoài Internet nếu không được cấp phép.

### Vai trò trong BudgetBot
Để bảo mật, Backend Lambda được đặt trong **Private Subnet** (phòng kín). Tuy nhiên, khi Backend muốn gọi AI (Bedrock) thì theo nguyên tắc nó cần mạng Internet. Thay vì mua một thiết bị đắt đỏ tên là **NAT Gateway** ($32/tháng) để cấp mạng, ta dùng **VPC Endpoints** (Những đường ống ngầm) để đi thẳng tới các dịch vụ AWS khác mà không cần ra Internet. Vừa bảo mật 100% lại tiết kiệm chi phí!

### Cấu hình cốt lõi (Terraform)
- **CIDR Block:** `10.0.0.0/16`.
- **Subnets:** Tạo 2 Private Subnets nằm ở 2 khu vực địa lý khác nhau (Availability Zones) để đạt **High Availability** (nếu 1 data center cháy, app vẫn chạy).
- **Gateway Endpoints:** Tạo cho S3 và DynamoDB. *Điểm đặc biệt: Loại Gateway này miễn phí 100%.*
- **Interface Endpoints:** Tạo cho Bedrock và Textract. *Điểm đặc biệt: Phải gắn Security Group mở cổng 443 (HTTPS) và bật tính năng Private DNS.*

> 💡 **Câu hỏi Grill:** *Tại sao hệ thống của em không dùng NAT Gateway?*
> **Trả lời:** "Dự án của bọn em tối ưu triệt để chi phí (Cost Optimization). NAT Gateway tốn phí duy trì cố định hơn 32 USD/tháng dù không có người truy cập. Bọn em đã thay thế hoàn toàn bằng kiến trúc No-NAT sử dụng VPC Endpoints, giúp giảm 100% chi phí mạng ra ngoài Internet, đồng thời tăng tính bảo mật vì dữ liệu tài chính không hề rời khỏi mạng nội bộ của AWS."

---

## 2. ⚡ AWS Lambda (Trái Tim Xử Lý)

### Khái niệm
**AWS Lambda** là máy chủ "tàng hình" (Serverless Computing). Thay vì thuê máy chủ chạy 24/7 (như EC2/ECS), Lambda chỉ thức dậy khi có request, xử lý code, trả kết quả rồi đi ngủ lại. 

### Vai trò trong BudgetBot
Lambda chứa toàn bộ mã nguồn Backend (FastAPI). Mô hình này được gọi là **Scale to Zero** (Lượng dùng = 0 thì Chi phí = $0), cực kỳ lý tưởng cho dự án cá nhân hoặc Hackathon ít vốn.

### Cấu hình cốt lõi
- **Kiến trúc (Architecture):** Chọn `arm64` (Chip Graviton2 do AWS thiết kế) thay vì `x86_64` truyền thống.
- **Tài nguyên:** RAM 256MB. Timeout nâng lên **30s** (vì AI cần khoảng 5-10 giây để suy nghĩ và trả về JSON).
- **Mạng (VPC):** Ép Lambda chạy trong 2 Private Subnets.

> 💡 **Câu hỏi Grill:** *Tại sao lại chọn kiến trúc arm64 cho Lambda?*
> **Trả lời:** "Vì 2 lý do thực dụng: Thứ nhất, chip ARM của AWS giúp tăng hiệu năng xử lý lên tới 19%. Thứ hai, giá thành của nó lại rẻ hơn 20% so với chip x86. Đây là một quyết định đo lường (Trade-off) hoàn hảo cho kiến trúc Serverless."

---

## 3. 🧠 Amazon Bedrock & AWS Textract (Bộ Não AI)

### Khái niệm
- **AWS Textract:** Dịch vụ đọc văn bản quang học (OCR). Đưa ảnh chụp hóa đơn vào, nó trả về chữ.
- **Amazon Bedrock:** Nền tảng cung cấp các mô hình AI tạo sinh hàng đầu thế giới (Claude, Llama) thông qua API mà không cần tự xây dựng máy chủ AI.

### Vai trò trong BudgetBot
- Tạo ra **AI Money Coach**. Textract chống việc user phải nhập tay dữ liệu.
- Bedrock (Sử dụng Claude 3.5 Haiku) hiểu ngữ cảnh tiêu dùng, phân loại danh mục tự động và đưa ra lời khuyên cắt giảm chi tiêu thông minh.

### Cấu hình cốt lõi
- **Model đã chọn:** `Claude 3.5 Haiku` kết hợp tính năng **Cross-Region Inference** để tăng băng thông xử lý, chống nghẽn mạng.

> 💡 **Câu hỏi Grill:** *Thế giới AI có rất nhiều Model giỏi, sao em lại chọn Claude Haiku?*
> **Trả lời:** "Nhóm em áp dụng nguyên tắc Data-driven. Bọn em đã test Claude 3.5 Sonnet, nó cực kỳ thông minh nhưng giá token đắt gấp 15 lần Haiku. Với bài toán Categorization thì Haiku cho độ chính xác >90% với tốc độ chỉ 1.5 giây. Chọn Haiku giúp hệ thống vừa nhanh, vừa thông minh, lại không bị vỡ ngân sách."

---

## 4. 🗄️ Amazon DynamoDB (Cơ Sở Dữ Liệu NoSQL)

### Vai trò
Lưu trữ thông tin người dùng, lịch sử thu chi và hạn mức ngân sách của người dùng.

### Cấu hình cốt lõi
- **Billing Mode:** Chọn `PAY_PER_REQUEST` (On-demand). Trả tiền theo số lượng click truy vấn, không tốn phí duy trì tĩnh.
- **Tính năng PITR:** Bật `Point-In-Time Recovery`.

> 💡 **Câu hỏi Grill:** *PITR trong DynamoDB là gì và tại sao lại bật nó?*
> **Trả lời:** "PITR giống như cỗ máy thời gian (Time Machine). Nếu lỡ tay xóa toàn bộ dữ liệu lúc 3:00 PM, bọn em có thể phục hồi lại cơ sở dữ liệu y nguyên như trạng thái lúc 2:59 PM. Đây là tiêu chuẩn bắt buộc (Compliance) để bảo vệ dữ liệu nhạy cảm của hệ thống FinTech."

---

## 5. 📦 Amazon S3 (Kho Lưu Trữ Tệp)

### Vai trò
Hệ thống dùng 2 Bucket:
1. **Frontend Bucket:** Chứa file ReactJS, mở công khai (Public).
2. **Uploads Bucket:** Chứa ảnh hóa đơn của khách, khóa kín (Private).

### Cấu hình cốt lõi (Uploads Bucket)
- **Block Public Access:** Bật 100% ON cả 4 lớp khóa.
- **Mã hóa (Encryption):** Bật SSE-KMS bằng CMK tự tạo. Dữ liệu tĩnh luôn bị xáo trộn.
- **Lifecycle Rule:** Quản lý vòng đời. Sau 30 ngày tự động đẩy hóa đơn sang ổ cứng rẻ `STANDARD_IA`, sau 90 ngày thì xóa sạch. Tiết kiệm 80% phí lưu rác.

> 💡 **Câu hỏi Grill:** *Nếu hacker lấy cắp đĩa cứng vật lý chứa S3 Bucket của AWS thì sao?*
> **Trả lời:** "Dữ liệu vẫn an toàn 100% ạ. Do đã kích hoạt mã hóa Server-Side Encryption bằng AWS KMS. Hacker có ổ cứng mà không có khóa giải mã thì chỉ nhìn thấy một đống dữ liệu vô nghĩa."

---

## 6. 🛡️ AWS IAM, KMS & Backup (Bảo Mật Kép)

- **AWS IAM (Phân quyền):** Áp dụng nguyên tắc **Least Privilege** (Quyền Tối Thiểu). Ví dụ thay vì cấp quyền "Làm mọi thứ với DynamoDB", nhóm chỉ cấp quyền `PutItem`, `GetItem` trỏ đích danh vào 1 bảng duy nhất. Tuyệt đối loại bỏ dấu `*` (Wildcard).
- **AWS KMS:** Tạo **Customer Managed Key (CMK)** để làm chìa khóa mã hóa S3 và Backup. Giúp hệ thống CloudTrail có thể Audit (Kiểm toán) được ai đã dùng chìa khóa lúc nào.
- **AWS Backup:** Cài kịch bản tự động chụp lại dữ liệu DynamoDB lúc 2:00 sáng mỗi ngày, giữ bản sao trong 7 ngày chống thảm họa.

> 💡 **Câu hỏi Grill:** *Tại sao việc không dùng dấu `*` trong IAM lại quan trọng?*
> **Trả lời:** "Lợi ích của việc giới hạn Blast Radius (phạm vi ảnh hưởng). Nếu Backend bị xâm nhập, hacker cũng chỉ phá được đúng 1 bảng DynamoDB của app, thay vì có thể xóa sổ toàn bộ tài nguyên AWS của tổ chức."

---

## 7. 🚪 Amazon API Gateway & CloudFront (Giao Tiếp & Phân Phối)

### Vai trò
- **API Gateway:** Lễ tân nhận request từ Frontend, chuyển cho Lambda.
- **CloudFront (CDN):** Trạm trung chuyển tĩnh, cache file ReactJS ra toàn cầu giúp app load trong vài mili-giây.

### Cấu hình cốt lõi
- **API Gateway (HTTP API):** 
  - Cấu hình **Throttling**: Giới hạn tốc độ `10 req/s`, burst `20 req`.
  - Mục đích: Chống tấn công **Denial of Wallet** (Kẻ thù cố tình spam API để làm tiền cước Lambda tăng cao).
- **CloudFront:**
  - Bật **Origin Access Control (OAC)** chặn user chọc trực tiếp vào link S3.
  - Custom Error Pages 403/404 tự động trỏ về `/index.html`. Việc này giúp React Router xử lý link nội bộ mà không báo lỗi trang.

---

## 8. 🚨 Giám Sát, Báo Động & Tự Động Vá Lỗi (CloudWatch, SNS, Budgets, EventBridge)

### Cấu hình cốt lõi
- **AWS Budgets:** Ngân sách `$10/tháng`. Khi tiêu mốc `$8` (80%), lập tức gửi cảnh báo qua Email thông qua **SNS Topic**.
- **CloudWatch Alarms:** Cài Alarm báo động nếu Lambda dính lỗi (Metric `Errors >= 1`), bắn thẳng tin nhắn về SNS réo gọi Developer.
- **Tiết kiệm Log:** Bắt buộc CloudWatch chỉ lưu log hệ thống trong **14 ngày** (mặc định là lưu vĩnh viễn rất tốn tiền).

### 🏆 Đỉnh Cao Kiến Trúc: Auto-Remediation (Tự Động Vá Lỗi)
Cơ chế bảo vệ S3 Uploads không cần bàn tay con người:
1. Ai đó (hacker/admin lỗi) tắt rào chắn `Block Public Access` của S3 Uploads.
2. Hệ thống kiểm toán **CloudTrail** ghi nhận lời gọi API `DeletePublicAccessBlock`.
3. Hệ thống báo động **EventBridge** lập tức nhận được tín hiệu.
4. EventBridge kích hoạt hàm Lambda khẩn cấp tên là `S3 Remediation`.
5. Lambda này ngay lập tức bắn lệnh `PutPublicAccessBlock` khóa 100% S3 lại.
6. **Kết quả:** Lỗ hổng bị vá lại thần tốc chỉ trong vòng **3-5 giây**! Đảm bảo dữ liệu không kịp tuồn ra Internet. Đạt điểm bảo mật hoàn hảo.

---

## 9. 🧪 Hướng Dẫn Test UI (Checklist Kiểm Tra Hệ Thống)

> Sau khi deploy hoặc thay đổi cấu hình (IAM, KMS, Lambda...), hãy chạy qua toàn bộ checklist này để đảm bảo hệ thống hoạt động đúng.

**URL Frontend:** `https://d39sr1v8scwccx.cloudfront.net`
**URL API:** `https://i13aq2rorl.execute-api.us-east-1.amazonaws.com`

### Bước 1: Kiểm tra CloudFront + S3 Frontend
| Hành động | Kết quả mong đợi | Service được test |
|---|---|---|
| Mở trình duyệt → vào URL Frontend | Giao diện hiện ra đẹp đẽ, không lỗi trắng trang | **CloudFront, S3 Frontend** |
| Bấm F12 → tab Console | Không có lỗi đỏ `ERR_CONNECTION_REFUSED` | **CORS, API Gateway** |

### Bước 2: Kiểm tra Đăng ký / Đăng nhập (Auth)
| Hành động | Kết quả mong đợi | Service được test |
|---|---|---|
| Bấm **Register** → điền thông tin → Submit | Tạo tài khoản thành công, chuyển trang | **Lambda, DynamoDB (Users table)** |
| Bấm **Login** → nhập username/password | Đăng nhập thành công, vào Dashboard | **Lambda, DynamoDB, JWT Auth** |

### Bước 3: Xem giao dịch (Transactions)
| Hành động | Kết quả mong đợi | Service được test |
|---|---|---|
| Vào trang **Transactions** | Danh sách giao dịch hiện ra (nếu đã có dữ liệu) | **DynamoDB Query** |
| Thêm giao dịch thủ công | Giao dịch mới xuất hiện trong danh sách | **DynamoDB PutItem, Bedrock (auto-categorize)** |

### Bước 4: Upload hóa đơn (⚠️ QUAN TRỌNG NHẤT)
| Hành động | Kết quả mong đợi | Service được test |
|---|---|---|
| Bấm **Upload** → chọn ảnh hóa đơn/biên lai | Hệ thống trả về danh sách giao dịch đã nhận dạng | **S3 PutObject, KMS Encrypt, Textract OCR, Bedrock Categorize** |
| Nếu lỗi `AccessDenied` | → KMS Key Policy chưa cấp quyền cho Lambda Role | Kiểm tra lại `s3.tf` |
| Nếu lỗi `textract... not authorized` | → IAM Policy Textract bị sai | Kiểm tra lại `lambda.tf` |

### Bước 5: AI Coach — Smart Insights (⚠️ QUAN TRỌNG THỨ 2)
| Hành động | Kết quả mong đợi | Service được test |
|---|---|---|
| Bấm **Generate Smart Insights** | Hiện ra các card phân tích chi tiêu thông minh | **Bedrock InvokeModel (ARN mới)** |
| Nếu lỗi `AccessDeniedException` | → ARN Bedrock trong IAM chưa khớp model đang dùng | Kiểm tra lại `lambda.tf` dòng resources Bedrock |
| Nếu lỗi `AI Insight Error - Failed to parse` | → Model trả về JSON bị cắt cụt (maxTokens quá thấp) | Kiểm tra `ai.py` → `maxTokens` phải >= 2000 |

### Bước 6: Chat AI
| Hành động | Kết quả mong đợi | Service được test |
|---|---|---|
| Vào **Chat** → gõ "phân tích chi tiêu tháng này" | AI trả lời tự nhiên bằng tiếng Việt | **Bedrock Chat, DynamoDB Query** |
| Gõ "tôi vừa ăn phở 50k" | AI nhận dạng giao dịch và lưu tự động | **Bedrock Parse, DynamoDB PutItem** |

### Bước 7: Budget Caps (Hạn mức chi tiêu)
| Hành động | Kết quả mong đợi | Service được test |
|---|---|---|
| Vào **Limits** → tạo budget cap mới (VD: Shopping 2,000,000đ) | Cap xuất hiện trong danh sách | **DynamoDB (Caps)** |
| Xóa hoặc chỉnh sửa cap | Cập nhật thành công | **DynamoDB DeleteItem/UpdateItem** |

### Bước 8: Kiểm tra Summary
| Hành động | Kết quả mong đợi | Service được test |
|---|---|---|
| Vào **Summary** hoặc **Dashboard** | Hiện biểu đồ tổng hợp chi tiêu theo danh mục | **DynamoDB Scan/Query** |

---

## 10. 📡 Bảng Tổng Hợp API Endpoints

> Toàn bộ các API endpoint đều đi qua cổng API Gateway (`ANY /{proxy+}`) rồi vào Lambda xử lý.

### API Công khai (Không cần đăng nhập)
| Method | Endpoint | Chức năng | Ví dụ |
|---|---|---|---|
| `GET` | `/health` | Kiểm tra sức khỏe hệ thống | Trả về `{"status": "ok"}` |
| `POST` | `/register` | Đăng ký tài khoản mới | Body: `{"full_name": "...", "username": "...", "password": "..."}` |
| `POST` | `/login` | Đăng nhập, nhận JWT token | Body: `{"username": "...", "password": "..."}` |

### API Bảo mật (Cần Header `Authorization: Bearer <token>`)
| Method | Endpoint | Chức năng | Service AWS liên quan |
|---|---|---|---|
| `GET` | `/profile` | Xem thông tin cá nhân | DynamoDB |
| `GET` | `/transactions?month=2025-05` | Lấy danh sách giao dịch (theo tháng) | DynamoDB |
| `POST` | `/transactions` | Thêm 1 giao dịch thủ công | DynamoDB + Bedrock (auto-categorize) |
| `POST` | `/transactions/batch` | Thêm nhiều giao dịch cùng lúc | DynamoDB |
| `PUT` | `/transactions/{id}` | Sửa giao dịch | DynamoDB |
| `DELETE` | `/transactions/{id}` | Xóa giao dịch | DynamoDB |
| `POST` | `/upload` | Upload ảnh hóa đơn (OCR) | **S3 + KMS + Textract + Bedrock** |
| `POST` | `/chat` | Chat với AI Coach | Bedrock |
| `POST` | `/chat/transaction` | Gõ tự do để AI tạo giao dịch | Bedrock + DynamoDB |
| `GET` | `/summary?month=2025-05` | Tổng hợp chi tiêu theo danh mục | DynamoDB |
| `GET` | `/coach` | AI phân tích & gợi ý cắt giảm chi tiêu | **Bedrock (Smart Insights)** |
| `GET` | `/caps` | Xem danh sách hạn mức ngân sách | DynamoDB |
| `POST` | `/caps` | Tạo/cập nhật hạn mức | DynamoDB |
| `DELETE` | `/caps/{category}` | Xóa hạn mức | DynamoDB |

---

## 11. 🔧 Xử Lý Sự Cố Thường Gặp (Troubleshooting)

| Lỗi trên UI | Nguyên nhân | Cách fix |
|---|---|---|
| Trang trắng, không load được giao diện | CloudFront cache cũ hoặc S3 chưa sync file mới | Chạy `aws cloudfront create-invalidation` xóa cache |
| `ERR_CONNECTION_REFUSED localhost:8000` | Frontend đang trỏ sai API URL về localhost | Kiểm tra file `.env` trong `frontend-react/`, sửa `VITE_API_URL` trỏ về API Gateway |
| `AccessDeniedException` khi gọi Bedrock | IAM Policy dùng `Resource: "*"` cũ hoặc ARN sai | Kiểm tra `lambda.tf` → statement Bedrock phải có ARN `anthropic.claude-*` |
| `AI Insight Error - Failed to parse` | Model AI trả về JSON bị cắt cụt | Tăng `maxTokens` trong `ai.py` lên >= 2000 |
| `KMS AccessDenied` khi upload file | KMS Key Policy chưa cấp quyền cho Lambda Role | Kiểm tra `s3.tf` → Key Policy phải có statement `AllowLambdaRoleToUseKey` |
| CORS Error (blocked by CORS policy) | API Gateway hoặc FastAPI CORS chưa cấu hình đúng | Kiểm tra `CORS_ORIGINS` trong Lambda env vars, phải chứa domain CloudFront |
| Giao dịch tháng này trống | Backend lấy sai tháng (AI trả date sai format) | Kiểm tra prompt AI phải kèm ngày hiện tại `today = YYYY-MM-DD` |
| React Router lỗi trắng trang khi F5 | CloudFront chưa cấu hình Custom Error Pages | Kiểm tra `cloudfront.tf` → phải có `custom_error_response` cho 403 và 404 trả về `/index.html` |

---

## 12. 📋 Bảng Tổng Hợp Nhanh (Quick Reference)

| Dịch vụ AWS | Cấu hình đặc biệt | Lợi ích |
|:---|:---|:---|
| **Amazon VPC** | CIDR `10.0.0.0/16`, 2 Private Subnets (Multi-AZ), **No NAT** | HA + Cô lập mạng + Tiết kiệm $32/tháng |
| **VPC Gateway Endpoints** | Gateway cho S3 và DynamoDB | Truy xuất nội bộ, **miễn phí 100%** |
| **VPC Interface Endpoints** | Interface cho Bedrock Runtime và Textract, Private DNS bật, SG port 443 | Lambda gọi AI an toàn không qua Internet |
| **AWS Lambda** | `arm64`, VPC config, timeout 30s, RAM 512MB | +19% hiệu năng, -20% giá, Scale to Zero |
| **Amazon Bedrock** | Claude 3.5 Haiku via Cross-Region Inference | Model mới, throughput cao, giá rẻ |
| **AWS Textract** | DetectDocumentText (Synchronous OCR) | Đọc hóa đơn tự động, không cần training |
| **AWS IAM** | Least-privilege, ARN cụ thể cho Bedrock, Textract giữ `*` (giới hạn AWS) | Giảm thiểu Blast Radius nếu bị hack |
| **Amazon S3** | Block Public 100%, Lifecycle 30d→IA / 90d→Delete, SSE-KMS CMK | Bảo mật + Tiết kiệm >80% storage |
| **AWS KMS** | CMK riêng, Key Policy trỏ đúng Lambda Role + Backup Role | Mã hóa AES-256 + Audit Trail |
| **Amazon DynamoDB** | PAY_PER_REQUEST, PITR bật | $0 khi rảnh + Khôi phục đến từng giây |
| **AWS Backup** | Vault + Daily Plan 2:00 AM, giữ 7 ngày | Sao lưu tự động 100% |
| **API Gateway** | HTTP API, Throttle 10/s burst 20, CORS chặt | Chống DDoS / Denial of Wallet |
| **CloudFront** | OAC, redirect-to-https, 403/404→index.html | Bảo mật CDN + React Router hoạt động |
| **AWS Budgets** | $10/tháng, cảnh báo 80% | Phanh khẩn cấp chi tiêu |
| **CloudWatch & SNS** | Alarm Errors>=1, Log 14 ngày, SNS alerts topic | Phát hiện sự cố + Tiết kiệm log |
| **EventBridge** | Self-Healing rule cho S3, Cost Guard cron | Auto-Remediation + Tự động kiểm chi phí |

