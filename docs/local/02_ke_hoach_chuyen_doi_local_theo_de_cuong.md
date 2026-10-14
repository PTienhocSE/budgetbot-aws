# KẾ HOẠCH CHUYỂN ĐỔI HỆ THỐNG SANG LOCAL & ĐỒNG BỘ THEO ĐỀ CƯƠNG ĐATN

> **Đề tài:** Xây dựng hệ thống hỗ trợ quản lý chi tiêu cá nhân dựa trên phân loại giao dịch bằng NLP và hỏi đáp bằng RAG  
> **Sinh viên thực hiện:**  
> • Võ Hồng Đức (MSV: 22IT070) — **RAG & Backend**  
> • Phan Nguyễn Huy Hoàng (MSV: 22IT101) — **NLP & Frontend**  
> **Trường:** Đại học Công nghệ Thông tin và Truyền thông Việt - Hàn (VKU) — Khoa Khoa học Máy tính  

---

## 1. BỐI CẢNH VÀ MỤC TIÊU CHUYỂN ĐỔI

### 1.1. Hiện trạng của dự án gốc (`budgetbot-aws`)
* Được thiết kế làm mẫu cho cuộc thi AWS Hackathon:
  * Phân loại giao dịch bằng **AWS Bedrock (Claude 3.5 Haiku)** gọi API đám mây.
  * Cơ sở dữ liệu: **Amazon DynamoDB** (NoSQL).
  * Lưu trữ tệp: **Amazon S3**; Xử lý bất đồng bộ qua **AWS Lambda (Processor)**.
  * Chưa có hệ thống **Vector Database** (chưa có RAG thực thụ, chatbot hỏi đáp dùng Tool Use trực tiếp).
  * Nhược điểm: Tốn chi phí tài nguyên AWS hàng tháng, cấu hình VPC/IAM phức tạp, không khớp với nội dung đã đăng ký trong đề cương tốt nghiệp.

### 1.2. Mục tiêu chuyển đổi sang môi trường Local
1. **Chi phí 0 VNĐ:** Toàn bộ hệ thống chạy trên máy tính cá nhân (Localhost), không phụ thuộc thẻ tín dụng hay tài nguyên trả phí AWS.
2. **Khớp 100% với Đề cương ĐATN:**
   * Tích hợp mô hình học máy NLP truyền thống: **TF-IDF + Linear SVC / Naive Bayes** để phân loại giao dịch.
   * Xây dựng pipeline RAG hoàn chỉnh: **PostgreSQL ➔ Tổng hợp dữ liệu tháng/danh mục ➔ ChromaDB ➔ LangChain ➔ LLM**.
   * Đánh giá hệ thống bằng đầy đủ các chỉ số khoa học: **Accuracy, F1-Score (NLP)** và **Context Precision, Context Recall, Faithfulness (RAG)**.

---

## 2. MA TRẬN SO SÁNH THAY ĐỔI CÔNG NGHỆ

| Thành phần | Kiến trúc cũ (AWS Hackathon) | **Kiến trúc mới (Local ĐATN)** | Lý do thay đổi & Lợi ích |
| :--- | :--- | :--- | :--- |
| **Phân loại giao dịch (Categorization)** | AWS Bedrock API (Claude 3.5 Haiku) | **Mô hình ML: TF-IDF + Linear SVC / Naive Bayes** (file `.joblib`) | Khớp mục tiêu nghiên cứu NLP trong đề cương; chạy offline siêu nhanh (~5ms/giao dịch). |
| **Cơ sở dữ liệu (Database)** | Amazon DynamoDB | **PostgreSQL (chạy Local / Docker)** | Phù hợp truy vấn quan hệ, nhóm giao dịch theo tháng/danh mục; đúng đề cương phân công cho Đức. |
| **Vector Database (RAG)** | *Không có* (Dùng InvokeModel) | **ChromaDB Local** (thư mục `./_data/chromadb`) | Miễn phí, lưu file trực tiếp, hỗ trợ lọc metadata theo `user_id`, dễ tích hợp Python. |
| **Embedding Model** | *Không có* | **`BAAI/bge-m3`** hoặc **`keepitreal/vietnamese-sbert`** | Hiểu tiếng Việt xuất sắc, chạy trực tiếp trên CPU/GPU local. |
| **Mô hình LLM (Hỏi đáp)** | AWS Bedrock Claude Haiku | **Google Gemini 1.5/2.0 Flash (Free API)** hoặc **Ollama Qwen 2.5 (Local)** | Tốc độ cực nhanh, miễn phí quota hoàn toàn, tiếng Việt tự nhiên. |
| **Framework RAG** | *Không có* | **LangChain** (`langchain`, `langchain-community`) | Khung chuẩn xây dựng chuỗi truy xuất ngữ cảnh và sinh phản hồi. |
| **Lưu trữ file sao kê** | Amazon S3 | **Ổ cứng cục bộ (Local Storage)** (`./_data/uploads`) | Đơn giản, tin cậy, không cần kết nối mạng. |

