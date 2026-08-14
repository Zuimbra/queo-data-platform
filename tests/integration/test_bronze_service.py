from pathlib import Path

import pandas as pd
from deltalake import DeltaTable

from queo_data_platform.bronze.control import (
    get_control_table_path,
)
from queo_data_platform.bronze.service import (
    load_bronze,
    load_bronze_data,
)
from queo_data_platform.config.settings import (
    load_settings,
)
from queo_data_platform.contracts.tracker import (
    BRONZE_TABLE_NAME,
    RAW_TRACKER_REQUIRED_COLUMNS,
)


def create_valid_tracker_file(
    file_path: Path,
    *,
    value: str = "value",
) -> None:
    dataframe = pd.DataFrame(
        {column: [value] for column in RAW_TRACKER_REQUIRED_COLUMNS}
    )

    dataframe.to_csv(
        file_path,
        index=False,
    )


def build_directories(
    tmp_path: Path,
) -> tuple[
    Path,
    Path,
    Path,
    Path,
    Path,
]:
    inbox = tmp_path / "raw" / "inbox"
    archive = tmp_path / "raw" / "archive"
    quarantine = tmp_path / "raw" / "quarantine"

    bronze = tmp_path / "lakehouse" / "01_bronze"
    control = tmp_path / "lakehouse" / "00_control"

    inbox.mkdir(
        parents=True,
    )

    return (
        inbox,
        archive,
        quarantine,
        bronze,
        control,
    )


def read_control_history(
    control_dir: Path,
) -> pd.DataFrame:
    dataframe = DeltaTable(
        str(
            get_control_table_path(
                control_dir,
            )
        )
    ).to_pandas()

    return dataframe.sort_values(
        "recorded_at",
    ).reset_index(
        drop=True,
    )


def test_valid_file_is_ingested_and_archived(
    tmp_path: Path,
) -> None:
    (
        inbox,
        archive,
        quarantine,
        bronze,
        control,
    ) = build_directories(tmp_path)

    source_file = inbox / "tracker.csv"

    create_valid_tracker_file(
        source_file,
    )

    result = load_bronze_data(
        inbox_dir=inbox,
        archive_dir=archive,
        quarantine_dir=quarantine,
        bronze_dir=bronze,
        control_dir=control,
    )

    assert result.discovered_file_count == 1

    assert result.successful_files == ("tracker.csv",)

    assert result.failed_files == ()
    assert result.skipped_files == ()

    assert result.inserted_row_count == 1
    assert result.duplicate_row_count == 0

    assert result.has_new_data
    assert len(result.batch_ids) == 1

    assert not source_file.exists()

    assert (archive / "tracker.csv").exists()

    bronze_dataframe = DeltaTable(str(bronze / BRONZE_TABLE_NAME)).to_pandas()

    assert len(bronze_dataframe) == 1

    assert (
        bronze_dataframe.loc[
            0,
            "batch_id",
        ]
        == result.batch_ids[0]
    )

    control_dataframe = read_control_history(
        control,
    )

    assert control_dataframe["status"].tolist() == [
        "PROCESSING",
        "SUCCESS",
    ]


def test_invalid_file_is_quarantined(
    tmp_path: Path,
) -> None:
    (
        inbox,
        archive,
        quarantine,
        bronze,
        control,
    ) = build_directories(tmp_path)

    source_file = inbox / "invalid.csv"

    source_file.write_text(
        "INVALID_COLUMN\nvalue",
    )

    result = load_bronze_data(
        inbox_dir=inbox,
        archive_dir=archive,
        quarantine_dir=quarantine,
        bronze_dir=bronze,
        control_dir=control,
    )

    assert result.failed_files == ("invalid.csv",)

    assert result.successful_files == ()

    assert result.inserted_row_count == 0
    assert not result.has_new_data

    assert not source_file.exists()

    assert (quarantine / "invalid.csv").exists()

    control_dataframe = read_control_history(
        control,
    )

    assert control_dataframe["status"].tolist() == [
        "PROCESSING",
        "FAILED",
    ]


