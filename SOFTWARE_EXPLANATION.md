# Finance Health Analyzer — Current Software Explanation

## 1. Project Overview

Finance Health Analyzer is a full-stack personal finance application that converts PDF bank statements into a structured transaction ledger, categorized spending data, financial analytics, and plain-language financial insights.

The system is designed for individuals who want to understand their money without manually cleaning statement rows in spreadsheets. A user uploads a statement, reviews the extracted transactions, confirms the import, corrects uncertain categories, and then explores monthly dashboards, category and merchant analytics, recurring subscriptions, friend-related transactions, a financial health score, and AI-assisted explanations.

The application deliberately separates calculation from explanation:

- deterministic backend code calculates balances, income, expenses, savings, trends, subscriptions, and health scores;
- machine learning assists transaction categorization;
- the LLM receives already-calculated financial context and explains it in readable language;
- a deterministic fallback keeps insights available when external AI providers fail.

## 2. What the System Actually Supports

### Supported input

- PDF bank statements
- Maximum file size: 10 MB
- Files must contain a valid PDF signature

CSV and Excel imports are not part of the current implementation.

### Main user-facing areas

- Authentication
- Statement upload and preview
- Transactions
- Category review
- Dashboard
- Category and merchant analytics
- Friends
- AI Insights

## 3. End-to-End System Flow

```text
Register or log in
        ↓
Upload a PDF bank statement
        ↓
Validate and parse the statement
        ↓
Clean transaction fields and extract merchants
        ↓
Suggest categories with rules and per-user ML
        ↓
Preview extracted rows and balances
        ↓
Confirm the import
        ↓
Skip exact duplicate transactions and save valid rows
        ↓
Review uncertain categories and save corrections
        ↓
Use learned corrections for future categorization
        ↓
Generate dashboards, analytics, health scores, and AI explanations
```

## 4. Authentication and User Isolation

The backend provides registration, login, token refresh, logout, and current-user endpoints. Passwords are hashed, and authenticated requests use JWT access tokens. Protected backend queries include the authenticated `user_id`, which keeps transactions, uploaded files, corrections, learned rules, friends, analytics, and insights isolated per account.

The React application protects private routes and uses one centralized Axios client. The client reads `VITE_API_BASE_URL`, attaches the stored access token to requests, and avoids hardcoded production API addresses throughout feature components. The backend exposes a refresh-token endpoint, while the current Axios interceptor only handles request authorization and does not automatically refresh a rejected request.

## 5. Statement Upload and Processing

### Upload preview

The frontend sends the selected PDF to:

```text
POST /uploads/preview
```

The backend:

1. validates the extension, file size, and PDF signature;
2. parses statement text and transaction rows with `pdfplumber`;
3. extracts dates, descriptions, reference numbers, withdrawals, deposits, balances, types, and amounts;
4. cleans descriptions and merchant names;
5. runs transaction categorization for preview rows;
6. returns opening and closing balances, successful rows, failed rows, and row-level errors.

Nothing is permanently stored during preview.

### Upload confirmation

After the user reviews the preview, the frontend sends the accepted rows to:

```text
POST /uploads/confirm
```

The backend creates an upload-history record and saves the transactions. Before saving a row, it checks the current user's existing data using the transaction date, amount, description, and reference number. Matching rows are skipped as duplicates.

Each saved transaction stores its category, confidence, categorization method, review state, extracted merchant, source file, and bank-statement values. The upload history shows saved statement metadata and can delete an uploaded statement together with its linked transactions.

## 6. Transaction Categorization Engine

The categorization engine is hybrid. It does not rely on one model or one confidence score.

### Categorization order

```text
Transaction description and merchant
        ↓
Exact user-learned merchant rule
        ↓
Fuzzy user-learned merchant rule
        ↓
Built-in keyword rules
        ↓
Per-user TF-IDF + Logistic Regression model
        ↓
Auto-assign or send to Needs Review
```

### Layer 1: learned merchant rules

When a user corrects a category, the backend stores a user-specific learning rule for the normalized merchant. Future transactions from the same merchant can reuse that category. Exact matches are preferred; RapidFuzz supports close matching for small merchant-name variations.

Learned rules carry usage and confidence metadata and can be listed, edited, or deleted through the category API.

### Layer 2: keyword rules

