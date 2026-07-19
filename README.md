# Finance Health Analyzer

## Project Overview

Finance Health Analyzer is a full-stack personal finance application for turning PDF bank statements into understandable financial reports. It is designed for users who want a faster way to review transactions, spending patterns, merchants, savings allocation, subscriptions, and money exchanged with friends. The system previews and cleans statement data, categorizes transactions through rules and machine learning, calculates verified financial metrics, and uses an LLM only to explain those metrics in plain language.

## Problem Statement

Personal finance reviews often require manually copying statement rows into spreadsheets, cleaning descriptions, assigning categories, and rebuilding the same calculations every month. Banking apps usually show balances and transactions but provide limited context about spending changes or what deserves attention. Inconsistent merchant descriptions also make reliable categorization difficult. Finance Health Analyzer automates statement processing, preserves a review step for uncertain predictions, and learns from user corrections. Deterministic analytics remain the source of truth for balances, trends, subscriptions, and health scores, while AI converts verified results into concise explanations rather than performing financial calculations.

## Features

- JWT-based registration, login, refresh, logout, and protected user data
- PDF bank statement validation, parsing, preview, confirmation, upload history, and duplicate detection
- Hybrid transaction categorization using learned merchant rules, keyword matching, fuzzy similarity, and a per-user TF-IDF + Logistic Regression classifier
- Confidence-based automatic assignment, needs-review queues, manual and bulk corrections, and model retraining
- Monthly dashboard metrics for income, expenses, balances, savings allocation, categories, merchants, and trends
- Category and merchant breakdowns with interactive Recharts visualizations
- Deterministic financial health scoring across savings rate, subscription control, spending stability, and financial balance
- Recurring-subscription detection and month-over-month financial insights
- Friend tracking with learned transaction matching and per-friend summaries
- AI-generated financial explanations using Gemini, Groq, and a deterministic fallback

## Architecture

### High-Level Architecture

```mermaid
flowchart LR
    U["User"] --> F["React + Vite SPA"]
    F -->|"JWT-authenticated REST requests"| A["FastAPI API"]
    A --> P["PDF parsing and normalization"]
    A --> C["Hybrid categorization pipeline"]
    A --> N["Deterministic analytics and health scoring"]
    A --> D[("MySQL")]
    C --> M["Per-user TF-IDF + Logistic Regression model"]
    N --> I["Verified financial context"]
    I --> L["Gemini, then Groq, then deterministic fallback"]
    D --> A
    A --> F
```

The backend is organized by responsibility under `backend/app`: API routes, services, parsers, analytics, AI orchestration, ML, database access, models, schemas, security, and utilities. The frontend is organized by feature under `frontend/src/features`, with shared layout, UI, context, and API-client modules.

### Statement Upload and Processing

```mermaid
sequenceDiagram
    actor User
    participant UI as React UI
    participant API as FastAPI
    participant Parser as PDF Parser
    participant DB as MySQL

    User->>UI: Select PDF statement
    UI->>API: POST /uploads/preview
    API->>Parser: Validate, extract, clean, and categorize rows
    Parser-->>API: Preview rows, balances, failures, and mapping
    API-->>UI: Reviewable preview
    User->>UI: Confirm import
    UI->>API: POST /uploads/confirm
    API->>DB: Skip duplicates and save transactions
    API-->>UI: Saved and skipped counts
```

### Transaction Categorization

```mermaid
sequenceDiagram
    participant API as FastAPI
    participant Rules as Categorization Service
    participant ML as Per-user ML Model
    participant DB as MySQL

    API->>Rules: Categorize description and merchant
    Rules->>DB: Check exact and fuzzy learned merchant rules
    alt Learned or keyword rule is confident
        Rules-->>API: Category and confidence
    else Rules are insufficient
        Rules->>ML: Predict with TF-IDF and Logistic Regression
        ML-->>Rules: Category probability
        Rules-->>API: Auto-assign at 0.80 or mark needs review
    end
    API->>DB: Store category, method, confidence, and review state
```

### Financial Health Score Generation

