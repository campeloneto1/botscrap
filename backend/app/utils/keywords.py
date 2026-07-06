import re
import unicodedata
from typing import List, Tuple, Dict, Any


def normalize_text(text: str) -> str:
    """
    Normalize text by removing accents and converting to lowercase.
    Example: "Manifestação" -> "manifestacao"
    """
    if not text:
        return ""
    # Remove accents: NFD decomposes characters, then we remove combining marks
    normalized = unicodedata.normalize('NFD', text)
    without_accents = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
    return without_accents.lower()


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

    text_normalized = normalize_text(text)
    matched = []
    highest_priority = 0

    for kw in keywords:
        word = kw.get("word", "")
        word_normalized = normalize_text(word)
        priority = kw.get("priority", 1)

        if not word_normalized:
            continue

        # Word boundary search with normalized text (no accents, lowercase)
        pattern = r'\b' + re.escape(word_normalized) + r'\b'
        if re.search(pattern, text_normalized):
            # Keep original word for display
            matched.append(word)
            if priority > highest_priority:
                highest_priority = priority

    return len(matched) > 0, matched, highest_priority


def highlight_keywords(text: str, keywords: List[str]) -> str:
    """
    Highlight keywords in text using HTML bold tags.
    Handles accents: keyword "manifestacao" will highlight "manifestação" in text.

    Args:
        text: The original text
        keywords: List of keywords to highlight

    Returns:
        Text with keywords wrapped in <b> tags
    """
    if not text or not keywords:
        return text

    result = text
    text_normalized = normalize_text(text)

    for word in keywords:
        word_normalized = normalize_text(word)
        if not word_normalized:
            continue

        # Find positions in normalized text
        pattern = re.compile(r'\b' + re.escape(word_normalized) + r'\b')

        # We need to find matches and replace in original text
        # Build a list of (start, end) positions from normalized, then replace in original
        matches = list(pattern.finditer(text_normalized))

        # Replace from end to start to preserve positions
        for match in reversed(matches):
            start, end = match.start(), match.end()
            original_word = text[start:end]
            result = result[:start] + f'<b>{original_word}</b>' + result[end:]

    return result
