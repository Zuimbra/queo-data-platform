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

# 62. Definir os contratos da camada Silver

Foi criado:

```text
src/
└── queo_data_platform/
    └── contracts/
        └── silver.py
```

## O que?

O desenvolvimento da Silver começou pela formalização do contrato da camada, antes da implementação das transformações.

Foram definidos os três produtos Silver:

```text
telemetry_events
device_identity_events
rejected_logs
```

Também foram definidas suas respectivas colunas de particionamento:

```text
telemetry_events
→ event_date

device_identity_events
→ event_date

rejected_logs
→ rejection_date
```

Outro ponto formalizado foi a preservação da linhagem criada na Bronze.

Foi definido:

```python
SILVER_LINEAGE_COLUMNS = BRONZE_METADATA_COLUMNS
```

Com isso, os produtos Silver devem continuar carregando:

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

Evitar que cada parte da Silver passe a definir nomes de tabelas, colunas de partição ou campos de lineage de maneira independente.

A relação entre contratos passa a ser:

```text
contracts/tracker.py
        │
        │ BRONZE_METADATA_COLUMNS
        ▼
contracts/silver.py
        │
        ├── telemetry_events
        ├── device_identity_events
        └── rejected_logs
```

A Silver pode interpretar e transformar campos de negócio, mas a identidade da linha originalmente ingerida deve permanecer rastreável.

## Como?

Foram criadas constantes como:

```python
TELEMETRY_TABLE_NAME = "telemetry_events"

DEVICE_IDENTITY_TABLE_NAME = "device_identity_events"

REJECTED_LOGS_TABLE_NAME = "rejected_logs"

SILVER_EVENT_PARTITION_COLUMN = "event_date"

SILVER_REJECTION_PARTITION_COLUMN = "rejection_date"
```

Também foram adicionados testes para validar:

```text
nomes das tabelas
colunas de partição
preservação do contrato de lineage
```

Após essa etapa:

```text
pytest
→ 50 testes aprovados
```

### Commit

```text
feat: define silver data contracts
```

---

# 63. Adicionar DuckDB e criar a normalização comum da Silver

Foi adicionada a dependência:

```powershell
uv add duckdb
```

E criado:

```text
src/
└── queo_data_platform/
    └── silver/
        └── normalization.py
```

## O que?

A Silver passou a possuir uma primeira etapa de transformação comum antes da classificação dos registros.

O objetivo dessa etapa é converter a representação da Bronze em uma representação intermediária consistente.

O fluxo passa a ser:

```text
01_bronze/tracker_logs
        ↓
normalize_bronze_dataframe()
        ↓
representação Silver normalizada
```

Nesse ponto ainda não existe separação entre:

```text
telemetry
identity
rejected
```

A função apenas prepara os dados para as etapas seguintes.

## Para que?

Separar:

```text
limpeza
+
normalização
+
tipagem básica
```

de:

```text
classificação
+
regra de negócio
```

Sem essa separação, a tendência seria reconstruir um módulo Silver monolítico contendo:

```text
leitura
normalização
classificação
transformação
persistência
incrementalidade
```

em uma única função.

A nova estrutura permite que cada etapa seja compreendida e testada isoladamente.

## Como?

Foi criado um mapeamento declarativo de colunas da Bronze para nomes utilizados internamente pela Silver.

Exemplos:

```text
TIPO_LOG
→ log_type

MESS_TYPE
→ message_type

LAT
→ latitude_raw

LONT
→ longitude_raw

SPEED
→ speed_raw
```

Os campos textuais passam por operações equivalentes a:

```sql
TRIM
+
NULLIF(..., '')
```

Portanto:

```text
"   T2   "
→ "T2"
```

e:

```text
"   "
→ NULL
```

Os timestamps são convertidos com `TRY_CAST`:

```text
DATA_SERVIDOR
→ server_timestamp

TM_STAMP
→ device_timestamp
```

Um timestamp inválido não interrompe o processamento:

```text
"invalid-timestamp"
→ NULL
```

A etapa também preserva os campos de lineage recebidos da Bronze.

---

## Decisão importante sobre campos do protocolo

Nesta etapa, campos como:

```text
BAT_VOLT
LAT
LONT
```

continuam sendo mantidos como texto:

```text
battery_voltage_raw
latitude_raw
longitude_raw
```

Isso ocorre porque mensagens do tipo:

```text
T1
```

reutilizam essas posições do protocolo para transportar identificadores.

Assim:

```text
BAT_VOLT
LAT
LONT
```

não significam necessariamente:

```text
bateria
latitude
longitude
```

até que o tipo da mensagem seja conhecido.

Converter esses valores para número antes da classificação poderia destruir informação válida de mensagens de identidade.

## Testes

Foram cobertos:

```text
coluna Bronze obrigatória ausente
trim de campos textuais
string vazia → NULL
timestamp válido
timestamp inválido → NULL
campos de protocolo preservados como texto
lineage preservado
```

Após essa etapa:

```text
pytest
→ 57 testes aprovados
```

### Commit

```text
feat: add silver bronze normalization
```

---

# 64. Criar a classificação dos registros Silver

Foi criado:

```text
src/
└── queo_data_platform/
    └── silver/
        └── classification.py
```

## O que?

Depois da normalização, a Silver passa a determinar a natureza de cada registro.

Foi criada:

```python
SilverClassificationResult
```

contendo três conjuntos:

```text
telemetry
identity
rejected
```

O fluxo passa a ser:

```text
normalized
    │
    ▼
classification
    │
    ├── telemetry
    ├── identity
    └── rejected
```

## Para que?

Separar a pergunta:

```text
"para onde esta linha deve ir?"
```

da pergunta:

```text
"como os campos desse tipo de registro devem ser interpretados?"
```

Assim:

```text
classification.py
→ decide o domínio

transformation.py
→ interpreta os campos daquele domínio
```

---

## Como?

Foi criado:

```text
event_timestamp
```

seguindo a prioridade:

```text
device_timestamp
      ↓ se ausente
server_timestamp
```

Conceitualmente:

```sql
COALESCE(
    device_timestamp,
    server_timestamp
)
```

A classificação do `message_type` segue:

```text
T1
→ identidade

T2, T3, T4, ...
→ telemetria
```

O formato aceito para mensagens de protocolo é:

```text
^T[0-9]+$
```

---

## Rejeições

Foram formalizados os principais motivos de rejeição:

```text
MISSING_MESSAGE_TYPE
INVALID_MESSAGE_TYPE
MISSING_OR_INVALID_TIMESTAMP
MISSING_DEVICE_SERIAL
```

Assim, um registro inválido não é simplesmente descartado.

Ele passa a carregar:

```text
rejection_reason
```

permitindo auditoria posterior.

---

## Partição `unknown`

Quando:

```text
device_timestamp = NULL
server_timestamp = NULL
```

não existe uma data válida que possa ser usada para particionamento.

Nesse caso:

```text
rejection_date = "unknown"
```

O registro continua persistível e auditável mesmo sem referência temporal válida.

---

## Exclusividade da classificação

Cada registro deve terminar em apenas um destino:

```text
                    normalized
                        │
              ┌─────────┴─────────┐
              │                   │
         rejection?              não
              │                   │
              ▼            ┌──────┴──────┐
          rejected         │             │
                          T1           T<n> ≠ T1
                           │             │
                           ▼             ▼
                       identity      telemetry
```

Uma linha não pode simultaneamente pertencer a:

```text
telemetry
+
rejected
```

por exemplo.

## Testes

Foram adicionados testes para:

```text
T2 → telemetry
T1 → identity
message_type ausente
message_type inválido
timestamps ausentes
serial ausente
prioridade de device_timestamp
fallback para server_timestamp
contrato mínimo da entrada
```

### Commit

```text
feat: add silver event classification
```

---

# 65. Criar as transformações tipadas dos produtos Silver

Foi criado:

```text
src/
└── queo_data_platform/
    └── silver/
        └── transformation.py
```

## O que?

Depois que os registros são classificados, os candidatos passam pelas transformações específicas de cada produto Silver.

Foram criadas:

```python
transform_telemetry_dataframe(...)
```

e:

```python
transform_identity_dataframe(...)
```

O fluxo passa a ser:

```text
normalization
    ↓
classification
    ↓
transformation
```

## Para que?

Evitar que a classificação também precise conhecer todos os detalhes do protocolo de telemetria e identidade.

A classificação determina:

```text
qual é o tipo do registro?
```

A transformação determina:

```text
como os campos desse tipo devem ser interpretados?
```

---

## Transformação da telemetria

Campos mantidos como texto durante a normalização passam agora por conversões seguras.

Exemplos:

```text
latitude_raw
→ latitude

longitude_raw
→ longitude

speed_raw
→ speed

hdop_raw
→ hdop

rpm_raw
→ rpm

serial_count_raw
→ serial_count
```

As conversões utilizam:

```text
TRY_CAST
```

Portanto:

```text
"45.5"
→ 45.5
```

enquanto:

```text
"invalid"
→ NULL
```

Um valor individual inválido não elimina todo o registro.

---

## Serial do dispositivo

O prefixo:

```text
M
```

é removido de:

```text
device_serial_raw
```

para gerar:

```text
device_serial
```

Exemplo:

```text
M123456789
→ 123456789
```

---

## Qualidade de posição

Foram criados:

```text
has_valid_coordinates
position_quality
```

As coordenadas são consideradas válidas quando:

```text
-90 <= latitude <= 90

-180 <= longitude <= 180
```

`position_quality` pode assumir:

```text
MISSING_COORDINATES
INVALID_COORDINATES
LOW_GPS_PRECISION
VALID
```

Quando:

```text
HDOP > 5
```

a posição recebe:

```text
LOW_GPS_PRECISION
```

### Decisão de regra de negócio

Coordenadas inválidas não enviam automaticamente o evento para:

```text
rejected_logs
```

O registro continua sendo um evento de telemetria.

A qualidade do posicionamento é registrada separadamente.

Isso distingue:

```text
registro estruturalmente inválido
```

de:

```text
evento válido com posição ruim
```

---

## Transformação das mensagens de identidade

Mensagens:

```text
T1
```

reutilizam posições do protocolo para transportar identificadores.

A transformação interpreta:

```text
battery_voltage_raw
→ iccid

latitude_raw
→ imsi

longitude_raw
→ imei
```

Também foram criados:

```text
has_valid_iccid_format
has_valid_imsi_format
has_valid_imei_format
```

As regras utilizadas são:

```text
ICCID
→ 18 a 22 dígitos

IMSI
→ 14 a 16 dígitos

IMEI
→ exatamente 15 dígitos
```

## Testes

Foram testados:

```text
tipagem numérica
valor numérico inválido → NULL
remoção do prefixo M
coordenadas válidas
coordenadas ausentes
coordenadas inválidas
HDOP alto
extração de ICCID
extração de IMSI
extração de IMEI
formatos válidos de identidade
formatos inválidos de identidade
preservação de lineage
```

### Commit

```text
feat: add silver product transformations
```

---

# 66. Formalizar os schemas PyArrow da Silver

O arquivo:

```text
src/queo_data_platform/contracts/silver.py
```

foi expandido.

Foram criados schemas explícitos para:

```text
TELEMETRY_SCHEMA
DEVICE_IDENTITY_SCHEMA
REJECTED_LOGS_SCHEMA
```

## O que?

A Silver deixa de depender apenas da inferência automática de tipos de Pandas e Arrow.

Cada produto passa a possuir um contrato físico explícito.

Exemplos:

```text
event_date
→ string

latitude
→ float64

serial_count
→ int64

has_valid_coordinates
→ bool

source_row_number
→ int64

ingested_at
→ timestamp UTC
```

## Para que?

Garantir estabilidade de schema inclusive quando uma tabela ou coluna está vazia.

Sem schema explícito:

```text
coluna possui apenas NULL
        ↓
Arrow tenta inferir
        ↓
NullType
```

Depois, quando chega:

```text
"TRACKER"
```

ou outro valor real, o tipo persistido anteriormente pode ser incompatível.

Com schema explícito:

```text
NULL
NULL
NULL
```

pode continuar tendo contrato:

```text
string
```

por exemplo.

Isso é especialmente importante para:

```text
rejected_logs
```

que pode inicialmente não possuir nenhuma linha.

---

# 67. Criar persistência Delta da Silver

Foi criado:

```text
src/
└── queo_data_platform/
    └── silver/
        └── writer.py
```

## O que?

A Silver passa a possuir um módulo exclusivamente responsável pela fronteira:

```text
DataFrame
   ↓
PyArrow
   ↓
Delta Lake
```

Foram implementadas operações para:

```text
conversão para Arrow
rebuild completo
replace seletivo por partição
remoção de partições que ficaram vazias
```

---

## `dataframe_to_arrow()`

A função:

```python
dataframe_to_arrow(...)
```

recebe:

```text
DataFrame
+
schema explícito
```

e:

1. valida se todas as colunas necessárias existem;
2. reorganiza as colunas segundo o contrato;
3. cria uma `pa.Table` utilizando o schema Silver.

O fluxo é:

```text
DataFrame
    ↓
Silver Schema
    ↓
PyArrow Table
    ↓
Delta Lake
```

---

## Rebuild completo

Foi criada:

```python
write_full_silver_table(...)
```

A escrita utiliza:

```text
mode="overwrite"
schema_mode="overwrite"
partition_by=[...]
```

Esse caminho permite reconstruir completamente um produto Silver.

---

## Replace seletivo por partição

Foi criada:

```python
write_incremental_silver_partitions(...)
```

Essa função recebe explicitamente:

```text
affected_partitions
```

e substitui somente essas partições.

Exemplo:

```text
telemetry_events

16/08
17/08
18/08
```

Se apenas:

```text
17/08
```

foi afetado:

```text
16/08 → permanece
17/08 → reconstruído
18/08 → permanece
```

A substituição utiliza:

```python
write_deltalake(
    ...,
    mode="overwrite",
    predicate=predicate,
)
```

com predicates equivalentes a:

```text
event_date = '2026-08-17'
```

ou:

```text
rejection_date = 'unknown'
```

---

## Partição afetada que ficou vazia

Também foi tratado o caso:

```text
partição antiga
→ possuía registros

reprocessamento
→ novo resultado = zero registros
```

Apenas deixar de escrever a partição não seria suficiente.

Os registros antigos continuariam existindo.

Nesse cenário é executado:

```python
delta_table.delete(predicate)
```

Assim:

```text
estado recalculado da partição = vazio
```

realmente resulta em:

```text
partição sem registros
```

---

## Preservação de schema

A conversão para Arrow utiliza schemas explícitos.

Isso evita que:

```text
resultado vazio
```

ou:

```text
coluna com somente NULL
```

cause mudanças indesejadas no schema Delta.

---

## Ajuste de tipagem PyArrow / Pyright

Inicialmente o filtro vetorizado utilizava:

```python
pc.equal(...)
```

A operação funcionava em runtime, mas os stubs utilizados pelo Pyright não reconheciam esse atributo.

A implementação foi ajustada para:

```python
pc.call_function("equal", ...)
```

A operação continua executada no Arrow, sem:

```text
converter para Pandas
```

e sem:

```text
ignorar o type checker
```

## Testes

Foram adicionados testes para:

```text
schema string preservado quando valor = NULL
rebuild completo cria Delta Table particionada
replace altera somente a partição afetada
partição vazia remove registros antigos
colunas de partição permanecem string
```