---

## 3. SƠ ĐỒ KIẾN TRÚC HỆ THỐNG MỤC TIÊU (LOCAL)

```mermaid
flowchart TD
    subgraph Client ["Frontend (Hoàng phụ trách)"]
        UI["ReactJS Dashboard + Chat UI\n(Port 5173)"]
    end

    subgraph Server ["Backend Core (Đức phụ trách)"]
        API["FastAPI Web Server\n(Port 8000)"]
        PG[("PostgreSQL\n(Port 5432)")]
        Disk[("Local Storage\n./_data/uploads")]
    end

    subgraph NLP_Module ["Module NLP (Hoàng phụ trách)"]
        Pre["Tiền xử lý tiếng Việt\n(pyvi / underthesea)"]
        Vec["TF-IDF Vectorizer"]
        SVC["Linear SVC Classifier\n(.joblib)"]
    end

    subgraph RAG_Module ["Module RAG (Đức phụ trách)"]
        Agg["Bộ tổng hợp tóm tắt\n(Monthly & Category Chunks)"]
        Emb["Mô hình Embedding\n(bge-m3 / sbert)"]
        Chroma[("ChromaDB Vector Store\n./_data/chromadb")]
        LC["LangChain Retrieval Chain"]
        LLM["LLM Engine\n(Gemini Free / Ollama)"]
    end

    UI -->|"1. Tải lên sao kê CSV / Nhập tay"| API
    API -->|"2. Lưu file gốc"| Disk
    API -->|"3. Gửi nội dung text"| Pre --> Vec --> SVC
    SVC -->|"4. Trả về Category + Confidence"| API
    API -->|"5. Lưu giao dịch đã phân loại"| PG

    PG -->|"6. Đọc dữ liệu chi tiêu"| Agg
    Agg -->|"7. Tạo văn bản ngữ cảnh"| Emb --> Chroma

    UI -->|"8. Người dùng hỏi đáp chi tiêu"| API
    API -->|"9. Gửi câu hỏi"| LC
    Chroma -->|"10. Semantic Search Top Context"| LC
    LC <-->|"11. Sinh câu trả lời kèm dẫn chứng"| LLM
    LC -->|"12. Trả lời tư vấn tài chính"| API --> UI
```

---

## 4. CHI TIẾT CÁC THAY ĐỔI CẦN THỰC HIỆN TRONG SOURCE CODE

> 📄 **Tài liệu phối hợp liên quan:** Xem chi tiết 9 mục thống nhất kỹ thuật giữa NLP & RAG tại [01_checklist_thong_nhat_nlp_rag.md](./01_checklist_thong_nhat_nlp_rag.md).

### 4.1. Cấu hình hệ thống & Môi trường ([.env.example](../../.env.example))
Thay đổi file `.env` (dựa trên [`.env.example`](../../.env.example)) để chuyển từ AWS sang các adapter cục bộ:
```ini
# --- TẮT TOÀN BỘ BACKEND AWS ---
AI_BACKEND=nlp_ml
STORAGE_BACKEND=local
STORAGE_LOCAL_DIR=./_data/uploads

# --- CƠ SỞ DỮ LIỆU POSTGRESQL ---
USERSTORE_BACKEND=postgres
USERSTORE_POSTGRES_URL=postgresql://postgres:postgres@localhost:5432/budgetbot

# --- CẤU HÌNH RAG & VECTOR DB ---
RAG_VECTOR_DIR=./_data/chromadb
RAG_EMBEDDING_MODEL=BAAI/bge-m3
RAG_LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key_here

# --- CẤU HÌNH SERVER ---
CORS_ORIGINS=*
APP_PORT=8000
```

