from collections.abc import Iterator
from datetime import UTC, datetime
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
    DEVICE_LAST_POSITION_SCHEMA,
    DEVICE_LAST_POSITION_TABLE_NAME,
    DEVICE_ROUTE_POINTS_SCHEMA,
    DEVICE_ROUTE_POINTS_TABLE_NAME,
    DIM_DEVICE_SCHEMA,
    DIM_DEVICE_TABLE_NAME,
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
    partition_by: str | None = None,
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

    if partition_by is None:
        write_deltalake(
            table_path,
            table,
            mode="overwrite",
        )
        return

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


def test_health_does_not_require_gold(
    api_client: tuple[
        TestClient,
        Path,
    ],
) -> None:
    client, _gold_dir = api_client

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_devices_returns_page(
    api_client: tuple[
        TestClient,
        Path,
    ],
) -> None:
    client, gold_dir = api_client

    write_gold_table(
        gold_dir,
        table_name=DIM_DEVICE_TABLE_NAME,
        schema=DIM_DEVICE_SCHEMA,
        rows=[
            {
                "device_serial": "device-a",
                "current_imei": ("354173560222769"),
            },
            {
                "device_serial": "device-b",
                "current_imei": ("359000000000001"),
            },
        ],
    )

    response = client.get(
        "/api/v1/devices",
        params={
            "limit": 1,
            "offset": 0,
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["total"] == 2
    assert payload["returned"] == 1
    assert payload["has_more"] is True
    assert payload["next_offset"] == 1

    assert payload["items"][0]["device_serial"] == "device-a"


def test_unknown_device_returns_404(
    api_client: tuple[
        TestClient,
        Path,
    ],
) -> None:
    client, gold_dir = api_client

    write_gold_table(
        gold_dir,
        table_name=DIM_DEVICE_TABLE_NAME,
        schema=DIM_DEVICE_SCHEMA,
        rows=[{"device_serial": "device-a"}],
    )

    response = client.get("/api/v1/devices/unknown")

    assert response.status_code == 404


def test_last_position_returns_device_position(
    api_client: tuple[
        TestClient,
        Path,
    ],
) -> None:
    client, gold_dir = api_client

    write_gold_table(
        gold_dir,
        table_name=(DEVICE_LAST_POSITION_TABLE_NAME),
        schema=DEVICE_LAST_POSITION_SCHEMA,
        rows=[
            {
                "device_serial": "device-a",
                "last_position_date": ("2026-08-20"),
                "last_position_at": datetime(
                    2026,
                    8,
                    20,
                    12,
                    0,
                    tzinfo=UTC,
                ),
                "latitude": -3.73,
                "longitude": -38.52,
            }
        ],
    )

    response = client.get("/api/v1/devices/device-a/last-position")

    assert response.status_code == 200

    payload = response.json()

    assert payload["device_serial"] == "device-a"

    assert payload["latitude"] == -3.73
    assert payload["longitude"] == -38.52


def test_route_returns_paginated_points(
    api_client: tuple[
        TestClient,
        Path,
    ],
) -> None:
    client, gold_dir = api_client

    write_gold_table(
        gold_dir,
        table_name=(DEVICE_ROUTE_POINTS_TABLE_NAME),
        schema=DEVICE_ROUTE_POINTS_SCHEMA,
        partition_by="event_date",
        rows=[
            {
                "event_date": "2026-08-19",
                "device_serial": "device-a",
                "point_sequence": 1,
                "event_timestamp": datetime(
                    2026,
                    8,
                    19,
                    10,
                    0,
                    tzinfo=UTC,
                ),
            },
            {
                "event_date": "2026-08-20",
                "device_serial": "device-a",
                "point_sequence": 2,
                "event_timestamp": datetime(
                    2026,
                    8,
                    20,
                    10,
                    0,
                    tzinfo=UTC,
                ),
            },
        ],
    )

    response = client.get(
        ("/api/v1/devices/device-a/route"),
        params={
            "start_date": ("2026-08-20"),
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["total"] == 1
    assert payload["returned"] == 1

    assert payload["items"][0]["event_date"] == "2026-08-20"


def test_reverse_route_date_range_returns_422(
    api_client: tuple[
        TestClient,
        Path,
    ],
) -> None:
    client, _gold_dir = api_client

    response = client.get(
        ("/api/v1/devices/device-a/route"),
        params={
            "start_date": ("2026-08-20"),
            "end_date": ("2026-08-19"),
        },
    )

    assert response.status_code == 422


def test_missing_gold_returns_503(
    api_client: tuple[
        TestClient,
        Path,
    ],
) -> None:
    client, _gold_dir = api_client

    response = client.get("/api/v1/devices")

    assert response.status_code == 503

    assert response.json() == {"detail": ("Gold data is not available.")}