The backend contains category keyword sets for common descriptions such as food, transport, subscriptions, shopping, healthcare, education, savings, investments, refunds, and income. A matching keyword creates a rule-based suggestion.

### Layer 3: per-user machine learning

The machine-learning pipeline is:

```text
Transaction description
        ↓
TF-IDF vectorization with unigrams and bigrams
        ↓
Logistic Regression classifier
        ↓
Predicted category and probability
```

The model is user-specific. Training data comes from that user's category corrections and other sufficiently confident manual, learned, or rule-based transactions. At least 20 labeled rows are required before training. Trained models are persisted with Joblib under the backend ML model directory and are invalidated after a correction so the next prediction uses the latest labels.

The training function is cached by the labeled-data signature. If the same user has the same training rows, the fitted state can be reused instead of recomputed within the running process.

### Confidence and review behavior

- ML predictions at or above 0.80 may be assigned automatically.
- Lower-confidence predictions are not presented as certain results.
- Uncertain rows enter the Needs Review flow with an optional suggested category.
- A manual correction sets the selected category as the accepted answer, records correction history, creates or updates the learned merchant rule, and invalidates the user's old model.
- The review page supports individual corrections and bulk saving.

### Learning Accuracy

The Review Categories page measures model quality with manual corrections as ground truth. It does not average stored confidence values.

The backend:

1. takes the newest manual correction for each normalized corrected description;
2. requires at least 20 corrections and at least two categories;
3. splits the correction data into training and held-out test sets with a fixed random seed;
4. trains TF-IDF + Logistic Regression on the training portion;
5. compares predictions with the user's actual categories on the held-out portion;
6. returns the proportion predicted correctly.

This score answers: “How often does the learned classifier reproduce the user's category choices on examples it was not trained on?” It is separate from a prediction's confidence.

## 7. Transactions and Category Review

The Transactions page reads the authenticated user's ledger and supports filtering, inspection, editing, category correction, and deletion. Category badges use a centralized display mapping so category colors remain consistent across the application.

The Review Categories page focuses on transactions marked for review. Users can:

- search by description or merchant;
- include or exclude already learned transactions;
- sort the list;
- select rows;
- choose a category;
- save corrections individually or in bulk;
- view Learning Accuracy when enough correction data exists.

Corrections update both the transaction and the user's future categorization behavior.

## 8. Friends Feature

Friends remains both a transaction category and a tracking feature in the current system.

When a transaction is categorized as Friends, the backend extracts and normalizes a person-like merchant name, creates or updates the friend record, and links the transaction. The friend-learning table stores normalized merchant/person patterns so later matching transactions can be attached automatically.

The Friends page provides:

- friend creation;
- friend list and aggregate dashboard data;
- per-friend details and linked transactions;
- friend renaming;
- hiding/deleting a friend record;
- totals, transaction counts, and recent activity.

Friend linking does not replace transaction categorization. The transaction remains in the ledger and retains its category while also being connected to the appropriate friend record.

## 9. Deterministic Financial Analytics

The analytics layer reads the authenticated user's categorized transactions for a selected month and year. It is the source of truth for every financial number shown to the user.

### Dashboard summary

The dashboard calculates and displays:

- opening balance;
- total income;
- total expenses;
- closing balance;
- available funds;
- savings and investments allocation;
- savings rate;
- lifestyle expenses;
- current balance where available;
- highest-spending category;
- month-over-month deltas.

The combined dashboard endpoint returns summary data, health data, deterministic insights, savings analytics, category analytics, merchant analytics, subscription analytics, and chart series in one response.

### Category and merchant analytics

The category analytics page groups expense transactions by category and displays:

- the total expense amount;
- category totals and shares;
- a donut chart;
- standalone merchant bar charts for each category;
- merchant amounts and transaction counts through chart interaction.

Category colors come from one canonical frontend palette so the dashboard, category badges, legends, donut chart, and bar-chart modules remain consistent.

### Savings analytics

Savings is treated as intentional allocation into Savings or Investments categories. The system calculates total allocation, allocation rate, and related month comparisons. It does not infer that all unspent money was intentionally saved.

### Subscription analytics

Subscription analytics uses transactions categorized as Subscriptions. The backend groups recurring merchant payments, estimates a monthly amount, stores or updates subscription records, and returns subscription count, monthly cost, annualized cost, confidence, and merchant details.

