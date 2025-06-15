from better_profanity import profanity
from app.lang_detect import detect_language

def is_valid_input(words: str) -> tuple[bool, str]:
    # Check word count
    word_list = words.strip().split()
    if not 1 <= len(word_list) <= 3:
        return False, "❌ Эй, нужно от 1 до 3 слов, не больше, не меньше! (Hey, 1 to 3 words only, no more, no less!)"
    
    # Check for profanity
    if profanity.contains_profanity(words):
        return False, "❌ Ух, какие слова! Давай без мата, а? (Whoa, those words! Let's keep it clean, okay?)"
    
    # Check language
    language = detect_language(words)
    if not language:
        return False, "❌ Это что, шифр инопланетян? Попробуй нормальные слова! (Is that alien code? Try normal words!)"
    
    return True, language
