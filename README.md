# 🚀 Jira-CrewAI AI-Driven SRE Automated Triage System

[![CI Pipeline](https://github.com/vaibhav2616/Jira-Crew-AI-Driven-SRE-Automated-Triage-System/actions/workflows/ci.yml/badge.svg)](https://github.com/vaibhav2616/Jira-Crew-AI-Driven-SRE-Automated-Triage-System/actions)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![CrewAI](https://img.shields.io/badge/CrewAI-1.15+-ff4f00.svg)](https://crewai.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Cost: 100% Free](https://img.shields.io/badge/Cost-100%25%20Free%20Tier-brightgreen.svg)](#-100-free-forever-tier-architecture)

An asynchronous, enterprise-grade, **zero-dollar cost** SRE incident triage microservice. Built for high-throughput distributed architectures—such as **Distributed Payment Gateways**, banking systems, and microservice meshes—it autonomously ingests production alerts, prevents alert storms via SHA-256 Redis deduplication, dispatches a collaborative **CrewAI multi-agent incident response team**, and creates enriched tickets in **Atlassian Jira REST API v3** using native **Atlassian Document Format (ADF)**.

---

## 📑 Table of Contents

- [Architectural Overview](#-architectural-overview)
- [CrewAI Multi-Agent Incident Response Team](#-crewai-multi-agent-incident-response-team)
- [100% Free-Forever Tier Architecture](#-100-free-forever-tier-architecture)
- [Universal Microservice Integration](#-universal-microservice-integration)
- [Project Layout](#-project-layout)
- [Quickstart Guide](#-quickstart-guide)
- [Integrating with Any Project (e.g., Distributed Payment Gateway)](#-integrating-with-any-project-eg-distributed-payment-gateway)
- [Alert Deduplication & Storm Protection](#-alert-deduplication--storm-protection)
- [Jira Atlassian Document Format (ADF) Output](#-jira-atlassian-document-format-adf-output)
- [Testing & Quality Verification](#-testing--quality-verification)
- [Docker Compose Deployment](#-docker-compose-deployment)

---

## 🏛 Architectural Overview

```
                                      [ Production Systems ]
                       +---------------------------------------------------+
                       | Distributed Payment Gateway | Prometheus | Sentry |
                       +---------------------------------------------------+
                                                 |
                                                 | Ingest Alert (REST / Webhook / SDK)
                                                 v
                       +---------------------------------------------------+
                       |            FastAPI Ingestion Engine               |
                       |   (/api/v1/triage/ingest  &  /api/v1/alerts)      |
                       +-------------------------+-------------------------+
                                                 |
                                                 v
                       +---------------------------------------------------+
                       |         Universal Adapter Ingestion Layer         |
                       | (GenericAdapter | AlertmanagerAdapter | Sentry)   |
                       +-------------------------+-------------------------+
                                                 |
                                                 v
                       +---------------------------------------------------+
                       |          Alert Deduplication Engine               |
                       |       SHA-256 Fingerprint + Redis Cache           |
                       +----+----------------------------------------------+
                            |                                    |
                Cache Hit   |                        Cache Miss  |
            (Alert Storm)   v                                    v
     +-------------------------------+   +------------------------------------+
     | Suppress Alert & Link to      |   |   CrewAI Multi-Agent SRE Engine    |
     | Existing Active Jira Issue    |   |------------------------------------|
     +-------------------------------+   | 1. Incident Commander              |
                                         | 2. Telemetry & Forensics SRE       |
                                         | 3. Root Cause Architect            |
                                         | 4. Runbook & Automation Engineer   |
                                         +-----------------+------------------+
                                                           |
                                                           | Structured Triage Output
                                                           v
                                         +------------------------------------+
                                         |   Atlassian Document Format (ADF)  |
                                         |          Payload Builder           |
                                         +-----------------+------------------+
                                                           |
                                                           | Asynchronous HTTPS Basic Auth
                                                           v
                                         +------------------------------------+
                                         |      Atlassian Jira Cloud v3       |
                                         |        (/rest/api/3/issue)         |
                                         +------------------------------------+
```

---

## 🤖 CrewAI Multi-Agent Incident Response Team

Rather than relying on a single generic LLM prompt, this system orchestrates four specialized autonomous SRE agents executing sequential investigations:

```
[Incoming Alert]
       │
       ▼
┌─────────────────────────────────┐
│     SRE Incident Commander      │ ──► Triages severity (High/Medium/Low), evaluates business
└────────────────┬────────────────┘     impact & SLO risk, defines incident scope.
                 │
                 ▼
┌─────────────────────────────────┐
│   Telemetry & Forensics SRE     │ ──► Parses stack traces, extracts metrics anomalies
└────────────────┬────────────────┘     (p99 latency, DB pools, error rates, error types).
                 │
                 ▼
┌─────────────────────────────────┐
│       RCA System Architect      │ ──► Identifies the mechanical root cause (e.g. deadlock,
└────────────────┬────────────────┘     connection pool starvation, upstream timeout, race condition).
                 │
                 ▼
┌─────────────────────────────────┐
│  Runbook & Automation Engineer  │ ──► Formulates actionable step-by-step mitigation commands,
└────────────────┬────────────────┘     exact rollback commands, and long-term prevention steps.
                 │
                 ▼
    [Enriched CrewSRETriageResult]
```

---

## 💸 100% Free-Forever Tier Architecture

This system is specifically engineered for student developers, open-source projects, and startups with **$0 cloud budget**:

| Component | Free Solution | Free Tier Allowance | Configuration |
| :--- | :--- | :--- | :--- |
| **Primary AI Engine** | **Google Gemini 2.5 Flash** | **15 RPM / 1M TPM / 1,500 RPD** free forever via Google AI Studio | `LLM_PROVIDER=gemini` |
| **100% Offline AI** | **Ollama** (Local Llama 3.2 / Mistral / Qwen) | **Unlimited (Local CPU/GPU)** | `LLM_PROVIDER=ollama` |
| **Ultra-Fast Cloud AI** | **Groq Cloud** (Llama 3.3 70B) | **Generous Free API Tier** | `LLM_PROVIDER=groq` |
| **Air-Gapped / CI AI** | **Deterministic SRE Heuristic Engine** | **100% Offline Fallback** (Zero dependencies) | Automatic Fallback |
| **Issue Tracker** | **Atlassian Jira Cloud** | **Free for up to 10 users** | REST API v3 Basic Auth |
| **Deduplication Cache**| **Local Redis / In-Memory Fakeredis** | **Free Docker / In-Memory auto-fallback** | Built-in |

---

## 🔌 Universal Microservice Integration

Any system in your architecture can seamlessly stream incident telemetry to the triage system using **three integration modes**:

### Mode 1: Python Client SDK (`sre-triage-sdk`)
Installable directly into any Python microservice (payment gateways, auth services, order processors):
```python
from sre_triage_sdk import SRETriageClient, triage_on_failure

# Synchronous or asynchronous reporting
client = SRETriageClient(endpoint="http://localhost:8000/api/v1/triage/ingest")

client.report_incident(
    service_name="payment-gateway",
    error_message="Postgres connection pool exhausted after 15000ms",
    error_type="PoolExhaustionError",
    raw_logs={"active_connections": 100, "max_pool": 100},
    metrics={"p99_latency_ms": 4800},
    trace_id="pmt-txn-48921",
)
```

### Mode 2: Zero-Boilerplate Decorator (`@triage_on_failure`)
Decorate critical path operations like payment processing or checkout:
```python
@triage_on_failure(service_name="distributed-payment-gateway")
def process_stripe_charge(order_id: str, amount_cents: int) -> dict[str, str]:
    # If this raises any unhandled exception (e.g. Stripe 504 or DB timeout),
    # an incident payload is asynchronously reported to SRE Triage before re-raising.
    return stripe_client.charge(order_id, amount_cents)
```

### Mode 3: Native Webhook Ingestion (Prometheus & Sentry)
- **Prometheus Alertmanager:** Configure webhook receivers pointing to `/api/v1/triage/ingest`. The `AlertmanagerAdapter` automatically normalizes `labels` and `annotations`.
- **Sentry / Datadog / PagerDuty:** Configure webhook notifications. The payload is automatically parsed and mapped into `UniversalAlertPayload`.

---

## 📁 Project Layout

```
ai-driven-sre-automated-triage-system/
├── Dockerfile                          # Multi-stage production container
├── docker-compose.yml                  # Full stack: FastAPI microservice + Redis
├── pyproject.toml                      # Modern packaging & strict mypy / ruff rules
├── requirements.txt                    # Python dependencies
├── .env.example                        # Template for environment configuration
├── main.py                             # Microservice entrypoint
├── src/
│   ├── config.py                       # Pydantic BaseSettings (Multi-LLM & Jira config)
│   ├── main.py                         # FastAPI application factory with lifespan
│   ├── api/
│   │   ├── alerts.py                   # /api/v1/alerts and /api/v1/triage/ingest routes
│   │   ├── deps.py                     # Singleton DI providers for Jira, LLM, Redis, Crew
│   │   └── health.py                   # Kubernetes health checks (/healthz, /livez)
│   ├── adapters/                       # Universal integration adapters
│   │   ├── base.py                     # BaseAlertAdapter interface
│   │   ├── generic.py                  # Adapter for arbitrary microservices (Payment, Auth)
│   │   ├── alertmanager.py             # Prometheus Alertmanager webhook adapter
│   │   └── sentry.py                   # Sentry issue webhook adapter
│   ├── crew/                           # CrewAI multi-agent reasoning engine
│   │   ├── agents.py                   # Commander, Forensics, RCA, and Runbook agents
│   │   ├── tasks.py                    # Multi-agent sequential triage tasks
│   │   └── sre_crew.py                 # SREIncidentCrew orchestrator & fallback engine
│   ├── infrastructure/
│   │   ├── jira_client.py              # Async Jira REST v3 client + ADF v1 builder
│   │   ├── llm_client.py               # Google Gemini client with structured output schema
│   │   ├── redis_client.py             # Async Redis connection pool + fakeredis fallback
│   │   └── exceptions.py               # Domain exceptions (JiraAPIError, SRETriageException)
│   ├── schemas/
│   │   ├── alert.py                    # IncomingAlert, LLMTriageResult, AlertTriageResponse
│   │   ├── universal_alert.py          # UniversalAlertPayload with SHA-256 fingerprinting
│   │   └── triage_result.py            # CrewSRETriageResult (impact, RCA, runbook, rollback)
│   └── services/
│       └── triage_service.py           # Core triage orchestrator (Dedup -> Crew -> Jira)
├── sdk/
│   └── python/sre_triage_sdk/          # Standalone client SDK and failure decorators
├── examples/
│   └── distributed_payment_gateway_demo.py  # Realistic distributed payment gateway simulation
└── tests/                              # Comprehensive test suite (57 tests, 96% coverage)
    ├── conftest.py                     # Pytest fixtures and test doubles
    ├── test_alerts_api.py              # Ingestion API tests
    ├── test_universal_adapters.py      # Adapter parsing tests
    ├── test_crew_sre.py                # Multi-agent reasoning tests
    ├── test_sdk.py                     # SDK client and decorator tests
    ├── test_jira_client.py             # Jira client and ADF tests
    ├── test_redis_client.py            # Deduplication cache tests
    └── test_coverage_gaps.py           # Resilience, fallback, and boundary tests
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- Python 3.12+
- (Optional) Docker & Docker Compose
- Free Google Gemini API Key from [Google AI Studio](https://aistudio.google.com/) (or local Ollama)
- Free Atlassian Jira Cloud instance from [Atlassian](https://www.atlassian.com/software/jira/free)

### 2. Installation
```bash
git clone https://github.com/vaibhav2616/Jira-Crew-AI-Driven-SRE-Automated-Triage-System.git
cd Jira-Crew-AI-Driven-SRE-Automated-Triage-System

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy `.env.example` to `.env` and fill in your free credentials:
```bash
cp .env.example .env
```

```env
# Atlassian Jira Cloud Configuration (Free Tier)
JIRA_DOMAIN=your-domain.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your_jira_api_token
JIRA_PROJECT_KEY=KAN

# AI Engine Provider (gemini | ollama | groq)
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_free_google_ai_studio_api_key

# Deduplication Cache
REDIS_URL=redis://localhost:6379
```

### 4. Start the Service
```bash
python main.py
# Or with Uvicorn:
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 💳 Integrating with Any Project (e.g., Distributed Payment Gateway)

Try the included comprehensive simulation:
```bash
python examples/distributed_payment_gateway_demo.py
```

This demonstrates:
1. **Database Connection Pool Exhaustion:** When payment workers saturate database connections under surge traffic.
2. **Stripe Gateway 504 Gateway Timeout:** Upstream payment processor timeouts handled gracefully with automated incident reporting.
3. **Alert Storm Suppression:** Firing 5 identical error payloads in rapid succession triggers the Redis deduplication filter, generating only **one** Jira ticket while returning existing ticket references for subsequent alerts.

---

## 🛡 Alert Deduplication & Storm Protection

During a cascade failure, hundreds of microservice instances might emit the same error per second.

1. **Fingerprint Computation:**
   ```python
   # SHA-256 hash across (service_name + error_message[:100])
   signature = hashlib.sha256(f"{service_name}:{error_message[:100]}".encode()).hexdigest()
   ```
2. **Redis Deduplication Lookup:**
   - On alert receipt, Redis is checked for `alert:dedup:{signature}`.
   - If present, the request immediately terminates with `status="deduplicated"` and links to the active Jira ticket.
   - If absent, the multi-agent Crew diagnoses the incident, creates the Jira issue, and registers the signature in Redis with a 15-minute TTL (900s).

---

## 📋 Jira Atlassian Document Format (ADF) Output

Every ticket created features structured, rich sections rendered in Jira:

- 🚨 **Executive Impact Assessment:** Blast radius and customer-facing impact.
- 🔍 **Root Cause Analysis (RCA):** Deep architectural diagnosis of the failure mechanism.
- ⚠️ **Anomalies Detected:** Bulleted breakdown of metrics and log indicators.
- 🛠 **Step-by-Step Runbook:** Ordered procedural checklist for on-call SREs.
- ⏪ **Rollback Guidance:** Code blocks containing precise rollback commands.
- 🛡 **Preventative Measures:** Long-term architectural fixes to prevent recurrence.
- 📊 **Diagnostic Logs & Trace ID:** Monospaced formatted telemetry data.

---

## 🧪 Testing & Quality Verification

Run the comprehensive test suite (all tests mock external network requests, allowing offline CI verification):

```bash
# Run pytest with 100% offline coverage report
HOME=/tmp CREWAI_STORAGE_DIR=/tmp/crewai_storage CREWAI_DISABLE_TELEMETRY=true pytest --cov=src --cov=sdk/python/sre_triage_sdk --cov-report=term-missing tests/

# Run strict type checking
python -m mypy --strict src/ tests/ sdk/ examples/

# Run code style and linting
python -m ruff check src/ tests/ sdk/ examples/
```

### Test Coverage Results:
- **57 Passed Tests Across 10 Test Modules**
- **96% Code Coverage**
- **0 Type Violations in Strict Mypy Mode**

---

## 🐳 Docker Compose Deployment

Spin up the entire microservice and a local Redis container with a single command:

```bash
docker compose up --build -d
```

Check health status:
```bash
curl http://localhost:8000/healthz
# {"status":"ok","timestamp":"...","version":"0.2.0"}
```

---

## 📄 License

This project is licensed under the MIT License. Built for students, engineers, and SRE teams worldwide.
