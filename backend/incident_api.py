import os, sqlite3, time, json
from typing import Optional, List, Dict
import yaml
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

OLLAMA_API = os.getenv("OLLAMA_API", "http://localhost:11434")
DB_PATH = os.getenv("DB_PATH", "/data/db/incident.db")
CATEGORIES_FILE = os.getenv("CATEGORIES_FILE", "/app/incident_categories.yml")
MODEL_NAME = os.getenv("MODEL_NAME", "llama2:7b")

app = FastAPI(title="AI Incident Copilot")

# ---------- DB ----------
def ensure_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS incidents (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      ts INTEGER NOT NULL,
      category TEXT,
      incident TEXT,
      response TEXT
    );""")
    conn.commit()
    conn.close()

def insert_incident(category: str, incident: str, response: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO incidents (ts, category, incident, response) VALUES (?,?,?,?)",
                (int(time.time()), category, incident, response))
    conn.commit()
    conn.close()

def list_incidents(limit: int = 50) -> List[Dict]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, ts, category, incident, response FROM incidents ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return [{"id": r[0], "ts": r[1], "category": r[2], "incident": r[3], "response": r[4]} for r in rows]

# ---------- Categories ----------
def load_categories() -> Dict[str, Dict]:
    with open(CATEGORIES_FILE, "r") as f:
        y = yaml.safe_load(f)
    return y.get("categories", {})

CATEGORIES = load_categories()
ensure_db()

# ---------- Models ----------
class IncidentRequest(BaseModel):
    category: str = Field(..., description="e.g., kubernetes_crash")
    incident: str

class AgentReport(BaseModel):
    source: str
    category: str
    incident: str

# ---------- Routes ----------
@app.get("/health")
def health():
    try:
        r = requests.get(f"{OLLAMA_API}/api/tags", timeout=5)
        ok = r.status_code == 200
    except Exception:
        ok = False
    return {"status": "ok" if ok else "degraded", "model": MODEL_NAME, "db": DB_PATH}

@app.get("/categories")
def categories():
    return {"categories": list(CATEGORIES.keys())}

def call_ollama(prompt: str) -> str:
    # use streaming=false by default
    payload = {"model": MODEL_NAME, "prompt": prompt, "stream": False}
    r = requests.post(f"{OLLAMA_API}/api/generate", json=payload, timeout=600)
    if r.status_code != 200:
        raise HTTPException(502, f"Ollama error: {r.text}")
    data = r.json()
    # when stream=false, response contains "response"
    return data.get("response", "").strip()

@app.post("/incident")
def handle_incident(req: IncidentRequest):
    if req.category not in CATEGORIES:
        raise HTTPException(400, f"Unknown category '{req.category}'. Use /categories to list.")
    template = CATEGORIES[req.category]["prompt"]
    prompt = template.format(incident=req.incident)
    ai = call_ollama(prompt)
    insert_incident(req.category, req.incident, ai)
    return {"category": req.category, "incident": req.incident, "response": ai}

@app.get("/incidents")
def get_incidents(limit: int = 50):
    return {"items": list_incidents(limit)}

@app.post("/agent/report")
def agent_report(rep: AgentReport):
    if rep.category not in CATEGORIES:
        raise HTTPException(400, f"Unknown category '{rep.category}'.")
    template = CATEGORIES[rep.category]["prompt"]
    ai = call_ollama(template.format(incident=rep.incident))
    insert_incident(rep.category, rep.incident, ai)
    return {"accepted": True, "response": ai}
