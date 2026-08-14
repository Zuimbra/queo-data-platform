from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from queo_data_platform.bronze.control import (
    get_control_table_path,
    load_successful_file_hashes,
    record_ingestion_status,
    should_skip_file_hash,
)
from queo_data_platform.bronze.files import (
    calculate_file_sha256,
    discover_csv_files,
    move_file,
)
from queo_data_platform.bronze.lineage import (
    add_lineage_metadata,
    generate_batch_id,
)
from queo_data_platform.bronze.validation import (
    validate_input_file,
)
from queo_data_platform.bronze.writer import (
    write_bronze_table,
)
from queo_data_platform.config.settings import Settings
from queo_data_platform.contracts.tracker import (
    BRONZE_TABLE_NAME,
)


@dataclass(frozen=True)
class BronzeLoadResult:
    """
    Resume o resultado de uma execução da Bronze.

    batch_ids contém somente batches que efetivamente
    inseriram novas linhas na tabela Bronze.
    """

    discovered_file_count: int

    successful_files: tuple[str, ...]
    skipped_files: tuple[str, ...]
    failed_files: tuple[str, ...]

    batch_ids: tuple[str, ...]

    inserted_row_count: int
    duplicate_row_count: int

    @property
    def has_new_data(self) -> bool:
        """
        Indica se a execução produziu novas linhas na Bronze.
        """

        return self.inserted_row_count > 0


