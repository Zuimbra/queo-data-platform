# Passo a passo — criação inicial do `queo-data-platform`

Este documento registra apenas os passos executados até aqui para criar a base do projeto.

---

# 1. Criar e acessar a pasta do projeto

## O que?

Criar uma pasta separada para o novo projeto:

```text
queo-data-platform/
```

Depois acessar a pasta:

```powershell
cd C:\Users\COLABORADOR QUEO.COLABORADOR.000\BigData\queo-data-platform
```

## Para que?

Separar a nova plataforma do projeto experimental anterior.

A ideia é reutilizar apenas as partes comprovadamente úteis, mas reorganizar o código desde o início.

---

# 2. Inicializar o projeto com `uv`

Executar:

```powershell
uv init --app .
```

## O que?

O `uv` passa a gerenciar:

```text
ambiente Python
dependências
versões
execução do projeto
```

Ele cria arquivos como:

```text
pyproject.toml
.python-version
README.md
uv.lock
```

## Para que?

Centralizar a configuração do projeto e evitar gerenciamento manual com `pip` e `venv`.

---

# 3. Configurar o `pyproject.toml`

O arquivo ficou assim:

```toml
[project]
name = "queo-data-platform"
version = "0.1.0"
description = "Enterprise data platform for ingestion, Lakehouse processing, APIs, analytics, and MCP integration."
readme = "README.md"
requires-python = ">=3.14"
dependencies = []

[dependency-groups]
dev = [
    "pyright>=1.1.411",
    "pytest>=9.1.1",
    "ruff>=0.16.3",
]
```

## O que?

O `pyproject.toml` é a configuração central do projeto Python.

Ele define:

```text
nome
versão
versão do Python
dependências
dependências de desenvolvimento
```

## Para que?

Permitir que o `uv` saiba como montar e executar o ambiente do projeto.

---

# 4. Criar o package principal

Foi criada a estrutura:

```text
src/
└── queo_data_platform/
    └── __init__.py
```

## O que?

`queo_data_platform` é o package principal da aplicação.

O nome usa `_` porque um package Python não pode ser importado usando hífen:

```python
import queo_data_platform
```

## Para que?

Permitir imports organizados como:

```python
from queo_data_platform.bronze.service import load_bronze
```

em vez de depender de arquivos Python soltos na raiz.

---

# 5. Criar os packages por responsabilidade

Foi criada a estrutura:

```text
src/
└── queo_data_platform/
    ├── api/
    ├── bronze/
    ├── config/
    ├── contracts/
    ├── gold/
    ├── infrastructure/
    ├── mcp/
    ├── pipeline/
    ├── query/
    └── silver/
```

Cada pasta recebeu:

```text
__init__.py
```

A estrutura criada localmente confirma esses packages.

## Para que?

Separar responsabilidades desde o início.

```text
config
→ configuração

contracts
→ contratos compartilhados

infrastructure
→ detalhes técnicos compartilhados

bronze
→ ingestão

silver
→ limpeza e transformação

gold
→ produtos de dados

query
→ leitura da Gold

api
→ REST API

mcp
→ interface MCP

pipeline
→ orquestração
```

---

# 6. Criar a estrutura de testes

Foi criada:

```text
tests/
├── api/
├── integration/
├── mcp/
└── unit/
```

A estrutura também está presente localmente.

## Para que?

Separar diferentes tipos de teste.

```text
unit
→ funções e módulos isolados

integration
→ componentes trabalhando juntos

api
→ endpoints

mcp
→ tools e comportamento MCP
```

---

# 7. Instalar ferramentas de desenvolvimento

Executar:

```powershell
uv add --dev pytest ruff pyright
```

Isso adiciona:

```toml
[dependency-groups]
dev = [
    "pyright>=1.1.411",
    "pytest>=9.1.1",
    "ruff>=0.16.3",
]
```

## Para que?

### `pytest`

Executar testes:

```powershell
uv run pytest
```

### `ruff`

Encontrar problemas de estilo e qualidade:

```powershell
uv run ruff check .
```

### `pyright`

Verificar erros de tipagem:

```powershell
uv run pyright
```

---

# 8. Remover o `main.py` criado pelo `uv`

O `uv init` havia criado um:

```text
main.py
```

na raiz.

Ele foi removido:

```powershell
Remove-Item main.py
```

## Para que?

O projeto terá pontos de entrada específicos dentro do package:

```text
api/
mcp/
pipeline/
```

Então um `main.py` genérico na raiz não é necessário.

---

# 9. Criar `settings.py`

Foi criado:

```text
src/
└── queo_data_platform/
    └── config/
        └── settings.py
```

Com:

```python
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    project_root: Path
    data_dir: Path
    raw_dir: Path
    lakehouse_dir: Path
    control_dir: Path
    bronze_dir: Path
    silver_dir: Path
    gold_dir: Path


def load_settings() -> Settings:
    project_root = Path(__file__).resolve().parents[3]

    data_dir = project_root / "data"
    raw_dir = data_dir / "raw"
    lakehouse_dir = data_dir / "lakehouse"

    return Settings(
        project_root=project_root,
        data_dir=data_dir,
        raw_dir=raw_dir,
        lakehouse_dir=lakehouse_dir,
        control_dir=lakehouse_dir / "00_control",
        bronze_dir=lakehouse_dir / "01_bronze",
        silver_dir=lakehouse_dir / "02_silver",
        gold_dir=lakehouse_dir / "03_gold",
    )


settings = load_settings()
```

## O que?

Esse arquivo centraliza os caminhos utilizados pela aplicação.

---

## `@dataclass(frozen=True)`

```python
@dataclass(frozen=True)
class Settings:
```

`dataclass` reduz código necessário para criar uma classe usada principalmente para armazenar dados.

`frozen=True` impede alteração das configurações depois da criação.

Por exemplo:

```python
settings.gold_dir = Path("outro")
```

não deve ser permitido.

---

## Descobrir a raiz

```python
project_root = Path(__file__).resolve().parents[3]
```

O arquivo está em:

```text
queo-data-platform/
└── src/
    └── queo_data_platform/
        └── config/
            └── settings.py
```

Então:

```text
parents[0] → config
parents[1] → queo_data_platform
parents[2] → src
parents[3] → queo-data-platform
```

Assim `project_root` aponta para a raiz.

---

## Construir os caminhos

```python
data_dir = project_root / "data"
raw_dir = data_dir / "raw"
lakehouse_dir = data_dir / "lakehouse"
```

O operador `/` de `Path` monta caminhos.

Depois:

```python
control_dir = (lakehouse_dir / "00_control",)
bronze_dir = (lakehouse_dir / "01_bronze",)
silver_dir = (lakehouse_dir / "02_silver",)
gold_dir = (lakehouse_dir / "03_gold",)
```

centraliza os diretórios de cada camada.

Assim, em outros módulos, usamos:

```python
from queo_data_platform.config.settings import settings

settings.bronze_dir
settings.silver_dir
settings.gold_dir
```

em vez de repetir:

```python
Path("data/lakehouse/03_gold")
```

em vários arquivos.

---

# 10. Criar a estrutura de dados

Executar:

```powershell
New-Item -ItemType Directory -Force -Path `
    data\raw\inbox, `
    data\raw\archive, `
    data\raw\quarantine, `
    data\lakehouse\00_control, `
    data\lakehouse\01_bronze, `
    data\lakehouse\02_silver, `
    data\lakehouse\03_gold
```

Resultado:

```text
data/
├── raw/
│   ├── inbox/
│   ├── archive/
│   └── quarantine/
│
└── lakehouse/
    ├── 00_control/
    ├── 01_bronze/
    ├── 02_silver/
    └── 03_gold/
```

## Para que?

### `inbox`

Receber arquivos novos.

### `archive`

Guardar arquivos processados com sucesso.

### `quarantine`

Isolar arquivos inválidos.

### `00_control`

Guardar informações de controle de processamento.

### `01_bronze`

Armazenar dados ingeridos.

### `02_silver`

Armazenar dados tratados.

### `03_gold`

Armazenar produtos de dados prontos para consumo.

---

# 11. Configurar o `.gitignore`

Adicionar:

```gitignore
.venv/
.pytest_cache/
__pycache__/
*.pyc

