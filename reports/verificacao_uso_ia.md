# Verificação das afirmações do USO_DE_IA.md e do diário do projeto

Gerado em 24/11/2026. Nada de código nem o `docs/USO_DE_IA.md` foi alterado. Os números foram recalculados a partir de `data/processed/panel.csv`, `data/processed/clima_semanal.csv`, `models/` e do `mlflow.db`, sem usar os relatórios como fonte.

**Teste final não reavaliado.** Para o item 6 só li datas e tamanhos do conjunto de teste (nenhum alvo, nenhuma previsão). As métricas de teste do item 1 foram apenas comparadas entre os dois arquivos já gravados.

Resumo: itens 1, 2, 3, 4, 5, 6 e 10 OK; item 7 tem uma DIVERGÊNCIA (`secrets.h`) e valores padrão inseguros; item 8 NÃO DÁ PARA VERIFICAR (depende das páginas oficiais); item 9 tem resíduos de teste no banco.

---

## 1. Teste final (`reports/teste_final.json/.md` x `models/model_meta.json`) — OK

Comando: Python lendo os dois JSON e comparando campo a campo (tolerância 1e-9).

| métrica | esperado | teste_final.json | model_meta.json | resultado |
|---|---|---|---|---|
| F1-macro RF | 0,611 | 0,610620 | 0,610620 | OK |
| F1-macro persistência | 0,570 | 0,570440 | 0,570440 | OK |
| recall alto RF | 0,702 | 0,701786 | 0,701786 | OK |
| recall alto persistência | 0,652 | 0,651786 | 0,651786 | OK |
| AUC macro | 0,817 | 0,816959 | 0,816959 | OK |
| delta F1 | +0,040 | +0,040180 | +0,040180 | OK |
| IC95% do delta F1 | [+0,021, +0,054] | bloco 4 sem.: [0,0207, 0,0539] | [0,0207, 0,0539] | OK (ver nota) |
| recall médio RF x persistência | 0,40 x 0,22 | 0,4011 x 0,2166 | (não consta no meta) | OK |
| recall alto da matriz de confusão | 0,702 | 393/560 = 0,7018 | — | OK |

Nota: o IC [+0,021, +0,054] é o do bootstrap com blocos de 4 semanas (o definido em `BOOTSTRAP_BLOCK_WEEKS`). Os outros blocos dão IC diferentes: 1 semana [+0,017, +0,061]; 2 semanas [+0,020, +0,057]. O relatório usa corretamente o de 4 semanas; vale citar qual bloco foi usado.

## 2. MLflow local (`mlflow.db`) — OK

Comando: `MlflowClient("sqlite:///mlflow.db")` com `search_experiments`, `search_runs`, `search_registered_models`, `get_model_version_by_alias`.

| experimento | runs (todas FINISHED) |
|---|---|
| 01-baseline | 2 |
| 02-comparacao-modelos | 7 |
| 03-otimizacao-hiperparametros | 65 |
| Default | 0 |

- Modelo `antecedengue-risk-classifier`: 1 versão (v1), alias `champion` → v1, run `b7e7159fdc45435ca12ec8671cf9ee1d` (nome `modelo-final`, experimento 03). É o mesmo `mlflow_run_id` de `model_meta.json`.
- Hiperparâmetros (esperado x encontrado), conferidos em três lugares (parâmetros do run, `models/best_model.joblib` e o modelo carregado de `models:/antecedengue-risk-classifier@champion`):

| parâmetro | esperado | run | joblib | Registry |
|---|---|---|---|---|
| tipo | RandomForest | RandomForest | RandomForestClassifier | RandomForestClassifier |
| n_estimators | 351 | 351 | 351 | 351 |
| max_depth | 20 | 20 | 20 | 20 |
| min_samples_leaf | 26 | 26 | 26 | 26 |
| min_samples_split | 26 | 26 | 26 | 26 |
| max_features | sqrt | sqrt | sqrt | sqrt |
| max_samples | 0,9 | 0,9 | 0,9 | 0,9 |
| class_weight | balanced_subsample | balanced_subsample | balanced_subsample | balanced_subsample |

