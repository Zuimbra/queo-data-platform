import re
from collections.abc import Mapping
from datetime import datetime
from typing import Literal

import pandas as pd

LEGACY_PROTOCOL_VERSION = "V14.06.111"

IMEI_PATTERN = re.compile(r"^[0-9]{15}$")

MESSAGE_TYPE_PATTERN = re.compile(r"^T[0-9]+$")


IdentityResolutionMethod = Literal[
    "DIRECT",
    "LEGACY_IMEI",
    "UNRESOLVED",
]


def validate_identity_resolution_input(
    dataframe: pd.DataFrame,
) -> None:
    """
    Confirma que o DataFrame normalizado possui as evidências
    mínimas necessárias para resolução de identidade.
    """

    required_columns = (
        "server_timestamp",
        "device_timestamp",
        "message_type",
        "protocol_version",
        "device_serial_raw",
        "longitude_raw",
        "source_file",
    )

    missing_columns = [
        column for column in required_columns if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "A entrada para resolução de identidade não possui "
            "todas as colunas necessárias: "
            f"{missing_columns}"
        )


def normalize_device_serial(
    device_serial_raw: object,
) -> str | None:
    """
    Normaliza o serial sem alterar o valor bruto original.

    Exemplos:

    M202527000021P
        -> 202527000021P

    202527000021P
        -> 202527000021P
    """

    if not isinstance(
        device_serial_raw,
        str,
    ):
        return None

    normalized = device_serial_raw.strip()

    if not normalized:
        return None

    normalized = normalized.removeprefix("M")

    return normalized or None


def normalize_imei(
    imei_raw: object,
) -> str | None:
    """
    Aceita somente IMEI com exatamente 15 dígitos.
    """

    if not isinstance(
        imei_raw,
        str,
    ):
        return None

    normalized = imei_raw.strip()

    if not IMEI_PATTERN.fullmatch(normalized):
        return None

    return normalized


def has_valid_timestamp(
    value: object,
) -> bool:
    """
    Verifica se o valor já normalizado representa
    um timestamp válido.
    """

    if not isinstance(
        value,
        datetime,
    ):
        return False

    return not bool(pd.isna(value))


def has_valid_event_timestamp(
    record: Mapping[object, object],
) -> bool:
    """
    Replica a ideia de fallback utilizada pela Silver:

    device_timestamp
        ↓
    server_timestamp
    """

    return has_valid_timestamp(record.get("device_timestamp")) or has_valid_timestamp(
        record.get("server_timestamp")
    )


def build_unambiguous_imei_to_serial_map(
    dataframe: pd.DataFrame,
) -> dict[str, str]:
    """
    Constrói relações confiáveis:

        IMEI -> device_serial

    somente a partir de mensagens T1 que já possuem
    identidade direta.

    Relações ambíguas são descartadas.
    """

    validate_identity_resolution_input(dataframe)

    candidates: dict[
        str,
        set[str],
    ] = {}

    for record in dataframe.to_dict(orient="records"):
        if record.get("message_type") != "T1":
            continue

        if not has_valid_event_timestamp(record):
            continue

        device_serial = normalize_device_serial(record.get("device_serial_raw"))

        if device_serial is None:
            continue

        imei = normalize_imei(record.get("longitude_raw"))

        if imei is None:
            continue

        candidates.setdefault(
            imei,
            set(),
        ).add(device_serial)

    return {
        imei: next(iter(serials))
        for imei, serials in candidates.items()
        if len(serials) == 1
    }


def build_unambiguous_legacy_file_imei_map(
    dataframe: pd.DataFrame,
) -> dict[str, str]:
    """
    Descobre o IMEI contextual de cada arquivo legado.

    Um arquivo somente entra no mapa quando possui
    exatamente um IMEI T1 válido distinto.
    """

    validate_identity_resolution_input(dataframe)

    candidates: dict[
        str,
        set[str],
    ] = {}

    for record in dataframe.to_dict(orient="records"):
        if record.get("protocol_version") != LEGACY_PROTOCOL_VERSION:
            continue

        if record.get("message_type") != "T1":
            continue

        if not has_valid_event_timestamp(record):
            continue

        source_file = record.get("source_file")

        if not isinstance(
            source_file,
            str,
        ):
            continue

        source_file = source_file.strip()

        if not source_file:
            continue

        imei = normalize_imei(record.get("longitude_raw"))

        if imei is None:
            continue

        candidates.setdefault(
            source_file,
            set(),
        ).add(imei)

    return {
        source_file: next(iter(imeis))
        for source_file, imeis in candidates.items()
        if len(imeis) == 1
    }


def validate_identity_event_reference_input(
    dataframe: pd.DataFrame,
) -> None:
    """
    Confirma que um produto Silver de identidade possui
    as evidências mínimas necessárias para servir como
    referência histórica de IMEI -> serial.
    """

    required_columns = (
        "device_serial_raw",
        "imei",
    )

    missing_columns = [
        column for column in required_columns if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "A referência histórica de identidade não possui "
            "todas as colunas necessárias: "
            f"{missing_columns}"
        )


