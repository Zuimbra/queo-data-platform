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
dtype = str
keep_default_na = False
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
---

# 37. Criar a tabela de controle da ingestão

Foi criado:

```text
src/
└── queo_data_platform/
    └── bronze/
        └── control.py
```

A tabela lógica utilizada para controle recebeu o nome:

```python
CONTROL_TABLE_NAME = "ingestion_files"
```

e é armazenada dentro de:

```text
data/
└── lakehouse/
    └── 00_control/
        └── ingestion_files/
```

## O que?

A tabela de controle registra o histórico operacional dos arquivos processados pela Bronze.

Até esse momento já existiam mecanismos para:

```text
descobrir arquivos
calcular hash
validar CSV
adicionar lineage
escrever tracker_logs
```

Porém ainda não havia um registro persistente que respondesse perguntas como:

```text
esse arquivo já foi processado?
quando ele começou a ser processado?
terminou com sucesso?
falhou?
quantas linhas foram inseridas?
quantas foram consideradas duplicadas?
```

A control table passa a exercer essa responsabilidade.

## Para que?

Separar dois tipos de informação:

```text
tracker_logs
→ dados de negócio ingeridos

ingestion_files
→ dados operacionais sobre a ingestão
```

Assim, informações de controle não precisam ser armazenadas dentro dos próprios registros de telemetria.

---

# 38. Criar `IngestionControlEvent`

Foi criada a dataclass:

```python
@dataclass(frozen=True)
class IngestionControlEvent:
```

Ela representa um evento do histórico de processamento.

Os principais campos são:

```text
control_event_id
batch_id
source_file
source_file_hash
status
stage
started_at
finished_at
row_count
inserted_row_count
duplicate_row_count
status_reason
error_message
recorded_at
```

## O que?

Cada mudança relevante no processamento de um arquivo gera um novo evento.

Exemplo:

```text
tracker.csv
    ↓
PROCESSING
    ↓
SUCCESS
```

não é representado atualizando uma mesma linha.

São gravados dois registros:

```text
evento 1
status = PROCESSING

evento 2
status = SUCCESS
```

## Para que?

Preservar o histórico completo da ingestão.

Uma estratégia baseada em UPDATE produziria apenas:

```text
tracker.csv | SUCCESS
```

e perderia a informação de que o arquivo anteriormente esteve em processamento.

Com eventos append-only:

```text
tracker.csv | PROCESSING
tracker.csv | SUCCESS
```

o histórico permanece disponível.

---

# 39. Definir os estados da ingestão

Foram definidos quatro estados:

```python
ControlStatus = Literal[
    "PROCESSING",
    "SUCCESS",
    "FAILED",
    "SKIPPED",
]
```

## `PROCESSING`

Indica que uma tentativa de ingestão foi iniciada.

```text
arquivo descoberto
    ↓
hash calculado
    ↓
PROCESSING
```

## `SUCCESS`

Indica que o arquivo concluiu a ingestão.

Pode conter:

```text
row_count
inserted_row_count
duplicate_row_count
```

## `FAILED`

Indica que a tentativa não foi concluída.

O evento pode registrar:

```text
status_reason
error_message
```

Exemplos de motivos posteriormente utilizados:

```text
FILE_HASH_ERROR
VALIDATION_FAILED
BRONZE_WRITE_FAILED
```

## `SKIPPED`

Indica que o arquivo não precisou ser novamente ingerido.

O principal caso é:

```text
SHA-256
   ↓
já existe SUCCESS para esse conteúdo
   ↓
SKIPPED
```

---

# 40. Tornar a control table append-only

Foi criada:

```python
append_control_event(...)
```

A estratégia de escrita é:

```text
tabela ainda não existe
        ↓
mode="overwrite"
        ↓
criação inicial

tabela já existe
        ↓
mode="append"
        ↓
novo evento
```

Não existe atualização dos eventos antigos.

O comportamento esperado é:

```text
tentativa 1
PROCESSING
FAILED

tentativa 2
PROCESSING
SUCCESS

tentativa 3
SKIPPED
```

