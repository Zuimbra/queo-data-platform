# Diagnóstico do protocolo legado e estratégia de resolução de identidade

## 1. Objetivo deste documento

Este documento registra em profundidade um problema descoberto somente depois que o pipeline passou a ser executado com os arquivos históricos reais.

O problema não era um erro de execução do Lakehouse.

O pipeline estava funcionando corretamente segundo as regras implementadas, porém os dados reais mostraram que uma dessas regras partia de uma premissa que não vale para todo o histórico do protocolo.

A regra era:

```text
mensagem de tracker válida
+
serial do dispositivo ausente
        ↓
MISSING_DEVICE_SERIAL
        ↓
rejected_logs
```

Essa regra continua correta quando não existe forma confiável de identificar o dispositivo.

O que mudou foi a descoberta de que, para uma grande parte dos registros antigos, existe informação suficiente para reconstruir essa identidade de maneira determinística.

O objetivo deste documento é explicar:

```text
como o problema apareceu
como foi investigado
quais evidências foram encontradas
quais hipóteses foram descartadas
por que a regra atual não deve simplesmente ser removida
qual solução foi escolhida
quais garantias a implementação deverá preservar
```

---

# 2. Contexto arquitetural

A plataforma utiliza uma arquitetura medalhão:

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
REST / MCP
```

A Bronze preserva o dado recebido e acrescenta metadados de linhagem.

A Silver interpreta o protocolo e classifica cada linha em:

```text
telemetry_events
device_identity_events
rejected_logs
```

A Gold agrega e consolida a Silver em produtos de consumo.

A decisão de manter rejeições explicitamente em:

```text
rejected_logs
```

foi fundamental para esta investigação.

Em vez de desaparecerem, os registros problemáticos permaneceram disponíveis com:

```text
source_file
source_row_number
rejection_reason
```

Isso permitiu rastrear cada comportamento até os arquivos históricos originais.

---

# 3. Validação operacional antes do diagnóstico

Antes de utilizar os arquivos históricos, o pipeline foi validado em três estados.

## 3.1 Ambiente vazio

```text
inbox vazio
Bronze inexistente
```

Resultado:

```text
Bronze → zero arquivos
Silver → NOOP
Gold   → NOOP
```

Isso confirmou que uma instalação nova pode permanecer ociosa sem gerar erro.

## 3.2 Primeiro processamento

Foi utilizado um CSV artificial de três registros:

```text
T2 válido
T1 válido
mensagem inválida
```

Resultado:

```text
Bronze
→ 3 linhas

Silver FULL
→ 1 telemetry
→ 1 identity
→ 1 rejected

Gold FULL
→ produtos criados
```

## 3.3 Segunda execução sem novos arquivos

Resultado:

```text
Bronze → nenhum batch
Silver → NOOP
Gold   → NOOP
```

## 3.4 Carga histórica real

Depois foram adicionados 74 arquivos reais.

Resultado da Bronze:

```text
74 descobertos
73 processados com sucesso
1 falhou
87.886 linhas inseridas
73 batches propagados
```

Resultado da Silver:

```text
mode = INCREMENTAL
telemetry_rows = 12.822
identity_rows = 804
rejected_rows = 74.260
```

Resultado da Gold:

```text
mode = INCREMENTAL
affected_devices = 3
route_points_rows = 12.790
daily_summary_rows = 60
quality_summary_rows = 94
```

A incrementalidade funcionou.

O volume de rejeições, porém, exigia investigação.

---

# 4. Primeiro problema separado: arquivo histórico sem contrato canônico

O único arquivo rejeitado ainda na Bronze foi:

```text
logs_rastreador_2026-02-24.csv
```

A validação informou que todas as colunas obrigatórias estavam ausentes.

A inspeção bruta mostrou:

```text
2026-02-24 15:11:16,[RX] RAW:,[2026-02-24 15:11:15,T1,1,V14.06.111,...]
2026-02-24 15:11:17,[RX] RAW:,[2026-02-23 22:16:45,T3,0,V14.06.111,...]
```

O arquivo não possui o header canônico:

```text
DATA_SERVIDOR,TIPO_LOG,TM_STAMP,MESS_TYPE,...
```

Ele representa outro estágio/formato de captura.

## 4.1 Decisão

Não flexibilizar a Bronze.

A Bronze atual possui um contrato estrutural claro.

Aceitar automaticamente esse arquivo implicaria transformar a camada de ingestão em um parser de múltiplos formatos implícitos.

A solução correta, se esse formato precisar ser recuperado, é:

```text
raw legado sem header
        ↓
