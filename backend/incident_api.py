from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3
import subprocess
import os
from typing import List, Dict
from datetime import datetime
import yaml

app = FastAPI()

DB_PATH = os.getenv("DB_PATH", "/data/db/incident.db")
CATEGORIES_FILE = os.getenv("CATEGORIES_FILE", "/app/incident_categories.yml")

class IncidentRequest(BaseModel):
    category: str
    agent: str
    incident: str

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

def load_category_prompt(category: str) -> str:
    """Load category-specific prompt from YAML, if exists"""
    try:
        with open(CATEGORIES_FILE, "r") as f:
            data = yaml.safe_load(f)
        return data.get("categories", {}).get(category, {}).get("prompt", "")
    except Exception:
        return ""

@app.post("/incident")
def handle_incident(req: IncidentRequest):
    # Load category-specific context (optional)
    category_context = load_category_prompt(req.category)

    # Build improved prompt
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

    # Call Ollama model
    command = f'ollama run llama2:7b "{prompt}"'
    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Ollama error: {result.stderr}")

    response_text = result.stdout.strip()
    save_incident(req.category, req.agent, req.incident, response_text)

    return {"response": response_text}

@app.get("/incidents")
def get_incidents(limit: int = 20) -> List[Dict]:
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
