from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import duckdb
import pyarrow as pa
from deltalake import DeltaTable

from queo_data_platform.config.settings import Settings
from queo_data_platform.contracts.gold import (
    DATA_QUALITY_SUMMARY_SCHEMA,
    DATA_QUALITY_SUMMARY_TABLE_NAME,
    DEVICE_DAILY_SUMMARY_SCHEMA,
    DEVICE_DAILY_SUMMARY_TABLE_NAME,
    DEVICE_LAST_POSITION_SCHEMA,
    DEVICE_LAST_POSITION_TABLE_NAME,
    DEVICE_ROUTE_POINTS_SCHEMA,
    DEVICE_ROUTE_POINTS_TABLE_NAME,
    DIM_DEVICE_SCHEMA,
    DIM_DEVICE_TABLE_NAME,
    GOLD_DEVICE_KEY,
    GOLD_EVENT_PARTITION_COLUMN,
    GOLD_QUALITY_PARTITION_COLUMN,
)
from queo_data_platform.contracts.silver import (
    DEVICE_IDENTITY_TABLE_NAME,
    REJECTED_LOGS_TABLE_NAME,
    TELEMETRY_TABLE_NAME,
)
from queo_data_platform.gold.base import (
    SILVER_IDENTITY_RELATION,
    SILVER_REJECTED_RELATION,
    SILVER_TELEMETRY_RELATION,
    create_gold_base_views,
)
from queo_data_platform.gold.daily_summary import (
    build_device_daily_summary,
)
from queo_data_platform.gold.dim_device import (
    build_dim_device,
)
from queo_data_platform.gold.incremental import (
    GoldIncrementalScope,
    build_gold_incremental_scope,
    build_quality_dates,
    normalize_partition_values,
)
from queo_data_platform.gold.last_position import (
    build_device_last_position,
)
from queo_data_platform.gold.quality_summary import (
    build_data_quality_summary,
)
from queo_data_platform.gold.route_points import (
    build_device_route_points,
)
from queo_data_platform.gold.writer import (
    write_gold_entity_table,
    write_gold_partitioned_table,
)
from queo_data_platform.infrastructure.delta.table import (
    is_delta_table,
)
from queo_data_platform.silver.service import (
    SilverLoadResult,
)

GoldMode = Literal[
    "FULL",
    "INCREMENTAL",
    "NOOP",
]


@dataclass(frozen=True)
class GoldPaths:
    """
    Caminhos físicos das fontes Silver
    e dos produtos Gold.
    """

    telemetry: Path
    identity: Path
    rejected: Path

    dim_device: Path
    last_position: Path
    route_points: Path
    daily_summary: Path
    quality_summary: Path


@dataclass(frozen=True)
class GoldProducts:
    """
    Resultado dos cinco builders Gold
    antes da persistência Delta.
    """

    dim_device: pa.Table
    last_position: pa.Table
    route_points: pa.Table
    daily_summary: pa.Table
    quality_summary: pa.Table


def empty_gold_table(
    schema: pa.Schema,
) -> pa.Table:
    """
    Cria um produto Gold vazio preservando
    exatamente o schema oficial.
    """

    return pa.Table.from_batches(
        [],
        schema=schema,
    )


@dataclass(frozen=True)
class GoldLoadResult:
    """
    Resume uma execução da camada Gold.
    """

    mode: GoldMode

    affected_event_dates: tuple[str, ...]
    affected_rejection_dates: tuple[str, ...]
    affected_quality_dates: tuple[str, ...]
    affected_devices: tuple[str, ...]

    dim_device_rows_written: int
    last_position_rows_written: int
    route_points_rows_written: int
    daily_summary_rows_written: int
    quality_summary_rows_written: int

    @property
    def has_changes(self) -> bool:
        return self.mode != "NOOP"