parser/adaptador específico
        ↓
registro canônico de 37 colunas
        ↓
Bronze
```

Portanto a quarantine está funcionando como projetado.

Esse problema é **independente** da resolução de identidade tratada no restante deste documento.

---

# 5. Distribuição das rejeições Silver

Depois da carga histórica, o estado de `rejected_logs` mostrou:

```text
MISSING_DEVICE_SERIAL    55.217
MISSING_MESSAGE_TYPE     18.771
INVALID_MESSAGE_TYPE        273
```

A soma inclui também o registro artificial rejeitado criado anteriormente na validação do bootstrap.

O primeiro ponto importante foi não assumir que todos esses registros tinham a mesma causa.

Foram investigados separadamente:

```text
MISSING_MESSAGE_TYPE
```

e:

```text
MISSING_DEVICE_SERIAL
```

---

# 6. `MISSING_MESSAGE_TYPE`: registros realmente externos ao protocolo

A análise de arquivos como:

```text
logs_rastreador_2026-06-17.csv
```

mostrou tráfego como:

```text
GET / HTTP/1.1
Host: ...
User-Agent: Mozilla/5.0 ...
```

Também apareceram assinaturas como:

```text
MQTT
PING
OPTIONS / RTSP/1.0
```

além de:

```text
payload binário
strings aleatórias
scanners de serviços
requisições HTTP
```

Esses dados chegam no mesmo log de recepção, mas não pertencem ao protocolo dos rastreadores.

## 6.1 Por que não recuperar esses registros?

Não existe evidência de que eles representem telemetria.

Associá-los a um dispositivo apenas por proximidade temporal ou por estarem no mesmo arquivo seria incorreto.

A Silver deve continuar excluindo esses registros dos produtos de negócio.

O comportamento correto é:

```text
payload não reconhecido como mensagem T<n>
        ↓
rejected_logs
```

## 6.2 Melhoria futura de observabilidade

Hoje parte desses casos cai em:

```text
MISSING_MESSAGE_TYPE
```

Uma classificação futura pode distinguir:

```text
NON_TRACKER_PAYLOAD
MISSING_MESSAGE_TYPE
INVALID_MESSAGE_TYPE
```

Isso melhoraria as métricas de qualidade, mas não mudaria a decisão de rejeitar o dado como telemetria.

---

# 7. `MISSING_DEVICE_SERIAL`: o comportamento que revelou uma mudança histórica

O segundo grupo apresentou um padrão completamente diferente.

A distribuição por versão de protocolo foi:

```text
V14.06.111    55.101
V14.06.117       108
1                   8
```

Ou seja, praticamente todo o problema estava concentrado em:

```text
V14.06.111
```

Ao agrupar por tipo de mensagem:

```text
V14.06.111 / T14    52.592
V14.06.111 / T3        794
V14.06.111 / T27       290
V14.06.111 / T28       196
V14.06.111 / T1        161
V14.06.111 / T17       136
...
```

O domínio do `T14` é especialmente relevante, mas o serial ausente não está limitado a um único tipo.

---

# 8. Evidência nos arquivos `V14.06.111`

O arquivo:

```text
logs_rastreador_2026-03-18.csv
```

possui o header canônico correto.

Portanto ele passou pela Bronze normalmente.

Porém seus registros mostram:

```text
2026-03-18 00:19:46,[RX] RAW,2026-03-18 00:19:46,T14,1,V14.06.111,,77,13.31
```

Observe:

```text
V14.06.111,,77
           ↑
       serial vazio
