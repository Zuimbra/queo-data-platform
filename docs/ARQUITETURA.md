# Arquitetura — QUEO Data Platform

# 1. Visão geral

A QUEO Data Platform é uma plataforma de dados estruturada em camadas para ingestão, tratamento, consolidação analítica e exposição de dados de rastreadores.

A arquitetura segue o fluxo:

```text
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
Consumidores externos
```

Cada camada possui uma responsabilidade específica.

O princípio central é:

```text
capturar
 ↓
preservar
 ↓
interpretar
 ↓
consolidar
 ↓
consultar
 ↓
expor
```

O sistema evita colocar todas essas responsabilidades no mesmo componente.

---

# 2. Arquitetura em alto nível

```text
┌───────────────────────────────────────────────────────────────┐
│                       FONTES DE DADOS                         │
│                                                               │
│                         CSVs                                  │
└──────────────────────────────┬────────────────────────────────┘
                               │
                               ▼
┌───────────────────────────────────────────────────────────────┐
│                          RAW                                  │
│                                                               │
│  inbox/                                                       │
│  archive/                                                     │
│  quarantine/                                                  │
└──────────────────────────────┬────────────────────────────────┘
                               │
                               ▼
┌───────────────────────────────────────────────────────────────┐
│                         BRONZE                                │
│                                                               │
│  tracker_logs                                                 │
│                                                               │
│  • preservação                                                │
│  • lineage                                                    │
│  • SHA-256                                                    │
│  • idempotência                                               │
│  • controle de ingestão                                      │
└──────────────────────────────┬────────────────────────────────┘
                               │
                               ▼
┌───────────────────────────────────────────────────────────────┐
│                         SILVER                                │
│                                                               │
│  telemetry_events                                             │
│  device_identity_events                                      │
│  rejected_logs                                                │
│                                                               │
│  • normalização                                               │
│  • resolução de identidade                                   │
│  • classificação                                              │
│  • tipagem                                                    │
│  • qualidade                                                  │
└──────────────────────────────┬────────────────────────────────┘
                               │
                               ▼
┌───────────────────────────────────────────────────────────────┐
│                          GOLD                                 │
│                                                               │
│  dim_device                                                   │
│  device_last_position                                        │
│  device_route_points                                         │
│  device_daily_summary                                        │
│  data_quality_summary                                        │
│                                                               │
│  • deduplicação lógica                                       │
│  • agregações                                                 │
│  • estado atual                                               │
│  • produtos analíticos                                       │
└──────────────────────────────┬────────────────────────────────┘
                               │
                               ▼
┌───────────────────────────────────────────────────────────────┐
│                      QUERY LAYER                              │
│                                                               │
│                     QueryService                              │
│                                                               │
│  • filtros                                                    │
│  • paginação                                                  │
│  • ordenação                                                  │
│  • COUNT                                                      │
│  • leitura read-only                                         │
└──────────────────────────────┬────────────────────────────────┘
                               │
                               ▼
┌───────────────────────────────────────────────────────────────┐
│                        REST API                               │
│                                                               │
│  FastAPI                                                      │
│                                                               │
│  • HTTP                                                       │
│  • Pydantic                                                   │
│  • status codes                                               │
│  • serialização                                               │
│  • CORS                                                       │
└──────────────────────────────┬────────────────────────────────┘
                               │
                               ▼
┌───────────────────────────────────────────────────────────────┐
│                  CONSUMIDORES EXTERNOS                       │
│                                                               │
│  Dashboard                                                    │
│  Backoffice                                                   │
│  aplicações                                                   │
│  integrações                                                  │
│  serviço MCP externo                                         │
└───────────────────────────────────────────────────────────────┘
```

---

# 3. Princípio de responsabilidade única entre camadas

A arquitetura evita que uma camada assuma funções pertencentes à camada seguinte.

A divisão é:

```text
Raw
→ recebe arquivos
```

```text
Bronze
→ preserva e rastreia
```

```text
Silver
→ interpreta
```

```text
Gold
→ consolida
```

```text
Query Layer
→ consulta
```

```text
REST API
→ expõe
```

Exemplo:

uma coordenada inválida não deve impedir que o arquivo seja armazenado na Bronze.

O fluxo correto é:

```text
arquivo estruturalmente válido
        ↓
Bronze
        ↓
Silver
        ↓
coordenada interpretada
        ↓
qualidade determinada
```

