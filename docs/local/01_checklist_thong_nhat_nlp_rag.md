# TÀI LIỆU THỐNG NHẤT GIAO DIỆN & QUY TẮC PHỐI HỢP GIỮA MODULE NLP VÀ RAG

> **Đề tài:** Xây dựng hệ thống hỗ trợ quản lý chi tiêu cá nhân dựa trên phân loại giao dịch bằng NLP và hỏi đáp bằng RAG  
> **Sinh viên thực hiện:**  
> 1. Võ Hồng Đức (MSV: 22IT070 - Lớp: 22GIT) — Phụ trách: **RAG & Backend**  
> 2. Phan Nguyễn Huy Hoàng (MSV: 22IT101 - Lớp: 22GIT) — Phụ trách: **NLP & Frontend**  
> **Người hướng dẫn:** ThS. Dương Thị Mai Nga  
> **Môi trường triển khai:** Local / On-Premise (Không phụ thuộc AWS Cloud)  
> 📄 **Kế hoạch triển khai:** Xem chi tiết kế hoạch chuyển đổi mã nguồn và phân công theo đề cương tại [02_ke_hoach_chuyen_doi_local_theo_de_cuong.md](./02_ke_hoach_chuyen_doi_local_theo_de_cuong.md).

---

## 1. BỘ DANH MỤC: MÃ, TÊN VÀ QUY TẮC GÁN NHÃN

Hệ thống thống nhất sử dụng **10 danh mục cố định** chuẩn tiếng Anh (PascalCase) làm định danh (Key/Class label) xuyên suốt từ mô hình NLP, Cơ sở dữ liệu đến giao diện Frontend:

| STT | Tên Danh Mục (Key/Label) | Tên Tiếng Việt Hiển Thị | Quy Tắc Nhận Diện & Gán Nhãn | Ví Dụ Điển Hình |
| :---: | :--- | :--- | :--- | :--- |
| 1 | `Food` | Ăn uống & Thực phẩm | Mọi chi tiêu cho nhà hàng, quán ăn, cafe, trà sữa, siêu thị đồ ăn, giao thức ăn. | Highlands Coffee, Phở Thìn, GrabFood, ShopeeFood, Winmart đồ ăn |
| 2 | `Transport` | Đi lại & Di chuyển | Chi phí xe cộ, xăng dầu, gọi xe công nghệ, vé tàu/xe/máy bay, gửi xe. | Grab, Be, Xanh SM, Đổ xăng Petrolimex, Vé xe Phương Trang |
| 3 | `Shopping` | Mua sắm cá nhân | Quần áo, giày dép, mỹ phẩm, đồ gia dụng, sàn thương mại điện tử. | Shopee, Lazada, Tiki, Zara, Uniqlo, Mua sách Tiki |
| 4 | `Utilities` | Hóa đơn & Tiện ích | Các chi phí sinh hoạt cố định: điện, nước, internet, truyền hình, điện thoại. | Tiền điện EVN, Tiền nước Sawaco, Cước internet FPT, Viettel, VNPT |
| 5 | `Entertainment` | Giải trí & Thư giãn | Vé xem phim, trò chơi điện tử, concert, karaoke, du lịch nghỉ dưỡng. | CGV Cinema, Lotte Cinema, Steam Game, Spotify Event, Vé concert |
| 6 | `Health` | Y tế & Sức khỏe | Khám chữa bệnh, thuốc men, phòng khám, bệnh viện, thực phẩm chức năng. | Nhà thuốc Long Châu, Pharmacity, Bệnh viện Hoàn Mỹ, Phòng khám Medlatec |
| 7 | `Subscriptions` | Dịch vụ định kỳ | Các gói dịch vụ trả phí gia hạn hàng tháng/năm trên nền tảng số. | Netflix, Spotify Premium, iCloud, ChatGPT Plus, GitHub Pro |
| 8 | `Income` | Thu nhập | Mọi khoản tiền vào: lương, thưởng, hoàn tiền, nhận chuyển khoản, quà biếu. | Chuyển khoản lương, Thưởng dự án, Tiền lì xì, Hoàn tiền Shopee |
| 9 | `Transfer` | Chuyển tiền / Tiết kiệm | Chuyển tiền cho người thân/bạn bè, gửi tiền vào quỹ tiết kiệm, trả nợ. | Chuyển tiền tiết kiệm, Trả nợ bạn vay tháng trước, Chuyển nội bộ |
| 10 | `Other` | Khác | Mã giao dịch ngân hàng viết tắt không rõ nghĩa, chi phí phát sinh không thuộc các nhóm trên. | FT0024918239, Phí quản lý tài khoản, TRX89312... |

