from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
import pytest
from deltalake import write_deltalake

from queo_data_platform.contracts.gold import (
    DATA_QUALITY_SUMMARY_SCHEMA,
    DATA_QUALITY_SUMMARY_TABLE_NAME,
    DEVICE_DAILY_SUMMARY_SCHEMA,
    DEVICE_DAILY_SUMMARY_TABLE_NAME,
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


def test_device_page_contains_total_metadata(
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
            },
            {
                "device_serial": "device-b",
            },
            {
                "device_serial": "device-c",
            },
        ],
    )

    service = QueryService(gold_dir=gold_dir)

    page = service.page_devices(
        limit=2,
        offset=0,
    )

    assert page.total == 3
    assert page.returned == 2
    assert page.limit == 2
    assert page.offset == 0
    assert page.has_more
    assert page.next_offset == 2


def test_last_device_page_has_no_next_offset(
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
            },
            {
                "device_serial": "device-b",
            },
            {
                "device_serial": "device-c",
            },
        ],
    )

    service = QueryService(gold_dir=gold_dir)

    page = service.page_devices(
        limit=2,
        offset=2,
    )

    assert page.total == 3
    assert page.returned == 1
    assert not page.has_more
    assert page.next_offset is None


def test_daily_summaries_filter_device_and_dates(
    tmp_path: Path,
) -> None:
    gold_dir = tmp_path / "03_gold"

    write_gold_table(
        gold_dir,
        table_name=(DEVICE_DAILY_SUMMARY_TABLE_NAME),
        schema=DEVICE_DAILY_SUMMARY_SCHEMA,
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
                "event_date": "2026-08-19",
                "device_serial": "device-b",
                "message_count": 40,
            },
        ],
    )

    service = QueryService(gold_dir=gold_dir)

    result = service.list_daily_summaries(
        device_serial="device-a",
        start_date="2026-08-19",
        end_date="2026-08-20",
    )

    assert result["event_date"].tolist() == [
        "2026-08-20",
        "2026-08-19",
    ]

    assert result["message_count"].tolist() == [
        30,
        20,
    ]


def test_daily_summary_page_counts_filtered_rows(
    tmp_path: Path,
) -> None:
    gold_dir = tmp_path / "03_gold"

    write_gold_table(
        gold_dir,
        table_name=(DEVICE_DAILY_SUMMARY_TABLE_NAME),
        schema=DEVICE_DAILY_SUMMARY_SCHEMA,
        partition_by="event_date",
        rows=[
            {
                "event_date": "2026-08-18",
                "device_serial": "device-a",
            },
            {
                "event_date": "2026-08-19",
                "device_serial": "device-a",
            },
            {
                "event_date": "2026-08-20",
                "device_serial": "device-a",
            },
            {
                "event_date": "2026-08-20",
                "device_serial": "device-b",
            },
        ],
    )

    service = QueryService(gold_dir=gold_dir)

    page = service.page_daily_summaries(
        device_serial="device-a",
        limit=1,
        offset=1,
    )

    assert page.total == 3
    assert page.returned == 1
    assert page.has_more
    assert page.next_offset == 2


def test_quality_summaries_filter_and_order_dates(
    tmp_path: Path,
) -> None:
    gold_dir = tmp_path / "03_gold"

    write_gold_table(
        gold_dir,
        table_name=(DATA_QUALITY_SUMMARY_TABLE_NAME),
        schema=DATA_QUALITY_SUMMARY_SCHEMA,
        partition_by="metric_date",
        rows=[
            {
                "metric_date": "2026-08-18",
                "total_event_count": 10,
            },
            {
                "metric_date": "2026-08-19",
                "total_event_count": 20,
            },
            {
                "metric_date": "2026-08-20",
                "total_event_count": 30,
            },
        ],
    )

    service = QueryService(gold_dir=gold_dir)

    result = service.list_quality_summaries(
        start_date="2026-08-19",
        end_date="2026-08-20",
    )

    assert result["metric_date"].tolist() == [
        "2026-08-20",
        "2026-08-19",
    ]


def test_quality_summary_page_contains_total(
    tmp_path: Path,
) -> None:
    gold_dir = tmp_path / "03_gold"

    write_gold_table(
        gold_dir,
        table_name=(DATA_QUALITY_SUMMARY_TABLE_NAME),
        schema=DATA_QUALITY_SUMMARY_SCHEMA,
        partition_by="metric_date",
        rows=[
            {
                "metric_date": "2026-08-18",
            },
            {
                "metric_date": "2026-08-19",
            },
            {
                "metric_date": "2026-08-20",
            },
        ],
    )

    service = QueryService(gold_dir=gold_dir)

    page = service.page_quality_summaries(
        limit=2,
        offset=0,
    )

    assert page.total == 3
    assert page.returned == 2
    assert page.has_more
    assert page.next_offset == 2


def test_route_page_counts_filtered_points(
    tmp_path: Path,
) -> None:
    gold_dir = tmp_path / "03_gold"

    write_gold_table(
        gold_dir,
        table_name=(DEVICE_ROUTE_POINTS_TABLE_NAME),
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
                "device_serial": "device-b",
                "point_sequence": 1,
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

    page = service.page_route_points(
        "device-a",
        limit=1,
        offset=0,
    )

    assert page.total == 2
    assert page.returned == 1
    assert page.has_more


def test_summary_queries_reject_reverse_date_range(
    tmp_path: Path,
) -> None:
    service = QueryService(gold_dir=tmp_path)

    with pytest.raises(
        ValueError,
        match="start_date",
    ):
        service.list_daily_summaries(
            start_date="2026-08-20",
            end_date="2026-08-19",
        )

    with pytest.raises(
        ValueError,
        match="start_date",
    ):
        service.list_quality_summaries(
            start_date="2026-08-20",
            end_date="2026-08-19",
        )
