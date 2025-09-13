from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3
import subprocess
import os
from typing import List, Dict
from datetime import datetime
import yaml
import json

app = FastAPI()

DB_PATH = os.getenv("DB_PATH", "/data/db/incident.db")
CATEGORIES_FILE = os.getenv("CATEGORIES_FILE", "/app/incident_categories.yml")

class IncidentRequest(BaseModel):
    category: str
    agent: str
    incident: str

def save_incident(category, agent, incident, response_json):
    """Save incident + structured response to SQLite"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY,
            timestamp TEXT,
            category TEXT,
            agent TEXT,
            incident TEXT,
            response TEXT
        )"""
    )
    cursor.execute(
        "INSERT INTO incidents (timestamp, category, agent, incident, response) VALUES (?, ?, ?, ?, ?)",
        (datetime.utcnow().isoformat(), category, agent, incident, json.dumps(response_json)),
    )
    conn.commit()
    conn.close()

def load_category_prompt(category: str) -> str:
    """Load category-specific prompt from YAML, if exists"""
    try:
        with open(CATEGORIES_FILE, "r") as f:
            data = yaml.safe_load(f)
        return data.get("categories", {}).get(category, {}).get("prompt", "")
    except Exception:
        return ""

def get_agent_connect_command(agent: str) -> str:
    """Return agent install command for given agent"""
    mapping = {
        "linux": "curl -sSL https://<YOUR_API>/agents/linux_agent/install.sh | bash",
        "linux_agent": "curl -sSL https://<YOUR_API>/agents/linux_agent/install.sh | bash",
        "aws": "curl -sSL https://<YOUR_API>/agents/aws_agent/install.sh | bash",
        "aws_agent": "curl -sSL https://<YOUR_API>/agents/aws_agent/install.sh | bash",
        "db": "curl -sSL https://<YOUR_API>/agents/db_agent/install.sh | bash",
        "db_agent": "curl -sSL https://<YOUR_API>/agents/db_agent/install.sh | bash",
    }
    return mapping.get(agent.lower(), "No agent install script available. See docs.")

@app.get("/categories")
def get_categories():
    """Return all available categories from YAML"""
    try:
        with open(CATEGORIES_FILE, "r") as f:
            data = yaml.safe_load(f)
        return {"categories": list(data.get("categories", {}).keys())}
    except Exception:
        return {"categories": ["aws_outage", "kubernetes_crash", "database_down", "network_issue", "linux_issue"]}

@app.post("/incident")
def handle_incident(req: IncidentRequest):
    # Load category-specific context
    category_context = load_category_prompt(req.category)

    # Structured output prompt
    prompt = f"""
You are an AI Incident Copilot.
Category: {req.category}
Agent: {req.agent}
Incident: {req.incident}

Additional context:
{category_context}

Your task:
Return ONLY valid JSON with the following keys:
- investigation_steps: list of top 3 steps
- commands: list of CLI commands
- fixes: list of recommended fixes
- severity: Low/Medium/High
- recommended_action: short summary
- notes: any other suggestions (optional)

If you cannot determine exact fixes, still provide best suggestions.
"""

    # Call Ollama model
    command = f'ollama run llama2:7b "{prompt}"'
    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Ollama error: {result.stderr}")

    raw_output = result.stdout.strip()

    # Try parsing JSON
    try:
        response_json = json.loads(raw_output)
    except Exception:
        # fallback to suggestion-only mode
        response_json = {
            "investigation_steps": [],
            "commands": [],
            "fixes": [],
            "severity": "Unknown",
            "recommended_action": raw_output,
            "notes": "Suggestion-only mode (could not parse structured JSON)."
        }

    # Save incident
    save_incident(req.category, req.agent, req.incident, response_json)

    return {
        "response": response_json,
        "agent_connect": get_agent_connect_command(req.agent)
    }

@app.get("/incidents")
def get_incidents(limit: int = 20) -> List[Dict]:
    """Fetch incident history"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY,
            timestamp TEXT,
            category TEXT,
            agent TEXT,
            incident TEXT,
            response TEXT
        )"""
    )
    cursor.execute(
        "SELECT timestamp, category, agent, incident, response FROM incidents ORDER BY id DESC LIMIT ?",
        (limit,),
    )
    rows = cursor.fetchall()
    conn.close()

    history = []
    for r in rows:
        try:
            response_json = json.loads(r[4])
        except Exception:
            response_json = {"recommended_action": r[4]}
        history.append({
            "timestamp": r[0],
            "category": r[1],
            "agent": r[2],
            "incident": r[3],
            "response": response_json
        })
    return history

@app.get("/health")
def health_check():
    return {"status": "ok", "db": "connected", "model": "llama2:7b"}