## Para que?

Permitir auditoria do ciclo de vida dos arquivos.

Também evita transformar a tabela de controle em uma estrutura cujo significado dependa de updates sucessivos sobre um único registro.

---

# 41. Criar schema PyArrow explícito para o controle

A transformação:

```python
control_event_to_arrow_table(...)
```

utiliza um schema PyArrow explícito.

Exemplo:

```text
control_event_id      string
batch_id              string
source_file           string
source_file_hash      string nullable
status                string
started_at            timestamp UTC
finished_at           timestamp UTC nullable
row_count             int64 nullable
inserted_row_count    int64 nullable
duplicate_row_count   int64 nullable
status_reason         string nullable
error_message         string nullable
recorded_at           timestamp UTC
```

## O que?

Campos como:

```text
finished_at
row_count
error_message
```

podem inicialmente possuir:

```python
None
```

Por exemplo, um evento:

```text
PROCESSING
```

normalmente ainda não possui `finished_at`.

Sem schema explícito, uma coluna contendo somente valores nulos poderia ser inferida de forma inadequada.

## Para que?

Garantir que o tipo da coluna seja conhecido mesmo quando o primeiro registro armazenado contiver `NULL`.

Assim:

```text
NULL
```

continua sendo um valor possível de:

```text
string
timestamp
int64
```

e não passa a definir o tipo da coluna.

---

# 42. Detectar arquivos anteriormente processados com sucesso

Foi criada:

```python
load_successful_file_hashes(...)
```

A função consulta apenas:

```text
source_file_hash
status
```

da tabela:

```text
00_control/ingestion_files
```

e retorna os hashes associados a:

```text
status == SUCCESS
```

Também foi criada:

```python
should_skip_file_hash(...)
```

## O que?

A decisão de reprocessamento passou a funcionar assim:

```text
novo arquivo
    ↓
SHA-256
    ↓
buscar hashes com SUCCESS
    ↓
hash encontrado?
   / \
 sim  não
 ↓     ↓
SKIP  processar
```

## Para que?

Evitar depender do nome físico do arquivo para definir identidade.

Dois arquivos:

```text
tracker_a.csv
tracker_b.csv
```

podem possuir exatamente o mesmo conteúdo.

Nesse caso:

```text
SHA256(tracker_a.csv)
==
SHA256(tracker_b.csv)
```

e o segundo não precisa ser ingerido novamente depois que o primeiro já concluiu com `SUCCESS`.

---

# 43. Criar testes da tabela de controle

Foi criado:

```text
tests/
└── unit/
    └── test_bronze_control.py
```

Os testes cobrem comportamentos como:

```text
PROCESSING não possui finished_at
estado final recebe finished_at
status inválido é rejeitado
row_count negativo é rejeitado
schema Arrow mantém tipos nullable
control table é append-only
somente hashes com SUCCESS são carregados
hash conhecido deve ser ignorado
hash desconhecido deve ser processado
```

Um teste importante grava:

```text
PROCESSING
SUCCESS
```

na mesma Delta Table e verifica que existem:

```text
2 registros
```

em vez de apenas o estado final.

## Para que?

Validar que o controle operacional funciona como histórico e não como uma tabela mutável de estado atual.

---

# 44. Corrigir a tipagem do alinhamento de schema

Durante a validação com:

```powershell
uv run pyright
```

foi encontrado um problema em:

```python
align_dataframe_to_target_schema(...)
```

A seleção:

```python
aligned[ordered_columns]
```

era entendida pelos stubs do Pandas como podendo resultar em:

```text
DataFrame
ou
Series
```

embora semanticamente fosse utilizada uma lista de colunas.

A implementação foi alterada para:

```python
return aligned.reindex(
    columns=ordered_columns,
)
```

## Para que?

Expressar explicitamente que a operação está reorganizando as colunas de um DataFrame.

Depois da correção:

```text
pyright
0 errors
0 warnings
0 informations
```