---

# 4. Estrutura física de dados

Por padrão, os dados ficam abaixo de:

```text
data/
```

A raiz pode ser substituída por:

```text
QUEO_DATA_DIR
```

A estrutura lógica é:

```text
data/
│
├── raw/
│   ├── inbox/
│   ├── archive/
│   └── quarantine/
│
└── lakehouse/
    │
    ├── 00_control/
    │
    ├── 01_bronze/
    │
    ├── 02_silver/
    │
    └── 03_gold/
```

---

# 5. Raw

A área Raw representa a fronteira inicial entre:

```text
arquivo externo
```

e:

```text
plataforma de dados
```

Existem três estados principais.

## `inbox`

```text
arquivo aguardando processamento
```

## `archive`

```text
arquivo processado
ou
arquivo já processado anteriormente
```

## `quarantine`

```text
arquivo que não pôde ser ingerido com segurança
```

O fluxo é:

```text
             ┌── sucesso ─────────→ archive
             │
inbox ───────┼── duplicado ───────→ archive
             │
             └── falha ───────────→ quarantine
```

---

# 6. Bronze

A Bronze é a camada de preservação e rastreabilidade.

Seu produto principal é:

```text
tracker_logs
```

A Bronze deve manter os dados o mais próximos possível da origem.

Ela não possui responsabilidade de decidir:

```text
telemetria válida
identidade válida
coordenada válida
mensagem válida
```

Essas decisões pertencem à Silver.

---

# 7. Responsabilidades da Bronze

A Bronze é responsável por:

```text
descobrir arquivos
```

```text
calcular SHA-256
```

```text
verificar duplicidade de arquivo
```

```text
validar estrutura
```

```text
adicionar lineage
```

```text
persistir em Delta Lake
```

```text
registrar status de ingestão
```

```text
arquivar ou colocar em quarantine
```

---

# 8. Lineage Bronze

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

O fluxo é:

```text
linha do CSV
     ↓
arquivo
     ↓
hash do arquivo
     ↓
posição da linha
     ↓
row_id determinístico
```

O `row_id` não utiliza:

```text
batch_id
```

na sua composição.

Portanto:

```text
mesmo arquivo
+
mesma linha
        ↓
mesmo row_id
```

mesmo em outra execução.

---

# 9. Idempotência Bronze

A Bronze possui dois níveis de proteção.

## Arquivo

```text
source_file_hash
```

impede o processamento normal de um arquivo cujo conteúdo já foi concluído com sucesso.

## Linha

```text
row_id
```

protege a Delta Table contra duplicação de linhas.

A escrita incremental utiliza conceitualmente:

```text
MERGE
    ON target.row_id = source.row_id
```

com:

```text
MATCHED
→ nada

NOT MATCHED
→ INSERT
```

A Bronze é, portanto:

```text
insert-only
```

---

# 10. Tabela de controle

A área:

```text
00_control/
```

registra o ciclo de ingestão.

Estados relevantes incluem:

```text
PROCESSING
SUCCESS
FAILED
SKIPPED
```

Ela permite responder:

```text
qual arquivo foi processado?

quando?

com qual batch?

quantas linhas entraram?

quantas eram duplicadas?

por que um arquivo falhou?
```

---

# 11. Silver

A Silver transforma registros brutos em informação operacional interpretada.

Ela produz:

```text
telemetry_events
device_identity_events
rejected_logs
```

Seu fluxo interno é:

```text
Bronze
 ↓
normalização
 ↓
resolução de identidade
 ↓
classificação
 ↓
tipagem
 ↓
persistência Silver
```

---

# 12. Normalização Silver

A primeira etapa converte a representação Bronze para nomes e tipos utilizados internamente.

Exemplo:

```text
DATA_SERVIDOR
→ server_timestamp

TM_STAMP
→ device_timestamp

MESS_TYPE
→ message_type

PRT_VER
→ protocol_version

S/N ou IMEI
→ device_serial_raw
```

Strings passam por:

```text
TRIM
```

e:

```text
""
→ NULL
```

Conversões de timestamp utilizam comportamento tolerante:

```text
valor válido
→ timestamp

valor inválido
→ NULL
```

---

# 13. Tempo lógico de evento

O instante do evento segue:

```text
device_timestamp
        ↓
se válido, utilizar
```

caso contrário:

```text
server_timestamp
```

