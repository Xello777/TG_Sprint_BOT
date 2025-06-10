from langdetect import detect, DetectorFactory
DetectorFactory.seed = 42

SUPPORTED_LANGUAGES = {"en", "ru", "es", "fr", "de", "uk", "it"}

def detect_language(text: str) -> str:
    try:
        lang = detect(text)
        return lang if lang in SUPPORTED_LANGUAGES else "unknown"
    except Exception:
        return "unknown"
