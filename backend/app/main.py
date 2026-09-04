from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.routes_health import router as health_router
from app.api.routes_transactions import router as transactions_router
from app.api.routes_demo import router as demo_router
from app.api.routes_agent_and_recovery import router as agent_router
from app.api.routes_dashboard_and_simulation import router as dashboard_router
from app.api.routes_webhook import router as webhook_router
from app.db.session import SessionLocal, engine, Base
from app.services.seed_service import seed_database

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure tables exist
    Base.metadata.create_all(bind=engine)
    # Only seed database automatically if not in production and not running PostgreSQL
    if settings.ENVIRONMENT != "production" and not settings.DATABASE_URL.startswith("postgresql") and not settings.DATABASE_URL.startswith("postgres"):
        db = SessionLocal()
        try:
            seed_database(db=db, customer_count=350, transaction_count=1200, force_reseed=False)
        finally:
            db.close()
    yield

app = FastAPI(
    title="RecoverIQ — AI Revenue Recovery Agent API",
    description="Intelligent, bounded, explainable revenue recovery engine for failed payments (Razorpay Track 3)",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS - Enable cross-origin API access for Vercel, Render and local development
cors_origins = settings.cors_origins_list
if settings.ENVIRONMENT == "development" or "*" in cors_origins:
    # A wildcard origin cannot be combined with credentials (browsers reject that combo).
    allow_origins = ["*"]
    allow_credentials = False
else:
    allow_origins = cors_origins
    allow_credentials = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(health_router)
app.include_router(transactions_router)
app.include_router(demo_router)
app.include_router(agent_router)
app.include_router(dashboard_router)
app.include_router(webhook_router)

@app.get("/")
def root():
    return {
        "message": "RecoverIQ AI Revenue Recovery Engine is active.",
        "mode": "TEST MODE / DEMO",
        "docs_url": "/docs",
        "health_check": "/api/health",
        "transactions": "/api/transactions",
        "dashboard": "/api/dashboard",
        "demo_scenario": "/api/demo/scenario"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
