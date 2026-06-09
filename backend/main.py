from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from database import SessionLocal
from auth import router as auth_router
from ai_insights import router as ai_insights_router
from budget_recommendations import router as budget_recommendations_router
from budgets import router as budgets_router
from categories import router as categories_router
from dashboard import router as dashboard_router
from friends import router as friends_router
from savings_goals import router as savings_goals_router
from transactions import router as transactions_router
from uploads import router as uploads_router
from models import Category
from schema_maintenance import ensure_database_schema
import models

ensure_database_schema()

DEFAULT_CATEGORIES = [
    "Debt Cleared",
    "Refunds",
    "Bills",
    "Subscriptions",
    "Education",
    "Entertainment",
    "Food",
    "Laundry",
    "Healthcare",
    "Investments",
    "Salary",
    "Groceries",
    "Shopping",
    "Travel",
    "Other",
    "Needs Review",
    "Friends",
]


def seed_default_categories():
    db = SessionLocal()
    try:
        existing_names = {category.name for category in db.query(Category).all()}
        missing_names = [name for name in DEFAULT_CATEGORIES if name not in existing_names]
        if missing_names:
            for name in missing_names:
                category = Category(name=name, description=f"{name} category")
                db.add(category)
            db.commit()
    finally:
        db.close()

app = FastAPI(
    title="AI-Powered Personal Finance Analyzer",
    description="REST API for personal finance management with AI insights",
    version="1.0.0"
)

# CORS: allow local frontend dev servers
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(auth_router)
app.include_router(ai_insights_router)
app.include_router(budget_recommendations_router)
app.include_router(budgets_router)
app.include_router(categories_router)
app.include_router(dashboard_router)
app.include_router(friends_router)
app.include_router(savings_goals_router)
app.include_router(transactions_router)
app.include_router(uploads_router)


@app.on_event("startup")
def on_startup():
    seed_default_categories()


seed_default_categories()


@app.get("/")
def home():
    return {
        "message": "AI-Powered Personal Finance Analyzer API",
        "version": "1.0.0",
        "endpoints": {
            "auth": "/auth",
            "ai_insights": "/ai/insights",
            "budget_recommendations": "/budget-recommendations",
            "budgets": "/budgets",
            "categories": "/categories",
            "dashboard": "/dashboard",
            "friends": "/friends",
            "savings_goals": "/savings-goals",
            "transactions": "/transactions",
            "uploads": "/uploads",
            "docs": "/docs",
            "redoc": "/redoc"
        }
    }
