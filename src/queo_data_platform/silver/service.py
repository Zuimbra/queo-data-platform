from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pandas as pd
from deltalake import DeltaTable

from queo_data_platform.config.settings import Settings
from queo_data_platform.contracts.silver import (
    DEVICE_IDENTITY_SCHEMA,
    DEVICE_IDENTITY_TABLE_NAME,
    REJECTED_LOGS_SCHEMA,
    REJECTED_LOGS_TABLE_NAME,
    SILVER_EVENT_PARTITION_COLUMN,
    SILVER_REJECTION_PARTITION_COLUMN,
    TELEMETRY_SCHEMA,
    TELEMETRY_TABLE_NAME,
)
from queo_data_platform.contracts.tracker import (
    BRONZE_TABLE_NAME,
)
from queo_data_platform.infrastructure.delta.table import (
    is_delta_table,
)
from queo_data_platform.silver.classification import (
    classify_normalized_dataframe,
)
from queo_data_platform.silver.incremental import (
    SilverAffectedPartitions,
    discover_affected_partitions,
    load_incremental_bronze_scope,
    normalize_batch_ids,
)
from queo_data_platform.silver.normalization import (
    normalize_bronze_dataframe,
)
from queo_data_platform.silver.transformation import (
    transform_identity_dataframe,
    transform_telemetry_dataframe,
)
from queo_data_platform.silver.writer import (
    dataframe_to_arrow,
    write_full_silver_table,
    write_incremental_silver_partitions,
)

SilverMode = Literal[
    "FULL",
    "INCREMENTAL",
    "NOOP",
]


@dataclass(frozen=True)
class SilverLoadResult:
    """
    Resume o processamento executado pela Silver.

    affected_event_dates será utilizado posteriormente
    para limitar também o processamento da Gold.
    """

    mode: SilverMode

    batch_ids: tuple[str, ...]

    affected_event_dates: tuple[str, ...]
    affected_rejection_dates: tuple[str, ...]

    telemetry_rows_written: int
    identity_rows_written: int
    rejected_rows_written: int

    @property
    def has_changes(self) -> bool:
        """
        Indica se a Silver executou alguma reconstrução.
        """

        return self.mode != "NOOP"


@dataclass(frozen=True)
class SilverPaths:
    bronze: Path

    telemetry: Path
    identity: Path
    rejected: Path


def get_silver_paths(
    *,
    bronze_dir: Path,
    silver_dir: Path,
) -> SilverPaths:
    """
    Resolve os caminhos físicos utilizados pela Silver.
    """

    return SilverPaths(
        bronze=(bronze_dir / BRONZE_TABLE_NAME),
        telemetry=(silver_dir / TELEMETRY_TABLE_NAME),
        identity=(silver_dir / DEVICE_IDENTITY_TABLE_NAME),
        rejected=(silver_dir / REJECTED_LOGS_TABLE_NAME),
    )


def load_bronze_table(
    bronze_path: Path,
) -> DeltaTable:
    """
    Abre a Bronze consolidada utilizada como fonte da Silver.
    """

    if not is_delta_table(bronze_path):
        raise FileNotFoundError(f"A Delta Table Bronze não existe: {bronze_path}")

    return DeltaTable(str(bronze_path))


def silver_supports_incremental_update(
    paths: SilverPaths,
) -> bool:
    """
    Incrementalidade exige que os três produtos Silver
    já existam como Delta Tables.

    Se qualquer produto estiver ausente, fazemos um
    rebuild completo para reconstruir um estado consistente.
    """

    return all(
        (
            is_delta_table(paths.telemetry),
            is_delta_table(paths.identity),
            is_delta_table(paths.rejected),
        )
    )


def get_unique_string_values(
    dataframe: pd.DataFrame,
    column: str,
) -> tuple[str, ...]:
    """
    Extrai valores textuais únicos, não nulos e ordenados.
    """

    if column not in dataframe.columns:
        return ()

    return tuple(sorted({str(value) for value in dataframe[column].dropna()}))


def write_silver_products(
    *,
    paths: SilverPaths,
    telemetry: pd.DataFrame,
    identity: pd.DataFrame,
    rejected: pd.DataFrame,
    full_rebuild: bool,
    affected_partitions: SilverAffectedPartitions,
) -> tuple[int, int, int]:
    """
    Converte os produtos para Arrow e os persiste.

    FULL:
        substitui completamente cada produto Silver.

    INCREMENTAL:
        substitui somente as partições afetadas.
    """

    telemetry_table = dataframe_to_arrow(
        telemetry,
        TELEMETRY_SCHEMA,
    )

    identity_table = dataframe_to_arrow(
        identity,
        DEVICE_IDENTITY_SCHEMA,
    )

    rejected_table = dataframe_to_arrow(
        rejected,
        REJECTED_LOGS_SCHEMA,
    )

    if full_rebuild:
        telemetry_rows = write_full_silver_table(
            paths.telemetry,
            telemetry_table,
            partition_by=(SILVER_EVENT_PARTITION_COLUMN),
        )

        identity_rows = write_full_silver_table(
            paths.identity,
            identity_table,
            partition_by=(SILVER_EVENT_PARTITION_COLUMN),
        )

        rejected_rows = write_full_silver_table(
            paths.rejected,
            rejected_table,
            partition_by=(SILVER_REJECTION_PARTITION_COLUMN),
        )

        return (
            telemetry_rows,
            identity_rows,
            rejected_rows,
        )

    telemetry_rows = write_incremental_silver_partitions(
        paths.telemetry,
        telemetry_table,
        partition_by=(SILVER_EVENT_PARTITION_COLUMN),
        affected_partitions=(affected_partitions.event_dates),
    )

    identity_rows = write_incremental_silver_partitions(
        paths.identity,
        identity_table,
        partition_by=(SILVER_EVENT_PARTITION_COLUMN),
        affected_partitions=(affected_partitions.event_dates),
    )

    rejected_rows = write_incremental_silver_partitions(
        paths.rejected,
        rejected_table,
        partition_by=(SILVER_REJECTION_PARTITION_COLUMN),
        affected_partitions=(affected_partitions.rejection_dates),
    )

    return (
        telemetry_rows,
        identity_rows,
        rejected_rows,
    )


