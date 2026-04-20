from __future__ import annotations

from dataclasses import dataclass

DEFAULT_ENDPOINT = "https://ingest.auralog.ai"
DEFAULT_FLUSH_INTERVAL_SECONDS = 5.0


@dataclass
class AuralogConfig:
    api_key: str
    environment: str
    endpoint: str = DEFAULT_ENDPOINT
    flush_interval: float = DEFAULT_FLUSH_INTERVAL_SECONDS
    capture_errors: bool = True
