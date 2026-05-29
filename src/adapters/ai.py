"""AI adapters. BudgetBot uses direct InvokeModel — no KB / no RAG.

Interface:
    categorize(description, amount, date) -> {"category": str, "confidence": "high|medium|low"}
"""
import datetime
import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


CATEGORIES = [
    "Food", "Transport", "Shopping", "Utilities", "Entertainment",
    "Health", "Subscriptions", "Income", "Transfer", "Other",
]


CATEGORIZE_PROMPT = """Categorize the following transaction into exactly one category.
Categories: {categories}

IMPORTANT GUIDELINES:
- If the transaction is about receiving money, salary, or incoming transfers (e.g., "nhận", "lương", "được chuyển", "thu", "lì xì"), you MUST categorize it as "Income".
- If the transaction is about spending or outgoing money (e.g., "mua", "trả", "chuyển khoản cho", "chi", "ăn", "uống", "đóng"), categorize it into the most appropriate expense category (Food, Transport, etc.).
- IMPORTANT FOR CONFIDENCE: If the description looks like an opaque transaction code (e.g., 'FT0024...', 'TRX...', random alphanumeric strings with no obvious meaning) or is highly ambiguous, assign confidence "low". Otherwise, if it's somewhat ambiguous, assign "medium". Usually assign "high".

Transaction: "{description}"
Amount: {amount}
Date: {date}

Respond with JSON only. No explanation.
{{"category": "<category>", "confidence": "high|medium|low"}}"""


EXTRACT_TRANSACTIONS_PROMPT = """Extract all financial transactions from the following text (e.g. from a PDF bank statement).
Categories: {categories}

IMPORTANT GUIDELINES:
- If the transaction is about receiving money, salary, or incoming transfers (or positive amounts), categorize it as "Income".
- If the transaction is about spending or outgoing money (or negative amounts), categorize it into the most appropriate expense category.
- Ensure dates are formatted as YYYY-MM-DD. If year is missing, assume current year.
- Ensure amounts are positive absolute numbers. The sign is determined by the category later.
- IMPORTANT FOR CONFIDENCE: If the description looks like an opaque transaction code (e.g., 'FT0024...', 'TRX...', random alphanumeric strings with no obvious meaning), assign confidence "low". Otherwise, if it's somewhat ambiguous, assign "medium". Usually assign "high".

Text:
{text}

Respond strictly with a JSON array of objects. No markdown formatting, no explanations.
[
  {{"date": "YYYY-MM-DD", "description": "...", "amount": 12345.67, "category": "...", "confidence": "high|medium|low"}}
]
"""


