# W7 — Giải Phẫu Từng Service (Cho người bắt đầu)

> Tài liệu này "dịch" toàn bộ những gì nhóm đã code bằng Terraform sang giao diện bấm tay (AWS Console) để bất cứ ai cũng có thể hiểu hệ thống đang được cài đặt những thông số gì bên dưới.

---

## 1. VPC & Mạng lưới (Không dùng NAT Gateway)
**Bí quyết:** Không tạo NAT Gateway để tiết kiệm tiền. Nhưng Lambda nằm trong Private Subnet làm sao gọi được Bedrock AI (nằm ngoài Internet)? Đáp án là VPC Endpoints.

**Cấu hình chi tiết (Settings):**
1. **VPC:** Tạo 1 VPC cấp phát dải IP `10.0.0.0/16`.
2. **Subnets:** Tạo 2 Private Subnets (cho Lambda) và 2 Public Subnets (cho đồ trang trí).
3. **VPC Endpoints (Kẻ đóng thế NAT Gateway):**
   - *Vào màn hình VPC > Endpoints > Create endpoint.*
   - **Endpoint 1 (S3):** Loại `Gateway Endpoint`. Chọn Service là `com.amazonaws.us-east-1.s3`. Gắn vào Route Table của Private Subnet. Mất $0 phí duy trì.
   - **Endpoint 2 (DynamoDB):** Loại `Gateway Endpoint`. Tương tự S3. Mất $0 phí duy trì.
   - **Endpoint 3 (Bedrock):** Loại `Interface Endpoint`. Chọn Service là `com.amazonaws.us-east-1.bedrock-runtime`. **Quan trọng:** Chọn Private Subnet và gắn Security Group cho phép Inbound HTTPS (Port 443). Mất phí tính theo giờ.
   - **Endpoint 4 (Textract):** Loại `Interface Endpoint`. Chọn Service là `com.amazonaws.us-east-1.textract`. (Cấu hình y hệt Bedrock).

---

## 2. AWS Lambda (Trái tim của hệ thống)
**Bí quyết:** Code xử lý tập trung ở 1 cục Lambda duy nhất, chạy trên chip ARM64.

**Cấu hình chi tiết (Settings):**
1. **Architecture:** Chọn `arm64` (thay vì x86_64 mặc định). Giá rẻ hơn, chạy nhanh hơn.
2. **Timeout:** Set lên `30 giây` (thay vì 3 giây mặc định) vì gọi AI Bedrock thỉnh thoảng mất 5-10 giây để suy nghĩ.
3. **VPC:** Đưa Lambda vào đúng 2 Private Subnets vừa tạo ở trên.
4. **Environment Variables:** Truyền vào các biến môi trường như `DYNAMODB_TABLE_NAME`, `S3_BUCKET_NAME` để code Python biết đường kết nối.
5. **IAM Role (Quyền hạn):** 
   - Không chọn quyền `AdministratorAccess` (Rất nguy hiểm).
   - Chỉ tạo 1 Role cấp đúng các quyền: `dynamodb:PutItem`, `s3:GetObject`, `bedrock:InvokeModel`, `textract:AnalyzeDocument`.

---

## 3. Amazon Bedrock & AWS Textract (Bộ não AI)
**Bí quyết:** Tích hợp AI không cần huấn luyện (No-training needed).

**Cấu hình chi tiết (Settings):**
1. **Bedrock Model Access:** Vào Amazon Bedrock > Model Access > Bấm Request access cho Model **Anthropic Claude 3 Haiku** (phải làm bằng tay trên Console, Terraform không cấp quyền này tự động được).
2. **Textract:** Dịch vụ này không cần setup gì thêm trên Console, chỉ cần IAM Role của Lambda có quyền gọi là xài được ngay.

---

## 4. Amazon S3 (Kho lưu trữ & Bảo mật)
**Bí quyết:** Khóa trái cửa (Block Public Access) và tự động bắt lỗi S3.

**Cấu hình chi tiết (Settings):**
1. **S3 Frontend Bucket:** Chứa file ReactJS. 
   - Tắt Block Public Access. 
   - Đính kèm **Bucket Policy** cho phép CloudFront (OAC) đọc file (`s3:GetObject`).
2. **S3 Uploads Bucket:** Chứa hóa đơn nhạy cảm của khách.
   - Bật **Block all public access (100%)**.
   - Kích hoạt **Server-Side Encryption (SSE-KMS)**, chọn cái chìa khóa CMK tự tạo ở dịch vụ KMS.
3. **Auto-Remediation (EventBridge + Lambda):**
   - Vào **EventBridge > Rules**. Tạo rule bắt sự kiện từ CloudTrail với điều kiện: `EventName = DeletePublicAccessBlock`.
   - Action (Đích đến): Gọi hàm **Lambda Security Guard**.
   - Cấu hình Lambda này gọi API `PutPublicAccessBlock` khóa bucket lại.

---

## 5. Amazon API Gateway (Cổng giao tiếp)
**Bí quyết:** Chặn các cuộc tấn công DDoS cơ bản và mở đường cho Frontend gọi Backend.

**Cấu hình chi tiết (Settings):**
1. **API Type:** Tạo `HTTP API` (nhanh và rẻ hơn REST API).
2. **Integration:** Trỏ thẳng vào Backend Lambda. Payload Format Version chọn `2.0`.
3. **CORS (Cross-Origin Resource Sharing):** 
   - Cực kỳ quan trọng để Frontend React gọi được API mà không bị lỗi mạng.
   - Allowed Origins: Điền link website CloudFront (`https://d39...cloudfront.net`).
   - Allowed Methods: `GET`, `POST`, `OPTIONS`.
   - Allowed Headers: `Authorization`, `Content-Type`.

---

## 6. Giám sát Sức khỏe & Chi phí (CloudWatch + Budgets)
**Bí quyết:** Không để hóa đơn cuối tháng làm bạn hết hồn.

**Cấu hình chi tiết (Settings):**
1. **CloudWatch Logs:** 
   - Mặc định AWS lưu log vĩnh viễn (tốn tiền). Vào Log Groups > Edit Retention > Chỉnh thành **14 days**.
2. **CloudWatch Alarms:**
   - Tạo Alarm giám sát Metric `Errors` của Backend Lambda.
   - Condition: Lỗi `>= 1` trong vòng 1 phút.
   - Action: Gửi cảnh báo vào **SNS Topic**.
3. **AWS Budgets:**
   - Tạo Budget loại `Cost budget`. Nhập ngân sách `$10`.
   - Alert Threshold: Khi chi tiêu chạm mốc `80%`. Đích đến là trỏ vào Email của bạn hoặc SNS Topic.

---
**🎁 Lời khuyên cuối cùng:** Bất cứ khi nào Giám khảo hỏi: *"Em đã cấu hình cái này ở đâu?"* Anh hãy lấy file này ra và đối chiếu nhé. Mọi thứ đã được nhóm Code 100% bằng Terraform, nhưng hiểu được cách bấm trên Console sẽ giúp anh làm chủ hệ thống tuyệt đối!