A mudança não altera o comportamento da persistência.

Ela torna o contrato de tipos da função mais explícito.

---

# 45. Adicionar movimentação de arquivos Raw

O módulo:

```text
bronze/files.py
```

recebeu:

```python
move_file(...)
```

O fluxo passa a poder mover arquivos de:

```text
raw/inbox
```

para:

```text
raw/archive
```

ou:

```text
raw/quarantine
```

## Colisão de nomes

Caso já exista:

```text
archive/tracker.csv
```

um novo arquivo não deve sobrescrever o anterior silenciosamente.

Quando um `conflict_suffix` é informado, o nome pode passar a:

```text
tracker__<batch_id>.csv
```

## Para que?

Preservar os arquivos físicos recebidos e evitar perda de dados causada por colisão de nomes.

---

# 46. Criar `BronzeLoadResult`

Foi criada:

```python
@dataclass(frozen=True)
class BronzeLoadResult:
```

com campos:

```text
discovered_file_count

successful_files
skipped_files
failed_files

batch_ids

inserted_row_count
duplicate_row_count
```

Também foi criada a propriedade:

```python
@property
def has_new_data(self) -> bool:
    return self.inserted_row_count > 0
```

## O que?

A execução da Bronze deixa de comunicar seu resultado apenas por efeitos colaterais.

Agora ela devolve explicitamente informações sobre o processamento.

Exemplo:

```text
2 arquivos descobertos
2 processados
150 linhas recebidas

145 novas
5 duplicadas
```

pode resultar em:

```text
discovered_file_count = 2
inserted_row_count = 145
duplicate_row_count = 5
has_new_data = True
```

## Para que?

Criar um contrato entre:

```text
Bronze
  ↓
Pipeline
  ↓
Silver
```

A futura orquestração poderá decidir:

```python
if not bronze_result.has_new_data:
    # Silver não precisa ser executada
```

sem precisar consultar diretamente a Delta Table.

---

# 47. Definir quais `batch_ids` devem ser propagados

`BronzeLoadResult.batch_ids` não contém simplesmente todos os batches executados.

São adicionados apenas batches que realmente inseriram novas linhas:

```python
if write_result.inserted_row_count > 0:
    inserted_batch_ids.append(batch_id)
```

## O que?

Considere:

```text
batch A
10 linhas recebidas
8 inseridas
2 duplicadas
```

O batch possui linhas novas na Bronze:

```text
batch_ids = [A]
```

Agora:

```text
batch B
10 linhas recebidas
0 inseridas
10 duplicadas
```

Nenhuma linha com:

```text
batch_id = B
```

foi efetivamente inserida.

Portanto:

```text
batch_ids
```

não deve conter `B`.

## Para que?

Evitar que a Silver seja solicitada a processar um batch que não possui nenhuma linha nova na Bronze.

---

# 48. Criar o serviço de ingestão Bronze

Foi criado:

```text
src/
└── queo_data_platform/
    └── bronze/
        └── service.py
```

Sua principal função é:

```python
load_bronze_data(...)
```

Ela recebe explicitamente:

```text
inbox_dir
archive_dir
quarantine_dir
bronze_dir
control_dir
```

## O que?

O serviço passa a coordenar os componentes construídos anteriormente.

O fluxo completo torna-se:

```text
inbox
  ↓
discover_csv_files()
  ↓
calculate_file_sha256()
  ↓
consultar control table
  ↓
arquivo já possui SUCCESS?
  ├── sim
  │    ↓
  │  SKIPPED
  │    ↓
  │  archive
  │
  └── não
       ↓
    PROCESSING
       ↓
 validate_input_file()
       ↓
    válido?
   /     \
 não      sim
 ↓         ↓
FAILED   lineage
 ↓         ↓
quarantine write Bronze
             ↓
          SUCCESS
             ↓
           archive
```

## Para que?

Centralizar **orquestração**, sem trazer novamente todas as responsabilidades para um módulo monolítico.

O serviço chama:

```text
files.py
control.py
validation.py
lineage.py
writer.py
```

