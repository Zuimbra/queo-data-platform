from queo_data_platform.config.settings import (
    load_settings,
)


def test_api_cors_origins_are_empty_by_default(
    monkeypatch,
) -> None:
    monkeypatch.delenv(
        "QUEO_API_CORS_ORIGINS",
        raising=False,
    )

    settings = load_settings()

    assert settings.api_cors_origins == ()


def test_api_cors_origins_are_parsed_from_environment(
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "QUEO_API_CORS_ORIGINS",
        ("http://localhost:5173, https://app.example.com, http://localhost:5173"),
    )

    settings = load_settings()

    assert settings.api_cors_origins == (
        "http://localhost:5173",
        "https://app.example.com",
    )
