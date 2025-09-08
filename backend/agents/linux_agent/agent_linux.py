#!/usr/bin/env python3
import psutil
import requests
import time
import socket
import os
from dotenv import load_dotenv

# Load config
load_dotenv("/opt/ai-incident-agent/.env")
API_URL = os.getenv("API_URL")
API_KEY = os.getenv("API_KEY")
PROJECT_ID = os.getenv("PROJECT_ID")

def report_incident(message):
    payload = {
        "project_id": PROJECT_ID,
        "category": "linux_host",
        "incident": message
    }
    headers = {"x-api-key": API_KEY}
    try:
        r = requests.post(API_URL, json=payload, headers=headers, timeout=10)
        print("Incident sent:", r.json())
    except Exception as e:
        print("Error sending incident:", e)

while True:
    cpu = psutil.cpu_percent(interval=5)
    mem = psutil.virtual_memory().percent
    if cpu > 80:
        report_incident(f"High CPU detected on {socket.gethostname()} - {cpu}%")
    if mem > 85:
        report_incident(f"High Memory usage detected on {socket.gethostname()} - {mem}%")
    time.sleep(30)
