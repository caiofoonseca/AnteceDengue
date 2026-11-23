# Registro de uso de IA

Projeto AnteceDengue (G15), CESAR School. Ferramenta: Claude Code (modelo Claude Sonnet 5.5), usado como assistente de programação no repositório. Uma entrada por passo. O grupo usa este registro para a declaração semanal de uso de IA aos orientadores.

> Os campos "Verificação humana" abaixo registram o que consta na conversa de trabalho (decisões, comandos e resultados que o Caio recebeu e aprovou). O Caio deve ajustá-los ao que realmente conferiu antes de entregar a declaração.

## Passo 0 — CLAUDE.md (23/11/2026)
- **O que o Claude Code fez:** criou o CLAUDE.md na raiz com o texto fornecido pelo Caio, sem alterá-lo e sem criar outros arquivos.
- **Verificação humana:** o Caio escreveu o conteúdo (decisões de ML, dados, stack e convenções) e fez o commit.

## Passo 1 — Estrutura, config e ambiente (23/11/2026)
- **O que o Claude Code fez:** avisou que o Python instalado era 3.14 (o projeto pede 3.11); instalou o Python 3.11 via winget a pedido do Caio; criou as pastas, `src/config.py`, `requirements.txt`, `.env.example`, `.gitignore`, `pytest.ini`, testes de configuração, o `.venv` e a seção "Como rodar localmente" no README.
- **Verificação humana:** o Caio decidiu instalar o 3.11 e definiu os critérios de pronto; foram mostrados `python --version`, 4 testes verdes e `git status` limpo.

## Passo 2 — Download e inspeção dos dados (23/11/2026)
- **O que o Claude Code fez:** achou o conjunto no Portal de Dados Abertos do Recife pela API CKAN, baixou os 13 CSVs (2013 a 2025), criou o leitor tolerante `src/data_recife.py`, `scripts/inspect_raw.py`, `scripts/download_raw.py`, `docs/DADOS.md` e o relatório `reports/dados_inspecao.md`. Listou os problemas de qualidade (colunas que mudam entre anos, separadores, datas mistas, 2014 incompleto).
- **Verificação humana:** o Caio recebeu a lista de problemas e tomou as decisões de dados (definição de caso, período, data de referência).

## Passo 3 — Painel bairro x semana (23/11/2026)
- **O que o Claude Code fez:** padronizou colunas por ano, normalizou nomes de bairro (exato, apelidos manuais em `src/bairro_aliases.py`, correspondência aproximada), tratou duplicatas, montou o painel completo em `data/processed/panel.csv` e o relatório `reports/painel_qualidade.md`, com testes.
- **Verificação humana:** o Caio definiu as regras (CASE_CODES, 2015–2025, data de sintomas) e recebeu o funil de registros, a lista de bairros descartados e as anomalias (cauda truncada, picos de 2015–2016).

## Passo 4 — Cauda de 2025 e clima semanal (23/11/2026)
- **O que o Claude Code fez:** analisou a fração de registros ainda sem classificação e propôs PANEL_END = 2025-08-17 (critério numérico em `reports/cauda_2025.md`); calculou os limiares de quantil do painel; pesquisou as fontes de clima (InfoDengue sem chuva; INMET A301 sem dados utilizáveis de 2022 em diante); montou o clima semanal com chuva do Open-Meteo (ERA5) e comparou com o INMET em 2015–2021 (Pearson 0,66; Spearman 0,80).
- **Também neste passo:** a pedido do Caio, removeu o trailer Co-Authored-By dos commits (reescrita de histórico e push forçado, com confirmação prévia) e configurou `.claude/settings.json`.
- **Verificação humana:** o Caio escolheu usar uma única fonte de chuva para todo o período e confirmou a reescrita do histórico. A licença do Open-Meteo citada em `docs/DADOS.md` veio de memória do assistente e precisa ser conferida pelo grupo.

## Passo 5 — Features, rótulos e validação (23/11/2026)
- **O que o Claude Code fez:** criou `src/features.py`, `src/labels.py`, `src/validation.py` e `src/evaluate.py`, o script `scripts/make_split_summary.py` e o relatório `reports/split_resumo.md`, mais testes (incluindo teste de vazamento do futuro, conferido ao quebrar de propósito uma feature). Removeu os comentários `#` do código existente, a pedido do Caio.
- **Verificação humana:** o Caio definiu as decisões do passo (sensor fora do treino, ffill causal de 2 semanas, class_weight balanced, F1-macro) e recebeu os tamanhos dos conjuntos, os limiares e as métricas do baseline.
