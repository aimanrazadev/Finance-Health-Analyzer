# UML Diagrams - AI-Powered Personal Finance Analyzer

## Overview
This directory contains comprehensive PlantUML diagrams documenting the complete system architecture for the AI-Powered Personal Finance Analyzer application. The diagrams cover use cases, database schema, class relationships, and detailed interaction sequences.

## Diagram Index

### 1. System Scope & Use Cases

#### 01_Main_UseCase_SystemScope.puml
**Purpose:** High-level system overview showing all 11 main use cases and external systems
- Shows the entire system boundary
- Lists all 11 key features/use cases
- Identifies external actors (User, AI Systems, Payment Gateways)
- Indicates external systems (Banks, LLM APIs)

### 2. Use Case Diagrams (Detailed)

#### 02_UC01_Authentication.puml
**Features:** User registration, login, logout, token verification, protected routes
- Registration with email/password
- Login with credentials and JWT token generation
- Session management and token refresh
- Logout functionality

#### 03_UC02_TransactionManagement.puml
**Features:** Manual transaction entry, CRUD operations, filtering, searching
- Add transactions with auto-categorization
- View all transactions with pagination
- Filter by category, date range, type
- Search transactions
- Edit and delete transactions

#### 04_UC03_StatementUpload.puml
**Features:** CSV/Excel bank statement import, parsing, bulk transaction creation
- File selection and preview
- Data validation and cleaning
- Automatic categorization
- Bulk insertion into database
- Upload history tracking

#### 05_UC04_ExpenseCategorization.puml
**Features:** Three-level categorization (rule-based → learning → AI)
- Level 1: Rule-based keyword matching
- Level 2: User learning and correction
- Level 3: AI fallback using LLM APIs
- Batch categorization for imports
- Cost optimization strategies

#### 06_UC05_DashboardReports.puml
**Features:** Summary cards, analytics, charts, reports, exports
- Total spending summary cards
- Pie chart by category
- Bar chart for top merchants
- Line chart for spending trends
- Monthly report generation
- PDF and CSV export

#### 07_UC06_AiSpendingInsights.puml
**Features:** Analytics, anomaly detection, LLM-powered insights
- Spending pattern analysis
- Month-on-month comparison
- Anomaly detection
- AI-generated insights and recommendations
- Savings opportunities identification

#### 08_UC07_BudgetManagement.puml
**Features:** Budget creation, tracking, alerts, AI recommendations
- Create and manage budgets by category
- Track spending vs budget in real-time
- Automatic alerts at thresholds
- AI-powered budget recommendations
- Budget history and adjustments

#### 09_UC08_ExpenseForecasting.puml
**Features:** Machine learning-based expense predictions
- Feature engineering from historical data
- Model training (Linear Regression, Random Forest, Gradient Boosting)
- Future predictions with confidence intervals
- Seasonal pattern detection
- Monthly model retraining

#### 10_UC09_SavingsGoals.puml
**Features:** Savings goal tracking with timeline and AI acceleration
- Create savings goals with deadlines
- Track progress vs milestones
- Calculate required daily/weekly/monthly savings
- AI-powered acceleration tips
- Goal completion tracking

#### 11_UC10_FinancialHealthScore.puml
**Features:** Comprehensive financial health scoring system
- 5 scoring components:
  * Savings rate (25% weight)
  * Budget control (20% weight)
  * Spending stability (20% weight)
  * Debt management (20% weight)
  * Emergency fund adequacy (15% weight)
- Overall score (0-100) with letter grade (A-F)
- Trend analysis and recommendations

#### 12_UC11_AiFinanceChatbot.puml
**Features:** Conversational AI assistant for financial queries
- Intent recognition and classification
- Multi-turn conversation with context
- Relevant data fetching for responses
- LLM-powered response generation
- Quick action buttons for common tasks
- Chat history and export

### 3. Data Model

#### 13_ER_Diagram.puml
**Purpose:** Entity-Relationship diagram showing database schema
- 12 core entities:
  * users
  * transactions
  * categories
  * budgets
  * savings_goals
  * ai_insights
  * forecast_results
  * financial_scores
  * chat_history
  * uploaded_files
  * user_learning
  * recurring_transactions