def build_unambiguous_imei_to_serial_map_from_identity_events(
    dataframe: pd.DataFrame,
) -> dict[str, str]:
    """
    Constrói relações IMEI -> serial a partir do produto
    Silver device_identity_events já persistido.

    Somente device_serial_raw é utilizado como evidência
    de identidade direta.

    Isso evita que uma identidade previamente inferida
    seja utilizada para justificar outra inferência.
    """

    validate_identity_event_reference_input(dataframe)

    candidates: dict[
        str,
        set[str],
    ] = {}

    for record in dataframe.to_dict(orient="records"):
        device_serial = normalize_device_serial(record.get("device_serial_raw"))

        if device_serial is None:
            continue

        imei = normalize_imei(record.get("imei"))

        if imei is None:
            continue

        candidates.setdefault(
            imei,
            set(),
        ).add(device_serial)

    return {
        imei: next(iter(serials))
        for imei, serials in candidates.items()
        if len(serials) == 1
    }


def merge_unambiguous_imei_to_serial_maps(
    *mappings: Mapping[str, str],
) -> dict[str, str]:
    """
    Combina múltiplas fontes de IMEI -> serial.

    Uma associação somente permanece utilizável quando,
    considerando todas as fontes, o IMEI continua
    apontando para exatamente um único serial.

    Se qualquer fonte introduzir conflito, a associação
    é descartada.
    """

    candidates: dict[
        str,
        set[str],
    ] = {}

    for mapping in mappings:
        for raw_imei, raw_serial in mapping.items():
            imei = normalize_imei(raw_imei)

            if imei is None:
                continue

            device_serial = normalize_device_serial(raw_serial)

            if device_serial is None:
                continue

            candidates.setdefault(
                imei,
                set(),
            ).add(device_serial)

    return {
        imei: next(iter(serials))
        for imei, serials in candidates.items()
        if len(serials) == 1
    }


def resolve_identity_dataframe(
    dataframe: pd.DataFrame,
    *,
    imei_to_serial: Mapping[
        str,
        str,
    ],
) -> pd.DataFrame:
    """
    Adiciona identidade resolvida ao DataFrame normalizado.

    Estratégias:

    DIRECT:
        serial veio diretamente do registro.

    LEGACY_IMEI:
        serial ausente, mas contexto legado permite
        resolução inequívoca via IMEI.

    UNRESOLVED:
        não existe evidência suficiente.

    device_serial_raw nunca é alterado.
    """

    validate_identity_resolution_input(dataframe)

    legacy_file_imei = build_unambiguous_legacy_file_imei_map(dataframe)

    resolved_serials: list[str | None] = []

    resolution_methods: list[IdentityResolutionMethod] = []

    for record in dataframe.to_dict(orient="records"):
        direct_serial = normalize_device_serial(record.get("device_serial_raw"))

        if direct_serial is not None:
            resolved_serials.append(direct_serial)

            resolution_methods.append("DIRECT")

            continue

        protocol_version = record.get("protocol_version")

        if protocol_version != LEGACY_PROTOCOL_VERSION:
            resolved_serials.append(None)

            resolution_methods.append("UNRESOLVED")

            continue

        message_type = record.get("message_type")

        if not isinstance(
            message_type,
            str,
        ):
            resolved_serials.append(None)

            resolution_methods.append("UNRESOLVED")

            continue

        if not MESSAGE_TYPE_PATTERN.fullmatch(message_type):
            resolved_serials.append(None)

            resolution_methods.append("UNRESOLVED")

            continue

        if not has_valid_event_timestamp(record):
            resolved_serials.append(None)

            resolution_methods.append("UNRESOLVED")

            continue

        source_file_raw = record.get("source_file")

        if not isinstance(
            source_file_raw,
            str,
        ):
            resolved_serials.append(None)

            resolution_methods.append("UNRESOLVED")

            continue

        source_file = source_file_raw.strip()

        if not source_file:
            resolved_serials.append(None)

            resolution_methods.append("UNRESOLVED")

            continue

        imei = legacy_file_imei.get(source_file)

        if imei is None:
            resolved_serials.append(None)

            resolution_methods.append("UNRESOLVED")

            continue

        resolved_serial = normalize_device_serial(imei_to_serial.get(imei))

        if resolved_serial is None:
            resolved_serials.append(None)

            resolution_methods.append("UNRESOLVED")

            continue

        resolved_serials.append(resolved_serial)

        resolution_methods.append("LEGACY_IMEI")

    resolved = dataframe.copy()

    resolved["device_serial"] = resolved_serials

    resolved["device_resolution_method"] = resolution_methods

    return resolved
