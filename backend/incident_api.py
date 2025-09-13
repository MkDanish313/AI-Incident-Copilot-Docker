from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3
import os
import requests
from typing import List, Dict
from datetime import datetime
import yaml

app = FastAPI()

DB_PATH = os.getenv("DB_PATH", "/data/db/incident.db")
CATEGORIES_FILE = os.getenv("CATEGORIES_FILE", "/app/incident_categories.yml")
OLLAMA_API = os.getenv("OLLAMA_API", "http://ollama:11434")

class IncidentRequest(BaseModel):
    category: str
    agent: str
    incident: str

# ---------------------------
# DB Utility
# ---------------------------
def save_incident(category, agent, incident, response):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS incidents (id INTEGER PRIMARY KEY, timestamp TEXT, category TEXT, agent TEXT, incident TEXT, response TEXT)"
    )
    cursor.execute(
        "INSERT INTO incidents (timestamp, category, agent, incident, response) VALUES (?, ?, ?, ?, ?)",
        (datetime.utcnow().isoformat(), category, agent, incident, response),
    )
    conn.commit()
    conn.close()

def get_incidents(limit: int = 20):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS incidents (id INTEGER PRIMARY KEY, timestamp TEXT, category TEXT, agent TEXT, incident TEXT, response TEXT)"
    )
    cursor.execute("SELECT timestamp, category, agent, incident, response FROM incidents ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()

    return [
        {"timestamp": r[0], "category": r[1], "agent": r[2], "incident": r[3], "response": r[4]}
        for r in rows
    ]

# ---------------------------
# Category Utility
# ---------------------------
def load_category_prompt(category: str) -> str:
    try:
        with open(CATEGORIES_FILE, "r") as f:
            data = yaml.safe_load(f)
        return data.get("categories", {}).get(category, {}).get("prompt", "")
    except Exception:
        return ""

@app.get("/categories")
def get_categories():
    try:
        with open(CATEGORIES_FILE, "r") as f:
            data = yaml.safe_load(f)
        return {"categories": list(data.get("categories", {}).keys())}
    except Exception:
        return {"categories": []}

# ---------------------------
# Agent Utility
# ---------------------------
def get_agent_connect_command(agent: str) -> str:
    mapping = {
        "linux_agent": "curl -sSL https://<YOUR_API>/agents/linux_agent/install.sh | bash",
        "aws_agent": "curl -sSL https://<YOUR_API>/agents/aws_agent/install.sh | bash",
        "db_agent": "curl -sSL https://<YOUR_API>/agents/db_agent/install.sh | bash",
    }
    return mapping.get(agent.lower(), "No agent install script available. See docs.")

@app.get("/agent/{agent}/connect")
def agent_connect(agent: str):
    return {"agent": agent, "command": get_agent_connect_command(agent)}

# ---------------------------
# Incident API
# ---------------------------
@app.post("/incident")
def handle_incident(req: IncidentRequest):
    category_context = load_category_prompt(req.category)

    prompt = f"""
You are an AI Incident Copilot.
Category: {req.category}
Agent: {req.agent}
Incident: {req.incident}

Additional context:
{category_context}

Your task:
1. Give top 3 **investigation steps**.
2. Provide **exact CLI commands** that should be run.
3. Suggest **fixes or recommended actions** (ready to apply).
4. Be concise and practical (use bullet points).
"""

    try:
        resp = requests.post(
            f"{OLLAMA_API}/api/generate",
            json={"model": "llama2:7b", "prompt": prompt, "stream": False},
            timeout=300,
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Ollama error: {resp.text}")

        response_text = resp.json().get("response", "").strip()

        save_incident(req.category, req.agent, req.incident, response_text)
        return {"response": response_text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ollama error: {str(e)}")

# ---------------------------
# History API
# ---------------------------
@app.get("/incidents")
def incidents(limit: int = 20) -> List[Dict]:
    return get_incidents(limit)

# ---------------------------
# Healthcheck
# ---------------------------
@app.get("/health")
def health():
    return {"status": "ok", "db": "connected", "model": "llama2:7b"}