def get_gold_paths(
    *,
    silver_dir: Path,
    gold_dir: Path,
) -> GoldPaths:
    """
    Resolve todos os caminhos usados pela Gold.
    """

    return GoldPaths(
        telemetry=silver_dir / TELEMETRY_TABLE_NAME,
        identity=silver_dir / DEVICE_IDENTITY_TABLE_NAME,
        rejected=silver_dir / REJECTED_LOGS_TABLE_NAME,
        dim_device=gold_dir / DIM_DEVICE_TABLE_NAME,
        last_position=gold_dir / DEVICE_LAST_POSITION_TABLE_NAME,
        route_points=gold_dir / DEVICE_ROUTE_POINTS_TABLE_NAME,
        daily_summary=gold_dir / DEVICE_DAILY_SUMMARY_TABLE_NAME,
        quality_summary=gold_dir / DATA_QUALITY_SUMMARY_TABLE_NAME,
    )


def validate_silver_sources(
    paths: GoldPaths,
) -> None:
    """
    A Gold exige os três produtos Silver.
    """

    missing_tables = [
        path
        for path in (
            paths.telemetry,
            paths.identity,
            paths.rejected,
        )
        if not is_delta_table(path)
    ]

    if missing_tables:
        raise FileNotFoundError(
            "A Gold exige todas as Delta Tables Silver. "
            "Tabelas ausentes: "
            f"{missing_tables}"
        )


def gold_supports_incremental_update(
    paths: GoldPaths,
) -> bool:
    """
    O modo incremental só é seguro quando
    todos os cinco produtos Gold já existem.
    """

    return all(
        is_delta_table(path)
        for path in (
            paths.dim_device,
            paths.last_position,
            paths.route_points,
            paths.daily_summary,
            paths.quality_summary,
        )
    )


def register_silver_sources(
    connection: duckdb.DuckDBPyConnection,
    paths: GoldPaths,
) -> None:
    """
    Registra as três Delta Tables Silver
    como relações DuckDB.
    """

    telemetry = DeltaTable(str(paths.telemetry))
    identity = DeltaTable(str(paths.identity))
    rejected = DeltaTable(str(paths.rejected))

    connection.register(
        SILVER_TELEMETRY_RELATION,
        telemetry.to_pyarrow_dataset(),
    )

    connection.register(
        SILVER_IDENTITY_RELATION,
        identity.to_pyarrow_dataset(),
    )

    connection.register(
        SILVER_REJECTED_RELATION,
        rejected.to_pyarrow_dataset(),
    )


def discover_all_event_dates(
    connection: duckdb.DuckDBPyConnection,
) -> tuple[str, ...]:
    """
    Descobre todas as event_dates presentes
    em telemetria ou identidade.
    """

    result = connection.execute(
        f"""
        SELECT DISTINCT
            CAST(
                event_date AS VARCHAR
            ) AS event_date

        FROM {SILVER_TELEMETRY_RELATION}

        WHERE event_date IS NOT NULL

        UNION

        SELECT DISTINCT
            CAST(
                event_date AS VARCHAR
            ) AS event_date

        FROM {SILVER_IDENTITY_RELATION}

        WHERE event_date IS NOT NULL

        ORDER BY event_date
        """
    ).df()

    return tuple(result["event_date"].astype(str).tolist())


def discover_all_rejection_dates(
    connection: duckdb.DuckDBPyConnection,
) -> tuple[str, ...]:
    """
    Descobre todas as partições existentes
    em rejected_logs.
    """

    result = connection.execute(
        f"""
        SELECT DISTINCT
            COALESCE(
                CAST(
                    rejection_date AS VARCHAR
                ),
                'unknown'
            ) AS rejection_date

        FROM {SILVER_REJECTED_RELATION}

        ORDER BY rejection_date
        """
    ).df()

    return tuple(result["rejection_date"].astype(str).tolist())


def build_full_gold_scope(
    connection: duckdb.DuckDBPyConnection,
) -> GoldIncrementalScope:
    """
    Constrói um escopo representando todo
    o estado atual da Silver.

    Embora use GoldIncrementalScope, aqui o objeto
    representa o escopo completo do rebuild.
    """

    event_dates = discover_all_event_dates(connection)

    rejection_dates = discover_all_rejection_dates(connection)

    return build_gold_incremental_scope(
        connection,
        affected_event_dates=event_dates,
        affected_rejection_dates=rejection_dates,
    )