mas cada módulo continua responsável pela sua própria lógica.

---

# 49. Tratamento de falhas durante a ingestão

O serviço diferencia falhas por estágio.

## Falha no hash

```text
arquivo
 ↓
SHA-256 falhou
 ↓
FAILED
status_reason = FILE_HASH_ERROR
 ↓
quarantine
```

## Falha de validação

```text
arquivo
 ↓
PROCESSING
 ↓
validation
 ↓
inválido
 ↓
FAILED
status_reason = VALIDATION_FAILED
 ↓
quarantine
```

## Falha de escrita

```text
arquivo válido
 ↓
lineage
 ↓
Delta
 ↓
erro
 ↓
FAILED
status_reason = BRONZE_WRITE_FAILED
 ↓
quarantine
```

## Para que?

Permitir identificar em qual estágio a ingestão falhou.

Isso é diferente de registrar apenas:

```text
FAILED
```

sem contexto.

---

# 50. Arquivar arquivos processados ou ignorados

O comportamento físico dos arquivos passa a ser:

```text
SUCCESS
   ↓
archive

SKIPPED
   ↓
archive

FAILED
   ↓
quarantine
```

## Por que `SKIPPED` vai para archive?

Porque o arquivo não é inválido.

Ele apenas contém dados que já foram processados anteriormente.

Portanto:

```text
quarantine
```

não representa corretamente sua situação.

O arquivo já foi analisado e pode sair do `inbox`.

---

# 51. Criar testes de integração da Bronze

Foi criado:

```text
tests/
└── integration/
    └── test_bronze_service.py
```

Esses testes deixam de verificar apenas funções isoladas.

Eles executam um fluxo vertical utilizando:

```text
CSV real
 ↓
discovery
 ↓
hash
 ↓
control Delta
 ↓
validation
 ↓
lineage
 ↓
tracker_logs Delta
 ↓
archive / quarantine
```

Entre os cenários cobertos estão:

```text
arquivo válido é ingerido e arquivado
arquivo inválido vai para quarantine
conteúdo previamente processado recebe SKIPPED
```

## Para que?

Validar que módulos que individualmente já possuem testes também funcionam corretamente quando conectados.

Esse é o primeiro teste da Bronze que exercita praticamente toda a cadeia de ingestão.

---

# 52. Corrigir suposição de ordem física da Delta Table

Os primeiros testes de integração esperavam diretamente:

```python
control_dataframe["status"].tolist()
==
[
    "PROCESSING",
    "SUCCESS",
]
```

Porém a leitura de uma Delta Table não garante que as linhas sejam retornadas na mesma ordem física das escritas.

Na prática foi observado:

```text
SUCCESS
PROCESSING
```

mesmo que os eventos tivessem sido persistidos na ordem lógica correta.

## Correção

Foi criada uma leitura cronológica:

```python
def read_control_history(
    control_dir: Path,
) -> pd.DataFrame:
```

que ordena os eventos por:

```text
recorded_at
```

antes das asserções.

O teste passa então a verificar:

```text
ordem temporal
```

e não:

```text
ordem física dos arquivos Parquet
```

## Para que?

Evitar que os testes dependam de uma propriedade que Delta Lake não garante.

---

# 53. Validar a primeira versão integrada da Bronze

Após as correções foram executados:

```powershell
uv run ruff format .
uv run ruff check .
uv run pyright
uv run pytest
```

A execução registrada naquele momento resultou em:

```text
ruff
→ All checks passed!

pyright
→ 0 errors
→ 0 warnings
→ 0 informations

pytest
→ 44 testes coletados
→ 41 passaram inicialmente
→ 3 falharam apenas pela suposição de ordenação física
```

Depois da correção da leitura cronológica, os testes de integração deixaram de depender dessa ordenação física.

---

# 54. Expandir `Settings` para a estrutura Raw

O `Settings` foi posteriormente ampliado para representar explicitamente:

```text
raw_dir
├── inbox_dir
├── archive_dir
└── quarantine_dir
```