```mermaid
sequenceDiagram
    participant UI as React UI
    participant API as FastAPI
    participant Analytics as Analytics Engine
    participant DB as MySQL

    UI->>API: Request score for month and year
    API->>Analytics: Calculate financial health
    Analytics->>DB: Read current and previous transaction periods
    Analytics->>Analytics: Score savings, subscriptions, stability, and balance
    Analytics->>DB: Save score snapshot
    Analytics-->>API: Score, breakdown, status, and improvement tips
    API-->>UI: Render verified health report
```

### AI Financial Insights Flow

```mermaid
sequenceDiagram
    participant UI as React UI
    participant API as FastAPI
    participant Analytics as Analytics Engine
    participant LLM as Gemini or Groq

    UI->>API: GET /ai/insights with month and year
    API->>Analytics: Build verified financial context
    Analytics-->>API: Metrics, trends, merchants, subscriptions, and score
    API->>LLM: Request structured JSON explanation
    alt Provider output is valid
        LLM-->>API: Structured insights
    else Provider is unavailable or invalid
        API->>API: Generate deterministic fallback insights
    end
    API-->>UI: Summary, insight groups, and priorities
```

## Tech Stack

| Layer | Technologies |
| --- | --- |
| Frontend | React 19, Vite 8, React Router, Axios, Recharts, Lucide React |
| Backend | Python, FastAPI, SQLAlchemy, Pydantic, Uvicorn |
| Database | MySQL with PyMySQL |
| Data processing | pdfplumber, RapidFuzz |
| Machine learning | scikit-learn TF-IDF, Logistic Regression, Joblib model persistence |
| AI | Gemini API, Groq API, validated structured output, deterministic fallback |
| Security | JWT access/refresh tokens, PBKDF2-SHA256 password hashing, per-user query isolation, CORS allowlist |
| Deployment | Vercel frontend, Railway backend and MySQL |

## Local Development

### Prerequisites

- Python 3.10+
- Node.js and npm
- MySQL 8+

### Setup

```bash
git clone https://github.com/aimanrazadev/Finance-Health-Analyzer.git
cd Finance-Health-Analyzer
```

Create `backend/.env`:

```env
DATABASE_URL=mysql+pymysql://USER:PASSWORD@localhost:3306/finance_analyzer
SECRET_KEY=replace-with-a-long-random-secret
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Optional AI providers; deterministic insights work without these keys
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
GROQ_API_KEY=
GROQ_MODEL=llama-3.3-70b-versatile
```

Run the backend:

```bash
cd backend
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

Run the frontend in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

The application runs at `http://localhost:5173`; FastAPI documentation is available at `http://localhost:8000/docs`. The frontend uses `http://localhost:8000` by default. For another backend address, set `VITE_API_BASE_URL` before building or starting Vite.

## Non-Functional Requirements

- **Performance:** lazy-loaded React routes, cached ML training signatures, persisted user models, and SQLAlchemy connection health checks
- **Security:** hashed passwords, expiring JWT access and refresh tokens, authenticated protected routes, user-scoped database queries, and environment-based secrets
- **Scalability:** stateless REST endpoints and separated frontend, API, database, analytics, and ML responsibilities; persisted model files currently require shared storage for horizontal backend scaling
- **Reliability:** upload preview before persistence, duplicate transaction checks, confidence-based human review, deterministic financial calculations, and deterministic AI fallback behavior
- **Maintainability:** feature-based frontend modules, responsibility-based backend modules, centralized Axios configuration, typed Pydantic contracts, and isolated analytics services

## Future Improvements

- Containerize the frontend, backend, and database with Docker Compose
- Add Redis caching and background jobs for expensive analytics and model retraining
- Move persisted ML models to shared object storage for multi-instance deployments
- Add automated backend, frontend, parser, and end-to-end test coverage
- Integrate Open Banking APIs for consent-based transaction synchronization
- Add investment portfolio analytics and configurable financial goals
- Add multi-model routing, provider observability, and AI cost controls
- Add Kubernetes deployment only if traffic and operational requirements justify it