- Primary/foreign key relationships
- Field definitions and data types
- Cardinality indicators

### 4. Application Design

#### 14_Class_Diagram.puml
**Purpose:** Object-oriented design showing backend classes and services
- Services layer (11+ service classes)
- Repository/DAO pattern for data access
- Pydantic models for validation
- Authentication manager
- Categorization engine
- Analytics and forecasting services
- LLM integration handler

### 5. Sequence Diagrams (Interaction Flows)

#### 15_Seq01_Authentication.puml
**Shows:** Complete authentication workflow
- Registration: form → validation → password hashing → DB insert
- Login: credentials → verification → JWT token generation
- Protected route access: token validation → auto-refresh
- Logout: token invalidation → session cleanup

**Key Actors:** User, Frontend, Backend, JWT Manager, Database, Password Hasher

#### 16_Seq02_TransactionManagement.puml
**Shows:** Transaction lifecycle and operations
- Add manual transaction with auto-categorization suggestion
- View and paginate all transactions
- Filter by category, date range, type
- Search functionality
- Edit and update transactions
- Delete with confirmation

**Key Actors:** User, Frontend, Backend, Categorization Service, Database

#### 17_Seq03_StatementUpload.puml
**Shows:** Bank statement import and processing
- File selection and validation
- Preview parsing results
- Data cleaning: duplicates, nulls, dates, normalization
- Auto-categorization of imported transactions
- Bulk database insertion
- Upload history tracking
- Error handling

**Key Actors:** User, Frontend, Backend, File Parser, Data Cleaner, Categorizer, Database

#### 18_Seq04_ExpenseCategorization.puml
**Shows:** Three-tier categorization system
- Level 1: Rule-based keyword matching (80% accuracy, free)
- Level 2: User learning database (15% accuracy, cached)
- Level 3: AI fallback via LLM (5% accuracy, paid)
- User correction feedback and learning
- Performance optimization and cost reduction
- Batch processing for efficiency

**Key Actors:** Frontend, Backend, Rule Engine, User Learning DB, LLM API, MySQL DB

#### 19_Seq05_DashboardReports.puml
**Shows:** Dashboard data loading and visualization
- Load summary cards (total spent, budget status, savings, health score)
- Generate expense breakdown pie chart by category
- Create bar chart of top merchants
- Generate line chart for 6-month trend
- Create monthly reports with metrics
- Export to PDF and CSV formats

**Key Actors:** User, Frontend, Backend, Analytics Engine, MySQL DB, Recharts

#### 20_Seq06_AiSpendingInsights.puml
**Shows:** AI-powered analytics and recommendations
- Fetch user transaction and budget data
- Calculate spending metrics and patterns
- Month-on-month comparison with percentage changes
- Anomaly detection using statistical methods (z-score)
- LLM prompt construction with metrics
- AI insight generation
- Savings recommendations and optimization tips

**Key Actors:** Frontend, Backend, Analytics Engine, LLM API, MySQL DB

#### 21_Seq07_BudgetManagement.puml
**Shows:** Budget creation and lifecycle
- Create budget with category, amount, period, alert threshold
- View all budgets with current spending status
- Track spending against budgets in real-time
- Trigger alerts when thresholds exceeded
- Email/in-app/push notifications
- Edit budget parameters
- AI-powered budget recommendations based on history
- Delete budgets

**Key Actors:** User, Frontend, Backend, Budget Service, Notification Service, Database

#### 22_Seq08_ExpenseForecasting.puml
**Shows:** Machine learning-based prediction pipeline
- Request forecast for specific category and time period
- Feature engineering: temporal, lag, rolling statistics, seasonality
- Model training using Random Forest (100 trees)
- Test set evaluation with accuracy metrics
- Generate future predictions with confidence intervals
- Widen confidence intervals for further predictions
- Display forecast chart with historical + predicted data
- Monthly model retraining with new data

**Key Actors:** Frontend, Backend, Feature Engineering, ML Model, MySQL DB