def build_gold_products(
    connection: duckdb.DuckDBPyConnection,
    *,
    full_rebuild: bool,
    scope: GoldIncrementalScope,
) -> GoldProducts:
    """
    Executa os cinco builders Gold.

    FULL:
        reconstrói todos os produtos usando
        todo o estado atual da Silver.

    INCREMENTAL:
        executa somente os builders realmente
        afetados pelo escopo.
    """

    if full_rebuild:
        return GoldProducts(
            dim_device=build_dim_device(connection),
            last_position=(build_device_last_position(connection)),
            route_points=(build_device_route_points(connection)),
            daily_summary=(build_device_daily_summary(connection)),
            quality_summary=(build_data_quality_summary(connection)),
        )

    if scope.affected_devices:
        dim_device = build_dim_device(
            connection,
            affected_devices=(scope.affected_devices),
        )

        last_position = build_device_last_position(
            connection,
            affected_devices=(scope.affected_devices),
        )

    else:
        dim_device = empty_gold_table(DIM_DEVICE_SCHEMA)

        last_position = empty_gold_table(DEVICE_LAST_POSITION_SCHEMA)

    if scope.event_dates:
        route_points = build_device_route_points(
            connection,
            event_dates=(scope.event_dates),
        )

        daily_summary = build_device_daily_summary(
            connection,
            event_dates=(scope.event_dates),
        )

    else:
        route_points = empty_gold_table(DEVICE_ROUTE_POINTS_SCHEMA)

        daily_summary = empty_gold_table(DEVICE_DAILY_SUMMARY_SCHEMA)

    if scope.quality_dates:
        quality_summary = build_data_quality_summary(
            connection,
            metric_dates=(scope.quality_dates),
        )

    else:
        quality_summary = empty_gold_table(DATA_QUALITY_SUMMARY_SCHEMA)

    return GoldProducts(
        dim_device=dim_device,
        last_position=last_position,
        route_points=route_points,
        daily_summary=daily_summary,
        quality_summary=quality_summary,
    )


def write_gold_products(
    *,
    paths: GoldPaths,
    products: GoldProducts,
    scope: GoldIncrementalScope,
    full_rebuild: bool,
) -> tuple[
    int,
    int,
    int,
    int,
    int,
]:
    """
    Persiste os cinco produtos usando
    a estratégia apropriada.
    """

    dim_device_rows = write_gold_entity_table(
        paths.dim_device,
        products.dim_device,
        schema=DIM_DEVICE_SCHEMA,
        key_column=GOLD_DEVICE_KEY,
        full_rebuild=full_rebuild,
    )

    last_position_rows = write_gold_entity_table(
        paths.last_position,
        products.last_position,
        schema=DEVICE_LAST_POSITION_SCHEMA,
        key_column=GOLD_DEVICE_KEY,
        full_rebuild=full_rebuild,
    )

    route_points_rows = write_gold_partitioned_table(
        paths.route_points,
        products.route_points,
        schema=DEVICE_ROUTE_POINTS_SCHEMA,
        partition_by=GOLD_EVENT_PARTITION_COLUMN,
        full_rebuild=full_rebuild,
        affected_partitions=scope.event_dates,
    )

    daily_summary_rows = write_gold_partitioned_table(
        paths.daily_summary,
        products.daily_summary,
        schema=DEVICE_DAILY_SUMMARY_SCHEMA,
        partition_by=GOLD_EVENT_PARTITION_COLUMN,
        full_rebuild=full_rebuild,
        affected_partitions=scope.event_dates,
    )

    quality_summary_rows = write_gold_partitioned_table(
        paths.quality_summary,
        products.quality_summary,
        schema=DATA_QUALITY_SUMMARY_SCHEMA,
        partition_by=GOLD_QUALITY_PARTITION_COLUMN,
        full_rebuild=full_rebuild,
        affected_partitions=scope.quality_dates,
    )

    return (
        dim_device_rows,
        last_position_rows,
        route_points_rows,
        daily_summary_rows,
        quality_summary_rows,
    )