* **Quy ước mã nhãn (Label Encoding cho NLP):**
  * `0: Food`, `1: Transport`, `2: Shopping`, `3: Utilities`, `4: Entertainment`
  * `5: Health`, `6: Subscriptions`, `7: Income`, `8: Transfer`, `9: Other`

---

## 2. SCHEMA GIAO DỊCH (DATABASE & API)

Dữ liệu giao dịch được lưu trữ tập trung tại **PostgreSQL** và trao đổi qua REST API theo cấu trúc chuẩn:

### 2.1. Cấu trúc bảng PostgreSQL (`transactions`)
```sql
CREATE TABLE IF NOT EXISTS transactions (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    txn_date DATE NOT NULL,
    description TEXT NOT NULL,
    amount NUMERIC(14, 2) NOT NULL,
    category VARCHAR(50) NOT NULL DEFAULT 'Other',
    confidence VARCHAR(20) DEFAULT 'high',
    engine VARCHAR(50) DEFAULT 'nlp_linear_svc',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_transactions_user_date ON transactions(user_id, txn_date);
CREATE INDEX idx_transactions_user_category ON transactions(user_id, category);
```

### 2.2. Quy ước kiểu dữ liệu & Bắt buộc
* `user_id`: Chuỗi định danh người dùng (Bắt buộc).
* `txn_date`: Định dạng chuẩn `YYYY-MM-DD` (Bắt buộc).
* `description`: Chuỗi mô tả giao dịch (Bắt buộc, không được để trống).
* `amount`: Số thực `float` / `numeric` (Bắt buộc, có phân biệt âm/dương).
* `category`: Thuộc 1 trong 10 danh mục ở Mục 1 (Bắt buộc).
* `confidence`: Mức độ tin cậy từ mô hình: `'high'` | `'medium'` | `'low'` (Mặc định: `'high'`).

---

## 3. QUY ƯỚC SỐ TIỀN, NGÀY THÁNG VÀ PHẠM VI THU/CHI

* **Đơn vị tiền tệ:** Mặc định là Việt Nam Đồng (**VND**).
* **Quy ước dấu:**
  * **Khoản chi (Expense):** Luôn là **SỐ ÂM** (`amount < 0`, ví dụ: `-65000`).
  * **Khoản thu (Income):** Luôn là **SỐ DƯƠNG** (`amount > 0`, ví dụ: `+18500000`).
* **Logic chuẩn hóa:**
  * Nếu danh mục là `Income` ➔ Ép buộc `amount = abs(amount)`.
  * Nếu danh mục khác ➔ Ép buộc `amount = -abs(amount)`.
* **Quy ước ngày tháng:**
  * Ngày giao dịch: `YYYY-MM-DD` (ví dụ: `2026-05-02`).
  * Tháng báo cáo/thống kê: `YYYY-MM` (ví dụ: `2026-05`).

---

## 4. ĐẦU VÀO VÀ ĐẦU RA CỦA MODULE NLP

Module phân loại giao dịch do **Phan Nguyễn Huy Hoàng** phát triển bằng thuật toán học máy (TF-IDF + Linear SVC / Naive Bayes).

### 4.1. Đầu vào (Input)
* `description`: `str` — Chuỗi mô tả giao dịch thô hoặc đã chuẩn hóa cơ bản.
  * *Ví dụ:* `"Highlands Coffee Crescent Mall"`, `"Chuyen tien an trua"`, `"Tien dien thang 4"`.
* *(Tùy chọn)* `amount`: `float` — Dùng để áp dụng rule bổ trợ (nếu `amount > 0` và có từ khóa nhận tiền ➔ ưu tiên phân loại `Income`).

### 4.2. Đầu ra (Output)
Hàm dự đoán trả về kiểu `dict` (hoặc JSON):
```json
{
  "category": "Food",
  "confidence": 0.92,
  "confidence_level": "high",
  "engine": "linear_svc"
}
```
* **Quy tắc xếp mức `confidence_level`:**
  * Xác suất $\ge 0.75$: `"high"`
  * $0.50 \le$ Xác suất $< 0.75$: `"medium"`
  * Xác suất $< 0.50$: `"low"` ➔ Tự động gắn nhãn `"Other"` và gắn cờ cần người dùng kiểm tra.

