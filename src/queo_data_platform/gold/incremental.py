from dataclasses import dataclass

import duckdb
import pandas as pd

from queo_data_platform.gold.base import (
    SILVER_IDENTITY_RELATION,
    SILVER_TELEMETRY_RELATION,
)


@dataclass(frozen=True)
class GoldIncrementalScope:
    """
    Representa todo o escopo que precisa ser
    recalculado pela Gold.
    """

    event_dates: tuple[str, ...]

    rejection_dates: tuple[str, ...]

    quality_dates: tuple[str, ...]

    affected_devices: tuple[str, ...]

    @property
    def is_empty(self) -> bool:
        """
        Indica que nenhuma partição Silver foi afetada.
        """

        return not self.event_dates and not self.rejection_dates

    @property
    def has_entity_changes(self) -> bool:
        """
        Indica se produtos baseados em device_serial
        precisam ser recalculados.
        """

        return bool(self.affected_devices)


def normalize_partition_values(
    values: (set[str] | list[str] | tuple[str, ...] | None),
) -> tuple[str, ...]:
    """
    Normaliza uma coleção de partições.

    - remove valores vazios;
    - remove duplicatas;
    - remove espaços externos;
    - ordena deterministicamente.
    """

    if values is None:
        return ()

    normalized = {
        str(value).strip()
        for value in values
        if value is not None and str(value).strip()
    }

    return tuple(sorted(normalized))


def build_quality_dates(
    event_dates: (set[str] | list[str] | tuple[str, ...] | None),
    rejection_dates: (set[str] | list[str] | tuple[str, ...] | None),
) -> tuple[str, ...]:
    """
    Datas do data_quality_summary.

    Uma alteração na qualidade pode vir tanto de:
    - eventos aceitos;
    - registros rejeitados.
    """

    normalized_event_dates = normalize_partition_values(event_dates)

    normalized_rejection_dates = normalize_partition_values(rejection_dates)

    return tuple(
        sorted(
            {
                *normalized_event_dates,
                *normalized_rejection_dates,
            }
        )
    )


def register_affected_event_dates(
    connection: duckdb.DuckDBPyConnection,
    event_dates: tuple[str, ...],
) -> None:
    """
    Registra as datas afetadas na conexão DuckDB.
    """

    connection.register(
        "affected_gold_event_dates",
        pd.DataFrame(
            {
                "event_date": pd.Series(
                    event_dates,
                    dtype="string",
                )
            }
        ),
    )


def discover_affected_devices(
    connection: duckdb.DuckDBPyConnection,
    event_dates: (set[str] | list[str] | tuple[str, ...] | None),
) -> tuple[str, ...]:
    """
    Descobre quais dispositivos possuem eventos Silver
    nas datas afetadas.

    Considera tanto:
    - telemetry_events;
    - device_identity_events.
    """

    normalized_event_dates = normalize_partition_values(event_dates)

    if not normalized_event_dates:
        return ()

    register_affected_event_dates(
        connection,
        normalized_event_dates,
    )

    result = connection.execute(
        f"""
        WITH telemetry_devices AS (
            SELECT DISTINCT
                CAST(
                    device_serial AS VARCHAR
                ) AS device_serial

            FROM {SILVER_TELEMETRY_RELATION}

            INNER JOIN affected_gold_event_dates
                ON CAST(
                    {SILVER_TELEMETRY_RELATION}.event_date
                    AS VARCHAR
                ) = affected_gold_event_dates.event_date

            WHERE device_serial IS NOT NULL
        ),

        identity_devices AS (
            SELECT DISTINCT
                CAST(
                    device_serial AS VARCHAR
                ) AS device_serial

            FROM {SILVER_IDENTITY_RELATION}

            INNER JOIN affected_gold_event_dates
                ON CAST(
                    {SILVER_IDENTITY_RELATION}.event_date
                    AS VARCHAR
                ) = affected_gold_event_dates.event_date

            WHERE device_serial IS NOT NULL
        )

        SELECT device_serial
        FROM telemetry_devices

        UNION

        SELECT device_serial
        FROM identity_devices

        ORDER BY device_serial
        """
    ).df()

    return tuple(result["device_serial"].astype(str).tolist())


def build_gold_incremental_scope(
    connection: duckdb.DuckDBPyConnection,
    *,
    affected_event_dates: (set[str] | list[str] | tuple[str, ...] | None),
    affected_rejection_dates: (set[str] | list[str] | tuple[str, ...] | None),
) -> GoldIncrementalScope:
    """
    Constrói todo o escopo incremental da Gold
    a partir das datas afetadas informadas pela Silver.
    """

    event_dates = normalize_partition_values(affected_event_dates)

    rejection_dates = normalize_partition_values(affected_rejection_dates)

    quality_dates = build_quality_dates(
        event_dates,
        rejection_dates,
    )

    affected_devices = discover_affected_devices(
        connection,
        event_dates,
    )

    return GoldIncrementalScope(
        event_dates=event_dates,
        rejection_dates=rejection_dates,
        quality_dates=quality_dates,
        affected_devices=affected_devices,
    )
