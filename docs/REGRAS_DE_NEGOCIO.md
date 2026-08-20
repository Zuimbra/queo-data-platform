# Regras de Negócio — QUEO Data Platform

# 1. Objetivo

Este documento descreve as regras de negócio, processamento e consumo atualmente implementadas na QUEO Data Platform.

O objetivo não é explicar linha por linha do código.

O objetivo é responder perguntas como:

```text
quando um arquivo pode entrar no Lakehouse?

quando um registro é aceito?

quando um registro é rejeitado?

o que identifica um dispositivo?

quando uma identidade pode ser inferida?

o que é considerado uma posição válida?

como é escolhida a última posição?

como são calculados os resumos diários?

como é calculada a qualidade dos dados?

quando o processamento é FULL, INCREMENTAL ou NOOP?

o que pode ser consultado externamente?
```

A arquitetura atual é:

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

Cada camada possui responsabilidades diferentes.

---

# 2. Princípio geral de separação das camadas

A plataforma segue o princípio:

```text
Bronze
→ preservar e rastrear

Silver
→ interpretar, classificar e tipar

Gold
→ consolidar e produzir informação analítica

Query Layer
→ consultar

REST API
→ expor
```

Portanto, uma regra não deve ser aplicada prematuramente em uma camada anterior.

Exemplo:

```text
timestamp inválido
```

não torna o arquivo inteiro inválido na Bronze.

O arquivo pode ser estruturalmente válido e ser ingerido normalmente.

A linha com timestamp inválido será tratada posteriormente pela Silver.

O fluxo correto é:

```text
CSV estruturalmente válido
        ↓
Bronze aceita
        ↓
Silver interpreta linha
        ↓
timestamp inválido
        ↓
rejected_logs
```

---

# 3. Conceitos principais

## Arquivo de origem

CSV recebido no:

```text
raw/inbox
```

Representa uma unidade física de ingestão.

---

## Batch

Cada tentativa de processamento de arquivo recebe:

```text
batch_id
```

O `batch_id` identifica uma execução de ingestão.

Ele não identifica permanentemente o conteúdo.

---

## Linha Bronze

Uma linha da fonte acrescida dos metadados técnicos da plataforma.

---

## `row_id`

Identificador determinístico da linha Bronze.

É calculado a partir de:

```text
hash do arquivo
+
posição original da linha
```

Portanto:

```text
mesmo arquivo
+
mesma linha
        ↓
mesmo row_id
```

---

## Dispositivo

Na Silver e na Gold, a identidade canônica é:

```text
device_serial
```

O campo original recebido é preservado separadamente como:

```text
device_serial_raw
```

---

## Evento

Um registro Silver aceito como:

```text
telemetria
```

ou:

```text
identidade
```

---

## Rejeição

Uma linha que chegou corretamente até a Silver, mas não atende aos requisitos mínimos necessários para ser tratada como evento válido.

Ela não é descartada.

É persistida em:

```text
rejected_logs
```

---

# 4. Regras de negócio da Bronze

# RN-BRZ-001 — A Bronze valida estrutura, não semântica

A Bronze deve responder:

```text
é possível ingerir este arquivo de forma segura?
```

Ela não deve responder:

```text
as coordenadas são válidas?

o timestamp é semanticamente válido?

a mensagem representa telemetria?

o serial existe?
```

Essas decisões pertencem à Silver.

---

# RN-BRZ-002 — Apenas arquivos CSV são processados

A ingestão considera arquivos:

```text
*.csv
```

Um caminho que não represente arquivo ou um arquivo com extensão diferente de:

```text
.csv
```

é inválido.

---

# RN-BRZ-003 — Arquivo vazio é inválido

Um arquivo com:

```text
0 bytes
```

não pode ser processado.

Também é inválido um CSV que, mesmo possuindo conteúdo físico, não contenha:

```text
cabeçalho/dados legíveis
```

ou:

```text
nenhuma linha de dados
```

---

# RN-BRZ-004 — Encodings suportados

A leitura tenta primeiro:

```text
UTF-8 com BOM
```

através de:

```text
utf-8-sig
```

Se a leitura falhar por encoding, a plataforma tenta:

```text
latin-1
```

---

# RN-BRZ-005 — A Bronze preserva inicialmente os dados como texto

Durante a leitura:

```text
dtype = str
```

é utilizado.

A Bronze não tenta inferir:

```text
inteiro
float
timestamp
boolean
```

nesse momento.

Strings vazias também são inicialmente preservadas como strings vazias.

A conversão semântica acontece na Silver.

---

# RN-BRZ-006 — Nomes de colunas são normalizados

Espaços externos são removidos.

Exemplo:

```text
" LAT "
```

torna-se:

```text
"LAT"
```

O conteúdo das células não é alterado por essa regra.

---

# RN-BRZ-007 — Existe um contrato mínimo de colunas