---

### 4.2. Nhiệm vụ cụ thể của Phan Nguyễn Huy Hoàng (NLP & Frontend)

#### Bước 1: Xây dựng & Huấn luyện mô hình NLP
* Tạo thư mục `src/nlp/`:
  * `train_nlp.py`:
    1. Đọc dữ liệu từ [`sample_data/bank_statement_q2_2026.csv`](../../sample_data/bank_statement_q2_2026.csv) và [`sample_data/eval_sample.csv`](../../sample_data/eval_sample.csv) (thu thập thêm để có tối thiểu 200 - 500 mẫu).
    2. Viết hàm tiền xử lý văn bản tiếng Việt: Chuẩn hóa Unicode NFC, xóa ký tự rác, lowercase, tách từ (tokenize) bằng `pyvi`.
    3. Trích xuất đặc trưng bằng `TfidfVectorizer(ngram_range=(1, 2), max_features=3000)`.
    4. Huấn luyện thử nghiệm 3 mô hình: **Linear SVC**, **Multinomial Naive Bayes**, **Logistic Regression**.
    5. Đánh giá và so sánh bằng `classification_report`: Accuracy, Precision, Recall, F1, Macro F1.
    6. Lưu mô hình tốt nhất thành 2 file: `tfidf_vectorizer.joblib` và `classifier_model.joblib`.
  * `predictor.py`: Đóng gói hàm `predict_transaction(text, amount)` để Backend gọi trực tiếp.

#### Bước 2: Tối ưu giao diện Frontend React
* Đảm bảo giao diện kết nối đúng vào API Backend local (`http://localhost:8000`).
* Màn hình **Transactions**: Hiển thị nhãn phân loại kèm badge độ tin cậy (`high`, `medium`, `low`).
* Màn hình **Review Modal**: Cho phép người dùng chỉnh sửa danh mục cho các khoản chi nghi ngờ.
* Màn hình **AI Coach / Chat**: Bổ sung khu vực hiển thị **"Dữ liệu tham khảo (Sources/Context)"** mà RAG trích xuất được để tăng tính minh bạch khi demo bảo vệ đồ án.

---

### 4.3. Nhiệm vụ cụ thể của Võ Hồng Đức (RAG & Backend)

#### Bước 1: Hoàn thiện Cơ sở dữ liệu PostgreSQL
* Hoàn thiện class `PostgresUserStore` trong [`src/adapters/userstore.py`](../../src/adapters/userstore.py):
  * Khởi tạo bảng `transactions` và bảng `users` (thay thế cho cơ chế DynamoDB hiện tại).
  * Đảm bảo các hàm `add_transaction`, `list_transactions`, `summary`, `update_transaction`, `delete_transaction` hoạt động mượt mà trên PostgreSQL.

#### Bước 2: Xây dựng Pipeline RAG với ChromaDB và LangChain
* Tạo thư mục `src/rag/`:
  * `ingestion.py`:
    * Hàm `aggregate_user_data(user_id, month)`: Truy vấn PostgreSQL và tạo văn bản tóm tắt có cấu trúc:
      * Tổng quan chi tiêu tháng: Tổng thu, tổng chi, tỷ lệ tiết kiệm.
      * Phân tích chi tiết từng danh mục: Tổng số tiền, số giao dịch, các khoản chi lớn nhất.
    * Hàm `sync_to_chromadb(user_id, month)`: Gọi embedding model (`BAAI/bge-m3`) và `upsert` các đoạn văn bản này vào ChromaDB.
  * `pipeline.py`:
    * Khởi tạo LangChain `RetrievalQA` kết hợp ChromaDB và Google Gemini Flash API (hoặc Ollama).
    * Thiết lập System Prompt chuyên biệt cho trợ lý tài chính tiếng Việt: Hướng dẫn LLM chỉ trả lời dựa trên context được cung cấp, không suy diễn ảo giác, trích dẫn rõ số liệu chi tiêu.

