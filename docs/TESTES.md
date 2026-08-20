# Testes — QUEO Data Platform

# 1. Objetivo

Este documento descreve a estratégia de testes da QUEO Data Platform.

O objetivo da suíte não é apenas verificar se funções Python retornam valores esperados.

O sistema trabalha com:

```text
arquivos CSV
Delta Lake
DuckDB
PyArrow
Pandas
processamento incremental
partições
contratos de schema
API HTTP
```

Por isso a estratégia de testes precisa validar diferentes níveis do sistema.

A estrutura atual é:

```text
tests/
│
├── unit/
│
├── integration/
│
└── api/
```

Cada grupo responde a um tipo diferente de pergunta:

```text
unit
→ a regra isolada funciona?

integration
→ as camadas funcionam juntas com persistência real?

api
→ o contrato HTTP funciona do ponto de vista do consumidor?
```

---

# 2. Filosofia geral dos testes

A plataforma segue quatro princípios principais.

## 2.1. Regra de negócio deve possuir teste próximo da implementação

Exemplo:

```text
T1
→ identidade
```

deve ser protegido em:

```text
test_silver_classification.py
```

Enquanto:

```text
V14.06.111
+
IMEI inequívoco
→ LEGACY_IMEI
```

deve ser protegido em:

```text
test_silver_identity_resolution.py
```

---

## 2.2. Persistência importante é testada com Delta real

Para componentes como:

```text
Bronze writer
Silver writer
Gold writer
Query Layer
services de integração
```

não é suficiente simular a persistência.

Os testes criam tabelas Delta reais em diretórios temporários.

O padrão é:

```text
tmp_path
   ↓
Delta Table temporária
   ↓
execução da função real
   ↓
leitura da Delta
   ↓
assert
```

Isso permite testar comportamento real de:

```text
MERGE
overwrite
particionamento
schema
idempotência
rebuild seletivo
```

---

## 2.3. Testes não devem depender do Lakehouse local do desenvolvedor

A suíte automatizada não deve depender de:

```text
data/
```

existente na máquina.

Cada teste deve produzir seu próprio estado quando necessário.

Isso evita:

```text
teste passando em uma máquina
e falhando em outra
```

por causa de dados locais diferentes.

---

## 2.4. FULL, INCREMENTAL e NOOP precisam ser testados separadamente

Esses modos possuem semânticas diferentes.

Portanto não basta testar apenas:

```text
processamento com dados
```

Também é necessário testar:

```text
FULL
INCREMENTAL
NOOP
recovery FULL
late-arriving
bootstrap vazio
```

---

# 3. Ferramentas utilizadas

A suíte utiliza:

```text
pytest
```

para execução dos testes.

Também fazem parte do quality gate:

```text
ruff
pyright
```

O ambiente de testes HTTP utiliza:

```text
FastAPI TestClient
httpx2
```

A persistência real dos testes utiliza as mesmas bibliotecas da aplicação:

```text
deltalake
duckdb
pandas
pyarrow
```

---

# 4. Estrutura atual da suíte

A estrutura conceitual é:

```text
tests/
│
├── unit/
│   │
│   ├── Bronze
│   ├── Silver
│   ├── Gold
│   ├── Query Layer
│   ├── Settings
│   ├── API Settings
│   └── CLI
│
├── integration/
│   │
│   ├── Bronze Service
│   ├── Silver Service
│   ├── Gold Service
│   └── Pipeline
│
└── api/
    │
    ├── endpoints básicos
    └── analytics / quality / CORS
```

Na coleta atualmente conhecida, a suíte possui:

```text
Unit tests          184
Integration tests    27
API tests            11
────────────────────────
Total               222
```

O número exato deve sempre ser confirmado pela execução atual de:

```powershell
uv run pytest
```

e não tratado como uma constante permanente do projeto.

---

# 5. Testes unitários da Bronze

# `test_bronze_files.py`

Valida operações físicas relacionadas aos arquivos de entrada.