def build_noop_result(
    *,
    silver_result: SilverLoadResult | None,
) -> GoldLoadResult:
    """
    Cria o resultado de uma execução sem alterações.
    """

    if silver_result is None:
        event_dates: tuple[str, ...] = ()
        rejection_dates: tuple[str, ...] = ()
    else:
        event_dates = normalize_partition_values(silver_result.affected_event_dates)

        rejection_dates = normalize_partition_values(
            silver_result.affected_rejection_dates
        )

    return GoldLoadResult(
        mode="NOOP",
        affected_event_dates=event_dates,
        affected_rejection_dates=rejection_dates,
        affected_quality_dates=build_quality_dates(
            event_dates,
            rejection_dates,
        ),
        affected_devices=(),
        dim_device_rows_written=0,
        last_position_rows_written=0,
        route_points_rows_written=0,
        daily_summary_rows_written=0,
        quality_summary_rows_written=0,
    )


def load_gold_data(
    *,
    silver_dir: Path,
    gold_dir: Path,
    silver_result: SilverLoadResult | None = None,
) -> GoldLoadResult:
    """
    Atualiza a Gold a partir da Silver.

    Sem SilverLoadResult:
        FULL.

    Silver FULL:
        FULL.

    Silver INCREMENTAL + Gold completa:
        INCREMENTAL.

    Silver NOOP + Gold completa:
        NOOP.

    Gold inexistente ou incompleta:
        FULL, independentemente do resultado Silver.
    """

    paths = get_gold_paths(
        silver_dir=silver_dir,
        gold_dir=gold_dir,
    )

    validate_silver_sources(paths)

    incremental_supported = gold_supports_incremental_update(paths)

    if (
        not incremental_supported
        or silver_result is None
        or silver_result.mode == "FULL"
    ):
        full_rebuild = True

    elif silver_result.mode == "NOOP":
        return build_noop_result(silver_result=silver_result)

    else:
        full_rebuild = False

    connection = duckdb.connect()

    try:
        register_silver_sources(
            connection,
            paths,
        )

        create_gold_base_views(connection)

        if full_rebuild:
            scope = build_full_gold_scope(connection)

            mode: GoldMode = "FULL"

        else:
            assert silver_result is not None

            scope = build_gold_incremental_scope(
                connection,
                affected_event_dates=(silver_result.affected_event_dates),
                affected_rejection_dates=(silver_result.affected_rejection_dates),
            )

            if scope.is_empty:
                return build_noop_result(silver_result=silver_result)

            mode = "INCREMENTAL"

        products = build_gold_products(
            connection,
            full_rebuild=full_rebuild,
            scope=scope,
        )

        (
            dim_device_rows,
            last_position_rows,
            route_points_rows,
            daily_summary_rows,
            quality_summary_rows,
        ) = write_gold_products(
            paths=paths,
            products=products,
            scope=scope,
            full_rebuild=full_rebuild,
        )

        return GoldLoadResult(
            mode=mode,
            affected_event_dates=scope.event_dates,
            affected_rejection_dates=scope.rejection_dates,
            affected_quality_dates=scope.quality_dates,
            affected_devices=scope.affected_devices,
            dim_device_rows_written=dim_device_rows,
            last_position_rows_written=last_position_rows,
            route_points_rows_written=route_points_rows,
            daily_summary_rows_written=daily_summary_rows,
            quality_summary_rows_written=quality_summary_rows,
        )

    finally:
        connection.close()


def load_gold(
    settings: Settings,
    *,
    silver_result: SilverLoadResult | None = None,
) -> GoldLoadResult:
    """
    Interface pública da Gold baseada em Settings.
    """

    return load_gold_data(
        silver_dir=settings.silver_dir,
        gold_dir=settings.gold_dir,
        silver_result=silver_result,
    )
