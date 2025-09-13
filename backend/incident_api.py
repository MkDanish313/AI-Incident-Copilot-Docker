import os
import time
import json
import sqlite3
import subprocess
import re
from datetime import datetime
from typing import List, Dict, Any, Optional

import yaml
import requests
from fastapi import FastAPI, HTTPException

app = FastAPI(title="AI Incident Copilot")

# Config (ensure these env vars are set in docker-compose or container)
OLLAMA_API = os.getenv("OLLAMA_API", "http://ollama:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "llama2:7b")
DB_PATH = os.getenv("DB_PATH", "/data/db/incident.db")
CATEGORIES_FILE = os.getenv("CATEGORIES_FILE", "/app/incident_categories.yml")

# ---------- Helpers ----------
def wait_for_ollama(max_retries: int = 60, delay: int = 5) -> None:
    """Wait until Ollama /api/tags responds 200. Raises if timeout."""
    for attempt in range(max_retries):
        try:
            r = requests.get(f"{OLLAMA_API}/api/tags", timeout=5)
            if r.status_code == 200:
                print("✅ Ollama is reachable")
                return
        except Exception:
            pass
        print(f"⏳ Waiting for Ollama... {attempt+1}/{max_retries}")
        time.sleep(delay)
    raise RuntimeError("Ollama not reachable after retries")

@app.on_event("startup")
def on_startup():
    # Ensure data dir exists and DB created
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    ensure_db()
    # Wait for Ollama to be reachable (prevents backend starting before ollama is up)
    try:
        wait_for_ollama()
    except Exception as e:
        # Startup should still continue, but we warn (Docker restart policy may handle it)
        print("Warning: Ollama not ready at startup:", e)

def ensure_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts INTEGER NOT NULL,
            timestamp TEXT,
            category TEXT,
            agent TEXT,
            incident TEXT,
            response_text TEXT,
            response_json TEXT
        )
        """
    )
    conn.commit()
    conn.close()

def save_incident(category: str, agent: str, incident: str, response_text: str, response_json: Optional[Dict[str, Any]] = None) -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO incidents (ts, timestamp, category, agent, incident, response_text, response_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (int(time.time()), datetime.utcnow().isoformat(), category, agent, incident, response_text, json.dumps(response_json) if response_json else None)
    )
    conn.commit()
    conn.close()

def load_category_prompt(category: str) -> str:
    try:
        with open(CATEGORIES_FILE, "r") as f:
            data = yaml.safe_load(f)
        return data.get("categories", {}).get(category, {}).get("prompt", "") or ""
    except Exception:
        return ""

def get_agent_connect_command(agent: str) -> str:
    # Keep these generic; replace your-api-server with real host later
    mapping = {
        "linux": "curl -sSL https://<YOUR_API>/agents/linux_agent/install.sh | bash",
        "linux_agent": "curl -sSL https://<YOUR_API>/agents/linux_agent/install.sh | bash",
        "aws": "curl -sSL https://<YOUR_API>/agents/aws_agent/install.sh | bash",
        "aws_agent": "curl -sSL https://<YOUR_API>/agents/aws_agent/install.sh | bash",
        "db": "curl -sSL https://<YOUR_API>/agents/db_agent/install.sh | bash",
        "db_agent": "curl -sSL https://<YOUR_API>/agents/db_agent/install.sh | bash",
    }
    return mapping.get(agent.lower(), "No agent install script available. See docs.")

def run_ollama(prompt: str, timeout: int = 300) -> str:
    """
    Safe call to local ollama CLI: send prompt via stdin to avoid shell quoting issues.
    Returns the raw stdout (string). Does NOT execute any returned commands.
    """
    # prefer calling ollama server via HTTP if available, else fallback to CLI
    try:
        # Preferred: use ollama HTTP generate endpoint if reachable
        r = requests.post(f"{OLLAMA_API}/api/generate", json={"model": MODEL_NAME, "prompt": prompt, "stream": False}, timeout=timeout)
        if r.status_code == 200:
            return r.json().get("response", "").strip()
        else:
            # fallback to CLI if server returns non-200
            print("ollama HTTP error:", r.status_code, r.text)
    except Exception as e:
        print("ollama HTTP generate failed:", e)

    # fallback: use local CLI safely (stdin)
    try:
        proc = subprocess.run(
            ["ollama", "run", MODEL_NAME],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or f"ollama CLI exited {proc.returncode}")
        return proc.stdout.strip()
    except Exception as e:
        raise RuntimeError(f"ollama call failed: {e}")

def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Try to find a JSON object in a long text and parse it.
    If multiple JSON objects present, parse the first one. Returns None if not found/parseable.
    """
    # common pattern: find {...} block
    m = re.search(r"(\{(?:.|\s)*\})", text)
    if not m:
        return None
    candidate = m.group(1)
    try:
        return json.loads(candidate)
    except Exception:
        # remove trailing commas, try again more leniently
        candidate2 = re.sub(r",\s*}", "}", candidate)
        try:
            return json.loads(candidate2)
        except Exception:
            return None

