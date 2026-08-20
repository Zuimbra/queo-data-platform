# QUEO Data Platform

Uma plataforma de dados para ingestão, processamento, consolidação e exposição de dados de rastreadores, construída sobre uma arquitetura Lakehouse em camadas.

A QUEO Data Platform transforma arquivos brutos recebidos dos dispositivos em dados rastreáveis, normalizados e prontos para consumo por aplicações, dashboards, integrações e outros serviços.

O projeto foi desenhado para resolver um problema que vai além de simplesmente "ler um CSV": dados reais podem chegar duplicados, atrasados, incompletos ou com diferenças entre versões de protocolo. Por isso, cada etapa da plataforma possui uma responsabilidade específica, preservando o dado original antes de interpretá-lo e mantendo rastreabilidade até a origem.

```text
CSV
 ↓
Raw
 ↓
Bronze
 ↓
Silver
 ↓
Gold
 ↓
Query Layer
 ↓
REST API
 ↓
Consumidores
```

---

## O que a plataforma faz

A plataforma recebe arquivos CSV contendo mensagens produzidas por rastreadores e executa todo o ciclo de tratamento dos dados:

```text
receber
  ↓
validar
  ↓
preservar
  ↓
normalizar
  ↓
resolver identidade
  ↓
classificar
  ↓
consolidar
  ↓
consultar
  ↓
expor
```

Entre as capacidades atualmente implementadas estão:

- ingestão de múltiplos arquivos;
- idempotência por hash e por linha;
- lineage completo da origem;
- tabela de controle de ingestão;
- archive e quarantine;
- processamento `FULL`, `INCREMENTAL` e `NOOP`;
- tratamento de dados atrasados;
- resolução de identidade de dispositivos;
- preservação de registros rejeitados;
- produtos analíticos Gold;
- consultas paginadas;
- REST API read-only;
- configuração por ambiente;
- testes unitários, de integração e HTTP.

---

# Arquitetura

A arquitetura segue uma separação clara de responsabilidades.

```text
┌─────────────────────────────────────────────────────────────┐
│                         RAW                                 │
│                                                             │
│          inbox / archive / quarantine                       │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                       BRONZE                                │
│                                                             │
│  preservação • lineage • SHA-256 • idempotência            │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                       SILVER                                │
│                                                             │
│  normalização • identidade • classificação • qualidade     │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                         GOLD                                │
│                                                             │
│  dispositivos • posição • rota • resumo • qualidade        │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                     QUERY LAYER                             │
│                                                             │
│        filtros • ordenação • paginação • consultas         │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                       REST API                              │
│                                                             │
│                 HTTP / JSON / FastAPI                       │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
                 aplicações e integrações
```

A regra arquitetural principal é:

```text
Bronze
→ preserva

Silver
→ interpreta

Gold
→ consolida

Query Layer
→ consulta

REST API
→ expõe
```

Cada camada evita conhecer detalhes que pertencem à próxima.

---

# Fluxo de dados

## Raw

Arquivos novos entram em:

```text
data/raw/inbox/
```

Depois do processamento:

```text
sucesso
→ archive

arquivo já processado
→ archive

falha de ingestão
→ quarantine
```

---

## Bronze

A Bronze preserva os registros recebidos e adiciona metadados técnicos.

```text
tracker_logs
```

Cada linha recebe:

```text
source_file
source_file_hash
source_row_number
row_id
batch_id
ingested_at
ingestion_date
```

O `row_id` é determinístico:

```text
hash do arquivo
+
posição da linha
        ↓
row_id
```

Isso permite reprocessar um arquivo sem duplicar linhas já existentes.

---

## Silver

A Silver interpreta os registros Bronze e os separa em três produtos:

```text
telemetry_events

device_identity_events

rejected_logs
```

O fluxo interno é:

```text
Bronze
 ↓
normalização
 ↓
resolução de identidade
 ↓
classificação
 ↓
transformação
 ↓
Silver
```

Mensagens `T1` representam eventos de identidade.

