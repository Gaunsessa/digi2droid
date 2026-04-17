import os

# RunPod
RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY", "")
RUNPOD_ENDPOINT_ID = os.environ.get("RUNPOD_ENDPOINT_ID", "")

# SerpAPI
SERPAPI_API_KEY = os.environ.get("SERPAPI_API_KEY", "")

# OpenRouter
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.environ.get(
    "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
).rstrip("/")
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "")

# Constants
TOP_N = 12
FACE_COUNT = 50_000
MAX_IMAGE_BYTES = int(os.environ.get("MAX_IMAGE_BYTES", str(10 * 1024 * 1024)))

RUNPOD_POLL_INTERVAL_SEC = float(os.environ.get("RUNPOD_POLL_INTERVAL_SEC", "2"))
RUNPOD_POLL_TIMEOUT_SEC = float(os.environ.get("RUNPOD_POLL_TIMEOUT_SEC", "900"))

JOB_TTL_SEC = float(os.environ.get("JOB_TTL_SEC", str(24 * 3600)))

# Required config vars
_REQUIRED = (
    "OPENROUTER_API_KEY",
    "OPENROUTER_MODEL",
    "SERPAPI_API_KEY",
    "RUNPOD_API_KEY",
    "RUNPOD_ENDPOINT_ID",
)


def check_required() -> list[str]:
    """Return names of required config vars that are empty/unset."""
    return [name for name in _REQUIRED if not globals()[name]]