def load_bronze_data(
    *,
    inbox_dir: Path,
    archive_dir: Path,
    quarantine_dir: Path,
    bronze_dir: Path,
    control_dir: Path,
) -> BronzeLoadResult:
    """
    Executa o fluxo completo de ingestão Bronze.

    Fluxo:
        inbox
          ↓
        discovery
          ↓
        SHA-256
          ↓
        controle de duplicidade
          ↓
        validação
          ↓
        lineage
          ↓
        Delta MERGE
          ↓
        archive / quarantine
    """

    input_files = discover_csv_files(inbox_dir)

    control_path = get_control_table_path(control_dir)
    bronze_table_path = bronze_dir / BRONZE_TABLE_NAME

    # Carregamos uma única vez o estado persistido.
    #
    # Depois atualizamos este set em memória sempre que
    # um arquivo termina com SUCCESS.
    successful_hashes = load_successful_file_hashes(control_path)

    successful_files: list[str] = []
    skipped_files: list[str] = []
    failed_files: list[str] = []

    inserted_batch_ids: list[str] = []

    inserted_row_count = 0
    duplicate_row_count = 0

    for source_path in input_files:
        batch_id = generate_batch_id()
        started_at = datetime.now(UTC)

        source_file_hash: str | None = None

        # --------------------------------------------------
        # HASH
        # --------------------------------------------------

        try:
            source_file_hash = calculate_file_sha256(source_path)
        except (OSError, ValueError) as error:
            record_ingestion_status(
                control_path,
                batch_id=batch_id,
                source_file=source_path.name,
                source_file_hash=None,
                status="FAILED",
                started_at=started_at,
                error_message=str(error),
                status_reason="FILE_HASH_ERROR",
            )

            failed_files.append(source_path.name)

            move_file(
                source_path,
                quarantine_dir,
                conflict_suffix=batch_id,
            )

            continue

        # --------------------------------------------------
        # ARQUIVO JÁ PROCESSADO
        # --------------------------------------------------

        if should_skip_file_hash(
            source_file_hash,
            successful_hashes,
        ):
            record_ingestion_status(
                control_path,
                batch_id=batch_id,
                source_file=source_path.name,
                source_file_hash=source_file_hash,
                status="SKIPPED",
                started_at=started_at,
                status_reason="SOURCE_FILE_HASH_ALREADY_SUCCESSFUL",
            )

            skipped_files.append(source_path.name)

            move_file(
                source_path,
                archive_dir,
                conflict_suffix=batch_id,
            )

            continue

        # --------------------------------------------------
        # PROCESSING
        # --------------------------------------------------

        record_ingestion_status(
            control_path,
            batch_id=batch_id,
            source_file=source_path.name,
            source_file_hash=source_file_hash,
            status="PROCESSING",
            started_at=started_at,
        )

        # --------------------------------------------------
        # VALIDAÇÃO
        # --------------------------------------------------

        validation_result = validate_input_file(source_path)

        if not validation_result.is_valid or validation_result.dataframe is None:
            error_message = (
                validation_result.error_message or "Falha de validação sem mensagem."
            )

            record_ingestion_status(
                control_path,
                batch_id=batch_id,
                source_file=source_path.name,
                source_file_hash=source_file_hash,
                status="FAILED",
                started_at=started_at,
                row_count=validation_result.row_count,
                status_reason="VALIDATION_FAILED",
                error_message=error_message,
            )

            failed_files.append(source_path.name)

            move_file(
                source_path,
                quarantine_dir,
                conflict_suffix=batch_id,
            )

            continue

        # --------------------------------------------------
        # LINEAGE + DELTA
        # --------------------------------------------------

        try:
            bronze_dataframe = add_lineage_metadata(
                dataframe=validation_result.dataframe,
                source_path=source_path,
                batch_id=batch_id,
                source_file_hash=source_file_hash,
                ingested_at=started_at,
            )

            write_result = write_bronze_table(
                dataframe=bronze_dataframe,
                table_path=bronze_table_path,
            )

        except (
            OSError,
            ValueError,
            RuntimeError,
        ) as error:
            record_ingestion_status(
                control_path,
                batch_id=batch_id,
                source_file=source_path.name,
                source_file_hash=source_file_hash,
                status="FAILED",
                started_at=started_at,
                row_count=validation_result.row_count,
                status_reason="BRONZE_WRITE_FAILED",
                error_message=str(error),
            )

            failed_files.append(source_path.name)

            move_file(
                source_path,
                quarantine_dir,
                conflict_suffix=batch_id,
            )

            continue

        # --------------------------------------------------
        # SUCCESS
        # --------------------------------------------------

        record_ingestion_status(
            control_path,
            batch_id=batch_id,
            source_file=source_path.name,
            source_file_hash=source_file_hash,
            status="SUCCESS",
            started_at=started_at,
            row_count=write_result.row_count,
            inserted_row_count=write_result.inserted_row_count,
            duplicate_row_count=write_result.duplicate_row_count,
        )

        successful_hashes.add(source_file_hash)
        successful_files.append(source_path.name)

        inserted_row_count += write_result.inserted_row_count
        duplicate_row_count += write_result.duplicate_row_count

        # Só propagamos para a Silver batches que realmente
        # possuem linhas novas na Bronze.
        if write_result.inserted_row_count > 0:
            inserted_batch_ids.append(batch_id)

        move_file(
            source_path,
            archive_dir,
            conflict_suffix=batch_id,
        )

    return BronzeLoadResult(
        discovered_file_count=len(input_files),
        successful_files=tuple(successful_files),
        skipped_files=tuple(skipped_files),
        failed_files=tuple(failed_files),
        batch_ids=tuple(inserted_batch_ids),
        inserted_row_count=inserted_row_count,
        duplicate_row_count=duplicate_row_count,
    )


def load_bronze(
    settings: Settings,
) -> BronzeLoadResult:
    """
    Executa a ingestão Bronze utilizando a configuração
    da plataforma.

    Esta é a interface de alto nível que será utilizada
    pela futura orquestração do pipeline.
    """

    return load_bronze_data(
        inbox_dir=settings.inbox_dir,
        archive_dir=settings.archive_dir,
        quarantine_dir=settings.quarantine_dir,
        bronze_dir=settings.bronze_dir,
        control_dir=settings.control_dir,
    )