def _parse_json_response(text: str) -> dict:
    """Extract first JSON object from LLM response. Falls back to Other if invalid."""
    text = text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\n?|```$", "", text, flags=re.MULTILINE).strip()
    match = re.search(r"\{[^}]+\}", text, re.DOTALL)
    if match:
        try:
            obj = json.loads(match.group())
            if obj.get("category") in CATEGORIES:
                return {
                    "category": obj.get("category", "Other"),
                    "confidence": obj.get("confidence", "medium"),
                    "engine": "bedrock"
                }
        except json.JSONDecodeError:
            pass
    return {"category": "Other", "confidence": "low", "engine": "bedrock"}


class BedrockAI:
    def __init__(self, region: str, model_id: str):
        import boto3
        self.runtime = boto3.client("bedrock-runtime", region_name=region)
        self.model_id = model_id

    def categorize(self, description: str, amount: float, date: str) -> dict:
        prompt = CATEGORIZE_PROMPT.format(
            categories=", ".join(CATEGORIES),
            description=description,
            amount=amount,
            date=date,
        )
        resp = self.runtime.converse(
            modelId=self.model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": 100, "temperature": 0.0},
        )
        text = resp["output"]["message"]["content"][0]["text"]
        return _parse_json_response(text)

    def extract_transactions_from_text(self, text: str) -> list:
        prompt = EXTRACT_TRANSACTIONS_PROMPT.format(
            categories=", ".join(CATEGORIES),
            text=text,
        )
        resp = self.runtime.converse(
            modelId=self.model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": 2000, "temperature": 0.0},
        )
        reply = resp["output"]["message"]["content"][0]["text"].strip()
        if "```" in reply:
            reply = re.sub(r"^```(?:json)?\n?|```$", "", reply, flags=re.MULTILINE).strip()
        try:
            arr = json.loads(reply)
            if isinstance(arr, list):
                valid_txns = []
                for item in arr:
                    if "date" in item and "description" in item and "amount" in item:
                        cat = item.get("category", "Other")
                        if cat not in CATEGORIES:
                            cat = "Other"
                        valid_txns.append({
                            "date": str(item["date"]),
                            "description": str(item["description"]),
                            "amount": float(item["amount"]),
                            "category": cat,
                            "confidence": item.get("confidence", "medium"),
                            "engine": "bedrock"
                        })
                return valid_txns
        except Exception:
            pass
        return []

    def chat(self, user_id: str, message: str, userstore, history: list[dict] = None) -> str:
        from datetime import datetime, timezone
        current_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        system_prompt = f"""You are BudgetBot, a helpful AI financial coach. Today is {current_date}.
    Always answer in the same language as the user.
    You can use tools to fetch the user's spending summary or specific transactions.
    Always use tools if the user asks about spending, income, last month's totals, category breakdowns, or trends.
    Answer the user's exact question, not a generic summary.
    If the user asks about a specific category such as food, transport, shopping, utilities, health, subscriptions, or entertainment:
    - call get_transactions with the matching category and month if present
    - sum the returned transaction amounts before answering
    - list out the detailed transaction line-items (date, description, amount formatted in VND) in a clear bulleted list
    - do not answer with the top category or the overall total unless the user asked for it
    If the user asks about trends across 3 months:
    - fetch each of the last 3 months separately using get_spending_summary
    - compare the monthly totals and mention whether the trend is up, down, or flat
    - include 3 brief savings ideas tied to the observed categories
    Give a concise, friendly, and actionable answer based on the data.
    Markdown is allowed when it helps readability, but keep it concise and practical."""
        
        tool_config = {
            "tools": [
                {
                    "toolSpec": {
                        "name": "get_spending_summary",
                        "description": "Fetch the user's spending summary (total and by category). If no month is provided, returns all-time summary.",
                        "inputSchema": {
                            "json": {
                                "type": "object",
                                "properties": {
                                    "month": {
                                        "type": "string",
                                        "description": "The month in YYYY-MM format. Leave empty for all-time summary."
                                    }
                                }
                            }
                        }
                    }
                },
                {
                    "toolSpec": {
                        "name": "get_transactions",
                        "description": "Fetch a list of specific transactions. Use this if the user asks for detailed line-items.",
                        "inputSchema": {
                            "json": {
                                "type": "object",
                                "properties": {
                                    "month": {
                                        "type": "string",
                                        "description": "The month in YYYY-MM format."
                                    },
                                    "category": {
                                        "type": "string",
                                        "description": "Filter by category (e.g. Food, Transport, Utilities)."
                                    }
                                }
                            }
                        }
                    }
                }
            ]
        }

        messages = []
        if history:
            for msg in history[-10:]:
                role = msg.get("role")
                content = msg.get("content")
                if role in ("user", "assistant") and content:
                    messages.append({
                        "role": role,
                        "content": [{"text": str(content)}]
                    })

        messages.append({
            "role": "user",
            "content": [{"text": message}]
        })
        
        max_loops = 3
        loops = 0
        while loops < max_loops:
            loops += 1
            resp = self.runtime.converse(
                modelId=self.model_id,
                messages=messages,
                system=[{"text": system_prompt}],
                toolConfig=tool_config,
                inferenceConfig={"maxTokens": 2000, "temperature": 0.7},
            )
            
            stop_reason = resp["stopReason"]
            output_message = resp["output"]["message"]
            messages.append(output_message)
            
            if stop_reason == "tool_use":
                tool_results = []
                for content_block in output_message.get("content", []):
                    if "toolUse" in content_block:
                        tool_use = content_block["toolUse"]
                        tool_name = tool_use["name"]
                        tool_input = tool_use["input"]
                        tool_id = tool_use["toolUseId"]
                        
                        try:
                            if tool_name == "get_spending_summary":
                                month = tool_input.get("month")
                                data = userstore.summary(user_id, month=month)
                            elif tool_name == "get_transactions":
                                month = tool_input.get("month")
                                category = tool_input.get("category")
                                data = userstore.list_transactions(user_id, month=month, category=category)
                            else:
                                data = {"error": f"Unknown tool: {tool_name}"}
                        except Exception as e:
                            data = {"error": str(e)}
                            
                        tool_results.append({
                            "toolResult": {
                                "toolUseId": tool_id,
                                "content": [{"json": data}]
                            }
                        })
                
                messages.append({"role": "user", "content": tool_results})
            else:
                for content_block in output_message.get("content", []):
                    if "text" in content_block:
                        return content_block["text"]
                return "No response generated."
                
        return "Sorry, I had to stop thinking to save time. Please ask again!"