A suíte registrada após essa fase chegou a:

```text
pytest
→ 82 testes aprovados
```

Também foram validados:

```text
ruff
pyright
pytest
```

### Commit

```text
feat: add silver delta persistence
```

---

# 68. Estrutura modular da Silver até a persistência

Neste ponto a Silver possui:

```text
src/queo_data_platform/silver/
│
├── normalization.py
├── classification.py
├── transformation.py
└── writer.py
```

Além do contrato:

```text
src/queo_data_platform/contracts/silver.py
```

O fluxo construído é:

```text
01_bronze/tracker_logs
        │
        ▼
normalization.py
        │
        │ limpeza
        │ timestamps
        │ representação raw
        │ lineage
        ▼
classification.py
        │
        ├── telemetry
        ├── identity
        └── rejected
        │
        ▼
transformation.py
        │
        ├── telemetria tipada
        └── identidade tipada
        │
        ▼
schemas PyArrow
        │
        ▼
writer.py
        │
        ├── telemetry_events
        ├── device_identity_events
        └── rejected_logs
```

A principal diferença em relação à POC é estrutural.

Em vez de concentrar:

```text
normalização
classificação
transformação
persistência
incrementalidade
```

em um único módulo extenso, cada responsabilidade passa a possuir uma fronteira própria.

---

# 69. Iniciar incrementalidade Silver por `batch_id`

O próximo componente iniciado é:

```text
src/
└── queo_data_platform/
    └── silver/
        └── incremental.py
```

## O que?

A incrementalidade da Silver passa a ser desenhada em torno dos:

```text
batch_ids
```

produzidos pela Bronze.

A intenção não é reprocessar diretamente:

```text
WHERE batch_id IN (...)
```

como resultado final.

Os batches servem para descobrir:

```text
quais partições foram afetadas?
```

---

## Estrutura principal

Foi definida:

```python
SilverAffectedPartitions
```

contendo:

```text
event_dates
rejection_dates
```

e propriedades:

```text
include_unknown
is_empty
```

Também foram definidas funções para:

```text
normalize_batch_ids(...)
discover_affected_partitions(...)
load_incremental_bronze_scope(...)
```

---

## `normalize_batch_ids()`

A função recebe coleções como:

```text
list
set
tuple
None
```

e produz uma coleção canônica:

```text
sem valores vazios
sem duplicatas
ordenada
```

Exemplo:

```text
[
    " batch-002 ",
    "batch-001",
    "batch-002",
    ""
]
```

resulta em:

```text
(
    "batch-001",
    "batch-002"
)
```

---

## Descoberta das partições afetadas

A função:

```python
discover_affected_partitions(...)
```

consulta a Bronze para encontrar os timestamps pertencentes aos batches novos.

Para cada linha é utilizado:

```text
TM_STAMP
      ↓ fallback
DATA_SERVIDOR
```

equivalente a:

```sql
COALESCE(
    TRY_CAST(TM_STAMP AS TIMESTAMP),
    TRY_CAST(DATA_SERVIDOR AS TIMESTAMP)
)
```

As datas encontradas passam a compor:

```text
event_dates
```

e também podem afetar:

```text
rejection_dates
```

---

## Regra fundamental da incrementalidade

Os `batch_ids` são utilizados apenas para descobrir quais datas mudaram.

Eles não devem limitar o conjunto final utilizado para reconstruir uma partição.

Considere:

```text
batch antigo
│
└── row A
    event_date = 17/08
```

Depois chega:

```text
batch novo
│
└── row B
    event_date = 17/08
```

O batch novo informa:

```text
17/08 foi afetado
```

Mas o rebuild de:

```text
17/08
```

deve utilizar:

```text
row A
+
row B
```

e não apenas:

```text
row B
```

O fluxo correto é:

```text
batch novo
    ↓
descobrir datas afetadas
    ↓
17/08
    ↓
recarregar TODA a Bronze de 17/08
    ↓
normalização
    ↓
classificação
    ↓
transformação
    ↓
replace completo da partição 17/08
```

Essa decisão é necessária para suportar corretamente:

```text
late-arriving data
```

---

## Late-arriving data

Late-arriving data representa o caso em que um evento chega posteriormente, mas pertence a uma data já processada.

Exemplo:

```text
18/08
chega evento cujo timestamp = 17/08
```

A Silver não deve:

```text
append isoladamente o novo evento
```

nem:

```text
substituir 17/08 usando apenas o batch novo
```

Ela deve:

```text
descobrir que 17/08 mudou
        ↓
reler toda a Bronze de 17/08
        ↓
reconstruir a partição Silver
```

Assim o estado final continua completo e idempotente.

---

## Partição `unknown`

Existe também o caso em que:

```text
TM_STAMP inválido
+
DATA_SERVIDOR inválido
```

ou ambos ausentes.

Esse registro não possui:

```text
event_date
```

e deve chegar a:

```text
rejected_logs
```

usando:

```text
rejection_date = "unknown"
```

Quando um batch novo contém um registro desse tipo:

```text
unknown
```

torna-se uma partição afetada.

Nesse caso, o rebuild deve carregar:

```text
todos os registros Bronze sem timestamp válido
```

e não somente os registros do batch novo.

O comportamento é análogo ao late-arriving data:

```text
batch novo
    ↓
descobre unknown afetado
    ↓
recarrega todo o universo Bronze sem timestamp válido
    ↓
reconstrói rejected_logs/unknown
```

---

## Testes planejados para `incremental.py`

Foram definidos testes para validar:

```text
normalização de batch_ids
batch vazio → nenhuma partição
descoberta de event_date
timestamp inválido → unknown
late-arriving data → scope completo da data
unknown → todos os registros sem timestamp
```

O teste mais importante é conceitualmente:

```text
Bronze

row-old
batch-old
17/08

row-late
batch-new
17/08

row-other
batch-other
18/08
```

Ao processar:

```text
batch-new
```

o scope esperado é:

```text
row-old
row-late
```

e não:

```text
row-late
```

Também não deve incluir:

```text
row-other
```

---

## Estado desta etapa

Neste ponto:

```text
contratos Silver            ✅
normalização                ✅
classificação               ✅
transformações tipadas      ✅
schemas PyArrow             ✅
persistência Delta          ✅

incrementalidade por batch  ◐ em implementação/validação
silver/service.py           ⏳ ainda não iniciado
```

A incrementalidade ainda não deve ser considerada concluída no relatório até executar:

```powershell
uv run ruff format .
uv run ruff check .
uv run pyright
uv run pytest
```

e confirmar os testes do novo:

```text
silver/incremental.py
```

O commit previsto, depois da validação, é:

```text
feat: add silver incremental partition discovery
```

---

# 70. Estado atual da arquitetura

O projeto chegou ao seguinte ponto:

```text
                         QUEO DATA PLATFORM


Raw
│
├── inbox
├── archive
└── quarantine
        │
        ▼
Bronze
│
├── files.py
├── validation.py
├── lineage.py
├── control.py
├── writer.py
└── service.py
        │
        ▼
01_bronze/tracker_logs
        │
        ▼
BronzeLoadResult
        │
        │ batch_ids
        ▼
Silver
│
├── contracts/silver.py
├── normalization.py
├── classification.py
├── transformation.py
├── writer.py
└── incremental.py        ← etapa atual
        │
        ▼
02_silver/
│
├── telemetry_events
├── device_identity_events
└── rejected_logs
```

A Bronze já funciona como uma camada integrada:

```text
inbox
  ↓
discovery
  ↓
hash
  ↓
validation
  ↓
lineage
  ↓
control
  ↓
Delta MERGE
  ↓
archive / quarantine
  ↓
BronzeLoadResult
```

A Silver já possui suas principais peças isoladas:

```text
normalization
classification
transformation
schemas
writer
incremental scope
```

mas ainda não possui:

```text
silver/service.py
```

Portanto, a Silver ainda não deve ser tratada como uma camada integrada concluída.

O próximo grande passo, depois da validação da incrementalidade, será criar:

```text
src/queo_data_platform/silver/service.py
```

responsável por coordenar:

```text
Bronze Delta
    ↓
batch_ids
    ↓
affected partitions
    ↓
Bronze scope
    ↓
normalization
    ↓
classification
    ↓
transformations
    ↓
schemas PyArrow
    ↓
Delta writer
    ↓
SilverLoadResult
```

O `SilverLoadResult` será a futura interface entre:

```text
Silver
↓
Gold
```

da mesma forma que:

```text
BronzeLoadResult
```

já formaliza a interface entre:

```text
Bronze
↓
Silver
```

---

# 71. Próximo passo previsto

Antes de iniciar:

```text
silver/service.py
```

deve ser concluída e validada a incrementalidade implementada em:

```text
silver/incremental.py
```

A validação esperada é:

```powershell
uv run ruff format .
uv run ruff check .
uv run pyright
uv run pytest
```

Somente depois dos checks verdes deverá ser realizado:

```text
feat: add silver incremental partition discovery
```

A sequência planejada passa a ser:

```text
incremental.py
    ↓
testes verdes
    ↓
commit
    ↓
silver/service.py
    ↓
SilverLoadResult
    ↓
teste integrado da Silver
    ↓
fechamento da Silver v1
```

---

# 71. Implementar incrementalidade Silver por `batch_id`

Foi criado:

```text
src/
└── queo_data_platform/
    └── silver/
        └── incremental.py
```

## O que?

A Silver passou a possuir uma camada dedicada à descoberta do escopo incremental.

Até este ponto, os componentes Silver eram capazes de:

```text
normalizar
classificar
transformar
persistir
```

mas ainda não existia uma forma de decidir:

```text
quais dados precisam ser recalculados
quando um novo batch chega na Bronze?
```

Foi criada:

```python
SilverAffectedPartitions
```

com:

```text
event_dates
rejection_dates
```

e propriedades auxiliares:

```text
include_unknown
is_empty
```

Também foram implementadas:

```python
normalize_batch_ids(...)
discover_affected_partitions(...)
load_incremental_bronze_scope(...)
```

---

## Para que?

Permitir que a Silver deixe de realizar rebuild completo em toda execução.

O objetivo é transformar:

```text
novo batch
    ↓
reprocessar toda Bronze
    ↓
regravar toda Silver
```

em:

```text
novo batch
    ↓
descobrir datas impactadas
    ↓
reprocessar somente o escopo necessário
    ↓
substituir apenas as partições afetadas
```

Isso reduz:

```text
leitura desnecessária
transformação desnecessária
escrita desnecessária
```

sem comprometer a consistência das tabelas.

---

## Como?

### Normalização dos `batch_ids`

Foi criada:

```python
normalize_batch_ids(...)
```

A função recebe:

```text
list
set
tuple
None
```

e produz uma tupla:

```text
limpa
deduplicada
ordenada
```

Exemplo:

```text
[
    " batch-002 ",
    "batch-001",
    "batch-002",
    ""
]
```

resulta em:

```text
(
    "batch-001",
    "batch-002",
)
```

Isso impede que detalhes de entrada influenciem o comportamento incremental.

---

## Descoberta das datas afetadas

Foi criada:

```python
discover_affected_partitions(...)
```

A função consulta a Bronze consolidada:

```text
01_bronze/tracker_logs
```

e considera apenas os batches recém-inseridos para descobrir:

```text
quais event_dates foram afetadas?
quais rejection_dates foram afetadas?
```

O timestamp de evento segue a mesma regra da normalização Silver:

```text
TM_STAMP
    ↓ se inválido ou ausente
DATA_SERVIDOR
```

conceitualmente:

```sql
COALESCE(
    TRY_CAST(TM_STAMP AS TIMESTAMP),
    TRY_CAST(DATA_SERVIDOR AS TIMESTAMP)
)
```

Quando há um timestamp válido:

```text
2026-08-17 11:59:50
```

a partição afetada é:

```text
2026-08-17
```

---

## Regra fundamental: batch descobre a partição, mas não define o rebuild

Esta é uma das regras mais importantes da Silver incremental.

Considere:

```text
batch-old
row A
event_date = 2026-08-17
```

Depois chega:

```text
batch-new
row B
event_date = 2026-08-17
```

O `batch-new` serve para descobrir:

```text
2026-08-17 foi afetado
```

Mas o rebuild não pode fazer:

```text
WHERE batch_id = batch-new
```

porque isso produziria:

```text
2026-08-17
└── row B
```

apagando:

```text
row A
```

quando a partição fosse substituída.

O comportamento correto é:

```text
batch-new
    ↓
discover_affected_partitions()
    ↓
2026-08-17
    ↓
load_incremental_bronze_scope()
    ↓
TODAS as linhas Bronze de 2026-08-17
    │
    ├── row A
    └── row B
    ↓
rebuild da partição
```

Portanto:

```text
batch_id
→ mecanismo de descoberta

event_date
→ unidade real de reconstrução
```

Essa separação é o que permite suporte correto a:

```text
late-arriving data
```

---

## Late-arriving data

Late-arriving representa um registro que chega agora, mas pertence logicamente a uma data anterior.

Exemplo:

```text
execução inicial
2026-08-17
└── row-old
```

Depois:

```text
novo arquivo recebido em outro momento
└── row-late
    event_date = 2026-08-17
```

A nova linha não deve simplesmente ser adicionada à Silver sem considerar o estado completo da data.

O fluxo implementado é:

```text
row-late
    ↓
batch-new
    ↓
affected_event_dates
    ↓
2026-08-17
    ↓
recarregar Bronze inteira de 2026-08-17
    ↓
row-old + row-late
    ↓
reconstruir Silver 2026-08-17
```

---

## Tratamento da partição `unknown`

Registros que não possuem:

```text
TM_STAMP válido
```

nem:

```text
DATA_SERVIDOR válido
```

não possuem data de evento.

Esses registros são rejeitados com:

```text
rejection_date = "unknown"
```

A incrementalidade também precisa reconstruir essa partição corretamente.

Considere:

```text
batch-old
row-old-unknown

batch-new
row-new-unknown
```

Quando `batch-new` afeta:

```text
unknown
```

o rebuild precisa carregar:

```text
row-old-unknown
+
row-new-unknown
```

e não somente:

```text
row-new-unknown
```

Por isso:

```python
include_unknown
```

determina se:

```python
load_incremental_bronze_scope(...)
```

também deve recuperar todas as linhas Bronze sem timestamp válido.

---

## Validação do contrato Bronze

A incrementalidade valida que a Bronze possui:

```text
DATA_SERVIDOR
TM_STAMP
batch_id
```

antes de executar a descoberta.

A Silver não assume silenciosamente que qualquer Delta Table pode ser utilizada como Bronze.

---

## Testes

Foram adicionados testes cobrindo:

```text
normalização de batch_ids
batch_ids vazios
descoberta de event_date
timestamp inválido → unknown
late-arriving recupera toda a data
unknown recupera todas as linhas sem timestamp
```

O teste central comprova:

```text
batch-new
        ↓
2026-08-17 afetado
        ↓
scope Bronze
        │
        ├── row-old
        └── row-late
```

e também comprova que:

```text
row de 2026-08-18
```

não entra no processamento de `2026-08-17`.

### Commit previsto / realizado nesta etapa

```text
feat: add silver incremental partition discovery
```

---

# 72. Criar o serviço de orquestração da Silver

Foi criado:

```text
src/
└── queo_data_platform/
    └── silver/
        └── service.py
```

## O que?

Até este ponto, a Silver possuía componentes independentes:

```text
normalization.py
classification.py
transformation.py
writer.py
incremental.py
```

mas ainda faltava uma fronteira pública que executasse essas peças como uma única camada.

Foi criado:

```python
load_silver_data(...)
```

e uma interface baseada em configuração:

```python
load_silver(...)
```

Também foram definidos:

```python
SilverLoadResult
SilverPaths
SilverMode
```

---

## Para que?

Transformar os componentes isolados em um pipeline Silver real:

```text
Bronze
    ↓
scope
    ↓
normalização
    ↓
classificação
    ↓
transformação
    ↓
persistência
    ↓
SilverLoadResult
```

O `service.py` não recria a lógica interna de cada componente.

Ele apenas coordena:

```text
incremental.py
normalization.py
classification.py
transformation.py
writer.py
```

Isso evita voltar ao desenho monolítico do projeto anterior.

---

## Como?

### Resolução dos caminhos

Foi criado:

```python
SilverPaths
```

contendo:

```text
bronze
telemetry
identity
rejected
```

A função:

```python
get_silver_paths(...)
```

resolve:

```text
01_bronze/tracker_logs

02_silver/telemetry_events
02_silver/device_identity_events
02_silver/rejected_logs
```

---

## Carregamento da Bronze

Foi criada:

```python
load_bronze_table(...)
```

Antes de abrir a origem, o código verifica:

```python
is_delta_table(...)
```

Se a Bronze consolidada não existir, a Silver não tenta continuar com um diretório inválido.

---

# 73. Implementar os modos `FULL`, `INCREMENTAL` e `NOOP`

Foi definido:

```python
SilverMode = Literal[
    "FULL",
    "INCREMENTAL",
    "NOOP",
]
```

## O que?

A execução Silver passou a ter três comportamentos explícitos.

---

## `FULL`

O modo:

```text
FULL
```

representa reconstrução completa.

Ele ocorre quando:

```text
batch_ids não foram informados
```

ou quando:

```text
um processamento incremental foi solicitado
mas a Silver ainda não está completamente disponível
```

Nesse caso:

```text
Bronze inteira
    ↓
normalização
    ↓
classificação
    ↓
transformações
    ↓
overwrite completo Silver
```

---

## `INCREMENTAL`

O modo:

```text
INCREMENTAL
```

é utilizado quando:

```text
batch_ids foram informados
+
as três Delta Tables Silver já existem
```

O fluxo é:

```text
batch_ids
    ↓
discover_affected_partitions()
    ↓
affected_event_dates
affected_rejection_dates
    ↓
load_incremental_bronze_scope()
    ↓
reprocessar escopo
    ↓
replace seletivo
```

---

## `NOOP`

O modo:

```text
NOOP
```

é retornado quando:

```text
batch_ids foram solicitados
```

mas:

```text
nenhuma partição Silver é afetada
```

Exemplo:

```text
batch-does-not-exist
```

O resultado é:

```text
mode = NOOP

telemetry_rows_written = 0
identity_rows_written = 0
rejected_rows_written = 0
```

Isso impede processamento inútil.

---

# 74. Criar `SilverLoadResult`

Foi criado:

```python
@dataclass(frozen=True)
class SilverLoadResult:
```

com informações como:

```text
mode
batch_ids
affected_event_dates
affected_rejection_dates
telemetry_rows_written
identity_rows_written
rejected_rows_written
```

Também foi criada:

```python
has_changes
```

com a regra:

```text
FULL
→ True

INCREMENTAL
→ True

NOOP
→ False
```

## Para que?

A Silver deixa de simplesmente:

```text
executar
```

e passa a comunicar para a camada seguinte:

```text
o que foi alterado?
```

Isso é importante para a futura Gold.

A Gold não precisa conhecer diretamente:

```text
source_file
source_file_hash
batch_id
```

Ela poderá receber:

```text
affected_event_dates
affected_rejection_dates
```

e decidir quais produtos derivados precisam ser recalculados.

O fluxo planejado passa a ser:

```text
BronzeLoadResult
        │
        │ batch_ids
        ▼
Silver
        │
        ▼
SilverLoadResult
        │
        ├── affected_event_dates
        └── affected_rejection_dates
                │
                ▼
              Gold
```

---

# 75. Integrar o fluxo completo Bronze → Silver

A função:

```python
load_silver_data(...)
```

passou a coordenar todas as etapas.

## Fluxo `FULL`

```text
Bronze Delta
    ↓
to_pandas()
    ↓
normalize_bronze_dataframe()
    ↓
classify_normalized_dataframe()
    ↓
┌──────────────────────┬──────────────────────┬───────────────┐
│ telemetry            │ identity             │ rejected      │
└──────────────────────┴──────────────────────┴───────────────┘
            ↓
transformações tipadas
            ↓
dataframe_to_arrow()
            ↓
write_full_silver_table()
            ↓
SilverLoadResult(mode="FULL")
```

---

## Fluxo `INCREMENTAL`

```text
Bronze Delta
    │
    │ batch_ids
    ▼
discover_affected_partitions()
    ↓
load_incremental_bronze_scope()
    ↓
TODAS as linhas das partições afetadas
    ↓
normalização
    ↓
classificação
    ↓
transformação
    ↓
write_incremental_silver_partitions()
    ↓
SilverLoadResult(mode="INCREMENTAL")
```

---

## Fluxo `NOOP`

```text
batch_ids
    ↓
nenhuma linha correspondente
    ↓
nenhuma partição afetada
    ↓
NOOP
```

Não existe:

```text
normalização
transformação
escrita Delta
```

nesse caso.

---

# 76. Criar testes de integração do serviço Silver

Foi criado:

```text
tests/
└── integration/
    └── test_silver_service.py
```

## O que?

Até este ponto, a maior parte da Silver estava coberta por testes unitários.

O novo teste de integração verifica o comportamento da camada funcionando como uma unidade.

Os primeiros cenários implementados foram:

```text
FULL cria os três produtos
batch desconhecido → NOOP
late-arriving → INCREMENTAL seletivo
```

---

## FULL cria os produtos Silver

O teste monta uma Bronze contendo:

```text
1 telemetria
1 identidade T1
1 registro rejeitado
```

Depois executa:

```python
load_silver_data(...)
```

e confirma:

```text
mode = FULL

telemetry_rows_written = 1
identity_rows_written = 1
rejected_rows_written = 1
```

Também verifica a existência física de:

```text
telemetry_events
device_identity_events
rejected_logs
```

como Delta Tables.

---

## Batch inexistente retorna `NOOP`

O teste primeiro cria uma Silver válida.

Depois solicita:

```text
batch-does-not-exist
```

O retorno esperado é:

```text
mode = NOOP
```

com:

```text
0 writes
```

---

## Late-arriving reconstrói somente a data afetada

O cenário utiliza inicialmente:

```text
2026-08-17
└── old-17

2026-08-18
└── row-18
```

Depois é adicionada à Bronze:

```text
late-17
batch-new
event_date = 2026-08-17
```

A Silver incremental recebe:

```text
batch-new
```

e descobre:

```text
affected_event_dates
→ ("2026-08-17",)
```

Depois do processamento:

```text
2026-08-17
├── old-17
└── late-17

2026-08-18
└── row-18
```

Isso comprova simultaneamente que:

```text
dados antigos da data afetada são preservados
```

e:

```text
datas não afetadas não são regravadas
```

---

# 77. Identificar falha com produtos Silver vazios

Durante os testes de integração foi encontrado um problema importante.

A primeira execução produziu:

```text
1 telemetria
0 identidades
```

O conjunto:

```text
identity
```

estava corretamente vazio.

Porém, ao converter esse DataFrame para PyArrow, ocorreu:

```text
ArrowTypeError
```

com uma mensagem equivalente a:

```text
Expected a string or bytes dtype,
got int32

Conversion failed for column event_date
```

## O que aconteceu?

O fluxo era:

```text
identity sem linhas
    ↓
DuckDB retorna DataFrame vazio
    ↓
Pandas/DuckDB infere dtype de event_date
    ↓
int32
```

enquanto o contrato Silver exige:

```text
event_date
→ string
```

Depois:

```python
pa.Table.from_pandas(
    dataframe,
    schema=DEVICE_IDENTITY_SCHEMA,
)
```

tentava reconciliar:

```text
DataFrame
event_date = int32
```

com:

```text
Arrow schema
event_date = string
```

e falhava.

---

## Por que isso é um bug importante?

Uma tabela Silver vazia é um estado normal.

Exemplos:

```text
arquivo só possui telemetria
→ identity vazio

arquivo só possui registros válidos
→ rejected vazio

arquivo só possui T1
→ telemetry vazio
```

Portanto:

```text
zero linhas
```

não pode ser tratado como erro.

Além disso, o schema não pode depender da inferência automática de um DataFrame vazio.

---

# 78. Corrigir preservação de schema em produtos vazios

A função:

```python
dataframe_to_arrow(...)
```

em:

```text
silver/writer.py
```

foi ajustada.

## Antes

O fluxo sempre executava:

```python
aligned = dataframe.reindex(columns=schema.names)

return pa.Table.from_pandas(
    aligned,
    schema=schema,
    preserve_index=False,
    safe=True,
)
```

mesmo quando:

```text
dataframe.empty = True
```

---

## Depois

Foi adicionada uma regra explícita:

```python
if dataframe.empty:
    return pa.Table.from_batches(
        [],
        schema=schema,
    )
```

O fluxo passa a ser:

```text
DataFrame possui linhas?
        │
   ┌────┴────┐
   │         │
  sim       não
   │         │
   ▼         ▼
from_pandas  criar tabela Arrow vazia
             diretamente com schema
```

Agora:

```text
event_date vazio
```

continua sendo:

```text
string
```

porque:

```text
schema explícito
```

é a fonte de verdade.

---

## Teste de regressão

Foi adicionado um teste que cria deliberadamente um DataFrame vazio com tipos incorretos:

```text
event_date     → int32
device_serial  → int32
value          → int32
```

mas passa um schema:

```text
event_date     → string
device_serial  → string
value          → float64
```

O resultado esperado é:

```text
0 linhas
+
schema exatamente igual ao contrato
```

Isso garante que o bug não seja reintroduzido.

---

# 79. Corrigir localização do teste de schema vazio

Durante a inclusão do teste anterior ocorreu um erro de organização.

O teste:

```python
test_empty_dataframe_uses_explicit_schema()
```

foi inicialmente colocado em:

```text
tests/unit/test_bronze_writer.py
```

quando deveria estar em:

```text
tests/unit/test_silver_writer.py
```

Isso produziu erros como:

```text
Undefined name dataframe_to_arrow
Undefined name TEST_SCHEMA
Undefined name pa
```

e:

```text
NameError
```

## Correção

O teste foi removido do arquivo Bronze e movido para:

```text
tests/unit/test_silver_writer.py
```

onde já existem:

```text
dataframe_to_arrow
TEST_SCHEMA
pyarrow as pa
```

A correção preserva a separação:

```text
Bronze writer tests
→ comportamento Bronze

Silver writer tests
→ comportamento Silver
```

Após essa correção, a suíte avançou para:

```text
92 testes
```

antes da inclusão dos cenários finais de fechamento da Silver.

---

# 80. Expandir os testes de fechamento da Silver

Depois da estabilização do `service.py`, foram adicionados três cenários adicionais ao teste de integração.

Os cenários são:

```text
primeira requisição incremental → FULL
unknown incremental
execução através de Settings
```

---

## Primeira execução incremental precisa cair para `FULL`

Considere:

```text
Bronze
├── 2026-08-17
└── 2026-08-18
```

A Silver ainda não existe.

A chamada solicita:

```text
batch de 2026-08-18
```

Seria incorreto criar:

```text
Silver
└── somente 2026-08-18
```

porque a camada passaria a representar apenas uma parte da Bronze.

Por isso foi testada a regra:

```text
Silver inexistente
        +
batch_ids informados
        ↓
FULL
```

O resultado precisa conter:

```text
2026-08-17
2026-08-18
```

e não somente a data do batch solicitado.

---

# 81. Validar rebuild incremental de `unknown`

Foi criado um teste de integração para a partição:

```text
rejected_logs/unknown
```

## Cenário inicial

```text
valid-row
+
old-unknown
```

A Silver completa é criada.

Depois chega:

```text
new-unknown
batch-new
```

com:

```text
TM_STAMP inválido
DATA_SERVIDOR inválido
```

A descoberta incremental resulta em:

```text
affected_event_dates
→ ()

affected_rejection_dates
→ ("unknown",)
```

A Silver então reconstrói:

```text
unknown
├── old-unknown
└── new-unknown
```

O teste comprova que a implementação não produz:

```text
unknown
└── new-unknown
```

apagando a rejeição antiga.

---

# 82. Validar execução Silver baseada em `Settings`

Além da função de baixo nível:

```python
load_silver_data(
    bronze_dir=...,
    silver_dir=...,
)
```

foi validada a interface pública:

```python
load_silver(settings)
```

O teste configura:

```text
QUEO_DATA_DIR
```

em um diretório temporário.

Depois:

```python
settings = load_settings()
```

e executa:

```python
load_silver(settings)
```

A função utiliza:

```text
settings.bronze_dir
settings.silver_dir
```

sem caminhos hardcoded.

Isso fecha a integração entre:

```text
config/
    ↓
Silver
```

e prepara a camada para futura orquestração do pipeline.

---

# 83. Estado dos testes após o fechamento da Silver

A suíte de integração Silver passou a possuir:

```text
6 testes
```

A execução específica registrou:

```text
tests/integration/test_silver_service.py
→ 6 passed
```

Os cenários cobertos são:

```text
FULL cria os produtos
batch desconhecido → NOOP
late-arriving → INCREMENTAL
primeiro incremental sem Silver → FULL
unknown incremental
execução via Settings
```

Depois foi executada a suíte completa:

```text
pytest
→ 95 testes aprovados
```

Resultado registrado:

```text
95 passed
```

O type checker também foi executado:

```text
pyright
→ 0 errors
→ 0 warnings
→ 0 informations
```

Portanto, neste ponto:

```text
runtime                 ✅
testes unitários        ✅
testes de integração    ✅
type checking           ✅
```

---

# 84. Pendência final de lint antes do commit de fechamento

Na última execução registrada, o Ruff encontrou apenas:

```text
I001
Import block is un-sorted or un-formatted
```

em:

```text
tests/integration/test_silver_service.py
```

A inconsistência ocorre porque:

```python
from queo_data_platform.config.settings import (
    load_settings,
)
```

foi adicionado depois dos demais imports internos.

Não existe erro funcional associado.

O próprio Ruff informa que a correção pode ser feita automaticamente com:

```powershell
uv run ruff check . --fix
```

seguido de:

```powershell
uv run ruff format .
```

Depois disso deve ser executado novamente:

```powershell
uv run ruff check .
uv run pyright
uv run pytest
```

O estado esperado para fechamento é:

```text
ruff
→ All checks passed

pyright
→ 0 errors

pytest
→ 95 passed
```

---

# 85. Estado atual da camada Silver

Neste ponto a Silver possui a seguinte estrutura:

```text
src/
└── queo_data_platform/
    └── silver/
        ├── __init__.py
        ├── normalization.py
        ├── classification.py
        ├── transformation.py
        ├── incremental.py
        ├── writer.py
        └── service.py
```

Os contratos ficam em:

```text
src/
└── queo_data_platform/
    └── contracts/
        └── silver.py
```

O fluxo completo implementado é:

```text
                         BRONZE

                01_bronze/tracker_logs
                           │
                           │
                           ▼
                    Silver Service
                           │
              ┌────────────┴────────────┐
              │                         │
             FULL                  INCREMENTAL
              │                         │
              │                         ▼
              │                  batch_ids
              │                         │
              │                         ▼
              │               affected partitions
              │                         │
              │                         ▼
              │               Bronze scope completo
              │                         │
              └─────────────┬───────────┘
                            │
                            ▼
                  normalization.py
                            │
                            ▼
                  classification.py
                  ┌─────────┼─────────┐
                  │         │         │
                  ▼         ▼         ▼
             telemetry   identity   rejected
                  │         │
                  └────┬────┘
                       ▼
               transformation.py
                       │
                       ▼
                    writer.py
                       │
        ┌──────────────┼─────────────────┐
        │              │                 │
        ▼              ▼                 ▼
telemetry_events  device_identity   rejected_logs
                       _events
        │              │                 │
        └──────────────┼─────────────────┘
                       ▼
                SilverLoadResult
                       │
            ┌──────────┴──────────────┐
            │                         │
 affected_event_dates    affected_rejection_dates
            │                         │
            └──────────┬──────────────┘
                       ▼
                  futura Gold
```

---

# 86. Capacidades concluídas na Silver

A camada atualmente possui suporte para:

```text
normalização de dados Bronze
trim de campos
string vazia → NULL
TRY_CAST de timestamps
preservação de campos raw
preservação de lineage

classificação T1
classificação de telemetria T<n>
rejeições estruturais
rejection_reason
rejection_date = unknown

tipagem de telemetria
tipagem de identidade
validação de coordenadas
position_quality
validação de ICCID
validação de IMSI
validação de IMEI

schemas PyArrow explícitos
produtos vazios com schema estável

Delta Lake particionado
full rebuild
replace seletivo de partições
remoção de partição vazia

batch-aware processing
affected partitions
late-arriving data
unknown incremental

FULL
INCREMENTAL
NOOP

SilverLoadResult
Settings
testes unitários
testes de integração
```

---

# 87. Relação atual Bronze → Silver

A fronteira entre as camadas agora está clara.

A Bronze retorna:

```python
BronzeLoadResult
```

contendo:

```text
has_new_data
batch_ids
```

Esses batches podem alimentar:

```python
load_silver(
    settings,
    batch_ids=bronze_result.batch_ids,
)
```

A Silver não precisa receber:

```text
nome do CSV
hash do arquivo
linhas específicas alteradas
```

Ela utiliza os batches apenas para descobrir:

```text
quais partições foram afetadas
```

Depois reconstrói o estado correto dessas partições.

O fluxo arquitetural passa a ser:

```text
Raw
 ↓
Bronze
 ↓
BronzeLoadResult
 ↓
batch_ids
 ↓
Silver
 ↓
SilverLoadResult
 ↓
affected_event_dates
affected_rejection_dates
 ↓
Gold
```

Essa interface reduz o acoplamento entre as camadas.

---

# 88. Próximo ponto de desenvolvimento

Após corrigir o último `I001` do Ruff e realizar o commit de fechamento, a camada Silver pode ser considerada concluída nesta primeira versão.

O commit de fechamento previsto é:

```text
feat: finalize silver processing layer
```

A próxima camada a ser iniciada será:

```text
Gold
```

Os produtos Gold já definidos pelo domínio são:

```text
data_quality_summary
device_daily_summary
device_last_position
device_route_points
dim_device
```

A estratégia deve continuar a mesma utilizada na Silver:

```text
contratos
    ↓
builders / transformações por produto
    ↓
persistência
    ↓
incrementalidade
    ↓
service
    ↓
testes de integração
```

evitando recriar um único módulo Gold monolítico.

---

# 89. Estado geral do projeto neste ponto

```text
                         QUEO DATA PLATFORM


Raw
│
├── inbox
├── archive
└── quarantine
        │
        ▼
Bronze                                      ✅
│
├── files.py
├── validation.py
├── lineage.py
├── control.py
├── writer.py
└── service.py
        │
        ▼
01_bronze/tracker_logs
        │
        ▼
BronzeLoadResult
        │
        │ batch_ids
        ▼
Silver                                      ✅ funcional
│
├── normalization.py
├── classification.py
├── transformation.py
├── incremental.py
├── writer.py
└── service.py
        │
        ▼
02_silver/
│
├── telemetry_events
├── device_identity_events
└── rejected_logs
        │
        ▼
SilverLoadResult
        │
        ├── affected_event_dates
        └── affected_rejection_dates
        │
        ▼
Gold                                        ⏳ próximo passo
│
├── data_quality_summary
├── device_daily_summary
├── device_last_position
├── device_route_points
└── dim_device
        │
        ▼
Query Layer                                 ⏳
        │
        ├── REST API                         ⏳
        └── MCP                              ⏳
```

Estado de validação registrado:

```text
pytest
→ 95 passed

pyright
→ 0 errors
→ 0 warnings
→ 0 informations

ruff
→ 1 pendência I001 de ordenação de import
   em test_silver_service.py
```

Portanto, o código da Silver está funcionalmente validado.

Antes de iniciar a Gold, resta apenas:

```text
1. corrigir o import com Ruff;
2. repetir ruff / pyright / pytest;
3. realizar o commit de fechamento;
4. iniciar os contratos Gold.
```

---

# 90. Iniciar a camada Gold pelos contratos estruturais

Após o fechamento funcional da Silver, o desenvolvimento avançou para:

```text
src/
└── queo_data_platform/
    └── gold/
```

Antes de implementar as agregações, foi criado:

```text
src/
└── queo_data_platform/
    └── contracts/
        └── gold.py
```

## O que?

O contrato Gold centraliza os nomes dos cinco produtos de dados planejados:

```python
DIM_DEVICE_TABLE_NAME = "dim_device"

DEVICE_LAST_POSITION_TABLE_NAME = "device_last_position"

DEVICE_ROUTE_POINTS_TABLE_NAME = "device_route_points"

DEVICE_DAILY_SUMMARY_TABLE_NAME = "device_daily_summary"

DATA_QUALITY_SUMMARY_TABLE_NAME = "data_quality_summary"
```

A Gold passa, portanto, a possuir os seguintes produtos:

```text
03_gold/
│
├── dim_device
├── device_last_position
├── device_route_points
├── device_daily_summary
└── data_quality_summary
```

## Para que?

A Silver organiza eventos tratados.

A Gold possui outra responsabilidade:

```text
Silver
→ eventos tratados

Gold
→ produtos prontos para consulta
```

Por exemplo:

```text
telemetry_events
```

contém vários eventos de um mesmo dispositivo.

Já:

```text
device_last_position
```

deve responder diretamente:

```text
qual é a posição mais recente do dispositivo?
```

sem obrigar API, Query Layer ou MCP a reconstruírem essa informação a cada consulta.

---

# 91. Separar produtos Gold por estratégia de atualização

No contrato também foram definidas duas categorias.

## Tabelas orientadas a entidade

```python
GOLD_ENTITY_TABLES = (
    DIM_DEVICE_TABLE_NAME,
    DEVICE_LAST_POSITION_TABLE_NAME,
)
```

Essas tabelas possuem como chave principal lógica:

```python
GOLD_DEVICE_KEY = "device_serial"
```

Portanto:

```text
dim_device
device_last_position
        ↓
uma linha atual por device_serial
```

A estratégia de persistência futura será baseada em:

```text
MERGE / UPSERT
ON device_serial
```

---

## Tabelas orientadas a partição temporal

Também foi definido:

```python
GOLD_EVENT_PARTITION_COLUMN = "event_date"

GOLD_QUALITY_PARTITION_COLUMN = "metric_date"
```

E:

```python
GOLD_PARTITIONED_TABLES = {
    DEVICE_ROUTE_POINTS_TABLE_NAME: GOLD_EVENT_PARTITION_COLUMN,
    DEVICE_DAILY_SUMMARY_TABLE_NAME: GOLD_EVENT_PARTITION_COLUMN,
    DATA_QUALITY_SUMMARY_TABLE_NAME: GOLD_QUALITY_PARTITION_COLUMN,
}
```

O desenho passa a ser:

```text
device_route_points
        ↓
event_date

device_daily_summary
        ↓
event_date

data_quality_summary
        ↓
metric_date
```

## Para que?

Permitir que o incremental da Gold tenha duas estratégias distintas:

```text
dados por entidade
        ↓
MERGE

dados por data
        ↓
replace seletivo da partição
```

Isso acompanha a própria natureza dos produtos.

---

# 92. Criar as bases deduplicadas da Gold

Foi criado:

```text
src/
└── queo_data_platform/
    └── gold/
        └── base.py
```

O módulo define as relações Silver utilizadas internamente pelo DuckDB:

```python
SILVER_TELEMETRY_RELATION = "silver_telemetry"

SILVER_IDENTITY_RELATION = "silver_identity"

SILVER_REJECTED_RELATION = "silver_rejected"
```

E duas views intermediárias:

```python
TELEMETRY_GOLD_BASE_VIEW = "telemetry_gold_base"

IDENTITY_GOLD_BASE_VIEW = "identity_gold_base"
```

## O que?

A Gold não deve necessariamente agregar diretamente todas as linhas Silver.

Antes dos produtos operacionais serem construídos, eventos logicamente equivalentes são deduplicados.

O fluxo passa a ser:

```text
telemetry_events
       ↓
silver_telemetry
       ↓
telemetry_gold_base
       ↓
produtos Gold
```

e:

```text
device_identity_events
       ↓
silver_identity
       ↓
identity_gold_base
       ↓
produtos Gold
```

## Para que?

A Bronze possui idempotência física por:

```text
row_id
```

Mas isso não significa que dois registros diferentes não possam representar o mesmo evento lógico.

Exemplo:

```text
arquivo A
row_id = AAA

arquivo B
row_id = BBB
```

Os dois registros podem ter:

```text
mesmo dispositivo
mesmo timestamp
mesmo tipo de mensagem
mesmo serial_count
mesma posição
mesma velocidade
```

Na Bronze e Silver:

```text
AAA
BBB
```

continuam sendo registros distintos de origem.

Na Gold operacional:

```text
mesmo evento lógico
        ↓
uma ocorrência
```

---

# 93. Implementar deduplicação lógica de telemetria

A view:

```text
telemetry_gold_base
```

é criada com:

```sql
ROW_NUMBER() OVER (...)
```

A partição lógica utiliza:

```text
device_serial
event_timestamp
message_type
serial_count
latitude
longitude
speed
```

Campos opcionais são normalizados no critério através de:

```sql
COALESCE(
    CAST(campo AS VARCHAR),
    '__NULL__'
)
```

## Como?

O conceito central é:

```sql
QUALIFY
    ROW_NUMBER() OVER (
        PARTITION BY
            device_serial,
            event_timestamp,
            message_type,
            ...
        ORDER BY
            server_timestamp DESC NULLS LAST,
            source_file DESC NULLS LAST
    ) = 1
```

Portanto:

```text
evento lógico duplicado
        ↓
ordenar candidatos
        ↓
preferir recebimento mais recente
        ↓
manter uma linha
```

---

## Filtro mínimo da base

Também é exigido:

```sql
WHERE device_serial IS NOT NULL
  AND event_timestamp IS NOT NULL
```

Assim, produtos Gold de dispositivo não trabalham com eventos que não possuam uma entidade ou momento identificável.

---

# 94. Implementar deduplicação lógica de identidade

A mesma ideia foi aplicada em:

```text
identity_gold_base
```

Porém o critério lógico é diferente.

A identidade é particionada por:

```text
device_serial
event_timestamp
imei
imsi
iccid
```

Portanto:

```text
mesmo device
+
mesmo timestamp
+
mesmo ICCID
+
mesmo IMSI
+
mesmo IMEI
        ↓
evento equivalente
```

Se os identificadores mudarem:

```text
IMEI antigo
        ↓
IMEI novo
```

os dois registros são preservados.

## Para que?

Eliminar retransmissões equivalentes sem perder mudanças reais de identidade.

---

# 95. Criar o produto Gold `dim_device`

Foi criado:

```text
src/
└── queo_data_platform/
    └── gold/
        └── dim_device.py
```

A principal função adicionada foi:

```python
build_dim_device(...)
```

## O que?

O produto:

```text
dim_device
```

consolida telemetria e identidade em:

```text
uma linha por device_serial
```

O resultado contém informações como:

```text
device_serial

current_imei
current_imsi
current_iccid
current_identity_auxiliary
current_protocol_version

first_seen_at
last_seen_at

first_identity_at
last_identity_at

first_telemetry_at
last_telemetry_at

identity_event_count
telemetry_event_count

has_identity_event
has_telemetry_event

current_imei_format_valid
current_imsi_format_valid
current_iccid_format_valid
```

---

# 96. Construir o resumo atual da identidade

Dentro de `build_dim_device(...)` foi criado um CTE:

```sql
identity_summary
```

Ele agrega:

```text
identity_gold_base
```

por:

```text
device_serial
```

Exemplo:

```sql
MIN(event_timestamp)
    AS first_identity_at

MAX(event_timestamp)
    AS last_identity_at

COUNT(*)
    AS identity_event_count
```

Os dados atuais são selecionados com:

```sql
ARG_MAX(
    imei,
    event_timestamp
)
```

A mesma estratégia é usada para:

```text
IMEI
IMSI
ICCID
identity_auxiliary
protocol_version

flags de validade
```

## Para que?

Considere:

```text
09:00 → IMEI A
15:00 → IMEI B
```

A dimensão deve apresentar:

```text
current_imei = IMEI B
```

mas continuar informando:

```text
first_identity_at
last_identity_at
identity_event_count
```

---

# 97. Construir o resumo de telemetria da dimensão

Também foi criado:

```sql
telemetry_summary
```

agrupado por:

```text
device_serial
```

Ele produz:

```text
first_telemetry_at
last_telemetry_at
telemetry_event_count
latest_telemetry_protocol_version
```

O universo final de dispositivos é obtido com:

```sql
SELECT device_serial
FROM identity_gold_base

UNION

SELECT device_serial
FROM telemetry_gold_base
```

## Para que?

Permitir que um dispositivo exista em:

```text
dim_device
```

mesmo que ainda não tenha produzido uma mensagem de identidade `T1`.

Exemplo:

```text
device 2001

telemetry ✅
identity  ❌
```

Resultado:

```text
dim_device
device_serial = 2001

identity_event_count = 0
telemetry_event_count = 1

has_identity_event = false
has_telemetry_event = true
```

---

# 98. Calcular primeira e última atividade global do dispositivo

Foi criado ainda:

```sql
all_activity
```

com:

```text
identity events
      +
telemetry events
```

seguido por:

```sql
activity_summary
```

que calcula:

```sql
MIN(event_timestamp)
    AS first_seen_at

MAX(event_timestamp)
    AS last_seen_at
```

## Para que?

`first_seen_at` e `last_seen_at` representam atividade do dispositivo na plataforma como um todo.

Não apenas:

```text
telemetria
```

nem apenas:

```text
identidade
```

mas:

```text
identity + telemetry
```

---

# 99. Preparar `dim_device` para incrementalidade por dispositivo

`build_dim_device(...)` aceita:

