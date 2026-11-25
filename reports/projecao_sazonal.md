# Projeção sazonal mensal de risco de dengue para 2026

> Projeção sazonal baseada no histórico até 17/08/2025; não há dados reais de 2026 para verificação. É projeção do padrão sazonal, não previsão verificada nem número exato de casos.

- Método escolhido: **recencia_h1** (Backtest A (F1-macro mensal); o Backtest B não participou da escolha).
- Último mês completo usado: 2025-07; painel até 2025-08-17.
- Limiares de classe (casos/mês, q0.60 e q0.85 só no histórico real): 1.08 e 6.50.

O baseline é o "mesmo mês do último ano". F1-macro e recall da classe alta são sobre as classes mensais (bairro x mês); Spearman é a média, por mês, da correlação entre o ranking real e o projetado dos bairros; MAE em casos/mês padronizados por bairro; pico = acerto do mês de maior total da cidade.

### Backtest A (até 2023 -> 2024)

| método | f1_macro | recall_alto | spearman_bairros | mae_casos_mes | pico_acerto |
|---|---|---|---|---|---|
| climatologia | 0.422 | 0.805 | 0.387 | 4.198 | 1.000 |
| ultimo_ano (baseline) | 0.486 | 0.257 | 0.393 | 2.264 | 1.000 |
| recencia_h1 | 0.518 | 0.407 | 0.429 | 2.406 | 0.000 |
| recencia_h2 | 0.495 | 0.531 | 0.421 | 2.743 | 0.000 |
| recencia_h3 | 0.466 | 0.611 | 0.412 | 3.011 | 0.000 |
| random_forest | 0.361 | 0.000 | 0.411 | 2.298 | 0.000 |

### Backtest B (até 2024 -> 2025)

| método | f1_macro | recall_alto | spearman_bairros | mae_casos_mes | pico_acerto |
|---|---|---|---|---|---|
| climatologia | 0.451 | 0.750 | 0.601 | 4.649 | 0.000 |
| ultimo_ano (baseline) | 0.518 | 0.431 | 0.418 | 3.912 | 0.000 |
| recencia_h1 | 0.595 | 0.500 | 0.586 | 3.080 | 0.000 |
| recencia_h2 | 0.578 | 0.552 | 0.618 | 2.953 | 0.000 |
| recencia_h3 | 0.560 | 0.664 | 0.616 | 3.041 | 0.000 |
| random_forest | 0.363 | 0.060 | 0.548 | 3.502 | 0.000 |

## Dados (verificado em 25/11/2026)

- O portal de dados abertos do Recife não tem recurso de 2026 e os arquivos de 2013, 2014 e 2025 têm o mesmo tamanho dos já baixados: não há dados novos. Painel antes e depois: 2015-01-04 a 2025-08-17 (inalterado).
- 2013 e 2014 não foram incorporados: 1.293 e 374 casos confirmados (2014 termina em julho e 2013 está em outra escala), o que quebraria a série mensal; a decisão de período 2015 a 2025 continua.
- Os registros brutos de 2025 vão até dezembro, mas a cauda tem classificação atrasada; o painel segue cortado em PANEL_END.

## Limitações

- Anos epidêmicos (2015-16, 2024) mudam muito a magnitude; o método captura sazonalidade, não surtos.
- Sem dados climáticos futuros e sem casos recentes de 2026.
- Agosto a dezembro de 2025 não entram (cauda com classificação atrasada, ver reports/cauda_2025.md); esses meses de 2026 se apoiam em anos anteriores a 2025 e a curva tem um degrau entre julho e agosto.
- O Backtest B tem só 7 meses (jan a jul/2025). Ele foi calculado uma vez e não participou da escolha do método.
- Nenhum resultado do modelo semanal nem o teste final foram alterados.