#### 23_Seq09_SavingsGoals.puml
**Shows:** Savings goal creation and tracking
- Create goal with name, target amount, deadline
- Calculate required daily/weekly/monthly savings rate
- View all goals with progress percentage
- Track detailed progress against milestones
- AI-powered acceleration tips for faster goal completion
- Quarterly milestone tracking
- Goal completion celebration
- Deadline extension or goal modification
- Goal deletion

**Key Actors:** User, Frontend, Backend, Goal Engine, LLM API, Database

#### 24_Seq10_FinancialHealthScore.puml
**Shows:** Comprehensive financial health scoring
- Component 1: Savings rate (% saved of income)
- Component 2: Budget control (adherence to budgets)
- Component 3: Spending stability (CV of monthly spending)
- Component 4: Debt management (debt-to-income ratio)
- Component 5: Emergency fund (months of expenses covered)
- Weighted average calculation
- Letter grade assignment (A-F)
- Component recommendations
- 12-month trend analysis

**Key Actors:** Frontend, Backend, Scoring Engine, Analytics, MySQL DB

#### 25_Seq11_AiFinanceChatbot.puml
**Shows:** Conversational AI assistant workflow
- User sends natural language message
- Intent recognition and parameter extraction
- Relevant data fetching based on intent
- LLM prompt construction with context
- Response generation
- Multi-turn conversation with context awareness
- Chat history storage
- Quick action buttons for common tasks
- Session management and export

**Key Actors:** User, Frontend, Backend, Intent Recognition, Data Fetcher, LLM API

## How to View Diagrams

### Using PlantUML Online Editor
1. Go to http://www.plantuml.com/plantuml/uml
2. Copy and paste any .puml file content
3. View the rendered diagram

### Using VS Code
1. Install "PlantUML" extension by jebbs
2. Open any .puml file
3. Use Alt+D to preview

### Using Command Line
```bash
# Install PlantUML
brew install plantuml  # macOS
# or download from http://plantuml.com/download

# Generate PNG from any diagram
plantuml 01_Main_UseCase_SystemScope.puml -o ../diagrams_output
```

## Diagram Coverage Summary

| Category | Count | Files |
|----------|-------|-------|
| System Scope | 1 | 01 |
| Use Case Details | 11 | 02-12 |
| Data Model | 1 | 13 |
| Class Design | 1 | 14 |
| Sequence Flows | 11 | 15-25 |
| **Total** | **26** | **01-25** |

## Data Flow Patterns

### Authentication Flow
- Register/Login → JWT generation → Token storage → Protected route access → Logout

### Transaction Management
- Manual entry / CSV import → Auto-categorization → DB storage → View/Filter/Search → Edit/Delete

### Analytics Pipeline
- Data collection → Feature engineering → Analysis → AI insights → Recommendations

### ML Pipeline
- Historical data → Feature engineering → Model training → Prediction → Confidence intervals

### AI Integration
- User query → Intent recognition → Data fetching → LLM call → Response → Quick actions

## Key Architectural Patterns

### Three-Tier Categorization
1. **Rule-based:** Fast, free, 80% accuracy
2. **Learning:** Cached, 15% accuracy (user corrections)
3. **AI Fallback:** LLM-based, 5% accuracy (paid)

### Weighted Scoring
- Financial Health Score uses 5 weighted components
- Flexible weighting allows prioritization

### Feature Engineering
- Temporal features (month, day patterns)
- Lag features (1-month, 3-month, 6-month averages)
- Rolling statistics (mean, std dev)
- Seasonality indicators

### Notification Strategy
- Email notifications for major events
- In-app toasts for immediate feedback
- Push notifications for important alerts

## Next Steps

1. **Backend Implementation:** Create SQLAlchemy models matching ER diagram
2. **API Development:** Implement routes for each sequence diagram
3. **Frontend Components:** Build React components for each use case
4. **Testing:** Write tests following sequence diagram flows
5. **Performance:** Optimize database queries and caching per sequence diagrams

---

*Last Updated: 2026*
*Total Diagrams: 25 PlantUML files*
*System: AI-Powered Personal Finance Analyzer*
