from pathlib import Path

import pandas as pd
import pytest
from deltalake import DeltaTable

from queo_data_platform.bronze.writer import (
    align_dataframe_to_target_schema,
    write_bronze_table,
)


def build_bronze_dataframe(
    row_ids: list[str],
    batch_id: str = "batch-001",
) -> pd.DataFrame:
    """
    Cria um pequeno DataFrame Bronze para os testes de persistência.
    """

    return pd.DataFrame(
        {
            "payload": [f"value-{row_id}" for row_id in row_ids],
            "row_id": row_ids,
            "batch_id": [batch_id for _ in row_ids],
            "ingestion_date": ["2026-08-14" for _ in row_ids],
        }
    )


def test_align_dataframe_adds_missing_target_columns() -> None:
    dataframe = pd.DataFrame(
        {
            "row_id": ["row-1"],
            "new_column": ["new"],
        }
    )

    aligned = align_dataframe_to_target_schema(
        dataframe=dataframe,
        target_columns=[
            "row_id",
            "old_column",
        ],
    )

    assert list(aligned.columns) == [
        "row_id",
        "old_column",
        "new_column",
    ]

    assert pd.isna(
        aligned.loc[
            0,
            "old_column",
        ]
    )


def test_empty_dataframe_is_rejected(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ValueError,
        match="DataFrame vazio",
    ):
        write_bronze_table(
            dataframe=pd.DataFrame(),
            table_path=tmp_path / "tracker_logs",
        )


def test_first_write_creates_delta_table(
    tmp_path: Path,
) -> None:
    table_path = tmp_path / "tracker_logs"

    dataframe = build_bronze_dataframe(
        [
            "row-1",
            "row-2",
        ]
    )

    result = write_bronze_table(
        dataframe=dataframe,
        table_path=table_path,
    )

    assert result.operation == "CREATE"
    assert result.row_count == 2
    assert result.inserted_row_count == 2
    assert result.duplicate_row_count == 0

    delta_table = DeltaTable(str(table_path))

    persisted = delta_table.to_pandas()

    assert len(persisted) == 2

    assert set(persisted["row_id"]) == {
        "row-1",
        "row-2",
    }


def test_reprocessing_same_rows_does_not_duplicate(
    tmp_path: Path,
) -> None:
    table_path = tmp_path / "tracker_logs"

    first_dataframe = build_bronze_dataframe(
        [
            "row-1",
            "row-2",
        ],
        batch_id="batch-001",
    )

    second_dataframe = build_bronze_dataframe(
        [
            "row-1",
            "row-2",
        ],
        batch_id="batch-002",
    )

    write_bronze_table(
        dataframe=first_dataframe,
        table_path=table_path,
    )

    result = write_bronze_table(
        dataframe=second_dataframe,
        table_path=table_path,
    )

    assert result.operation == "MERGE"
    assert result.inserted_row_count == 0
    assert result.duplicate_row_count == 2

    persisted = DeltaTable(str(table_path)).to_pandas()

    assert len(persisted) == 2


def test_merge_inserts_only_new_rows(
    tmp_path: Path,
) -> None:
    table_path = tmp_path / "tracker_logs"

    write_bronze_table(
        dataframe=build_bronze_dataframe(["row-1"]),
        table_path=table_path,
    )

    result = write_bronze_table(
        dataframe=build_bronze_dataframe(
            [
                "row-1",
                "row-2",
            ]
        ),
        table_path=table_path,
    )

    assert result.inserted_row_count == 1
    assert result.duplicate_row_count == 1

    persisted = DeltaTable(str(table_path)).to_pandas()

    assert set(persisted["row_id"]) == {
        "row-1",
        "row-2",
    }


def test_merge_allows_schema_evolution(
    tmp_path: Path,
) -> None:
    table_path = tmp_path / "tracker_logs"

    first_dataframe = build_bronze_dataframe(["row-1"])

    write_bronze_table(
        dataframe=first_dataframe,
        table_path=table_path,
    )

    second_dataframe = build_bronze_dataframe(["row-2"])

    second_dataframe["new_source_column"] = "extra-value"

    result = write_bronze_table(
        dataframe=second_dataframe,
        table_path=table_path,
    )

    assert result.inserted_row_count == 1

    persisted = DeltaTable(str(table_path)).to_pandas()

    assert "new_source_column" in persisted.columns

    row_two = persisted.loc[persisted["row_id"] == "row-2"].iloc[0]

    assert row_two["new_source_column"] == "extra-value"