Outras mensagens válidas `T<n>` representam telemetria.

Registros que não atendem aos requisitos mínimos não são descartados:

```text
rejected_logs
```

preserva o registro e seu motivo de rejeição.

---

## Gold

A Gold transforma os eventos Silver em produtos orientados a consumo.

### `dim_device`

Visão consolidada dos dispositivos conhecidos.

```text
1 linha
=
1 dispositivo
```

### `device_last_position`

Última posição publicável conhecida de cada dispositivo.

### `device_route_points`

Histórico ordenado dos pontos de rota.

### `device_daily_summary`

Resumo operacional diário por dispositivo.

### `data_quality_summary`

Métricas de aceitação e rejeição dos dados processados.

---

# Processamento incremental

A plataforma não reconstrói todo o Lakehouse a cada execução.

Silver e Gold trabalham com três modos:

```text
FULL
INCREMENTAL
NOOP
```

## FULL

Reconstrói integralmente a camada.

Utilizado em situações como:

```text
primeira construção
mudança incompatível de schema
rebuild explícito
recuperação de estado incompleto
```

## INCREMENTAL

Quando novos dados chegam:

```text
novo batch
 ↓
descobrir datas afetadas
 ↓
reprocessar apenas o escopo necessário
```

A plataforma também suporta dados atrasados.

Se hoje chegar um evento pertencente a uma data histórica:

```text
novo evento antigo
        ↓
partição histórica afetada
        ↓
partição reconstruída
```

## NOOP

Quando não existe nada novo para processar:

```text
inbox vazio
        ↓
Bronze sem batches
        ↓
Silver NOOP
        ↓
Gold NOOP
```

Uma execução ociosa não provoca rebuild completo.

---

# Resolução de identidade

Nem todos os registros históricos possuem o serial do dispositivo diretamente.

Por isso a Silver possui uma etapa dedicada de resolução de identidade.

Os resultados possíveis são:

```text
DIRECT
LEGACY_IMEI
UNRESOLVED
```

### `DIRECT`

O dispositivo pôde ser identificado diretamente pelo próprio registro.

### `LEGACY_IMEI`

A identidade foi inferida a partir de evidências históricas inequívocas envolvendo IMEI.

### `UNRESOLVED`

Não existe evidência suficiente para atribuir uma identidade com segurança.

O princípio é:

```text
não adivinhar identidade
```

Uma inferência só é realizada quando as regras de consistência são satisfeitas.

A investigação e a implementação do protocolo legado estão documentadas em:

[`docs/reports/DIAGNOSTICO_PROTOCOLO_LEGADO_E_RESOLUCAO_IDENTIDADE.md`](docs/reports/DIAGNOSTICO_PROTOCOLO_LEGADO_E_RESOLUCAO_IDENTIDADE.md)

---

# Query Layer

A Gold não é acessada diretamente pelos consumidores.

Existe uma camada read-only intermediária:

```text
QueryService
```

O fluxo interno é:

```text
QueryService
 ↓
Delta Lake
 ↓
PyArrow Dataset
 ↓
DuckDB
 ↓
resultado
```

A Query Layer centraliza:

```text
filtros
ordenação
paginação
COUNT
validação de parâmetros
```

Dessa forma, consumidores não precisam conhecer:

```text
Delta Lake
DuckDB
partições
paths físicos
```

---

# REST API

A plataforma expõe uma REST API read-only construída com FastAPI.

Fluxo:

```text
HTTP
 ↓
FastAPI
 ↓
QueryService
 ↓
Gold
```

A API não consulta Bronze, Silver ou Delta Lake diretamente.

Principais endpoints:

```text
GET /health

GET /api/v1/devices

GET /api/v1/devices/{device_serial}

GET /api/v1/devices/{device_serial}/last-position

GET /api/v1/devices/{device_serial}/route

GET /api/v1/daily-summaries

GET /api/v1/data-quality
```

A documentação completa está em:

[`docs/API.md`](docs/API.md)