Formalmente:

```text
event_timestamp
=
COALESCE(
    device_timestamp,
    server_timestamp
)
```

Esse timestamp é utilizado posteriormente para:

```text
event_date
ordenação
particionamento
última posição
rota
agregações
```

---

# 14. Resolução de identidade

Antes da classificação, o sistema tenta determinar:

```text
device_serial
```

O valor bruto permanece em:

```text
device_serial_raw
```

São possíveis três resultados:

```text
DIRECT
LEGACY_IMEI
UNRESOLVED
```

---

# 15. Identidade direta

Quando o próprio registro possui serial utilizável:

```text
device_serial_raw
        ↓
normalização
        ↓
device_serial
```

Exemplo:

```text
M202527000021P
        ↓
202527000021P
```

Nesse caso:

```text
device_resolution_method
=
DIRECT
```

---

# 16. Identidade legada

Existe tratamento específico para:

```text
V14.06.111
```

onde alguns registros não possuem serial diretamente.

A resolução utiliza evidências do tipo:

```text
T1
 ↓
IMEI
 ↓
IMEI → serial conhecido
 ↓
registro legado
```

Somente relações inequívocas podem ser utilizadas.

O princípio é:

```text
inferir somente quando existe evidência suficiente
```

e nunca:

```text
inferir para reduzir rejeições
```

Quando não há evidência suficiente:

```text
UNRESOLVED
```

---

# 17. Classificação Silver

Depois da resolução de identidade, cada linha segue uma árvore de decisão.

```text
message_type ausente?
        │
        ├── sim
        │    ↓
        │ MISSING_MESSAGE_TYPE
        │
        └── não
             ↓
message_type corresponde T<n>?
        │
        ├── não
        │    ↓
        │ INVALID_MESSAGE_TYPE
        │
        └── sim
             ↓
timestamp existe?
        │
        ├── não
        │    ↓
        │ MISSING_OR_INVALID_TIMESTAMP
        │
        └── sim
             ↓
device_serial existe?
        │
        ├── não
        │    ↓
        │ MISSING_DEVICE_SERIAL
        │
        └── sim
             ↓
message_type == T1?
        │
        ├── sim
        │    ↓
        │ identity
        │
        └── não
             ↓
          telemetry
```

---

# 18. Telemetria Silver

Mensagens:

```text
T<n>
```

exceto:

```text
T1
```

podem gerar:

```text
telemetry_events
```

A transformação converte campos como:

```text
latitude
longitude
speed
direction
battery
odometer
horimeter
HDOP
RX level
RPM
temperature
```

para tipos adequados.

Conversões inválidas produzem:

```text
NULL
```

em vez de falha global.

---

# 19. Qualidade de posição

A Silver adiciona:

```text
has_valid_coordinates
```

e:

```text
position_quality
```

Estados possíveis incluem:

```text
VALID
MISSING_COORDINATES
INVALID_COORDINATES
LOW_GPS_PRECISION
```

Uma posição pode possuir:

```text
has_valid_coordinates = TRUE
```

e simultaneamente:

```text
position_quality = LOW_GPS_PRECISION
```

---

# 20. Identidade Silver

Mensagens:

```text
T1
```

são tratadas como eventos de identidade.

A interpretação atual extrai:

```text
ICCID
IMSI
IMEI
```

e indicadores como:

```text
has_valid_iccid_format
has_valid_imsi_format
has_valid_imei_format
```

Esses campos são úteis tanto para consumo quanto para resolução histórica de identidade.

---

# 21. Rejeições Silver

Registros não interpretáveis como eventos válidos são preservados em:

```text
rejected_logs
```

Isso significa que:

```text
rejeição
≠
perda
```

O sistema preserva:

```text
linha
motivo
lineage
dados disponíveis
```

para auditoria e qualidade.

---

# 22. Incrementalidade Silver

A Silver possui três modos:

```text
FULL
INCREMENTAL
NOOP
```

---

# 23. Silver FULL

É executado quando:

```text
batch_ids is None
```

ou quando:

```text
Silver inexistente
Silver incompleta
Silver incompatível com contrato atual
```

Nesse caso:

```text
Bronze completa
        ↓
Silver reconstruída
```

---

# 24. Silver INCREMENTAL

Quando novos batches existem:

```text
batch_ids
        ↓
descobrir datas afetadas
```

