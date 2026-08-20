from collections.abc import Iterator
from pathlib import Path

import pyarrow as pa
import pytest
from deltalake import write_deltalake
from fastapi.testclient import TestClient

from queo_data_platform.api.app import (
    create_app,
)
from queo_data_platform.api.dependencies import (
    get_query_service,
)
from queo_data_platform.contracts.gold import (
    DATA_QUALITY_SUMMARY_SCHEMA,
    DATA_QUALITY_SUMMARY_TABLE_NAME,
    DEVICE_DAILY_SUMMARY_SCHEMA,
    DEVICE_DAILY_SUMMARY_TABLE_NAME,
)
from queo_data_platform.query import (
    QueryService,
)


def write_gold_table(
    gold_dir: Path,
    *,
    table_name: str,
    schema: pa.Schema,
    rows: list[dict[str, object]],
    partition_by: str,
) -> None:
    table_path = gold_dir / table_name

    table_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    table = pa.Table.from_pylist(
        rows,
        schema=schema,
    )

    write_deltalake(
        table_path,
        table,
        mode="overwrite",
        partition_by=[partition_by],
    )


@pytest.fixture
def api_client(
    tmp_path: Path,
) -> Iterator[
    tuple[
        TestClient,
        Path,
    ]
]:
    gold_dir = tmp_path / "03_gold"

    service = QueryService(gold_dir=gold_dir)

    application = create_app()

    def override_query_service() -> QueryService:
        return service

    application.dependency_overrides[get_query_service] = override_query_service

    with TestClient(application) as client:
        yield (
            client,
            gold_dir,
        )


def test_daily_summaries_return_filtered_page(
    api_client: tuple[
        TestClient,
        Path,
    ],
) -> None:
    client, gold_dir = api_client

    write_gold_table(
        gold_dir,
        table_name=(DEVICE_DAILY_SUMMARY_TABLE_NAME),
        schema=(DEVICE_DAILY_SUMMARY_SCHEMA),
        partition_by="event_date",
        rows=[
            {
                "event_date": "2026-08-18",
                "device_serial": "device-a",
                "message_count": 10,
            },
            {
                "event_date": "2026-08-19",
                "device_serial": "device-a",
                "message_count": 20,
            },
            {
                "event_date": "2026-08-20",
                "device_serial": "device-a",
                "message_count": 30,
            },
            {
                "event_date": "2026-08-20",
                "device_serial": "device-b",
                "message_count": 40,
            },
        ],
    )

    response = client.get(
        "/api/v1/daily-summaries",
        params={
            "device_serial": "device-a",
            "start_date": "2026-08-19",
            "end_date": "2026-08-20",
            "limit": 1,
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["total"] == 2
    assert payload["returned"] == 1
    assert payload["has_more"] is True

    assert payload["items"][0]["event_date"] == "2026-08-20"

    assert payload["items"][0]["message_count"] == 30


def test_data_quality_returns_filtered_page(
    api_client: tuple[
        TestClient,
        Path,
    ],
) -> None:
    client, gold_dir = api_client

    write_gold_table(
        gold_dir,
        table_name=(DATA_QUALITY_SUMMARY_TABLE_NAME),
        schema=(DATA_QUALITY_SUMMARY_SCHEMA),
        partition_by="metric_date",
        rows=[
            {
                "metric_date": "2026-08-18",
                "total_event_count": 10,
                "rejected_event_count": 2,
            },
            {
                "metric_date": "2026-08-19",
                "total_event_count": 20,
                "rejected_event_count": 3,
            },
            {
                "metric_date": "2026-08-20",
                "total_event_count": 30,
                "rejected_event_count": 4,
            },
        ],
    )

    response = client.get(
        "/api/v1/data-quality",
        params={
            "start_date": "2026-08-19",
            "end_date": "2026-08-20",
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["total"] == 2
    assert payload["returned"] == 2

    assert [item["metric_date"] for item in payload["items"]] == [
        "2026-08-20",
        "2026-08-19",
    ]


def test_summary_reverse_date_ranges_return_422(
    api_client: tuple[
        TestClient,
        Path,
    ],
) -> None:
    client, _gold_dir = api_client

    daily_response = client.get(
        "/api/v1/daily-summaries",
        params={
            "start_date": "2026-08-20",
            "end_date": "2026-08-19",
        },
    )

    quality_response = client.get(
        "/api/v1/data-quality",
        params={
            "start_date": "2026-08-20",
            "end_date": "2026-08-19",
        },
    )

    assert daily_response.status_code == 422

    assert quality_response.status_code == 422


def test_cors_allows_configured_origin(
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "QUEO_API_CORS_ORIGINS",
        "http://localhost:5173",
    )

    application = create_app()

    with TestClient(application) as client:
        response = client.options(
            "/api/v1/devices",
            headers={
                "Origin": ("http://localhost:5173"),
                ("Access-Control-Request-Method"): "GET",
            },
        )

    assert response.status_code == 200

    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