- Observação: o experimento `04-monitoramento-semanal` não existe neste `mlflow.db` (ele vive no MLflow/Airflow do compose, em volume próprio). Não é divergência, só não pôde ser conferido aqui.
- Observação: o run registra `mlflow.source.git.commit = 000cdfe` (commit da época do treino), não o HEAD atual.

## 3. Números da EDA (recalculados de `panel.csv`, só treino + validação) — OK

Comando: `scripts` ad hoc (`verif_dados.py` no scratchpad da sessão): recorte até a semana 2025-02-09 (528 semanas), sem nenhuma semana do teste. Os limiares de classe foram recalculados dos alvos do treino: quantis 0,60 e 0,85 = (0, 1).

| afirmação | esperado | encontrado | resultado |
|---|---|---|---|
| 3 episódios acima do p90 (limite 310,6 casos/sem.) | 61,4% dos casos | 3 episódios; 34.499 de 56.174 casos = 61,41% (53 semanas, 10% de 528) | OK |
| células bairro-semana com zero | 72,7% | 72,72% | OK |
| classe se repete t → t+1 | 76,2% | 76,20% (48.692 linhas) | OK |
| baixo → baixo | 87,0% | 87,0% | OK |
| alto → alto | 66,4% | 66,4% | OK |
| médio → médio | 23,6% | 23,6% (58,0% caem para baixo, 18,4% sobem para alto) | OK |
| maior \|rho\| Spearman clima x casos (cidade) | 0,217 (chuva, k=8) | chuva k=8 = +0,2174; temperatura k=0 = −0,2059; umidade k=3 = +0,1593 | OK |

Extras que também batem com o notebook: persistência F1-macro 0,5912 no treino e 0,5583 na validação; classes do treino 73,0/12,5/14,5% e da validação 82,0/10,4/7,5%; desde 2017 o maior \|rho\| é 0,420 (temperatura, k=0) e a chuva fica em 0,309 (k=8).

Sensibilidade a registrar: esses números só reproduzem se as 8 primeiras semanas do painel (antes de 2015-03-01) ficarem fora do cálculo de limiares e de persistência. Na minha primeira tentativa, que as incluiu, os limiares saíram (0, 2) em vez de (0, 1) e a repetição de classe saiu 76,1%, com médio→médio 35,8%. A proporção de zeros (72,7%) e os episódios usam o painel todo até 2025-02-09, como no notebook.

## 4. Importância por permutação na validação — OK

Comando: RandomForest com os hiperparâmetros finais ajustado só no treino (`build_model("rf", best_params)`), `permutation_importance` na validação, scorer F1-macro, 10 repetições, `random_state=42`.

| feature | esperado | encontrado | diferença | resultado |
|---|---|---|---|---|
| casos_mm4 | 0,046 | 0,0458 | 0,0002 | OK |
| casos_mm8 | 0,034 | 0,0335 | 0,0005 | OK |
| casos_media_hist | 0,019 | 0,0190 | 0,0000 | OK |
| casos_t | 0,013 | 0,0128 | 0,0002 | OK |

O quinto colocado é cidade_lag2 (0,0003); clima, cidade e sazonalidade ficam em torno de zero, como o notebook afirma.

## 5. Previsão em lote (`data/processed/predictions_latest.csv`) — OK

| verificação | esperado | encontrado | resultado |
|---|---|---|---|
| bairros | 94 | 94 (94 distintos) | OK |
| soma das probabilidades | 1 | de 0,9999999999999993 a 1,0000000000000009 | OK |
| semana base / alvo | 2025-08-17 / 2025-08-24 | 2025-08-17 / 2025-08-24 (único valor) | OK |
| classes | 37 alto, 32 baixo, 25 médio | 37, 32, 25 | OK |
| 10 primeiros | COHAB, AGUA FRIA, CAMPO GRANDE, BOA VIAGEM, IBURA, SANTO AMARO, NOVA DESCOBERTA, IMBIRIBEIRA, CAMPINA DO BARRETO, PINA | idêntico, na mesma ordem | OK |

