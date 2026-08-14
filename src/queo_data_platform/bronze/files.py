from hashlib import sha256
from pathlib import Path


def discover_csv_files(inbox_dir: Path) -> list[Path]:
    """
    Descobre os arquivos CSV disponíveis para ingestão.

    Apenas arquivos diretamente dentro do diretório informado
    são considerados. Subdiretórios não são percorridos.

    O resultado é ordenado pelo nome para garantir um
    comportamento determinístico entre execuções.
    """

    # Um inbox ainda não criado representa simplesmente
    # ausência de arquivos para processar.
    if not inbox_dir.exists():
        return []

    # Percorre somente o primeiro nível do diretório.
    #
    # is_file():
    # garante que diretórios não sejam retornados.
    #
    # suffix.lower():
    # permite extensões como .csv e .CSV.
    csv_files = [
        path
        for path in inbox_dir.iterdir()
        if path.is_file() and path.suffix.lower() == ".csv"
    ]

    # A ordenação evita que a ordem de processamento dependa
    # do sistema operacional ou do filesystem.
    return sorted(
        csv_files,
        key=lambda path: path.name.lower(),
    )


def calculate_file_sha256(file_path: Path) -> str:
    """
    Calcula o SHA-256 do conteúdo de um arquivo.

    O hash identifica o conteúdo do arquivo independentemente
    de seu nome e será usado posteriormente no controle de
    ingestão e na idempotência da Bronze.
    """

    # Inicializa o algoritmo SHA-256.
    digest = sha256()

    # O arquivo é lido em modo binário porque o hash deve ser
    # calculado sobre os bytes reais, sem depender de encoding.
    with file_path.open("rb") as file:
        # Processa o arquivo em blocos de 1 MiB.
        #
        # Isso evita carregar arquivos potencialmente grandes
        # inteiros na memória.
        while chunk := file.read(1024 * 1024):
            digest.update(chunk)

    # SHA-256 em representação hexadecimal possui 64 caracteres.
    return digest.hexdigest()
