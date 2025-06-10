import re
from better_profanity import profanity

profanity.load_censor_words()

WORD_RE = re.compile(r"\b\w{2,}\b", re.UNICODE)

def clean_input(text: str) -> list[str]:
    words = WORD_RE.findall(text.lower())
    return words[:3]

def is_valid_input(words: list[str]) -> bool:
    if not (1 <= len(words) <= 3):
        return False
    joined = ' '.join(words)
    if profanity.contains_profanity(joined):
        return False
    return True