Responsabilidades principais:

```text
descoberta de CSVs
ordenação dos arquivos
hash SHA-256
movimentação de arquivos
tratamento de conflitos
```

Esses testes protegem o fluxo:

```text
inbox
 ↓
discovery
 ↓
hash
 ↓
archive / quarantine
```

---

# `test_bronze_validation.py`

Valida o contrato estrutural dos arquivos.

Cobre regras como:

```text
arquivo válido
arquivo vazio
CSV sem linhas
colunas obrigatórias
colunas reservadas
colunas extras
normalização de nomes
```

O objetivo é garantir a separação:

```text
Bronze
→ valida estrutura

Silver
→ valida semântica
```

Um timestamp ruim, por exemplo, não deve fazer esse teste considerar o CSV estruturalmente inválido se o contrato do arquivo estiver correto.

---

# `test_bronze_lineage.py`

Protege a linhagem adicionada durante a ingestão.

São verificadas regras relacionadas a:

```text
batch_id
source_file
source_file_hash
source_row_number
row_id
ingested_at
ingestion_date
UTC
```

Um dos pontos mais importantes é:

```text
row_id determinístico
```

O teste comprova que:

```text
mesmo hash
+
mesma posição da linha
        ↓
mesmo row_id
```

e que linhas diferentes produzem IDs diferentes.

---

# `test_bronze_control.py`

Testa a tabela de controle da ingestão.

Protege operações relacionadas a:

```text
PROCESSING
SUCCESS
FAILED
SKIPPED
```

e à identificação de arquivos que já foram processados com sucesso.

O comportamento principal protegido é:

```text
source_file_hash já possui SUCCESS
        ↓
arquivo não deve ser processado novamente
```

---

# `test_bronze_writer.py`

Valida a persistência real da Bronze.

Cobre:

```text
criação da primeira Delta Table
MERGE
idempotência
row_id duplicado
linhas novas
schema alignment
evolução de schema
```

Um cenário fundamental é:

```text
execução 1
row A
row B
        ↓
2 inserts

execução 2
row A
row B
        ↓
0 inserts
2 duplicates
```

Outro cenário verifica:

```text
row A já existe
row C é nova
        ↓
somente C é inserida
```

---

# 6. Testes unitários da Silver

# `test_silver_normalization.py`

Valida a transformação inicial:

```text
Bronze
 ↓
representação normalizada Silver
```

Cobre:

```text
renomeação de campos
TRIM
string vazia → NULL
TRY_CAST de timestamps
preservação de lineage
contrato mínimo Bronze
```

Também protege a prioridade temporal:

```text
device_timestamp
```

e:

```text
server_timestamp
```

para etapas posteriores.

---

# `test_silver_identity_resolution.py`

É um dos conjuntos de testes mais importantes do sistema.

Protege a resolução de:

```text
device_serial
```

e:

```text
device_resolution_method
```

Cobre os métodos:

```text
DIRECT
LEGACY_IMEI
UNRESOLVED
```

Entre os cenários protegidos estão:

```text
serial direto
remoção do prefixo M
IMEI válido
IMEI inválido
IMEI ambíguo
IMEI → serial inequívoco
conflito de identidades
evidência histórica
```

Também existem testes específicos para o protocolo legado:

```text
V14.06.111
```

e para a utilização de T1 contextual de outra versão.

Um cenário crítico é:

```text
T1 V14.06.117
+
IMEI conhecido
+
mesmo source_file

        ↓

T2 V14.06.111

        ↓

LEGACY_IMEI
```

Ao mesmo tempo, outro teste protege:

```text
T2 V14.06.117
```

contra inferência indevida:

```text
→ UNRESOLVED
```

Isso garante que:

```text
a origem da evidência pode ser cross-protocol
```

mas:

```text
a elegibilidade do alvo continua restrita
```

---

# `test_silver_classification.py`

Valida a decisão:

```text
telemetry
identity
rejected
```

