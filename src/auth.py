"""JWT authentication utilities for BudgetBot."""
import datetime
import jwt
from fastapi import HTTPException, Depends, Request
from src.config import config


def create_access_token(data: dict) -> str:
    """Create a JWT token with expiration.
    The token payload includes the ``sub`` claim set to the user's ID.
    """
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=config.jwt_exp_minutes)
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, config.jwt_secret, algorithm=config.jwt_algorithm)
    return token


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token. Raises HTTPException on failure."""
    try:
        payload = jwt.decode(token, config.jwt_secret, algorithms=[config.jwt_algorithm])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user(request: Request) -> str:
    """FastAPI dependency that extracts the JWT token from the Authorization header.
    Returns the user_id (sub claim) after validation.
    """
    auth: str | None = request.headers.get("Authorization")
    if not auth or not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = auth.split(" ", 1)[1]
    payload = decode_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token payload missing sub")
    return user_id
