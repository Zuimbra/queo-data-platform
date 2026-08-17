from pathlib import Path

import pandas as pd
import pyarrow as pa
import pytest
from deltalake import DeltaTable

from queo_data_platform.gold.writer import (
    align_gold_table,
    write_gold_entity_table,
    write_gold_partitioned_table,
)

ENTITY_SCHEMA = pa.schema(
    [
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


PARTITIONED_SCHEMA = pa.schema(
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


def to_arrow(
    dataframe: pd.DataFrame,
) -> pa.Table:
    return pa.Table.from_pandas(
        dataframe,
        preserve_index=False,
    )


def test_align_empty_gold_table_preserves_schema() -> None:
    table = pa.table(
        {
            "device_serial": pa.array(
                [],
                type=pa.int32(),
            ),
            "value": pa.array(
                [],
                type=pa.int32(),
            ),
        }
    )

    aligned = align_gold_table(
        table,
        ENTITY_SCHEMA,
    )

    assert aligned.num_rows == 0

    assert aligned.schema == ENTITY_SCHEMA


def test_full_entity_write_creates_table(
    tmp_path: Path,
) -> None:
    table_path = tmp_path / "dim_device"

    table = to_arrow(
        pd.DataFrame(
            {
                "device_serial": [
                    "1001",
                    "2002",
                ],
                "value": [
                    10.0,
                    20.0,
                ],
            }
        )
    )

    rows_written = write_gold_entity_table(
        table_path,
        table,
        schema=ENTITY_SCHEMA,
        key_column="device_serial",
        full_rebuild=True,
    )

    assert rows_written == 2

    result = DeltaTable(str(table_path)).to_pandas()

    assert set(result["device_serial"]) == {
        "1001",
        "2002",
    }


def test_incremental_entity_merge_updates_and_inserts(
    tmp_path: Path,
) -> None:
    table_path = tmp_path / "dim_device"

    initial = to_arrow(
        pd.DataFrame(
            {
                "device_serial": [
                    "1001",
                    "2002",
                ],
                "value": [
                    10.0,
                    20.0,
                ],
            }
        )
    )

    write_gold_entity_table(
        table_path,
        initial,
        schema=ENTITY_SCHEMA,
        key_column="device_serial",
        full_rebuild=True,
    )

    incremental = to_arrow(
        pd.DataFrame(
            {
                "device_serial": [
                    "1001",
                    "3003",
                ],
                "value": [
                    99.0,
                    30.0,
                ],
            }
        )
    )

    rows_written = write_gold_entity_table(
        table_path,
        incremental,
        schema=ENTITY_SCHEMA,
        key_column="device_serial",
        full_rebuild=False,
    )

    assert rows_written == 2

    result = DeltaTable(str(table_path)).to_pandas()

    values = {row["device_serial"]: row["value"] for _, row in result.iterrows()}

    assert values == {
        "1001": 99.0,
        "2002": 20.0,
        "3003": 30.0,
    }


def test_entity_merge_rejects_duplicate_keys(
    tmp_path: Path,
) -> None:
    table_path = tmp_path / "dim_device"

    table = to_arrow(
        pd.DataFrame(
            {
                "device_serial": [
                    "1001",
                    "1001",
                ],
                "value": [
                    10.0,
                    20.0,
                ],
            }
        )
    )

    with pytest.raises(
        ValueError,
        match="chaves duplicadas",
    ):
        write_gold_entity_table(
            table_path,
            table,
            schema=ENTITY_SCHEMA,
            key_column="device_serial",
            full_rebuild=True,
        )


def test_full_partitioned_write_creates_partitions(
    tmp_path: Path,
) -> None:
    table_path = tmp_path / "device_daily_summary"

    table = to_arrow(
        pd.DataFrame(
            {
                "event_date": [
                    "2026-08-17",
                    "2026-08-18",
                ],
                "device_serial": [
                    "1001",
                    "1001",
                ],
                "value": [
                    10.0,
                    20.0,
                ],
            }
        )
    )

    rows_written = write_gold_partitioned_table(
        table_path,
        table,
        schema=PARTITIONED_SCHEMA,
        partition_by="event_date",
        full_rebuild=True,
    )

    assert rows_written == 2

    delta_table = DeltaTable(str(table_path))

    assert delta_table.metadata().partition_columns == ["event_date"]


def test_incremental_partition_write_replaces_only_affected_date(
    tmp_path: Path,
) -> None:
    table_path = tmp_path / "device_daily_summary"

    initial = to_arrow(
        pd.DataFrame(
            {
                "event_date": [
                    "2026-08-17",
                    "2026-08-18",
                ],
                "device_serial": [
                    "1001",
                    "1001",
                ],
                "value": [
                    10.0,
                    20.0,
                ],
            }
        )
    )

    write_gold_partitioned_table(
        table_path,
        initial,
        schema=PARTITIONED_SCHEMA,
        partition_by="event_date",
        full_rebuild=True,
    )

    rebuilt = to_arrow(
        pd.DataFrame(
            {
                "event_date": [
                    "2026-08-17",
                ],
                "device_serial": [
                    "1001",
                ],
                "value": [
                    99.0,
                ],
            }
        )
    )

    write_gold_partitioned_table(
        table_path,
        rebuilt,
        schema=PARTITIONED_SCHEMA,
        partition_by="event_date",
        full_rebuild=False,
        affected_partitions=("2026-08-17",),
    )

    result = DeltaTable(str(table_path)).to_pandas()

    day_17 = result.loc[result["event_date"] == "2026-08-17"]

    day_18 = result.loc[result["event_date"] == "2026-08-18"]

    assert len(day_17) == 1

    assert day_17.iloc[0]["value"] == 99.0

    assert day_18.iloc[0]["value"] == 20.0


def test_incremental_empty_partition_removes_old_rows(
    tmp_path: Path,
) -> None:
    table_path = tmp_path / "device_daily_summary"

    initial = to_arrow(
        pd.DataFrame(
            {
                "event_date": [
                    "2026-08-17",
                    "2026-08-18",
                ],
                "device_serial": [
                    "1001",
                    "1001",
                ],
                "value": [
                    10.0,
                    20.0,
                ],
            }
        )
    )

    write_gold_partitioned_table(
        table_path,
        initial,
        schema=PARTITIONED_SCHEMA,
        partition_by="event_date",
        full_rebuild=True,
    )

    empty = pa.Table.from_batches(
        [],
        schema=PARTITIONED_SCHEMA,
    )

    write_gold_partitioned_table(
        table_path,
        empty,
        schema=PARTITIONED_SCHEMA,
        partition_by="event_date",
        full_rebuild=False,
        affected_partitions=("2026-08-17",),
    )

    result = DeltaTable(str(table_path)).to_pandas()

    assert set(result["event_date"]) == {
        "2026-08-18",
    }


def test_incremental_write_requires_existing_table(
    tmp_path: Path,
) -> None:
    table_path = tmp_path / "device_daily_summary"

    table = to_arrow(
        pd.DataFrame(
            {
                "event_date": [
                    "2026-08-17",
                ],
                "device_serial": [
                    "1001",
                ],
                "value": [
                    10.0,
                ],
            }
        )
    )

    with pytest.raises(
        RuntimeError,
        match="Delta Table existente",
    ):
        write_gold_partitioned_table(
            table_path,
            table,
            schema=PARTITIONED_SCHEMA,
            partition_by="event_date",
            full_rebuild=False,
            affected_partitions=("2026-08-17",),
        )