---

## 5. PHÂN CHIA TRÁCH NHIỆM TIỀN XỬ LÝ (PREPROCESSING)

| Thành phần | Người phụ trách | Nhiệm vụ cụ thể |
| :--- | :---: | :--- |
| **Tiền xử lý dữ liệu nhập (File/API)** | **Võ Hồng Đức** | • Đọc parse file CSV/Excel sao kê.<br>• Loại bỏ dòng trống, chuẩn hóa định dạng số tiền (bỏ dấu phẩy, khoảng trắng).<br>• Chuẩn hóa ngày tháng về định dạng ISO `YYYY-MM-DD`.<br>• Trích xuất trường `description` sạch gửi sang Module NLP. |
| **Tiền xử lý văn bản NLP tiếng Việt** | **Phan Nguyễn Huy Hoàng** | • Chuẩn hóa bảng mã Unicode tiếng Việt (NFC).<br>• Chuyển chữ thường (lowercase).<br>• Loại bỏ ký tự đặc biệt, số điện thoại, số tài khoản vô nghĩa.<br>• Tách từ tiếng Việt (Tokenization) bằng `pyvi` hoặc `underthesea`.<br>• Biến đổi văn bản qua ma trận `TfidfVectorizer`. |

---

## 6. CÁCH GỌI NLP: IMPORT MODULE TRỰC TIẾP

Để hệ thống chạy mượt mà trên môi trường Local, tránh phát sinh lỗi mạng giữa các cổng (ports), hai bên thống nhất **Import Module trực tiếp qua file `.joblib`**:

### 6.1. Cấu trúc thư mục đóng gói (Hoàng bàn giao)
```text
src/
└── nlp/
    ├── __init__.py
    ├── tfidf_vectorizer.joblib     # Mô hình TF-IDF đã fit
    ├── classifier_model.joblib     # Mô hình Linear SVC / Naive Bayes đã train
    ├── preprocessor.py             # Hàm làm sạch & tách từ tiếng Việt
    └── predictor.py                # Class hoặc hàm dự đoán chính
```

### 6.2. Chữ ký hàm chuẩn trong `src/nlp/predictor.py`
```python
def predict_transaction(description: str, amount: float = None) -> dict:
    """
    Dự đoán danh mục chi tiêu từ nội dung giao dịch.
    Returns: {"category": str, "confidence": float, "confidence_level": str}
    """
```

### 6.3. Cách Backend (Đức) gọi sử dụng trong FastAPI
```python
from src.nlp.predictor import predict_transaction

# Trong route xử lý upload hoặc thêm giao dịch
result = predict_transaction(row["description"], row["amount"])
category = result["category"]
confidence = result["confidence_level"]
```

---

## 7. QUY TẮC XỬ LÝ LỖI VÀ NGƯỜI DÙNG SỬA DANH MỤC

Hệ thống triển khai cơ chế **Human-in-the-loop** nhằm đảm bảo dữ liệu luôn chính xác:

1. **Phân luồng tự động dựa trên Confidence:**
   * **`confidence_level == 'high'`:** Backend tự động lưu ngay vào bảng `transactions` trong PostgreSQL.
   * **`confidence_level in ('medium', 'low')`:** Giao dịch **chưa lưu vào DB ngay**, mà được đưa vào mảng `needs_review: []` trả về cho Frontend.
2. **Giao diện xác nhận (Frontend):**
   * Frontend hiển thị Modal danh sách các giao dịch nghi ngờ (`needs_review`).
   * Người dùng được phép chọn lại danh mục đúng thông qua Dropdown 10 danh mục.
3. **Lưu xác nhận:**
   * Frontend gửi mảng các giao dịch đã sửa lên API `POST /transactions/batch`.
   * Backend lưu các giao dịch này vào PostgreSQL với cờ `confidence = 'high'` (vì đã có con người xác nhận).
4. **Chỉnh sửa sau đó:**
   * Người dùng có thể sửa đổi bất kỳ lúc nào qua API `PUT /transactions/{id}` và xóa qua `DELETE /transactions/{id}`.

---

## 8. QUY TẮC CẬP NHẬT DỮ LIỆU RAG (CHROMA DB)