A Silver não processa apenas as novas linhas.

Depois de descobrir as datas:

```text
batch
 ↓
event_date afetada
 ↓
carregar toda a partição histórica
 ↓
recalcular
 ↓
substituir a partição
```

Isso é necessário para suportar:

```text
late-arriving data
```

---

# 25. Silver NOOP

Quando:

```text
batch_ids = ()
```

e a Silver já está completa e compatível:

```text
NOOP
```

Isso representa:

```text
nenhum dado novo
+
nenhuma recuperação necessária
```

e não:

```text
FULL
```

---

# 26. Gold

A Gold transforma eventos Silver em produtos voltados ao consumo.

Os cinco produtos atuais são:

```text
dim_device

device_last_position

device_route_points

device_daily_summary

data_quality_summary
```

---

# 27. Base Gold

Antes de construir os principais produtos analíticos, a Gold cria views de trabalho para:

```text
telemetry
identity
```

Essas views aplicam:

```text
filtros mínimos
+
deduplicação lógica
```

Assim os produtos Gold não precisam repetir essa lógica individualmente.

---

# 28. Deduplicação Gold

A deduplicação não utiliza simplesmente:

```text
row_id
```

porque o objetivo da Gold é identificar:

```text
eventos logicamente equivalentes
```

e não:

```text
linhas físicas idênticas
```

Para telemetria são considerados elementos como:

```text
device_serial
event_timestamp
message_type
serial_count
latitude
longitude
speed
```

Para identidade:

```text
device_serial
event_timestamp
IMEI
IMSI
ICCID
```

---

# 29. `dim_device`

Representa a visão consolidada dos dispositivos conhecidos.

Ela combina:

```text
identidade
+
telemetria
```

e produz campos como:

```text
current_imei
current_imsi
current_iccid
current_protocol_version

first_seen_at
last_seen_at

first_identity_at
last_identity_at

first_telemetry_at
last_telemetry_at

identity_event_count
telemetry_event_count
```

Sua granularidade é:

```text
1 registro por device_serial
```

---

# 30. `device_last_position`

Representa:

```text
última posição publicável
por dispositivo
```

Somente pontos com:

```text
has_valid_coordinates = TRUE
```

participam.

Também são excluídas coordenadas:

```text
0,0
```

A prioridade de seleção é:

```text
event_timestamp
 ↓
server_timestamp
 ↓
serial_count
```

do mais recente para o mais antigo.

---

# 31. `device_route_points`

Representa o histórico ordenado de pontos de rota.

A granularidade é:

```text
device_serial
+
event_date
+
point_sequence
```

A sequência reinicia a cada:

```text
dispositivo
+
dia
```

Também é produzido:

```text
is_moving
```

com regra atual:

```text
speed >= 5
```

---

# 32. `device_daily_summary`

Representa:

```text
1 dispositivo
+
1 dia
```

Produz métricas como:

```text
message_count
distinct_message_type_count

valid_position_count
invalid_position_count
valid_position_percentage

moving_event_count
stopped_event_count

average_speed
maximum_speed

HDOP

battery

odometer

primeira posição
última posição
```

É um produto de agregação operacional.

---

# 33. `data_quality_summary`

Representa a qualidade diária do processamento.

Combina diretamente:

```text
telemetry_events
device_identity_events
rejected_logs
```

Produz:

```text
telemetry_event_count
identity_event_count
accepted_event_count
rejected_event_count
total_event_count
rejection_percentage
```

e contagens por motivo de rejeição.

Diferentemente dos demais produtos:

```text
data_quality_summary
```

mede processamento Silver e não eventos Gold deduplicados.

---

# 34. Incrementalidade Gold

A Gold também possui:

```text
FULL
INCREMENTAL
NOOP
```

---

# 35. Gold FULL

Acontece quando:

```text
Silver FULL
```

ou:

```text
Gold incompleta
```

ou:

```text
não existe SilverLoadResult explícito
```

---

# 36. Gold INCREMENTAL

A Silver informa:

```text
affected_event_dates
affected_rejection_dates
```

A Gold deriva:

```text
affected_devices
quality_dates
```

O escopo é então:

```text
event_dates
        │
        ├── affected_devices
        │        ↓
        │   dim_device
        │   last_position
        │
        ├── route_points
        │
        └── daily_summary

rejection_dates
        │
        └──────────────┐
                       ▼
event_dates ─────→ quality_dates
                       ↓
              data_quality_summary
```

