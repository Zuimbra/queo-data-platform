from pathlib import Path

import pandas as pd
import pyarrow as pa
from deltalake import DeltaTable

from queo_data_platform.silver.writer import (
    dataframe_to_arrow,
    write_full_silver_table,
    write_incremental_silver_partitions,
)

TEST_SCHEMA = pa.schema(
    [
        pa.field(
            "event_date",
            pa.string(),
        ),
        pa.field(
            "device_serial",
            pa.string(),
        ),
        pa.field(
            "value",
            pa.float64(),
        ),
    ]
)


def test_dataframe_to_arrow_preserves_string_type_for_nulls() -> None:
    dataframe = pd.DataFrame(
        {
            "event_date": ["2026-08-17"],
            "device_serial": [None],
            "value": [1.0],
        }
    )

    table = dataframe_to_arrow(
        dataframe,
        TEST_SCHEMA,
    )

    assert table.schema.field("device_serial").type == pa.string()


def test_full_write_creates_partitioned_table(
    tmp_path: Path,
) -> None:
    table_path = tmp_path / "telemetry_events"

    dataframe = pd.DataFrame(
        {
            "event_date": [
                "2026-08-17",
                "2026-08-18",
            ],
            "device_serial": [
                "1",
                "2",
            ],
            "value": [
                10.0,
                20.0,
            ],
        }
    )

    table = dataframe_to_arrow(
        dataframe,
        TEST_SCHEMA,
    )

    rows_written = write_full_silver_table(
        table_path,
        table,
        partition_by="event_date",
    )

    assert rows_written == 2

    delta_table = DeltaTable(str(table_path))

    assert delta_table.metadata().partition_columns == ["event_date"]


def test_incremental_write_replaces_only_affected_partition(
    tmp_path: Path,
) -> None:
    table_path = tmp_path / "telemetry_events"

    initial = dataframe_to_arrow(
        pd.DataFrame(
            {
                "event_date": [
                    "2026-08-17",
                    "2026-08-18",
                ],
                "device_serial": [
                    "1",
                    "2",
                ],
                "value": [
                    10.0,
                    20.0,
                ],
            }
        ),
        TEST_SCHEMA,
    )

    write_full_silver_table(
        table_path,
        initial,
        partition_by="event_date",
    )

    replacement = dataframe_to_arrow(
        pd.DataFrame(
            {
                "event_date": ["2026-08-17"],
                "device_serial": ["1"],
                "value": [99.0],
            }
        ),
        TEST_SCHEMA,
    )

    write_incremental_silver_partitions(
        table_path,
        replacement,
        partition_by="event_date",
        affected_partitions=("2026-08-17",),
    )

    dataframe = DeltaTable(str(table_path)).to_pandas()

    day_17 = dataframe.loc[dataframe["event_date"] == "2026-08-17"]

    day_18 = dataframe.loc[dataframe["event_date"] == "2026-08-18"]

    assert len(day_17) == 1

    assert day_17.iloc[0]["value"] == 99.0

    assert day_18.iloc[0]["value"] == 20.0


def test_empty_rebuilt_partition_removes_old_rows(
    tmp_path: Path,
) -> None:
    table_path = tmp_path / "telemetry_events"

    initial = dataframe_to_arrow(
        pd.DataFrame(
            {
                "event_date": [
                    "2026-08-17",
                    "2026-08-18",
                ],
                "device_serial": [
                    "1",
                    "2",
                ],
                "value": [
                    10.0,
                    20.0,
                ],
            }
        ),
        TEST_SCHEMA,
    )

    write_full_silver_table(
        table_path,
        initial,
        partition_by="event_date",
    )

    empty = dataframe_to_arrow(
        pd.DataFrame(
            {
                "event_date": [],
                "device_serial": [],
                "value": [],
            }
        ),
        TEST_SCHEMA,
    )

    write_incremental_silver_partitions(
        table_path,
        empty,
        partition_by="event_date",
        affected_partitions=("2026-08-17",),
    )

    dataframe = DeltaTable(str(table_path)).to_pandas()

    assert set(dataframe["event_date"]) == {
        "2026-08-18",
    }
