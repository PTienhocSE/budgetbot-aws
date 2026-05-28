"""FastAPI app for BudgetBot. Runtime-agnostic."""
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Header, HTTPException, UploadFile, Depends
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from pydantic import BaseModel

from src.config import config
from src.auth import get_current_user, create_access_token
from src.adapters import factory
from src import handlers


app = FastAPI(title="BudgetBot — W7 Capstone Starter")


# CORS — allow frontend to live on a different origin (CloudFront / Amplify / separate ALB).
# CORS_ORIGINS env var controls this; default '*' is permissive for hackathon.
_allowed = ["*"] if config.cors_origins == "*" else [o.strip() for o in config.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed,
    allow_credentials=False if "*" in _allowed else True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ai_client = factory.make_ai()
storage = factory.make_storage()
userstore = factory.make_userstore()


# =====================================================================
# Pydantic request models
# =====================================================================

class RegisterRequest(BaseModel):
    full_name: str
    username: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class ChatRequest(BaseModel):
    message: str

class TransactionRequest(BaseModel):
    date: str
    description: str
    amount: float
    category: str = "uncategorized"
    confidence: float = 0.0

class TransactionUpdateRequest(BaseModel):
    date: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    category: Optional[str] = None

class TransactionBatchRequest(BaseModel):
    transactions: list[TransactionRequest]


class CapRequest(BaseModel):
    category: str
    amount: float


# =====================================================================
# Auth routes (public — no JWT required)
# =====================================================================

@app.post("/register")
def register(req: RegisterRequest) -> dict:
    """Create a new user account."""
    from src.adapters.userstore_dynamo_user import create_user
    try:
        user = create_user(req.full_name, req.username, req.password)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return user


@app.post("/login")
def login(req: LoginRequest) -> dict:
    """Authenticate and return a JWT token."""
    from src.adapters.userstore_dynamo_user import verify_password
    user = verify_password(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user["PK"]})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user["PK"],
        "username": user["username"],
        "full_name": user["full_name"],
    }


@app.get("/profile")
def profile(user_id: str = Depends(get_current_user)) -> dict:
    """Return the current user's profile."""
    from src.adapters.userstore_dynamo_user import get_user_by_id
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "user_id": user["PK"],
        "username": user["username"],
        "full_name": user["full_name"],
    }


# =====================================================================
# Health check (public)
# =====================================================================

@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "backends": {
            "ai": config.ai_backend,
            "storage": config.storage_backend,
            "userstore": config.userstore_backend,
        },
    }


# =====================================================================
# Protected routes — require JWT
# =====================================================================

@app.post("/upload")
async def upload(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
) -> dict:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    return handlers.handle_upload(
        user_id=user_id,
        filename=file.filename or "statement.csv",
        data=data,
        ai_client=ai_client,
        storage=storage,
        userstore=userstore,
    )


@app.get("/summary")
def summary(
    month: Optional[str] = None,
    user_id: str = Depends(get_current_user),
) -> dict:
    """`month` format: YYYY-MM. Omit for all-time summary."""
    return handlers.handle_summary(user_id, month, userstore)


@app.get("/transactions")
def list_transactions(
    month: Optional[str] = None,
    user_id: str = Depends(get_current_user),
) -> dict:
    return handlers.handle_list_transactions(user_id, month, userstore)


@app.post("/transactions")
def create_transaction(
    req: TransactionRequest,
    user_id: str = Depends(get_current_user),
) -> dict:
    """Manually add a single transaction, auto-categorized by AI."""
    cat_result = ai_client.categorize(req.description, req.amount, req.date)
    
    txn = {
        "date": req.date,
        "description": req.description,
        "amount": req.amount,
        "category": cat_result["category"],
        "confidence": cat_result["confidence"],
    }
    userstore.add_transaction(user_id, txn)
    return {"status": "created", "transaction": txn}


@app.post("/transactions/batch")
def create_transaction_batch(
    req: TransactionBatchRequest,
    user_id: str = Depends(get_current_user),
) -> dict:
    """Manually add multiple transactions at once (e.g. from manual review)."""
    inserted = 0
    for t_req in req.transactions:
        # We don't auto-categorize again here, we trust the client's category
        txn = {
            "date": t_req.date,
            "description": t_req.description,
            "amount": t_req.amount,
            "category": t_req.category,
            "confidence": "high",  # Since it's user-confirmed, confidence is high
        }
        userstore.add_transaction(user_id, txn)
        inserted += 1
    return {"status": "created", "count": inserted}


@app.put("/transactions/{transaction_id}")
def update_transaction(
    transaction_id: str,
    req: TransactionUpdateRequest,
    user_id: str = Depends(get_current_user),
) -> dict:
    """Update an existing transaction."""
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = userstore.update_transaction(user_id, transaction_id, updates)
    return {"status": "updated", "transaction": result}


@app.delete("/transactions/{transaction_id}")
def delete_transaction(
    transaction_id: str,
    user_id: str = Depends(get_current_user),
) -> dict:
    """Delete a transaction."""
    userstore.delete_transaction(user_id, transaction_id)
    return {"status": "deleted", "transaction_id": transaction_id}


@app.post("/chat")
def chat(
    request: ChatRequest,
    user_id: str = Depends(get_current_user),
) -> dict:
    return handlers.handle_chat(user_id, request.message, ai_client, userstore)


@app.post("/chat/transaction")
def chat_transaction(
    request: ChatRequest,
    user_id: str = Depends(get_current_user),
) -> dict:
    """Accept a free-form transaction description and store it."""
    return handlers.handle_chat_transaction(
        user_id,
        request.message,
        ai_client,
        userstore,
    )


@app.get("/coach")
def get_coach_insights(user_id: str = Depends(get_current_user)) -> dict:
    """Get AI generated budget insights for the user."""
    return handlers.handle_coach(user_id, ai_client, userstore)


@app.get("/caps")
def get_user_caps(user_id: str = Depends(get_current_user)) -> dict:
    """Get the user's active budget caps."""
    from src.adapters.userstore_dynamo_user import get_caps
    caps = get_caps(user_id)
    return {"caps": caps}


@app.post("/caps")
def set_user_cap(
    req: CapRequest,
    user_id: str = Depends(get_current_user)
) -> dict:
    """Set or update a budget cap."""
    from src.adapters.userstore_dynamo_user import set_cap
    caps = set_cap(user_id, req.category, req.amount)
    return {"status": "updated", "caps": caps}


@app.delete("/caps/{category}")
def remove_user_cap(
    category: str,
    user_id: str = Depends(get_current_user)
) -> dict:
    """Delete a budget cap."""
    from src.adapters.userstore_dynamo_user import delete_cap
    caps = delete_cap(user_id, category)
    return {"status": "deleted", "caps": caps}


# ---- Static frontend ----
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

if config.serve_frontend:
    @app.get("/")
    def index() -> dict:
        return {"message": "Frontend is hosted on S3. Visit the CloudFront URL."}

# AWS Lambda Handler
handler = Mangum(app)
