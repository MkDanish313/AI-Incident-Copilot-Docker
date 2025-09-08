#!/usr/bin/env python3
import psycopg2
import requests
import time
import os
from dotenv import load_dotenv

# Load config
load_dotenv("/opt/ai-incident-agent/.env")
API_URL = os.getenv("API_URL")
API_KEY = os.getenv("API_KEY")
PROJECT_ID = os.getenv("PROJECT_ID")

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "postgres"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASS", "example"),
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", 5432)),
}

def report_incident(message):
    payload = {
        "project_id": PROJECT_ID,
        "category": "database",
        "incident": message
    }
    headers = {"x-api-key": API_KEY}
    try:
        r = requests.post(API_URL, json=payload, headers=headers, timeout=10)
        print("Incident sent:", r.json())
    except Exception as e:
        print("Error sending incident:", e)

while True:
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        conn.close()
    except Exception as e:
        report_incident(f"Database connection failed: {str(e)}")
    time.sleep(30)
