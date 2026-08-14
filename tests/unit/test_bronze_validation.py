from pathlib import Path

import pandas as pd

from queo_data_platform.bronze.validation import (
    find_duplicated_columns,
    normalize_column_names,
    validate_input_file,
)
from queo_data_platform.contracts.tracker import (
    RAW_TRACKER_COLUMNS,
)


def build_valid_csv(
    file_path: Path,
    extra_columns: dict[str, str] | None = None,
) -> None:
    data = {column: ["value"] for column in RAW_TRACKER_COLUMNS}

    if extra_columns:
        data.update({column: [value] for column, value in extra_columns.items()})

    pd.DataFrame(data).to_csv(
        file_path,
        index=False,
    )


def test_normalize_column_names_removes_external_spaces() -> None:
    dataframe = pd.DataFrame(columns=[" LAT ", " LON", "NR_SEQ "])

    normalized = normalize_column_names(dataframe)

    assert list(normalized.columns) == [
        "LAT",
        "LON",
        "NR_SEQ",
    ]


def test_find_duplicated_columns_detects_collision_after_normalization() -> None:
    dataframe = pd.DataFrame(
        [["a", "b"]],
        columns=["LAT", " LAT "],
    )

    normalized = normalize_column_names(dataframe)

    assert find_duplicated_columns(normalized) == ("LAT",)


def test_empty_file_is_rejected(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "empty.csv"
    file_path.touch()

    result = validate_input_file(file_path)

    assert result.is_valid is False
    assert result.error_message == "O arquivo está vazio."


def test_missing_required_column_is_rejected(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "missing.csv"

    columns = [column for column in RAW_TRACKER_COLUMNS if column != "LAT"]

    pd.DataFrame({column: ["value"] for column in columns}).to_csv(
        file_path, index=False
    )

    result = validate_input_file(file_path)

    assert result.is_valid is False
    assert result.missing_columns == ("LAT",)


def test_extra_columns_are_allowed(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "extra.csv"

    build_valid_csv(
        file_path,
        extra_columns={
            "EXTRA_COLUMN": "extra",
        },
    )

    result = validate_input_file(file_path)

    assert result.is_valid is True
    assert result.row_count == 1


def test_reserved_metadata_column_is_rejected(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "reserved.csv"

    build_valid_csv(
        file_path,
        extra_columns={
            "batch_id": "fake-batch",
        },
    )

    result = validate_input_file(file_path)

    assert result.is_valid is False
    assert result.reserved_columns == ("batch_id",)


def test_valid_file_is_accepted(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "valid.csv"

    build_valid_csv(file_path)

    result = validate_input_file(file_path)

    assert result.is_valid is True
    assert result.row_count == 1
    assert result.dataframe is not None
    assert result.detected_encoding == "utf-8-sig"
