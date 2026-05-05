import pytest

from auralog.config import DEFAULT_MAX_QUEUE_SIZE, AuralogConfig


def test_config_defaults():
    cfg = AuralogConfig(api_key="k")
    assert cfg.api_key == "k"
    assert cfg.environment == "production"
    assert cfg.endpoint == "https://ingest.auralog.ai"
    assert cfg.flush_interval == 5.0
    assert cfg.capture_errors is True
    assert cfg.max_queue_size == DEFAULT_MAX_QUEUE_SIZE
    assert cfg.allow_insecure_endpoint is False


def test_config_environment_override():
    cfg = AuralogConfig(api_key="k", environment="staging")
    assert cfg.environment == "staging"


def test_config_overrides():
    cfg = AuralogConfig(
        api_key="k",
        environment="dev",
        endpoint="http://localhost:8787",
        flush_interval=1.5,
        capture_errors=False,
        allow_insecure_endpoint=True,
    )
    assert cfg.endpoint == "http://localhost:8787"
    assert cfg.flush_interval == 1.5
    assert cfg.capture_errors is False


def test_config_rejects_http_endpoint_by_default():
    with pytest.raises(ValueError, match="https://"):
        AuralogConfig(api_key="k", endpoint="http://insecure")


def test_config_accepts_http_endpoint_with_opt_in():
    cfg = AuralogConfig(api_key="k", endpoint="http://insecure", allow_insecure_endpoint=True)
    assert cfg.endpoint == "http://insecure"


def test_config_strips_trailing_slash_before_scheme_check():
    # Trailing-slash normalization shouldn't let a non-https URL slip past.
    with pytest.raises(ValueError, match="https://"):
        AuralogConfig(api_key="k", endpoint="http://insecure/")


def test_config_max_queue_size_override():
    cfg = AuralogConfig(api_key="k", max_queue_size=42)
    assert cfg.max_queue_size == 42


def test_config_rejects_zero_max_queue_size():
    # `deque(maxlen=0)` would silently swallow every non-error log; surface
    # the misconfiguration up front instead of quietly losing data.
    with pytest.raises(ValueError, match="max_queue_size"):
        AuralogConfig(api_key="k", max_queue_size=0)


def test_config_rejects_negative_max_queue_size():
    with pytest.raises(ValueError, match="max_queue_size"):
        AuralogConfig(api_key="k", max_queue_size=-1)


def test_config_accepts_uppercase_https_scheme():
    # Per RFC 3986 §3.1 URI schemes are case-insensitive.
    cfg = AuralogConfig(api_key="k", endpoint="HTTPS://ingest.example.com")
    assert cfg.endpoint == "HTTPS://ingest.example.com"


def test_config_accepts_mixed_case_https_scheme():
    cfg = AuralogConfig(api_key="k", endpoint="HtTpS://ingest.example.com")
    assert cfg.endpoint == "HtTpS://ingest.example.com"
