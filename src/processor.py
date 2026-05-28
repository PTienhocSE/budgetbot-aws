"""S3 Event-triggered Processor Lambda for async file processing.

This Lambda is invoked by S3 event notifications when a new file is uploaded.
It handles the heavy processing (PDF parsing, Textract OCR, Bedrock AI categorization)
and writes results to DynamoDB, bypassing the 29s API Gateway timeout limit.
"""
import json
import io
import os
import logging
import traceback

import boto3

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))


def handler(event, context):
    """S3 Event handler - processes uploaded files asynchronously."""
    logger.info("Processor Lambda invoked with event: %s", json.dumps(event, default=str))

    # Initialize AWS clients
    region = os.environ.get("AWS_REGION", "us-east-1")
    table_name = os.environ.get("USERSTORE_TABLE", "")
    bucket_name = os.environ.get("STORAGE_BUCKET", "")
    model_id = os.environ.get("AI_MODEL_ID", "anthropic.claude-haiku-4-5-20251001-v1:0")

    dynamodb = boto3.resource("dynamodb", region_name=region)
    table = dynamodb.Table(table_name)
    s3 = boto3.client("s3", region_name=region)

    import urllib.parse
    for record in event.get("Records", []):
        s3_bucket = record["s3"]["bucket"]["name"]
        s3_key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])

        # Skip non-upload files (e.g., system files)
        if not s3_key or s3_key.startswith("."):
            continue

        # Extract user_id from S3 key pattern: {user_id}/{filename}
        parts = s3_key.split("/", 1)
        if len(parts) < 2:
            logger.warning("Unexpected S3 key format: %s", s3_key)
            continue

        user_id = parts[0]
        filename = parts[1]

        # Find the JOB record for this upload
        job_id = _find_job_id(table, user_id, s3_key)
        if not job_id:
            logger.info("No JOB record found for key %s, skipping (might be a direct S3 upload)", s3_key)
            continue

        try:
            # Update status to PROCESSING (in case it wasn't already)
            _update_job_status(table, user_id, job_id, "PROCESSING")

            # Download file from S3
            logger.info("Downloading file from s3://%s/%s", s3_bucket, s3_key)
            obj = s3.get_object(Bucket=s3_bucket, Key=s3_key)
            data = obj["Body"].read()

            # Process the file
            inserted, samples, needs_review, parsed_count = _process_file(
                user_id, filename, data, table, region, model_id
            )

            # Update JOB record with results
            _update_job_completed(
                table, user_id, job_id,
                rows_parsed=parsed_count,
                rows_inserted=inserted,
                needs_review=needs_review,
                sample_categorized=samples,
            )
            logger.info(
                "Processing complete for %s: %d parsed, %d inserted, %d needs review",
                s3_key, parsed_count, inserted, len(needs_review)
            )

        except Exception as e:
            logger.error("Processing failed for %s: %s\n%s", s3_key, str(e), traceback.format_exc())
            _update_job_status(table, user_id, job_id, "FAILED", error=str(e))

    return {"statusCode": 200, "body": "Processing complete"}


def _find_job_id(table, user_id, s3_key):
    """Find the JOB record that matches this S3 key."""
    resp = table.query(
        KeyConditionExpression="PK = :u AND begins_with(SK, :p)",
        ExpressionAttributeValues={":u": user_id, ":p": "JOB#"},
        ScanIndexForward=False,  # newest first
        Limit=20,
    )
    for item in resp.get("Items", []):
        if item.get("s3_key") == s3_key and item.get("status") in ("PENDING", "PROCESSING"):
            return item["SK"]
    return None


def _update_job_status(table, user_id, job_id, status, error=None):
    """Update the status of a JOB record."""
    from datetime import datetime, timezone
    update_expr = "SET #st = :s, updated_at = :t"
    attr_names = {"#st": "status"}
    attr_values = {":s": status, ":t": datetime.now(timezone.utc).isoformat()}

    if error:
        update_expr += ", error_message = :e"
        attr_values[":e"] = error

    table.update_item(
        Key={"PK": user_id, "SK": job_id},
        UpdateExpression=update_expr,
        ExpressionAttributeNames=attr_names,
        ExpressionAttributeValues=attr_values,
    )


