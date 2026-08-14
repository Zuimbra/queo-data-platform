from pathlib import Path

from deltalake import DeltaTable


def is_delta_table(table_path: Path) -> bool:
    """
    Verifica se existe uma Delta Table válida no caminho informado.
    """

    return DeltaTable.is_deltatable(str(table_path))


def open_delta_table(table_path: Path) -> DeltaTable:
    """
    Abre uma Delta Table existente.
    """

    return DeltaTable(str(table_path))
