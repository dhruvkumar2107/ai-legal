# utils.py
from deep_translator import GoogleTranslator
from typing import List

LANG_MAP = {
    "English": "en", "Hindi": "hi", "Kannada": "kn", "Marathi": "mr",
    "Tamil": "ta", "Telugu": "te", "Bengali": "bn", "Gujarati": "gu"
}

def translate_text(text: str, target_language_name: str) -> str:
    """Translate using Deep Translator. target_language_name like 'Hindi' or 'English'."""
    if not text:
        return text
    target_code = LANG_MAP.get(target_language_name, "en")
    try:
        return GoogleTranslator(source='auto', target=target_code).translate(text)
    except Exception:
        return text

def translate_list(items: List[str], target_language_name: str) -> List[str]:
    return [translate_text(i, target_language_name) for i in (items or [])]