Extras: o rank vai de 1 a 94 sem repetição, está em ordem decrescente de `risk_score` e `risk_score = 50*prob_medio + 100*prob_alto` com erro máximo de 3e-14.

## 6. Divisão e vazamento — OK

Comando: `temporal_split(build_features(...))` (apenas datas e contagens) e pytest.

| conjunto | t inicial | t final | alvo final (t+1) | semanas | linhas |
|---|---|---|---|---|---|
| treino | 2015-03-01 | 2024-07-28 | 2024-08-04 | 492 | 46.248 |
| validação | 2024-08-11 | 2025-02-02 | 2025-02-09 | 26 | 2.444 |
| teste | 2025-02-16 | 2025-08-10 | 2025-08-17 | 26 | 2.444 |

- Gap: a semana 2024-08-04 (treino→validação) e a semana 2025-02-09 (validação→teste) ficam excluídas, 1 semana em cada transição, e o alvo da última linha de cada conjunto cai antes do início do seguinte (verificado por cálculo).
- Contas fecham: 46.248 + 2.444 + 2.444 + 2×94 (linhas do gap) = 51.324 linhas do `build_features`; treino + validação = 48.692, igual a `train_period.linhas` do `model_meta.json`.
- Testes (`pytest tests/test_validation.py tests/test_features.py tests/test_labels.py tests/test_train.py -v`): **31 passed**. Os mais relevantes: `test_gap_exclui_semanas_entre_conjuntos`, `test_alvo_da_ultima_linha_do_treino_nao_cai_na_validacao`, `test_conjuntos_sem_sobreposicao_de_linhas`, `test_limiares_do_split_vem_so_do_treino`, `test_splits_expansivos_nunca_usam_dado_futuro`, `test_limiares_de_cada_fold_usam_so_o_treino_do_fold`, `test_vazamento_casos_futuros_nao_mudam_features_anteriores`, `test_vazamento_clima_futuro_nao_muda_features_anteriores`, `test_ffill_causal_limite_de_duas_semanas`, `test_guarda_bloqueia_o_teste`, `test_treino_falha_se_pedir_o_teste`.
- Esses testes mostram ausência de vazamento nos casos cobertos; não provam por si sós que não existe nenhum outro caminho de vazamento.

## 7. Segurança — DIVERGE (parcial)

| verificação | esperado | encontrado | resultado |
|---|---|---|---|
| `.env` no `.gitignore` | sim | linha 228 (`git check-ignore -v .env`) | OK |
| `secrets.h` no `.gitignore` | sim | **não está**; não existe `secrets.h` no repositório (a pasta `embedded/` está vazia); só há `.streamlit/secrets.toml` (linha 223) | **DIVERGE** |
| `.claude/` não versionada | sim | `git ls-files` sem nada de `.claude`; ignorada na linha 239; `git log origin/main -- .claude` vazio (23 commits) | OK |
| `.env` versionado alguma vez | não | `git ls-files` e `git log --all -- .env` sem resultado | OK |
| senha real em arquivo versionado | nenhuma | `git grep -niE "password\|senha\|token\|secret\|api[_-]?key"` só acha placeholders, nomes de variáveis e texto de documentação | OK |

Detalhes:
- `.claude/` aparece em duas branches locais, `backup-antes-reescrita` e `backup-antes-reescrita-2`, que nunca foram enviadas (`git branch -r` só mostra `origin/main`). Apague-as localmente quando não precisar mais delas.
- O `.env` real (valores não exibidos aqui) tem POSTGRES_PASSWORD (14 caracteres), AIRFLOW_ADMIN_PASSWORD (14), AIRFLOW_FERNET_KEY (44) e AIRFLOW_SECRET_KEY (32), todos diferentes dos placeholders do `.env.example`.

