# 🛡️ CyberSentinel AI

> **Production-Grade, AI-Powered Cybersecurity & SOC Operations Platform**

CyberSentinel AI is an intelligent Security Operations Center (SOC) platform built for modern cybersecurity teams. It integrates automated log ingestion, ML/heuristic anomaly detection, real-time threat intelligence enrichment, WebSocket alert streaming, and a Google Gemini-powered AI security analyst.

---

## ✨ Key Features

- **🤖 AI Security Analyst**: Interactive SOC analyst assistant powered by Google Gemini with multi-turn conversations and contextual threat investigations.
- **⚡ Real-Time WebSockets**: Live security alert notifications and anomaly feeds streamed directly to SOC operators via org-scoped WebSockets.
- **📊 SIEM & Anomaly Detection**: Log ingestion engine with multi-pattern heuristic scoring for brute force, SQL injection, XSS, path traversal, scanner probes, and malware indicators.
- **🌐 Threat Intelligence Feeds**: Automated indicator synchronization with AbuseIPDB, AlienVault OTX, and curated open threat intelligence feeds.
- **🔐 Enterprise Security & RBAC**:
  - RS256 Asymmetric JWT authentication with RSA key rotation.
  - Multi-tenant organization scoping.
  - Strict Role-Based Access Control (**Admin**, **Analyst**, **Viewer**).
  - Dual-auth log ingestion via **`X-API-Key`** or JWT bearer tokens.
- **👥 Team Management**: User invitation, role modification, account lifecycle management, and rate limiting.
- **📄 Automated Security Reports**: Executive summaries, incident reports, and compliance snapshots generated on demand or asynchronously via Celery.
- **🎨 Cyber-Themed Modern UI**: Next.js 14 App Router interface with custom dark design system, Recharts data visualization, dynamic DEFCON threat levels, and live UTC clocks.

---

## 🏛️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 CyberSentinel Frontend UI                   │
│          Next.js 14 • React 18 • TypeScript • Recharts      │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP / WebSockets
┌──────────────────────────────▼──────────────────────────────┐
│                    FastAPI Backend Core                     │
│  Routers: Auth, Alerts, Logs, Threats, Assets, AI, Reports  │
│      Middlewares: CORS, GZip, Rate Limiting, Audit Logs     │
└──────────────┬───────────────────────────────┬──────────────┘
               │                               │
┌──────────────▼──────────────┐ ┌──────────────▼──────────────┐
│     PostgreSQL / SQLite     │ │     Redis & Celery Queue    │
│  SQLAlchemy 2.0 (Async)     │ │  Task Worker & Beat Sched.  │
└─────────────────────────────┘ └─────────────────────────────┘
```

---

## 🚀 Quick Start with Docker (Recommended)

### 1. Clone & Configure
```bash
git clone https://github.com/<your-username>/cybersentinel-ai.git
cd cybersentinel-ai
cp .env.example .env
```

Edit `.env` to configure your passwords and API keys:
```env
SECRET_KEY=generate_a_secure_random_64_character_string
POSTGRES_PASSWORD=your_strong_db_password
REDIS_PASSWORD=your_strong_redis_password
GEMINI_API_KEY=your_gemini_api_key_here
```

### 2. Launch Services
```bash
docker compose up --build -d
```

### 3. Access Applications
- **Frontend Dashboard:** [http://localhost:3000](http://localhost:3000)
- **FastAPI Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **API Health Check:** [http://localhost:8000/health](http://localhost:8000/health)

---

## 💻 Local Development Setup (Without Docker)

### Backend (FastAPI + SQLite Fallback)
```bash
cd backend

# Create & activate virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Generate RSA keys for RS256 JWT
python generate_keys.py

# (Optional) Seed demo data
python seed_db.py

# Start API server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Frontend (Next.js 14)
```bash
cd frontend

# Set environment
cp .env.local.example .env.local

# Install dependencies
npm install

# Start development server
npm run dev
```

---

## 🔑 Default Demo Credentials (Local Seeder)

| Role | Email | Password |
| :--- | :--- | :--- |
| **Admin (SOC Lead)** | `admin@cybersentinel.com` | `Admin@12345678` |

---

## 📡 Programmatic Log Ingestion API

Authenticate using either your organization **`X-API-Key`** or a JWT bearer token:

```bash
curl -X POST http://localhost:8000/api/v1/logs/ingest \
  -H "X-API-Key: cs_your_organization_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "firewall-edge-01",
    "raw_log": "Jul 30 12:00:00 srv sshd[1042]: Failed password for root from 192.168.1.50 port 22 ssh2",
    "log_type": "auth"
  }'
```

---

## 🛡️ License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

