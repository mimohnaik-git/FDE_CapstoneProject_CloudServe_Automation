import os
import math
from pathlib import Path

from dotenv import load_dotenv


# Loading a local .env file is safe during import. Validation of provider
# credentials happens only when a provider-specific integration asks for one.
load_dotenv()

class AppConfig:
    """Strongly typed, validated configuration context manager for the Capstone Project."""
    
    def __init__(self):
        # Credentials are optional for imports, unit tests, and offline flows.
        # A provider integration must call require_openrouter_api_key() before
        # issuing a live request.
        self.OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
        self.GROQ_API_KEY = os.getenv("GROQ_API_KEY")
            
        # Target Large Language and Vector Embedding Infrastructure Models
        self.MODEL_NAME = os.getenv("MODEL_NAME", "openrouter/free")
        self.OPENROUTER_MODEL_NAME = os.getenv("OPENROUTER_MODEL_NAME", self.MODEL_NAME)
        self.EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        self.GENERATION_PROVIDER = os.getenv("GENERATION_PROVIDER", "offline").strip().lower()
        self.OPENROUTER_BASE_URL = os.getenv(
            "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
        ).rstrip("/")
        self.GROQ_MODEL_NAME = os.getenv("GROQ_MODEL_NAME", "openai/gpt-oss-20b")
        self.GROQ_BASE_URL = os.getenv(
            "GROQ_BASE_URL", "https://api.groq.com/openai/v1"
        ).rstrip("/")
        try:
            self.GENERATION_TIMEOUT_SECONDS = float(
                os.getenv("GENERATION_TIMEOUT_SECONDS", "30")
            )
        except ValueError as exc:
            raise ValueError(
                "CONFIGURATION EXCEPTION: 'GENERATION_TIMEOUT_SECONDS' must be a valid number."
            ) from exc
        if not math.isfinite(self.GENERATION_TIMEOUT_SECONDS) or self.GENERATION_TIMEOUT_SECONDS <= 0:
            raise ValueError(
                "CONFIGURATION EXCEPTION: 'GENERATION_TIMEOUT_SECONDS' must be finite and positive."
            )
        
        # Paths and Local Persistence DB Systems
        self.CHROMA_PATH = Path(os.getenv("CHROMA_PATH", "./storage/chroma"))
        self.DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./storage/decisions.db")
        
        # Observability Metrics Level
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
        
        # Routing defaults retained after development evaluation found insufficient
        # evidence for a safe threshold change. Future changes require measured
        # development evidence; the legacy environment name remains supported.
        confidence_value = os.getenv(
            "CLASSIFICATION_CONFIDENCE_THRESHOLD",
            os.getenv("CONFIDENCE_THRESHOLD", "0.80"),
        )
        self.CLASSIFICATION_CONFIDENCE_THRESHOLD = self._probability_setting(
            "CLASSIFICATION_CONFIDENCE_THRESHOLD", confidence_value
        )
        self.CONFIDENCE_THRESHOLD = self.CLASSIFICATION_CONFIDENCE_THRESHOLD
        self.RETRIEVAL_ROUTING_THRESHOLD = self._probability_setting(
            "RETRIEVAL_ROUTING_THRESHOLD",
            os.getenv("RETRIEVAL_ROUTING_THRESHOLD", "0.30"),
        )
            
        try:
            self.RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "5"))
        except ValueError as exc:
            raise ValueError(
                "CONFIGURATION EXCEPTION: 'RETRIEVAL_TOP_K' must be a valid integer value."
            ) from exc
        if self.RETRIEVAL_TOP_K <= 0:
            raise ValueError(
                "CONFIGURATION EXCEPTION: 'RETRIEVAL_TOP_K' must be greater than zero."
            )

    @staticmethod
    def _probability_setting(name: str, value: str) -> float:
        try:
            parsed = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"CONFIGURATION EXCEPTION: '{name}' must be a valid float value."
            ) from exc
        if not math.isfinite(parsed) or not 0.0 <= parsed <= 1.0:
            raise ValueError(
                f"CONFIGURATION EXCEPTION: '{name}' must be finite and between 0.0 and 1.0."
            )
        return parsed

    def require_openrouter_api_key(self) -> str:
        """Return the provider credential or fail immediately before live use."""
        if not self.OPENROUTER_API_KEY:
            raise ValueError(
                "CRITICAL SYSTEM CONFIGURATION ERROR: 'OPENROUTER_API_KEY' environment variable "
                "is required before initializing the OpenRouter provider."
            )
        return self.OPENROUTER_API_KEY

    def require_groq_api_key(self) -> str:
        """Return the Groq credential or fail immediately before live use."""
        if not self.GROQ_API_KEY:
            raise ValueError(
                "CRITICAL SYSTEM CONFIGURATION ERROR: 'GROQ_API_KEY' environment variable "
                "is required before initializing the Groq provider."
            )
        return self.GROQ_API_KEY

    def ensure_runtime_directories(self) -> None:
        """Create configured local runtime directories when an entrypoint needs them."""
        self.CHROMA_PATH.mkdir(parents=True, exist_ok=True)
        
        if self.DATABASE_URL.startswith("sqlite:///"):
            db_file_path = Path(self.DATABASE_URL.replace("sqlite:///", ""))
            db_file_path.parent.mkdir(parents=True, exist_ok=True)

# Importing configuration must remain safe for tests and offline operation.
settings = AppConfig()