This is transaction-pattern analysis, not access to a bank's subscription management system.

### Trends and insights

The backend compares current and previous periods to calculate changes in income, expenses, savings, category spending, merchant activity, subscriptions, and balances. Deterministic dashboard insight rules convert those comparisons into factual notices and priorities.

The current application does not implement a general future-balance forecasting model, investment forecasting, or a standalone financial-risk prediction engine.

## 10. Financial Health Score

The health score is deterministic and ranges from 0 to 100. It is the equally weighted average of four component scores:

```text
Overall score =
(Savings rate score
 + Subscription control score
 + Spending stability score
 + Financial balance score) / 4
```

### Savings rate score

Compares transactions categorized as Savings or Investments with available funds. Higher intentional allocation produces a higher component score.

### Subscription control score

Compares detected monthly subscription cost with income. A smaller subscription share produces a higher score. A period with no detected recurring subscription cost receives the strongest component result.

### Spending stability score

Compares current lifestyle spending with available spending history from up to three previous periods. Smaller variation receives a higher score. If history is insufficient, the system returns a neutral middle score and explains that more data is needed.

### Financial balance score

Compares closing balance with available funds and penalizes a zero or negative closing balance. A stronger end-of-period buffer receives a higher score.

The resulting labels are:

- 85–100: Excellent
- 70–84: Good
- 50–69: Average
- below 50: Needs Improvement

The backend stores score snapshots and returns a component breakdown plus deterministic improvement tips.

## 11. AI Financial Insights

The AI layer is an explanation layer, not the financial calculator.

### Verified context

Before contacting an LLM, the backend builds structured context from deterministic services. That context includes:

- summary metrics;
- category and merchant spending;
- savings allocation;
- subscription information;
- current and previous-period trends;
- financial health score and components.

### Provider flow

```text
Verified financial context
        ↓
Structured prompt requesting JSON
        ↓
Gemini, if configured
        ↓ failure or unavailable
Groq, if configured
        ↓ failure, unavailable, or invalid output
Deterministic fallback
```

The prompt requests structured spending, savings, merchant, subscription, and health insight lists. Provider output is validated against a Pydantic schema. Invalid or missing output is discarded and replaced by deterministic content derived from the same verified context.

The result includes the provider used, selected period, generated timestamp, summary, grouped insights, priorities, health score, status, and trend.

The current implementation does not let an LLM invent balances, calculate the health score, or directly modify financial data.

## 12. Frontend Architecture

The frontend is a React 19 single-page application built with Vite. It is organized by feature:

```text
frontend/src/
├── app/                 Application shell, providers, and router
├── components/          Shared layout and UI components
├── features/
│   ├── auth/
│   ├── upload/
│   ├── dashboard/
│   ├── transactions/
│   ├── categories/
│   ├── friends/
│   └── ai-insights/
├── shared/              API client and shared contexts
├── styles/              Global application styles
└── utils/               Category and period display utilities
```

Every major page is loaded with `React.lazy` and rendered through `Suspense`. Protected routes require authentication. Recharts provides the dashboard and category visualizations, Lucide React provides icons, and Axios handles API communication.

## 13. Backend Architecture

The FastAPI backend is organized by responsibility:

```text
backend/app/
├── api/v1/              REST endpoints
├── services/            Categorization, category, learning, and friend logic
├── parsers/             PDF parsing and transaction cleaning
├── analytics/           Dashboard, financial context, and health scoring
├── ai/                  Prompting, providers, validation, and fallbacks
├── ml/                  Per-user categorization model and evaluation
├── db/                  SQLAlchemy session and schema maintenance
├── models/              Database models
├── schemas/             Request and response contracts
├── core/                Authentication and security helpers
└── utils/               Merchant and transaction normalization
```

FastAPI exposes the API, Pydantic validates contracts, SQLAlchemy accesses MySQL, and startup maintenance seeds the category catalog and performs limited schema compatibility checks.

## 14. Database Entities

The current SQLAlchemy model layer contains:

- `users` — accounts and password hashes;
- `transactions` — the cleaned financial ledger;
- `categories` — category catalog;
- `uploaded_files` — upload history and statement metadata;
- `category_corrections` — manual correction history and ML labels;
- `category_learning_rules` — user-specific learned merchant rules;
- `user_learning` — legacy merchant/category fallback data still represented in the model;
- `friends` — user friend records and aggregates;
- `friend_transaction_links` — safe friend-to-transaction links;
- `friend_merchant_learning` — learned friend matching patterns;
- `subscriptions` — detected recurring subscription records;
- `financial_scores` — stored health score snapshots.

The models currently use integer IDs and explicit `user_id` filtering rather than ORM relationship declarations and database-enforced foreign keys throughout.

## 15. REST API Areas

```text
/auth                 Registration, login, refresh, logout, current user
/uploads              PDF preview, confirmation, history, deletion
/transactions         Ledger CRUD and category correction
/categories           Catalog, prediction, review, correction, learning rules, ML evaluation
/dashboard            Summary, analytics, insights, snapshots, and charts
/financial-health     Deterministic score
/friends              Friend CRUD, dashboard, and detail views
/ai/insights          Structured AI financial insights
```

## 16. Technology Stack

| Layer | Current technologies |
| --- | --- |
| Frontend | React 19, Vite 8, React Router 6, Axios, Recharts, Lucide React |
| Backend | Python, FastAPI, Uvicorn, Pydantic, SQLAlchemy |
| Database | MySQL through PyMySQL |
| PDF processing | pdfplumber |
| Fuzzy matching | RapidFuzz |
| Machine learning | scikit-learn TF-IDF and Logistic Regression, Joblib persistence |
| AI providers | Gemini first, Groq fallback, deterministic local fallback |
| Security | JWT access/refresh tokens, password hashing, protected routes, CORS allowlist |
| Deployment configuration | Vercel frontend; Railway backend and MySQL |

## 17. Reliability and Performance Decisions

### Upload safety

- validates PDFs before parsing;
- previews data before persistence;
- reports failed rows;
- skips matching duplicates during confirmation;
- scopes upload history to the current user.

### Categorization reliability

- combines deterministic rules with probabilistic ML;
- requires confidence before automatic assignment;
- keeps uncertain predictions in human review;
- stores user corrections as future learning data;
- measures Learning Accuracy against held-out manual corrections.

### AI reliability

- calculates financial data before calling the LLM;
- validates structured provider output;
- falls back from Gemini to Groq;
- returns deterministic insights if both providers are unavailable or invalid.

### Frontend performance

- lazy-loads major routes;
- retrieves combined dashboard data through a shared API client;
- uses safe empty values before rendering charts;
- centralizes authorization headers and deployment base URL handling.

### Current scaling limitation

The API and database layers are separated, but persisted ML models are stored on the backend filesystem. A horizontally scaled deployment would need shared object storage or another shared model store so all backend instances use the same persisted user model.

## 18. Accurate Recruiter Explanation

> Finance Health Analyzer is a full-stack React, FastAPI, and MySQL application that turns PDF bank statements into an authenticated financial workspace. It validates and previews statement rows, prevents duplicate imports, categorizes transactions through user-learned merchant rules, keyword and fuzzy matching, and a per-user TF-IDF plus Logistic Regression model. Deterministic services calculate monthly analytics, recurring subscriptions, and a four-part financial health score. Gemini or Groq then explains that verified context through validated structured output, with a deterministic fallback when AI is unavailable.

## 19. What the Project Demonstrates

- full-stack SPA and REST API development;
- authentication and per-user data isolation;
- PDF extraction and transaction normalization;
- hybrid rules and machine-learning classification;
- human-in-the-loop correction and learning;
- deterministic financial analytics;
- interactive data visualization;
- structured LLM integration with provider fallback;
- environment-based frontend/backend deployment configuration;
- feature-based frontend and responsibility-based backend organization.

## 20. Important Boundaries

To describe the project accurately, do not claim that it currently provides:

- CSV or Excel statement imports;
- direct Open Banking synchronization;
- real-time bank account access;
- autonomous financial decisions or money movement;
- investment portfolio management;
- predictive future-balance forecasting;
- a standalone risk-prediction model;
- universally shared ML learning across users;
- guaranteed financial advice.

The application is a personal financial analysis and explanation tool. Its outputs depend on the transactions supplied and the categories confirmed by the user.