```

Também aparece:

```text
...,T2,1,V14.06.111,,77,13.31,852,-3.827969,-38.533058,...
```

A mensagem possui:

```text
timestamp
tipo T2
versão de protocolo
posição
telemetria
```

mas não possui serial no campo utilizado pela versão atual.

## 8.1 O arquivo de 18/03 como exemplo extremo

Esse arquivo possui:

```text
18.177 linhas
```

E a coluna:

```text
S/N ou IMEI
```

está vazia em todas elas.

Ao mesmo tempo, existem várias mensagens aparentemente válidas:

```text
T14
T3
T27
T28
T17
T21
T24
T1
T47
T2
...
```

Portanto não é coerente interpretar automaticamente todas as linhas como “telemetria corrompida”.

O problema está relacionado ao modo como a versão histórica representa a identidade.

---

# 9. Comparação com `V14.06.117`

Nos registros posteriores aparecem linhas como:

```text
...,T3,1,V14.06.117,202527000021P,7f,13.55,...
```

Agora o serial existe explicitamente:

```text
202527000021P
```

Nas mensagens T1 também aparece:

```text
...,T1,1,V14.06.117,M202527000021P,,89551180357000580854,12345678,724118041016833,354173560222769
```

Isso mostra que a premissa usada pela Silver foi construída corretamente para o formato moderno:

```text
T<n>
+
serial explícito
```

Porém ela não cobre o formato histórico.

---

# 10. O papel especial da mensagem T1

A plataforma já interpreta T1 como evento de identidade.

Nessa mensagem, posições originalmente nomeadas para telemetria são reutilizadas pelo protocolo:

```text
BAT_VOLT → ICCID
LAT      → IMSI
LONT     → IMEI
```

No legado `V14.06.111` foi observado:

```text
T1,1,V14.06.111,,,89551180357000580854,12345678,724118041016833,354173560222769
```

O serial está vazio.

Porém o IMEI permanece disponível:

```text
354173560222769
```

Isso fornece uma identidade técnica persistente capaz de conectar o evento antigo a um evento T1 posterior.

---

# 11. A ponte IMEI → serial

Na Silver moderna foram encontradas identidades como:

```text
202527000021P
IMEI = 354173560222769
```

E:

```text
202527000022
IMEI = 354173560218841
```

Assim existe uma relação observada:

```text
354173560222769
        ↓
202527000021P
```

Essa relação permite recuperar a identidade histórica sem inventar um identificador.

---

# 12. Por que não utilizar ICCID ou IMSI?

Os dois dispositivos conhecidos apresentaram valores compartilhados:

```text
IMSI = 724118041016833
```

E:

```text
ICCID = 89551180357000580854
```

Portanto, nesse conjunto de dados:

```text
IMSI
```

e:

```text
ICCID
```

não são suficientemente discriminantes para resolver o serial.

A resolução deve utilizar apenas uma relação que seja inequívoca.

O IMEI observado atende esse requisito para o caso investigado.

---

# 13. Unicidade por arquivo legado

Foi analisado o conjunto de mensagens:

```text
PRT_VER = V14.06.111
MESS_TYPE = T1
```

A extração considerou somente IMEIs com:

```text
exatamente 15 dígitos
```

Foram encontrados:

```text
23 arquivos
```

com um IMEI válido resolvível.

Todos apontaram para:

```text
354173560222769
```

Alguns arquivos continham também T1 parcial com valor vazio, mas isso deixa de criar falsa ambiguidade quando a regra exige IMEI sintaticamente válido.

Essa verificação é importante porque evita uma inferência perigosa do tipo:

```text
arquivo possui qualquer T1
→ usar esse T1 para tudo
```

A regra correta é:

```text
arquivo legado
+
exatamente um IMEI T1 válido distinto
→ contexto de identidade potencialmente utilizável
```

---

# 14. Cobertura da recuperação

Depois de identificar os arquivos com contexto inequívoco, foi calculado quantos registros atualmente classificados como:

```text
MISSING_DEVICE_SERIAL
```

estão nesses arquivos.

Resultado:

```text
FILES_RESOLVIVEIS             23
REJEICOES_RESOLVIVEIS      55011
TOTAL_MISSING_DEVICE_SERIAL 55217
COBERTURA                  99.63%
```

Portanto:

```text
55.011
```

dos:

```text
55.217
```

registros atualmente rejeitados por serial ausente estão em um contexto onde a identidade histórica pode potencialmente ser reconstruída.

Restam:

```text
206
```

fora dessa cobertura.

---

# 15. Reinterpretação do problema

Antes da análise:

```text
serial ausente
→ dado inválido
```

Depois da análise:

```text
serial ausente
        │
        ├── não existe identidade confiável
        │      ↓
        │   rejeição correta
        │
        └── protocolo legado possui identidade recuperável
               ↓
          resolver antes de rejeitar
