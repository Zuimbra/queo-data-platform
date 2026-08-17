from pathlib import Path

import pandas as pd
import pyarrow as pa
from deltalake import DeltaTable, write_deltalake

from queo_data_platform.silver.incremental import (
    SilverAffectedPartitions,
    discover_affected_partitions,
    load_incremental_bronze_scope,
    normalize_batch_ids,
)


def create_bronze_table(
    table_path: Path,
    rows: list[dict[str, object]],
) -> DeltaTable:
    dataframe = pd.DataFrame(rows)

    table = pa.Table.from_pandas(
        dataframe,
        preserve_index=False,
    )

    write_deltalake(
        table_path,
        table,
        mode="overwrite",
    )

    return DeltaTable(str(table_path))


def test_normalize_batch_ids() -> None:
    result = normalize_batch_ids(
        [
            " batch-002 ",
            "batch-001",
            "batch-002",
            "",
        ]
    )

    assert result == (
        "batch-001",
        "batch-002",
    )


def test_empty_batch_ids_return_no_partitions(
    tmp_path: Path,
) -> None:
    bronze_table = create_bronze_table(
        tmp_path / "tracker_logs",
        [
            {
                "DATA_SERVIDOR": ("2026-08-17 12:00:00"),
                "TM_STAMP": ("2026-08-17 11:59:00"),
                "batch_id": "batch-001",
                "row_id": "row-001",
            }
        ],
    )

    result = discover_affected_partitions(
        bronze_table,
        (),
    )

    assert result.is_empty
    assert result.event_dates == ()
    assert result.rejection_dates == ()


def test_batch_discovers_affected_event_date(
    tmp_path: Path,
) -> None:
    bronze_table = create_bronze_table(
        tmp_path / "tracker_logs",
        [
            {
                "DATA_SERVIDOR": ("2026-08-17 12:00:00"),
                "TM_STAMP": ("2026-08-17 11:59:00"),
                "batch_id": "batch-new",
                "row_id": "row-001",
            }
        ],
    )

    result = discover_affected_partitions(
        bronze_table,
        ("batch-new",),
    )

    assert result.event_dates == ("2026-08-17",)

    assert result.rejection_dates == ("2026-08-17",)


def test_invalid_timestamp_affects_unknown_partition(
    tmp_path: Path,
) -> None:
    bronze_table = create_bronze_table(
        tmp_path / "tracker_logs",
        [
            {
                "DATA_SERVIDOR": "invalid",
                "TM_STAMP": "invalid",
                "batch_id": "batch-new",
                "row_id": "row-001",
            }
        ],
    )

    result = discover_affected_partitions(
        bronze_table,
        ("batch-new",),
    )

    assert result.event_dates == ()

    assert result.rejection_dates == ("unknown",)

    assert result.include_unknown


def test_late_arriving_batch_rebuilds_entire_date(
    tmp_path: Path,
) -> None:
    bronze_table = create_bronze_table(
        tmp_path / "tracker_logs",
        [
            {
                "DATA_SERVIDOR": ("2026-08-17 10:00:00"),
                "TM_STAMP": ("2026-08-17 09:59:00"),
                "batch_id": "batch-old",
                "row_id": "row-old",
            },
            {
                "DATA_SERVIDOR": ("2026-08-17 12:00:00"),
                "TM_STAMP": ("2026-08-17 11:59:00"),
                "batch_id": "batch-new",
                "row_id": "row-late",
            },
            {
                "DATA_SERVIDOR": ("2026-08-18 12:00:00"),
                "TM_STAMP": ("2026-08-18 11:59:00"),
                "batch_id": "batch-other",
                "row_id": "row-other",
            },
        ],
    )

    affected = discover_affected_partitions(
        bronze_table,
        ("batch-new",),
    )

    scope = load_incremental_bronze_scope(
        bronze_table,
        affected,
    )

    assert set(scope["row_id"]) == {
        "row-old",
        "row-late",
    }

    assert "row-other" not in set(scope["row_id"])


def test_unknown_rebuild_includes_all_unknown_rows(
    tmp_path: Path,
) -> None:
    bronze_table = create_bronze_table(
        tmp_path / "tracker_logs",
        [
            {
                "DATA_SERVIDOR": "invalid",
                "TM_STAMP": "invalid",
                "batch_id": "batch-old",
                "row_id": "row-old-unknown",
            },
            {
                "DATA_SERVIDOR": None,
                "TM_STAMP": None,
                "batch_id": "batch-new",
                "row_id": "row-new-unknown",
            },
            {
                "DATA_SERVIDOR": ("2026-08-18 12:00:00"),
                "TM_STAMP": ("2026-08-18 11:59:00"),
                "batch_id": "batch-valid",
                "row_id": "row-valid",
            },
        ],
    )

    affected = discover_affected_partitions(
        bronze_table,
        ("batch-new",),
    )

    assert affected == SilverAffectedPartitions(
        event_dates=(),
        rejection_dates=("unknown",),
    )

    scope = load_incremental_bronze_scope(
        bronze_table,
        affected,
    )

    assert set(scope["row_id"]) == {
        "row-old-unknown",
        "row-new-unknown",
    }
