import pyarrow as pa

from queo_data_platform.contracts.gold import (
    DATA_QUALITY_SUMMARY_SCHEMA,
    DATA_QUALITY_SUMMARY_TABLE_NAME,
    DEVICE_DAILY_SUMMARY_SCHEMA,
    DEVICE_DAILY_SUMMARY_TABLE_NAME,
    DEVICE_LAST_POSITION_SCHEMA,
    DEVICE_LAST_POSITION_TABLE_NAME,
    DEVICE_ROUTE_POINTS_SCHEMA,
    DEVICE_ROUTE_POINTS_TABLE_NAME,
    DIM_DEVICE_SCHEMA,
    DIM_DEVICE_TABLE_NAME,
    GOLD_DEVICE_KEY,
    GOLD_ENTITY_TABLES,
    GOLD_EVENT_PARTITION_COLUMN,
    GOLD_PARTITIONED_TABLES,
    GOLD_QUALITY_PARTITION_COLUMN,
    GOLD_TABLE_SCHEMAS,
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
        "device_route_points": ("event_date"),
        "device_daily_summary": ("event_date"),
        "data_quality_summary": ("metric_date"),
    }


def test_gold_entity_tables() -> None:
    assert GOLD_ENTITY_TABLES == (
        "dim_device",
        "device_last_position",
    )

    assert GOLD_DEVICE_KEY == "device_serial"


def test_all_gold_tables_have_schema() -> None:
    assert set(GOLD_TABLE_SCHEMAS) == {
        DIM_DEVICE_TABLE_NAME,
        DEVICE_LAST_POSITION_TABLE_NAME,
        DEVICE_ROUTE_POINTS_TABLE_NAME,
        DEVICE_DAILY_SUMMARY_TABLE_NAME,
        DATA_QUALITY_SUMMARY_TABLE_NAME,
    }


def test_gold_partition_columns_are_strings() -> None:
    assert DEVICE_ROUTE_POINTS_SCHEMA.field("event_date").type == pa.string()

    assert DEVICE_DAILY_SUMMARY_SCHEMA.field("event_date").type == pa.string()

    assert DATA_QUALITY_SUMMARY_SCHEMA.field("metric_date").type == pa.string()


def test_gold_entity_keys_are_strings() -> None:
    assert DIM_DEVICE_SCHEMA.field(GOLD_DEVICE_KEY).type == pa.string()

    assert DEVICE_LAST_POSITION_SCHEMA.field(GOLD_DEVICE_KEY).type == pa.string()


def test_gold_count_fields_are_int64() -> None:
    assert DIM_DEVICE_SCHEMA.field("telemetry_event_count").type == pa.int64()

    assert DEVICE_DAILY_SUMMARY_SCHEMA.field("message_count").type == pa.int64()

    assert DATA_QUALITY_SUMMARY_SCHEMA.field("total_event_count").type == pa.int64()


def test_gold_geospatial_fields_are_float64() -> None:
    assert DEVICE_LAST_POSITION_SCHEMA.field("latitude").type == pa.float64()

    assert DEVICE_LAST_POSITION_SCHEMA.field("longitude").type == pa.float64()

    assert DEVICE_ROUTE_POINTS_SCHEMA.field("latitude").type == pa.float64()

    assert DEVICE_ROUTE_POINTS_SCHEMA.field("longitude").type == pa.float64()


def test_gold_boolean_fields_are_boolean() -> None:
    assert DIM_DEVICE_SCHEMA.field("has_telemetry_event").type == pa.bool_()

    assert DEVICE_ROUTE_POINTS_SCHEMA.field("is_moving").type == pa.bool_()

    assert (
        DEVICE_DAILY_SUMMARY_SCHEMA.field("has_odometer_regression").type == pa.bool_()
    )