data/raw/inbox/*
data/raw/archive/*
data/raw/quarantine/*

data/lakehouse/*
```

## Para que?

Evitar versionar:

```text
ambiente virtual
cache Python
dados locais
Delta Tables
arquivos processados
```

O Git deve guardar principalmente código, testes e configuração.

---

# 12. Testar a importação do package

Foi executado:

```powershell
uv run python -c "from queo_data_platform.config.settings import settings; print(settings.project_root); print(settings.bronze_dir); print(settings.gold_dir)"
```

O resultado foi:

```text
ModuleNotFoundError: No module named 'queo_data_platform'
```

## O que aconteceu?

O código existia em:

```text
src/queo_data_platform/
```

mas o próprio projeto ainda não estava instalado no ambiente Python.

O problema não era o `settings.py`.

---

# 13. Configurar o build do package

Adicionar ao `pyproject.toml`:

```toml
[build-system]
requires = ["uv_build>=0.12.3,<0.13"]
build-backend = "uv_build"
```

O arquivo completo passa a ser:

```toml
[project]
name = "queo-data-platform"
version = "0.1.0"
description = "Enterprise data platform for ingestion, Lakehouse processing, APIs, analytics, and MCP integration."
readme = "README.md"
requires-python = ">=3.14"
dependencies = []

[dependency-groups]
dev = [
    "pyright>=1.1.411",
    "pytest>=9.1.1",
    "ruff>=0.16.3",
]

[build-system]
requires = ["uv_build>=0.12.3,<0.13"]
build-backend = "uv_build"
```

## O que?

O `build-system` informa ao Python/`uv` como construir e instalar o próprio projeto.

```toml
build-backend = "uv_build"
```

define que o backend de build será o do `uv`.

## Para que?

Fazer com que:

```text
src/queo_data_platform/
```

seja reconhecido e instalado como package.

Assim podemos importar normalmente:

```python
import queo_data_platform
```

sem `sys.path.insert()` ou `PYTHONPATH` manual.

---

# 14. Sincronizar novamente o ambiente

Executar:

```powershell
uv sync
```

## Para que?

Depois da configuração do build, o `uv` pode:

```text
ler o pyproject
↓
construir o projeto
↓
instalar queo-data-platform no .venv
```

Depois, testar:

```powershell
uv run python -c "import queo_data_platform; print(queo_data_platform)"
```

E novamente:

```powershell
uv run python -c "from queo_data_platform.config.settings import settings; print(settings.project_root); print(settings.bronze_dir); print(settings.gold_dir)"
```

Quando esse comando funcionar, significa que a fundação do package e a configuração dos caminhos estão corretas.



---
# 15. Tornar o diretório de dados configurável

O `settings.py` inicialmente utilizava sempre:

```python
data_dir = project_root / "data"
```

Isso funcionava localmente, mas prendia o armazenamento dos dados à estrutura física do repositório.

Foi adicionada a possibilidade de configurar o diretório através da variável de ambiente:

```text
QUEO_DATA_DIR
```

O carregamento passou a seguir esta lógica:

```python
data_dir = Path(
    os.getenv(
        "QUEO_DATA_DIR",
        str(project_root / "data"),
    )
).resolve()
```

## O que?

A configuração procura primeiro:

```text
QUEO_DATA_DIR
```

Se a variável existir, utiliza o caminho informado.

Se ela não existir, mantém o comportamento local:

```text
<project_root>/data
```

## Para que?

Permitir que o mesmo código funcione em diferentes ambientes sem alterar o código-fonte.

Exemplo local:

```text
queo-data-platform/
└── data/
```

Exemplo em servidor:

```text
D:\queo\data
```

ou:

```text
/mnt/queo-data
```

Assim:

```text
código
  ↓
Settings
  ↓
QUEO_DATA_DIR
  ↓
local / servidor / container
```

---

# 16. Criar o primeiro contrato de dados

Foi criado:

```text
src/
└── queo_data_platform/
    └── contracts/
        └── tracker.py
```

## O que?

Esse módulo centraliza informações compartilhadas sobre o formato dos dados de rastreadores.

A separação principal é:

```text
dados fornecidos pela fonte

+

metadados gerados pela plataforma
```

O contrato define:

```python
BRONZE_TABLE_NAME = "tracker_logs"
```

e as colunas técnicas adicionadas pela plataforma:

```python
BRONZE_METADATA_COLUMNS = (
    "source_file",
    "source_file_hash",
    "source_row_number",
    "row_id",
    "batch_id",
    "ingested_at",
    "ingestion_date",
)
```

## Para que?

Evitar que Bronze, Silver e outros módulos mantenham cópias diferentes da mesma definição.

Em vez de:

```text
Bronze
→ define colunas

Silver
→ redefine as mesmas colunas
```

temos:

```text
contracts/tracker.py
        │
        ├── Bronze
        ├── Silver
        └── outros consumidores
```

O contrato informa **como os dados devem se apresentar**, mas não contém regras de leitura, persistência ou transformação.

---

# 17. Criar os primeiros testes da configuração

Foi criado:

```text
tests/
└── unit/
    └── test_settings.py
```

## O que?

Os testes verificam dois comportamentos principais.

### Configuração padrão

Sem `QUEO_DATA_DIR`:

```text
data_dir
=
<project_root>/data
```

### Configuração externa

Com:

```text
QUEO_DATA_DIR=<caminho>
```

os demais diretórios devem ser derivados desse local:

```text
QUEO_DATA_DIR
   │
   ├── raw
   │
   └── lakehouse
       ├── 00_control
       ├── 01_bronze
       ├── 02_silver
       └── 03_gold
```

## Para que?

Além de testar o `Settings`, esse teste valida a própria fundação do package:

```text
pytest
  ↓
importa queo_data_platform
  ↓
importa config
  ↓
executa load_settings()
```

Assim confirmamos que o layout `src/` e o sistema de build estão funcionando corretamente.

---

# 18. Criar descoberta de arquivos da Bronze

Foi criado:

```text
src/
└── queo_data_platform/
    └── bronze/
        └── files.py
```

A primeira responsabilidade adicionada foi:

```python
discover_csv_files(...)
```

## O que?

A função procura arquivos diretamente dentro do diretório de entrada.

São considerados apenas:

```text
*.csv
*.CSV
```

Diretórios internos não são percorridos.

Exemplo:

```text
inbox/
├── b.csv
├── a.csv
├── ignore.txt
└── subdir/
    └── hidden.csv
```

Resultado:

```text
a.csv
b.csv
```

## Para que?

Separar a descoberta de arquivos da lógica de ingestão.

A função também ordena o resultado por nome:

```text
filesystem
   ↓
discover_csv_files()
   ↓
ordem determinística
```

Isso facilita testes, logs e previsibilidade do processamento.

---

# 19. Adicionar identificação do arquivo por SHA-256

No mesmo módulo:

```text
bronze/files.py
```

foi adicionada:

```python
calculate_file_sha256(...)
```

## O que?

A função calcula um SHA-256 sobre os bytes do arquivo.

O arquivo é lido em blocos:

```python
while chunk := file.read(1024 * 1024):
    digest.update(chunk)
```

em vez de ser carregado inteiro na memória.

## Para que?

Identificar o **conteúdo** do arquivo, e não apenas seu nome.

Exemplo:

```text
arquivo_A.csv
conteúdo X

arquivo_B.csv
conteúdo X
```

Embora os nomes sejam diferentes:

```text
SHA-256(A) == SHA-256(B)
```

Isso será utilizado posteriormente para controle de ingestão e idempotência.

Foram adicionados testes para:

```text
✓ somente CSVs são descobertos
✓ .CSV também é aceito
✓ subdiretórios são ignorados
✓ diretório inexistente retorna lista vazia
✓ hash é determinístico
✓ conteúdos diferentes geram hashes diferentes
```

---

# 20. Adicionar validação estrutural da entrada Bronze

Foi adicionada a primeira dependência de runtime:

```powershell
uv add pandas
```

E criado:

```text
src/
└── queo_data_platform/
    └── bronze/
        └── validation.py
```

## O que?

Esse módulo valida se um arquivo pode entrar com segurança na Bronze.

Foi criada:

```python
FileValidationResult
```

para representar o resultado da validação.

O resultado contém informações como:

```text
source_path
is_valid
dataframe
row_count
detected_encoding
missing_columns
reserved_columns
duplicated_columns
error_message
```

---

## Leitura do CSV

Foi criada:

```python
read_csv_with_supported_encoding(...)
```

A estratégia é:

```text
UTF-8
 ↓ falhou por encoding
Latin-1
```

O Pandas é chamado com:

```python
dtype=str
keep_default_na=False
```

## Para que?

A Bronze deve evitar inferência precoce de tipos.

Neste estágio:

```text
"00123"
```

deve permanecer dado bruto, e não ser automaticamente transformado em:

```text
123
```

A tipagem pertence às camadas posteriores.

---

# 21. Normalizar e validar nomes de colunas

Foi criada:

```python
normalize_column_names(...)
```

que remove espaços externos dos nomes.

Exemplo:

```text
" LAT "
```

vira:

```text
"LAT"
```

Também foi adicionada detecção de colisões.

Exemplo de entrada:

```text
LAT
" LAT "
```

Depois da normalização:

```text
LAT
LAT
```

Esse arquivo deve ser rejeitado.

## Para que?

Evitar que duas colunas diferentes da origem se transformem silenciosamente no mesmo nome depois da normalização.

---

# 22. Validar colunas obrigatórias e reservadas

A validação verifica dois grupos.

## Colunas obrigatórias da fonte

O arquivo precisa conter o conjunto mínimo esperado pelo contrato.

Colunas adicionais continuam sendo permitidas.

## Colunas reservadas

A fonte não pode enviar campos como:

```text
source_file
source_file_hash
source_row_number
row_id
batch_id
ingested_at
ingestion_date
```

## Para que?

Essas colunas representam metadados internos da plataforma.

Permitir que a origem as fornecesse tornaria possível sobrescrever informações de lineage.

O fluxo passou a ser:

```text
CSV
 ↓
leitura
 ↓
normalização
 ↓
duplicidade?
 ↓
colunas obrigatórias?
 ↓
metadados reservados?
 ↓
válido / inválido
```

---

# 23. Corrigir o contrato real do tracker

Durante a migração foi identificado que a primeira versão de:

```python
RAW_TRACKER_COLUMNS
```

não correspondia ao schema realmente utilizado pelo projeto experimental.

O contrato foi corrigido e renomeado para:

```python
RAW_TRACKER_REQUIRED_COLUMNS
```

## O que?

O novo nome deixa claro que a lista representa:

```text
colunas mínimas obrigatórias
```

e não:

```text
todas as únicas colunas permitidas
```

O schema passou a incluir os campos reais utilizados pela origem, como:

```text
DATA_SERVIDOR
TM_STAMP
TIPO_LOG
MESS_TYPE
REPT_TYPE
PRT_VER
S/N ou IMEI
TERM_STATUS
BAT_VOLT
LOC_STATUS
LAT
LONT
SPEED
DIR
...
SER_COUNT
...
TEMP_4
```

## Para que?

Manter:

```text
contrato
=
estrutura real da fonte
```

antes de outras partes da plataforma começarem a depender dele.

A correção também reforçou a regra:

```text
campos obrigatórios
+
campos extras permitidos
```

---

# 24. Criar a camada de lineage da Bronze

Foi criado:

```text
src/
└── queo_data_platform/
    └── bronze/
        └── lineage.py
```

## O que?

Esse módulo adiciona identidade e rastreabilidade aos registros ingeridos.

Foram criadas as funções:

```python
generate_batch_id(...)
normalize_ingestion_timestamp(...)
calculate_row_id(...)
add_lineage_metadata(...)
```

---

## `batch_id`

Cada execução recebe:

```python
str(uuid4())
```

Assim:

```text
execução A
→ batch A

execução B
→ batch B
```

Mesmo que processem o mesmo arquivo.

---

## `row_id`

A identidade da linha é calculada a partir de:

```text
source_file_hash
+
source_row_number
```

Fluxo:

```text
hash do arquivo
        +
posição da linha
        ↓
     SHA-256
        ↓
      row_id
```

## Para que?

Garantir que a mesma linha da mesma fonte produza sempre a mesma identidade.

Exemplo:

```text
batch A
row_id XYZ

batch B
row_id XYZ
```

O `batch_id` mudou porque é outra execução.

O `row_id` permaneceu porque é o mesmo registro de origem.

Essa diferença será usada para idempotência da persistência.

---

# 25. Adicionar os metadados técnicos

`add_lineage_metadata()` adiciona:

```text
source_file
source_file_hash
source_row_number
row_id
batch_id
ingested_at
ingestion_date
```

ao DataFrame validado.

O fluxo passa a ser:

```text
DataFrame validado
        ↓
add_lineage_metadata()
        ↓
DataFrame Bronze
```

O DataFrame original não é modificado diretamente.

A função cria uma cópia antes de adicionar os metadados.

## Para que?

Evitar efeitos colaterais e manter a transformação explícita.

---

# 26. Normalizar timestamps de ingestão em UTC

Foi criada:

```python
normalize_ingestion_timestamp(...)
```

A regra é:

```text
timestamp ausente
→ agora em UTC

timestamp sem timezone
→ interpretar como UTC

timestamp com timezone
→ converter para UTC
```

Durante os testes, o Ruff recomendou utilizar:

```python
datetime.UTC
```

em vez de:

```python
timezone.utc
```

O código foi ajustado para utilizar:

```python
from datetime import UTC, datetime
```

Também foi mantido um teste proposital para `datetime` sem timezone:

```python
datetime(  # noqa: DTZ001
    ...
)
```

## Para que?

Esse caso existe especificamente para validar o comportamento de normalização de timestamps *naive*.

A exceção do Ruff fica restrita apenas ao teste que precisa representar esse cenário.

---

# 27. Ajustar geração do hash do `row_id`

O Ruff também identificou:

```python
.encode("utf-8")
```

como argumento desnecessário.

Foi simplificado para:

```python
.encode()
```

porque UTF-8 já é o encoding padrão dessa operação.

O comportamento do algoritmo não muda.

---

# 28. Adicionar persistência Delta

Foram adicionadas:

```powershell
uv add deltalake pyarrow
```

## O que?

`deltalake` passa a fornecer:

```text
Delta Table
MERGE
transaction log
escrita
```

`pyarrow` passa a ser utilizado como representação colunar na fronteira de persistência.

O fluxo é:

```text
Pandas DataFrame
      ↓
PyArrow Table
      ↓
Delta Lake
```

---

# 29. Criar infraestrutura Delta compartilhada

Foi criada:

```text
src/
└── queo_data_platform/
    └── infrastructure/
        └── delta/
            ├── __init__.py
            └── table.py
```

O módulo contém operações básicas como:

```python
is_delta_table(...)
open_delta_table(...)
```

## Para que?

Evitar duplicar operações genéricas de Delta em:

```text
Bronze
Silver
Gold
Query
```

A dependência passa a seguir:

```text
Bronze ──┐
Silver ──┼──→ infrastructure/delta
Gold   ──┘
```

Esse módulo deve conter apenas detalhes técnicos compartilhados.

Regras específicas de Bronze continuam dentro de:

```text
bronze/
```

---

# 30. Criar o writer da Bronze

Foi criado:

```text
src/
└── queo_data_platform/
    └── bronze/
        └── writer.py
```

## O que?

Esse módulo recebe um DataFrame que já passou por:

```text
validation
   ↓
lineage
```

e persiste os registros em:

```text
01_bronze/tracker_logs
```

O writer não conhece:

```text
inbox
archive
quarantine
leitura CSV
FileValidationResult
```

## Para que?

Manter a persistência coesa e desacoplada das outras responsabilidades da ingestão.

---

# 31. Criar a primeira Delta Table Bronze

Quando:

```text
tracker_logs
```

ainda não existe, o fluxo é:

```text
DataFrame
 ↓
PyArrow
 ↓
write_deltalake()
 ↓
CREATE
```

A tabela é particionada por:

```text
ingestion_date
```

Estrutura esperada:

```text
data/
└── lakehouse/
    └── 01_bronze/
        └── tracker_logs/
            ├── _delta_log/
            └── ingestion_date=...
```

---

# 32. Implementar MERGE insert-only

Quando a Delta Table já existe, a estratégia muda para:

```text
MERGE
```

usando:

```text
target.row_id = source.row_id
```

O comportamento é:

```text
row_id encontrado
→ não alterar

row_id não encontrado
→ inserir
```

## Para que?

Garantir idempotência.

Exemplo:

```text
execução 1
row_id ABC
→ INSERT

execução 2
row_id ABC
→ já existe
→ IGNORE
```

Uma nova tentativa não duplica o registro.

---

# 33. Alinhar schema antes do MERGE

Foi criada:

```python
align_dataframe_to_target_schema(...)
```

## O que?

Antes de fazer o MERGE, a fonte é comparada ao schema já existente.

Se uma coluna antiga estiver ausente:

```text
target possui coluna
source não possui
```

ela é adicionada ao novo DataFrame com:

```text
NULL
```

Se a nova fonte possuir uma coluna adicional, ela é mantida.

Exemplo:

```text
target:
A B C

novo arquivo:
A B C D

resultado:
A B C D
```

## Para que?

Permitir evolução controlada do schema sem quebrar arquivos que não possuam exatamente o mesmo conjunto de colunas extras.

---

# 34. Criar `BronzeWriteResult`

Foi criada uma `dataclass` para representar o resultado da persistência:

```python
BronzeWriteResult
```

Ela contém:

```text
table_path
row_count
inserted_row_count
duplicate_row_count
operation
metrics
```

## Para que?

O restante da aplicação não precisa interpretar diretamente as métricas internas retornadas pelo Delta Lake.

Exemplo:

```text
100 linhas recebidas
 ↓
90 novas
10 duplicadas
```

Resultado:

```text
row_count = 100
inserted_row_count = 90
duplicate_row_count = 10
```

Esses valores serão utilizados posteriormente pelo controle operacional da ingestão.

---

# 35. Criar testes de persistência Delta

Foi criado:

```text
tests/
└── unit/
    └── test_bronze_writer.py
```

Os testes cobrem:

```text
criação da primeira Delta Table
DataFrame vazio
alinhamento de schema
reprocessamento das mesmas linhas
MERGE somente de linhas novas
evolução de schema
```

Diferentemente dos primeiros testes da Bronze, esses testes exercitam uma Delta Table real em diretórios temporários.

## Para que?

Validar não apenas a lógica Python, mas o comportamento efetivo da camada de persistência.

---

# 36. Corrigir organização dos imports do writer

Ao executar:

```powershell
uv run ruff check .
```

foi identificado:

```text
I001 Import block is un-sorted or un-formatted
```

em:

```text
src/queo_data_platform/bronze/writer.py
```

A correção indicada é:

```powershell
uv run ruff check . --fix
```

Depois:

```powershell
uv run ruff format .
uv run ruff check .
uv run pyright
uv run pytest
```

## Estado atual

O desenvolvimento está atualmente neste ponto:

```text
files.py
  ↓
validation.py
  ↓
lineage.py
  ↓
writer.py
  ↓
Delta tracker_logs
```

A persistência Delta foi implementada, mas a última etapa registrada é a correção/validação final de qualidade do `writer.py`.

O próximo componente planejado é:

```text
00_control/ingestion_files
```

que registrará o histórico operacional dos arquivos processados.

Depois dele será possível criar:

```text
bronze/service.py
```

para coordenar o fluxo completo:

```text
discover
 ↓
hash
 ↓
control
 ↓
validate
 ↓
lineage
 ↓
write
 ↓
archive / quarantine
 ↓
registrar resultado
```


