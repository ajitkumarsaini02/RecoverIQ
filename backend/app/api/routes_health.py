from fastapi import APIRouter
from app.config import settings
from datetime import datetime, timezone

router = APIRouter(prefix="/api", tags=["Health & System"])

@router.get("/health")
def get_health():
    return {
        "status": "healthy",
        "service": "RecoverIQ - AI Revenue Recovery Agent",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": "TEST MODE / DEMO",
        "integrations": {
            "razorpay": {
                "configured": settings.is_razorpay_configured,
                "mode": "TEST_MODE" if settings.is_razorpay_configured else "SIMULATION_MODE",
                "key_id_masked": f"{settings.RAZORPAY_KEY_ID[:8]}..." if settings.RAZORPAY_KEY_ID else "UNCONFIGURED (SIMULATION)"
            },
            "ai_engine": {
                "configured": settings.is_ai_configured,
                "provider": settings.LLM_PROVIDER,
                "mode": "LIVE_LLM" if settings.is_ai_configured else "DETERMINISTIC_FALLBACK_RULE_ENGINE"
            },
            "database": {
                "status": "CONNECTED",
                "engine": "PostgreSQL (SQLAlchemy 2.0)" if settings.DATABASE_URL.startswith("postgresql") or settings.DATABASE_URL.startswith("postgres") else "SQLite (SQLAlchemy 2.0)"
            }
        }
    }

@router.get("/system/status")
def get_system_status():
    return get_health()
