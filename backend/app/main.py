import os

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from app.db.session import SessionLocal
from app.api.v1.auth import router as auth_router
from app.api.v1.ai_insights import router as ai_insights_router
from app.api.v1.categories import router as categories_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.financial_health import router as financial_health_router
from app.api.v1.friends import router as friends_router
from app.api.v1.transactions import router as transactions_router
from app.api.v1.uploads import router as uploads_router
from app.db.schema_maintenance import ensure_database_schema
from app.models import models
from app.services.category_service import seed_default_categories
from app.utils.transaction_merchant_cleanup import clean_existing_transaction_merchants

ensure_database_schema()

def seed_categories():
    db = SessionLocal()
    try:
        seed_default_categories(db)
        clean_existing_transaction_merchants(db)
    finally:
        db.close()

app = FastAPI(
    title="AI-Powered Personal Finance Analyzer",
    description="REST API for personal finance management with AI insights",
    version="1.0.0"
)

# CORS: allow local development plus the deployed frontend configured by Render.
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

frontend_url = os.getenv("FRONTEND_URL", "").strip().rstrip("/")
if frontend_url:
    origins.append(frontend_url)

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
app.include_router(categories_router)
app.include_router(dashboard_router)
app.include_router(financial_health_router)
app.include_router(friends_router)
app.include_router(transactions_router)
app.include_router(uploads_router)


@app.on_event("startup")
def on_startup():
    seed_categories()


@app.get("/")
def home():
    return {
        "message": "AI-Powered Personal Finance Analyzer API",
        "version": "1.0.0",
        "endpoints": {
            "auth": "/auth",
            "ai_insights": "/ai/insights",
            "categories": "/categories",
            "dashboard": "/dashboard",
            "financial_health": "/financial-health/score",
            "friends": "/friends",
            "transactions": "/transactions",
            "uploads": "/uploads",
            "docs": "/docs",
            "redoc": "/redoc"
        }
    }