A configuração passa a incluir:

```python
inbox_dir: Path
archive_dir: Path
quarantine_dir: Path
```

e esses caminhos são derivados de:

```python
raw_dir = data_dir / "raw"
```

resultando em:

```text
QUEO_DATA_DIR
    │
    ├── raw
    │   ├── inbox
    │   ├── archive
    │   └── quarantine
    │
    └── lakehouse
        ├── 00_control
        ├── 01_bronze
        ├── 02_silver
        └── 03_gold
```

## Para que?

Evitar que módulos da aplicação reconstruam manualmente caminhos como:

```python
settings.raw_dir / "inbox"
```

Os paths físicos relevantes passam a possuir uma única fonte de definição.

---

# 55. Atualizar os testes de `Settings`

O teste:

```text
tests/unit/test_settings.py
```

passou a verificar também:

```text
inbox_dir
archive_dir
quarantine_dir
```

Além dos diretórios já existentes:

```text
control_dir
bronze_dir
silver_dir
gold_dir
```

Foi executado:

```powershell
uv run pytest tests/unit/test_settings.py
```

com resultado:

```text
2 passed
```

Também foram executados:

```text
ruff       → OK
pyright    → OK
```

## Para que?

Confirmar que toda a árvore de diretórios continua derivada corretamente de:

```text
QUEO_DATA_DIR
```

e não apenas os diretórios do Lakehouse.

---

# 56. Criar uma interface de alto nível para a Bronze

Além de:

```python
load_bronze_data(...)
```

foi criada uma interface baseada em configuração:

```python
load_bronze(
    settings: Settings,
) -> BronzeLoadResult:
```

Internamente ela delega para:

```python
load_bronze_data(
    inbox_dir=settings.inbox_dir,
    archive_dir=settings.archive_dir,
    quarantine_dir=settings.quarantine_dir,
    bronze_dir=settings.bronze_dir,
    control_dir=settings.control_dir,
)
```

## O que?

Passam a existir dois níveis de chamada.

### Interface explícita

```python
load_bronze_data(...)
```

Recebe os caminhos individualmente.

É especialmente útil para:

```text
testes
execuções isoladas
injeção de diretórios temporários
```

### Interface da plataforma

```python
load_bronze(settings)
```

Recebe a configuração completa.

É a interface que poderá ser utilizada pela futura orquestração.

## Para que?

Evitar que o pipeline precise conhecer todos os detalhes de localização física usados pela Bronze.

Em vez de:

```python
load_bronze_data(
    inbox_dir=settings.inbox_dir,
    archive_dir=settings.archive_dir,
    quarantine_dir=settings.quarantine_dir,
    bronze_dir=settings.bronze_dir,
    control_dir=settings.control_dir,
)
```

o pipeline poderá utilizar:

```python
load_bronze(settings)
```

---

# 57. Validar a Bronze através de `Settings`

Foi adicionado um cenário de integração que executa:

```text
QUEO_DATA_DIR temporário
       ↓
load_settings()
       ↓
Settings
       ↓
load_bronze(settings)
       ↓
ingestão real
```

O teste verifica que a execução produz:

```text
archive/tracker.csv
01_bronze/tracker_logs
00_control/ingestion_files
```

e retorna:

```text
has_new_data = True
inserted_row_count = 1
```

Após a inclusão dos cenários finais, a execução isolada de:

```powershell
uv run pytest tests/integration/test_bronze_service.py
```

registrou:

```text
6 testes coletados
6 testes aprovados
```

Também foi registrado:

```text
pyright
0 errors
0 warnings
0 informations
```

---

# 58. Estado da camada Bronze após a integração

A arquitetura da Bronze passa a ser:

```text
                       Settings
                          │
                          ▼
                    load_bronze()
                          │
                          ▼
                 load_bronze_data()
                          │
          ┌───────────────┼────────────────┐
          │               │                │
          ▼               ▼                ▼
       files.py       control.py     validation.py
          │               │                │
          └──────────┐    │    ┌───────────┘
                     ▼    ▼    ▼
                      lineage.py
                          │
                          ▼
                       writer.py
                          │
                          ▼
                 01_bronze/tracker_logs
                          │
                          ▼
                  BronzeLoadResult
                          │
                ┌─────────┴─────────┐
                ▼                   ▼
          has_new_data           batch_ids
                │                   │
                └─────────┬─────────┘
                          ▼
                   futura Silver
```

Fisicamente, o fluxo completo é:

```text
data/raw/inbox
       │
       ▼
 descoberta de CSV
       │
       ▼
      SHA-256
       │
       ▼
00_control/ingestion_files
       │
       ├── hash já processado
       │       ↓
       │    SKIPPED
       │       ↓
       │    archive
       │
       └── novo conteúdo
               ↓
           PROCESSING
               ↓
           validation
             /     \
            /       \
        inválido    válido
           ↓          ↓
        FAILED      lineage
           ↓          ↓
      quarantine    MERGE
                      ↓
                   SUCCESS
                      ↓
                   archive
```

---

# 59. Responsabilidades finais dos módulos Bronze

Ao final dessa fase, a camada está dividida em responsabilidades explícitas.

## `files.py`

Responsável por:

```text
descoberta de CSV
SHA-256
movimentação de arquivos
```

## `validation.py`

Responsável por:

```text
leitura CSV
encoding
normalização de colunas
colunas obrigatórias
colunas reservadas
duplicidade de nomes
resultado de validação
```

## `lineage.py`

Responsável por:

```text
batch_id
row_id
source_file
source_file_hash
source_row_number
ingested_at
ingestion_date
```

## `writer.py`

Responsável por:

```text
PyArrow
CREATE
MERGE insert-only
schema alignment
schema evolution
BronzeWriteResult
```

## `control.py`

Responsável por:

```text
ingestion_files
eventos operacionais
PROCESSING
SUCCESS
FAILED
SKIPPED
histórico append-only
detecção de hashes já processados
```

## `service.py`

Responsável por:

```text
orquestrar as operações anteriores
archive
quarantine
BronzeLoadResult
```

Essa divisão evita voltar à estrutura de um único arquivo responsável por toda a camada.

---

# 60. Resultado da Bronze v1

Ao final dessa etapa, a plataforma possui:

```text
Raw
├── inbox
├── archive
└── quarantine

Control
└── ingestion_files
    ├── PROCESSING
    ├── SUCCESS
    ├── FAILED
    └── SKIPPED

Bronze
└── tracker_logs
    ├── lineage
    ├── ingestion_date
    ├── CREATE inicial
    ├── MERGE insert-only
    ├── idempotência por row_id
    └── evolução de schema
```

A sequência lógica implementada é:

```text
arquivo recebido
      ↓
descoberta
      ↓
hash
      ↓
controle de idempotência
      ↓
validação
      ↓
lineage
      ↓
persistência Delta
      ↓
controle operacional
      ↓
archive / quarantine
```

O resultado da camada é exposto por:

```python
BronzeLoadResult
```

permitindo que as próximas etapas da plataforma consumam:

```text
has_new_data
batch_ids
inserted_row_count
duplicate_row_count
```

sem precisar conhecer detalhes internos da ingestão.

---

# 61. Próxima etapa planejada

Com a Bronze isolada e funcional, a próxima camada passa a ser:

```text
Silver
```

A primeira evolução não deve começar diretamente pela implementação das transformações.

Antes é necessário definir os contratos dos produtos Silver:

```text
telemetry_events
device_identity_events
rejected_logs
```

e estabelecer quais metadados precisam atravessar:

```text
Bronze
   ↓
Silver
```

especialmente:

```text
row_id
batch_id
source_file
source_file_hash
source_row_number
ingested_at
```

A nova etapa deverá preservar a estratégia seguida até aqui:

```text
definir contrato
    ↓
implementar comportamento isolado
    ↓
testar
    ↓
integrar
    ↓
somente então orquestrar
```

