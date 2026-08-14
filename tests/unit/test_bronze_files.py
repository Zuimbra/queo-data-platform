from pathlib import Path

from queo_data_platform.bronze.files import (
    calculate_file_sha256,
    discover_csv_files,
    move_file,
)


def test_discover_csv_files_returns_only_csv_files(
    tmp_path: Path,
) -> None:
    (tmp_path / "b.csv").write_text("data")
    (tmp_path / "a.csv").write_text("data")
    (tmp_path / "ignore.txt").write_text("data")

    files = discover_csv_files(tmp_path)

    assert [file.name for file in files] == [
        "a.csv",
        "b.csv",
    ]


def test_discover_csv_files_accepts_uppercase_extension(
    tmp_path: Path,
) -> None:
    (tmp_path / "tracker.CSV").write_text("data")

    files = discover_csv_files(tmp_path)

    assert [file.name for file in files] == [
        "tracker.CSV",
    ]


def test_discover_csv_files_does_not_scan_subdirectories(
    tmp_path: Path,
) -> None:
    subdirectory = tmp_path / "subdirectory"
    subdirectory.mkdir()

    (subdirectory / "hidden.csv").write_text("data")

    files = discover_csv_files(tmp_path)

    assert files == []


def test_discover_csv_files_returns_empty_list_for_missing_directory(
    tmp_path: Path,
) -> None:
    missing_directory = tmp_path / "missing"

    files = discover_csv_files(missing_directory)

    assert files == []


def test_file_hash_is_deterministic(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "tracker.csv"
    file_path.write_text("same content")

    first_hash = calculate_file_sha256(file_path)
    second_hash = calculate_file_sha256(file_path)

    assert first_hash == second_hash


def test_different_file_contents_generate_different_hashes(
    tmp_path: Path,
) -> None:
    first_file = tmp_path / "first.csv"
    second_file = tmp_path / "second.csv"

    first_file.write_text("content A")
    second_file.write_text("content B")

    assert calculate_file_sha256(first_file) != calculate_file_sha256(second_file)


def test_move_file_moves_source_to_destination(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "source"
    destination_dir = tmp_path / "archive"

    source_dir.mkdir()

    source_path = source_dir / "tracker.csv"

    source_path.write_text("data")

    destination_path = move_file(
        source_path,
        destination_dir,
    )

    assert not source_path.exists()
    assert destination_path.exists()
    assert destination_path.name == "tracker.csv"


def test_move_file_uses_suffix_on_name_collision(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "source"
    destination_dir = tmp_path / "archive"

    source_dir.mkdir()
    destination_dir.mkdir()

    source_path = source_dir / "tracker.csv"

    source_path.write_text("new")

    (destination_dir / "tracker.csv").write_text("old")

    destination_path = move_file(
        source_path,
        destination_dir,
        conflict_suffix="batch-001",
    )

    assert destination_path.name == "tracker__batch-001.csv"

    assert destination_path.read_text() == "new"