Hệ thống RAG do **Võ Hồng Đức** phụ trách sẽ tổng hợp dữ liệu chi tiêu có cấu trúc từ PostgreSQL thành các đoạn văn bản giàu ngữ cảnh (Semantic Chunks) để lưu vào Vector Database:

### 8.1. Cấu trúc 2 tầng Chunking của RAG
* **Tầng 1 - Chunk Tổng quan tháng (Monthly Summary):**
  * *Nội dung sinh tự động:* `"Báo cáo tổng kết chi tiêu tháng MM/YYYY của người dùng: Tổng thu nhập: ... VND. Tổng chi tiêu: ... VND. Tiết kiệm ròng: ... VND. Các danh mục chi tiêu cao nhất: Food (...%), Transport (...%)..."`
  * *Document ID:* `summary_{user_id}_{YYYY-MM}`
* **Tầng 2 - Chunk Chi tiết từng danh mục (Category Breakdown):**
  * *Nội dung sinh tự động:* `"Chi tiết danh mục [Category] tháng MM/YYYY: Tổng số tiền: ... VND với ... giao dịch. Các khoản chi lớn nhất gồm: [Tên - Số tiền - Ngày]..."`
  * *Document ID:* `cat_{user_id}_{YYYY-MM}_{category}`

### 8.2. Quy tắc kích hoạt cập nhật (Sync Events)
* **Khi nào cập nhật:**
  1. Khi người dùng hoàn tất upload file sao kê mới (`POST /upload` hoàn tất).
  2. Khi người dùng xác nhận lưu các giao dịch duyệt tay (`POST /transactions/batch`).
  3. Khi người dùng sửa/xóa giao dịch qua API (`PUT` hoặc `DELETE /transactions/{id}`).
* **Cơ chế ghi đè (Upsert):**
  * Thay vì thêm mới gây trùng lặp vector, hệ thống sử dụng hàm `collection.upsert()` theo `Document ID` cố định. Khi tháng đó có giao dịch thay đổi, văn bản tóm tắt được tính toán lại và ghi đè vào đúng ID vector cũ.

---

## 9. BỘ DỮ LIỆU KIỂM THỬ CHUNG (TEST DATASETS)

Hai bên thống nhất xây dựng và sử dụng **2 bộ dataset chuẩn** đặt tại thư mục [`sample_data/`](../../sample_data/) để phục vụ đánh giá theo đúng đề cương:

### 9.1. Dataset kiểm thử NLP (`sample_data/eval_nlp.csv`) — Hoàng phụ trách
* Gồm tối thiểu 100 - 200 dòng giao dịch thực tế đặc trưng Việt Nam đã có nhãn chuẩn (`true_category`).
* Cột: `date,description,amount,true_category`.
* Dùng để chạy script sinh báo cáo đánh giá mô hình:
  * **Accuracy**
  * **Precision**
  * **Recall**
  * **F1-Score và Macro F1**

### 9.2. Dataset kiểm thử RAG (`sample_data/eval_rag.json`) — Đức phụ trách
* Gồm 20 câu hỏi người dùng thường gặp về quản lý tài chính cá nhân (hỏi tổng tiền, so sánh tháng, tìm khoản chi lớn nhất, hỏi lời khuyên tiết kiệm).
* Cấu trúc mỗi mẫu:
  ```json
  {
    "question": "Tháng 05/2026 tôi đã chi bao nhiêu tiền cho việc ăn uống?",
    "ground_truth_context": "Chi tiết danh mục Food tháng 05/2026: Tổng số tiền: 4.500.000 VND...",
    "ground_truth_answer": "Trong tháng 05/2026, bạn đã chi tiêu 4.500.000 VND cho danh mục Ăn uống (Food)."
  }
  ```
* Dùng framework `ragas` đo 3 chỉ số cốt lõi:
  * **Context Precision** (Độ chính xác ngữ cảnh truy xuất)
  * **Context Recall** (Độ đầy đủ ngữ cảnh truy xuất)
  * **Faithfulness** (Độ trung thực, không ảo giác của câu trả lời)

---

## 10. KÝ XÁC NHẬN THỐNG NHẤT

| Đại diện Module RAG & Backend | Đại diện Module NLP & Frontend |
| :---: | :---: |
| *(Đã thống nhất)* | *(Đã thống nhất)* |
| **Võ Hồng Đức** | **Phan Nguyễn Huy Hoàng** |