def _update_job_completed(table, user_id, job_id, rows_parsed, rows_inserted, needs_review, sample_categorized):
    """Mark a JOB as COMPLETED with result data."""
    from datetime import datetime, timezone
    from decimal import Decimal

    # Convert floats to Decimal for DynamoDB
    def to_decimal(obj):
        if isinstance(obj, float):
            return Decimal(str(obj))
        if isinstance(obj, dict):
            return {k: to_decimal(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [to_decimal(i) for i in obj]
        return obj

    table.update_item(
        Key={"PK": user_id, "SK": job_id},
        UpdateExpression=(
            "SET #st = :s, completed_at = :t, rows_parsed = :rp, "
            "rows_inserted = :ri, needs_review = :nr, sample_categorized = :sc"
        ),
        ExpressionAttributeNames={"#st": "status"},
        ExpressionAttributeValues={
            ":s": "COMPLETED",
            ":t": datetime.now(timezone.utc).isoformat(),
            ":rp": rows_parsed,
            ":ri": rows_inserted,
            ":nr": to_decimal(needs_review),
            ":sc": to_decimal(sample_categorized),
        },
    )


def _process_file(user_id, filename, data, table, region, model_id):
    """Process an uploaded file: parse CSV or PDF, categorize with AI, store transactions."""
    import csv
    from decimal import Decimal
    from datetime import datetime, timezone
    import uuid

    inserted = 0
    samples = []
    needs_review = []
    parsed_count = 0

    # Initialize AI client
    ai_client = _make_ai_client(region, model_id)

    if filename.lower().endswith((".pdf", ".png", ".jpg", ".jpeg")):
        # PDF / image processing
        text = _extract_text(data, filename, region)
        txns = ai_client.extract_transactions_from_text(text)
        parsed_count = len(txns)

        for txn in txns:
            if txn.get("category", "").lower() == "income":
                txn["amount"] = abs(txn["amount"])
            else:
                txn["amount"] = -abs(txn["amount"])

            if txn.get("confidence") == "high":
                _store_transaction(table, user_id, txn)
                inserted += 1
                if len(samples) < 5:
                    samples.append(txn)
            else:
                needs_review.append(txn)
    else:
        # CSV processing
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
                "engine": cat_result.get("engine", "unknown"),
            }
            if txn["category"].lower() == "income":
                txn["amount"] = abs(txn["amount"])
            else:
                txn["amount"] = -abs(txn["amount"])

            if txn.get("confidence") == "high":
                _store_transaction(table, user_id, txn)
                inserted += 1
                if len(samples) < 5:
                    samples.append(txn)
            else:
                needs_review.append(txn)

    return inserted, samples, needs_review, parsed_count


def _extract_text(data, filename, region):
    """Extract text from PDF or image file."""
    text = ""

    # Try local PDF parsing first
    if filename.lower().endswith(".pdf"):
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(data))
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        except Exception:
            pass

    # Fallback to Textract if scanned PDF or image
    if len(text.strip()) < 50:
        try:
            textract = boto3.client("textract", region_name=region)
            resp = textract.detect_document_text(Document={"Bytes": data})
            text = ""
            for block in resp.get("Blocks", []):
                if block["BlockType"] == "LINE":
                    text += block["Text"] + "\n"
        except Exception as e:
            logger.error("Textract failed: %s", str(e))
            raise

    return text


def _parse_csv(data):
    """Parse CSV file into list of transaction dicts."""
    import csv
    text = data.decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return []

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


def _store_transaction(table, user_id, txn):
    """Store a single transaction in DynamoDB."""
    import uuid
    from decimal import Decimal
    from datetime import datetime, timezone

    sk = f"TXN#{txn['date']}#{uuid.uuid4().hex[:8]}"
    item = {**txn, "amount": Decimal(str(txn["amount"]))} if "amount" in txn else txn
    table.put_item(Item={
        "PK": user_id,
        "SK": sk,
        "created_at": datetime.now(timezone.utc).isoformat(),
        **item,
    })


def _make_ai_client(region, model_id):
    """Create AI client matching the backend's adapter pattern."""
    from src.adapters.ai import HybridAI
    return HybridAI(region=region, model_id=model_id)