A principal árvore protegida é:

```text
message_type ausente
→ MISSING_MESSAGE_TYPE

message_type inválido
→ INVALID_MESSAGE_TYPE

timestamp ausente
→ MISSING_OR_INVALID_TIMESTAMP

device_serial ausente
→ MISSING_DEVICE_SERIAL

T1 válido
→ identity

T<n> válido, exceto T1
→ telemetry
```

Também existe proteção para a precedência dos motivos de rejeição.

Isso é importante porque uma linha pode possuir mais de um problema, mas recebe apenas:

```text
um rejection_reason principal
```

---

# `test_silver_transformation.py`

Testa a tipagem dos produtos Silver.

Para telemetria, protege conversões como:

```text
latitude
longitude
speed
battery
odometer
HDOP
temperaturas
serial_count
```

Também cobre:

```text
has_valid_coordinates
position_quality
```

incluindo:

```text
MISSING_COORDINATES
INVALID_COORDINATES
LOW_GPS_PRECISION
VALID
```

Para identidade, protege:

```text
ICCID
IMSI
IMEI
```

e seus indicadores de formato.

Também garante que:

```text
device_serial
device_resolution_method
```

já resolvidos sejam preservados e não recalculados pela transformação.

---

# `test_silver_contracts.py`

Protege os schemas PyArrow oficiais da Silver.

Entre os campos protegidos está:

```text
device_resolution_method
```

nos produtos:

```text
telemetry_events
device_identity_events
rejected_logs
```

Esse tipo de teste evita que uma alteração aparentemente simples no código mude silenciosamente o contrato físico das Delta Tables.

---

# `test_silver_incremental.py`

Valida a descoberta do escopo incremental.

Protege regras como:

```text
normalização de batch_ids
descoberta de event_dates
descoberta de rejection_dates
unknown
batch inexistente
late-arriving
```

A regra fundamental testada é:

```text
batch_id
→ descobre partição afetada
```

mas depois:

```text
partição inteira
→ reconstruída
```

e não apenas as linhas do batch.

---

# `test_silver_writer.py`

Valida a persistência dos produtos Silver.

Cobre:

```text
FULL overwrite
incremental partition replacement
schema explícito
partições vazias
substituição seletiva
```

O objetivo é proteger a atomicidade lógica:

```text
partição antiga
        ↓
recalcular estado completo
        ↓
substituir partição
```

---

# 7. Testes unitários da Gold

# `test_gold_contracts.py`

Protege os schemas físicos dos cinco produtos Gold:

```text
dim_device
device_last_position
device_route_points
device_daily_summary
data_quality_summary
```

Esse arquivo funciona como proteção contra mudanças acidentais de:

```text
nome de coluna
tipo
partição
contrato
```

---

# `test_gold_dim_device.py`

Valida a construção da dimensão de dispositivos.

Cobre situações como:

```text
dispositivo com identidade e telemetria
dispositivo somente com telemetria
identidade mais recente
first_seen_at
last_seen_at
contagem de eventos
affected_devices
```

Também protege a escolha da identidade atual:

```text
current_imei
current_imsi
current_iccid
current_protocol_version
```

---

# `test_gold_last_position.py`

Protege a regra de escolha da última posição.

Cobre:

```text
posição mais recente
coordenadas inválidas
remoção de (0,0)
desempate
affected_devices
preservação das métricas
```

A ordenação protegida é aproximadamente:

```text
event_timestamp DESC
server_timestamp DESC
serial_count DESC
```

---

# `test_gold_route_points.py`

Valida a construção da rota.

Cobre:

```text
coordenadas válidas
remoção de (0,0)
ordenação cronológica
point_sequence
reset diário da sequência
is_moving
filtro por event_dates
```

Um comportamento importante é:

```text
device A
2026-08-19
→ sequence 1, 2, 3

device A
2026-08-20
→ sequence 1, 2...
```

---

# `test_gold_daily_summary.py`