O arquivo precisa possuir todas as colunas:

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
INT_BATT
ODO_TRIP
ODO_TOTAL
HORIMETER
HDOP
MCC
MNC
LAC
CELL_ID
RX_LEVEL
SER_COUNT
TX_TECH
GRP_MSG
IO_STATUS
DRIVER_ID
PASS_ID
RPM
TACHO_SPD
TACHO_ODO
TEMP_1
TEMP_2
TEMP_3
TEMP_4
```

Se qualquer uma delas estiver ausente:

```text
arquivo inteiro
→ VALIDATION_FAILED
```

---

# RN-BRZ-008 — Colunas adicionais são permitidas

O contrato Bronze é:

```text
colunas obrigatórias
+
zero ou mais colunas adicionais
```

Portanto:

```text
coluna extra
```

não invalida automaticamente o arquivo.

---

# RN-BRZ-009 — Metadados internos não podem vir da fonte

As seguintes colunas são reservadas:

```text
source_file
source_file_hash
source_row_number
row_id
batch_id
ingested_at
ingestion_date
```

Elas devem ser produzidas exclusivamente pela plataforma.

Se o CSV recebido já possuir alguma dessas colunas:

```text
arquivo
→ inválido
```

---

# RN-BRZ-010 — Colunas duplicadas são inválidas

Depois da normalização dos nomes, não podem existir nomes duplicados.

Exemplo:

```text
LAT
" LAT "
```

após normalização podem colidir.

Nesse caso:

```text
arquivo
→ inválido
```

---

# RN-BRZ-011 — O conteúdo do arquivo é identificado por SHA-256

Antes do processamento é calculado:

```text
source_file_hash
```

utilizando SHA-256.

A regra de idempotência de arquivo utiliza o conteúdo e não apenas o nome.

Consequentemente:

```text
mesmo conteúdo
+
nome diferente
```

continua representando um arquivo já processado.

---

# RN-BRZ-012 — Arquivo já processado com sucesso é ignorado

Se:

```text
source_file_hash
```

já aparece no controle com processamento bem-sucedido:

```text
status = SKIPPED
```

A causa registrada é:

```text
SOURCE_FILE_HASH_ALREADY_SUCCESSFUL
```

O arquivo não é processado novamente.

---

# RN-BRZ-013 — Arquivo ignorado é arquivado

Quando um arquivo é identificado como já processado:

```text
inbox
 ↓
SKIPPED
 ↓
archive
```

Ele não é enviado para quarantine porque seu conteúdo não é inválido.

---

# RN-BRZ-014 — Arquivo inválido é enviado para quarantine

Falhas de:

```text
hash
validação
persistência Bronze
```

resultam em:

```text
failed
 ↓
quarantine
```

O arquivo não é simplesmente apagado.

---

# RN-BRZ-015 — Arquivo processado com sucesso é arquivado

Depois da persistência bem-sucedida:

```text
inbox
 ↓
Bronze
 ↓
SUCCESS
 ↓
archive
```

---

# RN-BRZ-016 — Toda tentativa recebe um novo `batch_id`

Mesmo que posteriormente o arquivo seja identificado como duplicado:

```text
tentativa
→ novo batch_id
```

O `batch_id` representa a tentativa operacional e não a identidade permanente do arquivo.

---

# RN-BRZ-017 — Toda linha recebe linhagem técnica

A Bronze adiciona:

```text
source_file
source_file_hash
source_row_number
row_id
batch_id
ingested_at
ingestion_date
```

Esses campos acompanham o registro durante o restante do pipeline quando aplicável.

---

# RN-BRZ-018 — `source_row_number` começa em 1

A primeira linha de dados recebe:

```text
source_row_number = 1
```

e assim sucessivamente.

---

# RN-BRZ-019 — `row_id` é determinístico

O identificador é produzido a partir de:

```text
SHA256(
    source_file_hash
    +
    source_row_number
)
```

O `batch_id` não participa desse cálculo.

Isso garante:

```text
mesma linha reprocessada
→ mesmo row_id
```

---

# RN-BRZ-020 — O horário de ingestão é normalizado para UTC

`ingested_at` utiliza UTC.

`ingestion_date` é derivado desse instante.

---

# RN-BRZ-021 — A Bronze é insert-only por `row_id`

Depois da primeira criação da tabela:

```text
row_id já existe
→ não alterar

row_id não existe
→ inserir
```

A Bronze não atualiza uma linha histórica que já foi persistida.

---

# RN-BRZ-022 — Duplicidade de linha não gera nova linha

Se uma linha já existe:

```text
duplicate_row_count += 1
```

e:

```text
inserted_row_count
```

não aumenta.

---

# RN-BRZ-023 — Apenas batches com dados novos são propagados

Um batch somente entra em:

```text
BronzeLoadResult.batch_ids
```

se:

```text
inserted_row_count > 0
```

Assim:

```text
arquivo processado
+
nenhuma linha nova
        ↓
não dispara processamento incremental desnecessário
```

---

# 5. Regras de negócio da Silver

# RN-SLV-001 — A Silver exige o contrato Bronze

Antes de processar, a Silver exige as colunas obrigatórias da fonte e os metadados Bronze.

Se o contrato físico da Bronze não estiver disponível:

```text
processamento Silver
→ falha explícita
```

---

# RN-SLV-002 — Strings são normalizadas

Os campos textuais passam por:

```text
TRIM
```

e:

```text
string vazia
→ NULL
```

---

# RN-SLV-003 — Timestamp do equipamento possui prioridade

O instante lógico do evento é:

```text
device_timestamp
```

quando válido.

Caso contrário:

```text
server_timestamp
```

é utilizado.

Formalmente:

```text
event_timestamp
=
COALESCE(
    device_timestamp,
    server_timestamp
)
```

---

# RN-SLV-004 — Timestamp inválido não derruba a transformação

A Silver utiliza conversões tolerantes.

Portanto:

```text
timestamp ilegível
→ NULL
```

e não uma falha global de processamento.

---

# 6. Resolução de identidade

# RN-ID-001 — `device_serial_raw` nunca é sobrescrito

O valor original recebido permanece disponível para:

```text
auditoria
diagnóstico
linhagem
```

A identidade tratada fica em:

```text
device_serial
```

---

# RN-ID-002 — Serial direto possui prioridade absoluta

Se `device_serial_raw` puder ser normalizado:

```text
device_resolution_method
=
DIRECT
```

Nenhuma inferência por IMEI é necessária.

---

# RN-ID-003 — Prefixo `M` é removido do serial canônico

Exemplo:

```text
M202527000021P
```

torna-se:

```text
202527000021P
```

O bruto continua:

```text
device_serial_raw
=
M202527000021P
```

---

# RN-ID-004 — Ausência de identidade não implica inferência automática

Se não houver serial direto, o comportamento padrão é:

```text
UNRESOLVED
```

A inferência somente acontece quando todas as condições da estratégia legada são satisfeitas.

---

# RN-ID-005 — IMEI válido possui exatamente 15 dígitos

Para servir como evidência:

```text
^[0-9]{15}$
```

deve ser atendido.

Exemplos inválidos:

```text
354173560222769]
```

```text
35417356022276
```

```text
ABC173560222769
```

Esses valores não participam da inferência.

---

# RN-ID-006 — Relação IMEI → serial deve ser inequívoca

Se um IMEI estiver associado a:

```text
um único serial
```

ele pode entrar no mapa de referência.

Se estiver associado a:

```text
mais de um serial
```

a relação é descartada.

A plataforma não escolhe arbitrariamente entre identidades conflitantes.

---

# RN-ID-007 — Relação direta é construída a partir de T1

Para produzir evidência direta:

```text
message_type = T1
```

é obrigatório.

Além disso, devem existir:

```text
timestamp válido
serial direto
IMEI válido
```

---

# RN-ID-008 — Em T1, determinados campos possuem semântica de identidade

Na interpretação atual do protocolo:

```text
BAT_VOLT
→ ICCID

