# config.py

from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env.local")

UPLOADS_DIR = BASE_DIR / "uploads"

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────────────────────────────────────
# Local OCR settings
# ─────────────────────────────────────────────────────────────

TESSERACT_PATH = os.getenv("TESSERACT_PATH", r"C:\Program Files\Tesseract-OCR\tesseract.exe")

# Tesseract language packs to try
# German, English, Polish, Russian, Turkish, Hungarian
TESSERACT_LANGS = os.getenv("TESSERACT_LANGS", "deu+eng+rus")

# Choose OCR engine: rapidocr, tesseract, or auto.
# rapidocr is the default because it does not need a separate Windows install.
OCR_ENGINE = os.getenv("OCR_ENGINE", "rapidocr").lower()


# ─────────────────────────────────────────────────────────────
# Local model settings
# ─────────────────────────────────────────────────────────────
LOCAL_TEXT_MODEL = os.getenv("LOCAL_TEXT_MODEL", "mistral-nemo:12b")  # qwen2.5:7b
LOCAL_VISION_MODEL = os.getenv("LOCAL_VISION_MODEL", "qwen2.5vl:7b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# ─────────────────────────────────────────────────────────────
# Paid fallback settings
# Disabled by default
# ─────────────────────────────────────────────────────────────

PAID_FALLBACK_ENABLED = os.getenv("PAID_FALLBACK_ENABLED", "false").lower() == "true"
PAID_PROVIDER = os.getenv("PAID_PROVIDER", "mistral")

MISTRAL_API_KEY       = os.getenv("MISTRAL_API_KEY",       "")
MISTRAL_OCR_MODEL     = os.getenv("MISTRAL_OCR_MODEL",     "mistral-ocr-latest")
MISTRAL_EXTRACT_MODEL = os.getenv("MISTRAL_EXTRACT_MODEL", "mistral-small-latest")
OPENAI_API_KEY        = os.getenv("OPENAI_API_KEY",        "")

# ─────────────────────────────────────────────────────────────
# Pipeline behavior
# ─────────────────────────────────────────────────────────────

SAVE_DEBUG_IMAGES = os.getenv("SAVE_DEBUG_IMAGES", "true").lower() == "true"
SAVE_PREPROCESSED_IMAGES = os.getenv("SAVE_PREPROCESSED_IMAGES", "true").lower() == "true"

# If quality is extremely poor, route to local vision model
BLUR_THRESHOLD = float(os.getenv("BLUR_THRESHOLD", "15"))
VERY_BLURRY_THRESHOLD = float(os.getenv("VERY_BLURRY_THRESHOLD", "10"))
DARK_THRESHOLD = float(os.getenv("DARK_THRESHOLD", "120"))
MIN_DOC_SIZE = int(os.getenv("MIN_DOC_SIZE", "1200"))