Protege os agregados diários por dispositivo.

Entre os cenários estão:

```text
message_count
message types distintos
posições válidas
posições inválidas
low GPS precision
movimento
parada
velocidade média
velocidade máxima
HDOP
bateria
odômetro
regressão de odômetro
primeira posição
última posição
filtro por event_dates
```

Também protege a regra:

```text
odômetro final < odômetro inicial
        ↓
odometer_delta_raw = NULL
has_odometer_regression = TRUE
```

---

# `test_gold_quality_summary.py`

Valida o produto:

```text
data_quality_summary
```

Cobre:

```text
telemetria aceita
identidade aceita
rejeições
total processado
percentual de rejeição
motivos de rejeição
datas
unknown
metric_dates
```

Um ponto importante é que esse produto usa:

```text
Silver diretamente
```

e não as views deduplicadas utilizadas por outros produtos Gold.

O teste protege essa semântica.

---

# `test_gold_incremental.py`

Protege a propagação do escopo incremental Silver → Gold.

Cobre:

```text
event_dates
rejection_dates
quality_dates
affected_devices
normalização de partições
```

Regra importante:

```text
quality_dates
=
event_dates
UNION
rejection_dates
```

---

# `test_gold_writer.py`

Valida a persistência Gold.

Existem duas estratégias principais:

```text
entity tables
```

e:

```text
partitioned tables
```

Para:

```text
dim_device
device_last_position
```

a escrita trabalha por entidade.

Para:

```text
device_route_points
device_daily_summary
data_quality_summary
```

a persistência trabalha por partição.

Os testes verificam comportamento FULL e incremental dessas estratégias.

---

# 8. Testes unitários da Query Layer

# `test_query_service.py`

Valida as primeiras capacidades públicas de leitura da Gold.

Cobre:

```text
list_devices
get_device
list_last_positions
get_last_position
list_route_points
paginação
filtros
ordenação
Gold inexistente
parâmetros inválidos
```

Os testes utilizam Delta Tables temporárias reais.

Assim o fluxo testado é:

```text
Delta Gold
 ↓
PyArrow Dataset
 ↓
DuckDB
 ↓
QueryService
 ↓
DataFrame
```

---

# `test_query_summary_service.py`

Protege a expansão da Query Layer.

Cobre:

```text
QueryPage
total
returned
has_more
next_offset
daily summaries
data quality
filtros temporais
paginação
COUNT
intervalos inválidos
```

Um cenário importante verifica que:

```text
items
```

representa apenas a página atual enquanto:

```text
total
```

representa todos os registros que atendem aos filtros.

---

# 9. Testes de configuração

# `test_settings.py`

Protege a resolução dos diretórios da plataforma.

Valida:

```text
project_root
data_dir
raw_dir
lakehouse_dir
Bronze
Silver
Gold
```

e o uso de:

```text
QUEO_DATA_DIR
```

quando configurado.

---

# `test_api_settings.py`

Protege:

```text
QUEO_API_CORS_ORIGINS
```

Cobre:

```text
nenhuma origem por padrão
múltiplas origens
remoção de espaços
remoção de duplicatas
```

Também protege a compatibilidade:

```text
Settings(...)
```

sem configuração específica de CORS.

---

# 10. Testes da CLI

# `test_cli.py`

Valida a interface de linha de comando.

O objetivo é garantir que:

```text
CLI
 ↓
load_settings
 ↓
run_pipeline
```

funcione como adaptador do pipeline sem duplicar regras internas.

Também protege a representação dos resultados:

```text
Bronze
Silver
Gold
Pipeline
```

para o usuário do terminal.

---

# 11. Testes de integração

Os testes de integração verificam fluxos envolvendo múltiplos componentes reais.

A principal diferença é:

```text
unit test
→ testa componente/regra específica

integration test
→ testa colaboração entre componentes
```

---

# `integration/test_bronze_service.py`

Exercita:

```text
arquivo
 ↓
discovery
 ↓
hash
 ↓
validation
 ↓
lineage
 ↓
Bronze Delta
 ↓
control table
 ↓
archive/quarantine
```

Cobre cenários como:

```text
ingestão bem-sucedida
arquivo duplicado
arquivo inválido
quarantine
archive
batch propagation
```

O objetivo é garantir que os módulos Bronze isoladamente corretos também funcionem corretamente quando orquestrados pelo:

```python
load_bronze()
```

---

# `integration/test_silver_service.py`

Exercita o fluxo real:

```text
Bronze Delta
 ↓
normalization
 ↓
identity resolution
 ↓
classification
 ↓
transformation
 ↓
Silver Delta
```

Entre os cenários protegidos estão:

```text
FULL
INCREMENTAL
NOOP
batch desconhecido
late-arriving
identity resolution FULL
identity resolution INCREMENTAL
contexto T1 cross-protocol
```

Esses testes são especialmente importantes porque a resolução histórica de identidade precisa funcionar não apenas isoladamente, mas dentro do ciclo real da Silver.

---

# `integration/test_gold_service.py`

Exercita:

```text
Silver real
 ↓
Gold base views
 ↓
builders
 ↓
writer
 ↓
cinco Delta Tables Gold
```

Protege:

```text
FULL
INCREMENTAL
NOOP
recovery FULL
paths vindos de Settings
```

Além de verificar que os cinco produtos Gold são efetivamente persistidos.

---

# `integration/test_pipeline_service.py`

É o teste mais próximo do funcionamento operacional completo.

Valida:

```text
Bronze
 ↓
Silver
 ↓
Gold
```

como uma única execução.

Entre os cenários estão:

```text
pipeline completo
NOOP sem arquivo novo
novo batch incremental
bootstrap vazio
```

O cenário de bootstrap protege:

```text
primeira execução
+
inbox vazio
+
Bronze inexistente
        ↓
Silver NOOP
Gold NOOP
```

Isso garante que um ambiente vazio seja um estado válido e não uma falha.

---

# 12. Testes HTTP

Os testes HTTP ficam separados porque validam um contrato diferente:

```text
JSON / HTTP
```

e não apenas funções Python.

Utilizam:

```text
FastAPI TestClient
```

com substituição da dependência:

```text
get_query_service
```

por um `QueryService` apontando para Gold temporária.

O fluxo é:

```text
Delta Gold temporária
 ↓
QueryService
 ↓
FastAPI
 ↓
TestClient
 ↓
HTTP response
```

---

# `api/test_app.py`

Protege os primeiros endpoints da API.

Cobre:

```text
GET /health

GET /api/v1/devices

GET /api/v1/devices/{device_serial}

GET /api/v1/devices/{device_serial}/last-position

GET /api/v1/devices/{device_serial}/route
```

Também testa:

```text
paginação
404
422
503
Gold ausente
```

---

# `api/test_summary_routes.py`

Protege:

```text
GET /api/v1/daily-summaries
```

e:

```text
GET /api/v1/data-quality
```

Além disso valida:

```text
filtros de data
paginação
intervalo invertido
CORS
```

O teste de CORS verifica que uma origem configurada em:

```text
QUEO_API_CORS_ORIGINS
```

recebe a resposta HTTP apropriada.

---

# 13. Uso de `tmp_path`

`pytest` fornece:

```python
tmp_path
```

para criação de diretórios temporários.

Essa estratégia é utilizada extensivamente para:

```text
CSV temporário
inbox
archive
quarantine
control
Bronze Delta
Silver Delta
Gold Delta
```

Exemplo conceitual:

```text
tmp_path/
│
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

Quando o teste termina, esse ambiente deixa de fazer parte do sistema real.

Isso garante isolamento.

---

# 14. Uso de `monkeypatch`

Configurações dependentes de ambiente são testadas através de:

```python
monkeypatch
```

Exemplos:

```text
QUEO_DATA_DIR
QUEO_API_CORS_ORIGINS
```

O teste pode definir:

```text
variável presente
```

ou:

```text
variável ausente
```

sem modificar permanentemente o ambiente do desenvolvedor.

---

# 15. Dependency Override da FastAPI

Nos testes HTTP não é desejável utilizar:

```text
Gold local real
```

Por isso:

```python
application.dependency_overrides[
    get_query_service
]
```

é utilizado.

O fluxo passa a ser:

```text
API em teste
 ↓
QueryService de teste
 ↓
tmp_path/03_gold
```

Isso mantém o endpoint real e troca apenas a infraestrutura física utilizada pelo teste.

---

# 16. O que não deve ser mockado desnecessariamente

Para este projeto, é importante não transformar toda a suíte em mocks.

Especialmente para:

```text
Delta Lake
partições
MERGE
schema
DuckDB
Query Layer
```

o comportamento real possui valor.

Um mock poderia afirmar:

```text
MERGE funcionou
```

sem testar o Delta Lake.

Por isso componentes de persistência usam, sempre que razoável:

```text
Delta Tables temporárias reais
```

---

# 17. Como executar todos os testes

Na raiz do projeto:

```powershell
uv run pytest
```

Para saída detalhada:

```powershell
uv run pytest -v
```

---

# 18. Executar somente testes unitários

```powershell
uv run pytest tests/unit -v
```

Esse conjunto deve ser utilizado durante alterações locais em regras isoladas.

---

# 19. Executar integração

```powershell
uv run pytest tests/integration -v
```

Esse conjunto deve ser executado sempre que forem alterados:

```text
services
writers
incrementalidade
contratos físicos
orquestração
```

---

# 20. Executar testes HTTP

```powershell
uv run pytest tests/api -v
```

Deve ser executado ao alterar:

```text
FastAPI
rotas
Pydantic
serialização
CORS
Query Layer utilizada pela API
```

---

# 21. Executar testes de uma camada específica

## Bronze

```powershell
uv run pytest tests/unit/test_bronze_*.py tests/integration/test_bronze_service.py -v
```

## Silver

```powershell
uv run pytest tests/unit/test_silver_*.py tests/integration/test_silver_service.py -v
```

## Gold

```powershell
uv run pytest tests/unit/test_gold_*.py tests/integration/test_gold_service.py -v
```

## Query Layer

```powershell
uv run pytest tests/unit/test_query_service.py tests/unit/test_query_summary_service.py -v
```

## API

```powershell
uv run pytest tests/api tests/unit/test_api_settings.py -v
```

## Pipeline

```powershell
uv run pytest tests/integration/test_pipeline_service.py -v
```

---

# 22. Executar um único arquivo

Exemplo:

```powershell
uv run pytest tests/unit/test_silver_identity_resolution.py -v
```

---

# 23. Executar um único teste

Exemplo:

```powershell
uv run pytest tests/unit/test_silver_identity_resolution.py::test_nome_do_teste -v
```

Essa estratégia é útil durante investigação de uma regressão específica.

---

# 24. Quality gate completo

Antes de considerar um bloco de implementação concluído, a sequência recomendada é:

```powershell
uv run ruff format .
uv run ruff check .
uv run pyright
uv run pytest
```

Cada comando valida uma dimensão diferente.

```text
ruff format
→ formatação

ruff check
→ qualidade estática / estilo

pyright
→ tipos

pytest
→ comportamento
```

Uma alteração só deve ser considerada fechada quando todas as dimensões relevantes estiverem aprovadas.

---

# 25. Ordem recomendada durante desenvolvimento

Durante uma alteração local, não é necessário começar sempre pelos 222 testes.

O fluxo recomendado é:

```text
alterar componente
        ↓
teste específico
        ↓
testes da camada
        ↓
Ruff
        ↓
Pyright
        ↓
integração relacionada
        ↓
suíte completa
```

Exemplo para uma alteração de identidade:

```powershell
uv run pytest tests/unit/test_silver_identity_resolution.py -v

