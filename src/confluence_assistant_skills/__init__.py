"""Confluence Assistant Skills - CLI for Confluence operations."""

try:
    from importlib.metadata import version

    __version__ = version("confluence-assistant-skills")
except Exception:
    __version__ = "dev"
