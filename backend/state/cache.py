"""Cache module — stores generated quizzes, visuals, and explanations to avoid regeneration."""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from backend.config import DATA_DIR

CACHE_PATH = DATA_DIR / "cache.json"


def _read_cache() -> dict:
    """Read cache file."""
    if not CACHE_PATH.exists():
        return {}
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def _write_cache(cache: dict):
    """Write cache file."""
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def _make_key(topic_id: str, cache_type: str) -> str:
    """Make a cache key from topic_id and type."""
    return f"{topic_id}:{cache_type}"


def _make_content_key(subject: str, chapter: str, topic: str, cache_type: str) -> str:
    """Make a cache key from content fields (for when topic_id isn't available)."""
    content = f"{subject}|{chapter}|{topic}".lower()
    hash_str = hashlib.md5(content.encode()).hexdigest()[:12]
    return f"{hash_str}:{cache_type}"


def get_cached(topic_id: str, cache_type: str) -> dict | None:
    """Get cached content by topic_id and type (quiz, visual, explanation)."""
    cache = _read_cache()
    key = _make_key(topic_id, cache_type)
    entry = cache.get(key)
    if entry:
        print(f"[CACHE] Hit: {key}")
        return entry.get("data")
    return None


def get_cached_by_content(subject: str, chapter: str, topic: str, cache_type: str) -> dict | None:
    """Get cached content by content fields."""
    cache = _read_cache()
    key = _make_content_key(subject, chapter, topic, cache_type)
    entry = cache.get(key)
    if entry:
        print(f"[CACHE] Content hit: {key}")
        return entry.get("data")
    return None


def set_cached(topic_id: str, cache_type: str, data, 
               subject: str = "", chapter: str = "", topic: str = ""):
    """Store data in cache."""
    cache = _read_cache()
    
    # Store by topic_id
    key = _make_key(topic_id, cache_type)
    cache[key] = {
        "data": data,
        "created": datetime.now().isoformat(),
        "type": cache_type,
        "subject": subject,
        "chapter": chapter,
        "topic": topic
    }
    
    # Also store by content hash for content-based lookups
    if subject and chapter and topic:
        content_key = _make_content_key(subject, chapter, topic, cache_type)
        cache[content_key] = cache[key]
    
    _write_cache(cache)
    print(f"[CACHE] Stored: {key}")


def clear_cache():
    """Clear entire cache."""
    _write_cache({})
    print("[CACHE] Cleared")
