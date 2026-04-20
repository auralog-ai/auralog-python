from auralog.config import AuralogConfig


def test_config_defaults():
    cfg = AuralogConfig(api_key="k", environment="prod")
    assert cfg.api_key == "k"
    assert cfg.environment == "prod"
    assert cfg.endpoint == "https://ingest.auralog.ai"
    assert cfg.flush_interval == 5.0
    assert cfg.capture_errors is True


def test_config_overrides():
    cfg = AuralogConfig(
        api_key="k",
        environment="dev",
        endpoint="http://localhost:8787",
        flush_interval=1.5,
        capture_errors=False,
    )
    assert cfg.endpoint == "http://localhost:8787"
    assert cfg.flush_interval == 1.5
    assert cfg.capture_errors is False