---

# 37. Gold NOOP

Quando:

```text
Silver NOOP
+
Gold completa
```

o resultado é:

```text
Gold NOOP
```

Nenhum produto é reprocessado sem necessidade.

---

# 38. Pipeline

A orquestração principal é:

```text
run_pipeline()
```

Seu fluxo é:

```text
load_bronze()
        ↓
BronzeLoadResult
        ↓
batch_ids
        ↓
load_silver()
        ↓
SilverLoadResult
        ↓
affected dates
        ↓
load_gold()
        ↓
GoldLoadResult
```

O pipeline não implementa regras internas das camadas.

Ele apenas conecta seus resultados.

---

# 39. Bootstrap vazio

O sistema aceita como estado válido:

```text
primeira execução
+
inbox vazio
+
Bronze inexistente
```

Nesse cenário:

```text
Bronze
→ sem dados

Silver
→ NOOP

Gold
→ NOOP
```

Isso permite inicializar a plataforma sem exigir artificialmente um arquivo de entrada.

---

# 40. `PipelineResult`

O pipeline consolida:

```text
bronze
silver
gold
```

e expõe dois conceitos importantes.

## `has_new_data`

Significa:

```text
Bronze inseriu novas linhas
```

## `has_changes`

É mais amplo:

```text
nova Bronze
OU
Silver reconstruída
OU
Gold reconstruída
```

Isso permite distinguir:

```text
novos dados
```

de:

```text
mudança de estado
```

---

# 41. Query Layer

A Query Layer foi criada para separar:

```text
armazenamento
```

de:

```text
consumo
```

Sua interface central é:

```text
QueryService
```

Ela é deliberadamente:

```text
read-only
```

---

# 42. Fluxo interno da Query Layer

O fluxo de consulta atual é:

```text
QueryService
      ↓
DeltaTable
      ↓
PyArrow Dataset
      ↓
DuckDB
      ↓
DataFrame
```

DuckDB é utilizado para:

```text
filtros
ordenação
COUNT
LIMIT
OFFSET
```

---

# 43. Responsabilidades da Query Layer

A Query Layer possui:

```text
validação de filtros
```

```text
validação de paginação
```

```text
filtros por dispositivo
```

```text
filtros temporais
```

```text
ordenação determinística
```

```text
COUNT
```

```text
paginação
```

Ela não possui:

```text
HTTP
Pydantic
status codes
CORS
```

---

# 44. `QueryPage`

As consultas paginadas retornam conceitualmente:

```text
items
total
limit
offset
returned
has_more
next_offset
```

Isso evita que cada consumidor precise implementar sua própria lógica de paginação.

---

# 45. Fronteira entre Query Layer e REST API

A arquitetura é:

```text
REST API
    ↓
QueryService
    ↓
Gold
```

Não é permitido arquiteturalmente:

```text
REST endpoint
    ↓
DeltaTable
```

nem:

```text
REST endpoint
    ↓
DuckDB SQL
```

A API não deve duplicar regras de consulta.

---

# 46. REST API

A camada HTTP utiliza:

```text
FastAPI
Pydantic
```

Sua responsabilidade é:

```text
receber HTTP
 ↓
validar parâmetros
 ↓
chamar QueryService
 ↓
serializar
 ↓
retornar HTTP
```

---

# 47. Endpoints atuais

A superfície read-only inclui:

```text
GET /health
```

```text
GET /api/v1/devices
```

```text
GET /api/v1/devices/{device_serial}
```

```text
GET /api/v1/devices/{device_serial}/last-position
```

```text
GET /api/v1/devices/{device_serial}/route
```

```text
GET /api/v1/daily-summaries
```

```text
GET /api/v1/data-quality
```

---

# 48. Tratamento de erros HTTP

A API traduz erros internos para contratos externos.

## Recurso específico não encontrado

```text
404
```

Exemplo:

```text
device desconhecido
```

---

## Parâmetro semanticamente inválido

```text
422
```

Exemplo:

```text
start_date > end_date
```

---

## Gold indisponível

```text
503
```

A API retorna uma mensagem pública sem expor:

```text
paths físicos
```

do Lakehouse.

---

# 49. CORS

A API não libera origens por padrão.

A configuração é feita por:

```text
QUEO_API_CORS_ORIGINS
```

Exemplo:

```text
http://localhost:5173,https://app.example.com
```

O objetivo é tornar o consumidor configurável sem codificar origens na aplicação.

---

# 50. Configuração da plataforma

As principais configurações de ambiente atuais são:

```text
QUEO_DATA_DIR
```

para alterar a raiz dos dados.

E:

```text
QUEO_API_CORS_ORIGINS
```

para configurar origens HTTP permitidas.

A configuração permanece centralizada em:

```text
Settings
```

---

# 51. Consumidores internos e externos

A arquitetura diferencia dois tipos de consumidores.

## Consumidor interno

Executa no mesmo ambiente/processo e pode utilizar:

```text
QueryService
```

diretamente.

Exemplos:

```text
CLI
script interno
job interno
componente Python no mesmo deployment
```

---

## Consumidor externo

Executa em:

```text
outro serviço
outro container
outra aplicação
outro repositório
```

Nesse caso a fronteira recomendada é:

```text
REST API
```

---

# 52. MCP externo

Existe a possibilidade de integração com um serviço MCP externo.

Nesse cenário, a arquitetura recomendada é:

```text
┌───────────────────────────────┐
│      QUEO DATA PLATFORM       │
│                               │
│ Gold                          │
│  ↓                            │
│ QueryService                  │
│  ↓                            │
│ REST API                      │
└───────────────┬───────────────┘
                │
                │ HTTP / JSON
                │
┌───────────────▼───────────────┐
│          MCP SERVICE          │
│                               │
│ DataPlatformClient            │
│  ↓                            │
│ MCP Tools                     │
│  ↓                            │
│ MCP Server                    │
└───────────────┬───────────────┘
                │
                ▼
           MCP Client / LLM
```

O MCP não precisa ser implementado neste repositório quando já pertence a outro serviço.

---

# 53. Por que o MCP externo deve consumir a REST API

Se o MCP acessasse diretamente:

```text
Delta
```

seria necessário compartilhar:

```text
filesystem
schemas internos
DuckDB
Delta Lake
configuração da plataforma
ciclo de deploy
```

Com HTTP:

```text
MCP
 ↓
REST API
```

o serviço conhece apenas:

```text
URL
endpoint
parâmetros
JSON
status HTTP
```

Isso reduz o acoplamento.

---

# 54. Escalabilidade por novos consumidores

A arquitetura permite:

```text
                              ┌── Dashboard
                              │
Gold → QueryService → REST API├── MCP
                              │
                              ├── Backoffice
                              │
                              ├── Mobile
                              │
                              └── Integrações
```

Cada consumidor não precisa conhecer a estrutura física do Lakehouse.

---

# 55. Escalabilidade pela Query Layer

Quando surgir uma nova necessidade, a regra geral é:

```text
a Gold já possui a informação?
```

Se sim:

```text
QueryService
 ↓
novo método
 ↓
REST endpoint
 ↓
consumidor
```

Se não:

```text
Gold
 ↓
novo produto/regra
 ↓
QueryService
 ↓
REST API
 ↓
consumidor
```

---

# 56. Exemplo de evolução correta

Novo requisito:

```text
listar dispositivos sem telemetria há 7 dias
```

Não implementar diretamente:

```text
FastAPI route
 ↓
SQL
```

O fluxo deve ser:

```text
QueryService
 ↓
list_inactive_devices(...)
 ↓
testes Query
 ↓
REST endpoint
 ↓
testes HTTP
 ↓
consumidores
```

---

# 57. Evolução que exige nova Gold

Novo requisito:

```text
distância total confiável por dispositivo por mês
```

Se esse produto ainda não existe:

```text
Silver
 ↓
Gold
 ↓
device_monthly_distance
 ↓
QueryService
 ↓
REST API
```

A regra analítica não deve nascer:

```text
na API
```

nem:

```text
no MCP
```

---

# 58. Testabilidade como parte da arquitetura

A arquitetura possui três níveis principais de testes:

```text
unit
integration
api
```

## Unit

Protege:

```text
regras isoladas
```

## Integration

Protege:

```text
colaboração real entre componentes
+
Delta Lake
```

## API

Protege:

```text
contratos HTTP
```

---

# 59. Persistência real nos testes

Grande parte dos testes utiliza:

```text
tmp_path
```

para criar:

```text
CSVs
Delta Tables
diretórios Raw
Bronze
Silver
Gold
```

