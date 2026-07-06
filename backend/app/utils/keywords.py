import re
from typing import List, Tuple, Dict, Any


def find_keywords(
    text: str,
    keywords: List[Dict[str, Any]],
) -> Tuple[bool, List[str], int]:
    """
    Find keywords in text.

    Args:
        text: The text to search in
        keywords: List of keyword dicts with 'word' and 'priority' keys

    Returns:
        Tuple of (has_match, matched_words, highest_priority)
    """
    if not text or not keywords:
        return False, [], 0

    text_lower = text.lower()
    matched = []
    highest_priority = 0

    for kw in keywords:
        word = kw.get("word", "").lower()
        priority = kw.get("priority", 1)

        if not word:
            continue

        # Simple word boundary search
        pattern = r'\b' + re.escape(word) + r'\b'
        if re.search(pattern, text_lower):
            matched.append(word)
            if priority > highest_priority:
                highest_priority = priority

    return len(matched) > 0, matched, highest_priority


def highlight_keywords(text: str, keywords: List[str]) -> str:
    """
    Highlight keywords in text using HTML bold tags.

    Args:
        text: The original text
        keywords: List of keywords to highlight

    Returns:
        Text with keywords wrapped in <b> tags
    """
    if not text or not keywords:
        return text

    result = text
    for word in keywords:
        pattern = re.compile(r'\b(' + re.escape(word) + r')\b', re.IGNORECASE)
        result = pattern.sub(r'<b>\1</b>', result)

    return result