uv run pytest tests/unit/test_silver_classification.py -v

uv run pytest tests/integration/test_silver_service.py -v

uv run ruff check .

uv run pyright

uv run pytest
```

Isso acelera o feedback sem abrir mão da regressão completa no fechamento.

---

# 26. Como interpretar uma falha

Uma falha deve ser classificada antes da correção.

Exemplo:

```text
unit test falhou
```

pode significar:

```text
regra de negócio mudou
implementação está errada
teste ficou desatualizado
```

Não se deve alterar o teste automaticamente apenas para fazê-lo passar.

Primeiro deve ser respondido:

```text
qual é a regra correta?
```

Depois:

```text
o código ou o teste está divergindo dela?
```

---

# 27. Falha de contrato

Exemplo:

```text
campo ausente em schema
```

Normalmente aponta para:

```text
contracts/
```

ou para mudança física não propagada.

Nunca deve ser resolvida simplesmente removendo a assertion se o campo continua fazendo parte do contrato oficial.

---

# 28. Falha FULL / INCREMENTAL / NOOP

Essas falhas precisam ser tratadas com atenção porque podem provocar grandes efeitos operacionais.

Exemplo:

```text
esperava NOOP
recebeu FULL
```

não é apenas diferença em um valor.

Pode significar:

```text
rebuild completo do Lakehouse
```

Por isso testes desses modos representam proteção operacional.

---

# 29. Falha de identidade

Se um teste de identidade esperado como:

```text
UNRESOLVED
```

passa a produzir:

```text
LEGACY_IMEI
```

isso pode indicar que a plataforma ampliou sua inferência.

Esse tipo de mudança não deve ser aceito somente porque reduz:

```text
MISSING_DEVICE_SERIAL
```

É necessário provar que a nova evidência é inequívoca.

---

# 30. Falha em teste HTTP

Um teste HTTP pode falhar mesmo quando a Query Layer está correta.

Exemplo:

```text
QueryService retorna resultado correto
```

mas:

```text
Pydantic não serializa
```

Nesse caso a falha pertence à fronteira:

```text
Query Layer
→ API
```

e não necessariamente à Gold.

---

# 31. Testes e regras de negócio

A suíte deve funcionar como proteção executável das regras documentadas em:

```text
docs/REGRAS_DE_NEGOCIO.md
```

Exemplos:

```text
Regra:
T1 válido é identidade

Teste:
test_silver_classification.py
```

```text
Regra:
(0,0) não é última posição publicável

Teste:
test_gold_last_position.py
```

```text
Regra:
V14.06.117 não recebe automaticamente LEGACY_IMEI

Teste:
test_silver_identity_resolution.py
```

```text
Regra:
batch_ids=() com Silver completa significa NOOP

Teste:
test_silver_service.py
+
test_pipeline_service.py
```

Essa relação deve ser mantida ao longo da evolução do projeto.

---

# 32. Cobertura por responsabilidade

A suíte atual pode ser resumida como:

```text
Bronze
├── arquivos
├── validação
├── lineage
├── controle
├── writer
└── service

Silver
├── normalização
├── identidade
├── classificação
├── transformação
├── contratos
├── incremental
├── writer
└── service

Gold
├── contratos
├── dim_device
├── last_position
├── route_points
├── daily_summary
├── quality_summary
├── incremental
├── writer
└── service

Pipeline
└── Bronze → Silver → Gold

Query
├── leitura
├── filtros
├── paginação
├── COUNT
└── summaries

API
├── health
├── devices
├── positions
├── routes
├── daily summaries
├── data quality
├── erros HTTP
└── CORS
```

---

# 33. Relação entre os três níveis de testes

Um mesmo comportamento pode aparecer em mais de um nível.

Exemplo de identidade:

```text
UNIT
resolve_identity_dataframe()
        ↓
prova a regra isolada
```

```text
INTEGRATION
load_silver()
        ↓