LAT
→ IMSI

LONT
→ IMEI
```

Essa interpretação ocorre especificamente no produto:

```text
device_identity_events
```

---

# RN-ID-009 — Inferência legada é restrita ao protocolo `V14.06.111`

Somente um registro com:

```text
protocol_version
=
V14.06.111
```

pode receber:

```text
device_resolution_method
=
LEGACY_IMEI
```

pela estratégia atual.

Protocolos como:

```text
V14.06.117
```

não recebem essa inferência automaticamente.

---

# RN-ID-010 — O registro legado precisa possuir um tipo T válido

O tipo precisa obedecer:

```text
^T[0-9]+$
```

Caso contrário:

```text
UNRESOLVED
```

---

# RN-ID-011 — O registro legado precisa possuir timestamp válido

É necessário possuir:

```text
device_timestamp válido
```

ou:

```text
server_timestamp válido
```

Caso contrário a inferência não é aplicada.

---

# RN-ID-012 — A inferência legada depende do contexto do arquivo

Para uma linha legada sem serial ser resolvida, o sistema precisa identificar no mesmo:

```text
source_file
```

um IMEI contextual inequívoco proveniente de uma mensagem T1 válida.

---

# RN-ID-013 — A T1 contextual pode ser de outra versão de protocolo

A mensagem T1 usada para descobrir:

```text
source_file → IMEI
```

não precisa ser:

```text
V14.06.111
```

Ela pode pertencer a outra versão.

Isso não altera a regra do registro que recebe a identidade.

O alvo continua obrigatoriamente:

```text
V14.06.111
```

---

# RN-ID-014 — O arquivo precisa possuir um único IMEI T1 válido

Se um arquivo apresentar:

```text
IMEI A
IMEI B
```

como IMEIs T1 válidos distintos:

```text
o arquivo não fornece contexto inequívoco
```

e a inferência não é realizada com essa evidência.

---

# RN-ID-015 — Evidência histórica incremental não pode depender de inferência anterior

Durante processamento incremental, a Silver pode utilizar:

```text
device_identity_events
```

já persistido.

Porém a relação histórica:

```text
IMEI → serial
```

é construída a partir de:

```text
device_serial_raw
```

e não de:

```text
device_serial inferido
```

Isso evita:

```text
inferência
→ justificar outra inferência
→ justificar outra inferência
```

---

# RN-ID-016 — Conflito entre evidência atual e histórica invalida a associação

Ao combinar mapas:

```text
histórico
+
batch atual
```

o IMEI precisa continuar associado a:

```text
um único serial
```

Se surgir conflito:

```text
associação
→ descartada
```

---

# RN-ID-017 — Métodos possíveis de resolução

Todo registro recebe conceitualmente um dos estados:

```text
DIRECT
LEGACY_IMEI
UNRESOLVED
```

Significados:

```text
DIRECT
→ identidade veio do próprio registro

LEGACY_IMEI
→ identidade foi inferida por evidência inequívoca

