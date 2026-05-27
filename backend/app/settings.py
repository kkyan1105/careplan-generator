import os

SECRET_KEY = "dev-secret-key-not-for-production"
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "corsheaders",
    "rest_framework",
    "app",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "app.exceptions.AppExceptionMiddleware",
]

REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": "app.exceptions.drf_exception_handler",
}

CORS_ALLOW_ALL_ORIGINS = True

ROOT_URLCONF = "app.urls"
WSGI_APPLICATION = "app.wsgi.application"

DATABASE_URL = os.environ.get("DATABASE_URL", "")
if DATABASE_URL:
    import urllib.parse
    r = urllib.parse.urlparse(DATABASE_URL)
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": r.path.lstrip("/"),
            "USER": r.username,
            "PASSWORD": r.password,
            "HOST": r.hostname,
            "PORT": r.port or 5432,
        }
    }
else:
    DATABASES = {}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── LLM configuration ─────────────────────────────────────────────────────────
# Switch providers by changing LLM_BACKEND. No code changes needed.
LLM_BACKEND = os.environ.get("LLM_BACKEND", "openai")   # "openai" | "claude"

OPENAI_API_KEY  = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL    = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL   = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
