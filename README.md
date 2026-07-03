# AI-Powered Personal Finance Analyzer

A React and FastAPI personal-finance analyzer with statement imports, transaction categorization, dashboard analytics, friend tracking, financial health scoring, and AI-generated insights.

## Structure

```text
backend/
  app/
    routes/       FastAPI route modules
    services/     Domain workflows and persistence services
    parsers/      Statement parsing and transaction normalization
    analytics/    Financial calculations, reporting, and health scoring
    ai/           LLM client, prompts, validation, and insight orchestration
    ml/           User-specific categorization model support
    database/     SQLAlchemy connection and schema maintenance
    models/       SQLAlchemy models
    schemas/      Pydantic request and response schemas
    utils/        Shared merchant and transaction utilities
    core/         Authentication and security utilities
frontend/
  src/
    features/     Feature-owned pages and styles
    components/   Shared UI and layout components
    context/      React context providers
    hooks/        Shared React hooks
    services/     API client
    utils/        Shared display and period utilities
    styles/       Global application styles
```

## Run the backend

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

## Run the frontend

```powershell
cd frontend
npm install
npm run dev
```

## Verification

```powershell
cd frontend
npm run lint
npm run build
```

The backend API documentation is available at `http://127.0.0.1:8000/docs` while the server is running.
