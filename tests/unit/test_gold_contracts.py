from queo_data_platform.contracts.gold import (
    DATA_QUALITY_SUMMARY_TABLE_NAME,
    DEVICE_DAILY_SUMMARY_TABLE_NAME,
    DEVICE_LAST_POSITION_TABLE_NAME,
    DEVICE_ROUTE_POINTS_TABLE_NAME,
    DIM_DEVICE_TABLE_NAME,
    GOLD_DEVICE_KEY,
    GOLD_ENTITY_TABLES,
    GOLD_EVENT_PARTITION_COLUMN,
    GOLD_PARTITIONED_TABLES,
    GOLD_QUALITY_PARTITION_COLUMN,
)


def test_gold_table_names() -> None:
    assert DIM_DEVICE_TABLE_NAME == "dim_device"

    assert DEVICE_LAST_POSITION_TABLE_NAME == "device_last_position"

    assert DEVICE_ROUTE_POINTS_TABLE_NAME == "device_route_points"

    assert DEVICE_DAILY_SUMMARY_TABLE_NAME == "device_daily_summary"

    assert DATA_QUALITY_SUMMARY_TABLE_NAME == "data_quality_summary"


def test_gold_partition_columns() -> None:
    assert GOLD_EVENT_PARTITION_COLUMN == "event_date"

    assert GOLD_QUALITY_PARTITION_COLUMN == "metric_date"


def test_gold_partitioned_tables() -> None:
    assert GOLD_PARTITIONED_TABLES == {
        "device_route_points": "event_date",
        "device_daily_summary": "event_date",
        "data_quality_summary": "metric_date",
    }


def test_gold_entity_tables() -> None:
    assert GOLD_ENTITY_TABLES == (
        "dim_device",
        "device_last_position",
    )

    assert GOLD_DEVICE_KEY == ("device_serial")
