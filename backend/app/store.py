import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from .config import DATA_PATH, MONGODB_URI, MONGODB_DATABASE

_lock = Lock()
_client = None
_collection = None

def _mongo_collection():
    global _client, _collection
    if not MONGODB_URI:
        return None
    if _collection is None:
        _client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=1500)
        _client.admin.command("ping")
        _collection = _client[MONGODB_DATABASE]["transactions"]
        _collection.create_index("transaction_id", unique=True)
        _collection.create_index("created_at")
        _collection.create_index("risk_level")
    return _collection

def insert(record: dict) -> dict:
    item = dict(record)
    item["created_at"] = item["created_at"].isoformat() if isinstance(item.get("created_at"), datetime) else item.get("created_at")
    try:
        col = _mongo_collection()
        if col is not None:
            col.insert_one(item.copy())
            return item
    except PyMongoError:
        # Keep local demo usable if the remote database is temporarily unavailable.
        pass
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _lock, DATA_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(item) + "\n")
    return item

def all_records(limit: int = 200) -> list[dict]:
    try:
        col = _mongo_collection()
        if col is not None:
            docs = list(col.find({}, {"_id": 0}).sort("created_at", -1).limit(limit))
            for d in docs:
                if isinstance(d.get("created_at"), datetime):
                    d["created_at"] = d["created_at"].isoformat()
            return docs
    except PyMongoError:
        pass
    if not DATA_PATH.exists():
        return []
    with _lock, DATA_PATH.open(encoding="utf-8") as f:
        lines = f.readlines()[-limit:]
    records = []
    for line in reversed(lines):
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records

def update_label(transaction_id: str, label: str) -> bool:
    try:
        col = _mongo_collection()
        if col is not None:
            result = col.update_one({"transaction_id": transaction_id}, {"$set": {"analyst_label": label}})
            return result.modified_count > 0 or col.count_documents({"transaction_id": transaction_id}) > 0
    except PyMongoError:
        pass
    records = all_records(limit=100000)
    changed = False
    for record in records:
        if record.get("transaction_id") == transaction_id:
            record["analyst_label"] = label
            changed = True
    if changed:
        DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _lock, DATA_PATH.open("w", encoding="utf-8") as f:
            for record in reversed(records):
                f.write(json.dumps(record) + "\n")
    return changed
