from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal, cast
from uuid import uuid4

import pyarrow as pa
from deltalake import DeltaTable, write_deltalake

from queo_data_platform.bronze.lineage import (
    normalize_ingestion_timestamp,
)
from queo_data_platform.infrastructure.delta.table import (
    is_delta_table,
)

CONTROL_TABLE_NAME = "ingestion_files"
CONTROL_STAGE = "BRONZE"

ControlStatus = Literal[
    "PROCESSING",
    "SUCCESS",
    "FAILED",
    "SKIPPED",
]

CONTROL_STATUSES: tuple[ControlStatus, ...] = (
    "PROCESSING",
    "SUCCESS",
    "FAILED",
    "SKIPPED",
)


@dataclass(frozen=True)
class IngestionControlEvent:
    """
    Representa um evento imutável do histórico de ingestão.

    A tabela de controle é append-only:
    uma mudança de estado gera uma nova linha.
    """

    control_event_id: str
    batch_id: str
    source_file: str
    source_file_hash: str | None
    status: ControlStatus
    stage: str
    started_at: datetime
    finished_at: datetime | None
    row_count: int | None
    inserted_row_count: int | None
    duplicate_row_count: int | None
    status_reason: str | None
    error_message: str | None
    recorded_at: datetime


def get_control_table_path(
    control_dir: Path,
) -> Path:
    """
    Retorna o caminho da tabela de controle de ingestão.
    """

    return control_dir / CONTROL_TABLE_NAME


def create_control_event(
    *,
    batch_id: str,
    source_file: str,
    source_file_hash: str | None,
    status: str,
    started_at: datetime,
    finished_at: datetime | None = None,
    row_count: int | None = None,
    inserted_row_count: int | None = None,
    duplicate_row_count: int | None = None,
    status_reason: str | None = None,
    error_message: str | None = None,
    recorded_at: datetime | None = None,
) -> IngestionControlEvent:
    """
    Cria e valida um evento de controle.
    """

    normalized_status = status.strip().upper()

    if normalized_status not in CONTROL_STATUSES:
        raise ValueError(
            f"Status de controle inválido: {status}. Esperado: {CONTROL_STATUSES}."
        )

    if not batch_id.strip():
        raise ValueError("batch_id não pode ser vazio.")

    if not source_file.strip():
        raise ValueError("source_file não pode ser vazio.")

    for field_name, value in (
        ("row_count", row_count),
        ("inserted_row_count", inserted_row_count),
        ("duplicate_row_count", duplicate_row_count),
    ):
        if value is not None and value < 0:
            raise ValueError(f"{field_name} não pode ser negativo.")

    normalized_started_at = normalize_ingestion_timestamp(started_at)

    normalized_recorded_at = normalize_ingestion_timestamp(recorded_at)

    normalized_finished_at = (
        normalize_ingestion_timestamp(finished_at) if finished_at is not None else None
    )

    if (
        normalized_finished_at is not None
        and normalized_finished_at < normalized_started_at
    ):
        raise ValueError("finished_at não pode ser anterior a started_at.")

    # PROCESSING representa uma tentativa ainda aberta.
    #
    # Estados finais recebem automaticamente recorded_at
    # como finished_at quando o chamador não informar um.
    if normalized_status != "PROCESSING" and normalized_finished_at is None:
        normalized_finished_at = normalized_recorded_at

    return IngestionControlEvent(
        control_event_id=str(uuid4()),
        batch_id=batch_id,
        source_file=source_file,
        source_file_hash=source_file_hash,
        status=cast(
            ControlStatus,
            normalized_status,
        ),
        stage=CONTROL_STAGE,
        started_at=normalized_started_at,
        finished_at=normalized_finished_at,
        row_count=row_count,
        inserted_row_count=inserted_row_count,
        duplicate_row_count=duplicate_row_count,
        status_reason=status_reason,
        error_message=error_message,
        recorded_at=normalized_recorded_at,
    )