#### Bước 3: Đấu nối API Backend ([`src/handlers.py`](../../src/handlers.py))
* Đổi hàm xử lý upload: Sử dụng `predict_transaction` của Hoàng để phân loại giao dịch thay cho Bedrock.
* Đổi hàm `handle_chat`: Chuyển sang gọi hàm `rag_pipeline.query(user_id, message)`.
* Tự động gọi `sync_to_chromadb` sau khi upload hoặc sau khi user sửa/xóa giao dịch.

#### Bước 4: Xây dựng kịch bản đánh giá RAG bằng `ragas`
* Tạo script `eval_rag.py`:
  * Đo lường 3 chỉ số trong đề cương: **Context Precision**, **Context Recall**, và **Faithfulness**.
  * Xuất bảng số liệu phục vụ Chương 3 Báo cáo tốt nghiệp.

---

## 5. HƯỚNG DẪN CÀI ĐẶT & CHẠY HỆ THỐNG LOCAL

### 5.1. Khởi chạy PostgreSQL cục bộ
Dùng lệnh Docker đơn giản (hoặc cài PostgreSQL trực tiếp trên Windows):
```bash
docker run --name budgetbot-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=budgetbot \
  -p 5432:5432 -d postgres:15
```

### 5.2. Cài đặt thư viện Python
Cài đặt bổ sung các thư viện phục vụ NLP và RAG:
```bash
pip install psycopg2-binary scikit-learn pyvi joblib
pip install chromadb langchain langchain-community langchain-google-genai ragas
```

### 5.3. Khởi chạy Backend & Frontend
* **Terminal 1 — Backend FastAPI:**
  ```bash
  uvicorn src.app:app --reload --port 8000
  ```
* **Terminal 2 — Frontend React:**
  ```bash
  cd frontend-react
  npm install
  npm run dev
  ```
  Truy cập giao diện tại: `http://localhost:5173`.

---

## 6. LỘ TRÌNH THỰC HIỆN THEO TIẾN ĐỘ ĐỀ CƯƠNG ĐATN

| Giai đoạn | Thời gian | Nhiệm vụ chính của Hoàng (NLP & Frontend) | Nhiệm vụ chính của Đức (RAG & Backend) |
| :---: | :---: | :--- | :--- |
| **Giai đoạn 1** | 29/9 – 05/10 | Khảo sát yêu cầu, chuẩn bị dữ liệu giao dịch mẫu (`sample_data`). | Thiết kế schema cơ sở dữ liệu PostgreSQL, setup môi trường local. |
| **Giai đoạn 2** | 05/10 – 25/10 | Viết code tiền xử lý tiếng Việt, huấn luyện & so sánh Linear SVC vs Naive Bayes. Export file model `.joblib`. | Hoàn thiện các API CRUD quản lý giao dịch với PostgreSQL; kết nối model của Hoàng vào Backend. |
| **Giai đoạn 3** | 25/10 – 15/11 | Xây dựng giao diện web React, hoàn thiện Dashboard và Review Modal. | Xây dựng pipeline RAG (ChromaDB + LangChain + LLM); viết script đo RAGAS (Context Precision, Recall, Faithfulness). |
| **Giai đoạn 4** | 15/11 – 20/12 | Đánh giá mô hình NLP (Accuracy, Precision, Recall, Macro F1); hoàn thiện UI Chat. | Đấu nối toàn diện Backend - RAG - Frontend; tối ưu prompt và xử lý các case ngoại lệ. |
| **Giai đoạn 5** | 20/12 – 27/12 | Kiểm thử toàn diện hệ thống, viết Báo cáo phần NLP và kết quả thực nghiệm. | Kiểm thử toàn diện hệ thống, viết Báo cáo phần RAG, kiến trúc và kết luận đồ án. |