UNRESOLVED
→ evidência insuficiente
```

---

# 7. Classificação Silver

# RN-SLV-005 — Tipos de mensagem válidos obedecem `T<n>`

Um `message_type` válido deve obedecer:

```text
^T[0-9]+$
```

Exemplos válidos:

```text
T1
T2
T3
T14
```

Exemplos inválidos:

```text
HTTP
MQTT
PING
RTSP
ABC
```

---

# RN-SLV-006 — `T1` representa identidade

Se:

```text
message_type = T1
+
timestamp válido
+
device_serial resolvido
```

o registro é enviado para:

```text
device_identity_events
```

---

# RN-SLV-007 — Outros `T<n>` representam telemetria

Se:

```text
message_type = T<n>
```

e:

```text
message_type != T1
```

e ainda houver:

```text
timestamp válido
device_serial resolvido
```

o registro é enviado para:

```text
telemetry_events
```

---

# RN-SLV-008 — Motivos de rejeição possuem precedência

A classificação atual utiliza a seguinte ordem:

```text
1. MISSING_MESSAGE_TYPE
2. INVALID_MESSAGE_TYPE
3. MISSING_OR_INVALID_TIMESTAMP
4. MISSING_DEVICE_SERIAL
```

Isso significa que uma linha com múltiplos problemas recebe:

```text
o primeiro motivo aplicável
```

e não múltiplos motivos simultâneos.

---

# RN-SLV-009 — Mensagem ausente é rejeitada

Se:

```text
message_type IS NULL
```

o motivo é:

```text
MISSING_MESSAGE_TYPE
```

---

# RN-SLV-010 — Tipo de mensagem inválido é rejeitado

Se o campo existe, mas não corresponde a:

```text
T<n>
```

o motivo é:

```text
INVALID_MESSAGE_TYPE
```

---

# RN-SLV-011 — Ausência de ambos os timestamps rejeita a linha

Se:

```text
device_timestamp = NULL
```

e:

```text
server_timestamp = NULL
```

o motivo é:

```text
MISSING_OR_INVALID_TIMESTAMP
```

---

# RN-SLV-012 — Ausência de identidade canônica rejeita a linha

Depois da resolução:

```text
device_serial IS NULL
```

resulta em:

```text
MISSING_DEVICE_SERIAL
```

A classificação não utiliza:

```text
device_serial_raw
```

para essa decisão.

---

# RN-SLV-013 — Registros rejeitados são preservados

Uma rejeição não significa:

```text
DROP
```

Ela é persistida em:

```text
rejected_logs
```

junto com:

```text
rejection_reason
linhagem
dados normalizados disponíveis
identidade disponível
método de resolução
```

---

# RN-SLV-014 — Rejeição sem data pertence a `unknown`

Quando nenhum timestamp pode produzir uma data:

```text
rejection_date
=
unknown
```

Isso garante que registros temporalmente inválidos continuem mensuráveis.

---

# 8. Tipagem e qualidade de telemetria

# RN-TEL-001 — Conversão numérica inválida gera NULL

Campos como:

```text
speed
latitude
longitude
hdop
odometer
battery
temperature
```

são convertidos de forma tolerante.

Valor impossível de converter:

```text
→ NULL
```

Isso, isoladamente, não rejeita o registro.

---

# RN-TEL-002 — Coordenadas são válidas pela faixa geográfica

Uma coordenada é considerada válida quando:

```text
latitude existe
longitude existe
-90 <= latitude <= 90
-180 <= longitude <= 180
```

Caso contrário:

```text
has_valid_coordinates = FALSE
```

---

# RN-TEL-003 — Coordenadas ausentes possuem qualidade específica

Se latitude ou longitude estiver ausente:

```text
position_quality
=
MISSING_COORDINATES
```

---

# RN-TEL-004 — Coordenadas fora da faixa são inválidas

Se as coordenadas excederem a faixa geográfica:

```text
position_quality
=
INVALID_COORDINATES
```

---

# RN-TEL-005 — HDOP acima de 5 representa baixa precisão

Se as coordenadas são utilizáveis e:

```text
hdop > 5
```

então:

```text
position_quality
=
LOW_GPS_PRECISION
```

Essa classificação não transforma:

```text
has_valid_coordinates
```

em `FALSE`.

Ou seja:

```text
coordenada válida
+
HDOP alto
        ↓
has_valid_coordinates = TRUE
position_quality = LOW_GPS_PRECISION
```

---

# RN-TEL-006 — Demais posições ficam como `VALID`

Quando não existe problema de coordenada nem HDOP acima de 5:

```text
position_quality
=
VALID
```

---

# RN-TEL-007 — `(0, 0)` possui tratamento especial posterior

Na validação básica de faixa:

```text
latitude = 0
longitude = 0
```

está dentro dos limites geográficos.

Portanto:

```text
has_valid_coordinates = TRUE
```

na Silver.

Porém a Gold aplica uma regra adicional para:

```text
última posição
rota
```

e exclui explicitamente:

```text
(0, 0)
```

Essa diferença é importante.

---

# 9. Qualidade dos identificadores de identidade

# RN-IDE-001 — ICCID é validado por formato

É considerado formato válido quando possui:

```text
18 a 22 dígitos
```

A falha não rejeita automaticamente a mensagem T1.

Ela gera:

```text
has_valid_iccid_format = FALSE
```

---

# RN-IDE-002 — IMSI é validado por formato

É considerado formato válido com:

```text
14 a 16 dígitos
```

A falha é registrada como indicador de qualidade.

---

# RN-IDE-003 — IMEI é validado por formato

É considerado válido com:

```text
15 dígitos
```

A falha produz:

```text
has_valid_imei_format = FALSE
```

Isso não significa automaticamente rejeição da T1 se os demais requisitos de classificação estiverem presentes.

---

# 10. Processamento incremental da Silver

# RN-SLV-015 — `batch_ids=None` significa FULL explícito

Quando:

```python
batch_ids is None
```

a Silver executa:

```text
FULL
```

---

# RN-SLV-016 — `batch_ids=()` não significa FULL

Quando:

```python
batch_ids == ()
```

e as três tabelas Silver existem e são compatíveis:

```text
NOOP
```

Essa regra impede rebuild completo durante uma execução ociosa do pipeline.

---

# RN-SLV-017 — Silver ausente ou incompatível exige recuperação FULL

O incremental somente é permitido se existirem e forem compatíveis:

```text
telemetry_events
device_identity_events
rejected_logs
```

Se qualquer produto estiver:

```text
ausente
incompleto
incompatível com o schema atual
```

o processamento muda para:

```text
FULL de recuperação/migração
```

mesmo quando nenhum batch novo foi recebido.

---

# RN-SLV-018 — Batch inexistente produz NOOP

Se os `batch_ids` solicitados não existirem na Bronze ou não afetarem nenhuma partição:

```text
Silver
→ NOOP
```

---

# RN-SLV-019 — Batch identifica datas afetadas, não linhas finais

No incremental:

```text
batch_id
```

é utilizado apenas para descobrir:

```text
event_dates afetadas
rejection_dates afetadas
```

Depois disso o processamento não fica limitado às linhas do batch.

---

# RN-SLV-020 — A partição inteira afetada é reconstruída

Depois que uma data é identificada:

```text
todas as linhas Bronze dessa data
```

são recarregadas.

Não apenas:

```text
linhas do novo batch
```

Isso garante tratamento correto de dados atrasados.

---

# RN-SLV-021 — Dados atrasados recompõem o estado histórico

Exemplo:

```text
partição 2026-03-20 já existe
        ↓
novo batch traz evento de 2026-03-20
        ↓
2026-03-20 é afetada
        ↓
Silver recarrega todo 2026-03-20
        ↓