class HybridAI:
    """Bedrock-first AI with LocalAI fallback for offline/dev runs."""

    def __init__(self, region: str, model_id: str):
        self.primary = BedrockAI(region=region, model_id=model_id)
        self.fallback = LocalAI()

    def categorize(self, description: str, amount: float, date: str) -> dict:
        try:
            local_res = self.fallback.categorize(description, amount, date)
            if local_res.get("category") != "Other":
                return local_res
        except Exception:
            pass

        try:
            return self.primary.categorize(description, amount, date)
        except Exception as e:
            logger.error(f"Primary AI failed: {e}. Falling back.")
            return {"category": "Other", "confidence": "low", "engine": "fallback"}

    def chat(self, user_id: str, message: str, userstore, history: list[dict] = None) -> str:
        try:
            return self.primary.chat(user_id, message, userstore, history=history)
        except Exception as e:
            logger.exception(f"Primary AI chat failed: {e}")
            return self.fallback.chat(user_id, message, userstore, history=history)

    def extract_transactions_from_text(self, text: str) -> list:
        try:
            return self.primary.extract_transactions_from_text(text)
        except Exception as e:
            logger.exception(f"Primary AI extract_transactions_from_text failed: {e}")
            return self.fallback.extract_transactions_from_text(text)


class LocalAI:
    """Rule-based categorizer. Keyword matching only. Use for development."""

    # Order matters: first match wins. Subscriptions BEFORE Entertainment so
    # "Netflix monthly subscription" → Subscriptions (subscription keyword fires).
    KEYWORDS = {
        "Income": ["salary", "deposit credit", "payroll", "incoming transfer"],
        "Transfer": ["transfer to", "transfer from", "moved to savings"],
        "Subscriptions": ["subscription", "netflix", "spotify", "openai", "chatgpt", "anthropic",
                          "claude", "github", "icloud", "google one"],
        "Food": ["restaurant", "cafe", "coffee", "starbucks", "highlands", "phở", "pho", "food",
                 "grab food", "shopee food", "lunch", "dinner", "bakery"],
        "Transport": ["grab", "uber", " be ", "xanh sm", "taxi", "metro", "bus", "petrol", "shell",
                      "vinfast", "fuel"],
        "Shopping": ["shopee", "lazada", "tiki", "amazon", "store", "mall", "vincom", "shop"],
        "Utilities": ["electric", "evn", "water", "internet", "viettel", "vnpt", "fpt", "utility"],
        "Entertainment": ["cinema", "cgv", "lotte cinema", "concert", "game"],
        "Health": ["pharmacy", "hospital", "clinic", "guardian", "long chau", "medlatec"],
    }

    def categorize(self, description: str, amount: float, date: str) -> dict:
        desc_lower = description.lower()
        for category, keywords in self.KEYWORDS.items():
            for kw in keywords:
                if kw in desc_lower:
                    # Đã có trong từ khoá thì chắc chắn đúng, confidence = high
                    return {"category": category, "confidence": "high", "engine": "local"}
        return {
            "category": "Other",
            "confidence": "low",
            "engine": "local"
        }

    def extract_transactions_from_text(self, text: str) -> list:
        # Fallback LocalAI cannot extract transactions from raw text reliably
        return []

    def chat(self, user_id: str, message: str, userstore, history: list[dict] = None) -> str:
        msg = message.lower()
        import re

        # Handle the /coach prompt which expects a JSON object with insights and suggested_caps
        if "financial data" in msg or "spending summary" in msg or msg.startswith("analyze"):
            return """{
              "insights": [
                {"title": "Quản lý Tốt", "description": "Bạn đang quản lý chi tiêu rất hiệu quả ở chế độ Local AI.", "type": "positive", "actionable_steps": ["Hãy tiếp tục duy trì thói quen ghi chép chi tiêu."]},
                {"title": "Cảnh báo Nhỏ", "description": "Lưu ý một số danh mục chi tiêu có thể đang tăng lên.", "type": "warning", "actionable_steps": ["Xem lại danh mục Food nếu vượt quá ngân sách."]},
                {"title": "Mẹo Tiết kiệm", "description": "Thử thiết lập tính năng Cảnh báo (Caps & Alerts) để ngân sách không bao giờ bị vượt ngưỡng.", "type": "neutral", "actionable_steps": ["Vào phần Caps & Alerts để thiết lập hạn mức."]}
              ],
              "suggested_caps": [
                {"category": "Food", "suggested_cap": 2000000, "reason": "Dựa trên chi tiêu Food tháng trước, đặt hạn mức 2M sẽ giúp bạn tiết kiệm."}
              ]
            }"""

        def _previous_month() -> str:
            today = datetime.date.today().replace(day=1)
            last_day_previous_month = today - datetime.timedelta(days=1)
            return last_day_previous_month.strftime("%Y-%m")

        def _current_month() -> str:
            return datetime.date.today().strftime("%Y-%m")

        if any(kw in msg for kw in ("tháng trước", "last month", "previous month")):
            month = _previous_month()
        elif any(kw in msg for kw in ("tháng này", "this month", "current month")):
            month = _current_month()
        else:
            month = None

        if month == _previous_month():
            period_text = "tháng trước"
        elif month == _current_month():
            period_text = "tháng này"
        else:
            period_text = "toàn bộ dữ liệu"

        expense_keywords = (
            "spending",
            "summary",
            "tổng",
            "chi tiêu",
            "thống kê",
            "chi bao nhiêu",
            "ăn uống",
            "ăn uong",
            "food",
            "spent",
        )
        income_keywords = (
            "income",
            "thu nhập",
            "doanh thu",
            "lương",
            "salary",
            "nhập",
        )

        def _extract_category() -> str | None:
            category_map = [
                ("Food", ("ăn uống", "an uong", "food", "ăn", "uong", "thực phẩm")),
                ("Transport", ("di chuyển", "transport", "xe", "grab", "taxi", "bus", "metro")),
                ("Shopping", ("mua sắm", "shopping", "shop", "shopee", "lazada", "tiki")),
                ("Utilities", ("hóa đơn", "utilities", "điện", "nước", "internet", "evn", "fpt", "vnpt")),
                ("Entertainment", ("giải trí", "entertainment", "movie", "cinema", "game", "concert")),
                ("Health", ("sức khỏe", "health", "bệnh viện", "pharmacy", "clinic", "thuốc")),
                ("Subscriptions", ("subscription", "gói", "đăng ký", "netflix", "spotify", "chatgpt")),
            ]
            for category, keywords in category_map:
                if any(keyword in msg for keyword in keywords):
                    return category
            return None

        if any(keyword in msg for keyword in income_keywords):
            summary = userstore.summary(user_id, month=month)
            if not summary:
                return "Bạn chưa có giao dịch nào được lưu trữ. Hãy upload file CSV trước nhé!"

            income_total = sum(v['total'] for v in summary.values() if v['total'] > 0)
            if income_total <= 0:
                return "Mình chưa thấy khoản thu nhập nào trong dữ liệu hiện tại."

            formatted_income = f"{income_total:,.0f}".replace(",", ".")
            return f"Thu nhập của bạn trong {period_text} là {formatted_income}đ."
            
        if any(keyword in msg for keyword in expense_keywords):
            summary = userstore.summary(user_id, month=month)
            if not summary:
                return "Bạn chưa có giao dịch nào được lưu trữ. Hãy upload file CSV trước nhé!"

            target_category = _extract_category()
            if target_category:
                category_total = float(summary.get(target_category, {}).get("total", 0.0))
                if category_total < 0:
                    all_txns = userstore.list_transactions(user_id, month=month)
                    txns = [t for t in all_txns if t.get("category", "").lower() == target_category.lower()]
                    txn_lines = []
                    for t in txns:
                        amt = float(t.get("amount", 0))
                        formatted_amt = f"{abs(amt):,.0f}".replace(",", ".")
                        txn_lines.append(f"- **{t.get('date')}**: {formatted_amt}đ - {t.get('description')}")
                    
                    lines_str = "\n".join(txn_lines)
                    formatted_category_total = f"{-category_total:,.0f}".replace(",", ".")
                    return (
                        f"Dựa trên **{period_text}**, chi tiêu cho **{target_category.lower()}** của bạn là **{formatted_category_total}đ**.\n\n"
                        f"Chi tiết các giao dịch:\n{lines_str}"
                    )
                return f"Dựa trên **{period_text}**, mình chưa thấy khoản chi tiêu nào trong danh mục **{target_category.lower()}**."
            
            expenses = {k: v['total'] for k, v in summary.items() if v['total'] < 0}
            if not expenses:
                return "Bạn chưa có khoản chi tiêu nào. Quản lý tài chính rất tốt!"
                
            top_cat = min(expenses, key=expenses.get)
            total_expense = sum(expenses.values())

            formatted_total_expense = f"{-total_expense:,.0f}".replace(",", ".")
            formatted_top_cat = f"{-expenses[top_cat]:,.0f}".replace(",", ".")
            period_text_expense = "dữ liệu hiện tại" if period_text == "toàn bộ dữ liệu" else period_text
            return f"Dựa trên **{period_text_expense}**, tổng chi tiêu của bạn là **{formatted_total_expense}đ**. Bạn đang tiêu tốn nhiều tiền nhất vào danh mục **{top_cat}** với **{formatted_top_cat}đ**. Bạn có muốn mình phân tích chi tiết hơn không?"
            
        elif re.search(r"\b(hi|hello|chào|xin chào)\b", msg):
            return "Xin chào! Mình là BudgetBot AI 🤖. Mình có thể giúp bạn xem thống kê chi tiêu nhanh chóng. Bạn muốn hỏi gì nào?"
            
        else:
            return f"**LocalAI** chỉ hỗ trợ một số câu lệnh cơ bản. Bạn vừa hỏi: '{message}'. Để trò chuyện phức tạp hơn, tài khoản AWS của bạn cần được mở giới hạn (Quota) trên Bedrock."