temporários.

Assim:

```text
testes
```

não dependem:

```text
do Lakehouse real do desenvolvedor
```

---

# 60. Dependências arquiteturais

A direção correta das dependências é:

```text
Bronze
    ↓
Silver
    ↓
Gold
```

e para consumo:

```text
Gold
    ↓
Query
    ↓
API
```

O pipeline depende das camadas para orquestrá-las.

A API depende da Query Layer.

Consumidores externos dependem da API.

---

# 61. Dependências que devem ser evitadas

Não deve existir:

```text
Bronze
→ Gold
```

pulando a Silver.

Não deve existir:

```text
API
→ Silver
```

Não deve existir:

```text
API
→ Bronze
```

Não deve existir:

```text
MCP externo
→ Gold filesystem
```

Não deve existir:

```text
dashboard externo
→ Delta Table
```

---

# 62. Separação entre contratos internos e externos

Existem diferentes contratos.

## Contrato da fonte

```text
CSV tracker
```

## Contrato Bronze

```text
source columns
+
lineage
```

## Contratos Silver

```text
telemetry
identity
rejected
```

## Contratos Gold

```text
produtos analíticos
```

## Contrato Query

```text
DataFrame
QueryPage
```

## Contrato externo

```text
HTTP / JSON / Pydantic
```

Uma mudança em um contrato não deve ser propagada silenciosamente para outro.

---

# 63. Recuperação automática por incompatibilidade

Silver e Gold verificam se seus produtos persistidos permitem execução incremental.

Caso a estrutura existente esteja incompatível:

```text
incremental inseguro
        ↓
FULL
```

Esse comportamento funciona como mecanismo de:

```text
recovery
```

e:

```text
migração de schema
```

---

# 64. Estado ocioso como comportamento normal

A arquitetura foi projetada para que:

```text
nenhum arquivo novo
```

não seja erro.

Fluxo normal:

```text
Bronze
inserted_rows = 0
        ↓
batch_ids = ()
        ↓
Silver
NOOP
        ↓
Gold
NOOP
```

O pipeline pode ser executado repetidamente sem provocar rebuild desnecessário.

---

# 65. Late-arriving data

Dados podem chegar depois de uma partição histórica já ter sido processada.

Por isso:

```text
novo batch
```

não significa:

```text
append somente das novas linhas
```

O mecanismo é:

```text
novo registro antigo
        ↓
descobrir data afetada
        ↓
recarregar todas as linhas daquela data
        ↓
recalcular
        ↓
substituir partição
```

Essa regra existe tanto para preservar consistência Silver quanto Gold.

---

# 66. Observabilidade por dados

A própria arquitetura produz sinais operacionais.

Bronze:

```text
control table
```

Silver:

```text
rejected_logs
```

Gold:

```text
data_quality_summary
```

Isso cria uma cadeia:

```text
ingestão
 ↓
rejeição
 ↓
qualidade
```

sem depender exclusivamente de logs da aplicação.

---

# 67. Limites atuais da arquitetura

A implementação atual é deliberadamente simples em alguns aspectos.

Ainda não fazem parte da arquitetura principal atual:

```text
streaming contínuo
```

```text
mensageria
```

```text
autenticação/autorização avançada
```

```text
API de escrita
```

```text
MCP interno
```

```text
orquestrador distribuído
```

```text
cluster de processamento
```

Esses elementos podem ser adicionados posteriormente sem invalidar a separação atual de responsabilidades.

---

# 68. Evolução para streaming

Uma possível evolução futura poderia ser:

```text
MQTT / Kafka / Event Bus
        ↓
Ingestion Adapter
        ↓
Bronze
```

A regra seria preservar:

```text
Bronze
→ camada inicial persistida
```

independentemente da origem passar de:

```text
CSV batch
```

para:

```text
event stream
```

---

# 69. Evolução da persistência

Hoje:

```text
Delta Lake local
```

é utilizado.

No futuro a infraestrutura física pode migrar para:

```text
object storage
cloud storage
serviço distribuído
```

sem necessariamente modificar:

```text
regras Silver
produtos Gold
contratos HTTP
```

desde que a infraestrutura continue oferecendo os contratos esperados pelas camadas superiores.

---

# 70. Evolução da API

Hoje:

```text
REST API read-only
```

é suficiente para os consumidores planejados.

Futuramente podem ser adicionados:

```text
autenticação
rate limiting
API Gateway
observabilidade
versionamento adicional
```

sem deslocar regras analíticas para a camada HTTP.

---

# 71. Princípio de extensibilidade

A plataforma deve crescer verticalmente.

Exemplo:

```text
novo requisito
        ↓
qual camada possui responsabilidade?
        ↓
implementar ali
        ↓
expor para camada seguinte
```

Não:

```text
novo requisito
        ↓
implementar onde for mais rápido
```

---

# 72. Mapa de responsabilidades

```text
┌──────────────────────┬─────────────────────────────────────────┐
│ Componente           │ Responsabilidade                        │
├──────────────────────┼─────────────────────────────────────────┤
│ Raw                  │ Receber e organizar arquivos            │
│ Bronze               │ Preservar e rastrear                    │
│ Control              │ Auditar ingestão                        │
│ Silver               │ Interpretar e classificar               │
│ Identity Resolution  │ Resolver identidade canônica            │
│ Gold                 │ Produzir informação analítica           │
│ Pipeline             │ Orquestrar camadas                      │
│ Query Layer          │ Consultar Gold                          │
│ REST API             │ Expor contratos HTTP                    │
│ MCP externo          │ Expor semântica para agentes/LLMs       │
└──────────────────────┴─────────────────────────────────────────┘
```

---

# 73. Fluxo completo de um arquivo

```text
CSV
 │
 ▼
raw/inbox
 │
 ▼
descoberta
 │
 ▼
SHA-256
 │
 ├── já processado
 │       ↓
 │     SKIPPED
 │       ↓
 │     archive
 │
 └── novo
         ↓
     validação
         │
         ├── inválido
         │     ↓
         │   FAILED
         │     ↓
         │ quarantine
         │
         └── válido
               ↓
             lineage
               ↓
           Bronze MERGE
               ↓
             SUCCESS
               ↓
             archive
               ↓
             batch_id
               ↓
              Silver
               ↓
        normalização
               ↓
        identity resolution
               ↓
          classificação
          /      |      \
         /       |       \
 telemetry   identity   rejected
      \          |          /
       \         |         /
        └────── Gold ─────┘
                  ↓
            QueryService
                  ↓
              REST API
                  ↓
             consumidor
```

---

# 74. Fluxo completo de uma consulta

Exemplo:

```text
GET
/api/v1/devices/202527000021P/last-position
```

Fluxo:

```text
HTTP client
    ↓
FastAPI
    ↓
get_last_position()
    ↓
QueryService.get_last_position()
    ↓
device_last_position
    ↓
DeltaTable
    ↓
PyArrow Dataset
    ↓
DuckDB
    ↓
DataFrame
    ↓
Pydantic
    ↓
JSON
    ↓
HTTP client
```

---

# 75. Fluxo com MCP externo

```text
LLM / MCP Client
        ↓
MCP Tool
        ↓
DataPlatformClient
        ↓
HTTP
        ↓
REST API
        ↓
QueryService
        ↓
Gold
```

O MCP atua como:

```text
adaptador semântico
```

e não como:

```text
nova camada analítica
```

---

# 76. Arquitetura consolidada

A arquitetura atual pode ser resumida em três grandes blocos.

## Processamento

```text
Raw
 ↓
Bronze
 ↓
Silver
 ↓
Gold
```

## Consumo interno

```text
Gold
 ↓
Query Layer
```

## Exposição externa

```text
Query Layer
 ↓
REST API
 ↓
consumidores
```

---

# 77. Princípio arquitetural final

O princípio central da QUEO Data Platform é:

```text
cada camada deve saber apenas o necessário
para cumprir sua responsabilidade
```

Bronze não precisa conhecer regras analíticas.

Silver não precisa conhecer HTTP.

Gold não precisa conhecer consumidores.

Query Layer não precisa conhecer FastAPI.

REST API não precisa conhecer Delta Lake diretamente.

MCP externo não precisa conhecer o Lakehouse.

A arquitetura é, portanto:

```text
dados brutos
 ↓
dados confiáveis
 ↓
produtos analíticos
 ↓
serviço de consulta
 ↓
interfaces de consumo
```

Essa separação é a principal base para manter:

```text
testabilidade
manutenibilidade
auditabilidade
incrementalidade
baixo acoplamento
extensibilidade
```

à medida que a plataforma evolui.