substitui partição completa
```

---

# RN-SLV-022 — `unknown` também é uma partição lógica de rejeição

Se um novo batch contém linha sem qualquer timestamp válido:

```text
unknown
```

entra no escopo afetado e precisa ser reconstruído.

---

# 11. Regras da Gold

# RN-GLD-001 — A Gold exige os três produtos Silver

Para processar, precisam existir:

```text
telemetry_events
device_identity_events
rejected_logs
```

A ausência de qualquer um deles impede o processamento Gold normal.

---

# RN-GLD-002 — Telemetria e identidade possuem deduplicação lógica

Os principais produtos Gold não operam diretamente sobre cada linha Silver sem tratamento.

São criadas bases deduplicadas para:

```text
telemetry
identity
```

---

# RN-GLD-003 — Deduplicação de telemetria

Um evento de telemetria é considerado logicamente equivalente utilizando:

```text
device_serial
event_timestamp
message_type
serial_count
latitude
longitude
speed
```

Quando existem múltiplos equivalentes, é priorizado o registro com:

```text
server_timestamp mais recente
```

e, como desempate:

```text
source_file
```

---

# RN-GLD-004 — Deduplicação de identidade

Uma identidade é comparada por:

```text
device_serial
event_timestamp
imei
imsi
iccid
```

O registro mais recente por:

```text
server_timestamp
```

possui prioridade.

---

# RN-GLD-005 — `data_quality_summary` não usa essa deduplicação

Essa é uma exceção importante.

Qualidade mede:

```text
quantos registros a Silver aceitou ou rejeitou
```

Portanto utiliza diretamente:

```text
telemetry_events
device_identity_events
rejected_logs
```

sem a deduplicação das views Gold.

---

# 12. `dim_device`

# RN-DIM-001 — Um dispositivo existe se possuir identidade ou telemetria

O conjunto de dispositivos é:

```text
devices de identity
UNION
devices de telemetry
```

Portanto um dispositivo pode existir mesmo sem evento T1.

---

# RN-DIM-002 — Primeira atividade é a menor data observada

```text
first_seen_at
```

é calculado considerando:

```text
identidade
+
telemetria
```

---

# RN-DIM-003 — Última atividade é a atividade mais recente

```text
last_seen_at
```

também considera ambas as fontes.

---

# RN-DIM-004 — Identidade atual é a identidade T1 mais recente

Campos como:

```text
current_imei
current_imsi
current_iccid
current_identity_auxiliary
```

são obtidos do evento de identidade mais recente.

---

# RN-DIM-005 — Versão atual do protocolo prioriza identidade

A regra é:

```text
protocol_version da identidade mais recente
```

quando disponível.

Caso contrário:

```text
protocol_version da telemetria mais recente
```

---

# RN-DIM-006 — Quantidades de eventos são mantidas separadas

A dimensão mantém:

```text
identity_event_count
telemetry_event_count
```

e também:

```text
has_identity_event
has_telemetry_event
```

---

# 13. `device_last_position`

# RN-POS-001 — Existe no máximo uma última posição por dispositivo

O produto:

```text
device_last_position
```

representa o estado atual da última posição publicável de cada dispositivo.

---

# RN-POS-002 — Somente coordenadas válidas podem ser última posição

É obrigatório:

```text
has_valid_coordinates = TRUE
```

---

# RN-POS-003 — `(0, 0)` nunca pode ser última posição

Mesmo estando dentro da faixa geográfica:

```text
latitude = 0
longitude = 0
```

é explicitamente excluído desse produto.

---

# RN-POS-004 — A posição com maior `event_timestamp` vence

A seleção ocorre prioritariamente por:

```text
event_timestamp DESC
```

---

# RN-POS-005 — `server_timestamp` é desempate

Em empate de `event_timestamp`:

```text
server_timestamp DESC
```

possui prioridade.

---

# RN-POS-006 — `serial_count` é outro desempate

Persistindo o empate:

```text
serial_count DESC
```

é utilizado.

---

# RN-POS-007 — Baixa precisão GPS ainda pode ser publicada

Uma posição:

```text
LOW_GPS_PRECISION
```

pode possuir:

```text
has_valid_coordinates = TRUE
```

e, portanto, pode participar da escolha da última posição.

A qualidade é preservada no campo:

```text
position_quality
```

para o consumidor decidir como utilizá-la.

---

# 14. `device_route_points`

# RN-RTE-001 — A rota utiliza somente posições geograficamente utilizáveis

É necessário:

```text
has_valid_coordinates = TRUE
```

e:

```text
(latitude, longitude) != (0, 0)
```

---

# RN-RTE-002 — A rota é organizada por dispositivo e dia

Cada ponto pertence a:

```text
event_date
device_serial
```

---

# RN-RTE-003 — `point_sequence` reinicia diariamente

A sequência é calculada dentro de:

```text
device_serial
+
event_date
```

Portanto:

```text
novo dia
→ sequência volta a 1
```

---

# RN-RTE-004 — Ordem da sequência

Os pontos são ordenados por:

```text
event_timestamp
received_at
serial_count
```

---

# RN-RTE-005 — Movimento utiliza limiar de velocidade 5

A regra atual é:

```text
speed >= 5
→ is_moving = TRUE

speed < 5
→ is_moving = FALSE