```python
affected_devices: tuple[str, ...] | None
```

Quando informado, é registrada uma relação temporária:

```text
affected_gold_devices
```

O resultado é filtrado para:

```sql
WHERE devices.device_serial IN (
    SELECT device_serial
    FROM affected_gold_devices
)
```

O comportamento passa a ser:

```text
FULL
→ affected_devices=None
→ todos os dispositivos

INCREMENTAL
→ affected_devices=(...)
→ somente dispositivos afetados
```

A persistência incremental ainda não foi implementada neste ponto.

O builder apenas já está preparado para receber esse escopo.

---

# 100. Corrigir os tipos de timestamp nos testes Gold

Durante os testes de `dim_device`, foi encontrado:

```text
AssertionError

'2026-08-16 08:00:00'
!=
Timestamp('2026-08-16 08:00:00')
```

## O que aconteceu?

Os fixtures de teste forneciam:

```python
"event_timestamp":
    "2026-08-16 08:00:00"
```

ou seja:

```text
string
```

Como o DataFrame era registrado diretamente no DuckDB:

```text
string
    ↓
DuckDB
    ↓
MIN / MAX
    ↓
string
```

Porém, o contrato real da Silver já estabelece timestamps tipados.

## Correção

Os testes passaram a utilizar:

```python
pd.Timestamp("2026-08-16 08:00:00")
```

Assim:

```text
fixture de teste
      ↓
representa o contrato Silver real
      ↓
Gold recebe TIMESTAMP
```

## Por que corrigir o teste e não a Gold?

Porque adicionar um:

```sql
CAST(event_timestamp AS TIMESTAMP)
```

apenas para acomodar um fixture incorreto esconderia uma inconsistência do teste.

A fronteira já define:

```text
Silver
event_timestamp → TIMESTAMP
```

Logo o teste deve respeitar esse contrato.

---

# 101. Atualizar a API Arrow utilizada pelo DuckDB

Durante essa mesma etapa foi emitido:

```text
DeprecationWarning

fetch_arrow_table()
is deprecated
```

O código foi atualizado de:

```python
.fetch_arrow_table()
```

para:

```python
.to_arrow_table()
```

Esse padrão passou a ser utilizado pelos builders Gold seguintes.

O fluxo permanece:

```text
DuckDB query
     ↓
Arrow Table
     ↓
futura persistência Delta
```

---

# 102. Criar `device_last_position`

Foi criado:

```text
src/
└── queo_data_platform/
    └── gold/
        └── last_position.py
```

A função principal é:

```python
build_device_last_position(...)
```

## O que?

O produto retorna:

```text
no máximo uma posição por device_serial
```

representando a última posição operacionalmente válida conhecida.

---

# 103. Filtrar posições utilizáveis para `device_last_position`

A origem utilizada é:

```text
telemetry_gold_base
```

Antes de escolher a última posição, são mantidas apenas linhas com:

```sql
has_valid_coordinates = TRUE
```

Também são descartados pontos:

```text
latitude  = 0
longitude = 0
```

através de:

```sql
AND NOT (
    latitude = 0
    AND longitude = 0
)
```

## Para que?

Uma posição `(0, 0)` pode ser matematicamente válida em termos de faixa:

```text
latitude  ∈ [-90, 90]
longitude ∈ [-180, 180]
```

mas não deve substituir a última posição operacional real de um rastreador.

Portanto:

```text
posição válida anterior
        ↓
novo ponto (0, 0)
        ↓
Gold ignora
        ↓
última posição real permanece
```

---

# 104. Selecionar a última posição por dispositivo

A escolha utiliza:

```sql
ROW_NUMBER() OVER (
    PARTITION BY device_serial

    ORDER BY
        event_timestamp DESC,
        server_timestamp DESC NULLS LAST,
        serial_count DESC NULLS LAST
)
```

seguido por:

```sql
QUALIFY ... = 1
```

A prioridade é:

```text
1. event_timestamp mais recente
2. server_timestamp mais recente
3. maior serial_count
```

O produto preserva:

```text
device_serial

last_position_date
last_position_at
received_at

latitude
longitude
speed
direction_degrees

battery_voltage
internal_battery

odometer_total
horimeter

hdop
rx_level

message_type
report_type
serial_count
protocol_version
position_quality
source_file
```

---

# 105. Preparar `device_last_position` para incrementalidade

Assim como a dimensão, o builder aceita:

```python
affected_devices
```

e registra:

```text
affected_position_devices
```

O filtro final permite recalcular:

```text
somente dispositivos afetados
```

em uma execução incremental futura.

O destino previsto será:

```text
device_last_position
        ↓
MERGE
        ↓
device_serial
```

---

# 106. Criar `device_route_points`

Foi criado:

```text
src/
└── queo_data_platform/
    └── gold/
        └── route_points.py
```

A função principal é:

```python
build_device_route_points(...)
```

## O que?

Diferentemente de:

```text
device_last_position
```

que mantém somente uma posição atual, `device_route_points` mantém o histórico de posições válidas.

O modelo é:

```text
device_serial
+
event_date
+
sequência de pontos
```

---

# 107. Filtrar os pontos válidos da rota

Foi criado o CTE:

```sql
valid_points
```

Ele exige:

```sql
has_valid_coordinates = TRUE
```

e também remove:

```text
(0, 0)
```

O `event_date` é derivado de:

```sql
STRFTIME(
    event_timestamp,
    '%Y-%m-%d'
)
```

O resultado mantém dados como:

```text
event_date
device_serial
event_timestamp
received_at

latitude
longitude
speed
direction_degrees

odometer_trip
odometer_total
horimeter
hdop
rx_level

message_type
report_type
serial_count
protocol_version
position_quality
source_file
```

---

# 108. Sequenciar os pontos de rota

Foi criado:

```sql
ROW_NUMBER() OVER (
    PARTITION BY
        device_serial,
        event_date

    ORDER BY
        event_timestamp,
        received_at NULLS LAST,
        serial_count NULLS LAST
)
```

produzindo:

```text
point_sequence
```

Exemplo:

```text
device 1001
2026-08-17

10:00 → point_sequence = 1
11:00 → point_sequence = 2
12:00 → point_sequence = 3
```

No próximo dia:

```text
device 1001
2026-08-18

08:00 → point_sequence = 1
```

## Para que?

Permitir reconstrução direta da trajetória:

```text
ponto 1
  ↓
ponto 2
  ↓
ponto 3
  ↓
...
```

sem o consumidor precisar ordenar e enumerar toda a telemetria novamente.

---

# 109. Classificar movimento nos pontos de rota

Foi adicionada:

```text
is_moving
```

com:

```sql
COALESCE(
    speed,
    0
) >= 5
```

A regra é:

```text
speed < 5
→ parado

speed >= 5
→ movimento

speed NULL
→ tratado como 0
→ parado
```

Esse indicador já deixa o produto preparado para consultas de trajetória e análise de movimento.

---

# 110. Preparar `device_route_points` para rebuild por data

O builder aceita:

```python
event_dates
```

Quando o argumento é fornecido, é registrada:

```text
route_gold_dates
```

A consulta passa a incluir somente:

```text
datas afetadas
```

O comportamento planejado é:

```text
SilverLoadResult
    │
    └── affected_event_dates
              ↓
Gold
              ↓
build_device_route_points(
    event_dates=...
)
              ↓
replace seletivo
```

O writer Gold ainda não foi implementado nesta etapa.

---

# 111. Criar `device_daily_summary`

Foi criado:

```text
src/
└── queo_data_platform/
    └── gold/
        └── daily_summary.py
```

A função principal é:

```python
build_device_daily_summary(...)
```

## O que?

Esse é o primeiro produto Gold realmente agregado.

O agrupamento é:

```text
device_serial
+
event_date
```

Portanto:

```text
uma linha
=
resumo de um dispositivo em um dia
```

---

# 112. Agregar volume e tipos de mensagens por dia

No CTE:

```sql
daily_aggregated
```

são calculados:

```sql
MIN(event_timestamp)
    AS first_event_at

MAX(event_timestamp)
    AS last_event_at

COUNT(*)
    AS message_count

COUNT(DISTINCT message_type)
    AS distinct_message_type_count
```

O produto consegue responder diretamente:

```text
quando o dispositivo começou a enviar eventos no dia?
quando enviou o último?
quantos eventos?
quantos tipos de mensagem diferentes?
```

---

# 113. Agregar qualidade das posições

Também são calculados:

```text
valid_position_count
invalid_position_count
low_gps_precision_count
valid_position_percentage
```

A contagem válida usa:

```sql
WHERE has_valid_coordinates = TRUE
```

Enquanto a inválida utiliza:

```sql
WHERE has_valid_coordinates IS NOT TRUE
```

O percentual é:

```text
valid_position_count
---------------------------- × 100
message_count
```

com arredondamento para duas casas.

---

# 114. Agregar movimento e velocidade

Foram adicionadas:

```text
moving_event_count
stopped_event_count

average_speed
average_speed_while_moving
maximum_speed
```

A regra permanece:

```text
speed >= 5
→ moving

speed < 5
→ stopped
```

Porém:

```text
speed IS NULL
```

não entra em:

```text
stopped_event_count
```

porque a regra exige explicitamente:

```sql
speed IS NOT NULL
AND speed < 5
```

---

# 115. Agregar métricas de GPS e bateria

Também são produzidas:

```text
average_hdop
minimum_hdop
maximum_hdop

minimum_battery_voltage
maximum_battery_voltage
average_battery_voltage

minimum_internal_battery
maximum_internal_battery
average_internal_battery
```

## Para que?

Transformar dezenas ou milhares de eventos Silver em métricas diárias prontas para:

```text
dashboard
API
alertas
MCP
analytics
```

---

# 116. Calcular evolução diária do odômetro

O resumo busca:

```text
first_odometer_total
last_odometer_total
```

utilizando o timestamp do evento.

Em seguida:

```text
odometer_delta_raw
```

é calculado.

A regra é:

```text
first = NULL
ou
last = NULL
        ↓
delta = NULL
```

Se:

```text
last >= first
```

então:

```text
delta = last - first
```

---

# 117. Detectar regressão de odômetro

Também foi criado:

```text
has_odometer_regression
```

Quando:

```text
last_odometer_total
<
first_odometer_total
```

o resultado é:

```text
has_odometer_regression = true
odometer_delta_raw = NULL
```

## Para que?

Evitar transformar uma regressão de contador em:

```text
distância negativa
```

que poderia ser interpretada como uma medição válida.

O produto sinaliza explicitamente a anomalia.

---

# 118. Armazenar primeira e última posição válida do dia

O resumo diário também produz:

```text
first_valid_position_at
last_valid_position_at

first_latitude
first_longitude

last_latitude
last_longitude
```

Somente posições com:

```text
has_valid_coordinates = TRUE
```

participam desse cálculo.

Assim, uma telemetria inválida no início ou fim do dia não substitui as posições utilizáveis.

---

# 119. Preparar `device_daily_summary` para incrementalidade

O builder aceita:

```python
event_dates
```

Quando informado:

```text
daily_gold_dates
```

é registrado no DuckDB.

A agregação é limitada às datas solicitadas.

Isso prepara o fluxo:

```text
Silver
affected_event_dates
        ↓
Gold
        ↓
device_daily_summary
        ↓
somente datas afetadas
        ↓
replace seletivo
```

---

# 120. Criar `data_quality_summary`

Foi criado:

```text
src/
└── queo_data_platform/
    └── gold/
        └── quality_summary.py
```

A função principal é:

```python
build_data_quality_summary(...)
```

## O que?

Esse produto mede a qualidade diária do processamento Silver.

Ele combina:

```text
telemetry_events
device_identity_events
rejected_logs
```

e produz:

```text
uma linha por metric_date
```

---

# 121. Não utilizar a base deduplicada para métricas de qualidade

Existe uma diferença importante.

Produtos operacionais utilizam:

```text
telemetry_gold_base
identity_gold_base
```

porque querem eventos logicamente deduplicados.

Porém:

```text
data_quality_summary
```

consulta diretamente:

```text
silver_telemetry
silver_identity
silver_rejected
```

O fluxo é:

```text
Silver real
   │
   ├── telemetry
   ├── identity
   └── rejected
        ↓
data_quality_summary
```

## Para que?

A pergunta do produto de qualidade não é:

```text
quantos eventos lógicos diferentes existiram?
```

mas:

```text
quantos registros a Silver aceitou ou rejeitou?
```

Portanto, deduplicar antes dessa métrica alteraria o volume real processado.

---

# 122. Agregar eventos aceitos

Foi criado:

```sql
telemetry_counts
```

que agrupa:

```text
telemetry_events
```

por:

```text
event_date
```

produzindo:

```text
telemetry_event_count
```

Também:

```sql
identity_counts
```

produz:

```text
identity_event_count
```

O total aceito é:

```text
accepted_event_count
=
telemetry_event_count
+
identity_event_count
```

---

# 123. Agregar rejeições e seus motivos

Foi criado:

```sql
rejected_counts
```

agrupado por:

```text
rejection_date
```

O resultado contém:

```text
rejected_event_count

missing_message_type_count
invalid_message_type_count
invalid_timestamp_count
missing_device_serial_count
unknown_rejection_count
```

Os motivos utilizados correspondem aos motivos definidos pela Silver:

```text
MISSING_MESSAGE_TYPE
INVALID_MESSAGE_TYPE
MISSING_OR_INVALID_TIMESTAMP
MISSING_DEVICE_SERIAL
UNKNOWN_REJECTION_REASON
```

---

# 124. Preservar a partição `unknown` nas métricas de qualidade

A data da rejeição é normalizada através de:

```sql
COALESCE(
    CAST(
        rejection_date
        AS VARCHAR
    ),
    'unknown'
)
```

Portanto:

```text
rejection_date = NULL
```

é transformado em:

```text
metric_date = unknown
```

Da mesma forma, registros Silver já classificados com:

```text
rejection_date = "unknown"
```

permanecem nessa mesma categoria.

## Para que?

Manter mensuráveis justamente os registros que não possuem timestamp válido.

Sem isso:

```text
registro sem data
→ desaparece das métricas por data
```

Com:

```text
unknown
```

temos:

```text
registro sem data
→ continua observável
```

---

# 125. Construir o conjunto completo de datas de qualidade

Foi criado:

```sql
all_dates
```

com:

```text
datas da telemetria
UNION
datas da identidade
UNION
datas das rejeições
```

## Para que?

Uma data pode existir somente em uma das fontes.

Exemplo:

```text
17/08
→ somente telemetria

18/08
→ somente identidade

19/08
→ somente rejected
```

O produto precisa gerar:

```text
17/08
18/08
19/08
```

e preencher métricas ausentes com:

```text
0
```

Isso é feito com:

```sql
COALESCE(..., 0)
```

---

# 126. Calcular total e percentual de rejeição

Após combinar as fontes:

```text
accepted_event_count
=
telemetry
+
identity
```

e:

```text
total_event_count
=
telemetry
+
identity
+
rejected
```

O percentual é:

```text
rejected_event_count
----------------------------- × 100
total_event_count
```

com:

```sql
NULLIF(total, 0)
```

para evitar divisão por zero.

O resultado é armazenado em:

```text
rejection_percentage
```

---

# 127. Preparar `data_quality_summary` para incrementalidade

O builder aceita:

```python
metric_dates
```

e registra:

```text
quality_gold_dates
```