```

Essa distinção é central.

A solução não é remover a validação.

A solução é adicionar uma etapa anterior capaz de responder:

```text
é possível determinar o dispositivo de forma inequívoca?
```

---

# 16. Medida escolhida: `identity_resolution`

A Silver deverá receber uma responsabilidade nova e explícita:

```text
identity resolution
```

A implementação planejada deverá ficar isolada, por exemplo em:

```text
src/queo_data_platform/silver/identity_resolution.py
```

O resolver não deve escrever Delta diretamente.

Sua responsabilidade será produzir identidade resolvida ou informar que não existe resolução segura.

---

# 17. Estratégia de resolução

## 17.1 DIRECT

Quando o serial já existe na origem:

```text
device_serial_raw = M202527000021P
```

normalizar:

```text
M202527000021P
→ 202527000021P
```

Resultado conceitual:

```text
device_serial_raw        = M202527000021P
device_serial            = 202527000021P
device_resolution_method = DIRECT
```

## 17.2 LEGACY_IMEI

Para registros legados sem serial:

```text
PRT_VER = V14.06.111
```

seguir:

```text
source_file
    ↓
T1 legado do mesmo arquivo
    ↓
extrair IMEI válido
    ↓
exatamente um IMEI distinto?
    ↓ sim
mapa IMEI → serial conhecido
    ↓
exatamente um serial?
    ↓ sim
resolver dispositivo
```

Resultado conceitual:

```text
device_serial_raw        = NULL
device_serial            = 202527000021P
device_resolution_method = LEGACY_IMEI
```

## 17.3 UNRESOLVED

Se qualquer etapa for ambígua:

```text
nenhum T1 válido
mais de um IMEI válido
IMEI sem serial conhecido
IMEI associado a mais de um serial
```

então:

```text
device_serial = NULL
```

E a classificação permanece:

```text
MISSING_DEVICE_SERIAL
```

---

# 18. A resolução precisa ser conservadora

O resolver deve seguir uma regra fundamental:

```text
não adivinhar
```

Uma associação incorreta é mais grave do que uma rejeição.

Uma rejeição permanece observável em:

```text
rejected_logs
```

Uma associação incorreta contaminaria:

```text
telemetry_events
dim_device
device_last_position
device_route_points
device_daily_summary
```

E poderia fazer um dispositivo receber posições ou métricas pertencentes a outro.

Por isso a resolução só é permitida quando a relação for inequívoca.

---

# 19. O `device_serial_raw` não deve ser alterado

O campo bruto precisa continuar representando exatamente o que veio da origem.

Para um registro legado:

```text
device_serial_raw = NULL
```

mesmo depois da resolução.

O valor resolvido deve existir separadamente.

Isso preserva auditabilidade.

Um consumidor técnico poderá responder:

```text
o serial estava realmente presente no log?
```

E também:

```text
qual identidade a plataforma conseguiu resolver?
```

Sem essa separação, a Silver apagaria a diferença entre dado recebido e dado derivado.

---

# 20. Registrar o método de resolução

É recomendável persistir um campo como:

```text
device_resolution_method
```

com valores controlados:

```text
DIRECT
LEGACY_IMEI
```

E, se fizer sentido no contrato final:

```text
UNRESOLVED
```

para representação intermediária ou rejeições.

Isso permitirá:

```text
métricas de qualidade
investigação operacional
debug de identidade
migrações futuras
```

Exemplo de análise futura:

```text
quantos eventos possuem identidade direta?
quantos foram recuperados do legado?
quantos continuam sem resolução?
```

---

# 21. Evitar associação por arquivo sem validar a mensagem

Um risco importante foi demonstrado pelos arquivos que misturam tracker e tráfego externo.

Não é seguro executar:

```text
arquivo resolvido como device X
→ atribuir device X a todas as linhas do arquivo
```

Antes da resolução contextual, o registro precisa continuar satisfazendo critérios mínimos de mensagem tracker.

No mínimo:

```text
message_type válido ^T[0-9]+$
timestamp válido
versão legada suportada
```

Registros como:

```text
GET / HTTP/1.1
MQTT
OPTIONS / RTSP/1.0
payload binário
```

não podem herdar identidade do arquivo.

Eles continuam rejeitados independentemente de existir T1 válido no mesmo arquivo.

---

# 22. Ordem recomendada dentro da Silver

A arquitetura conceitual deverá evoluir de:

```text
normalization
    ↓
