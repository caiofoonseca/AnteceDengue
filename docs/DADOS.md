# Dados do AnteceDengue

## Origem
- **Conjunto:** "Casos de Dengue, Zika e Chikungunya" — Secretaria de Saúde do Recife (publicado pela EMPREL).
- **Portal:** Portal de Dados Abertos do Recife — https://dados.recife.pe.gov.br/dataset/casos-de-dengue-zika-e-chikungunya
- **API usada para descobrir os arquivos:** `https://dados.recife.pe.gov.br/api/3/action/package_show?id=casos-de-dengue-zika-e-chikungunya`
- **Licença:** Open Data Commons Open Database License (ODbL) — http://www.opendefinition.org/licenses/odc-odbl (conferida em 24/11/2026 nos metadados do conjunto no portal, campo `license_id = odc-odbl`).
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

## Clima semanal (um valor para o município todo)

| Variável | Fonte | Licença / observação |
|---|---|---|
| temp_media, temp_min, temp_max, umid_media | InfoDengue, `https://info.dengue.mat.br/api/alertcity` (geocode 2611606, doença dengue), colunas `tempmed`, `tempmin`, `tempmax`, `umidmed` | Licença dos dados **não localizada**; citar InfoDengue (Fiocruz/FGV) como fonte. A resposta real da API **não traz precipitação**. |
| chuva_mm | Open-Meteo Historical Weather API, `https://archive-api.open-meteo.com/v1/archive`, modelo **ERA5**, variável `precipitation_sum` (ponto -8.05, -34.9) | CC BY 4.0 (conferido em 24/11/2026 em open-meteo.com/en/licence e /en/terms). Exige link visível onde os dados forem exibidos: "Weather data by Open-Meteo.com" (https://open-meteo.com/). Citação: Zippenfenig, P. (2023). Open-Meteo.com Weather API [Computer software]. Zenodo. https://doi.org/10.5281/ZENODO.7970649. A API gratuita é só para uso não comercial; citar também o ERA5/Copernicus. **É reanálise em grade (~25 km), não observação de estação.** |

- **INMET foi tentado primeiro** (estação automática A301, Recife, zips anuais em `https://portal.inmet.gov.br/uploads/dadoshistoricos/<ano>.zip`) e descartado: chuva vazia em 2022 e 2023, estação ausente nos zips de 2024 e 2025. É usado só para validar o Open-Meteo em 2015–2021 (ver `reports/clima_qualidade.md`).
- Semana = domingo a sábado (`week_start`), somando a chuva por dia local; o número da semana epidemiológica não é usado, então a virada de ano não gera erro.

### Como baixar de novo
```powershell
python scripts/build_clima.py            # baixa InfoDengue + Open-Meteo, gera data/processed/clima_semanal.csv e reports/clima_qualidade.md
python scripts/build_clima.py --sem-download   # só reprocessa os brutos já em data/raw/clima/
```
Brutos ficam em `data/raw/clima/` (fora do git). Para refazer a validação com o INMET: `python -c "from src import data_clima as c; [c.download_inmet_year(y) for y in range(2015, 2022)]"` (cada zip tem ~100 MB).

## Limites dos bairros (mapa do dashboard)
- Fonte: Portal de Dados Abertos do Recife (https://dados.recife.pe.gov.br), conjunto "Área urbana", recurso "Bairros do Recife" (GeoJSON), obtido via API CKAN em 24/11/2026.
- Licença: ODbL (Open Database License), conferida em 24/11/2026 nos metadados do conjunto "Área urbana" no portal (`license_id = odc-odbl`).
- Tratamento: `scripts/build_bairros_geojson.py` normaliza os nomes com o mesmo normalizador do painel (94 de 94 bairros casam) e simplifica os polígonos (Douglas-Peucker, tolerância 0,00002 grau, 5 casas decimais). A simplificação é só visual; o arquivo (`app/assets/bairros.geojson`, ~0,19 MB) não serve para medições de área.
- O download do portal oscila (erro 503 intermitente); o script tenta de novo até 6 vezes.

## Licenças (resumo, conferido em 24/11/2026)
| Dado | Licença | Observação |
|---|---|---|
| Casos de dengue (Portal de Dados Abertos do Recife) | ODbL | conferida nos metadados do conjunto no portal |
| GeoJSON de bairros (`app/assets/bairros.geojson`) | ODbL | conferida nos metadados do conjunto "Área urbana" |
| Chuva (Open-Meteo, ERA5) | CC BY 4.0 | link obrigatório "Weather data by Open-Meteo.com"; citação Zippenfenig (2023), DOI 10.5281/ZENODO.7970649; uso gratuito só não comercial |
| Temperatura e umidade (InfoDengue) | não localizada | citar Fiocruz/FGV |

**Nota sobre a ODbL:** a licença tem cláusula de compartilhamento pela mesma licença (share-alike) para bases de dados derivadas que forem distribuídas. O painel e os arquivos derivados dos casos e do GeoJSON, se publicados, devem manter a ODbL e a atribuição ao Portal de Dados Abertos do Recife.

