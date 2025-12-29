"""
Response Caching for Confluence Assistant Skills

Provides a simple file-based cache for API responses to reduce
redundant requests and improve performance.

Features:
- File-based persistence
- TTL (time-to-live) expiration
- LRU eviction when cache is full
- Thread-safe operations
- JSON serialization

Usage:
    from cache import Cache, cached

    # Direct cache usage
    cache = Cache()
    cache.set("key", {"data": "value"}, ttl=300)
    value = cache.get("key")

    # Decorator usage
    @cached(ttl=300)
    def get_page(page_id):
        return client.get(f"/api/v2/pages/{page_id}")
"""

import os
import json
import time
import hashlib
import threading
from pathlib import Path
from typing import Any, Optional, Callable, Dict
from functools import wraps


class Cache:
    """
    File-based cache with TTL support.

    Cache files are stored in the user's cache directory:
    - macOS: ~/Library/Caches/confluence-assistant-skills/
    - Linux: ~/.cache/confluence-assistant-skills/
    - Windows: %LOCALAPPDATA%/confluence-assistant-skills/cache/
    """

    DEFAULT_TTL = 300  # 5 minutes
    MAX_ENTRIES = 1000

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        default_ttl: int = DEFAULT_TTL,
        max_entries: int = MAX_ENTRIES,
        enabled: bool = True,
    ):
        """
        Initialize the cache.

        Args:
            cache_dir: Custom cache directory. If None, uses platform default.
            default_ttl: Default time-to-live in seconds
            max_entries: Maximum number of cached entries
            enabled: Whether caching is enabled
        """
        self.cache_dir = cache_dir or self._get_default_cache_dir()
        self.default_ttl = default_ttl
        self.max_entries = max_entries
        self.enabled = enabled
        self._lock = threading.Lock()

        if self.enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_default_cache_dir(self) -> Path:
        """Get platform-specific cache directory."""
        if os.name == 'nt':
            # Windows
            base = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
            return base / 'confluence-assistant-skills' / 'cache'
        elif os.name == 'darwin':
            # macOS
            return Path.home() / 'Library' / 'Caches' / 'confluence-assistant-skills'
        else:
            # Linux/Unix
            xdg_cache = os.environ.get('XDG_CACHE_HOME', Path.home() / '.cache')
            return Path(xdg_cache) / 'confluence-assistant-skills'

    def _get_cache_key(self, key: str) -> str:
        """Generate a filesystem-safe cache key."""
        # Use MD5 for consistent, short filenames
        return hashlib.md5(key.encode()).hexdigest()

    def _get_cache_path(self, key: str) -> Path:
        """Get the file path for a cache key."""
        cache_key = self._get_cache_key(key)
        return self.cache_dir / f"{cache_key}.json"

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a value from the cache.

        Args:
            key: Cache key
            default: Default value if key not found or expired

        Returns:
            Cached value or default
        """
        if not self.enabled:
            return default

        cache_path = self._get_cache_path(key)

        try:
            with self._lock:
                if not cache_path.exists():
                    return default

                with open(cache_path, 'r', encoding='utf-8') as f:
                    entry = json.load(f)

                # Check expiration
                if entry.get('expires_at', 0) < time.time():
                    cache_path.unlink(missing_ok=True)
                    return default

                # Update access time for LRU
                entry['accessed_at'] = time.time()
                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump(entry, f)

                return entry.get('value', default)

        except (json.JSONDecodeError, IOError, KeyError):
            return default

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Set a value in the cache.

        Args:
            key: Cache key
            value: Value to cache (must be JSON-serializable)
            ttl: Time-to-live in seconds (uses default if None)

        Returns:
            True if successfully cached
        """
        if not self.enabled:
            return False

        ttl = ttl if ttl is not None else self.default_ttl
        cache_path = self._get_cache_path(key)

        try:
            with self._lock:
                # Evict if necessary
                self._evict_if_needed()

                entry = {
                    'key': key,
                    'value': value,
                    'created_at': time.time(),
                    'accessed_at': time.time(),
                    'expires_at': time.time() + ttl,
                }

                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump(entry, f)

                return True

        except (TypeError, IOError) as e:
            # Value not JSON-serializable or IO error
            return False

    def delete(self, key: str) -> bool:
        """
        Delete a value from the cache.

        Args:
            key: Cache key

        Returns:
            True if entry was deleted
        """
        if not self.enabled:
            return False

        cache_path = self._get_cache_path(key)

        try:
            with self._lock:
                if cache_path.exists():
                    cache_path.unlink()
                    return True
                return False
        except IOError:
            return False

    def clear(self) -> int:
        """
        Clear all cached entries.

        Returns:
            Number of entries cleared
        """
        if not self.enabled:
            return 0

        count = 0
        try:
            with self._lock:
                for cache_file in self.cache_dir.glob('*.json'):
                    cache_file.unlink()
                    count += 1
        except IOError:
            pass

        return count

    def _evict_if_needed(self) -> None:
        """Evict old entries if cache is full (LRU)."""
        try:
            cache_files = list(self.cache_dir.glob('*.json'))

            if len(cache_files) < self.max_entries:
                return

            # Sort by access time and evict oldest
            entries = []
            for cache_file in cache_files:
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        entry = json.load(f)
                        entries.append((cache_file, entry.get('accessed_at', 0)))
                except (json.JSONDecodeError, IOError):
                    cache_file.unlink(missing_ok=True)

            # Sort by access time (oldest first)
            entries.sort(key=lambda x: x[1])

            # Evict oldest 10%
            evict_count = max(1, len(entries) // 10)
            for cache_file, _ in entries[:evict_count]:
                cache_file.unlink(missing_ok=True)

        except IOError:
            pass

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries.

        Returns:
            Number of entries removed
        """
        if not self.enabled:
            return 0

        count = 0
        now = time.time()

        try:
            with self._lock:
                for cache_file in self.cache_dir.glob('*.json'):
                    try:
                        with open(cache_file, 'r', encoding='utf-8') as f:
                            entry = json.load(f)

                        if entry.get('expires_at', 0) < now:
                            cache_file.unlink()
                            count += 1

                    except (json.JSONDecodeError, IOError):
                        cache_file.unlink(missing_ok=True)
                        count += 1

        except IOError:
            pass

        return count

    def stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        try:
            cache_files = list(self.cache_dir.glob('*.json'))
            total_size = sum(f.stat().st_size for f in cache_files)

            return {
                'enabled': self.enabled,
                'entries': len(cache_files),
                'max_entries': self.max_entries,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'cache_dir': str(self.cache_dir),
                'default_ttl': self.default_ttl,
            }
        except IOError:
            return {
                'enabled': self.enabled,
                'error': 'Unable to read cache directory',
            }


# Global cache instance
_global_cache: Optional[Cache] = None


def get_cache() -> Cache:
    """Get or create the global cache instance."""
    global _global_cache
    if _global_cache is None:
        _global_cache = Cache()
    return _global_cache


def cached(
    ttl: Optional[int] = None,
    key_prefix: str = "",
    cache: Optional[Cache] = None,
):
    """
    Decorator to cache function results.

    Args:
        ttl: Time-to-live in seconds
        key_prefix: Prefix for cache keys
        cache: Cache instance to use (uses global if None)

    Usage:
        @cached(ttl=300)
        def get_page(page_id):
            return client.get(f"/api/v2/pages/{page_id}")

        # With prefix
        @cached(ttl=600, key_prefix="space")
        def get_space(space_key):
            return client.get(f"/api/v2/spaces/{space_key}")
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            _cache = cache or get_cache()

            # Build cache key from function name and arguments
            key_parts = [key_prefix, func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = ":".join(filter(None, key_parts))

            # Try to get from cache
            result = _cache.get(cache_key)
            if result is not None:
                return result

            # Call function and cache result
            result = func(*args, **kwargs)
            _cache.set(cache_key, result, ttl=ttl)

            return result

        # Add cache control methods
        wrapper.cache_clear = lambda: get_cache().clear()
        wrapper.cache_key = lambda *a, **kw: ":".join(
            filter(None, [key_prefix, func.__name__] + [str(x) for x in a] +
                   [f"{k}={v}" for k, v in sorted(kw.items())])
        )

        return wrapper

    return decorator


def invalidate(pattern: str) -> int:
    """
    Invalidate cache entries matching a pattern.

    Note: This is a simple implementation that checks all entries.
    For large caches, consider using a more efficient approach.

    Args:
        pattern: Key pattern to match (uses simple substring matching)

    Returns:
        Number of entries invalidated
    """
    cache = get_cache()
    count = 0

    try:
        for cache_file in cache.cache_dir.glob('*.json'):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    entry = json.load(f)

                if pattern in entry.get('key', ''):
                    cache_file.unlink()
                    count += 1

            except (json.JSONDecodeError, IOError):
                pass

    except IOError:
        pass

    return count