classification
    ↓
transformation
```

para algo próximo de:

```text
normalization
    ↓
identity resolution context
    ↓
classification
    ↓
transformation
```

Outra possibilidade é manter a resolução parcialmente acoplada à preparação da classificação, desde que a responsabilidade permaneça isolada em um módulo próprio.

O ponto essencial é:

```text
MISSING_DEVICE_SERIAL
```

só deve ser definido depois que a plataforma tentar as estratégias de resolução permitidas.

---

# 23. Construção segura do mapa IMEI → serial

O mapa não deve aceitar qualquer relação observada.

A regra deve ser:

```text
T1 com serial direto válido
+
IMEI válido
        ↓
agrupar por IMEI
        ↓
IMEI aponta para exatamente um serial distinto?
        ↓ sim
aceitar associação
```

Exemplo válido:

```text
354173560222769
→ somente 202527000021P
```

Exemplo que deve ser recusado:

```text
IMEI X
→ device A
→ device B
```

Nesse caso o mapa não deve produzir nenhuma resolução para `IMEI X`.

---

# 24. Construção segura do contexto legado por arquivo

Também deve ser conservadora.

Para cada `source_file` legado:

```text
selecionar T1 V14.06.111
extrair LONT
normalizar string
aceitar somente ^\d{15}$
obter valores distintos
```

Somente:

```text
len(imeis_distintos) == 1
```

é resolvível.

Isso evita que um arquivo que realmente contenha dois dispositivos seja incorretamente associado a apenas um.

---

# 25. O que muda na classificação

A regra atual é conceitualmente:

```text
message_type ausente
→ MISSING_MESSAGE_TYPE

message_type inválido
→ INVALID_MESSAGE_TYPE

timestamp inválido
→ MISSING_OR_INVALID_TIMESTAMP

serial raw ausente
→ MISSING_DEVICE_SERIAL
```

Depois da resolução, o último teste deverá considerar a identidade operacional:

```text
serial resolvido ausente
→ MISSING_DEVICE_SERIAL
```

Assim:

```text
device_serial_raw = NULL
```

não implica automaticamente rejeição se:

```text
device_serial
```

foi resolvido de forma segura.

---

# 26. Impacto nos produtos Silver

## telemetry_events

Deverá receber os eventos históricos recuperados.

Eles manterão:

```text
source_file
source_row_number
row_id
batch_id
```

preservando lineage.

## device_identity_events

Os T1 legados também podem passar a representar identidade resolvida.

É importante manter os identificadores extraídos:

```text
imei
imsi
iccid
```

mesmo quando o serial original estava ausente.

## rejected_logs

Deverá perder os registros recuperados de:

```text
MISSING_DEVICE_SERIAL
```

mas continuar contendo os casos realmente irresolvíveis.

---

# 27. Impacto na Gold

A mudança não é apenas uma correção local da Silver.

Ao recuperar dezenas de milhares de eventos, poderão mudar:

```text
dim_device
```

porque `first_seen_at`, `last_seen_at` e contagens podem mudar.

Também:

```text
device_last_position
```

pode mudar caso exista posição histórica/reprocessada relevante.

E:

```text
device_route_points
```

receberá novos pontos históricos.

```text
device_daily_summary
```

terá novos volumes, posições, velocidades, odômetro e métricas diárias.

```text
data_quality_summary
```

mudará de forma significativa porque registros deixarão de ser rejeitados e passarão a ser aceitos.

---

# 28. Estratégia de migração após a implementação

A alteração modifica uma regra histórica de classificação.

Portanto, executar apenas:

```text
pipeline incremental sem novos arquivos
```

não é suficiente.

Não existe um batch novo que faça as datas antigas serem automaticamente reprocessadas.

A migração deverá solicitar explicitamente um rebuild.

A opção mais segura para esta primeira mudança é:

```text
Bronze existente permanece
        ↓