speed NULL
→ tratado como 0 para is_moving
```

---

# 15. `device_daily_summary`

# RN-DAY-001 — A granularidade é dispositivo por dia

A chave lógica é:

```text
event_date
+
device_serial
```

---

# RN-DAY-002 — `message_count` conta eventos da base Gold de telemetria

É calculado como:

```text
COUNT(*)
```

por dispositivo/dia após a deduplicação Gold de telemetria.

---

# RN-DAY-003 — Tipos distintos são contabilizados

```text
distinct_message_type_count
```

representa a quantidade de `message_type` diferentes observados naquele dia.

---

# RN-DAY-004 — Posições válidas são contabilizadas por `has_valid_coordinates`

```text
valid_position_count
```

conta:

```text
has_valid_coordinates = TRUE
```

e:

```text
invalid_position_count
```

conta o restante.

Importante:

```text
(0, 0)
```

é considerado dentro da faixa pela Silver.

Portanto ele pode entrar nessa métrica como coordenada válida, embora seja excluído de:

```text
device_last_position
device_route_points
```

Essa é a semântica atual do sistema.

---

# RN-DAY-005 — Baixa precisão é contabilizada separadamente

```text
low_gps_precision_count
```

conta:

```text
position_quality
=
LOW_GPS_PRECISION
```

---

# RN-DAY-006 — Percentual de posições válidas

A regra é:

```text
valid_position_count
------------------------ × 100
message_count
```

com arredondamento para duas casas.

---

# RN-DAY-007 — Movimento diário utiliza velocidade >= 5

```text
speed >= 5
→ moving_event_count
```

---

# RN-DAY-008 — Parada exige velocidade conhecida menor que 5

```text
speed IS NOT NULL
AND
speed < 5
→ stopped_event_count
```

Uma velocidade `NULL` não entra como evento parado nessa métrica.

---

# RN-DAY-009 — Velocidade média considera valores conhecidos

É calculada:

```text
average_speed
```

sobre valores de `speed` disponíveis.

---

# RN-DAY-010 — Velocidade média em movimento considera apenas `speed >= 5`

```text
average_speed_while_moving
```

exclui eventos abaixo do limiar.

---

# RN-DAY-011 — Velocidade máxima diária é preservada

```text
maximum_speed
=
MAX(speed)
```

---

# RN-DAY-012 — HDOP possui métricas diária média, mínima e máxima

São produzidos:

```text
average_hdop
minimum_hdop
maximum_hdop
```

---

# RN-DAY-013 — Baterias possuem métricas agregadas

Para:

```text
battery_voltage
internal_battery
```

são calculados:

```text
mínimo
máximo
média
```

---

# RN-DAY-014 — O delta de odômetro não pode ser negativo

São encontrados:

```text
first_odometer_total
last_odometer_total
```

Se:

```text
last >= first
```

então:

```text
odometer_delta_raw
=
last - first
```

Se:

```text
last < first
```

então:

```text
odometer_delta_raw = NULL
has_odometer_regression = TRUE
```

A plataforma não transforma regressão em distância negativa.

---

# RN-DAY-015 — Primeira e última posição válida do dia são preservadas

São mantidos:

```text
first_valid_position_at
last_valid_position_at
first_latitude
first_longitude
last_latitude
last_longitude
```

utilizando eventos com:

```text
has_valid_coordinates = TRUE
```

---

# 16. `data_quality_summary`

# RN-QLT-001 — Qualidade mede registros processados pela Silver

A métrica utiliza:

```text
telemetry_events
device_identity_events
rejected_logs
```

diretamente.

---

# RN-QLT-002 — Eventos aceitos

```text
accepted_event_count
=
telemetry_event_count
+
identity_event_count
```

---

# RN-QLT-003 — Total processado

```text
total_event_count
=
telemetry_event_count
+
identity_event_count
+
rejected_event_count
```

---

# RN-QLT-004 — Percentual de rejeição

```text
rejection_percentage
=
rejected_event_count
------------------------
total_event_count
× 100
```

O resultado é arredondado para quatro casas decimais.

---

# RN-QLT-005 — Motivos de rejeição são contabilizados

O produto mantém contagens de:

```text
MISSING_MESSAGE_TYPE

INVALID_MESSAGE_TYPE

MISSING_OR_INVALID_TIMESTAMP

MISSING_DEVICE_SERIAL

UNKNOWN_REJECTION_REASON
```

---

# RN-QLT-006 — Datas podem existir somente em uma fonte

Uma data entra no resumo se aparecer em:

```text
telemetry
```

ou:

```text
identity
```

ou:

```text
rejected
```

Não é necessário existir atividade nas três fontes.

---

# RN-QLT-007 — Ausência de uma categoria equivale a zero

Exemplo:

```text
data possui telemetria
mas nenhuma rejeição
```

então:

```text
rejected_event_count = 0
```

---

# RN-QLT-008 — `unknown` é preservado como período de qualidade

Rejeições sem data válida são agregadas em:

```text
metric_date = unknown
```

Elas não desaparecem das métricas.

---

# 17. Incrementalidade da Gold

# RN-GLD-006 — Gold sem resultado Silver explícito executa FULL

Quando:

```python
silver_result is None
```

a Gold executa:

```text
FULL
```

---

# RN-GLD-007 — Silver FULL provoca Gold FULL

Se:

```text
Silver.mode = FULL
```

a Gold também reconstrói integralmente seus produtos.

---

# RN-GLD-008 — Silver NOOP permite Gold NOOP

Se:

```text
Silver = NOOP
```

e todos os produtos Gold necessários já existem:

```text
Gold = NOOP
```

---

# RN-GLD-009 — Gold incompleta provoca FULL de recuperação

Incrementalidade exige os cinco produtos:

```text
dim_device
device_last_position
device_route_points
device_daily_summary
data_quality_summary
```

Se algum estiver ausente:

```text
FULL
```

---

# RN-GLD-010 — Datas de evento afetam dispositivos

Para cada:

```text
event_date
```

afetada pela Silver, a Gold descobre os dispositivos presentes em:

```text
telemetry_events
device_identity_events
```

nessa data.

---

# RN-GLD-011 — Produtos por dispositivo são recalculados para dispositivos afetados

Os dispositivos encontrados alimentam:

```text
dim_device
device_last_position
```

---

# RN-GLD-012 — Produtos históricos são recalculados por data

As `event_dates` afetadas alimentam:

```text
device_route_points
device_daily_summary
```

---

# RN-GLD-013 — Qualidade pode mudar por evento aceito ou rejeição

As datas afetadas de qualidade são:

```text
event_dates
UNION
rejection_dates
```

Portanto:

```text
nova telemetria
```

pode mudar qualidade.

E:

```text
nova rejeição
```

também pode mudar qualidade.

---

# 18. Regras do pipeline

# RN-PIP-001 — A ordem obrigatória é Bronze → Silver → Gold

Uma execução normal segue:

```text
load_bronze()
        ↓
