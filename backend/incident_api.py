from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import sqlite3
import os
import requests
from typing import List, Dict
from datetime import datetime
import yaml
import json

app = FastAPI()

DB_PATH = os.getenv("DB_PATH", "/data/db/incident.db")
CATEGORIES_FILE = os.getenv("CATEGORIES_FILE", "/app/incident_categories.yml")
OLLAMA_API = os.getenv("OLLAMA_API", "http://ollama:11434")
PUBLIC_API_URL = os.getenv("PUBLIC_API_URL", "http://localhost:8000")

# ---------------------------
# Mount agents/
# ---------------------------
if os.path.isdir("agents"):
    app.mount("/agents", StaticFiles(directory="agents"), name="agents")

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
        "CREATE TABLE IF NOT EXISTS incidents "
        "(id INTEGER PRIMARY KEY, timestamp TEXT, category TEXT, agent TEXT, incident TEXT, response TEXT)"
    )
    cursor.execute(
        "INSERT INTO incidents (timestamp, category, agent, incident, response) VALUES (?, ?, ?, ?, ?)",
        (datetime.utcnow().isoformat(), category, agent, incident, response),
    )
    conn.commit()
    conn.close()

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
    base_url = PUBLIC_API_URL.rstrip("/")
    mapping = {
        "linux_agent": f"curl -sSL {base_url}/agents/linux_agent/install.sh | bash",
        "aws_agent": f"curl -sSL {base_url}/agents/aws_agent/install.sh | bash",
        "db_agent": f"curl -sSL {base_url}/agents/db_agent/install.sh | bash",
    }
    return mapping.get(agent.lower(), "No agent install script available. See docs.")

@app.get("/agent/{agent}/connect")
def agent_connect(agent: str):
    return {"agent": agent, "command": get_agent_connect_command(agent)}

# ---------------------------
# Incident API (Strict JSON Response with fallback)
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
Return ONLY valid JSON with exactly these fields:
- investigation (list of top 3 steps)
- commands (list of CLI commands)
- fixes (list of recommended fixes)

Example format:
{{
  "investigation": ["step1", "step2"],
  "commands": ["command1", "command2"],
  "fixes": ["fix1", "fix2"]
}}

Do not add extra text outside JSON.
If unsure, still return generic investigation, commands, and fixes.
"""

    def stream_response():
        collected = ""
        try:
            with requests.post(
                f"{OLLAMA_API}/api/generate",
                json={"model": "ai/mistral:7B-Q4_0", "prompt": prompt, "stream": True},
                stream=True,
                timeout=600,
            ) as r:
                for line in r.iter_lines():
                    if line:
                        try:
                            data = json.loads(line.decode("utf-8"))
                            chunk = data.get("response", "")
                            collected += chunk
                            # stream raw text back
                            yield chunk
                        except Exception:
                            pass
        except Exception as e:
            yield json.dumps({"error": str(e)})

        # Final parse attempt at the end
        if collected.strip():
            try:
                parsed = json.loads(collected)
                save_incident(req.category, req.agent, req.incident, json.dumps(parsed))
            except Exception:
                # Fallback: wrap raw output into JSON
                fallback = {
                    "investigation": ["Review logs manually."],
                    "commands": ["echo 'No structured response'"],
                    "fixes": [collected.strip()]
                }
                save_incident(req.category, req.agent, req.incident, json.dumps(fallback))

    return StreamingResponse(stream_response(), media_type="application/json")

# ---------------------------
# History API
# ---------------------------
@app.get("/incidents")
def incidents(limit: int = 20) -> List[Dict]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS incidents "
        "(id INTEGER PRIMARY KEY, timestamp TEXT, category TEXT, agent TEXT, incident TEXT, response TEXT)"
    )
    cursor.execute(
        "SELECT timestamp, category, agent, incident, response FROM incidents ORDER BY id DESC LIMIT ?",
        (limit,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {"timestamp": r[0], "category": r[1], "agent": r[2], "incident": r[3], "response": r[4]}
        for r in rows
    ]

# ---------------------------
# Healthcheck
# ---------------------------
@app.get("/health")
def health():
    return {"status": "ok", "db": "connected", "model": "ai/mistral:7B-Q4_0"}
