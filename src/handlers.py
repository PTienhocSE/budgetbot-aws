"""Endpoint business logic for BudgetBot."""
import csv
import io
from typing import Optional


def _parse_csv(data: bytes) -> list:
    """Expect CSV columns: date, description, amount. Header row optional."""
    text = data.decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return []
    # Detect header
    header = [c.lower().strip() for c in rows[0]]
    if "date" in header and "amount" in header:
        idx = {col: i for i, col in enumerate(header)}
        data_rows = rows[1:]
    else:
        idx = {"date": 0, "description": 1, "amount": 2}
        data_rows = rows
    parsed = []
    for r in data_rows:
        if len(r) < 3 or not r[idx.get("date", 0)].strip():
            continue
        try:
            parsed.append({
                "date": r[idx.get("date", 0)].strip(),
                "description": r[idx.get("description", 1)].strip(),
                "amount": float(r[idx.get("amount", 2)].strip().replace(",", "")),
            })
        except (ValueError, IndexError):
            continue
    return parsed


def handle_upload(
    user_id: str,
    filename: str,
    data: bytes,
    ai_client,
    storage,
    userstore,
) -> dict:
    """Parse CSV or PDF → extract transactions via AI (for PDF) or row-by-row (for CSV) → persist to userstore."""
    key = f"{user_id}/{filename}"
    location = storage.put(key, data)
    
    inserted = 0
    samples = []
    needs_review = []
    parsed_count = 0
    
    if filename.lower().endswith((".pdf", ".png", ".jpg", ".jpeg")):
        import pypdf
        import boto3
        
        text = ""
        try:
            reader = pypdf.PdfReader(io.BytesIO(data))
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        except Exception:
            pass
            
        # Fallback to Textract if scanned PDF
        if len(text.strip()) < 50:
            try:
                textract = boto3.client("textract", region_name="us-east-1")
                resp = textract.detect_document_text(Document={"Bytes": data})
                text = ""
                for block in resp.get("Blocks", []):
                    if block["BlockType"] == "LINE":
                        text += block["Text"] + "\n"
            except Exception as e:
                return {
                    "filename": filename,
                    "stored_at": location,
                    "error": f"Textract failed: {e}"
                }
                
        # Use AI to extract transactions
        txns = ai_client.extract_transactions_from_text(text)
        parsed_count = len(txns)
        for txn in txns:
            if txn.get("category", "").lower() == "income":
                txn["amount"] = abs(txn["amount"])
            else:
                txn["amount"] = -abs(txn["amount"])
                
            if txn.get("confidence") == "high":
                userstore.add_transaction(user_id, txn)
                inserted += 1
                if len(samples) < 5:
                    samples.append(txn)
            else:
                needs_review.append(txn)
    else:
        rows = _parse_csv(data)
        parsed_count = len(rows)
        for row in rows:
            cat_result = ai_client.categorize(
                description=row["description"], amount=row["amount"], date=row["date"]
            )
            txn = {
                "date": row["date"],
                "description": row["description"],
                "amount": row["amount"],
                "category": cat_result["category"],
                "confidence": cat_result["confidence"],
                "engine": cat_result.get("engine", "unknown")
            }
            if txn["category"].lower() == "income":
                txn["amount"] = abs(txn["amount"])
            else:
                txn["amount"] = -abs(txn["amount"])
                
            if txn.get("confidence") == "high":
                userstore.add_transaction(user_id, txn)
                inserted += 1
                if len(samples) < 5:
                    samples.append(txn)
            else:
                needs_review.append(txn)

    return {
        "filename": filename,
        "stored_at": location,
        "rows_parsed": parsed_count,
        "rows_inserted": inserted,
        "sample_categorized": samples,
        "needs_review": needs_review,
    }


def handle_summary(user_id: str, month: Optional[str], userstore) -> dict:
    summary = userstore.summary(user_id, month=month)
    total = sum(v["total"] for v in summary.values())
    sorted_cats = sorted(summary.items(), key=lambda kv: -abs(kv[1]["total"]))
    return {
        "user_id": user_id,
        "month": month,
        "total_spend": total,
        "by_category": dict(sorted_cats),
        "top_3_drivers": [
            {"category": cat, "total": v["total"], "count": v["count"]}
            for cat, v in sorted_cats[:3]
        ],
    }


def handle_list_transactions(user_id: str, month: Optional[str], userstore) -> dict:
    return {"user_id": user_id, "month": month, "transactions": userstore.list_transactions(user_id, month=month)}


def handle_chat(user_id: str, message: str, ai_client, userstore) -> dict:
    # Pass userstore to the AI client so it can autonomously call tools to fetch data
    reply = ai_client.chat(user_id, message, userstore)
    
    return {
        "reply": reply
    }

def _parse_chat_txn(message: str) -> dict:
    """
    Very lightweight natural‑language parser for a transaction sentence.
    Returns a dict with keys: date (YYYY‑MM‑DD), description, amount (float).
    If parsing fails, returns an empty dict.
    """
    import re
    import datetime
    from dateutil import parser as date_parser

    # Extract amount – supports $ / USD / plain number
    amount_match = re.search(r"(?i)(?:\$|usd)?\s*([\d,]+(?:\.\d{1,2})?)", message)
    amount = float(amount_match.group(1).replace(",", "")) if amount_match else None

    # Extract a date – try to find a date string, otherwise use today
    try:
        date_match = re.search(r"\b(on\s+)?(\d{4}[-/]\d{2}[-/]\d{2}|\w+\s+\d{1,2}(?:st|nd|rd|th)?,?\s*\d{4})\b", message, re.I)
        if date_match:
            date_str = date_match.group(2)
            date_obj = date_parser.parse(date_str, fuzzy=True)
            date_iso = date_obj.date().isoformat()
        else:
            date_iso = datetime.date.today().isoformat()
    except Exception:
        date_iso = datetime.date.today().isoformat()

    # Description – remove amount and date substrings
    cleaned = re.sub(r"(?i)(?:\$|usd)?\s*[\d,]+(?:\.\d{1,2})?", "", message)
    cleaned = re.sub(r"\b(on\s+)?(\d{4}[-/]\d{2}[-/]\d{2}|\w+\s+\d{1,2}(?:st|nd|rd|th)?,?\s*\d{4})\b", "", cleaned, flags=re.I)
    description = cleaned.strip().strip(".")

    if amount is None or date_iso is None or not description:
        return {}
    return {"date": date_iso, "description": description, "amount": amount}

