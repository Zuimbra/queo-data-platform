from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
import pytest
from deltalake import DeltaTable

from queo_data_platform.bronze.control import (
    append_control_event,
    control_event_to_arrow_table,
    create_control_event,
    load_successful_file_hashes,
    should_skip_file_hash,
)

STARTED_AT = datetime(
    2026,
    8,
    14,
    18,
    0,
    tzinfo=UTC,
)


def test_processing_event_has_no_finished_at() -> None:
    event = create_control_event(
        batch_id="batch-001",
        source_file="tracker.csv",
        source_file_hash="hash-001",
        status="processing",
        started_at=STARTED_AT,
    )

    assert event.status == "PROCESSING"
    assert event.stage == "BRONZE"
    assert event.finished_at is None


def test_final_status_receives_finished_at() -> None:
    event = create_control_event(
        batch_id="batch-001",
        source_file="tracker.csv",
        source_file_hash="hash-001",
        status="SUCCESS",
        started_at=STARTED_AT,
    )

    assert event.finished_at is not None
    assert event.finished_at.tzinfo == UTC


def test_invalid_status_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="Status de controle inválido",
    ):
        create_control_event(
            batch_id="batch-001",
            source_file="tracker.csv",
            source_file_hash="hash-001",
            status="UNKNOWN",
            started_at=STARTED_AT,
        )


def test_negative_row_count_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="row_count não pode ser negativo",
    ):
        create_control_event(
            batch_id="batch-001",
            source_file="tracker.csv",
            source_file_hash="hash-001",
            status="SUCCESS",
            started_at=STARTED_AT,
            row_count=-1,
        )


def test_control_arrow_schema_preserves_nullable_types() -> None:
    event = create_control_event(
        batch_id="batch-001",
        source_file="tracker.csv",
        source_file_hash=None,
        status="PROCESSING",
        started_at=STARTED_AT,
    )

    table = control_event_to_arrow_table(event)

    assert table.schema.field("source_file_hash").type == pa.string()

    assert table.schema.field("row_count").type == pa.int64()

    assert table.schema.field("finished_at").type == pa.timestamp(
        "us",
        tz="UTC",
    )


def test_control_table_is_append_only(
    tmp_path: Path,
) -> None:
    control_path = tmp_path / "ingestion_files"

    processing = create_control_event(
        batch_id="batch-001",
        source_file="tracker.csv",
        source_file_hash="hash-001",
        status="PROCESSING",
        started_at=STARTED_AT,
    )

    success = create_control_event(
        batch_id="batch-001",
        source_file="tracker.csv",
        source_file_hash="hash-001",
        status="SUCCESS",
        started_at=STARTED_AT,
        row_count=10,
        inserted_row_count=10,
        duplicate_row_count=0,
    )

    append_control_event(
        control_path,
        processing,
    )

    append_control_event(
        control_path,
        success,
    )

    dataframe = DeltaTable(str(control_path)).to_pandas()

    assert len(dataframe) == 2

    assert set(dataframe["status"]) == {
        "PROCESSING",
        "SUCCESS",
    }


def test_load_successful_file_hashes(
    tmp_path: Path,
) -> None:
    control_path = tmp_path / "ingestion_files"

    failed = create_control_event(
        batch_id="batch-001",
        source_file="failed.csv",
        source_file_hash="hash-failed",
        status="FAILED",
        started_at=STARTED_AT,
    )

    success = create_control_event(
        batch_id="batch-002",
        source_file="success.csv",
        source_file_hash="hash-success",
        status="SUCCESS",
        started_at=STARTED_AT,
    )

    append_control_event(
        control_path,
        failed,
    )

    append_control_event(
        control_path,
        success,
    )

    hashes = load_successful_file_hashes(control_path)

    assert hashes == {
        "hash-success",
    }


def test_should_skip_successful_hash() -> None:
    successful_hashes = {
        "hash-001",
        "hash-002",
    }

    assert should_skip_file_hash(
        "hash-001",
        successful_hashes,
    )


def test_should_not_skip_unknown_hash() -> None:
    successful_hashes = {
        "hash-001",
    }

    assert not should_skip_file_hash(
        "hash-999",
        successful_hashes,
    )
