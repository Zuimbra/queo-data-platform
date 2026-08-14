from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from pandas.errors import EmptyDataError, ParserError

from queo_data_platform.contracts.tracker import (
    BRONZE_METADATA_COLUMNS,
    RAW_TRACKER_REQUIRED_COLUMNS,
)


@dataclass(frozen=True)
class FileValidationResult:
    """
    Resultado da validação estrutural de um arquivo de entrada.

    A Bronze valida apenas se o arquivo pode ser ingerido com segurança.
    Regras de negócio sobre timestamps, coordenadas e conteúdo das linhas
    pertencem às camadas posteriores.
    """

    source_path: Path
    is_valid: bool
    dataframe: pd.DataFrame | None = None
    row_count: int = 0
    detected_encoding: str | None = None
    missing_columns: tuple[str, ...] = ()
    reserved_columns: tuple[str, ...] = ()
    duplicated_columns: tuple[str, ...] = ()
    error_message: str | None = None


def normalize_column_names(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Remove espaços externos dos nomes das colunas.

    Exemplo:
        " LAT " -> "LAT"

    O conteúdo das linhas não é alterado.
    """

    normalized_dataframe = dataframe.copy()

    normalized_dataframe.columns = [
        str(column).strip() for column in normalized_dataframe.columns
    ]

    return normalized_dataframe


def read_csv_with_supported_encoding(
    file_path: Path,
) -> tuple[pd.DataFrame, str]:
    """
    Lê um CSV tentando UTF-8 primeiro e Latin-1 como fallback.

    dtype=str evita inferência prematura de tipos na Bronze.
    keep_default_na=False preserva strings vazias como strings vazias.
    """

    try:
        dataframe = pd.read_csv(
            file_path,
            encoding="utf-8-sig",
            dtype=str,
            keep_default_na=False,
        )

        return dataframe, "utf-8-sig"

    except UnicodeDecodeError:
        dataframe = pd.read_csv(
            file_path,
            encoding="latin-1",
            dtype=str,
            keep_default_na=False,
        )

        return dataframe, "latin-1"


def find_missing_columns(
    dataframe: pd.DataFrame,
) -> tuple[str, ...]:
    """
    Retorna as colunas obrigatórias da fonte que não estão presentes.

    Colunas extras são permitidas.
    """

    available_columns = set(dataframe.columns)

    return tuple(
        column
        for column in RAW_TRACKER_REQUIRED_COLUMNS
        if column not in available_columns
    )


def find_reserved_columns(
    dataframe: pd.DataFrame,
) -> tuple[str, ...]:
    """
    Detecta metadados técnicos que não podem vir do arquivo bruto.

    Esses campos devem ser gerados exclusivamente pela plataforma.
    """

    available_columns = set(dataframe.columns)

    return tuple(
        column for column in BRONZE_METADATA_COLUMNS if column in available_columns
    )


def find_duplicated_columns(
    dataframe: pd.DataFrame,
) -> tuple[str, ...]:
    """
    Detecta nomes duplicados depois da normalização das colunas.
    """

    duplicated = dataframe.columns[dataframe.columns.duplicated()]

    return tuple(dict.fromkeys(str(column) for column in duplicated))


def validate_input_file(
    file_path: Path,
) -> FileValidationResult:
    """
    Valida estruturalmente um CSV antes da ingestão Bronze.

    São considerados inválidos:
    - caminho inexistente ou que não seja arquivo;
    - arquivo que não seja CSV;
    - arquivo vazio;
    - CSV ilegível ou inconsistente;
    - ausência de colunas obrigatórias;
    - uso de nomes reservados da Bronze;
    - colunas duplicadas após normalização.

    Colunas extras são aceitas.
    """

    if not file_path.is_file():
        return FileValidationResult(
            source_path=file_path,
            is_valid=False,
            error_message="O caminho não representa um arquivo.",
        )

    if file_path.suffix.lower() != ".csv":
        return FileValidationResult(
            source_path=file_path,
            is_valid=False,
            error_message="A extensão do arquivo não é CSV.",
        )

    if file_path.stat().st_size == 0:
        return FileValidationResult(
            source_path=file_path,
            is_valid=False,
            error_message="O arquivo está vazio.",
        )

    try:
        dataframe, detected_encoding = read_csv_with_supported_encoding(file_path)

        dataframe = normalize_column_names(dataframe)

    except EmptyDataError:
        return FileValidationResult(
            source_path=file_path,
            is_valid=False,
            error_message=("O arquivo não contém cabeçalho ou dados legíveis."),
        )

    except ParserError as error:
        return FileValidationResult(
            source_path=file_path,
            is_valid=False,
            error_message=(f"O CSV possui estrutura inconsistente: {error}"),
        )

    except (OSError, UnicodeError, ValueError) as error:
        return FileValidationResult(
            source_path=file_path,
            is_valid=False,
            error_message=(f"Não foi possível ler o arquivo: {error}"),
        )

    if dataframe.empty:
        return FileValidationResult(
            source_path=file_path,
            is_valid=False,
            dataframe=dataframe,
            detected_encoding=detected_encoding,
            error_message="O arquivo não possui linhas de dados.",
        )

    duplicated_columns = find_duplicated_columns(dataframe)

    if duplicated_columns:
        return FileValidationResult(
            source_path=file_path,
            is_valid=False,
            dataframe=dataframe,
            row_count=len(dataframe),
            detected_encoding=detected_encoding,
            duplicated_columns=duplicated_columns,
            error_message=("O arquivo possui nomes de colunas duplicados."),
        )

    missing_columns = find_missing_columns(dataframe)

    if missing_columns:
        return FileValidationResult(
            source_path=file_path,
            is_valid=False,
            dataframe=dataframe,
            row_count=len(dataframe),
            detected_encoding=detected_encoding,
            missing_columns=missing_columns,
            error_message=("O arquivo não possui todas as colunas obrigatórias."),
        )

    reserved_columns = find_reserved_columns(dataframe)

    if reserved_columns:
        return FileValidationResult(
            source_path=file_path,
            is_valid=False,
            dataframe=dataframe,
            row_count=len(dataframe),
            detected_encoding=detected_encoding,
            reserved_columns=reserved_columns,
            error_message=(
                "O arquivo utiliza nomes reservados para metadados da Bronze."
            ),
        )

    return FileValidationResult(
        source_path=file_path,
        is_valid=True,
        dataframe=dataframe,
        row_count=len(dataframe),
        detected_encoding=detected_encoding,
    )