---

# Integração com MCP

Quando um serviço MCP externo precisa consumir a plataforma, a arquitetura recomendada é:

```text
QUEO Data Platform
        │
        ▼
    REST API
        │
        │ HTTP / JSON
        ▼
   MCP Service
        │
        ▼
    MCP Tools
        │
        ▼
   LLM / Client
```

O MCP não precisa acessar diretamente:

```text
Delta Lake
DuckDB
Gold filesystem
```

A REST API funciona como contrato entre os serviços.

Mais detalhes:

[`docs/MCP_INTEGRATION.md`](docs/MCP_INTEGRATION.md)

---

# Estrutura do projeto

```text
.
├── docs/
│
├── src/
│   └── queo_data_platform/
│       ├── api/
│       ├── bronze/
│       ├── config/
│       ├── contracts/
│       ├── gold/
│       ├── infrastructure/
│       ├── pipeline/
│       ├── query/
│       └── silver/
│
├── tests/
│   ├── api/
│   ├── integration/
│   └── unit/
│
├── README.md
├── STEPSREPORT.md
├── pyproject.toml
└── uv.lock
```

---

# Tecnologias

O projeto utiliza principalmente:

| Tecnologia | Uso |
|---|---|
| Python 3.14 | linguagem principal |
| uv | dependências e ambiente |
| Delta Lake | persistência Lakehouse |
| PyArrow | schemas e integração columnar |
| DuckDB | transformação e consultas |
| Pandas | manipulação tabular |
| FastAPI | REST API |
| Pydantic | contratos HTTP |
| Uvicorn | servidor ASGI |
| Pytest | testes |
| Ruff | lint e formatação |
| Pyright | análise estática de tipos |

---

# Quickstart

## 1. Instale as dependências

Na raiz do projeto:

```powershell
uv sync
```

---

## 2. Adicione arquivos ao inbox

```text
data/
└── raw/
    └── inbox/
        └── arquivo.csv
```

---

## 3. Execute o pipeline

```powershell
uv run queo-data-platform
```

Também é possível:

```powershell
uv run python -m queo_data_platform
```

O pipeline executará:

```text
Bronze
 ↓
Silver
 ↓
Gold
```

---

## 4. Observe o resultado

Exemplo:

```text
[BRONZE]
  discovered_files=1
  successful_files=1
  inserted_rows=100

[SILVER]
  mode=INCREMENTAL
  telemetry_rows=...
  identity_rows=...
  rejected_rows=...

[GOLD]
  mode=INCREMENTAL
  affected_devices=...

[PIPELINE] has_new_data=True
[PIPELINE] has_changes=True
```

---

# Executar a API

Inicie:

```powershell
uv run uvicorn queo_data_platform.api.app:app --reload
```

A API ficará disponível por padrão em:

```text
http://127.0.0.1:8000
```

Health check:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/health"
```

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

OpenAPI:

```text
http://127.0.0.1:8000/openapi.json
```

---

# Exemplo de consulta

Listar dispositivos:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/devices?limit=5" |
    ConvertTo-Json -Depth 6
```

Consultar a última posição:

```powershell
Invoke-RestMethod `
    "http://127.0.0.1:8000/api/v1/devices/202527000021P/last-position" |
    ConvertTo-Json -Depth 6
```

---

# Configuração

## Diretório de dados

Por padrão:

```text
<project_root>/data
```

Para utilizar outro diretório:

```powershell
$env:QUEO_DATA_DIR="D:\queo-data"
```

---

## CORS

Por padrão, nenhuma origem externa é adicionada.

Para autorizar uma aplicação local:

```powershell
$env:QUEO_API_CORS_ORIGINS="http://localhost:5173"
```

Múltiplas origens:

```powershell
$env:QUEO_API_CORS_ORIGINS="http://localhost:5173,https://app.example.com"
```

---

# Testes e qualidade

Execute a suíte completa:

```powershell
uv run pytest
```

Quality gate recomendado:

```powershell
uv run ruff format .
uv run ruff check .
uv run pyright
uv run pytest
```

Testes estão divididos em:

```text
tests/unit/
→ regras isoladas

