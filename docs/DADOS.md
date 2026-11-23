# Dados do AnteceDengue

## Origem
- **Conjunto:** "Casos de Dengue, Zika e Chikungunya" — Secretaria de Saúde do Recife (publicado pela EMPREL).
- **Portal:** Portal de Dados Abertos do Recife — https://dados.recife.pe.gov.br/dataset/casos-de-dengue-zika-e-chikungunya
- **API usada para descobrir os arquivos:** `https://dados.recife.pe.gov.br/api/3/action/package_show?id=casos-de-dengue-zika-e-chikungunya`
- **Licença:** Open Data Commons Open Database License (ODbL) — http://www.opendefinition.org/licenses/odc-odbl
- **Frequência de atualização informada pelo portal:** trimestral.
- **Data do download:** 23/11/2026.
- **Arquivos usados:** os 13 CSVs "Casos de Dengue" de 2013 a 2025 (um por ano) e, como apoio, a "Tabela de Bairros" e os dois JSON de metadados de dengue.

> Os registros do portal são notificações individuais (uma linha por notificação), já sem identificação direta do paciente. Os CSVs em `data/raw/` **não vão para o git** (ver `.gitignore`).

## Como baixar de novo
Com o ambiente virtual ativo, na raiz do repositório:

```powershell
python scripts/download_raw.py
python scripts/inspect_raw.py
```

- `download_raw.py` consulta a API do portal, baixa os CSVs para `data/raw/dengue_<ano>.csv` e os auxiliares para `data/raw/auxiliares/`.
- `inspect_raw.py` regera `reports/dados_inspecao.md`.

Se o download automático falhar, baixe manualmente pela página do conjunto de dados, recurso "Casos de Dengue <ano>", e salve cada arquivo como `data/raw/dengue_<ano>.csv` (o ano é lido do nome do arquivo).

## Pontos de atenção (detalhes em `reports/dados_inspecao.md`)
- Os nomes das colunas mudam entre anos (2013–2020: `dt_notificacao`, `no_bairro_residencia`, `tp_classificacao_final`…; 2021–2025: `DT_NOTIFIC`, `NM_BAIRRO`, `CLASSI_FIN`…; 2023 vem em minúsculas).
- Separador e formato de datas variam entre arquivos; o leitor em `src/data_recife.py` trata isso.
- Os códigos de classificação final seguem a ficha do SINAN (metadados do portal): 5 = descartado, 8 = inconclusivo, 10/11/12 = dengue (sem sinais de alarme / com sinais de alarme / grave); 1–4 = classificação antiga (2013–2016).
