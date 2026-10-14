"""Local SQLite audit trail for completed analyses; images stay base64 in one row."""
from __future__ import annotations
import json, os, sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(os.getenv("ANALYSIS_DB_PATH", "analysis_history.sqlite3"))

def _connection():
    con=sqlite3.connect(DB_PATH); con.row_factory=sqlite3.Row
    con.execute("""CREATE TABLE IF NOT EXISTS analyses (
        id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL,
        location TEXT, pipeline TEXT NOT NULL, request_json TEXT NOT NULL,
        result_json TEXT NOT NULL)""")
    return con

def save_analysis(result: dict, request: dict, location: str | None = None) -> int:
    with _connection() as con:
        cursor=con.execute("INSERT INTO analyses(created_at,location,pipeline,request_json,result_json) VALUES(?,?,?,?,?)",
            (datetime.now(timezone.utc).isoformat(),location,result.get("pipeline","unknown"),json.dumps(request),json.dumps(result)))
        return int(cursor.lastrowid)

def list_analyses(limit: int = 50) -> list[dict]:
    with _connection() as con:
        rows=con.execute("SELECT id,created_at,location,pipeline,result_json FROM analyses ORDER BY id DESC LIMIT ?",(min(max(limit,1),200),)).fetchall()
    return [{"id":r["id"],"created_at":r["created_at"],"location":r["location"],"pipeline":r["pipeline"],"percent_changed":json.loads(r["result_json"]).get("percent_changed",0)} for r in rows]

def get_analysis(analysis_id: int) -> dict | None:
    with _connection() as con: row=con.execute("SELECT * FROM analyses WHERE id=?",(analysis_id,)).fetchone()
    if row is None: return None
    return {"id":row["id"],"created_at":row["created_at"],"location":row["location"],"pipeline":row["pipeline"],"request":json.loads(row["request_json"]),"result":json.loads(row["result_json"])}
