# Resumo do split temporal

Dados: 51324 linhas (bairro x semana) de 2015-03-01 a 2025-08-10, 94 bairros, 21 features. As 8 primeiras semanas do painel foram descartadas (histórico incompleto) e a última semana não tem alvo.

## Conjuntos

Cada linha t tem features até a semana t e alvo na semana t+1. Entre os conjuntos há 1 semana(s) de linhas excluídas, de modo que o alvo da última linha de um conjunto cai antes da primeira linha do seguinte.

| conjunto | t inicial | t final | alvo inicial (t+1) | alvo final (t+1) | semanas | linhas |
|---|---|---|---|---|---|---|
| treino | 2015-03-01 | 2024-07-28 | 2015-03-08 | 2024-08-04 | 492 | 46248 |
| validação | 2024-08-11 | 2025-02-02 | 2024-08-18 | 2025-02-09 | 26 | 2444 |
| teste | 2025-02-16 | 2025-08-10 | 2025-02-23 | 2025-08-17 | 26 | 2444 |

## Limiares de risco (ajustados só nos alvos do treino)

- Quantil 0.6: **0** casos/semana/bairro
- Quantil 0.85: **1** casos/semana/bairro
- Regra: baixo = casos <= q_mid; médio = casos <= q_high; alto = acima.

> O limiar de baixo risco é 0: a classe 'baixo' significa nenhum caso.

## Distribuição de classes (alvo t+1, com os limiares do treino)

| conjunto | baixo | medio | alto |
|---|---|---|---|
| treino | 33765 (73.0%) | 5774 (12.5%) | 6709 (14.5%) |
| validação | 2005 (82.0%) | 255 (10.4%) | 184 (7.5%) |
| teste | 1510 (61.8%) | 374 (15.3%) | 560 (22.9%) |

> **Atenção:** a distribuição muda bastante entre conjuntos. A maior diferença para o treino é 11.2 pontos percentuais (classe 'baixo' no conjunto 'teste'). Métricas de validação e de teste não são comparáveis entre si sem levar isso em conta.

## Baseline de persistência (classe de casos(t) repetida em t+1, mesmos limiares)

| conjunto | F1-macro | balanced accuracy | recall baixo | recall médio | recall alto |
|---|---|---|---|---|---|
| validação | 0.558 | 0.555 | 0.906 | 0.227 | 0.533 |
| teste | 0.570 | 0.568 | 0.835 | 0.217 | 0.652 |

Matriz de confusão, validação (linhas = real, colunas = previsto; baixo, médio, alto):

```
[1817, 152, 36]
[154, 58, 43]
[40, 46, 98]
```

Matriz de confusão, teste (linhas = real, colunas = previsto; baixo, médio, alto):

```
[1261, 176, 73]
[195, 81, 98]
[86, 109, 365]
```

## CV de janela expansiva (5 splits, só dentro do treino)

Os limiares de cada fold usam só os alvos do treino daquele fold.

| fold | treino (t) | linhas treino | validação (t) | linhas validação | limiares do fold | % baixo/médio/alto na validação |
|---|---|---|---|---|---|---|
| 1 | 2015-03-01 a 2016-09-11 | 7614 | 2016-09-25 a 2018-04-15 | 7708 | (1, 7) | 96/4/0 |
| 2 | 2015-03-01 a 2018-04-08 | 15322 | 2018-04-22 a 2019-11-10 | 7708 | (0, 3) | 74/21/5 |
| 3 | 2015-03-01 a 2019-11-03 | 23030 | 2019-11-17 a 2021-06-06 | 7708 | (0, 2) | 78/15/8 |
| 4 | 2015-03-01 a 2021-05-30 | 30738 | 2021-06-13 a 2023-01-01 | 7708 | (0, 2) | 77/17/6 |
| 5 | 2015-03-01 a 2022-12-25 | 38446 | 2023-01-08 a 2024-07-28 | 7708 | (0, 2) | 81/14/5 |

> **Atenção:** no fold 1 a classe 'alto' tem menos de 1% da validação. O fold 1 treina só na epidemia de 2015-2016, então seus limiares (altos) deixam quase nada como 'alto' depois; a F1-macro desse fold é pouco informativa.