tests/integration/
→ colaboração entre camadas e Delta real

tests/api/
→ contratos HTTP
```

Mais detalhes:

[`docs/TESTES.md`](docs/TESTES.md)

---

# Documentação

A documentação foi separada por responsabilidade para que o README permaneça como ponto de entrada do projeto.

| Documento | Conteúdo |
|---|---|
| [Arquitetura](docs/ARQUITETURA.md) | organização das camadas, responsabilidades e fluxo do sistema |
| [Regras de negócio](docs/REGRAS_DE_NEGOCIO.md) | decisões e comportamentos implementados |
| [Contratos de dados](docs/CONTRATOS_DE_DADOS.md) | tabelas, schemas, granularidade e campos |
| [Testes](docs/TESTES.md) | estratégia, cobertura e execução da suíte |
| [Operação](docs/OPERACAO.md) | runbook para execução, diagnóstico e recuperação |
| [REST API](docs/API.md) | endpoints, filtros, paginação, configuração e erros |
| [Integração MCP](docs/MCP_INTEGRATION.md) | consumo externo da plataforma por um serviço MCP |
| [Diagnóstico do protocolo legado](docs/reports/DIAGNOSTICO_PROTOCOLO_LEGADO_E_RESOLUCAO_IDENTIDADE.md) | investigação e resolução de identidade histórica |
| [STEPSREPORT](STEPSREPORT.md) | histórico detalhado da construção e das decisões do projeto |

---

# Princípios do projeto

A arquitetura foi desenvolvida em torno de alguns princípios.

### Preservar antes de interpretar

```text
Raw
 ↓
Bronze
 ↓
Silver
```

Dados não devem ser descartados simplesmente porque ainda não podem ser interpretados.

### Rejeição é dado

```text
rejected_logs
```

faz parte da plataforma e permite medir a qualidade do tráfego recebido.

### Não inferir sem evidência

A resolução de identidade prefere:

```text
UNRESOLVED
```

a atribuir um dispositivo incorretamente.

### Incrementalidade sem perder consistência

```text
batch
→ identifica escopo

partição
→ é reconstruída de forma consistente
```

### Produtos derivados devem ser reproduzíveis

```text
Bronze
→ reconstrói Silver

Silver
→ reconstrói Gold
```

O estado derivado não deve depender de correções manuais.

### Consumidores não conhecem o armazenamento

```text
Gold
 ↓
Query Layer
 ↓
REST API
 ↓
consumidor
```

Isso mantém baixo acoplamento entre processamento e consumo.

---

# Estado atual

```text
Raw / ingestão               ✅

Bronze                       ✅
├── múltiplos arquivos
├── lineage
├── controle de ingestão
└── idempotência

Silver                       ✅
├── normalização
├── resolução de identidade
├── classificação
├── rejeições
├── FULL
├── INCREMENTAL
└── NOOP

Gold                         ✅
├── dim_device
├── device_last_position
├── device_route_points
├── device_daily_summary
└── data_quality_summary

Pipeline                     ✅

Query Layer                  ✅

REST API read-only           ✅

Testes automatizados         ✅

Integração MCP externa       ↗ via REST API
```

---

# Fluxo resumido

```text
arquivo CSV
    ↓
raw/inbox
    ↓
validação estrutural
    ↓
Bronze
preservação + lineage
    ↓
Silver
normalização + identidade + classificação
    ↓
             ┌──────────── telemetry
             │
             ├──────────── identity
             │
             └──────────── rejected
                           ↓
                          Gold
                           ↓
              produtos para consumo
                           ↓
                     QueryService
                           ↓
                       REST API
                           ↓
             aplicações / integrações
```

A ideia central da plataforma pode ser resumida em:

> **preservar o dado bruto, transformar com regras explícitas e expor apenas produtos estáveis para consumo.**