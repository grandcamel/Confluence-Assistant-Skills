"""
Configuration Manager for Confluence Assistant Skills

Handles configuration from multiple sources with priority:
1. Environment variables (highest priority)
2. settings.local.json (personal, gitignored)
3. settings.json (team defaults, committed)
4. Built-in defaults (lowest priority)

Environment Variables:
    CONFLUENCE_API_TOKEN - API token for authentication
    CONFLUENCE_EMAIL - Email address for authentication
    CONFLUENCE_SITE_URL - Confluence site URL (e.g., https://your-site.atlassian.net)
    CONFLUENCE_PROFILE - Profile name to use (default: "default")

Usage:
    from config_manager import get_confluence_client, get_config

    # Get a configured client
    client = get_confluence_client(profile="production")

    # Get raw configuration
    config = get_config()
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Union

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """Raised when configuration is invalid or missing."""
    pass


class ConfigManager:
    """
    Manages configuration from multiple sources.

    Priority (highest to lowest):
    1. Environment variables
    2. settings.local.json
    3. settings.json
    4. Built-in defaults
    """

    # Default configuration values
    DEFAULTS = {
        "api": {
            "version": "2",
            "timeout": 30,
            "max_retries": 3,
            "retry_backoff": 2.0,
            "verify_ssl": True,
        },
        "default_profile": "default",
    }

    # Environment variable mappings
    ENV_VARS = {
        "api_token": "CONFLUENCE_API_TOKEN",
        "email": "CONFLUENCE_EMAIL",
        "site_url": "CONFLUENCE_SITE_URL",
        "profile": "CONFLUENCE_PROFILE",
    }

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize the configuration manager.

        Args:
            config_dir: Path to the .claude directory. If not provided,
                       searches upward from the current directory.
        """
        self.config_dir = config_dir or self._find_config_dir()
        self._config_cache: Optional[Dict[str, Any]] = None

    def _find_config_dir(self) -> Path:
        """
        Find the .claude directory by searching upward from current directory.

        Returns:
            Path to the .claude directory

        Raises:
            ConfigError: If .claude directory is not found
        """
        current = Path.cwd()

        # Search upward for .claude directory
        for parent in [current] + list(current.parents):
            claude_dir = parent / ".claude"
            if claude_dir.is_dir():
                return claude_dir

        # Fall back to current directory's .claude
        return current / ".claude"

    def _load_json_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Load a JSON configuration file.

        Args:
            file_path: Path to the JSON file

        Returns:
            Parsed configuration dictionary, or empty dict if file doesn't exist
        """
        if not file_path.exists():
            return {}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in {file_path}: {e}")
            return {}
        except Exception as e:
            logger.warning(f"Error reading {file_path}: {e}")
            return {}

    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """
        Deep merge two dictionaries.

        Args:
            base: Base dictionary
            override: Dictionary with values to override

        Returns:
            Merged dictionary
        """
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def _get_env_config(self) -> Dict[str, Any]:
        """
        Get configuration from environment variables.

        Returns:
            Dictionary with environment-based configuration
        """
        config = {}

        # API token
        if os.environ.get(self.ENV_VARS["api_token"]):
            config["api_token"] = os.environ[self.ENV_VARS["api_token"]]

        # Email
        if os.environ.get(self.ENV_VARS["email"]):
            config["email"] = os.environ[self.ENV_VARS["email"]]

        # Site URL
        if os.environ.get(self.ENV_VARS["site_url"]):
            config["url"] = os.environ[self.ENV_VARS["site_url"]]

        return config

    def get_config(self, force_reload: bool = False) -> Dict[str, Any]:
        """
        Get the merged configuration from all sources.

        Args:
            force_reload: Force reloading from files

        Returns:
            Complete merged configuration dictionary
        """
        if self._config_cache is not None and not force_reload:
            return self._config_cache

        # Start with defaults
        config = self.DEFAULTS.copy()

        # Load settings.json (team defaults)
        settings_path = self.config_dir / "settings.json"
        settings = self._load_json_file(settings_path)
        if "confluence" in settings:
            config = self._deep_merge(config, settings["confluence"])

        # Load settings.local.json (personal overrides)
        local_settings_path = self.config_dir / "settings.local.json"
        local_settings = self._load_json_file(local_settings_path)
        if "confluence" in local_settings:
            config = self._deep_merge(config, local_settings["confluence"])

        # Apply environment variables (highest priority)
        env_config = self._get_env_config()
        if env_config:
            config = self._deep_merge(config, env_config)

        self._config_cache = config
        return config

    def get_profile(self, profile_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get configuration for a specific profile.

        Args:
            profile_name: Profile name. If None, uses default profile or env var.

        Returns:
            Profile configuration with inherited API settings

        Raises:
            ConfigError: If profile is not found and required credentials are missing
        """
        config = self.get_config()

        # Determine which profile to use
        profile_name = (
            profile_name
            or os.environ.get(self.ENV_VARS["profile"])
            or config.get("default_profile", "default")
        )

        # Get profiles from config
        profiles = config.get("profiles", {})

        # Get the specific profile
        profile = profiles.get(profile_name, {})

        # Merge with base config (API settings, etc.)
        api_config = config.get("api", self.DEFAULTS["api"])

        # Check for credentials at config root level (from env or local settings)
        # These should override profile settings since env vars have highest priority
        root_credentials = {
            k: v for k, v in config.items()
            if k in ("url", "email", "api_token")
        }

        # Build result with priority: env vars (root) > profile > api defaults
        result = {
            "profile_name": profile_name,
            **api_config,
            **profile,
            **root_credentials,  # env vars override profile settings
        }

        return result

    def validate_profile(self, profile: Dict[str, Any]) -> bool:
        """
        Validate that a profile has required credentials.

        Args:
            profile: Profile configuration dictionary

        Returns:
            True if valid

        Raises:
            ConfigError: If required credentials are missing
        """
        required = ["url", "email", "api_token"]
        missing = [key for key in required if not profile.get(key)]

        if missing:
            raise ConfigError(
                f"Missing required configuration: {', '.join(missing)}.\n"
                f"Set via environment variables:\n"
                f"  CONFLUENCE_SITE_URL, CONFLUENCE_EMAIL, CONFLUENCE_API_TOKEN\n"
                f"Or add to .claude/settings.local.json"
            )

        return True

    def list_profiles(self) -> Dict[str, Dict[str, Any]]:
        """
        List all available profiles.

        Returns:
            Dictionary of profile names to their configurations
        """
        config = self.get_config()
        return config.get("profiles", {})