O filtro final permite reconstruir somente métricas específicas.

No futuro, essas datas deverão resultar da união:

```text
SilverLoadResult
│
├── affected_event_dates
└── affected_rejection_dates
        │
        ▼
quality metric dates
```

Assim:

```text
novo evento válido
→ pode alterar qualidade

nova rejeição
→ também pode alterar qualidade
```

---

# 128. Adicionar testes unitários dos produtos Gold

Foram adicionados testes específicos para os produtos implementados.

## `dim_device`

O arquivo:

```text
tests/unit/test_gold_dim_device.py
```

cobre cenários como:

```text
identidade + telemetria
identidade mais recente
dispositivo apenas com telemetria
first_seen / last_seen
filtro por affected_devices
```

---

## `device_last_position`

O arquivo:

```text
tests/unit/test_gold_last_position.py
```

cobre:

```text
seleção do evento mais recente
coordenadas inválidas
remoção de (0, 0)
desempate por server_timestamp
affected_devices
preservação das métricas de posição
```

---

## `device_route_points`

O arquivo:

```text
tests/unit/test_gold_route_points.py
```

cobre:

```text
ordem cronológica
point_sequence
reset da sequência por device/data
coordenadas inválidas
remoção de (0, 0)
is_moving
filtro por event_dates
```

---

## `device_daily_summary`

O arquivo:

```text
tests/unit/test_gold_daily_summary.py
```

cobre:

```text
agregação diária
qualidade de posições
movimento e parada
delta do odômetro
regressão do odômetro
primeira/última posição válida
filtro por event_dates
```

---

## `data_quality_summary`

O arquivo:

```text
tests/unit/test_gold_quality_summary.py
```

cobre:

```text
aceitos + rejeitados
motivos de rejeição
datas provenientes das três fontes
unknown
filtro por metric_dates
contagem direta da Silver
```

---

# 129. Estado atual dos builders Gold

Neste ponto, o código Gold implementado está organizado em:

```text
src/
└── queo_data_platform/
    │
    ├── contracts/
    │   └── gold.py
    │
    └── gold/
        ├── __init__.py
        ├── base.py
        ├── dim_device.py
        ├── last_position.py
        ├── route_points.py
        ├── daily_summary.py
        └── quality_summary.py
```

A transformação disponível neste momento é:

```text
Silver
│
├── telemetry_events
├── device_identity_events
└── rejected_logs
        │
        ▼
DuckDB relations
        │
        ├── silver_telemetry
        ├── silver_identity
        └── silver_rejected
        │
        ▼
Gold base views
        │
        ├── telemetry_gold_base
        └── identity_gold_base
        │
        ▼
Gold builders
        │
        ├── dim_device
        ├── device_last_position
        ├── device_route_points
        ├── device_daily_summary
        └── data_quality_summary
        │
        ▼
PyArrow Tables
```

---

# 130. O que ainda não foi implementado na Gold

Embora os cinco produtos já possuam builders, a camada Gold ainda não está completa.

Ainda faltam:

```text
schemas PyArrow definitivos
        ↓
writer Gold
        ↓
persistência Delta
        ↓
MERGE de tabelas por entidade
        ↓
replace seletivo de partições
        ↓
descoberta de dispositivos afetados
        ↓
service Gold
        ↓
FULL / INCREMENTAL / NOOP
        ↓
GoldLoadResult
        ↓
testes de integração
```

Portanto:

```text
Gold transformations
        ✅

Gold persistence
        ⏳

Gold orchestration
        ⏳
```

---

# 131. Estratégia planejada para persistência Gold

Com os contratos e builders atuais, a persistência deverá seguir dois caminhos.

## Tabelas por entidade

```text
dim_device
device_last_position
```

Estratégia:

```text
PyArrow
   ↓
Delta MERGE
   ↓
device_serial
```

Comportamento desejado:

```text
device já existe
→ atualizar estado Gold

device novo
→ inserir
```

---

## Tabelas por partição

```text
device_route_points
device_daily_summary
data_quality_summary
```

Estratégia:

```text
recalcular partição completa afetada
        ↓
overwrite seletivo
```

Partições:

```text
route_points
→ event_date

daily_summary
→ event_date

quality_summary
→ metric_date
```

Essa estratégia mantém o mesmo princípio usado na Silver:

```text
late-arriving data
        ↓
descobrir escopo afetado
        ↓
reconstruir estado completo do escopo
        ↓
substituir somente esse estado
```

---

# 132. Ponto atual de desenvolvimento

O projeto está atualmente neste ponto:

```text
                         QUEO DATA PLATFORM

Raw
 │
 ▼
Bronze                                      ✅
 │
 ├── discovery
 ├── validation
 ├── lineage
 ├── control
 ├── Delta MERGE
 └── service
 │
 ▼
Silver                                      ✅
 │
 ├── normalization
 ├── classification
 ├── transformation
 ├── explicit schemas
 ├── Delta writer
 ├── affected partitions
 ├── late-arriving
 ├── FULL
 ├── INCREMENTAL
 └── NOOP
 │
 ▼
Gold                                        🚧
 │
 ├── contracts                              ✅
 ├── deduplicated base views                ✅
 │
 ├── dim_device                             ✅ builder
 ├── device_last_position                   ✅ builder
 ├── device_route_points                    ✅ builder
 ├── device_daily_summary                   ✅ builder
 └── data_quality_summary                   ✅ builder
 │
 ├── Arrow schemas                          ⏳
 ├── Delta writer                           ⏳
 ├── incremental orchestration              ⏳
 └── service                                ⏳
 │
 ▼
Query Layer                                 ⏳
 │
 ├── REST API                               ⏳
 └── MCP                                    ⏳
```

O desenvolvimento deve continuar a partir de:

```text
contracts/gold.py
        ↓
adicionar schemas Arrow dos cinco produtos
        ↓
gold/writer.py
```

Somente depois da persistência deve ser criado:

```text
gold/service.py
```

para não misturar:

```text
transformação
persistência
incrementalidade
orquestração
```

em um único módulo.

---

# 133. Próximo passo recomendado

O próximo passo é expandir:

```text
src/queo_data_platform/contracts/gold.py
```

com schemas PyArrow explícitos para:

```text
DIM_DEVICE_SCHEMA

DEVICE_LAST_POSITION_SCHEMA

DEVICE_ROUTE_POINTS_SCHEMA

DEVICE_DAILY_SUMMARY_SCHEMA

DATA_QUALITY_SUMMARY_SCHEMA
```

## Para que?

A experiência da Silver já demonstrou que inferência automática de schema pode ser problemática, principalmente em:

```text
DataFrames vazios
colunas completamente NULL
rebuilds seletivos
```

A Gold deve aplicar a mesma regra:

```text
builder
    ↓
Arrow Table
    ↓
schema Gold explícito
    ↓
Delta
```

O contrato, e não a inferência dos dados de uma execução específica, deve ser a fonte de verdade para os tipos persistidos.

Depois:

```text
schemas
   ↓
writer
   ↓
incremental
   ↓
service
   ↓
GoldLoadResult
   ↓
integração
```

Esse é o ponto exato para retomada do desenvolvimento.

Conferi o estado atual do `main`. O `STEPSREPORT.md` termina no **Passo 133**, enquanto a Gold já avançou até schemas explícitos, writer Delta, escopo incremental, service completo e testes de integração de fechamento. 

**Não incluí o pipeline como concluído**, porque no repositório publicado `src/queo_data_platform/pipeline/` ainda contém apenas `__init__.py`. Além disso, a Silver publicada ainda interpreta `batch_ids=()` como `FULL`, ponto que precisa ser corrigido antes da orquestração ponta a ponta. ([GitHub][1])

Copie e cole **a partir daqui**, depois do Passo 133:


---

# 134. Definir schemas PyArrow explícitos para os produtos Gold

O próximo passo após a implementação dos cinco builders foi transformar:

```text
contracts/gold.py
```

em um contrato físico completo da camada Gold.

Até então, o arquivo já definia:

```text
nomes das tabelas
chaves
colunas de partição
```

mas ainda não definia formalmente os tipos persistidos.

Foram adicionados schemas PyArrow para os cinco produtos:

```python
DIM_DEVICE_SCHEMA
DEVICE_LAST_POSITION_SCHEMA
DEVICE_ROUTE_POINTS_SCHEMA
DEVICE_DAILY_SUMMARY_SCHEMA
DATA_QUALITY_SUMMARY_SCHEMA
```

## O que?

Cada produto Gold passou a possuir uma definição explícita de:

```text
nome da coluna
tipo físico
ordem das colunas
```

Por exemplo, `dim_device` passou a possuir um schema semelhante a:

```text
device_serial                  string
current_imei                   string
current_imsi                   string
current_iccid                  string
current_identity_auxiliary     string
current_protocol_version       string

first_seen_at                  timestamp[us]
last_seen_at                   timestamp[us]

first_identity_at              timestamp[us]
last_identity_at               timestamp[us]

first_telemetry_at             timestamp[us]
last_telemetry_at              timestamp[us]

identity_event_count           int64
telemetry_event_count          int64

has_identity_event             bool
has_telemetry_event            bool
```

## Para que?

Evitar que o schema persistido dependa da inferência de tipos realizada em uma execução específica.

O problema da inferência automática já havia aparecido na Silver.

Por exemplo:

```text
execução A
coluna possui valores
        ↓
tipo inferido corretamente

execução B
coluna completamente NULL
        ↓
tipo inferido pode mudar
```

Com o contrato explícito:

```text
builder
   ↓
PyArrow Table
   ↓
schema oficial Gold
   ↓
Delta Table
```

o contrato passa a ser a fonte de verdade.

---

# 135. Definir os tipos físicos compartilhados da Gold

Foi criada a constante:

```python
GOLD_TIMESTAMP = pa.timestamp("us")
```

## O que?

Essa constante representa o tipo utilizado pelos timestamps de negócio da Gold.

Ela é reutilizada em campos como:

```text
first_seen_at
last_seen_at

last_position_at
received_at

event_timestamp

first_event_at
last_event_at

first_valid_position_at
last_valid_position_at
```

## Para que?

Evitar repetir:

```python
pa.timestamp("us")
```

em vários schemas.

Além disso, garante que todos os produtos utilizem a mesma resolução temporal.

A estrutura fica:

```text
contracts/gold.py
        │
        └── GOLD_TIMESTAMP
                │
                ├── dim_device
                ├── last_position
                ├── route_points
                └── daily_summary
```

---

# 136. Manter datas de partição como texto

As colunas:

```text
event_date
metric_date
```

foram definidas como:

```python
pa.string()
```

e não como:

```python
pa.date32()
```

## O que?

As tabelas particionadas da Gold utilizam:

```text
device_route_points
→ event_date

device_daily_summary
→ event_date

data_quality_summary
→ metric_date
```

## Para que?

Além das datas normais:

```text
2026-08-17
2026-08-18
```

o fluxo de qualidade precisa suportar:

```text
unknown
```

para registros rejeitados sem timestamp válido.

Portanto:

```text
metric_date
```

não pode assumir que todos os valores são datas reais.

A decisão foi manter as partições como strings.

---

# 137. Classificar formalmente as tabelas Gold

Foram adicionadas estruturas que classificam os produtos por estratégia de persistência.

## Tabelas por entidade

```python
GOLD_ENTITY_TABLES = (
    DIM_DEVICE_TABLE_NAME,
    DEVICE_LAST_POSITION_TABLE_NAME,
)
```

Isso representa:

```text
dim_device
device_last_position
```

Ambas possuem:

```text
device_serial
```

como chave lógica.

---

## Tabelas particionadas

Foi criado:

```python
GOLD_PARTITIONED_TABLES = {
    DEVICE_ROUTE_POINTS_TABLE_NAME: GOLD_EVENT_PARTITION_COLUMN,
    DEVICE_DAILY_SUMMARY_TABLE_NAME: GOLD_EVENT_PARTITION_COLUMN,
    DATA_QUALITY_SUMMARY_TABLE_NAME: GOLD_QUALITY_PARTITION_COLUMN,
}
```

Representando:

```text
device_route_points
→ event_date

device_daily_summary
→ event_date

data_quality_summary
→ metric_date
```

## Para que?

Permitir que a persistência trate corretamente dois tipos diferentes de produto:

```text
produto por entidade
        ↓
MERGE

produto por partição
        ↓
replace seletivo
```

---

# 138. Criar o catálogo de schemas Gold

Também foi criado:

```python
GOLD_TABLE_SCHEMAS
```

com o mapeamento:

```text
dim_device
→ DIM_DEVICE_SCHEMA

device_last_position
→ DEVICE_LAST_POSITION_SCHEMA

device_route_points
→ DEVICE_ROUTE_POINTS_SCHEMA

device_daily_summary
→ DEVICE_DAILY_SUMMARY_SCHEMA

data_quality_summary
→ DATA_QUALITY_SUMMARY_SCHEMA
```

## Para que?

Centralizar a relação:

```text
nome lógico da tabela
        ↓
schema físico oficial
```

Isso facilita persistência, validação e futuras camadas de leitura.

---

# 139. Criar o writer da camada Gold

Foi criado:

```text
src/
└── queo_data_platform/
    └── gold/
        └── writer.py
```

## O que?

Esse módulo concentra a persistência Delta da Gold.

A separação ficou:

```text
builders
→ transformação

writer.py
→ persistência
```

Ele implementa duas estratégias principais:

```text
entity tables
→ MERGE

partitioned tables
→ selective overwrite
```

## Para que?

Evitar que funções como:

```text
build_dim_device()
build_device_route_points()
```

também sejam responsáveis por:

```text
abrir Delta Tables
executar MERGE
executar DELETE
executar overwrite
```

Assim:

```text
Gold builder
     ↓
PyArrow Table
     ↓
Gold writer
     ↓
Delta Lake
```

---

# 140. Alinhar produtos Gold ao schema oficial

Foi criada:

```python
align_gold_table(...)
```

## O que?

Antes da persistência, o writer verifica se o produto contém todas as colunas definidas no schema.

A lógica começa com:

```text
schema.names
     ↓
comparar com table.column_names
     ↓
coluna ausente?
     ↓
ValueError
```

Depois:

```python
ordered = table.select(schema.names)
```

garante a ordem correta.

Por fim:

```python
ordered.cast(
    schema,
    safe=True,
)
```

converte os tipos para o contrato físico.

## Para que?

Mesmo que o DuckDB retorne:

```text
colunas em ordem diferente
tipos compatíveis mas diferentes
```

o dado persistido deve seguir exatamente:

```text
contracts/gold.py
```

---

# 141. Preservar schema em produtos Gold vazios

`align_gold_table()` também trata:

```text
table.num_rows == 0
```

de forma especial.

Nesse caso:

```python
pa.Table.from_batches(
    [],
    schema=schema,
)
```

é retornado.

## O que?

Um produto vazio continua carregando o schema completo.

Exemplo:

```text
0 registros
```

mas ainda:

```text
device_serial      string
latitude           float64
event_timestamp    timestamp[us]
...
```

## Para que?

Evitar que:

```text
resultado vazio
    ↓
inferência de schema
    ↓
null / int32 / tipos inconsistentes
```

quebre rebuilds incrementais ou criação de Delta Tables.

---

# 142. Validar a chave das tabelas por entidade

Foi criada:

```python
validate_entity_key(...)
```

## O que?

Antes de um MERGE, o writer verifica:

