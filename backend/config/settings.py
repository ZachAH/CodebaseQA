"""Django settings for the CodebaseQA project."""
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).lower() in {"1", "true", "yes", "on"}


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-secret-change-me")
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = os.environ.get(
    "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1"
).split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party
    "rest_framework",
    "corsheaders",
    "pgvector.django",
    # Local apps
    "apps.repos",
    "apps.chat",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database — parsed from DATABASE_URL
_db_url = os.environ.get(
    "DATABASE_URL", "postgres://codebaseqa:codebaseqa@localhost:5432/codebaseqa"
)
_parsed = urlparse(_db_url)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": _parsed.path.lstrip("/"),
        "USER": _parsed.username,
        "PASSWORD": _parsed.password,
        "HOST": _parsed.hostname,
        "PORT": _parsed.port or 5432,
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    # Per-IP rate limits (anonymous). Tune via the rates below.
    "DEFAULT_THROTTLE_RATES": {
        "ask_burst": os.environ.get("THROTTLE_ASK_BURST", "15/min"),
        "ask_day": os.environ.get("THROTTLE_ASK_DAY", "200/day"),
        "index_burst": os.environ.get("THROTTLE_INDEX_BURST", "10/hour"),
    },
}

# CORS — allow the Vite dev server
CORS_ALLOWED_ORIGINS = [
    os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173"),
]

# --- AI / RAG configuration ---
# Which LLM answers questions: "groq" (free, default) or "anthropic" (Claude).
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "groq").lower()

# Groq — free tier, no credit card, OpenAI-compatible. Default provider.
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

# Anthropic (Claude) — optional premium provider. Set LLM_PROVIDER=anthropic.
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-8")

# --- Embeddings ---
# "local"  = fastembed, runs on-device — no API, no key, no card (default).
# "voyage" = Voyage AI (code-specialized, but requires a Voyage key + a payment
#            method on file, so it's off by default).
EMBED_PROVIDER = os.environ.get("EMBED_PROVIDER", "local").lower()

# Local model (fastembed). bge-small-en-v1.5 is 384-dim and lightweight.
LOCAL_EMBED_MODEL = os.environ.get("LOCAL_EMBED_MODEL", "BAAI/bge-small-en-v1.5")

# Voyage (only used if EMBED_PROVIDER=voyage).
VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY", "")
VOYAGE_EMBED_MODEL = os.environ.get("VOYAGE_EMBED_MODEL", "voyage-code-3")

# Vector dimension MUST match the active model
# (384 for bge-small-en-v1.5, 1024 for voyage-code-3).
_default_dim = "1024" if EMBED_PROVIDER == "voyage" else "384"
EMBED_DIM = int(os.environ.get("EMBED_DIM", _default_dim))

# Directory where repositories are cloned for indexing
REPO_CLONE_DIR = Path(os.environ.get("REPO_CLONE_DIR", BASE_DIR / ".repos"))
REPO_CLONE_DIR.mkdir(parents=True, exist_ok=True)

# --- Cost / usage guardrails ---
# Output cap per answer (Claude). Keeps any single reply bounded.
MAX_OUTPUT_TOKENS = int(os.environ.get("MAX_OUTPUT_TOKENS", "1536"))
# How many code chunks to retrieve and feed to Claude (bounds INPUT tokens).
RETRIEVAL_TOP_K = int(os.environ.get("RETRIEVAL_TOP_K", "6"))
# Per-chunk character cap when building the prompt context.
MAX_CONTEXT_CHARS_PER_CHUNK = int(os.environ.get("MAX_CONTEXT_CHARS_PER_CHUNK", "2400"))
# Effort level for Claude (low|medium|high|max). medium balances cost vs quality.
ANTHROPIC_EFFORT = os.environ.get("ANTHROPIC_EFFORT", "medium")

# Cap embeddings work per repo (bounds Voyage cost on huge repos).
MAX_CHUNKS_PER_REPO = int(os.environ.get("MAX_CHUNKS_PER_REPO", "6000"))

# App-level daily budget guard (UTC day). Requests are refused once EITHER
# the token total OR the estimated dollar spend for the day is reached.
DAILY_TOKEN_BUDGET = int(os.environ.get("DAILY_TOKEN_BUDGET", "2000000"))
DAILY_COST_BUDGET_USD = float(os.environ.get("DAILY_COST_BUDGET_USD", "2.00"))

# Pricing per 1M tokens, used to estimate spend for the dollar budget.
# Groq's free tier costs nothing, so its defaults are 0 (the token budget below
# still applies, protecting the free-tier quota from abuse). Claude defaults to
# claude-opus-4-8 pricing.
_default_in, _default_out = ("0.0", "0.0") if LLM_PROVIDER == "groq" else ("5.0", "25.0")
MODEL_INPUT_COST_PER_MTOK = float(os.environ.get("MODEL_INPUT_COST_PER_MTOK", _default_in))
MODEL_OUTPUT_COST_PER_MTOK = float(os.environ.get("MODEL_OUTPUT_COST_PER_MTOK", _default_out))
