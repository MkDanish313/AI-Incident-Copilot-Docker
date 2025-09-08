FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# app code
COPY incident_api.py .
COPY incident_bot.py .
COPY incident_copilot_v2.py .
COPY incident_categories.yml .

CMD ["uvicorn", "incident_api:app", "--host", "0.0.0.0", "--port", "8000"]
