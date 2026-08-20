from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
import pytest
from deltalake import write_deltalake

from queo_data_platform.contracts.gold import (
    DEVICE_LAST_POSITION_SCHEMA,
    DEVICE_LAST_POSITION_TABLE_NAME,
    DEVICE_ROUTE_POINTS_SCHEMA,
    DEVICE_ROUTE_POINTS_TABLE_NAME,
    DIM_DEVICE_SCHEMA,
    DIM_DEVICE_TABLE_NAME,
)
from queo_data_platform.query.service import (
    MAX_QUERY_LIMIT,
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


def test_list_devices_is_sorted_and_paginated(
    tmp_path: Path,
) -> None:
    gold_dir = tmp_path / "03_gold"

    write_gold_table(
        gold_dir,
        table_name=DIM_DEVICE_TABLE_NAME,
        schema=DIM_DEVICE_SCHEMA,
        rows=[
            {
                "device_serial": "device-c",
            },
            {
                "device_serial": "device-a",
            },
            {
                "device_serial": "device-b",
            },
        ],
    )

    service = QueryService(gold_dir=gold_dir)

    result = service.list_devices(
        limit=2,
        offset=1,
    )

    assert result["device_serial"].tolist() == [
        "device-b",
        "device-c",
    ]


def test_get_device_returns_exact_match(
    tmp_path: Path,
) -> None:
    gold_dir = tmp_path / "03_gold"

    write_gold_table(
        gold_dir,
        table_name=DIM_DEVICE_TABLE_NAME,
        schema=DIM_DEVICE_SCHEMA,
        rows=[
            {
                "device_serial": "device-a",
                "current_imei": "354173560222769",
            },
            {
                "device_serial": "device-b",
                "current_imei": "359000000000001",
            },
        ],
    )

    service = QueryService(gold_dir=gold_dir)

    result = service.get_device("device-b")

    assert len(result) == 1

    assert (
        result.loc[
            0,
            "device_serial",
        ]
        == "device-b"
    )

    assert (
        result.loc[
            0,
            "current_imei",
        ]
        == "359000000000001"
    )


def test_get_device_returns_empty_dataframe_when_unknown(
    tmp_path: Path,
) -> None:
    gold_dir = tmp_path / "03_gold"

    write_gold_table(
        gold_dir,
        table_name=DIM_DEVICE_TABLE_NAME,
        schema=DIM_DEVICE_SCHEMA,
        rows=[
            {
                "device_serial": "device-a",
            }
        ],
    )

    service = QueryService(gold_dir=gold_dir)

    result = service.get_device("unknown-device")

    assert result.empty


def test_list_last_positions_can_filter_device(
    tmp_path: Path,
) -> None:
    gold_dir = tmp_path / "03_gold"

    write_gold_table(
        gold_dir,
        table_name=DEVICE_LAST_POSITION_TABLE_NAME,
        schema=DEVICE_LAST_POSITION_SCHEMA,
        rows=[
            {
                "device_serial": "device-a",
                "last_position_date": "2026-08-20",
                "last_position_at": datetime(
                    2026,
                    8,
                    20,
                    10,
                    0,
                    tzinfo=UTC,
                ),
                "latitude": -3.73,
                "longitude": -38.52,
            },
            {
                "device_serial": "device-b",
                "last_position_date": "2026-08-20",
                "last_position_at": datetime(
                    2026,
                    8,
                    20,
                    11,
                    0,
                    tzinfo=UTC,
                ),
                "latitude": -3.74,
                "longitude": -38.53,
            },
        ],
    )

    service = QueryService(gold_dir=gold_dir)

    result = service.list_last_positions(device_serial="device-a")

    assert len(result) == 1

    assert (
        result.loc[
            0,
            "device_serial",
        ]
        == "device-a"
    )


def test_get_last_position_returns_exact_device(
    tmp_path: Path,
) -> None:
    gold_dir = tmp_path / "03_gold"

    write_gold_table(
        gold_dir,
        table_name=DEVICE_LAST_POSITION_TABLE_NAME,
        schema=DEVICE_LAST_POSITION_SCHEMA,
        rows=[
            {
                "device_serial": "device-a",
                "last_position_date": "2026-08-20",
                "last_position_at": datetime(
                    2026,
                    8,
                    20,
                    10,
                    0,
                    tzinfo=UTC,
                ),
                "latitude": -3.73,
                "longitude": -38.52,
            }
        ],
    )

    service = QueryService(gold_dir=gold_dir)

    result = service.get_last_position("device-a")

    assert len(result) == 1

    assert (
        result.loc[
            0,
            "device_serial",
        ]
        == "device-a"
    )


def test_route_points_are_filtered_and_ordered(
    tmp_path: Path,
) -> None:
    gold_dir = tmp_path / "03_gold"

    write_gold_table(
        gold_dir,
        table_name=DEVICE_ROUTE_POINTS_TABLE_NAME,
        schema=DEVICE_ROUTE_POINTS_SCHEMA,
        partition_by="event_date",
        rows=[
            {
                "event_date": "2026-08-18",
                "device_serial": "device-a",
                "point_sequence": 1,
                "event_timestamp": datetime(
                    2026,
                    8,
                    18,
                    10,
                    0,
                    tzinfo=UTC,
                ),
                "latitude": -3.70,
                "longitude": -38.50,
            },
            {
                "event_date": "2026-08-20",
                "device_serial": "device-a",
                "point_sequence": 2,
                "event_timestamp": datetime(
                    2026,
                    8,
                    20,
                    11,
                    0,
                    tzinfo=UTC,
                ),
                "latitude": -3.72,
                "longitude": -38.52,
            },
            {
                "event_date": "2026-08-19",
                "device_serial": "device-a",
                "point_sequence": 1,
                "event_timestamp": datetime(
                    2026,
                    8,
                    19,
                    9,
                    0,
                    tzinfo=UTC,
                ),
                "latitude": -3.71,
                "longitude": -38.51,
            },
            {
                "event_date": "2026-08-19",
                "device_serial": "device-b",
                "point_sequence": 1,
                "event_timestamp": datetime(
                    2026,
                    8,
                    19,
                    8,
                    0,
                    tzinfo=UTC,
                ),
                "latitude": -3.80,
                "longitude": -38.60,
            },
        ],
    )

    service = QueryService(gold_dir=gold_dir)

    result = service.list_route_points(
        "device-a",
        start_date="2026-08-19",
        end_date="2026-08-20",
    )

    assert result["event_date"].tolist() == [
        "2026-08-19",
        "2026-08-20",
    ]

    assert result["device_serial"].tolist() == [
        "device-a",
        "device-a",
    ]


def test_route_points_support_pagination(
    tmp_path: Path,
) -> None:
    gold_dir = tmp_path / "03_gold"

    write_gold_table(
        gold_dir,
        table_name=DEVICE_ROUTE_POINTS_TABLE_NAME,
        schema=DEVICE_ROUTE_POINTS_SCHEMA,
        partition_by="event_date",
        rows=[
            {
                "event_date": "2026-08-20",
                "device_serial": "device-a",
                "point_sequence": 1,
                "event_timestamp": datetime(
                    2026,
                    8,
                    20,
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
                    11,
                    0,
                    tzinfo=UTC,
                ),
            },
            {
                "event_date": "2026-08-20",
                "device_serial": "device-a",
                "point_sequence": 3,
                "event_timestamp": datetime(
                    2026,
                    8,
                    20,
                    12,
                    0,
                    tzinfo=UTC,
                ),
            },
        ],
    )

    service = QueryService(gold_dir=gold_dir)

    result = service.list_route_points(
        "device-a",
        limit=1,
        offset=1,
    )

    assert len(result) == 1

    assert (
        result.loc[
            0,
            "point_sequence",
        ]
        == 2
    )


def test_query_rejects_invalid_pagination(
    tmp_path: Path,
) -> None:
    service = QueryService(gold_dir=tmp_path)

    with pytest.raises(
        ValueError,
        match="limit",
    ):
        service.list_devices(limit=0)

    with pytest.raises(
        ValueError,
        match="limit",
    ):
        service.list_devices(limit=(MAX_QUERY_LIMIT + 1))

    with pytest.raises(
        ValueError,
        match="offset",
    ):
        service.list_devices(offset=-1)


def test_route_query_rejects_invalid_date_range(
    tmp_path: Path,
) -> None:
    service = QueryService(gold_dir=tmp_path)

    with pytest.raises(
        ValueError,
        match="start_date",
    ):
        service.list_route_points(
            "device-a",
            start_date="20-08-2026",
        )

    with pytest.raises(
        ValueError,
        match="start_date must be less",
    ):
        service.list_route_points(
            "device-a",
            start_date="2026-08-20",
            end_date="2026-08-19",
        )


def test_missing_gold_table_is_rejected(
    tmp_path: Path,
) -> None:
    service = QueryService(gold_dir=tmp_path / "03_gold")

    with pytest.raises(
        FileNotFoundError,
        match="Gold Delta Table",
    ):
        service.list_devices()
