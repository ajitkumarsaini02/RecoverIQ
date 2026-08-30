# RecoverIQ — AI Revenue Recovery Agent
> **Razorpay Buildathon Track 3: AI Revenue Recovery**  
> *Intelligent, explainable, bounded, and policy-governed revenue recovery for merchants.*

---

## 📌 Disclaimer
> **Synthetic & Test Data Notice:** All metrics, transaction records, customer histories, and recovery statistics presented in this application are generated from **Razorpay TEST MODE** APIs or deterministic **Synthetic / Demo Data**. RecoverIQ does **not** process live real-world merchant revenue or touch real money.

---

## 1. Executive Summary & Problem Statement

### The Core Problem
E-commerce and SaaS merchants lose significant revenue due to transient payment failures, UPI PSP timeouts, bank declines, network drops, and abandoned checkout flows. 

- **Manual investigation is impossible at scale**: Merchants cannot manually triage hundreds of failed transactions daily.
- **Naive automated retries cause severe friction**: Indiscriminate retries cause customer frustration, bank decline fees, and card network penalties.
- **Generic chatbots cannot solve recovery**: Unconstrained LLMs cannot safely execute financial actions without strict, deterministic guardrails.

### The Solution: RecoverIQ
**RecoverIQ** is an autonomous fintech recovery agent that pairs structured AI reasoning with a deterministic safety policy engine:
1. **Detects** payment failures across merchant transactions in real-time.
2. **Diagnoses** the technical root cause (`UPI_TIMEOUT`, `BANK_DECLINED`, `INSUFFICIENT_FUNDS`, `NETWORK_ERROR`, `PAYMENT_METHOD_ERROR`).
3. **Understands Customer Context** (Lifetime Value, historical success/failure ratio, retry attempts).
4. **Predicts Recovery Probability** using a calibrated, Pydantic-validated reasoning model.
5. **Enforces Deterministic Safety Rules** through the Policy Engine before executing any payment action.
6. **Executes Safe Recovery** (`RETRY_PAYMENT`, `PAYMENT_LINK`, `ALTERNATIVE_PAYMENT_METHOD`, `REMINDER`, `HUMAN_ESCALATION`, `STOP`) on Razorpay Test Gateway.
7. **Quantifies Recovered Revenue** dynamically and logs an immutable audit trail.

---

## 2. Complete End-to-End Recovery Pipeline

```
FAILED PAYMENT
       ↓
DETECT (Gateway Webhook / Transaction Ingestion)
       ↓
DIAGNOSE (UPI Timeout vs Bank Decline vs Insufficient Funds)
       ↓
AI DECISION (Probability Estimation & Action Recommendation)
       ↓
POLICY VALIDATION (Deterministic Safety Guardrails)
       ↓
RECOVERY ACTION (Razorpay Test Mode Order / Payment Link / Gated Queue)
       ↓
RESULT (Success / Pending / Gated / Stopped)
       ↓
REVENUE RECOVERED (+₹ Captured)
       ↓
DASHBOARD & AUDIT TRAIL (Live Real-Time Math & Compliance Logging)
```

---

## 3. System Architecture

```mermaid
graph TD
    subgraph Merchant Interface
        User([Merchant / Operator]) --> FE[React 18 + TypeScript + Tailwind Frontend]
    end

    subgraph Backend Core (FastAPI)
        FE -->|REST API| API[FastAPI Routers]
        API --> AgentSvc[AI Agent Service - Pydantic v2]
        API --> PolicyEng[Deterministic Policy Engine]
        API --> RecovEng[Recovery Execution Engine]
        API --> AuditSvc[Audit Trail Service]
        API --> SimEng[Batch Portfolio Simulation Engine]
        API --> RazorpaySvc[Razorpay Test Mode Layer]
    end

    subgraph Storage Layer
        API --> DB[(SQLite / SQLAlchemy 2.0 DB)]
        AuditSvc --> DB
    end

    subgraph External Gateways
        AgentSvc -->|Structured Reasoning| AIModel[LLM Provider / Heuristic Fallback]
        RazorpaySvc -->|Test Mode / Simulation| RzpAPI[Razorpay Test Gateway]
    end
```

---

## 4. Key Architectural Modules

### 🛡️ Deterministic Policy Engine (Guardrails)
The AI agent strictly *recommends*, but the **Policy Engine** has final binding authority:
- **Rule 1 (Max 2 Retries Ceiling)**: Enforces an absolute cap of 2 automatic retries. Exceeding retries forces `STOP`.
- **Rule 2 (High-Value Gate)**: Payments $\ge$ ₹20,000 are automatically gated for merchant sign-off in the Approval Queue.
- **Rule 3 (Repeated Failure Cap)**: Chronic failure histories ($\ge 3$ prior declines) trigger `STOP`.
- **Rule 4 (Minimum Probability Floor)**: If predicted recovery probability $< 25\%$ $\rightarrow$ forced `STOP`.
- **Rule 5 (Cooldown Window)**: Prevents rapid back-to-back retries within a 30-second window.
- **Rule 6 (Risky Action Escalation)**: High-risk assessments gate for human operator verification.
- **Rule 7 (100% Immutable Audit Logging)**: Every rule check produces an explainable checklist stored in the database.