Valores padrão inseguros encontrados:
1. `.env.example`: `DATABASE_URL=postgresql://antecedengue:antecedengue@localhost:5432/antecedengue` (usuário e senha iguais ao nome do sistema). O mesmo padrão está em `src/config.py:62` (valor padrão de `DATABASE_URL`) e no `.env` real.
2. `.env.example`: placeholders `troque-esta-senha`, `troque-a-senha-do-airflow`, `gere-uma-chave`, `gere-um-segredo` e `AIRFLOW_ADMIN_USER=admin`. O compose exige POSTGRES_PASSWORD (`:?`) e o `airflow-init` aborta sem senha, mas nada impede alguém de deixar o placeholder.
3. `docker-compose.yml`: `POSTGRES_USER` e `POSTGRES_DB` com padrão `antecedengue`; `AIRFLOW_FERNET_KEY`, `AIRFLOW_SECRET_KEY` e `AIRFLOW_ADMIN_PASSWORD` com padrão vazio (`:-`).
4. `docker/mosquitto.conf`: `allow_anonymous true`, e a porta 1883 é publicada em `0.0.0.0` (qualquer máquina da rede publica leituras).
5. API (8000) e dashboard (8501) publicados em `0.0.0.0` sem autenticação; Postgres, MLflow e Airflow ficam só em 127.0.0.1.
6. Um commit antigo (`6a4936c`) contém só o placeholder `POSTGRES_PASSWORD=troque-esta-senha`, não uma senha real.

## 8. Licenças em `docs/DADOS.md` — NÃO DÁ PARA VERIFICAR

Não consultei as páginas oficiais. Texto atual para você comparar:

- Casos (linha 7): "Licença: Open Data Commons Open Database License (ODbL) — http://www.opendefinition.org/licenses/odc-odbl". Também: "Frequência de atualização informada pelo portal: trimestral."
- GeoJSON de bairros (linhas 50-51): "Fonte: Portal de Dados Abertos do Recife ..., conjunto 'Área urbana', recurso 'Bairros do Recife' (GeoJSON), obtido via API CKAN em 24/11/2026. Licença: ODbL (Open Database License), a mesma dos demais dados do portal."
- InfoDengue (linha 36): "Dados do projeto InfoDengue (Fiocruz/FGV); citar a fonte. A resposta real da API não traz precipitação." Não há nome de licença para o InfoDengue; só a recomendação de citar.
- Open-Meteo (linha 37): "Open-Meteo oferece dados abertos sob CC BY 4.0 (uso não comercial gratuito); citar Open-Meteo e o ERA5/Copernicus. É reanálise em grade (~25 km), não observação de estação."

Pontos para checar nas páginas oficiais: (a) se a licença do conjunto de GeoJSON no portal é mesmo a ODbL e não outra; (b) se a API gratuita do Open-Meteo continua restrita a uso não comercial e como pedem a atribuição; (c) se o InfoDengue indica uma licença específica (o texto atual não nomeia nenhuma). A ODbL também tem cláusula de compartilhamento pela mesma licença para bases derivadas, que o texto não menciona.

## 9. Banco do sensor (Postgres do compose, tabela `sensor_readings`) — DIVERGE (resíduos)

Comando: `docker compose exec -T postgres psql ... group by station_id`.

| station_id | válidas | inválidas | total | primeira leitura | última leitura | em `stations_bairros.json` |
|---|---|---|---|---|---|---|
| recife-001 | 549 | 39 | 588 | 2026-11-03 16:54 | 2026-11-24 18:04 | sim (BOA VIAGEM) |
| recife-002 | 549 | 39 | 588 | 2026-11-03 16:54 | 2026-11-24 18:04 | sim (VARZEA) |
| teste-1795539451 | 1 | 2 | 3 | 2025-03-03 12:00 | 2025-03-03 13:00 | **não** |
| teste-1795539999 | 1 | 2 | 3 | 2025-03-03 12:00 | 2025-03-03 13:00 | **não** |
| teste-1795542643 | 1 | 2 | 3 | 2025-03-03 12:00 | 2025-03-03 13:00 | **não** |

- Motivos das 84 leituras inválidas: temperature_c fora da faixa (120.0) = 78; temperature_c = 500 = 3; payload não é JSON válido = 3.
- As 3 estações `teste-*` não estão no mapa de bairros, então a agregação semanal as ignora com aviso. Parecem resíduos de testes (timestamps de 2025-03-03 e IDs numéricos). Não sei dizer qual rotina as gravou neste banco; não apaguei nada.
- As leituras inválidas de recife-001/002 (39 cada) vêm do simulador, que injeta valores fora de faixa de propósito.
- `sensor_weekly` não tem coluna `station_id` (agrega por bairro), então não dá para ver por estação ali.