def handle_chat_transaction(user_id: str, message: str, ai_client, userstore) -> dict:
    """
    Parse a free‑form spend message, categorize via AI, persist to DynamoDB,
    and return a friendly confirmation.
    """
    txn = _parse_chat_txn(message)
    if not txn:
        return {
            "status": "error",
            "detail": "Could not parse transaction. Please provide amount, description and date (e.g. 'I spent $12 on coffee yesterday')."
        }

    # Ask AI to categorize
    cat_result = ai_client.categorize(
        description=txn["description"],
        amount=txn["amount"],
        date=txn["date"],
    )
    txn["category"] = cat_result.get("category", "uncategorized")
    txn["confidence"] = cat_result.get("confidence", 0.0)
    txn["engine"] = cat_result.get("engine", "unknown")

    # Convert spending amount to negative (outflow), except for Income
    if txn["category"].lower() == "income":
        txn["amount"] = abs(txn["amount"])
        sign = "+"
    else:
        txn["amount"] = -abs(txn["amount"])
        sign = "-"

    # Persist
    userstore.add_transaction(user_id, txn)

    formatted_amount = f"{abs(txn['amount']):,.0f}".replace(",", ".")
    return {
        "status": "saved",
        "transaction": txn,
        "message": f"Saved {sign}{formatted_amount}đ on {txn['date']} as {txn['category']} (confidence {txn['confidence']})."
    }


def handle_coach(user_id: str, ai_client, userstore) -> dict:
    """Generate budget insights based on the user's spending data."""
    from datetime import datetime, timezone
    import json
    
    now = datetime.now(timezone.utc)
    current_month_str = now.strftime("%Y-%m")
    if now.month == 1:
        prev_month_str = f"{now.year - 1}-12"
    else:
        prev_month_str = f"{now.year}-{now.month - 1:02d}"
        
    current_txns = userstore.list_transactions(user_id, month=current_month_str)
    prev_txns = userstore.list_transactions(user_id, month=prev_month_str)
    
    # Calculate category spending distribution in Python for chartData
    curr_totals = {}
    prev_totals = {}
    
    for txn in current_txns:
        amt = float(txn.get("amount", 0))
        if amt < 0:
            cat = txn.get("category", "Other")
            curr_totals[cat] = curr_totals.get(cat, 0) + abs(amt)
            
    for txn in prev_txns:
        amt = float(txn.get("amount", 0))
        if amt < 0:
            cat = txn.get("category", "Other")
            prev_totals[cat] = prev_totals.get(cat, 0) + abs(amt)
            
    chartData = [{"name": k, "value": v} for k, v in curr_totals.items()]
    chartData = sorted(chartData, key=lambda x: x["value"], reverse=True)
    
    summary_text = f"Previous Month ({prev_month_str}) Spending: {prev_totals}. Current Month ({current_month_str}) Spending: {curr_totals}."
    
    prompt = f"""Analyze the user's financial data and provide financial insights and budget cap suggestions. 
Data Summary: {summary_text}

Format the output STRICTLY as a JSON object. Do not include markdown code block wrappers (like ```json), just the raw JSON.
The JSON object must have:
- "insights": An array of 3-5 insight objects. Each insight has: "title" (string), "description" (string), "type" ("positive", "warning", or "neutral"), and "actionable_steps" (array of strings).
- "suggested_caps": An array of budget cap suggestions. Each suggestion has: "category" (string), "suggested_cap" (number, positive integer), and "reason" (string). Only suggest caps for categories where the user is overspending or spending significantly.

Example:
{{
  "insights": [
    {{
      "title": "High Food Spending",
      "description": "You spent heavily on Food this month.",
      "type": "warning",
      "actionable_steps": ["Cook at home 3 times this week"]
    }}
  ],
  "suggested_caps": [
    {{
      "category": "Food",
      "suggested_cap": 2000000,
      "reason": "Based on last month's spending of 2.5M, a 2M cap will help you save."
    }}
  ]
}}
"""
    
    reply = ai_client.chat(user_id, prompt, userstore)
    
    try:
        # Some LLMs wrap JSON in markdown blocks
        if "```json" in reply:
            reply = reply.split("```json")[1].split("```")[0].strip()
        elif "```" in reply:
            reply = reply.split("```")[1].split("```")[0].strip()
            
        start_idx = reply.find('{')
        end_idx = reply.rfind('}')
        if start_idx != -1 and end_idx != -1:
            reply = reply[start_idx:end_idx+1]
            
        result = json.loads(reply)
        insights = result.get("insights", [])
        suggested_caps = result.get("suggested_caps", [])
    except Exception as e:
        # Fallback if parsing fails
        insights = [
            {
                "title": "AI Insight Error", 
                "description": f"Failed to parse AI output. Raw text: {reply}. Error: {str(e)}", 
                "type": "neutral",
                "actionable_steps": ["Check the backend logs."]
            }
        ]
        suggested_caps = []
        
    return {
        "insights": insights,
        "suggested_caps": suggested_caps,
        "chartData": chartData
    }