prova a regra dentro da Silver real
```

```text
PIPELINE
run_pipeline()
        ↓
prova a propagação entre camadas
```

Isso não é duplicação inútil.

Cada nível protege uma fronteira diferente.

---

# 34. O que um teste unitário não prova

Por exemplo:

```text
test_silver_identity_resolution
PASS
```

prova que o resolver isolado funciona.

Ele não prova sozinho que:

```text
normalização
 ↓
resolver
 ↓
classificação
 ↓
writer
```

estão corretamente conectados.

Essa responsabilidade pertence aos testes de integração.

---

# 35. O que um teste de integração não substitui

Um teste grande de pipeline pode detectar que:

```text
resultado final está errado
```

mas ser ruim para localizar a causa.

Os testes unitários permitem descobrir se a falha pertence a:

```text
normalização
identidade
classificação
writer
incrementalidade
```

Por isso os dois níveis são necessários.

---

# 36. Dados reais e testes automatizados possuem papéis diferentes

A suíte automatizada usa cenários controlados.

Depois de alterações de regra relevantes, também pode ser necessária validação operacional sobre o histórico real.

Exemplo já utilizado no projeto:

```text
resolver identidade histórica
        ↓
unit tests
        ↓
integration tests
        ↓
full pytest
        ↓
rebuild real
        ↓
medir MISSING_DEVICE_SERIAL
```

Portanto:

```text
teste automatizado
```

e:

```text
validação empírica do Lakehouse
```

não são a mesma coisa.

---

# 37. Quando adicionar um novo teste

Uma nova regra deve receber teste quando introduzir:

```text
novo comportamento
nova regra de negócio
novo caso de erro
novo schema
novo modo incremental
nova integração
novo endpoint
regressão corrigida
```

Especialmente para bugs, a regra recomendada é:

```text
bug identificado
        ↓
criar/reproduzir teste que falha
        ↓
corrigir implementação
        ↓
teste passa
```

Isso impede que o mesmo problema reapareça silenciosamente.

---

# 38. Testes para novas funcionalidades futuras

Se uma nova capacidade for adicionada à Query Layer, o fluxo esperado é:

```text
QueryService
        ↓
unit test da Query
        ↓
REST endpoint
        ↓
API test
```

Se a capacidade exigir novo produto analítico:

```text
regra Gold
        ↓
unit test Gold
        ↓
Gold integration
        ↓
Query Layer
        ↓
Query test
        ↓
API
        ↓
API test
```

Assim a cobertura cresce seguindo a própria arquitetura.

---

# 39. Critério de conclusão de um bloco

Um bloco de desenvolvimento só deve ser tratado como tecnicamente encerrado quando:

```text
regra implementada
        ↓
teste específico aprovado
        ↓
integração relevante aprovada
        ↓
Ruff aprovado
        ↓
Pyright aprovado
        ↓
suíte completa aprovada
        ↓
validação operacional,
quando necessária
```

Somente depois disso a mudança deve ser considerada pronta para versionamento.

---

# 40. Resumo

A suíte da QUEO Data Platform não é tratada apenas como verificação final.

Ela faz parte da arquitetura.

```text
Unit tests
→ protegem regras
```

```text
Integration tests
→ protegem colaboração entre componentes
```

```text
API tests
→ protegem contratos externos
```

```text
Ruff
→ protege qualidade estática
```

```text
Pyright
→ protege contratos de tipos
```

```text
Validação real
→ confirma comportamento sobre o Lakehouse histórico
```

O princípio central é:

```text
toda regra importante
deve possuir uma proteção executável
```

e:

```text
nenhuma alteração deve ser considerada segura
somente porque funciona em um cenário manual
```

A combinação de testes unitários, integração, HTTP e validação real é o mecanismo utilizado para reduzir regressões em:

```text
ingestão
classificação
identidade
incrementalidade
persistência
produtos analíticos
consulta
exposição externa
```