Silver FULL rebuild
        ↓
Gold FULL rebuild
```

A Bronze não precisa ser recriada porque:

```text
dado bruto
lineage
batch_id
row_id
```

já estão preservados.

A mudança é de interpretação Silver.

Depois de validada, a execução operacional volta ao modo incremental normal.

---

# 29. Testes obrigatórios do resolver

Antes de conectar o resolver ao service Silver, ele deve ser testado isoladamente.

## Caso 1 — relação direta inequívoca

```text
IMEI A → serial X
```

Resultado:

```text
resolve X
```

## Caso 2 — IMEI ligado a dois seriais

```text
IMEI A → serial X
IMEI A → serial Y
```

Resultado:

```text
não resolver
```

## Caso 3 — arquivo legado com exatamente um IMEI válido

```text
source_file A
T1 → IMEI X
```

Resultado:

```text
contexto X
```

## Caso 4 — arquivo com dois IMEIs válidos

```text
source_file A
T1 → IMEI X
T1 → IMEI Y
```

Resultado:

```text
não resolver contexto
```

## Caso 5 — T1 parcial com vazio

```text
T1 → ""
T1 → IMEI X
```

Resultado:

```text
considerar apenas X
```

## Caso 6 — payload HTTP no mesmo arquivo

Mesmo que o arquivo tenha um IMEI válido:

```text
GET / HTTP/1.1
```

não pode virar telemetria.

## Caso 7 — versão moderna sem serial

Um registro `V14.06.117` sem serial não deve automaticamente herdar a regra legado se ela foi definida exclusivamente para:

```text
V14.06.111
```

Isso evita ampliar a inferência além da evidência observada.

---

# 30. Critérios de aceitação da mudança

A implementação só deve ser considerada concluída se:

```text
ruff passa
pyright passa
pytest passa
```

E, em dados reais, for demonstrado que:

```text
MISSING_DEVICE_SERIAL cai drasticamente
```

sem reduzir artificialmente:

```text
MISSING_MESSAGE_TYPE
INVALID_MESSAGE_TYPE
```

nem converter tráfego externo em telemetry.

Também deve ser confirmado que:

```text
354173560222769
→ 202527000021P
```

é aplicado apenas onde o contexto legado é inequívoco.

---

# 31. Resultado esperado após o rebuild

A medição atual é:

```text
MISSING_DEVICE_SERIAL = 55.217
```

A análise mostrou:

```text
55.011
```

potencialmente recuperáveis.

Portanto é razoável esperar uma redução próxima de:

```text
99,63%
```

desse motivo de rejeição específico.

Isso **não deve ser tratado como número garantido antes da implementação**.

Alguns registros podem falhar em critérios adicionais necessários para a segurança da resolução.

O objetivo correto é:

```text
recuperar somente o subconjunto comprovadamente resolvível
```

não maximizar artificialmente a taxa de aceitação.

---

# 32. Decisão final

A investigação demonstrou três classes distintas de dados:

```text
1. formato raw legado sem contrato tabular
   → quarantine
   → futuro adapter/parser

2. tráfego não tracker dentro dos logs
   → rejected_logs
   → não tentar resolver identidade

3. mensagens tracker V14.06.111 sem serial explícito
   + T1 com IMEI válido
   + associação moderna IMEI → serial
   → candidatas à resolução histórica
```

A medida técnica escolhida é:

```text
adicionar identity_resolution na Silver
```

antes da rejeição definitiva por ausência de dispositivo.

Essa solução foi escolhida porque preserva:

```text
raw imutável
lineage
regras de qualidade
segurança de identidade
compatibilidade histórica
```

sem transformar a plataforma em um sistema de inferência permissivo.

A implementação deverá ser iniciada pelo componente isolado e seus testes.

Somente depois o resolver será conectado à classificação e será executado um rebuild controlado da Silver e da Gold.
