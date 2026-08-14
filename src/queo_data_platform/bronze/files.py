from hashlib import sha256
from pathlib import Path
from shutil import move


def discover_csv_files(inbox_dir: Path) -> list[Path]:
    """
    Descobre os arquivos CSV disponíveis para ingestão.

    Apenas arquivos diretamente dentro do diretório informado
    são considerados. Subdiretórios não são percorridos.

    O resultado é ordenado pelo nome para garantir um
    comportamento determinístico entre execuções.
    """

    if not inbox_dir.exists():
        return []

    csv_files = [
        path
        for path in inbox_dir.iterdir()
        if path.is_file() and path.suffix.lower() == ".csv"
    ]

    return sorted(
        csv_files,
        key=lambda path: path.name.lower(),
    )


def calculate_file_sha256(file_path: Path) -> str:
    """
    Calcula o SHA-256 do conteúdo de um arquivo.
    """

    digest = sha256()

    with file_path.open("rb") as file:
        while chunk := file.read(1024 * 1024):
            digest.update(chunk)

    return digest.hexdigest()


def move_file(
    source_path: Path,
    destination_dir: Path,
    *,
    conflict_suffix: str | None = None,
) -> Path:
    """
    Move um arquivo para outro diretório.

    Se já existir um arquivo com o mesmo nome no destino,
    conflict_suffix é acrescentado ao nome para evitar overwrite.
    """

    if not source_path.is_file():
        raise FileNotFoundError(f"Arquivo de origem não encontrado: {source_path}")

    destination_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination_path = destination_dir / source_path.name

    if destination_path.exists():
        if not conflict_suffix:
            raise FileExistsError(
                f"Já existe um arquivo com o mesmo nome no destino: {destination_path}"
            )

        destination_path = destination_dir / (
            f"{source_path.stem}__{conflict_suffix}{source_path.suffix}"
        )

    if destination_path.exists():
        raise FileExistsError(f"O arquivo de destino já existe: {destination_path}")

    move(
        str(source_path),
        str(destination_path),
    )

    return destination_path