def test_successful_hash_is_skipped_on_next_run(
    tmp_path: Path,
) -> None:
    (
        inbox,
        archive,
        quarantine,
        bronze,
        control,
    ) = build_directories(tmp_path)

    first_file = inbox / "first.csv"

    create_valid_tracker_file(
        first_file,
    )

    first_result = load_bronze_data(
        inbox_dir=inbox,
        archive_dir=archive,
        quarantine_dir=quarantine,
        bronze_dir=bronze,
        control_dir=control,
    )

    assert first_result.has_new_data

    second_file = inbox / "second.csv"

    create_valid_tracker_file(
        second_file,
    )

    second_result = load_bronze_data(
        inbox_dir=inbox,
        archive_dir=archive,
        quarantine_dir=quarantine,
        bronze_dir=bronze,
        control_dir=control,
    )

    assert second_result.successful_files == ()

    assert second_result.skipped_files == ("second.csv",)

    assert second_result.batch_ids == ()

    assert second_result.inserted_row_count == 0
    assert not second_result.has_new_data

    assert (archive / "second.csv").exists()

    bronze_dataframe = DeltaTable(str(bronze / BRONZE_TABLE_NAME)).to_pandas()

    # O mesmo conteúdo não foi duplicado.
    assert len(bronze_dataframe) == 1

    control_dataframe = read_control_history(
        control,
    )

    assert control_dataframe["status"].tolist() == [
        "PROCESSING",
        "SUCCESS",
        "SKIPPED",
    ]


def test_bronze_can_run_from_settings(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(
        "QUEO_DATA_DIR",
        str(tmp_path),
    )

    settings = load_settings()

    settings.inbox_dir.mkdir(
        parents=True,
    )

    source_file = settings.inbox_dir / "tracker.csv"

    create_valid_tracker_file(
        source_file,
    )

    result = load_bronze(
        settings,
    )

    assert result.has_new_data
    assert result.inserted_row_count == 1

    assert (settings.archive_dir / "tracker.csv").exists()

    assert (settings.bronze_dir / BRONZE_TABLE_NAME).exists()

    assert get_control_table_path(
        settings.control_dir,
    ).exists()


def test_multiple_files_are_processed_in_one_run(
    tmp_path: Path,
) -> None:
    (
        inbox,
        archive,
        quarantine,
        bronze,
        control,
    ) = build_directories(tmp_path)

    create_valid_tracker_file(
        inbox / "b.csv",
        value="second",
    )

    create_valid_tracker_file(
        inbox / "a.csv",
        value="first",
    )

    result = load_bronze_data(
        inbox_dir=inbox,
        archive_dir=archive,
        quarantine_dir=quarantine,
        bronze_dir=bronze,
        control_dir=control,
    )

    assert result.discovered_file_count == 2

    # Discovery é determinístico por nome.
    assert result.successful_files == (
        "a.csv",
        "b.csv",
    )

    assert result.skipped_files == ()
    assert result.failed_files == ()

    assert result.inserted_row_count == 2
    assert result.duplicate_row_count == 0

    assert result.has_new_data

    # Cada arquivo processado possui seu próprio batch.
    assert len(result.batch_ids) == 2
    assert len(set(result.batch_ids)) == 2

    assert (archive / "a.csv").exists()

    assert (archive / "b.csv").exists()

    bronze_dataframe = DeltaTable(str(bronze / BRONZE_TABLE_NAME)).to_pandas()

    assert len(bronze_dataframe) == 2

    assert set(bronze_dataframe["batch_id"]) == set(result.batch_ids)


def test_empty_inbox_returns_no_new_data(
    tmp_path: Path,
) -> None:
    (
        inbox,
        archive,
        quarantine,
        bronze,
        control,
    ) = build_directories(tmp_path)

    result = load_bronze_data(
        inbox_dir=inbox,
        archive_dir=archive,
        quarantine_dir=quarantine,
        bronze_dir=bronze,
        control_dir=control,
    )

    assert result.discovered_file_count == 0

    assert result.successful_files == ()
    assert result.skipped_files == ()
    assert result.failed_files == ()

    assert result.batch_ids == ()

    assert result.inserted_row_count == 0
    assert result.duplicate_row_count == 0

    assert not result.has_new_data
