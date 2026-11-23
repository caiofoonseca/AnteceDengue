# Qualidade do painel bairro x semana

Painel: **94 bairros** x **555 semanas** (2015-01-04 a 2025-08-17, semanas começando no domingo) = 52170 linhas. Soma de casos do painel: **59085** (último passo do funil: 59085; confere).

## Funil de registros

| etapa | registros | variação |
|---|---|---|
| Registros lidos (2013–2025) | 110640 |  |
| Após período 2015–2025 | 106219 | -4421 |
| Após caso confirmado | 61284 | -44935 |
| Após data válida | 61284 | 0 |
| Após bairro válido | 60924 | -360 |
| Após duplicatas | 60924 | 0 |
| Após janela do painel (casos no painel) | 59085 | -1839 |

## Detalhes do funil

**Data de referência** — casos que usaram a data de notificação no lugar da de sintomas:

- sintomas absurdos (anteriores ao ano do arquivo - 1): 24

- Descartados sem nenhuma data válida: **0**

**Bairros** — registros por método de resolução (antes de descartar):

- exato: 60915
- nulo: 339
- não encontrado na tabela: 19
- apelido: 9
- não é bairro: 2

Registros descartados por motivo:

- nulo: 339
- não encontrado na tabela: 19
- não é bairro: 2

Valores descartados (todos):

| motivo | valor no arquivo | registros |
|---|---|---|
| nulo | <nulo> | 339 |
| não encontrado na tabela |  JARDIM ATLANTICO | 1 |
| não encontrado na tabela | ALTO DA BONDADE | 1 |
| não encontrado na tabela | ALTO SANTA ISABEL | 1 |
| não encontrado na tabela | ALUIZIO PINTO | 1 |
| não encontrado na tabela | BOLA NA REDE | 1 |
| não encontrado na tabela | CAMPO | 1 |
| não encontrado na tabela | COQUEIRO | 1 |
| não encontrado na tabela | EST | 1 |
| não encontrado na tabela | GUAB | 1 |
| não encontrado na tabela | GUARARAPES | 1 |
| não encontrado na tabela | IMB | 1 |
| não encontrado na tabela | JAGUARANA | 1 |
| não encontrado na tabela | MANGUE | 1 |
| não encontrado na tabela | P | 1 |
| não encontrado na tabela | PACHECO | 1 |
| não encontrado na tabela | RESIDENCIAL | 1 |
| não encontrado na tabela | SITIO NOVO | 1 |
| não encontrado na tabela | TA | 1 |
| não encontrado na tabela | TEJUCOPAPO | 1 |
| não é bairro | CENTRO | 1 |
| não é bairro | ZONA RURAL | 1 |

Valores corrigidos por apelido ou correspondência aproximada:

| método | valor no arquivo | bairro oficial | registros |
|---|---|---|---|
| apelido | GRAAS | GRACAS | 2 |
| apelido | AREAIS | AREIAS | 1 |
| apelido | BREJO DE GUABIRABA | BREJO DA GUABIRABA | 1 |
| apelido | JIQU] | JIQUIA | 1 |
| apelido | PONRO DE PARADA | PONTO DE PARADA | 1 |
| apelido | TAMA | TAMARINEIRA | 1 |
| apelido | TEJIPI | TEJIPIO | 1 |
| apelido | VASCO | VASCO DA GAMA | 1 |

**Duplicatas**

- Linhas 100% idênticas removidas: 0
- `nu_notificacao` repetido com bairro, datas e classificação iguais (removidos): 0
- Linhas com `nu_notificacao` repetido mas dados diferentes (mantidas): 1647
- Casos fora da janela do painel (antes de 2015-01-04 ou após 2025-08-17): 1839

## Casos totais por ano

| ano (início da semana) | casos |
|---|---|
| 2015 | 23370 |
| 2016 | 11964 |
| 2017 | 971 |
| 2018 | 1202 |
| 2019 | 4061 |
| 2020 | 1517 |
| 2021 | 7438 |
| 2022 | 1290 |
| 2023 | 1417 |
| 2024 | 2658 |
| 2025 | 3197 |

## Bairros com menos de 50 casos no período (8; só listados, não removidos)

| bairro | casos |
|---|---|
| HIPODROMO | 48 |
| SOLEDADE | 38 |
| SANTO ANTONIO | 33 |
| JAQUEIRA | 33 |
| TORREAO | 29 |
| PAISSANDU | 29 |
| ILHA DO LEITE | 25 |
| PAU FERRO | 1 |

## 10 bairros com mais casos

| bairro | casos |
|---|---|
| COHAB | 3975 |
| IBURA | 3113 |
| VARZEA | 2527 |
| BOA VIAGEM | 2340 |
| IMBIRIBEIRA | 2214 |
| IPUTINGA | 2197 |
| AGUA FRIA | 2098 |
| AFOGADOS | 2056 |
| AREIAS | 1674 |
| CASA AMARELA | 1457 |

## 10 semanas com mais casos (soma da cidade)

| week_start | casos |
|---|---|
| 2015-03-29 | 1530 |
| 2015-04-05 | 1334 |
| 2015-04-12 | 1285 |
| 2015-03-22 | 1258 |
| 2015-03-15 | 1150 |
| 2015-04-19 | 1145 |
| 2016-02-14 | 1129 |
| 2016-02-07 | 1041 |
| 2015-03-08 | 999 |
| 2016-01-31 | 947 |

## Limiares de risco se calculados em todo o painel (informativo)

- Quantil 0.6: **0** casos/semana/bairro
- Quantil 0.85: **2** casos/semana/bairro
- Regra usada aqui: baixo = casos <= q_mid; médio = q_mid < casos <= q_high; alto = casos > q_high.

> **AVISO:** o limiar de baixo risco é 0: 'baixo' significa exatamente zero casos (72.2% das células do painel são zero).

| classe | células | % |
|---|---|---|
| baixo | 37674 | 72.2 |
| medio | 9144 | 17.5 |
| alto | 5352 | 10.3 |

## Bairros da tabela oficial sem nenhum caso no painel (0)

Nenhum.
