import os
from pathlib import Path
from typing import List, Any
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BASE_DIR.parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(ROOT_DIR / ".env"), str(BASE_DIR / ".env"), ".env"),
        extra="ignore"
    )

    ENVIRONMENT: str = "development"
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:5174"
    FRONTEND_URL: str = ""
    
    # Database
    DATABASE_URL: str = "sqlite:///./recoveriq.db"
    
    # Razorpay Test Mode
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = "whsec_dummy"
    
    # AI Engine
    LLM_PROVIDER: str = "gemini"
    GEMINI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.8-flash"
    OPENAI_API_KEY: str = ""

    def model_post_init(self, __context: Any) -> None:
        # Strip whitespace and resolve GOOGLE_API_KEY fallback if GEMINI_API_KEY is unset
        resolved_gemini = (self.GEMINI_API_KEY or self.GOOGLE_API_KEY or os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")).strip().strip("'\"")
        self.GEMINI_API_KEY = resolved_gemini
        self.RAZORPAY_KEY_ID = self.RAZORPAY_KEY_ID.strip().strip("'\"")
        self.RAZORPAY_KEY_SECRET = self.RAZORPAY_KEY_SECRET.strip().strip("'\"")

    @property
    def cors_origins_list(self) -> List[str]:
        origins = [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        if self.FRONTEND_URL and self.FRONTEND_URL.strip():
            origins.append(self.FRONTEND_URL.strip().rstrip("/"))
        seen = set()
        unique_origins = []
        for o in origins:
            if o not in seen:
                seen.add(o)
                unique_origins.append(o)
        return unique_origins

    @property
    def is_razorpay_configured(self) -> bool:
        return bool(
            self.RAZORPAY_KEY_ID 
            and self.RAZORPAY_KEY_SECRET 
            and not self.RAZORPAY_KEY_ID.startswith("rzp_test_placeholder")
            and not self.RAZORPAY_KEY_SECRET.startswith("placeholder")
        )

    @property
    def is_ai_configured(self) -> bool:
        if self.LLM_PROVIDER == "gemini":
            return bool(self.GEMINI_API_KEY and not self.GEMINI_API_KEY.startswith("placeholder") and not self.GEMINI_API_KEY.startswith("AIzaSy_placeholder"))
        elif self.LLM_PROVIDER == "openai":
            return bool(self.OPENAI_API_KEY and not self.OPENAI_API_KEY.startswith("sk-placeholder"))
        return False

settings = Settings()