def control_event_to_arrow_table(
    event: IngestionControlEvent,
) -> pa.Table:
    """
    Converte um evento para Arrow usando schema explícito.

    O schema explícito impede que campos inicialmente NULL
    sejam persistidos como NullType.
    """

    schema = pa.schema(
        [
            pa.field(
                "control_event_id",
                pa.string(),
                nullable=False,
            ),
            pa.field(
                "batch_id",
                pa.string(),
                nullable=False,
            ),
            pa.field(
                "source_file",
                pa.string(),
                nullable=False,
            ),
            pa.field(
                "source_file_hash",
                pa.string(),
                nullable=True,
            ),
            pa.field(
                "status",
                pa.string(),
                nullable=False,
            ),
            pa.field(
                "stage",
                pa.string(),
                nullable=False,
            ),
            pa.field(
                "started_at",
                pa.timestamp(
                    "us",
                    tz="UTC",
                ),
                nullable=False,
            ),
            pa.field(
                "finished_at",
                pa.timestamp(
                    "us",
                    tz="UTC",
                ),
                nullable=True,
            ),
            pa.field(
                "row_count",
                pa.int64(),
                nullable=True,
            ),
            pa.field(
                "inserted_row_count",
                pa.int64(),
                nullable=True,
            ),
            pa.field(
                "duplicate_row_count",
                pa.int64(),
                nullable=True,
            ),
            pa.field(
                "status_reason",
                pa.string(),
                nullable=True,
            ),
            pa.field(
                "error_message",
                pa.string(),
                nullable=True,
            ),
            pa.field(
                "recorded_at",
                pa.timestamp(
                    "us",
                    tz="UTC",
                ),
                nullable=False,
            ),
        ]
    )

    return pa.Table.from_pylist(
        [
            {
                "control_event_id": (event.control_event_id),
                "batch_id": event.batch_id,
                "source_file": event.source_file,
                "source_file_hash": (event.source_file_hash),
                "status": event.status,
                "stage": event.stage,
                "started_at": event.started_at,
                "finished_at": event.finished_at,
                "row_count": event.row_count,
                "inserted_row_count": (event.inserted_row_count),
                "duplicate_row_count": (event.duplicate_row_count),
                "status_reason": (event.status_reason),
                "error_message": (event.error_message),
                "recorded_at": event.recorded_at,
            }
        ],
        schema=schema,
    )


def append_control_event(
    control_path: Path,
    event: IngestionControlEvent,
) -> None:
    """
    Acrescenta um evento à tabela Delta de controle.
    """

    control_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    write_mode = "append" if is_delta_table(control_path) else "overwrite"

    write_deltalake(
        control_path,
        control_event_to_arrow_table(event),
        mode=write_mode,
    )


def record_ingestion_status(
    control_path: Path,
    *,
    batch_id: str,
    source_file: str,
    source_file_hash: str | None,
    status: str,
    started_at: datetime,
    finished_at: datetime | None = None,
    row_count: int | None = None,
    inserted_row_count: int | None = None,
    duplicate_row_count: int | None = None,
    status_reason: str | None = None,
    error_message: str | None = None,
) -> IngestionControlEvent:
    """
    Cria e persiste um evento de controle.
    """

    event = create_control_event(
        batch_id=batch_id,
        source_file=source_file,
        source_file_hash=source_file_hash,
        status=status,
        started_at=started_at,
        finished_at=finished_at,
        row_count=row_count,
        inserted_row_count=inserted_row_count,
        duplicate_row_count=duplicate_row_count,
        status_reason=status_reason,
        error_message=error_message,
    )

    append_control_event(
        control_path=control_path,
        event=event,
    )

    return event


def load_successful_file_hashes(
    control_path: Path,
) -> set[str]:
    """
    Retorna os hashes que já possuem pelo menos um SUCCESS.

    PROCESSING, FAILED e SKIPPED não representam uma
    ingestão concluída.
    """

    if not is_delta_table(control_path):
        return set()

    dataframe = DeltaTable(str(control_path)).to_pandas(
        columns=[
            "source_file_hash",
            "status",
        ]
    )

    if dataframe.empty:
        return set()

    successful_hashes = dataframe.loc[
        dataframe["status"] == "SUCCESS",
        "source_file_hash",
    ].dropna()

    return {
        str(file_hash)
        for file_hash in successful_hashes.tolist()
        if str(file_hash).strip()
    }


def should_skip_file_hash(
    source_file_hash: str,
    successful_file_hashes: set[str],
) -> bool:
    """
    Decide se o conteúdo já foi processado com sucesso.
    """

    return source_file_hash in successful_file_hashes
