🛡️ AI Incident Copilot

Your AI-powered Incident Response Assistant for Cloud, DevOps & Databases
Deployed with Terraform + Docker + LangChain + Ollama

📖 Overview

AI Incident Copilot is an open-source, lightweight SaaS-ready tool that connects directly with your cloud infrastructure, Kubernetes clusters, and databases to help you handle incidents in real-time.

It provides:

🚨 Automated incident detection & AI-driven response suggestions

🔗 Agent connectors for Linux, AWS, and Databases

🌐 User-friendly dashboard to monitor, investigate, and resolve issues

⚡ Single-command deployment via Terraform + Docker Compose

💸 Lightweight & cost-effective (runs on t3.medium / t3.large EC2)

🏗️ Architecture
AI-Incident-Copilot-Docker/
├── infra/                     # Terraform infrastructure
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   └── modules/
│       └── ec2/
│           ├── main.tf
│           ├── variables.tf
│           └── outputs.tf
│
├── backend/                   # FastAPI + LangChain + Agents
│   ├── incident_api.py
│   ├── incident_bot.py
│   ├── incident_copilot_v2.py
│   ├── incident_categories.yml
│   └── agents/
│       ├── linux_agent/
│       │   └── agent_linux.py
│       ├── aws_agent/
│       │   └── agent_aws.py
│       └── db_agent/
│           └── agent_db.py
│
├── frontend/                  # Streamlit Dashboard
│   └── app.py
│
├── data/                      # Persistent volumes
│   ├── db/        # SQLite DB auto-created
│   └── ollama/    # Ollama model cache
│
├── docker-compose.yml         # Service orchestration
└── README.md

⚡ Features

🔥 Incident Copilot (AI suggestions with step-by-step troubleshooting)

📂 Incident Categories (AWS outage, K8s crash, DB down, Linux issue)

🧩 Extensible Agents (Linux, AWS, DB → more coming soon)

🌍 REST API (/incident) for programmatic usage

📊 Frontend Dashboard (Streamlit) for non-technical users

🐳 Dockerized Deployment (Lightweight & portable)

☁️ Terraform IaC (EC2 infra provisioning in one command)

🚀 Quick Start
1️⃣ Clone the Repository
git clone https://github.com/MkDanish313/AI-Incident-Copilot-Docker.git
cd AI-Incident-Copilot-Docker

2️⃣ Deploy Infra with Terraform
cd infra
terraform init
terraform apply -auto-approve


This provisions an EC2 instance with Docker + Docker Compose pre-installed and auto-runs the project.

3️⃣ Access the Services

Frontend (Dashboard):
http://<EC2_PUBLIC_IP>:8501

Backend (API Health):
http://<EC2_PUBLIC_IP>:8000/health

Incident API Example:

curl -X POST http://<EC2_PUBLIC_IP>:8000/incident \
  -H "Content-Type: application/json" \
  -d '{"category": "kubernetes_crash", "incident": "Pods stuck in CrashLoopBackOff"}'

🔗 Agents

Agents connect the Copilot with your environment:

🐧 Linux Agent → Collects logs, system stats, dmesg, etc.

☁️ AWS Agent → Monitors EC2, S3, CloudWatch alerts.

🗄️ DB Agent → Collects DB logs, slow queries, connection issues.

Each agent runs as a lightweight script and connects to backend via secure API.

📊 Example Incident

Input:

{
  "category": "aws_outage",
  "incident": "EC2 instance CPU usage is 95%"
}


AI Copilot Response:

1. Check CloudWatch metrics for instance i-xxxxxx
2. SSH into instance and run `top` or `htop` to identify processes
3. If load is due to app, consider scaling ASG or using ECS/EKS

🏆 Why AI Incident Copilot?

Traditional monitoring tools alert you ⚠️ but don’t tell you what to do next.

AI Incident Copilot gives step-by-step guided response so even L1 engineers can act fast.

Saves time, cost, and MTTR (Mean Time to Resolve).

🛠️ Tech Stack

Infra: Terraform, AWS EC2, Security Groups

AI Model: Ollama + LLaMA 2 (7B, lightweight)

Backend: FastAPI + LangChain + Agents

Frontend: Streamlit

DB: SQLite (lightweight, can upgrade to Postgres)

Containerization: Docker + Docker Compose

📌 Roadmap

 Terraform IaC for infra provisioning

 Docker Compose for lightweight deployment

 Backend (API + LangChain)

 Frontend (Streamlit dashboard)

 Agents (Linux, AWS, DB)

 User Auth (Firebase / JWT)

 Multi-tenant SaaS support

 Postgres integration for production

 Webhook connectors (Jenkins, K8s, Prometheus, CloudWatch)

 Stripe billing integration

🤝 Contributing

Pull requests are welcome! Please open an issue first to discuss what you would like to change.

📄 License

MIT License © 2025 Danish Malak
