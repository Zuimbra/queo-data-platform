import pyarrow as pa

from queo_data_platform.contracts.silver import (
    DEVICE_IDENTITY_SCHEMA,
    DEVICE_IDENTITY_TABLE_NAME,
    REJECTED_LOGS_SCHEMA,
    REJECTED_LOGS_TABLE_NAME,
    SILVER_EVENT_PARTITION_COLUMN,
    SILVER_LINEAGE_COLUMNS,
    SILVER_REJECTION_PARTITION_COLUMN,
    TELEMETRY_SCHEMA,
    TELEMETRY_TABLE_NAME,
)
from queo_data_platform.contracts.tracker import (
    BRONZE_METADATA_COLUMNS,
)


def test_silver_table_names() -> None:
    assert TELEMETRY_TABLE_NAME == "telemetry_events"

    assert DEVICE_IDENTITY_TABLE_NAME == "device_identity_events"

    assert REJECTED_LOGS_TABLE_NAME == "rejected_logs"


def test_silver_partition_columns() -> None:
    assert SILVER_EVENT_PARTITION_COLUMN == "event_date"

    assert SILVER_REJECTION_PARTITION_COLUMN == "rejection_date"


def test_silver_preserves_bronze_lineage_contract() -> None:
    assert SILVER_LINEAGE_COLUMNS == BRONZE_METADATA_COLUMNS

    assert SILVER_LINEAGE_COLUMNS == (
        "source_file",
        "source_file_hash",
        "source_row_number",
        "row_id",
        "batch_id",
        "ingested_at",
        "ingestion_date",
    )


def test_silver_partition_columns_are_strings() -> None:
    assert TELEMETRY_SCHEMA.field("event_date").type == pa.string()

    assert DEVICE_IDENTITY_SCHEMA.field("event_date").type == pa.string()

    assert REJECTED_LOGS_SCHEMA.field("rejection_date").type == pa.string()


def test_identity_resolution_method_is_persisted() -> None:
    assert TELEMETRY_SCHEMA.field("device_resolution_method").type == pa.string()

    assert DEVICE_IDENTITY_SCHEMA.field("device_resolution_method").type == pa.string()

    assert REJECTED_LOGS_SCHEMA.field("device_resolution_method").type == pa.string()