# ---------- API endpoints ----------

@app.get("/health")
def health():
    # minimal health that checks if Ollama HTTP endpoint responds
    ok = False
    model = os.getenv("MODEL_NAME", MODEL_NAME)
    try:
        r = requests.get(f"{OLLAMA_API}/api/tags", timeout=3)
        ok = r.status_code == 200
    except Exception:
        ok = False
    return {"status": "ok" if ok else "degraded", "model": model, "db": DB_PATH}

@app.get("/categories")
def categories():
    y = {}
    try:
        with open(CATEGORIES_FILE, "r") as f:
            y = yaml.safe_load(f) or {}
    except Exception:
        y = {}
    return {"categories": list((y.get("categories") or {}).keys())}

@app.post("/incident")
def handle_incident(payload: Dict[str, str]):
    """
    Accepts payload: { "category": "...", "agent": "...", "incident": "raw logs or metrics or description" }
    Returns structured response JSON (investigation_steps, commands, fixes, severity, recommended_action)
    """
    category = payload.get("category", "") or "general"
    agent = payload.get("agent", "") or "general"
    incident = payload.get("incident", "") or ""

    # add category-specific context if available
    category_context = load_category_prompt(category)

    # Build strict JSON-output prompt
    # NOTE: we instruct the model to return JSON ONLY, with a defined schema.
    schema = {
        "investigation_steps": ["string - step 1", "string - step 2"],
        "commands": ["string - exact shell/cli commands to run (examples). DO NOT EXECUTE"],
        "fixes": ["string - recommended fixes or workarounds"],
        "severity": "low|medium|high|critical",
        "recommended_action": "short action e.g. 'scale-up', 'restart-service', 'open-incident-ticket'",
        "notes": "free text, additional context"
    }

    prompt = f"""
You are an AI Incident Copilot that NEVER executes commands. You must ALWAYS return a valid JSON object only (no extra text) with the schema provided below. 
Schema:
{json.dumps(schema, indent=2)}

Context:
Category: {category}
Agent: {agent}
Incident (raw): \"\"\"{incident}\"\"\"

Additional category-specific hints (if available):
{category_context}

Task:
- Analyze the incident text above (could be logs, metrics, or free text) and produce:
  1) investigation_steps: a short ordered list of top 3 steps to investigate.
  2) commands: exact CLI commands (examples only) that an operator should run to collect evidence or apply a fix. **DO NOT EXECUTE**.
  3) fixes: concise fixes or workarounds to resolve the issue.
  4) severity: low/medium/high/critical.
  5) recommended_action: single short action label (scale-up, restart-service, rollback-deploy, escalate-to-oncall, etc).
  6) notes: optional human-readable explanation.

- Output MUST BE a single JSON object and nothing else (no markdown, no commentary).
- Be concise and practical.
"""

    # call ollama (safe)
    try:
        raw = run_ollama(prompt)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ollama call failed: {e}")

    # try to parse JSON out of the raw text
    parsed = extract_json_from_text(raw)
    response_json = None
    if parsed:
        response_json = parsed
    else:
        # if model didn't return JSON, fallback: wrap raw text into response_text field
        response_json = {
            "investigation_steps": [],
            "commands": [],
            "fixes": [],
            "severity": "unknown",
            "recommended_action": "investigate",
            "notes": raw
        }

    # Save full text & structured JSON (if available)
    save_incident(category, agent, incident, raw, response_json)

    # agent connect command (help frontend show how to connect)
    agent_connect = get_agent_connect_command(agent)

    # Return both the structured JSON and the raw text to frontend
    return {"response_json": response_json, "response_text": raw, "agent_connect": agent_connect}


@app.get("/incidents")
def get_incidents(limit: int = 20) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT timestamp, category, agent, incident, response_text, response_json FROM incidents ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()

    items = []
    for r in rows:
        ts, category, agent, incident, response_text, response_json = r
        parsed = None
        try:
            parsed = json.loads(response_json) if response_json else None
        except Exception:
            parsed = None
        items.append({
            "timestamp": ts,
            "category": category,
            "agent": agent,
            "incident": incident,
            "response_text": response_text,
            "response_json": parsed
        })
    return {"items": items}