### 💳 Razorpay Test Mode & Simulation Abstraction
- Clean abstraction implemented in `RazorpayService`.
- Authenticates against official Razorpay APIs when `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` are configured in `.env`.
- Automatically activates **SIMULATION MODE** when credentials are unset, ensuring 100% uptime for demos.
- **Strict Security**: Secrets are **never exposed to the frontend** and **real money is never used**.

### 🤖 Explainable AI Reasoning Layer
- Structured Pydantic v2 validation schema (`AIAgentRecommendation`).
- Analyzes customer lifetime value, historical success rates, and retry counts.
- Built-in heuristic domain fallback guaranteeing 100% uptime even if external LLM APIs fail.

---

## 5. Recovery Playground: 6 Preset Scenarios

| Scenario | Amount | Failure Reason | Customer Context | Action | Outcome |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Temporary UPI Failure** | **₹4,999** | `UPI_TIMEOUT` | 8 success / 1 fail (₹39,992 LTV) | `RETRY_PAYMENT` | **₹4,999 Recovered** (91% Prob) |
| **2. Bank Decline** | **₹2,499** | `BANK_DECLINED` | 6 success / 2 fail (₹14,994 LTV) | `ALTERNATIVE_PAYMENT_METHOD` | Smart Payment Link Sent |
| **3. Gateway Network Drop** | **₹999** | `NETWORK_ERROR` | 3 success / 0 fail (₹2,997 LTV) | `RETRY_PAYMENT` | **₹999 Recovered** (88% Prob) |
| **4. Insufficient Funds** | **₹14,999** | `INSUFFICIENT_FUNDS` | 4 success / 1 fail (₹59,996 LTV) | `PAYMENT_LINK` | Scheduled Link Dispatched |
| **5. Repeated Failure Cap** | **₹4,999** | `BANK_DECLINED` | 2 prior failed retries | `STOP` | **Policy Halted** (2-Retry Limit) |
| **6. High-Value Payment** | **₹49,999** | `BANK_DECLINED` | Enterprise client | `HUMAN_ESCALATION` | **Gated for Approval Queue** |

---

## 6. Dynamic Fintech Dashboard Metrics

All metrics are computed dynamically in real-time from database records:
- **Revenue at Risk**: $\sum \text{failed transaction amounts}$
- **Revenue Recovered**: $\sum \text{successful recovery amounts}$
- **Recovery Rate**: $\frac{\text{Revenue Recovered}}{\text{Revenue at Risk} + \text{Revenue Recovered}} \times 100$
- **5 Dynamic Recharts Graphs**:
  1. *Revenue at Risk vs Recovered (7-Day Area Trend)*
  2. *Failure Reasons Distribution (Bar Chart)*
  3. *Recovery Actions Recommended (Bar Chart)*
  4. *Recovery Status Outcomes (Status Chart)*
  5. *7-Day Recovery Rate Trend (%)*

---

## 7. Environment Variables

Create `.env` in `backend/` based on `.env.example`:

| Variable | Description | Default / Example |
| :--- | :--- | :--- |
| `RAZORPAY_KEY_ID` | Razorpay Test Mode Key ID | `rzp_test_...` (optional) |
| `RAZORPAY_KEY_SECRET`| Razorpay Test Mode Key Secret | `secret_...` (optional) |
| `DATABASE_URL` | SQLite database URI | `sqlite:///./recoveriq.db` |
| `ENVIRONMENT` | Application mode | `development` |
| `PORT` | FastAPI backend port | `8000` |
| `LLM_PROVIDER` | AI provider (`gemini` / `openai`) | `gemini` |
| `GEMINI_API_KEY` | Optional Gemini API Key | `""` (fallback engine used if empty) |

---

## 8. Quick Start & Setup Instructions

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm

### 1. Backend Setup
```bash
cd backend
python -m venv ../venv
../venv/Scripts/pip install -r requirements.txt
cp .env.example .env

# Run FastAPI backend server
../venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- API Base URL: `http://127.0.0.1:8000`
- Interactive Swagger Docs: `http://127.0.0.1:8000/docs`

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
- Web Application: `http://127.0.0.1:5173`

---

## 9. Running Automated Tests

Run the complete backend test suite covering all 11 test modules:
```bash
cd backend
../venv/Scripts/python -m pytest -v tests
```
*All 48 unit, integration, policy guardrail, simulation, and scenario tests execute in < 2s.*

---

## 10. Known Limitations & Future Improvements

### Known Limitations
1. **Test Mode Operation**: Uses Razorpay Test Mode orders and payment links; cannot capture live real-money credit card networks.
2. **Synchronous Polling for Links**: Payment link completions are verified on-demand or simulated rather than listening on external public webhooks.

### Future Improvements
1. **NPCI UPI AutoPay Integration**: Smart mandate retrying for recurring subscription failures.
2. **WhatsApp Interactive Recovery**: Send conversational UPI pay buttons directly via Razorpay WhatsApp API.
3. **Multi-Merchant Partitioning**: Multi-tenant database schemas for SaaS payment platforms.
