# Project cleanup report

## Summary

- Removed 10,702 lines and added 1,807 lockfile/formatting lines across the cleanup diff.
- Removed 648 dead rules from `App.css` plus dead rules from page and component styles.
- Reduced the built shared CSS bundle from 159.00 kB to 87.53 kB.
- Preserved current application pages, data flows, charts, authentication, uploads, categorization, friends, dashboard analytics, and Feature 3 AI insights.

## Files deleted

### Backend

- `backend/app/ai/llm_client.py`
- `backend/app/api/merchants.py`
- `backend/app/services/ai_categorization_service.py`
- `backend/app/services/categorization_service.py`
- `backend/app/services/merchant_service.py`
- `backend/app/services/spending_insights.py`
- `backend/tests/__init__.py`
- `backend/tests/test_feature2_analytics.py`
- `backend/tests/test_feature3_ai_insights.py`
- `backend/tests/test_pdf_upload.py`
- `backend/tests/test_transaction_types.py`

### Frontend

- `frontend/src/components/CategoryDropdown.jsx`
- `frontend/src/components/SummaryCard.jsx`
- `frontend/src/styles/CategoryDropdown.css`
- `frontend/src/styles/FinancialHealth.css`
- `frontend/README.md`

### Root artifacts and obsolete setup files

- `AUTHENTICATION_SETUP.md`
- `agent.md`
- `requirements.txt`
- `package.json`
- `package-lock.json`
- `design-qa.md`
- `design-qa-friends-desktop.png`
- `design-qa-friends-mobile.png`
- `ai-insights-final-comparison.png`
- `ai-insights-final-qa.png`
- `ai-insights-restored.png`
- `ai-insights-v2-comparison.png`
- `ai-insights-v2-final.png`
- `ai-insights-v2-focused-comparison.png`
- `ai-insights-v2-qa.png`

## Files modified

- `.github/workflows/ci-cd.yml`
- `backend/app/api/categories.py`
- `backend/app/api/friends.py`
- `backend/app/api/transactions.py`
- `backend/app/api/uploads.py`
- `backend/app/db/schema_maintenance.py`
- `backend/app/main.py`
- `backend/app/models/models.py`
- `backend/app/schemas/schemas.py`
- `backend/app/services/categorization.py`
- `backend/app/services/financial_analytics_service.py`
- `backend/app/services/friend_service.py`
- `backend/app/services/learning_service.py`
- `backend/app/services/ml_categorization_service.py`
- `backend/app/services/transaction_cleaner_service.py`
- `backend/requirements.txt`
- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/vite.config.js`
- `frontend/src/App.jsx`
- `frontend/src/App.css`
- `frontend/src/pages/AIInsights.css`
- `frontend/src/pages/Dashboard.css`
- `frontend/src/styles/Navigation.css`
- `frontend/src/styles/UploadStatement.css`

## Database changes

- Removed the unused `merchants` model and dropped the physical `merchants` table after confirming zero incoming/outgoing foreign keys. The table contained 131 legacy rows.
- Removed the unused `AiInsight` model and dropped the physical `ai_insights` table after confirming zero incoming/outgoing foreign keys. The table contained 223 legacy rows.
- Removed the obsolete `merchants.total_spent` schema-maintenance rule.
- No active table, column, relationship, or index was changed.

## Code removed

### Services and AI

- Legacy generic `LLMClient` replaced by the active Feature 3 `InsightsLLMService` flow.
- Legacy stored spending-insight generator and persistence flow.
- Unreachable merchant-directory service and API.
- Unused AI categorization wrapper and categorization compatibility wrapper.
- Unused helper functions: `predict_category_name`, `get_predicted_category_id`, `get_user_learning_rules`, `get_model_confidence`, and `parse_date`.

### Schemas and models

- Merchant directory request/response schemas.
- Legacy stored AI insight response schemas.
- Unused `TokenData` and `DashboardMetric` schemas.
- Unused `Merchant` and `AiInsight` SQLAlchemy models.

### Routes

- Unreachable merchant API module.
- Duplicate trailing-slash category, friend, and transaction decorators.
- Duplicate singular `/upload/*` aliases; active `/uploads/*` routes remain.
- Obsolete frontend redirect aliases for merchants, needs-review, category-breakdown, financial-health, and insights.
- Duplicate import-time database seeding; startup seeding remains.

### Frontend and CSS

- Unused `CategoryDropdown` and `SummaryCard` components.
- Unused Financial Health and Category Dropdown stylesheets.
- 648 dead `App.css` rules and additional selectors proven absent from React source.
- Preserved dynamic `tone-*`, `metric-format-*`, `method-*`, toast, number-animation, and Recharts runtime selectors.

### Dependencies and configuration

- Removed unused frontend `framer-motion`, Tailwind, and Tailwind Vite packages.
- Removed unused backend Alembic, aiofiles, and OpenAI packages.
- Removed redundant root Node and Python manifests.
- Updated CI to install `backend/requirements.txt` directly.

## Verification

- Before deletion: 29 backend unit tests passed.
- After each backend/frontend pass: the same 29 backend tests passed until the requested test-suite removal.
- Frontend ESLint passed.
- Frontend production build passed with Vite.
- 47 remaining backend Python modules parsed successfully.
- Backend imported successfully and registered 58 FastAPI/Starlette routes.
- Backend restarted successfully; `/categories` returned HTTP 200.
- OpenAPI retained `/dashboard`, `/dashboard/category-merchants`, `/ai/insights`, and `/uploads/preview`.
- OpenAPI no longer exposes unreachable `/merchants` or legacy `/upload/preview`.
- Frontend routes `/dashboard`, `/transactions`, `/categories`, `/dashboard/category-analytics`, `/friends`, `/ai-insights`, and `/upload` each returned HTTP 200.
- `git diff --check` reported no whitespace errors.

## Verification limits

- The test suite was intentionally removed only after its final successful 29-test run, per the cleanup request.
- The Product Design baseline contains one accepted Dashboard screenshot; further in-app Browser captures timed out and were rejected.
