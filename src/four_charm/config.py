import json
import multiprocessing
import pathlib
from typing import Any


class Config:
    # Default configuration values
    _DEFAULTS = {
        "MAX_WORKERS": min(5, multiprocessing.cpu_count()),
        "DOWNLOAD_TIMEOUT": (10, 60),
        "RATE_LIMIT_DELAY": 0.3,
        "MAX_RETRIES": 3,
        "CHUNK_SIZE": 8192,
        "MAX_FILENAME_LENGTH": 200,
        "MIN_FREE_SPACE_MB": 100,
        "PROGRESS_UPDATE_INTERVAL": 0.1,
        "MAX_FOLDER_NAME_LENGTH": 40,
        "API_TIMEOUT": 30,
        "RETRY_DELAY": 2.0,
        "CATALOG_SCRAPE_DELAY": 0.5,
        "BASE_DELAY": 0.3,
        "BACKOFF_MULTIPLIER": 1.5,
        "MAX_DELAY": 5.0,
        "POOL_CONNECTIONS_MULTIPLIER": 4,
        "POOL_MAXSIZE_MULTIPLIER": 4,
        "BASE_RETRY_DELAY": 1.0,
        "MAX_RETRY_DELAY": 60,
        "ADAPTIVE_CHUNK_THRESHOLDS": (10 * 1024 * 1024, 100 * 1024 * 1024),
        "CHUNK_SIZES": (8192, 65536, 262144),
        "BANDWIDTH_UPDATE_INTERVAL": 0.5,
        "BANDWIDTH_WINDOW_SECONDS": 5.0,
    }

    # Safe validation ranges for user configuration
    _VALIDATION_RULES = {
        "MAX_WORKERS": {"min": 1, "max": 20, "type": int},
        "RATE_LIMIT_DELAY": {"min": 0.1, "max": 5.0, "type": float},
        "MAX_RETRIES": {"min": 0, "max": 10, "type": int},
        "CHUNK_SIZE": {"min": 1024, "max": 1048576, "type": int},
        "API_TIMEOUT": {"min": 5, "max": 120, "type": int},
        "RETRY_DELAY": {"min": 0.5, "max": 30.0, "type": float},
        "CATALOG_SCRAPE_DELAY": {"min": 0.1, "max": 2.0, "type": float},
        "BASE_DELAY": {"min": 0.1, "max": 2.0, "type": float},
        "BACKOFF_MULTIPLIER": {"min": 1.0, "max": 3.0, "type": float},
        "MAX_DELAY": {"min": 1.0, "max": 30.0, "type": float},
        "POOL_CONNECTIONS_MULTIPLIER": {"min": 1, "max": 10, "type": int},
        "POOL_MAXSIZE_MULTIPLIER": {"min": 1, "max": 10, "type": int},
        "BASE_RETRY_DELAY": {"min": 0.5, "max": 10.0, "type": float},
        "MAX_RETRY_DELAY": {"min": 5.0, "max": 300.0, "type": float},
        "BANDWIDTH_UPDATE_INTERVAL": {"min": 0.1, "max": 2.0, "type": float},
        "BANDWIDTH_WINDOW_SECONDS": {"min": 1.0, "max": 30.0, "type": float},
    }

    # Global instance for backward compatibility
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self._config_path = pathlib.Path.home() / ".4charm" / "config.json"
        self._user_config = self._load_config()
        self._apply_config()

    @classmethod
    def get_config_path(cls) -> pathlib.Path:
        """Get the path to the user configuration file."""
        return pathlib.Path.home() / ".4charm" / "config.json"

    def _load_config(self) -> dict[str, Any]:
        """Load user configuration from file, creating default if needed."""
        try:
            if self._config_path.exists():
                with open(self._config_path, encoding="utf-8") as f:
                    user_config = json.load(f)
                self._validate_config(user_config)
                return user_config
            else:
                # Create default config file
                self._create_default_config()
                return {}
        except (json.JSONDecodeError, OSError) as e:
            # Log warning and use defaults if config is corrupted
            print(f"Warning: Could not load config from {self._config_path}: {e}")
            return {}

    def _create_default_config(self) -> None:
        """Create a default configuration file for user reference."""
        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            default_config = {
                "MAX_WORKERS": self._DEFAULTS["MAX_WORKERS"],
                "RATE_LIMIT_DELAY": 0.3,
                "MAX_RETRIES": 3,
                "CHUNK_SIZE": 8192,
                "API_TIMEOUT": 30,
                "POOL_CONNECTIONS_MULTIPLIER": 4,
                "POOL_MAXSIZE_MULTIPLIER": 4,
                "BASE_RETRY_DELAY": 1.0,
                "MAX_RETRY_DELAY": 60,
                "BANDWIDTH_UPDATE_INTERVAL": 0.5,
                "BANDWIDTH_WINDOW_SECONDS": 5.0,
            }

            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=2, sort_keys=True)
        except OSError as e:
            print(
                f"Warning: Could not create default config at {self._config_path}: {e}"
            )

    def _validate_config(self, config: dict[str, Any]) -> None:
        """Validate user configuration values against safe ranges."""
        for key, value in config.items():
            if key in self._VALIDATION_RULES:
                rules = self._VALIDATION_RULES[key]
                try:
                    # Type conversion
                    if rules["type"] is int:
                        value = int(value)
                    elif rules["type"] is float:
                        value = float(value)

                    # Range validation with safe numeric conversion
                    try:
                        value_num = float(value)
                        min_val = rules["min"]
                        max_val = rules["max"]

                        # Convert min/max to float safely
                        if isinstance(min_val, (int, float)):
                            min_num = float(min_val)
                        else:
                            min_num = float(str(min_val))

                        if isinstance(max_val, (int, float)):
                            max_num = float(max_val)
                        else:
                            max_num = float(str(max_val))

                        if value_num < min_num or value_num > max_num:
                            raise ValueError(
                                f"{key} must be between {rules['min']} and {rules['max']}, got {value}"
                            )
                    except (TypeError, ValueError) as conv_err:
                        raise ValueError(
                            f"Invalid numeric value for {key}: {conv_err}"
                        ) from None

                    # Update config with validated value
                    config[key] = value
                except (ValueError, TypeError) as e:
                    raise ValueError(f"Invalid value for {key}: {e}") from None

    def _apply_config(self) -> None:
        """Apply user configuration values, falling back to defaults."""
        # Set all default values first
        for key, value in self._DEFAULTS.items():
            setattr(self, key, value)

        # Apply user overrides
        for key, value in self._user_config.items():
            if key in self._DEFAULTS:
                setattr(self, key, value)

    def reload_config(self) -> None:
        """Reload configuration from file."""
        self._user_config = self._load_config()
        self._apply_config()

    @property
    def config_file_path(self) -> str:
        """Get the path to the configuration file."""
        return str(self._config_path)

    MEDIA_EXTENSIONS = {
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
        ".bmp",
        ".webm",
        ".mp4",
        ".mov",
        ".avi",
        ".mkv",
        ".pdf",
        ".txt",
        ".zip",
        ".rar",
    }

    PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}

    VIDEO_EXTENSIONS = {".webm", ".mp4", ".mov", ".avi", ".mkv"}

    USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"


# Global singleton instance
_global_config = None


def get_global_config() -> Config:
    """Get the global configuration instance."""
    global _global_config
    if _global_config is None:
        _global_config = Config()
    return _global_config


# Module-level attributes for backward compatibility
def __getattr__(name: str) -> Any:
    """Provide backward compatibility for module-level attribute access."""
    config = get_global_config()
    if hasattr(config, name):
        return getattr(config, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
