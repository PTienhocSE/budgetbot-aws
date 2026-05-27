"""User store adapter for auth users — DynamoDB in AWS, SQLite for local dev."""
import uuid
import bcrypt
import boto3
from boto3.dynamodb.conditions import Key
from src.config import config


def _use_dynamodb() -> bool:
    return config.userstore_backend == "dynamodb"


def _get_table():
    """Return the DynamoDB Table resource for the users table."""
    if not config.users_table:
        raise ValueError("USERS_TABLE env var not set")
    return boto3.resource("dynamodb", region_name=config.aws_region).Table(config.users_table)


def _get_sqlite_conn():
    import sqlite3
    from pathlib import Path

    db_path = config.userstore_sqlite_path
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            PK TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            caps TEXT DEFAULT '{}'
        )
        """
    )
    conn.commit()
    return conn


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def get_user_by_username(username: str) -> dict | None:
    """Look up a user by username via the GSI. Returns the item dict or None."""
    if _use_dynamodb():
        table = _get_table()
        resp = table.query(
            IndexName="username-index",
            KeyConditionExpression=Key("username").eq(username),
        )
        items = resp.get("Items", [])
        return items[0] if items else None

    conn = _get_sqlite_conn()
    cur = conn.execute(
        "SELECT PK, username, full_name, password_hash, caps FROM users WHERE username = ?",
        (username,),
    )
    row = cur.fetchone()
    if not row:
        return None
    return {
        "PK": row[0],
        "username": row[1],
        "full_name": row[2],
        "password_hash": row[3],
        "caps": row[4],
    }


def get_user_by_id(user_id: str) -> dict | None:
    """Look up a user by PK (user_id). Returns the item dict or None."""
    if _use_dynamodb():
        table = _get_table()
        resp = table.get_item(Key={"PK": user_id})
        return resp.get("Item")

    conn = _get_sqlite_conn()
    cur = conn.execute(
        "SELECT PK, username, full_name, password_hash, caps FROM users WHERE PK = ?",
        (user_id,),
    )
    row = cur.fetchone()
    if not row:
        return None
    return {
        "PK": row[0],
        "username": row[1],
        "full_name": row[2],
        "password_hash": row[3],
        "caps": row[4],
    }


def create_user(full_name: str, username: str, password: str) -> dict:
    """Register a new user. Raises ValueError if username is taken."""
    if get_user_by_username(username):
        raise ValueError("Username already taken")
    user_id = str(uuid.uuid4())

    if _use_dynamodb():
        table = _get_table()
        item = {
            "PK": user_id,
            "username": username,
            "full_name": full_name,
            "password_hash": _hash_password(password),
        }
        table.put_item(Item=item)
    else:
        conn = _get_sqlite_conn()
        conn.execute(
            "INSERT INTO users (PK, username, full_name, password_hash) VALUES (?, ?, ?, ?)",
            (user_id, username, full_name, _hash_password(password)),
        )
        conn.commit()

    return {"user_id": user_id, "username": username, "full_name": full_name}


def verify_password(username: str, password: str) -> dict | None:
    """Authenticate user by username + password. Returns the user dict or None."""
    user = get_user_by_username(username)
    if not user:
        return None
    if _check_password(password, user.get("password_hash", "")):
        return user
    return None


def get_caps(user_id: str) -> dict:
    """Get the active budget caps for the user."""
    user = get_user_by_id(user_id)
    if not user:
        return {}
    return user.get("caps", {})


def set_cap(user_id: str, category: str, amount: float) -> dict:
    """Set or update a budget cap for a specific category."""
    table = _get_table()
    from decimal import Decimal
    
    # We use an UpdateExpression to add/update the specific category in the caps Map.
    # If the caps attribute doesn't exist yet, we can't directly set a nested attribute,
    # so we must handle that case.
    
    # Fetch user first to see if 'caps' exists
    user = get_user_by_id(user_id)
    if user is None:
        raise ValueError("User not found")
        
    caps = user.get("caps", {})
    caps[category] = Decimal(str(amount))
    
    resp = table.update_item(
        Key={"PK": user_id},
        UpdateExpression="SET caps = :c",
        ExpressionAttributeValues={":c": caps},
        ReturnValues="ALL_NEW"
    )
    
    new_caps = resp.get("Attributes", {}).get("caps", {})
    return {k: float(v) for k, v in new_caps.items()}


def delete_cap(user_id: str, category: str) -> dict:
    """Delete a budget cap for a specific category."""
    table = _get_table()
    user = get_user_by_id(user_id)
    if user is None:
        raise ValueError("User not found")
        
    caps = user.get("caps", {})
    if category in caps:
        del caps[category]
        
    resp = table.update_item(
        Key={"PK": user_id},
        UpdateExpression="SET caps = :c",
        ExpressionAttributeValues={":c": caps},
        ReturnValues="ALL_NEW"
    )
    
    new_caps = resp.get("Attributes", {}).get("caps", {})
    return {k: float(v) for k, v in new_caps.items()}