load_silver()
        ↓
load_gold()
```

---

# RN-PIP-002 — A Bronze controla quais batches chegam à Silver

O pipeline passa:

```python
bronze_result.batch_ids
```

para a Silver.

Como a Bronze só inclui batches que inseriram linhas:

```text
sem linha nova
→ nenhum batch propagado
```

---

# RN-PIP-003 — Ambiente inicial vazio é válido

Se:

```text
inbox vazio
+
Bronze ainda não existe
```

o sistema não trata isso como erro.

O resultado é:

```text
Bronze sem dados
Silver NOOP
Gold NOOP
```

---

# RN-PIP-004 — `has_new_data` significa nova linha Bronze

```text
PipelineResult.has_new_data
```

é verdadeiro quando:

```text
Bronze inseriu novas linhas
```

---

# RN-PIP-005 — `has_changes` é mais amplo

`has_changes` também considera:

```text
rebuild Silver
rebuild Gold
```

mesmo que nenhum arquivo novo tenha sido ingerido.

Isso permite distinguir:

```text
dados novos
```

de:

```text
mudança real de estado da plataforma
```

---

# 19. Regras da Query Layer

# RN-QRY-001 — Query Layer é somente leitura

A Query Layer não:

```text
cria Gold
reconstrói Gold
altera Gold
ingere arquivos
```

Ela apenas consulta produtos já publicados.

---

# RN-QRY-002 — Gold ausente gera erro explícito

Se o produto solicitado não existir:

```text
FileNotFoundError
```

A Query Layer não cria silenciosamente a tabela.

---

# RN-QRY-003 — `device_serial` obrigatório não pode ser vazio

Após `TRIM`:

```text
""
```

não é um filtro válido.

---

# RN-QRY-004 — Paginação possui limite padrão

Por padrão:

```text
limit = 100
offset = 0
```

---

# RN-QRY-005 — Limite máximo é 1000

```text
1 <= limit <= 1000
```

---

# RN-QRY-006 — Offset não pode ser negativo

```text
offset >= 0
```

---

# RN-QRY-007 — Datas utilizam ISO `YYYY-MM-DD`

Filtros temporais precisam utilizar:

```text
YYYY-MM-DD
```

---

# RN-QRY-008 — Intervalo invertido é inválido

Quando ambos existem:

```text
start_date <= end_date
```

é obrigatório.

---

# RN-QRY-009 — Consultas temporais utilizam colunas de partição

Rota e resumo diário utilizam:

```text
event_date
```

Qualidade utiliza:

```text
metric_date
```

Isso mantém a consulta alinhada ao particionamento físico.

---

# RN-QRY-010 — Páginas retornam metadados

Uma `QueryPage` contém:

```text
items
total
limit
offset
returned
has_more
next_offset
```

---

# RN-QRY-011 — `total` ignora LIMIT/OFFSET

```text
total
```

representa todos os registros que satisfazem os filtros antes da paginação.

---

# RN-QRY-012 — Ordenação deve ser determinística

Exemplos:

```text
devices
→ device_serial
```

```text
route
→ event_timestamp, point_sequence
```

```text
daily summaries
→ event_date DESC, device_serial
```

Isso evita páginas inconsistentes entre consultas equivalentes.

---

# 20. Regras da REST API

# RN-API-001 — A API é read-only

A implementação atual expõe operações de leitura.

Não existem endpoints de:

```text
POST para alterar Gold
PUT
PATCH
DELETE
```

---

# RN-API-002 — API não acessa Delta diretamente

O fluxo obrigatório é:

```text
REST API
   ↓
QueryService
   ↓
Gold
```

Não deve existir regra de acesso:

```text
route
→ DeltaTable
```

---

# RN-API-003 — API não contém SQL de negócio

Filtros e consultas pertencem à:

```text
Query Layer
```

A rota HTTP deve apenas:

```text
validar HTTP
chamar QueryService
serializar
retornar status
```

---

# RN-API-004 — Health não depende da Gold

```text
GET /health
```

responde:

```json
{
    "status": "ok"
}
```

mesmo que os produtos Gold ainda não existam.

Esse endpoint representa:

```text
processo HTTP ativo
```

e não:

```text
dados disponíveis
```

---

# RN-API-005 — Dispositivo inexistente retorna 404

Em:

```text
GET /api/v1/devices/{device_serial}
```

se não existir registro:

```text
404
```

---

# RN-API-006 — Última posição inexistente retorna 404

Em:

```text
GET /api/v1/devices/{device_serial}/last-position
```

se não existir posição publicável:

```text
404
```

---

# RN-API-007 — Consulta de rota vazia não é necessariamente erro

Uma consulta válida pode retornar:

```text
items = []
total = 0
```

Isso representa uma consulta sem resultados e não obrigatoriamente um recurso HTTP inexistente.

---

# RN-API-008 — Parâmetros semanticamente inválidos resultam em 422

Exemplo:

```text
start_date > end_date
```

resulta em:

```text
422
```

---

# RN-API-009 — Gold indisponível resulta em 503

Se o produto Gold necessário não existir:

```text
503 Service Unavailable
```

A resposta exposta é:

```json
{
    "detail": "Gold data is not available."
}
```

---

# RN-API-010 — Caminhos internos não são expostos

Embora a Query Layer conheça o caminho físico da tabela, a API não retorna:

```text
C:\...
data/lakehouse/...
```

em erros públicos de Gold ausente.

---

# RN-API-011 — NaN/NaT não são enviados diretamente

Antes da resposta HTTP:

```text
NaN
NaT
```

são transformados em:

```text
None
```

e consequentemente:

```json
null
```

---

# RN-API-012 — CORS é fechado por padrão

A configuração padrão é:

```python
api_cors_origins = ()
```

Nenhuma origem externa é adicionada implicitamente.

---

# RN-API-013 — CORS é configurado por ambiente

A variável utilizada é:

```text
QUEO_API_CORS_ORIGINS
```

Exemplo:

```text
http://localhost:5173,https://app.example.com
```

---

# RN-API-014 — Origens duplicadas são removidas

A configuração:

```text
A,B,A
```

torna-se:

```text
A,B
```

preservando a ordem.

---

# RN-API-015 — CORS autoriza somente leitura na configuração atual

O middleware é configurado para:

```text
GET
```

coerentemente com a natureza read-only da API atual.

---

# 21. Produtos disponíveis externamente

A API atual expõe:

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

Esses endpoints correspondem aos produtos:

```text
dim_device