def load_silver_data(
    *,
    bronze_dir: Path,
    silver_dir: Path,
    batch_ids: (set[str] | list[str] | tuple[str, ...] | None) = None,
) -> SilverLoadResult:
    """
    Atualiza a Silver a partir da Bronze consolidada.

    Sem batch_ids:
        executa rebuild completo.

    Com batch_ids e Silver existente:
        descobre as partições afetadas e executa
        reconstrução incremental.

    Com batch_ids que não existem na Bronze:
        retorna NOOP.

    Com Silver incompleta ou inexistente:
        executa rebuild completo.
    """

    paths = get_silver_paths(
        bronze_dir=bronze_dir,
        silver_dir=silver_dir,
    )

    bronze_table = load_bronze_table(paths.bronze)

    normalized_batch_ids = normalize_batch_ids(
        batch_ids,
    )

    requested_full_rebuild = batch_ids is None

    incremental_supported = silver_supports_incremental_update(
        paths,
    )

    if requested_full_rebuild or not incremental_supported:
        full_rebuild = True

    elif not normalized_batch_ids:
        return SilverLoadResult(
            mode="NOOP",
            batch_ids=(),
            affected_event_dates=(),
            affected_rejection_dates=(),
            telemetry_rows_written=0,
            identity_rows_written=0,
            rejected_rows_written=0,
        )

    else:
        full_rebuild = False

    # --------------------------------------------------
    # DEFINE O ESCOPO BRONZE
    # --------------------------------------------------

    if full_rebuild:
        bronze_scope = bronze_table.to_pandas()

        affected_partitions = SilverAffectedPartitions(
            event_dates=(),
            rejection_dates=(),
        )

    else:
        affected_partitions = discover_affected_partitions(
            bronze_table,
            normalized_batch_ids,
        )

        # Batch solicitado não existe na Bronze
        # ou não afeta nenhuma partição.
        if affected_partitions.is_empty:
            return SilverLoadResult(
                mode="NOOP",
                batch_ids=(normalized_batch_ids),
                affected_event_dates=(),
                affected_rejection_dates=(),
                telemetry_rows_written=0,
                identity_rows_written=0,
                rejected_rows_written=0,
            )

        bronze_scope = load_incremental_bronze_scope(
            bronze_table,
            affected_partitions,
        )

    # --------------------------------------------------
    # BRONZE -> NORMALIZAÇÃO
    # --------------------------------------------------

    normalized = normalize_bronze_dataframe(bronze_scope)

    # --------------------------------------------------
    # CLASSIFICAÇÃO
    # --------------------------------------------------

    classified = classify_normalized_dataframe(normalized)

    # --------------------------------------------------
    # PRODUTOS TIPADOS
    # --------------------------------------------------

    telemetry = transform_telemetry_dataframe(classified.telemetry)

    identity = transform_identity_dataframe(classified.identity)

    # rejected já está no formato lógico esperado.
    rejected = classified.rejected

    # --------------------------------------------------
    # PERSISTÊNCIA
    # --------------------------------------------------

    (
        telemetry_rows_written,
        identity_rows_written,
        rejected_rows_written,
    ) = write_silver_products(
        paths=paths,
        telemetry=telemetry,
        identity=identity,
        rejected=rejected,
        full_rebuild=full_rebuild,
        affected_partitions=(affected_partitions),
    )

    # --------------------------------------------------
    # RESULTADO
    # --------------------------------------------------

    if full_rebuild:
        affected_event_dates = tuple(
            sorted(
                {
                    *get_unique_string_values(
                        telemetry,
                        "event_date",
                    ),
                    *get_unique_string_values(
                        identity,
                        "event_date",
                    ),
                }
            )
        )

        affected_rejection_dates = get_unique_string_values(
            rejected,
            "rejection_date",
        )

        mode: SilverMode = "FULL"

    else:
        affected_event_dates = affected_partitions.event_dates

        affected_rejection_dates = affected_partitions.rejection_dates

        mode = "INCREMENTAL"

    return SilverLoadResult(
        mode=mode,
        batch_ids=normalized_batch_ids,
        affected_event_dates=(affected_event_dates),
        affected_rejection_dates=(affected_rejection_dates),
        telemetry_rows_written=(telemetry_rows_written),
        identity_rows_written=(identity_rows_written),
        rejected_rows_written=(rejected_rows_written),
    )


def load_silver(
    settings: Settings,
    *,
    batch_ids: (set[str] | list[str] | tuple[str, ...] | None) = None,
) -> SilverLoadResult:
    """
    Interface pública da camada Silver baseada em Settings.
    """

    return load_silver_data(
        bronze_dir=settings.bronze_dir,
        silver_dir=settings.silver_dir,
        batch_ids=batch_ids,
    )
