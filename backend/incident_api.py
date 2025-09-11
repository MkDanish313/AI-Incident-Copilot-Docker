from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3
import subprocess
import os
from typing import List, Dict
from datetime import datetime

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

@app.post("/incident")
def handle_incident(req: IncidentRequest):
    # Call Ollama model
    command = f'ollama run llama2:7b "{req.incident}"'
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
