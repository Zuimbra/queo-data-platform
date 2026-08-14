from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

import pandas as pd
import pytest

from queo_data_platform.bronze.lineage import (
    add_lineage_metadata,
    calculate_row_id,
    generate_batch_id,
    normalize_ingestion_timestamp,
)


def test_generate_batch_id_returns_valid_uuid() -> None:
    batch_id = generate_batch_id()

    parsed_uuid = UUID(batch_id)

    assert str(parsed_uuid) == batch_id


def test_generate_batch_id_generates_different_values() -> None:
    first_batch = generate_batch_id()
    second_batch = generate_batch_id()

    assert first_batch != second_batch


def test_calculate_row_id_is_deterministic() -> None:
    first_row_id = calculate_row_id(
        source_file_hash="file-hash",
        source_row_number=1,
    )

    second_row_id = calculate_row_id(
        source_file_hash="file-hash",
        source_row_number=1,
    )

    assert first_row_id == second_row_id


def test_calculate_row_id_changes_for_different_rows() -> None:
    first_row_id = calculate_row_id(
        source_file_hash="file-hash",
        source_row_number=1,
    )

    second_row_id = calculate_row_id(
        source_file_hash="file-hash",
        source_row_number=2,
    )

    assert first_row_id != second_row_id


def test_calculate_row_id_rejects_invalid_row_number() -> None:
    with pytest.raises(
        ValueError,
        match="source_row_number precisa começar em 1",
    ):
        calculate_row_id(
            source_file_hash="file-hash",
            source_row_number=0,
        )


def test_normalize_naive_timestamp_as_utc() -> None:
    timestamp = datetime(  # noqa: DTZ001
        2026,
        8,
        14,
        15,
        0,
    )

    normalized = normalize_ingestion_timestamp(timestamp)

    assert normalized.tzinfo == UTC
    assert normalized.hour == 15


def test_normalize_timezone_aware_timestamp_to_utc() -> None:
    brazil_timezone = timezone(timedelta(hours=-3))

    timestamp = datetime(
        2026,
        8,
        14,
        15,
        0,
        tzinfo=brazil_timezone,
    )

    normalized = normalize_ingestion_timestamp(timestamp)

    assert normalized.tzinfo == UTC
    assert normalized.hour == 18


def test_add_lineage_metadata(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "tracker.csv"
    source_path.write_text("test")

    dataframe = pd.DataFrame(
        {
            "LAT": ["-3.7", "-3.8"],
            "LONT": ["-38.5", "-38.6"],
        }
    )

    ingested_at = datetime(
        2026,
        8,
        14,
        18,
        30,
        tzinfo=UTC,
    )

    result = add_lineage_metadata(
        dataframe=dataframe,
        source_path=source_path,
        batch_id="batch-001",
        source_file_hash="hash-001",
        ingested_at=ingested_at,
    )

    assert result["source_file"].tolist() == [
        "tracker.csv",
        "tracker.csv",
    ]

    assert result["source_file_hash"].tolist() == [
        "hash-001",
        "hash-001",
    ]

    assert result["source_row_number"].tolist() == [
        1,
        2,
    ]

    assert result["batch_id"].tolist() == [
        "batch-001",
        "batch-001",
    ]

    assert result["ingestion_date"].tolist() == [
        "2026-08-14",
        "2026-08-14",
    ]

    assert result["LAT"].tolist() == [
        "-3.7",
        "-3.8",
    ]


def test_same_source_line_keeps_row_id_across_batches(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "tracker.csv"
    source_path.write_text("test")

    dataframe = pd.DataFrame(
        {
            "LAT": ["-3.7"],
        }
    )

    first = add_lineage_metadata(
        dataframe=dataframe,
        source_path=source_path,
        batch_id="batch-001",
        source_file_hash="same-hash",
    )

    second = add_lineage_metadata(
        dataframe=dataframe,
        source_path=source_path,
        batch_id="batch-002",
        source_file_hash="same-hash",
    )

    assert first.loc[0, "batch_id"] != second.loc[0, "batch_id"]

    assert first.loc[0, "row_id"] == second.loc[0, "row_id"]