```text
a coluna existe?
        ↓
não → erro

possui NULL?
        ↓
sim → erro

possui chave duplicada?
        ↓
sim → erro
```

A chave utilizada atualmente é:

```text
device_serial
```

## Para que?

Um MERGE precisa de correspondência determinística.

Este caso é inválido:

```text
source
device_serial = 1001
device_serial = 1001
```

porque o writer não deveria decidir qual linha representa o estado final da entidade.

Essa responsabilidade pertence ao builder.

---

# 143. Implementar persistência FULL das tabelas por entidade

Foi criada:

```python
write_gold_entity_table(...)
```

No modo:

```text
full_rebuild = True
```

é executado:

```python
write_deltalake(
    table_path,
    aligned,
    mode="overwrite",
    schema_mode="overwrite",
)
```

## O que?

Uma reconstrução FULL substitui completamente o estado anterior da tabela.

Fluxo:

```text
Silver completa
     ↓
builder completo
     ↓
Gold completa
     ↓
overwrite
```

## Para que?

Casos como:

```text
primeira execução
Gold inexistente
migração de schema
Gold incompleta
rebuild solicitado
```

precisam reconstruir o produto inteiro.

---

# 144. Implementar MERGE incremental das tabelas por entidade

Quando:

```text
full_rebuild = False
```

`write_gold_entity_table()` executa um MERGE Delta.

A condição utilizada é:

```text
target.device_serial
=
source.device_serial
```

O MERGE possui:

```text
MATCHED
→ UPDATE ALL

NOT MATCHED
→ INSERT ALL
```

## O que?

Exemplo:

```text
Gold atual

1001 → estado antigo
2002 → estado atual
```

Novo escopo:

```text
1001 → estado recalculado
3003 → dispositivo novo
```

Resultado:

```text
1001 → atualizado
2002 → preservado
3003 → inserido
```

## Para que?

Evitar sobrescrever:

```text
dim_device
device_last_position
```

inteiras quando apenas poucos dispositivos mudaram.

---

# 145. Implementar persistência seletiva das tabelas particionadas

Foi criada:

```python
write_gold_partitioned_table(...)
```

## FULL

Quando:

```text
full_rebuild = True
```

é feito:

```text
overwrite completo
+
partition_by
```

## INCREMENTAL

Quando:

```text
full_rebuild = False
```

o writer percorre:

```python
affected_partitions
```

e reconstrói somente cada partição afetada.

Exemplo:

```text
Gold
├── 2026-08-17
├── 2026-08-18
└── 2026-08-19

affected
└── 2026-08-18
```

Resultado:

```text
17 → preservado
18 → substituído
19 → preservado
```

## Para que?

Manter o mesmo princípio de late-arriving data utilizado na Silver:

```text
nova informação antiga
        ↓
descobrir data afetada
        ↓
recalcular estado completo da data
        ↓
substituir apenas a data
```

---

# 146. Filtrar cada partição antes do overwrite

Foi criada:

```python
filter_partition(...)
```

A função usa:

```python
pc.call_function("equal", [...])
```

para selecionar apenas:

```text
partition_column
=
partition_value
```

## O que?

Se:

```text
table
├── 17/08
├── 18/08
└── 19/08
```

e o loop está processando:

```text
18/08
```

o writer obtém apenas:

```text
partition_table
└── 18/08
```

antes de executar o overwrite Delta.

---

# 147. Remover partições que ficaram vazias

O incremental também trata o cenário:

```text
partição existia anteriormente
        ↓
rebuild atual produz 0 registros
```

Nesse caso:

```python
delta_table.delete(predicate)
```

é executado.

## Para que?

Sem esse comportamento:

```text
Gold antiga
17/08 → 10 registros

rebuild
17/08 → 0 registros
```

deixaria os 10 registros antigos incorretamente persistidos.

O comportamento correto é:

```text
rebuild = vazio
        ↓
remover partição anterior
```

---

# 148. Adicionar testes unitários do writer Gold

Foi criado:

```text
tests/unit/test_gold_writer.py
```

Os testes cobrem:

```text
schema preservado em resultado vazio
FULL de tabela por entidade
MERGE com UPDATE + INSERT
rejeição de chaves duplicadas
FULL particionado
replace somente da data afetada
remoção de partição que ficou vazia
erro em incremental sem Delta Table existente
```

## Para que?

Esses testes validam diretamente as propriedades críticas da persistência:

```text
schema
idempotência
escopo incremental
integridade das entidades
preservação de partições não afetadas
```

---

# 149. Criar o modelo de escopo incremental da Gold

Foi criado:

```text
src/
└── queo_data_platform/
    └── gold/
        └── incremental.py
```

com:

```python
@dataclass(frozen=True)
class GoldIncrementalScope:
```

O objeto possui:

```text
event_dates
rejection_dates
quality_dates
affected_devices
```

## O que?

Ele representa:

> exatamente qual parte da Gold precisa ser recalculada.

Exemplo:

```text
event_dates
→ 2026-08-17

rejection_dates
→ 2026-08-17
→ unknown

quality_dates
→ 2026-08-17
→ unknown

affected_devices
→ 1001
→ 2002
```

---

# 150. Normalizar valores de partição Gold

Foi criada:

```python
normalize_partition_values(...)
```

A função:

```text
remove valores vazios
remove duplicatas
remove espaços
ordena valores
```

Exemplo:

```text
entrada:

2026-08-18
" 2026-08-17 "
2026-08-18
""
```

resultado:

```text
2026-08-17
2026-08-18
```

## Para que?

Garantir que o escopo incremental seja:

```text
limpo
determinístico
sem duplicidade
```

antes de chegar aos builders e writers.

---

# 151. Calcular datas afetadas da qualidade

Foi criada:

```python
build_quality_dates(...)
```

A lógica é:

```text
quality_dates
=
event_dates
UNION
rejection_dates
```

## Por quê?

`data_quality_summary` depende de:

```text
telemetry_events
device_identity_events
rejected_logs
```

Então tanto:

```text
novo evento aceito
```

quanto:

```text
nova rejeição
```

podem alterar uma métrica diária de qualidade.

Exemplo:

```text
event_dates
→ 17/08
→ 18/08

rejection_dates
→ 18/08
→ unknown
```

resultado:

```text
quality_dates
→ 17/08
→ 18/08
→ unknown
```

---

# 152. Descobrir dispositivos afetados

Foi criada:

```python
discover_affected_devices(...)
```

## O que?

A função recebe:

```text
event_dates
```

e consulta duas fontes:

```text
silver_telemetry
silver_identity
```

Ela executa:

```text
telemetry devices
        +
identity devices
        ↓
UNION
        ↓
affected_devices
```

## Para que?

Uma alteração de telemetria pode modificar:

```text
dim_device
device_last_position
```

mas uma mensagem de identidade T1 também pode modificar:

```text
current_imei
current_imsi
current_iccid
current_protocol_version
first_seen_at
last_seen_at
identity_event_count
```

Por isso não basta olhar somente:

```text
telemetry_events
```

---

# 153. Separar datas afetadas de dispositivos afetados

A incrementalidade Gold passou a distinguir dois conceitos.

## Produtos por data

```text
device_route_points
device_daily_summary
```

recebem:

```text
event_dates
```

## Produto de qualidade

```text
data_quality_summary
```

recebe:

```text
quality_dates
```

## Produtos por entidade

```text
dim_device
device_last_position
```

recebem:

```text
affected_devices
```

A estrutura fica:

```text
SilverLoadResult
      │
      ├── affected_event_dates
      │          │
      │          ├── route_points
      │          ├── daily_summary
      │          │
      │          └── discover devices
      │                    │
      │                    ├── dim_device
      │                    └── last_position
      │
      └── affected_rejection_dates
                  │
                  ▼
       event_dates ∪ rejection_dates
                  │
                  ▼
             quality_dates
                  │
                  ▼
        data_quality_summary
```

---

# 154. Adicionar testes do escopo incremental Gold

Foi criado:

```text
tests/unit/test_gold_incremental.py
```

Os testes verificam:

```text
normalização de partições

união de event_dates
+
rejection_dates

dispositivos vindos de telemetria

dispositivos vindos de identidade

isolamento entre datas

rejeição unknown sem alteração de entidades

construção completa de GoldIncrementalScope
```

Um caso especialmente importante é:

```text
affected_event_dates = ()

affected_rejection_dates =
("unknown",)
```

Nesse caso:

```text
affected_devices = ()

quality_dates =
("unknown",)
```

Ou seja:

```text
apenas qualidade precisa mudar
```

---

# 155. Criar o service da camada Gold

Foi criado:

```text
src/
└── queo_data_platform/
    └── gold/
        └── service.py
```

## O que?

O service passou a orquestrar:

```text
fontes Silver
     ↓
DuckDB
     ↓
Gold base views
     ↓
escopo
     ↓
builders
     ↓
writer
     ↓
GoldLoadResult
```

O objetivo é manter:

```text
builders
→ transformação

incremental.py
→ descoberta de escopo

writer.py
→ persistência

service.py
→ orquestração
```

---

# 156. Criar `GoldPaths`

Foi criada:

```python
@dataclass(frozen=True)
class GoldPaths:
```

Ela contém:

```text
telemetry
identity
rejected

dim_device
last_position
route_points
daily_summary
quality_summary
```

## Para que?

Centralizar todos os caminhos físicos usados pela execução Gold.

Em vez de espalhar:

```python
gold_dir / "dim_device"
gold_dir / "device_route_points"
```

pela implementação, os caminhos são resolvidos em:

```python
get_gold_paths(...)
```

---

# 157. Criar `GoldProducts`

Também foi criada:

```python
@dataclass(frozen=True)
class GoldProducts:
```

contendo:

```text
dim_device
last_position
route_points
daily_summary
quality_summary
```

Cada atributo é:

```text
pa.Table
```

## O que?

Esse objeto representa:

```text
resultado dos builders
```

antes da persistência.

Fluxo:

```text
DuckDB
  ↓
builders
  ↓
GoldProducts
  ↓
writer
```

---

# 158. Criar `GoldLoadResult`

Foi criado:

```python
@dataclass(frozen=True)
class GoldLoadResult:
```

com:

```text
mode

affected_event_dates
affected_rejection_dates
affected_quality_dates
affected_devices

dim_device_rows_written
last_position_rows_written
route_points_rows_written
daily_summary_rows_written
quality_summary_rows_written
```

Também foi adicionada:

```python
@property
def has_changes(...)
```

## Para que?

A Gold deixa de retornar apenas:

```text
processamento concluído
```

e passa a informar exatamente:

```text
qual modo executou

qual escopo foi afetado

quais entidades mudaram

quantas linhas foram persistidas
```

Isso prepara a integração futura com:

```text
pipeline
logs
observabilidade
API administrativa
```

---

# 159. Validar que todas as fontes Silver existem

Foi criada:

```python
validate_silver_sources(...)
```

A Gold exige:

```text
telemetry_events
device_identity_events
rejected_logs
```

como Delta Tables válidas.

Se alguma estiver ausente:

```text
Gold
→ FileNotFoundError
```

## Para que?

Evitar que a Gold construa um estado aparentemente válido a partir de uma Silver incompleta.

A regra é:

```text
Silver completa
→ Gold pode executar

Silver incompleta
→ erro
```

---

# 160. Registrar Delta Tables Silver no DuckDB

Foi criada:

```python
register_silver_sources(...)
```

A função abre:

```text
telemetry_events
device_identity_events
rejected_logs
```

com:

```python
DeltaTable(...)
```

e registra os datasets no DuckDB.

As relações utilizadas são:

```text
silver_telemetry
silver_identity
silver_rejected
```

Fluxo:

```text
Delta Lake
   ↓
PyArrow Dataset
   ↓
DuckDB relation
```

## Para que?

Os builders Gold continuam trabalhando com DuckDB sem conhecer detalhes da persistência física.

---

# 161. Descobrir o escopo completo de um rebuild Gold

Foram criadas:

```python
discover_all_event_dates(...)
discover_all_rejection_dates(...)
build_full_gold_scope(...)
```

## O que?

No modo FULL, o service não depende do escopo incremental recebido da Silver.

Ele consulta diretamente o estado atual das tabelas.

### Datas de eventos

São obtidas de:

```text
telemetry
UNION
identity
```

### Datas de rejeição

São obtidas de:

```text
rejected_logs
```

incluindo:

```text
unknown
```

Depois:

```text
event_dates
+
rejection_dates
        ↓
build_gold_incremental_scope()
        ↓
scope completo
```

## Para que?

Um rebuild FULL precisa representar:

```text
todo o estado Silver atual
```

e não apenas o último batch executado.

---

# 162. Implementar execução FULL dos cinco builders

Foi criada:

```python
build_gold_products(...)
```

No modo:

```text
full_rebuild = True
```

são executados sem filtros:

```python
build_dim_device(connection)

build_device_last_position(connection)

build_device_route_points(connection)

build_device_daily_summary(connection)

build_data_quality_summary(connection)
```

## O que?

Todos os produtos são recalculados a partir da Silver completa.

Fluxo:

```text
Silver completa
     ↓
Gold base
     ↓
5 builders completos
     ↓
GoldProducts
```

---

# 163. Executar apenas builders afetados no incremental

O comportamento incremental foi refinado.

Antes de executar cada builder, o service verifica o escopo.

## Produtos por entidade

```python
if scope.affected_devices:
```

só então são executados:

```text
dim_device
device_last_position
```

## Produtos por data

```python
if scope.event_dates:
```

só então são executados:

```text
device_route_points
device_daily_summary
```

## Produto de qualidade

```python
if scope.quality_dates:
```

só então é executado:

```text
data_quality_summary
```

## Para que?

Evitar processamento desnecessário.

Exemplo:

```text
nova rejeição
rejection_date = unknown
```

gera:

```text
affected_devices = ()
event_dates = ()
quality_dates = ("unknown",)
```

Então:

```text
dim_device              não executa
last_position           não executa
route_points            não executa
daily_summary           não executa
quality_summary         executa
```

---

# 164. Criar produtos Gold vazios com schema explícito

Para permitir que produtos não afetados atravessem o fluxo sem executar builders, foi criada:

```python
empty_gold_table(...)
```

A função retorna:

```python
pa.Table.from_batches(
    [],
    schema=schema,
)
```

## O que?

Um produto não afetado é representado por:

```text
0 linhas
+
schema oficial
```

## Para que?

Isso permite manter:

```text
GoldProducts
```

sempre completo, sem utilizar:

```text
None
```

e sem executar builders desnecessários.

Exemplo:

```text
quality-only update

GoldProducts
├── dim_device          0 linhas
├── last_position       0 linhas
├── route_points        0 linhas
├── daily_summary       0 linhas
└── quality_summary     recalculado
```

---

# 165. Centralizar a persistência em `write_gold_products`

Foi criada:

```python
write_gold_products(...)
```

## O que?

Ela recebe:

```text
GoldPaths
GoldProducts
GoldIncrementalScope
full_rebuild
```

e direciona cada produto ao writer correto.

### Entidades

```text
dim_device
last_position
        ↓
write_gold_entity_table()
```

### Partições por evento

```text
route_points
daily_summary
        ↓
write_gold_partitioned_table()
        ↓
event_date
```

### Qualidade

```text
quality_summary
        ↓
write_gold_partitioned_table()
        ↓
metric_date
```

---

# 166. Implementar os modos FULL, INCREMENTAL e NOOP da Gold