## 10. API — POST /predict (API no ar em localhost:8000; `/health`: ok, modelo do Registry) — OK

Corpo esperado: `{"rows": [ {feature: valor, ...} ]}`. Minhas duas primeiras tentativas, com o objeto solto, deram 422 `rows: Field required`, o que é coerente com o contrato.

| caso | resultado |
|---|---|
| linha completa (27 features) | 200, RandomForest, classe alto, risk_score 71,18 |
| mesma linha + chave extra `chave_extra_xyz` | **200**, resposta idêntica (chave ignorada, como a descrição do schema diz) |
| sem `chuva_acum8` | 422 `[{"linha":0,"feature":"chuva_acum8","problema":"ausente"}]` |
| sem `chuva_acum8` e `casos_t` | 422 listando as duas: `casos_t` e `chuva_acum8`, ambas "ausente" |
| `casos_t = null` | 422 `valor inválido (esperado número): None` |
| `casos_t = "abc"` | 422 `valor inválido (esperado número): 'abc'` |

---

## Divergências, da mais grave para a menos grave

1. **`secrets.h` não está no `.gitignore`** (item 7). Hoje não existe esse arquivo no repositório, mas a equipe do ESP32 vai criá-lo; sem a regra, é fácil commitar a senha do Wi-Fi. Corrigir: acrescentar `secrets.h` (e, se quiser, `**/secrets.h`) ao `.gitignore`.
2. **Padrões inseguros de rede e credenciais** (item 7): Mosquitto anônimo em `0.0.0.0:1883`; API e dashboard em `0.0.0.0` sem autenticação; `DATABASE_URL` padrão com senha igual ao usuário. Aceitável numa máquina de desenvolvimento, mas precisa constar como limitação se o grupo demonstrar em rede compartilhada.
3. **Resíduos `teste-*` no banco do sensor** (item 9): 3 estações não mapeadas, com 9 leituras de 2025-03-03. Não afetam o modelo nem o dashboard (são ignoradas), mas aparecem se alguém listar as estações.
4. **Nuance do IC do bootstrap** (item 1): o IC [+0,021, +0,054] é o do bloco de 4 semanas; com blocos de 1 e 2 semanas o intervalo é um pouco mais largo. Citar o bloco no relatório.
5. **Sensibilidade das estatísticas da EDA** (item 3): os 76,2% e os limiares (0, 1) dependem de excluir as 8 primeiras semanas do painel. Sem essa exclusão os números mudam (limiar 0, 2; 76,1%).
6. **Backups locais com `.claude/`** (item 7): as branches `backup-antes-reescrita` e `backup-antes-reescrita-2` guardam o histórico antigo. Não foram enviadas ao GitHub; é só higiene local.

## O que você ainda precisa olhar com seus próprios olhos

- As páginas oficiais de licença: Portal de Dados Abertos do Recife (casos e GeoJSON), InfoDengue e Open-Meteo/ERA5 (item 8). Não consultei nenhuma.
- O notebook `notebooks/01_eda.ipynb` e os gráficos `reports/figuras/eda_*.png`: só conferi os números, não se os gráficos estão legíveis e se os textos batem com as figuras.
- O dashboard em celular, projetor e notebook (aparência do redesenho; ver a entrada de 24/11/2026 em `docs/USO_DE_IA.md`).
- O Airflow em `http://localhost:8081`: execução dos DAGs na interface e o download com `refresh=true`, que não foi testado.
- Se a regra de rótulo (limiar de baixo = 0 casos) e a escolha do período (2015 a 2025, sem 2013-2014) fazem sentido para a banca; isto é decisão de método, não de verificação.
- O MLflow do compose (`http://localhost:5000`) e o experimento `04-monitoramento-semanal`, que não estão no `mlflow.db` local.
- A origem dos três registros `teste-*` no banco: se vieram de um teste automatizado apontando para o Postgres do compose, convém isolar o banco dos testes.