# Module-level convenience functions

_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get or create the global ConfigManager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_config(force_reload: bool = False) -> Dict[str, Any]:
    """
    Get the merged configuration.

    Args:
        force_reload: Force reloading from files

    Returns:
        Complete configuration dictionary
    """
    return get_config_manager().get_config(force_reload=force_reload)


def get_confluence_client(
    profile: Optional[str] = None,
    **kwargs
) -> "ConfluenceClient":
    """
    Get a configured Confluence client.

    Args:
        profile: Profile name to use (defaults to CONFLUENCE_PROFILE or "default")
        **kwargs: Additional arguments passed to ConfluenceClient

    Returns:
        Configured ConfluenceClient instance

    Raises:
        ConfigError: If required credentials are missing
    """
    from confluence_client import ConfluenceClient

    manager = get_config_manager()
    profile_config = manager.get_profile(profile)
    manager.validate_profile(profile_config)

    # Build client kwargs
    client_kwargs = {
        "base_url": profile_config["url"],
        "email": profile_config["email"],
        "api_token": profile_config["api_token"],
        "timeout": profile_config.get("timeout", 30),
        "max_retries": profile_config.get("max_retries", 3),
        "retry_backoff": profile_config.get("retry_backoff", 2.0),
        "verify_ssl": profile_config.get("verify_ssl", True),
    }

    # Allow overrides from kwargs
    client_kwargs.update(kwargs)

    return ConfluenceClient(**client_kwargs)


def get_default_space() -> Optional[str]:
    """
    Get the default space key from configuration.

    Returns:
        Default space key or None if not configured
    """
    profile = get_config_manager().get_profile()
    return profile.get("default_space")


def get_space_keys() -> list:
    """
    Get the list of configured space keys.

    Returns:
        List of space keys from the current profile
    """
    profile = get_config_manager().get_profile()
    return profile.get("space_keys", [])