A função principal passou a ser:

```python
load_gold_data(...)
```

Ela decide entre três modos.

## FULL

Executado quando:

```text
Gold não existe
```

ou:

```text
Gold está incompleta
```

ou:

```text
silver_result não foi informado
```

ou:

```text
Silver executou FULL
```

---

## INCREMENTAL

Executado quando:

```text
Gold completa
+
SilverLoadResult.mode = INCREMENTAL
```

Nesse caso:

```text
SilverLoadResult
     ↓
GoldIncrementalScope
     ↓
builders seletivos
     ↓
writers seletivos
```

---

## NOOP

Executado quando:

```text
Gold completa
+
SilverLoadResult.mode = NOOP
```

ou quando o escopo incremental calculado fica vazio.

Resultado:

```text
GoldLoadResult.mode
=
NOOP
```

com:

```text
rows_written = 0
```

---

# 167. Criar `build_noop_result`

Foi adicionada:

```python
build_noop_result(...)
```

## O que?

A função cria de forma centralizada um:

```text
GoldLoadResult
```

sem alterações.

Ela mantém:

```text
affected_event_dates
affected_rejection_dates
affected_quality_dates
```

normalizados, mas retorna:

```text
affected_devices = ()

todos rows_written = 0
```

## Para que?

Evitar repetir a construção do resultado NOOP em vários pontos do service.

---

# 168. Implementar recuperação automática de Gold incompleta

Foi criada a regra:

```text
Silver NOOP
+
Gold incompleta
≠
Gold NOOP
```

Neste caso:

```text
Gold
→ FULL
```

## Exemplo

Estado:

```text
Silver
├── telemetry_events      existe
├── identity_events       existe
└── rejected_logs         existe

Gold
├── dim_device            existe
├── last_position         existe
├── route_points          AUSENTE
├── daily_summary         existe
└── quality_summary       existe
```

Mesmo que:

```text
SilverLoadResult.mode = NOOP
```

o service detecta:

```text
Gold incompleta
```

e executa:

```text
FULL rebuild
```

## Para que?

Permitir autorrecuperação da camada Gold a partir da Silver persistida.

---

# 169. Criar interface Gold baseada em `Settings`

Foi adicionada:

```python
load_gold(
    settings,
    silver_result=...,
)
```

Ela delega para:

```python
load_gold_data(
    silver_dir=settings.silver_dir,
    gold_dir=settings.gold_dir,
    silver_result=silver_result,
)
```

## Para que?

Manter duas formas de uso.

### Interna e testes

```python
load_gold_data(
    silver_dir=...,
    gold_dir=...,
)
```

### Aplicação

```python
load_gold(settings)
```

Isso mantém os caminhos centralizados em:

```text
config/settings.py
```

---

# 170. Adicionar testes de integração do service Gold

Foi expandido:

```text
tests/integration/test_gold_service.py
```

O arquivo cria Delta Tables Silver reais para testar a Gold de ponta a ponta.

Os cenários cobertos incluem:

```text
FULL inicial

NOOP quando Silver não mudou

incremental por data afetada

late-arriving data

incremental somente da partição unknown

recuperação de Gold incompleta

erro quando fontes Silver estão ausentes

execução usando Settings
```

---

# 171. Validar late-arriving data na Gold

Um dos testes adiciona posteriormente uma nova telemetria para uma data antiga.

Exemplo:

```text
Gold existente

17/08
18/08
```

Depois chega:

```text
nova telemetria
17/08 12:00
```

O resultado esperado é:

```text
17/08
→ reconstruído

18/08
→ preservado
```

O teste verifica isso em:

```text
device_route_points
device_daily_summary
```

## Para que?

Confirmar que:

```text
incremental
```

não significa:

```text
processar somente as novas linhas
```

mas:

```text
descobrir escopo afetado
        ↓
reconstruir o estado correto desse escopo
```

---

# 172. Validar atualização exclusiva de `unknown`

Foi adicionado um teste específico para:

```text
rejected_logs
rejection_date = unknown
```

Nesse cenário:

```text
affected_event_dates = ()

affected_rejection_dates =
("unknown",)

affected_devices = ()

quality_dates =
("unknown",)
```

O comportamento validado é:

```text
dim_device_rows_written = 0

last_position_rows_written = 0

route_points_rows_written = 0

daily_summary_rows_written = 0

quality_summary_rows_written = 1
```

## Para que?

Confirmar que uma alteração puramente de qualidade não provoca processamento operacional desnecessário.

---

# 173. Validar recuperação quando uma tabela Gold desaparece

Foi adicionado um teste que:

```text
1. cria toda a Gold
2. remove device_route_points
3. informa Silver NOOP
4. executa a Gold novamente
```

O resultado esperado é:

```text
mode = FULL
```

e todas as cinco tabelas devem existir novamente.

## Para que?

Validar a regra:

```text
NOOP da fonte
≠
camada destino saudável
```

---

# 174. Validar ausência das fontes Silver

Também foi adicionado um teste em que:

```text
02_silver/
```

existe, mas suas Delta Tables não.

A chamada:

```python
load_gold_data(...)
```

deve lançar:

```text
FileNotFoundError
```

## Para que?

Impedir que a Gold seja criada silenciosamente sem fontes válidas.

---

# 175. Validar execução Gold através de `Settings`

Foi criado um teste que monta:

```python
Settings(...)
```

com diretórios temporários.

Depois executa:

```python
load_gold(settings)
```

e confirma a criação de:

```text
dim_device
device_last_position
device_route_points
device_daily_summary
data_quality_summary
```

## Para que?

Validar não apenas:

```text
load_gold_data()
```

mas também a interface pública que será utilizada pelo futuro pipeline.

---

# 176. Estado atual da camada Gold

A camada Gold possui agora:

```text
src/
└── queo_data_platform/
    │
    ├── contracts/
    │   └── gold.py
    │
    └── gold/
        ├── __init__.py
        ├── base.py
        ├── dim_device.py
        ├── last_position.py
        ├── route_points.py
        ├── daily_summary.py
        ├── quality_summary.py
        ├── incremental.py
        ├── writer.py
        └── service.py
```

O fluxo completo é:

```text
Silver Delta Tables
        │
        ▼
register_silver_sources
        │
        ▼
DuckDB
        │
        ▼
Gold base views
        │
        ├── telemetry_gold_base
        └── identity_gold_base
        │
        ▼
Gold scope
        │
        ├── event_dates
        ├── rejection_dates
        ├── quality_dates
        └── affected_devices
        │
        ▼
Gold builders
        │
        ├── dim_device
        ├── device_last_position
        ├── device_route_points
        ├── device_daily_summary
        └── data_quality_summary
        │
        ▼
Gold schemas
        │
        ▼
Gold writer
        │
        ├── entity MERGE
        └── partition replace
        │
        ▼
Delta Lake
        │
        ▼
GoldLoadResult
```

---

# 177. Situação atual das três camadas do Lakehouse

O projeto chegou ao seguinte estado:

```text
                         QUEO DATA PLATFORM

Raw
 │
 ▼
Bronze                                      ✅
 │
 ├── múltiplos arquivos
 ├── validação
 ├── quarantine
 ├── archive
 ├── hash
 ├── lineage
 ├── tabela de controle
 ├── MERGE insert-only
 ├── idempotência
 └── BronzeLoadResult
 │
 ▼
Silver                                      ✅
 │
 ├── normalization
 ├── classification
 ├── transformation
 ├── explicit schemas
 ├── telemetry_events
 ├── device_identity_events
 ├── rejected_logs
 ├── Delta writer
 ├── affected partitions
 ├── late-arriving
 ├── FULL
 ├── INCREMENTAL
 ├── NOOP
 └── SilverLoadResult
 │
 ▼
Gold                                        ✅
 │
 ├── explicit schemas
 ├── deduplicated base views
 │
 ├── dim_device
 ├── device_last_position
 ├── device_route_points
 ├── device_daily_summary
 ├── data_quality_summary
 │
 ├── incremental scope
 ├── affected devices
 ├── quality dates
 │
 ├── MERGE de entidades
 ├── selective partition overwrite
 ├── empty partition cleanup
 │
 ├── FULL
 ├── INCREMENTAL
 ├── NOOP
 ├── recovery rebuild
 └── GoldLoadResult
 │
 ▼
Pipeline                                    ⏳
 │
 ▼
Query Layer                                 ⏳
 │
 ├── REST API                               ⏳
 └── MCP                                    ⏳
```

---

# 178. Separação de responsabilidades atingida na Gold

A implementação final não concentra tudo em um único arquivo.

A responsabilidade ficou:

```text
contracts/gold.py
→ estrutura física dos produtos

gold/base.py
→ relações deduplicadas compartilhadas

gold/dim_device.py
→ transformação da dimensão

gold/last_position.py
→ transformação da última posição

gold/route_points.py
→ transformação da rota

gold/daily_summary.py
→ agregação diária

gold/quality_summary.py
→ métricas de qualidade

gold/incremental.py
→ descoberta do escopo afetado

gold/writer.py
→ persistência Delta

gold/service.py
→ orquestração
```

## Para que?

Evitar uma estrutura como:

```text
gold.py
├── transformação
├── SQL
├── Delta
├── incrementalidade
├── paths
├── orchestration
└── regras de recovery
```

em um único módulo.

A arquitetura atual permite testar cada responsabilidade isoladamente.

---

# 179. Contratos de resultado entre as camadas

Neste ponto, cada camada possui um objeto que descreve sua execução.

```text
Bronze
   ↓
BronzeLoadResult

Silver
   ↓
SilverLoadResult

Gold
   ↓
GoldLoadResult
```

## Bronze

Informa principalmente:

```text
arquivos descobertos
arquivos processados
linhas inseridas
batch_ids
```

## Silver

Informa:

```text
mode
batch_ids
affected_event_dates
affected_rejection_dates
rows_written
```

## Gold

Informa:

```text
mode
affected_event_dates
affected_rejection_dates
affected_quality_dates
affected_devices
rows_written por produto
```

## Para que?

Esses objetos formam a interface natural para o próximo componente:

```text
pipeline
```

Em vez de uma camada depender internamente da implementação da anterior:

```text
pipeline
   ↓
resultados explícitos
   ↓
próxima camada
```

---

# 180. Próximo problema antes da criação do pipeline

Embora Bronze, Silver e Gold já estejam implementadas individualmente, existe uma diferença semântica importante que precisa ser resolvida antes do pipeline.

Atualmente a Silver recebe:

```python
batch_ids = None
```

ou:

```python
batch_ids = ...
```

A lógica atual considera:

```python
requested_incremental = bool(normalized_batch_ids)
```

Portanto:

```text
batch_ids = ()
```

produz:

```text
requested_incremental = False
        ↓
FULL
```

## Por que isso se torna um problema no pipeline?

A Bronze pode executar sem encontrar novos arquivos:

```text
inbox vazio
        ↓
BronzeLoadResult.batch_ids = ()
```

O pipeline naturalmente deverá fazer:

```text
BronzeLoadResult.batch_ids
        ↓
Silver
```

Mas com a regra atual:

```text
nenhum batch novo
        ↓
Silver FULL
```

Isso causaria rebuild completo desnecessário a cada execução vazia.

---

# 181. Semântica desejada para `batch_ids` na Silver

Antes da orquestração ponta a ponta, a Silver deve distinguir:

```text
batch_ids = None
```

de:

```text
batch_ids = ()
```

A semântica desejada é:

```text
batch_ids=None
        ↓
FULL explícito
```

enquanto:

```text
batch_ids=()
+
Silver completa
        ↓
NOOP
```

Se:

```text
batch_ids=()
+
Silver incompleta
```

o comportamento deve continuar sendo:

```text
FULL
```

para permitir recuperação.

Assim:

```text
None
→ quero rebuild completo

()
→ não existe novo batch

("batch-x",)
→ existem novos batches
```

---

# 182. Próximo passo recomendado — preparar Silver para o pipeline

O próximo passo deve alterar a decisão inicial de:

```python
load_silver_data(...)
```

para separar:

```text
rebuild explícito
incremental
nenhum batch novo
recovery
```

A regra esperada é:

```text
batch_ids is None
        ↓
FULL
```

```text
batch_ids == ()
+
Silver completa
        ↓
NOOP
```

```text
batch_ids == ()
+
Silver incompleta
        ↓
FULL
```

```text
batch_ids possui valores
+
Silver completa
        ↓
INCREMENTAL
```

```text
batch_ids possui valores
+
Silver incompleta
        ↓
FULL
```

Um teste de integração deverá fixar especificamente:

```text
Silver já existe
+
batch_ids=()
        ↓
SilverLoadResult.mode = NOOP
```

---

# 183. Pipeline planejado

Depois do ajuste anterior, poderá ser criado:

```text
src/
└── queo_data_platform/
    └── pipeline/
        └── service.py
```

A responsabilidade planejada é pequena:

```text
load_bronze(settings)
        ↓
BronzeLoadResult
        │
        └── batch_ids
                ↓
load_silver(
    settings,
    batch_ids=...
)
        ↓
SilverLoadResult
        │
        ├── affected_event_dates
        └── affected_rejection_dates
                ↓
load_gold(
    settings,
    silver_result=...
)
        ↓
GoldLoadResult
```

O pipeline não deverá conhecer:

```text
hash de arquivo
schema CSV
DuckDB
Delta MERGE
predicates
regras T1/T2
partições Silver
partições Gold
```

Ele deve apenas coordenar os contratos públicos das camadas.

---

# 184. Resultado esperado da futura orquestração

A execução inicial deverá funcionar assim:

```text
CSV novo
   ↓
Bronze
   ↓
batch_id novo
   ↓
Silver FULL
   ↓
Gold FULL
```

Depois, com outro arquivo:

```text
novo CSV
   ↓
Bronze incremental
   ↓
novo batch_id
   ↓
Silver incremental
   ↓
affected dates
   ↓
Gold incremental
```

E quando não existir nada novo:

```text
inbox vazio
   ↓
Bronze sem novos batches
   ↓
Silver NOOP
   ↓
Gold NOOP
```

Esse será o primeiro fluxo realmente ponta a ponta:

```text
Raw
 ↓
Bronze
 ↓
Silver
 ↓
Gold
```

executado através de uma única interface.

---

# 185. Ponto atual de desenvolvimento

O ponto atual do projeto passa a ser:

```text
Bronze
████████████████████  concluída

Silver
████████████████████  concluída

Gold
████████████████████  concluída

Pipeline
░░░░░░░░░░░░░░░░░░░░  próximo

Query Layer
░░░░░░░░░░░░░░░░░░░░

REST API
░░░░░░░░░░░░░░░░░░░░

MCP
░░░░░░░░░░░░░░░░░░░░
```

Antes de implementar:

```text
pipeline/service.py
```

deve ser concluído o pequeno ajuste semântico da Silver relacionado a:

```text
batch_ids=()
```

Depois disso:

```text
BronzeLoadResult
        ↓
SilverLoadResult
        ↓
GoldLoadResult
        ↓
PipelineResult
```

passará a formar a cadeia completa de processamento da plataforma.

Esse é o ponto exato para retomada do desenvolvimento.
````

[1]: https://github.com/Zuimbra/queo-data-platform/tree/main/src/queo_data_platform/pipeline "queo-data-platform/src/queo_data_platform/pipeline at main · Zuimbra/queo-data-platform · GitHub"
