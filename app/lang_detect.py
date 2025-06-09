# === lang_detect.py ===

from langdetect import detect, DetectorFactory
DetectorFactory.seed = 42

SUPPORTED_LANGUAGES = {"en", "ru", "es", "fr", "de", "uk", "it"}  # можно расширить


def detect_language(text: str) -> str:
    try:
        lang = detect(text)
        return lang if lang in SUPPORTED_LANGUAGES else "unknown"
    except Exception:
        return "unknown"