device_last_position

device_route_points

device_daily_summary

data_quality_summary
```

---

# 22. Regras arquiteturais para consumidores externos

A fronteira pública da plataforma é:

```text
REST API
```

Consumidores externos não devem depender diretamente de:

```text
Delta Lake
DuckDB
diretórios Gold
```

A arquitetura recomendada é:

```text
Consumidor
    ↓
REST API
    ↓
Query Layer
    ↓
Gold
```

Se um MCP existir como serviço separado, a integração recomendada é:

```text
MCP Service
    ↓
REST API
    ↓
QueryService
    ↓
Gold
```

e não:

```text
MCP externo
    ↓
Delta diretamente
```

---

# 23. Pontos importantes da semântica atual

## Bronze aceita arquivos semanticamente ruins

Desde que o contrato estrutural esteja correto:

```text
timestamp ruim
coordenada ruim
message_type ruim
serial ausente
```

não invalidam necessariamente o arquivo inteiro.

A Silver decide o destino linha a linha.

---

## Uma rejeição não significa perda do dado

```text
rejected_logs
```

faz parte formal da Silver.

Rejeições são dados observáveis.

---

## Uma identidade inferida nunca deve ser um palpite

`LEGACY_IMEI` exige:

```text
protocolo elegível
mensagem elegível
timestamp
arquivo
IMEI contextual inequívoco
mapa IMEI → serial inequívoco
```

Na ausência dessas condições:

```text
UNRESOLVED
```

---

## Baixa precisão GPS não é igual a coordenada inválida

```text
HDOP > 5
```

resulta em:

```text
LOW_GPS_PRECISION
```

mas pode continuar com:

```text
has_valid_coordinates = TRUE
```

---

## `(0,0)` possui duas interpretações atuais

Na Silver:

```text
(0,0)
→ dentro da faixa
→ has_valid_coordinates = TRUE
```

Na Gold:

```text
device_last_position
device_route_points
```

excluem `(0,0)` explicitamente.

Por outro lado:

```text
device_daily_summary.valid_position_count
```

usa `has_valid_coordinates` e, portanto, pode considerar `(0,0)` válido.

Essa é uma diferença semântica atual e deve ser levada em consideração em futuras alterações.

---

## Métrica de qualidade mede processamento, não eventos deduplicados

```text
data_quality_summary
```

é baseado diretamente na Silver.

Portanto seu objetivo é responder:

```text
quantos registros foram aceitos ou rejeitados?
```

e não:

```text
quantos eventos lógicos únicos existem?
```

---

# 24. Resumo da decisão de cada linha

O fluxo conceitual de um registro pode ser representado como:

```text
Arquivo
  │
  ├── estrutura inválida
  │       ↓
  │   quarantine
  │
  └── estrutura válida
          ↓
        Bronze
          ↓
     normalização
          ↓
 resolução de identidade
          ↓
   message_type existe?
          │
      não ─────→ MISSING_MESSAGE_TYPE
          │
         sim
          ↓
    corresponde T<n>?
          │
      não ─────→ INVALID_MESSAGE_TYPE
          │
         sim
          ↓
   possui timestamp?
          │
      não ─────→ MISSING_OR_INVALID_TIMESTAMP
          │
         sim
          ↓
 device_serial resolvido?
          │
      não ─────→ MISSING_DEVICE_SERIAL
          │
         sim
          ↓
       é T1?
       │    │
      sim   não
       │    │
       ▼    ▼
  identidade telemetria
       │    │
       └─┬──┘
         ▼
        Gold
         ↓
     Query Layer
         ↓
      REST API
```

---

# 25. Resumo de FULL, INCREMENTAL e NOOP

## Silver

```text
batch_ids=None
→ FULL
```

```text
batch_ids=()
+
Silver completa
→ NOOP
```

```text
batch_ids=()
+
Silver ausente/incompatível
→ FULL de recuperação
```

```text
batch_ids existentes
+
Silver completa
→ INCREMENTAL
```

```text
batch_ids desconhecidos
→ NOOP
```

---

## Gold

```text
sem SilverLoadResult
→ FULL
```

```text
Silver FULL
→ Gold FULL
```

```text
Silver INCREMENTAL
+
Gold completa
→ Gold INCREMENTAL
```

```text
Silver NOOP
+
Gold completa
→ Gold NOOP
```

```text
Gold incompleta
→ FULL de recuperação
```

---

# 26. Regra central do sistema

A regra que resume a arquitetura atual é:

```text
preservar primeiro
interpretar depois
consolidar depois
expor por último
```

Ou:

```text
Raw
 ↓
Bronze
preserva e rastreia
 ↓
Silver
interpreta e classifica
 ↓
Gold
consolida regras analíticas
 ↓
Query Layer
consulta
 ↓
REST API
expõe contratos estáveis
```

Essa separação deve ser preservada nas próximas evoluções do sistema.

Uma nova regra não deve ser colocada na camada mais conveniente tecnicamente.

Ela deve ser implementada na camada que possui responsabilidade semântica sobre aquela decisão.