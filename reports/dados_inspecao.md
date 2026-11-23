# Inspeção dos dados brutos de dengue (Recife)

## 1. Arquivos lidos

| arquivo | ano | encoding | separador | linhas | colunas |
|---|---|---|---|---|---|
| dengue_2013.csv | 2013 | utf-8-sig | ';' | 3229 | 79 |
| dengue_2014.csv | 2014 | utf-8-sig | ';' | 1192 | 79 |
| dengue_2015.csv | 2015 | utf-8-sig | ',' | 34556 | 126 |
| dengue_2016.csv | 2016 | utf-8-sig | ';' | 18612 | 126 |
| dengue_2017.csv | 2017 | utf-8-sig | ';' | 2454 | 107 |
| dengue_2018.csv | 2018 | utf-8-sig | ';' | 2687 | 111 |
| dengue_2019.csv | 2019 | utf-8-sig | ',' | 7308 | 126 |
| dengue_2020.csv | 2020 | utf-8-sig | ';' | 3540 | 125 |
| dengue_2021.csv | 2021 | utf-8-sig | ';' | 10898 | 126 |
| dengue_2022.csv | 2022 | utf-8-sig | ';' | 2906 | 130 |
| dengue_2023.csv | 2023 | utf-8-sig | ';' | 3523 | 130 |
| dengue_2024.csv | 2024 | utf-8-sig | ';' | 10548 | 130 |
| dengue_2025.csv | 2025 | utf-8-sig | ';' | 9187 | 130 |

Anos presentes: 2013–2025 (13 arquivos). Anos faltando em 2013–2025: nenhum.

## 2. Colunas e mudanças entre anos

Conjuntos distintos de colunas (nomes exatos): **10**.

### Esquema 1 — anos [2013, 2014] (79 colunas)

`nu_notificacao`, `tp_notificacao`, `co_cid`, `dt_notificacao`, `ds_semana_notificacao`, `notificacao_ano`, `co_uf_notificacao`, `co_municipio_notificacao`, `id_regional`, `co_unidade_notificacao`, `dt_diagnostico_sintoma`, `ds_semana_sintoma`, `dt_nascimento`, `nu_idade`, `tp_sexo`, `tp_gestante`, `tp_raca_cor`, `tp_escolaridade`, `co_uf_residencia`, `co_municipio_residencia`, `co_regional_residencia`, `co_distrito_residencia`, `co_bairro_residencia`, `no_bairro_residencia`, `co_logradouro_residencia`, `nome_logradouro_residencia`, `co_geo_campo_1`, `co_geo_campo_2`, `ds_referencia_residencia`, `nu_cep_residencia`, `tp_zona_residencia`, `co_pais_residencia`, `tp_duplicidade`, `dt_digitacao`, `dt_transf_us`, `dt_transf_dm`, `dt_transf_sm`, `dt_transf_rm`, `dt_transf_rs`, `dt_transf_se`, `nu_lote_vertical`, `nu_lote_horizontal`, `tp_fluxo_retorno`, `st_fluxo_retorno_recebido`, `ds_identificador_registro`, `st_importado`, `dt_investigacao`, `co_cbo_ocupacao`, `dt_coleta_exame`, `tp_result_exame`, `dt_coleta_NS1`, `Tp_result_NS1`, `dt_coleta_isolamento`, `tp_result_isolamento`, `dt_coleta_rtpcr`, `tp_result_rtpcr`, `tp_sorotipo`, `tp_result_histopatologia`, `tp_result_imunohistoquimica`, `tp_classificacao_final`, `tp_criterio_confirmacao`, `tp_autoctone_residencia`, `co_uf_infeccao`, `co_pais_infeccao`, `co_municipio_infeccao`, `co_distrito_infeccao`, `co_bairro_infeccao`, `no_bairro_infeccao`, `st_doenca_trabalho`, `tp_evolucao_caso`, `dt_obito`, `dt_encerramento`, `st_ocorreu_hospitalizacao`, `dt_internacao`, `co_uf_hospital`, `co_municipio_hospital`, `co_unidade_hospital`, `nu_ddd_hospital`, `nu_telefone_hospital`

### Esquema 2 — anos [2015, 2016] (126 colunas)

`nu_notificacao`, `tp_notificacao`, `co_cid`, `dt_notificacao`, `ds_semana_notificacao`, `notificacao_ano`, `co_uf_notificacao`, `co_municipio_notificacao`, `id_regional`, `co_unidade_notificacao`, `dt_diagnostico_sintoma`, `ds_semana_sintoma`, `dt_nascimento`, `nu_idade`, `tp_sexo`, `tp_gestante`, `tp_raca_cor`, `tp_escolaridade`, `co_uf_residencia`, `co_municipio_residencia`, `co_regional_residencia`, `co_distrito_residencia`, `co_bairro_residencia`, `no_bairro_residencia`, `co_logradouro_residencia`, `nome_logradouro_residencia`, `nu_cep_residencia`, `tp_zona_residencia`, `co_pais_residencia`, `dt_investigacao`, `co_cbo_ocupacao`, `febre`, `mialgia`, `cefaleia`, `exantema`, `vomito`, `nausea`, `dor_costas`, `conjutivite`, `artrite`, `artralgia`, `petequia_n`, `leucopenia`, `laco`, `dor_retro`, `diabetes`, `hematolog`, `hepatopat`, `renal`, `hipertensao`, `acido_pept`, `auto_imune`, `dt_chil_s1`, `dt_chil_s2`, `dt_prnt`, `res_chiks1`, `res_chiks2`, `resul_prnt`, `dt_coleta_exame`, `tp_result_exame`, `dt_coleta_NS1`, `Tp_result_NS1`, `dt_coleta_isolamento`, `tp_result_isolamento`, `dt_coleta_rtpcr`, `tp_result_rtpcr`, `tp_sorotipo`, `tp_result_histopatologia`, `tp_result_imunohistoquimica`, `st_ocorreu_hospitalizacao`, `dt_internacao`, `co_uf_hospital`, `co_municipio_hospital`, `tp_autoctone_residencia`, `co_uf_infeccao`, `co_pais_infeccao`, `co_municipio_infeccao`, `co_distrito_infeccao`, `co_bairro_infeccao`, `no_bairro_infeccao`, `tp_classificacao_final`, `tp_criterio_confirmacao`, `st_doenca_trabalho`, `clinc_chik`, `tp_evolucao_caso`, `dt_obito`, `dt_encerramento`, `alrm_hipot`, `alrm_plaq`, `alrm_vom`, `alrm_sang`, `alrm_hemat`, `alrm_abdom`, `alrm_letar`, `alrm_hepat`, `alrm_liq`, `dt_alrm`, `grav_pulso`, `grav_conv`, `grav_ench`, `grav_insuf`, `grav_taqui`, `grav_extre`, `grav_hipot`, `grav_hemat`, `grav_melen`, `grav_metro`, `grav_sang`, `grav_ast`, `grav_mioc`, `grav_consc`, `grav_orgao`, `dt_grav`, `mani_hemor`, `epistaxe`, `gengivo`, `metro`, `petequias`, `hematura`, `sangram`, `laco_n`, `plasmatico`, `evidencia`, `plaq_menor`, `con_fhd`, `complica`

### Esquema 3 — anos [2017] (107 colunas)

`nu_notificacao`, `tp_notificacao`, `co_cid`, `dt_notificacao`, `ds_semana_notificacao`, `notificacao_ano`, `co_uf_notificacao`, `co_municipio_notificacao`, `id_regional`, `co_unidade_notificacao`, `dt_diagnostico_sintoma`, `ds_semana_sintoma`, `dt_nascimento`, `nu_idade`, `tp_sexo`, `tp_gestante`, `tp_raca_cor`, `tp_escolaridade`, `co_uf_residencia`, `co_municipio_residencia`, `co_regional_residencia`, `co_distrito_residencia`, `co_bairro_residencia`, `no_bairro_residencia`, `co_logradouro_residencia`, `nome_logradouro_residencia`, `nu_cep_residencia`, `tp_zona_residencia`, `co_pais_residencia`, `dt_investigacao`, `co_cbo_ocupacao`, `febre`, `mialgia`, `cefaleia`, `exantema`, `vomito`, `nausea`, `dor_costas`, `conjutivite`, `artrite`, `artralgia`, `petequia_n`, `leucopenia`, `laco`, `dor_retro`, `diabetes`, `hematolog`, `hepatopat`, `renal`, `hipertensao`, `acido_pept`, `auto_imune`, `dt_chil_s1`, `dt_chil_s2`, `dt_prnt`, `res_chiks1`, `res_chiks2`, `resul_prnt`, `dt_coleta_exame`, `tp_result_exame`, `dt_coleta_NS1`, `Tp_result_NS1`, `dt_coleta_isolamento`, `tp_result_isolamento`, `dt_coleta_rtpcr`, `tp_result_rtpcr`, `tp_sorotipo`, `tp_result_histopatologia`, `tp_result_imunohistoquimica`, `st_ocorreu_hospitalizacao`, `dt_internacao`, `co_uf_hospital`, `co_municipio_hospital`, `tp_autoctone_residencia`, `co_uf_infeccao`, `co_pais_infeccao`, `co_municipio_infeccao`, `co_distrito_infeccao`, `co_bairro_infeccao`, `no_bairro_infeccao`, `tp_classificacao_final`, `tp_criterio_confirmacao`, `st_doenca_trabalho`, `clinc_chik`, `tp_evolucao_caso`, `dt_obito`, `dt_encerramento`, `alrm_hipot`, `alrm_plaq`, `alrm_vom`, `alrm_sang`, `alrm_hemat`, `alrm_abdom`, `alrm_letar`, `alrm_hepat`, `alrm_liq`, `dt_alrm`, `epistaxe`, `gengivo`, `metro`, `petequias`, `hematura`, `sangram`, `laco_n`, `plasmatico`, `evidencia`, `plaq_menor`

### Esquema 4 — anos [2018] (111 colunas)

`nu_notificacao`, `tp_notificacao`, `co_cid`, `dt_notificacao`, `ds_semana_notificacao`, `notificacao_ano`, `co_uf_notificacao`, `co_municipio_notificacao`, `id_regional`, `co_unidade_notificacao`, `dt_diagnostico_sintoma`, `ds_semana_sintoma`, `dt_nascimento`, `nu_idade`, `tp_sexo`, `tp_gestante`, `tp_raca_cor`, `tp_escolaridade`, `co_uf_residencia`, `co_municipio_residencia`, `co_regional_residencia`, `co_distrito_residencia`, `co_bairro_residencia`, `no_bairro_residencia`, `co_logradouro_residencia`, `nome_logradouro_residencia`, `nu_cep_residencia`, `tp_zona_residencia`, `co_pais_residencia`, `dt_investigacao`, `co_cbo_ocupacao`, `febre`, `mialgia`, `cefaleia`, `exantema`, `vomito`, `nausea`, `dor_costas`, `conjutivite`, `artrite`, `artralgia`, `petequia_n`, `leucopenia`, `laco`, `dor_retro`, `diabetes`, `hematolog`, `hepatopat`, `renal`, `hipertensao`, `acido_pept`, `auto_imune`, `dt_chil_s1`, `dt_chil_s2`, `dt_prnt`, `res_chiks1`, `res_chiks2`, `resul_prnt`, `dt_coleta_exame`, `tp_result_exame`, `dt_coleta_NS1`, `Tp_result_NS1`, `dt_coleta_isolamento`, `tp_result_isolamento`, `dt_coleta_rtpcr`, `tp_result_rtpcr`, `tp_sorotipo`, `tp_result_histopatologia`, `tp_result_imunohistoquimica`, `st_ocorreu_hospitalizacao`, `dt_internacao`, `co_uf_hospital`, `co_municipio_hospital`, `hospital`, `ddd_hospital`, `tel_hospital`, `tp_autoctone_residencia`, `co_uf_infeccao`, `co_pais_infeccao`, `co_municipio_infeccao`, `co_distrito_infeccao`, `co_bairro_infeccao`, `no_bairro_infeccao`, `tp_classificacao_final`, `tp_criterio_confirmacao`, `st_doenca_trabalho`, `clinc_chik`, `tp_evolucao_caso`, `dt_obito`, `dt_encerramento`, `alrm_hipot`, `alrm_plaq`, `alrm_vom`, `alrm_sang`, `alrm_hemat`, `alrm_abdom`, `alrm_letar`, `alrm_hepat`, `alrm_liq`, `dt_alrm`, `epistaxe`, `gengivo`, `metro`, `petequias`, `hematura`, `sangram`, `laco_n`, `plasmatico`, `evidencia`, `plaq_menor`, `con_fhd`

### Esquema 5 — anos [2019] (126 colunas)

`nu_notificacao`, `tp_notificacao`, `co_cid`, `dt_notificacao`, `ds_semana_notificacao`, `notificacao_ano`, `co_uf_notificacao`, `co_municipio_notificacao`, `id_regional`, `co_unidade_notificacao`, `dt_diagnostico_sintoma`, `ds_semana_sintoma`, `dt_nascimento`, `nu_idade`, `tp_sexo`, `tp_gestante`, `tp_raca_cor`, `tp_escolaridade`, `co_uf_residencia`, `co_municipio_residencia`, `co_regional_residencia`, `co_distrito_residencia`, `co_bairro_residencia`, `no_bairro_residencia`, `co_logradouro_residencia`, `nome_logradouro_residencia`, `nu_cep_residencia`, `tp_zona_residencia`, `co_pais_residencia`, `dt_investigacao`, `co_cbo_ocupacao`, `febre`, `mialgia`, `cefaleia`, `exantema`, `vomito`, `nausea`, `dor_costas`, `conjutivite`, `artrite`, `artralgia`, `petequia_n`, `leucopenia`, `laco`, `dor_retro`, `diabetes`, `hematolog`, `hepatopat`, `renal`, `hipertensao`, `acido_pept`, `auto_imune`, `dt_chil_s1`, `dt_chil_s2`, `dt_prnt`, `res_chiks1`, `res_chiks2`, `resul_prnt`, `dt_coleta_exame`, `tp_result_exame`, `dt_coleta_NS1`, `Tp_result_NS1`, `dt_coleta_isolamento`, `tp_result_isolamento`, `dt_coleta_rtpcr`, `tp_result_rtpcr`, `tp_sorotipo`, `tp_result_histopatologia`, `tp_result_imunohistoquimica`, `st_ocorreu_hospitalizacao`, `dt_internacao`, `co_uf_hospital`, `co_municipio_hospital`, `tp_autoctone_residencia`, `co_uf_infeccao`, `co_pais_infeccao`, `co_municipio_infeccao`, `co_distrito_infeccao`, `co_bairro_infeccao`, `no_bairro_infeccao`, `tp_classificacao_final`, `tp_criterio_confirmacao`, `st_doenca_trabalho`, `clinc_chik`, `tp_evolucao_caso`, `dt_obito`, `dt_encerramento`, `alrm_hipot`, `alrm_plaq`, `alrm_vom`, `alrm_sang`, `alrm_hemat`, `alrm_abdom`, `alrm_letar`, `alrm_hepat`, `alrm_liq`, `dt_alrm`, `grav_pulso`, `grav_conv`, `grav_ench`, `grav_insuf`, `grav_taqui`, `grav_extre`, `grav_hipot`, `grav_hemat`, `grav_melen`, `grav_metro`, `grav_sang`, `grav_ast`, `grav_mioc`, `grav_consc`, `grav_orgao`, `dt_grav`, `mani_hemor`, `epistaxe`, `gengivo`, `metro`, `petequias`, `hematura`, `sangram`, `laco_n`, `plasmatico`, `evidencia`, `plaq_menor`, `conf_fhd`, `complica`

### Esquema 6 — anos [2020] (125 colunas)

`nu_notificacao`, `tp_notificacao`, `co_cid`, `dt_notificacao`, `ds_semana_notificacao`, `notificacao_ano`, `co_uf_notificacao`, `co_municipio_notificacao`, `id_regional`, `co_unidade_notificacao`, `dt_diagnostico_sintoma`, `ds_semana_sintoma`, `dt_nascimento`, `nu_idade`, `tp_sexo`, `tp_gestante`, `tp_raca_cor`, `tp_escolaridade`, `co_uf_residencia`, `co_municipio_residencia`, `co_regional_residencia`, `co_distrito_residencia`, `co_bairro_residencia`, `no_bairro_residencia`, `co_logradouro_residencia`, `nome_logradouro_residencia`, `nu_cep_residencia`, `tp_zona_residencia`, `co_pais_residencia`, `dt_investigacao`, `co_cbo_ocupacao`, `febre`, `mialgia`, `cefaleia`, `exantema`, `vomito`, `nausea`, `dor_costas`, `conjutivite`, `artrite`, `artralgia`, `petequia_n`, `leucopenia`, `laco`, `dor_retro`, `diabetes`, `hematolog`, `hepatopat`, `renal`, `hipertensao`, `acido_pept`, `auto_imune`, `dt_chil_s1`, `dt_chil_s2`, `dt_prnt`, `res_chiks1`, `res_chiks2`, `resul_prnt`, `dt_coleta_exame`, `tp_result_exame`, `dt_coleta_NS1`, `Tp_result_NS1`, `dt_coleta_isolamento`, `tp_result_isolamento`, `dt_coleta_rtpcr`, `tp_result_rtpcr`, `tp_sorotipo`, `tp_result_histopatologia`, `tp_result_imunohistoquimica`, `st_ocorreu_hospitalizacao`, `dt_internacao`, `co_uf_hospital`, `co_municipio_hospital`, `tp_autoctone_residencia`, `co_uf_infeccao`, `co_pais_infeccao`, `co_municipio_infeccao`, `co_distrito_infeccao`, `co_bairro_infeccao`, `no_bairro_infeccao`, `tp_classificacao_final`, `tp_criterio_confirmacao`, `st_doenca_trabalho`, `clinc_chik`, `tp_evolucao_caso`, `dt_obito`, `dt_encerramento`, `alrm_hipot`, `alrm_plaq`, `alrm_vom`, `alrm_sang`, `alrm_hemat`, `alrm_abdom`, `alrm_letar`, `alrm_hepat`, `alrm_liq`, `dt_alrm`, `grav_pulso`, `grav_conv`, `grav_ench`, `grav_insuf`, `grav_taqui`, `grav_extre`, `grav_hipot`, `grav_hemat`, `grav_melen`, `grav_metro`, `grav_sang`, `grav_ast`, `grav_mioc`, `grav_consc`, `grav_orgao`, `dt_grav`, `mani_hemor`, `epistaxe`, `gengivo`, `metro`, `petequias`, `hematura`, `sangram`, `laco_n`, `plasmatico`, `evidencia`, `plaq_menor`, `con_fhd`

### Esquema 7 — anos [2021] (126 colunas)

`NU_NOTIFIC`, `TP_NOT`, `ID_AGRAVO`, `DT_NOTIFIC`, `SEM_NOT`, `NU_ANO`, `SG_UF_NOT`, `ID_MUNICIP`, `ID_REGIONA`, `ID_UNIDADE`, `DT_SIN_PRI`, `SEM_PRI`, `DT_NASC`, `NU_IDADE_N`, `CS_SEXO`, `CS_GESTANT`, `CS_RACA`, `CS_ESCOL_N`, `SG_UF`, `ID_MN_RESI`, `ID_RG_RESI`, `ID_DISTRIT`, `ID_BAIRRO`, `NM_BAIRRO`, `ID_LOGRADO`, `NM_LOGRADO`, `NU_CEP`, `CS_ZONA`, `ID_PAIS`, `DT_INVEST`, `ID_OCUPA_N`, `FEBRE`, `MIALGIA`, `CEFALEIA`, `EXANTEMA`, `VOMITO`, `NAUSEA`, `DOR_COSTAS`, `CONJUNTVIT`, `ARTRITE`, `ARTRALGIA`, `PETEQUIA_N`, `LEUCOPENIA`, `LACO`, `DOR_RETRO`, `DIABETES`, `HEMATOLOG`, `HEPATOPAT`, `RENAL`, `HIPERTENSA`, `ACIDO_PEPT`, `AUTO_IMUNE`, `DT_CHIK_S1`, `DT_CHIK_S2`, `DT_PRNT`, `RES_CHIKS1`, `RES_CHIKS2`, `RESUL_PRNT`, `DT_SORO`, `RESUL_SORO`, `DT_NS1`, `RESUL_NS1`, `DT_VIRAL`, `RESUL_VI_N`, `DT_PCR`, `RESUL_PCR_`, `SOROTIPO`, `HISTOPA_N`, `IMUNOH_N`, `HOSPITALIZ`, `DT_INTERNA`, `UF`, `TPAUTOCTO`, `COUFINF`, `COPAISINF`, `COMUNINF`, `CODISINF`, `CO_BAINF`, `NOBAIINF`, `CLASSI_FIN`, `CRITERIO`, `DOENCA_TRA`, `CLINC_CHIK`, `EVOLUCAO`, `DT_OBITO`, `DT_ENCERRA`, `ALRM_HIPOT`, `ALRM_PLAQ`, `ALRM_VOM`, `ALRM_SANG`, `ALRM_HEMAT`, `ALRM_ABDOM`, `ALRM_LETAR`, `ALRM_HEPAT`, `ALRM_LIQ`, `DT_ALRM`, `GRAV_PULSO`, `GRAV_CONV`, `GRAV_ENCH`, `GRAV_INSUF`, `GRAV_TAQUI`, `GRAV_EXTRE`, `GRAV_HIPOT`, `GRAV_HEMAT`, `GRAV_MELEN`, `GRAV_METRO`, `GRAV_SANG`, `GRAV_AST`, `GRAV_MIOC`, `GRAV_CONSC`, `GRAV_ORGAO`, `DT_GRAV`, `MANI_HEMOR`, `EPISTAXE`, `GENGIVO`, `METRO`, `PETEQUIAS`, `HEMATURA`, `SANGRAM`, `LACO_N`, `PLASMATICO`, `EVIDENCIA`, `PLAQ_MENOR`, `CON_FHD`, `COMPLICA`, `NU_LOTE_I`

### Esquema 8 — anos [2022] (130 colunas)

`NU_NOTIFIC`, `TP_NOT`, `ID_AGRAVO`, `DT_NOTIFIC`, `SEM_NOT`, `NU_ANO`, `SG_UF_NOT`, `ID_MUNICIP`, `ID_REGIONA`, `ID_UNIDADE`, `DT_SIN_PRI`, `SEM_PRI`, `DT_NASC`, `NU_IDADE_N`, `CS_SEXO`, `CS_GESTANT`, `CS_RACA`, `CS_ESCOL_N`, `SG_UF`, `ID_MN_RESI`, `ID_RG_RESI`, `ID_DISTRIT`, `ID_BAIRRO`, `NM_BAIRRO`, `ID_LOGRADO`, `NM_LOGRADO`, `NU_CEP`, `CS_ZONA`, `ID_PAIS`, `DT_INVEST`, `ID_OCUPA_N`, `FEBRE`, `MIALGIA`, `CEFALEIA`, `EXANTEMA`, `VOMITO`, `NAUSEA`, `DOR_COSTAS`, `CONJUNTVIT`, `ARTRITE`, `ARTRALGIA`, `PETEQUIA_N`, `LEUCOPENIA`, `LACO`, `DOR_RETRO`, `DIABETES`, `HEMATOLOG`, `HEPATOPAT`, `RENAL`, `HIPERTENSA`, `ACIDO_PEPT`, `AUTO_IMUNE`, `DT_CHIK_S1`, `DT_CHIK_S2`, `DT_PRNT`, `RES_CHIKS1`, `RES_CHIKS2`, `RESUL_PRNT`, `DT_SORO`, `RESUL_SORO`, `DT_NS1`, `RESUL_NS1`, `DT_VIRAL`, `RESUL_VI_N`, `DT_PCR`, `RESUL_PCR_`, `SOROTIPO`, `HISTOPA_N`, `IMUNOH_N`, `HOSPITALIZ`, `DT_INTERNA`, `UF`, `MUNICIPIO`, `HOSPITAL`, `DDD_HOSP`, `TEL_HOSP`, `TPAUTOCTO`, `COUFINF`, `COPAISINF`, `COMUNINF`, `CODISINF`, `CO_BAINF`, `NOBAIINF`, `CLASSI_FIN`, `CRITERIO`, `DOENCA_TRA`, `CLINC_CHIK`, `EVOLUCAO`, `DT_OBITO`, `DT_ENCERRA`, `ALRM_HIPOT`, `ALRM_PLAQ`, `ALRM_VOM`, `ALRM_SANG`, `ALRM_HEMAT`, `ALRM_ABDOM`, `ALRM_LETAR`, `ALRM_HEPAT`, `ALRM_LIQ`, `DT_ALRM`, `GRAV_PULSO`, `GRAV_CONV`, `GRAV_ENCH`, `GRAV_INSUF`, `GRAV_TAQUI`, `GRAV_EXTRE`, `GRAV_HIPOT`, `GRAV_HEMAT`, `GRAV_MELEN`, `GRAV_METRO`, `GRAV_SANG`, `GRAV_AST`, `GRAV_MIOC`, `GRAV_CONSC`, `GRAV_ORGAO`, `DT_GRAV`, `MANI_HEMOR`, `EPISTAXE`, `GENGIVO`, `METRO`, `PETEQUIAS`, `HEMATURA`, `SANGRAM`, `LACO_N`, `PLASMATICO`, `EVIDENCIA`, `PLAQ_MENOR`, `CON_FHD`, `COMPLICA`, `NU_LOTE_I`

### Esquema 9 — anos [2023] (130 colunas)

`nu_notific`, `tp_not`, `id_agravo`, `dt_notific`, `sem_not`, `nu_ano`, `sg_uf_not`, `id_municip`, `id_regiona`, `id_unidade`, `dt_sin_pri`, `sem_pri`, `dt_nasc`, `nu_idade_n`, `cs_sexo`, `cs_gestant`, `cs_raca`, `cs_escol_n`, `sg_uf`, `id_mn_resi`, `id_rg_resi`, `id_distrit`, `id_bairro`, `nm_bairro`, `id_logrado`, `nm_logrado`, `nu_cep`, `id_pais`, `dt_invest`, `id_ocupa_n`, `febre`, `mialgia`, `cefaleia`, `exantema`, `vomito`, `nausea`, `dor_costas`, `conjuntvit`, `artrite`, `artralgia`, `petequia_n`, `leucopenia`, `laco`, `dor_retro`, `diabetes`, `hematolog`, `hepatopat`, `renal`, `hipertensa`, `acido_pept`, `auto_imune`, `dt_chik_s1`, `dt_chik_s2`, `dt_prnt`, `res_chiks1`, `res_chiks2`, `resul_prnt`, `dt_soro`, `resul_soro`, `dt_ns1`, `resul_ns1`, `dt_viral`, `resul_vi_n`, `dt_pcr`, `resul_pcr_`, `sorotipo`, `histopa_n`, `imunoh_n`, `hospitaliz`, `dt_interna`, `uf`, `municipio`, `hospital`, `ddd_hosp`, `tel_hosp`, `tpautocto`, `coufinf`, `copaisinf`, `comuninf`, `codisinf`, `co_bainf`, `nobaiinf`, `classi_fin`, `criterio`, `doenca_tra`, `clinc_chik`, `evolucao`, `dt_obito`, `dt_encerra`, `alrm_hipot`, `alrm_plaq`, `alrm_vom`, `alrm_sang`, `alrm_hemat`, `alrm_abdom`, `alrm_letar`, `alrm_hepat`, `alrm_liq`, `dt_alrm`, `grav_pulso`, `grav_conv`, `grav_ench`, `grav_insuf`, `grav_taqui`, `grav_extre`, `grav_hipot`, `grav_hemat`, `grav_melen`, `grav_metro`, `grav_sang`, `grav_ast`, `grav_mioc`, `grav_consc`, `grav_orgao`, `dt_grav`, `mani_hemor`, `epistaxe`, `gengivo`, `metro`, `petequias`, `hematura`, `sangram`, `laco_n`, `plasmatico`, `evidencia`, `plaq_menor`, `con_fhd`, `complica`, `nu_lote_i`, `ds_obs`

### Esquema 10 — anos [2024, 2025] (130 colunas)

`NU_NOTIFIC`, `TP_NOT`, `ID_AGRAVO`, `DT_NOTIFIC`, `SEM_NOT`, `NU_ANO`, `SG_UF_NOT`, `ID_MUNICIP`, `ID_REGIONA`, `ID_UNIDADE`, `DT_SIN_PRI`, `SEM_PRI`, `DT_NASC`, `NU_IDADE_N`, `CS_SEXO`, `CS_GESTANT`, `CS_RACA`, `CS_ESCOL_N`, `SG_UF`, `ID_MN_RESI`, `ID_RG_RESI`, `ID_DISTRIT`, `ID_BAIRRO`, `NM_BAIRRO`, `ID_LOGRADO`, `NM_LOGRADO`, `NU_CEP`, `ID_PAIS`, `DT_INVEST`, `ID_OCUPA_N`, `FEBRE`, `MIALGIA`, `CEFALEIA`, `EXANTEMA`, `VOMITO`, `NAUSEA`, `DOR_COSTAS`, `CONJUNTVIT`, `ARTRITE`, `ARTRALGIA`, `PETEQUIA_N`, `LEUCOPENIA`, `LACO`, `DOR_RETRO`, `DIABETES`, `HEMATOLOG`, `HEPATOPAT`, `RENAL`, `HIPERTENSA`, `ACIDO_PEPT`, `AUTO_IMUNE`, `DT_CHIK_S1`, `DT_CHIK_S2`, `DT_PRNT`, `RES_CHIKS1`, `RES_CHIKS2`, `RESUL_PRNT`, `DT_SORO`, `RESUL_SORO`, `DT_NS1`, `RESUL_NS1`, `DT_VIRAL`, `RESUL_VI_N`, `DT_PCR`, `RESUL_PCR_`, `SOROTIPO`, `HISTOPA_N`, `IMUNOH_N`, `HOSPITALIZ`, `DT_INTERNA`, `UF`, `MUNICIPIO`, `HOSPITAL`, `DDD_HOSP`, `TEL_HOSP`, `TPAUTOCTO`, `COUFINF`, `COPAISINF`, `COMUNINF`, `CODISINF`, `CO_BAINF`, `NOBAIINF`, `CLASSI_FIN`, `CRITERIO`, `DOENCA_TRA`, `CLINC_CHIK`, `EVOLUCAO`, `DT_OBITO`, `DT_ENCERRA`, `ALRM_HIPOT`, `ALRM_PLAQ`, `ALRM_VOM`, `ALRM_SANG`, `ALRM_HEMAT`, `ALRM_ABDOM`, `ALRM_LETAR`, `ALRM_HEPAT`, `ALRM_LIQ`, `DT_ALRM`, `GRAV_PULSO`, `GRAV_CONV`, `GRAV_ENCH`, `GRAV_INSUF`, `GRAV_TAQUI`, `GRAV_EXTRE`, `GRAV_HIPOT`, `GRAV_HEMAT`, `GRAV_MELEN`, `GRAV_METRO`, `GRAV_SANG`, `GRAV_AST`, `GRAV_MIOC`, `GRAV_CONSC`, `GRAV_ORGAO`, `DT_GRAV`, `MANI_HEMOR`, `EPISTAXE`, `GENGIVO`, `METRO`, `PETEQUIAS`, `HEMATURA`, `SANGRAM`, `LACO_N`, `PLASMATICO`, `EVIDENCIA`, `PLAQ_MENOR`, `CON_FHD`, `COMPLICA`, `NU_LOTE_I`, `DS_OBS`

### Colunas-chave por ano (nome real no arquivo)

| ano | data_notificacao | data_sintomas | bairro_residencia | agravo | classificacao_final | criterio | evolucao |
|---|---|---|---|---|---|---|---|
| 2013 | dt_notificacao | dt_diagnostico_sintoma | no_bairro_residencia | co_cid | tp_classificacao_final | tp_criterio_confirmacao | tp_evolucao_caso |
| 2014 | dt_notificacao | dt_diagnostico_sintoma | no_bairro_residencia | co_cid | tp_classificacao_final | tp_criterio_confirmacao | tp_evolucao_caso |
| 2015 | dt_notificacao | dt_diagnostico_sintoma | no_bairro_residencia | co_cid | tp_classificacao_final | tp_criterio_confirmacao | tp_evolucao_caso |
| 2016 | dt_notificacao | dt_diagnostico_sintoma | no_bairro_residencia | co_cid | tp_classificacao_final | tp_criterio_confirmacao | tp_evolucao_caso |
| 2017 | dt_notificacao | dt_diagnostico_sintoma | no_bairro_residencia | co_cid | tp_classificacao_final | tp_criterio_confirmacao | tp_evolucao_caso |
| 2018 | dt_notificacao | dt_diagnostico_sintoma | no_bairro_residencia | co_cid | tp_classificacao_final | tp_criterio_confirmacao | tp_evolucao_caso |
| 2019 | dt_notificacao | dt_diagnostico_sintoma | no_bairro_residencia | co_cid | tp_classificacao_final | tp_criterio_confirmacao | tp_evolucao_caso |
| 2020 | dt_notificacao | dt_diagnostico_sintoma | no_bairro_residencia | co_cid | tp_classificacao_final | tp_criterio_confirmacao | tp_evolucao_caso |
| 2021 | DT_NOTIFIC | DT_SIN_PRI | NM_BAIRRO | ID_AGRAVO | CLASSI_FIN | CRITERIO | EVOLUCAO |
| 2022 | DT_NOTIFIC | DT_SIN_PRI | NM_BAIRRO | ID_AGRAVO | CLASSI_FIN | CRITERIO | EVOLUCAO |
| 2023 | dt_notific | dt_sin_pri | nm_bairro | id_agravo | classi_fin | criterio | evolucao |
| 2024 | DT_NOTIFIC | DT_SIN_PRI | NM_BAIRRO | ID_AGRAVO | CLASSI_FIN | CRITERIO | EVOLUCAO |
| 2025 | DT_NOTIFIC | DT_SIN_PRI | NM_BAIRRO | ID_AGRAVO | CLASSI_FIN | CRITERIO | EVOLUCAO |

## 3. Linhas por ano

| ano | linhas |
|---|---|
| 2013 | 3229 |
| 2014 | 1192 |
| 2015 | 34556 |
| 2016 | 18612 |
| 2017 | 2454 |
| 2018 | 2687 |
| 2019 | 7308 |
| 2020 | 3540 |
| 2021 | 10898 |
| 2022 | 2906 |
| 2023 | 3523 |
| 2024 | 10548 |
| 2025 | 9187 |

## 4. Tipos inferidos e % de nulos

**data_notificacao**

| ano | coluna | tipo | % nulos |
|---|---|---|---|
| 2013 | dt_notificacao | data | 0.0% |
| 2014 | dt_notificacao | data | 0.0% |
| 2015 | dt_notificacao | data | 0.1% |
| 2016 | dt_notificacao | data | 0.0% |
| 2017 | dt_notificacao | data | 0.0% |
| 2018 | dt_notificacao | data | 0.0% |
| 2019 | dt_notificacao | data | 0.1% |
| 2020 | dt_notificacao | data | 0.0% |
| 2021 | DT_NOTIFIC | data | 0.0% |
| 2022 | DT_NOTIFIC | data | 1.0% |
| 2023 | dt_notific | data | 0.0% |
| 2024 | DT_NOTIFIC | data | 0.0% |
| 2025 | DT_NOTIFIC | data | 0.0% |

**data_sintomas**

| ano | coluna | tipo | % nulos |
|---|---|---|---|
| 2013 | dt_diagnostico_sintoma | data | 0.0% |
| 2014 | dt_diagnostico_sintoma | data | 0.0% |
| 2015 | dt_diagnostico_sintoma | data | 0.1% |
| 2016 | dt_diagnostico_sintoma | data | 0.0% |
| 2017 | dt_diagnostico_sintoma | data | 0.0% |
| 2018 | dt_diagnostico_sintoma | data | 0.0% |
| 2019 | dt_diagnostico_sintoma | data | 0.1% |
| 2020 | dt_diagnostico_sintoma | data | 0.0% |
| 2021 | DT_SIN_PRI | data | 0.0% |
| 2022 | DT_SIN_PRI | data | 1.0% |
| 2023 | dt_sin_pri | data | 0.0% |
| 2024 | DT_SIN_PRI | data | 0.0% |
| 2025 | DT_SIN_PRI | data | 0.0% |

**bairro_residencia**

| ano | coluna | tipo | % nulos |
|---|---|---|---|
| 2013 | no_bairro_residencia | texto | 0.0% |
| 2014 | no_bairro_residencia | texto | 0.0% |
| 2015 | no_bairro_residencia | texto | 0.8% |
| 2016 | no_bairro_residencia | texto | 1.8% |
| 2017 | no_bairro_residencia | texto | 0.0% |
| 2018 | no_bairro_residencia | texto | 0.3% |
| 2019 | no_bairro_residencia | texto | 1.1% |
| 2020 | no_bairro_residencia | texto | 0.3% |
| 2021 | NM_BAIRRO | texto | 0.0% |
| 2022 | NM_BAIRRO | texto | 1.0% |
| 2023 | nm_bairro | texto | 0.0% |
| 2024 | NM_BAIRRO | texto | 0.0% |
| 2025 | NM_BAIRRO | texto | 0.2% |

**agravo**

| ano | coluna | tipo | % nulos |
|---|---|---|---|
| 2013 | co_cid | texto | 0.0% |
| 2014 | co_cid | texto | 0.0% |
| 2015 | co_cid | texto | 0.1% |
| 2016 | co_cid | texto | 0.0% |
| 2017 | co_cid | texto | 0.0% |
| 2018 | co_cid | texto | 0.0% |
| 2019 | co_cid | texto | 0.1% |
| 2020 | co_cid | texto | 0.0% |
| 2021 | ID_AGRAVO | texto | 0.0% |
| 2022 | ID_AGRAVO | texto | 1.0% |
| 2023 | id_agravo | texto | 0.0% |
| 2024 | ID_AGRAVO | texto | 0.0% |
| 2025 | ID_AGRAVO | texto | 0.0% |

**classificacao_final**

| ano | coluna | tipo | % nulos |
|---|---|---|---|
| 2013 | tp_classificacao_final | numérico | 0.0% |
| 2014 | tp_classificacao_final | numérico | 0.0% |
| 2015 | tp_classificacao_final | numérico | 0.2% |
| 2016 | tp_classificacao_final | numérico | 0.1% |
| 2017 | tp_classificacao_final | numérico | 0.0% |
| 2018 | tp_classificacao_final | numérico | 0.0% |
| 2019 | tp_classificacao_final | numérico | 0.1% |
| 2020 | tp_classificacao_final | numérico | 0.0% |
| 2021 | CLASSI_FIN | numérico | 0.0% |
| 2022 | CLASSI_FIN | numérico | 1.0% |
| 2023 | classi_fin | numérico | 0.0% |
| 2024 | CLASSI_FIN | numérico | 0.0% |
| 2025 | CLASSI_FIN | numérico | 2.8% |

**criterio**

| ano | coluna | tipo | % nulos |
|---|---|---|---|
| 2013 | tp_criterio_confirmacao | numérico | 0.0% |
| 2014 | tp_criterio_confirmacao | numérico | 0.0% |
| 2015 | tp_criterio_confirmacao | numérico | 8.8% |
| 2016 | tp_criterio_confirmacao | numérico | 8.0% |
| 2017 | tp_criterio_confirmacao | numérico | 0.2% |
| 2018 | tp_criterio_confirmacao | numérico | 0.4% |
| 2019 | tp_criterio_confirmacao | numérico | 8.0% |
| 2020 | tp_criterio_confirmacao | numérico | 3.5% |
| 2021 | CRITERIO | numérico | 0.0% |
| 2022 | CRITERIO | numérico | 1.1% |
| 2023 | criterio | numérico | 2.2% |
| 2024 | CRITERIO | numérico | 0.0% |
| 2025 | CRITERIO | numérico | 5.9% |

**evolucao**

| ano | coluna | tipo | % nulos |
|---|---|---|---|
| 2013 | tp_evolucao_caso | numérico | 0.5% |
| 2014 | tp_evolucao_caso | numérico | 1.8% |
| 2015 | tp_evolucao_caso | numérico | 12.2% |
| 2016 | tp_evolucao_caso | numérico | 14.0% |
| 2017 | tp_evolucao_caso | numérico | 0.3% |
| 2018 | tp_evolucao_caso | numérico | 1.0% |
| 2019 | tp_evolucao_caso | numérico | 9.6% |
| 2020 | tp_evolucao_caso | numérico | 4.8% |
| 2021 | EVOLUCAO | numérico | 0.0% |
| 2022 | EVOLUCAO | numérico | 1.1% |
| 2023 | evolucao | numérico | 2.0% |
| 2024 | EVOLUCAO | numérico | 0.0% |
| 2025 | EVOLUCAO | numérico | 9.9% |

### % de nulos de todas as colunas (nomes em minúsculas; só colunas com ≥ 1% de nulos em algum ano)

| coluna | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| acido_pept | nan | nan | 93.8 | 32.2 | 0.0 | 0.1 | 2.1 | 0.3 | 0.0 | 1.1 | 0.4 | 0.0 | 1.3 |
| alrm_abdom | nan | nan | 100.0 | 99.9 | 99.9 | 99.0 | 97.8 | 99.3 | 99.6 | 97.3 | 98.4 | 98.6 | 98.3 |
| alrm_hemat | nan | nan | 100.0 | 99.9 | 99.9 | 99.0 | 97.8 | 99.4 | 99.6 | 97.4 | 98.5 | 98.7 | 98.4 |
| alrm_hepat | nan | nan | 100.0 | 99.9 | 99.9 | 99.0 | 97.8 | 99.4 | 99.6 | 97.5 | 98.5 | 98.7 | 98.4 |
| alrm_hipot | nan | nan | 100.0 | 99.9 | 99.9 | 99.0 | 97.8 | 99.4 | 99.6 | 97.4 | 98.4 | 98.7 | 98.4 |
| alrm_letar | nan | nan | 100.0 | 99.9 | 99.9 | 99.0 | 97.8 | 99.4 | 99.6 | 97.4 | 98.5 | 98.7 | 98.4 |
| alrm_liq | nan | nan | 100.0 | 99.9 | 99.9 | 99.0 | 97.8 | 99.4 | 99.6 | 97.4 | 98.5 | 98.7 | 98.4 |
| alrm_plaq | nan | nan | 100.0 | 99.9 | 99.9 | 99.0 | 97.8 | 99.4 | 99.6 | 97.4 | 98.4 | 98.7 | 98.3 |
| alrm_sang | nan | nan | 100.0 | 99.9 | 99.9 | 99.0 | 97.8 | 99.4 | 99.6 | 97.4 | 98.5 | 98.7 | 98.3 |
| alrm_vom | nan | nan | 100.0 | 99.9 | 99.9 | 99.0 | 97.8 | 99.4 | 99.6 | 97.3 | 98.4 | 98.7 | 98.4 |
| artralgia | nan | nan | 93.8 | 32.2 | 0.0 | 0.1 | 2.1 | 0.3 | 0.0 | 1.1 | 0.4 | 0.0 | 1.3 |
| artrite | nan | nan | 93.8 | 32.2 | 0.0 | 0.1 | 2.1 | 0.3 | 0.0 | 1.1 | 0.4 | 0.0 | 1.3 |
| auto_imune | nan | nan | 93.8 | 32.2 | 0.0 | 0.1 | 2.1 | 0.3 | 0.0 | 1.1 | 0.4 | 0.0 | 1.3 |
| cefaleia | nan | nan | 93.8 | 32.2 | 0.0 | 0.1 | 2.1 | 0.3 | 0.0 | 1.1 | 0.4 | 0.0 | 1.3 |
| classi_fin | nan | nan | nan | nan | nan | nan | nan | nan | 0.0 | 1.0 | 0.0 | 0.0 | 2.8 |
| clinc_chik | nan | nan | 100.0 | 99.0 | 93.0 | 97.0 | 95.4 | 92.8 | 88.4 | 84.0 | 82.3 | 92.2 | 96.3 |
| co_bainf | nan | nan | nan | nan | nan | nan | nan | nan | 88.2 | 88.4 | 97.0 | 98.7 | 97.9 |
| co_bairro_infeccao | 79.1 | 89.5 | 90.4 | 83.3 | 89.2 | 92.0 | 91.0 | 91.2 | nan | nan | nan | nan | nan |
| co_bairro_residencia | 0.0 | 0.0 | 2.1 | 4.7 | 0.0 | 0.5 | 2.4 | 0.3 | nan | nan | nan | nan | nan |
| co_cbo_ocupacao | 96.7 | 94.6 | 97.4 | 98.0 | 97.5 | 95.1 | 92.7 | 93.1 | nan | nan | nan | nan | nan |
| co_distrito_infeccao | 76.8 | 89.3 | 90.4 | 83.0 | 88.6 | 90.0 | 88.8 | 91.5 | nan | nan | nan | nan | nan |
| co_distrito_residencia | 0.0 | 0.3 | 12.5 | 18.8 | 0.0 | 0.5 | 13.7 | 0.1 | nan | nan | nan | nan | nan |
| co_geo_campo_1 | 100.0 | 100.0 | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan |
| co_geo_campo_2 | 100.0 | 100.0 | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan |
| co_logradouro_residencia | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | nan | nan | nan | nan | nan |
| co_municipio_hospital | 99.1 | 98.3 | 98.4 | 98.4 | 100.0 | 93.0 | 94.1 | 97.3 | nan | nan | nan | nan | nan |
| co_municipio_infeccao | 75.7 | 87.2 | 78.5 | 74.4 | 87.2 | 86.0 | 86.4 | 88.5 | nan | nan | nan | nan | nan |
| co_pais_infeccao | 75.7 | 87.2 | 78.0 | 74.3 | 86.8 | 85.7 | 86.2 | 88.2 | nan | nan | nan | nan | nan |
| co_uf_hospital | 99.1 | 98.3 | 98.3 | 98.3 | 96.5 | 92.8 | 93.9 | 97.3 | nan | nan | nan | nan | nan |
| co_uf_infeccao | 75.7 | 87.2 | 78.0 | 74.3 | 86.8 | 85.7 | 86.2 | 88.2 | nan | nan | nan | nan | nan |
| co_unidade_hospital | 99.4 | 98.5 | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan |
| codisinf | nan | nan | nan | nan | nan | nan | nan | nan | 87.2 | 88.0 | 95.7 | 98.8 | 99.4 |
| complica | nan | nan | 100.0 | 100.0 | nan | nan | 100.0 | nan | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| comuninf | nan | nan | nan | nan | nan | nan | nan | nan | 80.5 | 83.6 | 93.4 | 98.1 | 96.5 |
| con_fhd | nan | nan | 100.0 | 100.0 | nan | 100.0 | nan | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| conf_fhd | nan | nan | nan | nan | nan | nan | 100.0 | nan | nan | nan | nan | nan | nan |
| conjuntvit | nan | nan | nan | nan | nan | nan | nan | nan | 0.0 | 1.1 | 0.4 | 0.0 | 1.3 |
| conjutivite | nan | nan | 93.8 | 32.2 | 0.0 | 0.1 | 2.1 | 0.3 | nan | nan | nan | nan | nan |
| copaisinf | nan | nan | nan | nan | nan | nan | nan | nan | 80.2 | 83.5 | 93.3 | 98.1 | 96.5 |
| coufinf | nan | nan | nan | nan | nan | nan | nan | nan | 80.2 | 83.5 | 93.3 | 98.1 | 96.5 |
| criterio | nan | nan | nan | nan | nan | nan | nan | nan | 0.0 | 1.1 | 2.2 | 0.0 | 5.9 |
| cs_escol_n | nan | nan | nan | nan | nan | nan | nan | nan | 15.8 | 16.1 | 18.8 | 18.6 | 18.6 |
| cs_gestant | nan | nan | nan | nan | nan | nan | nan | nan | 0.1 | 1.0 | 0.0 | 0.0 | 0.1 |
| cs_raca | nan | nan | nan | nan | nan | nan | nan | nan | 0.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| cs_sexo | nan | nan | nan | nan | nan | nan | nan | nan | 0.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| cs_zona | nan | nan | nan | nan | nan | nan | nan | nan | 5.2 | 1.0 | nan | nan | nan |
| ddd_hosp | nan | nan | nan | nan | nan | nan | nan | nan | nan | 97.3 | 97.4 | 98.3 | 95.8 |
| ddd_hospital | nan | nan | nan | nan | nan | 97.2 | nan | nan | nan | nan | nan | nan | nan |
| diabetes | nan | nan | 93.8 | 32.2 | 0.0 | 0.1 | 2.1 | 0.3 | 0.0 | 1.1 | 0.4 | 0.0 | 1.3 |
| doenca_tra | nan | nan | nan | nan | nan | nan | nan | nan | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| dor_costas | nan | nan | 93.8 | 32.2 | 0.0 | 0.1 | 2.1 | 0.3 | 0.0 | 1.1 | 0.4 | 0.0 | 1.3 |
| dor_retro | nan | nan | 93.8 | 32.2 | 0.0 | 0.1 | 2.1 | 0.3 | 0.0 | 1.1 | 0.4 | 0.0 | 1.3 |
| ds_identificador_registro | 100.0 | 100.0 | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan |
| ds_obs | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | 100.0 | 74.4 | 72.5 |
| ds_referencia_residencia | 90.6 | 93.4 | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan |
| dt_alrm | nan | nan | 100.0 | 99.9 | 99.9 | 99.0 | 97.9 | 99.4 | 99.6 | 97.6 | 98.7 | 98.7 | 98.4 |
| dt_chik_s1 | nan | nan | nan | nan | nan | nan | nan | nan | 98.7 | 98.2 | 99.1 | 99.4 | 99.6 |
| dt_chik_s2 | nan | nan | nan | nan | nan | nan | nan | nan | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| dt_chil_s1 | nan | nan | 100.0 | 99.8 | 99.2 | 98.8 | 99.2 | 98.1 | nan | nan | nan | nan | nan |
| dt_chil_s2 | nan | nan | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | nan | nan | nan | nan | nan |
| dt_coleta_exame | 84.9 | 79.1 | 92.7 | 96.3 | 94.7 | 88.4 | 88.0 | 92.7 | nan | nan | nan | nan | nan |
| dt_coleta_isolamento | 99.6 | 99.6 | 99.5 | 99.8 | 99.8 | 99.8 | 99.4 | 99.5 | nan | nan | nan | nan | nan |
| dt_coleta_ns1 | 99.8 | 99.6 | 99.7 | 99.9 | 99.9 | 99.1 | 98.6 | 99.7 | nan | nan | nan | nan | nan |
| dt_coleta_rtpcr | 99.7 | 98.8 | 99.8 | 99.7 | 99.2 | 99.5 | 98.7 | 99.5 | nan | nan | nan | nan | nan |
| dt_encerra | nan | nan | nan | nan | nan | nan | nan | nan | 0.0 | 1.0 | 0.3 | 0.0 | 8.1 |
| dt_encerramento | 0.0 | 0.0 | 0.8 | 2.1 | 0.0 | 0.0 | 0.1 | 1.0 | nan | nan | nan | nan | nan |
| dt_grav | nan | nan | 100.0 | 100.0 | nan | nan | 99.8 | 100.0 | 99.9 | 99.8 | 99.9 | 99.9 | 99.9 |
| dt_interna | nan | nan | nan | nan | nan | nan | nan | nan | 97.5 | 93.2 | 95.1 | 96.7 | 93.3 |
| dt_internacao | 99.1 | 98.3 | 98.4 | 98.4 | 96.7 | 92.9 | 94.1 | 97.4 | nan | nan | nan | nan | nan |
| dt_invest | nan | nan | nan | nan | nan | nan | nan | nan | 0.0 | 1.1 | 0.4 | 0.0 | 1.3 |
| dt_investigacao | 0.0 | 0.0 | 3.7 | 3.6 | 0.0 | 0.1 | 2.1 | 0.3 | nan | nan | nan | nan | nan |
| dt_nasc | nan | nan | nan | nan | nan | nan | nan | nan | 4.2 | 1.9 | 0.8 | 1.0 | 0.7 |
| dt_nascimento | 9.7 | 6.3 | 1.7 | 3.5 | 1.0 | 2.0 | 3.0 | 1.5 | nan | nan | nan | nan | nan |
| dt_notific | nan | nan | nan | nan | nan | nan | nan | nan | 0.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| dt_ns1 | nan | nan | nan | nan | nan | nan | nan | nan | 99.4 | 97.7 | 98.8 | 96.7 | 85.4 |
| dt_obito | 99.4 | 99.8 | 99.9 | 99.4 | 99.5 | 99.6 | 99.6 | 99.8 | 99.9 | 99.7 | 99.7 | 99.8 | 99.7 |
| dt_pcr | nan | nan | nan | nan | nan | nan | nan | nan | 99.0 | 96.8 | 98.9 | 97.8 | 82.8 |
| dt_prnt | nan | nan | 100.0 | 100.0 | 99.8 | 99.8 | 99.9 | 99.8 | 100.0 | 99.9 | 100.0 | 100.0 | 99.8 |
| dt_sin_pri | nan | nan | nan | nan | nan | nan | nan | nan | 0.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| dt_soro | nan | nan | nan | nan | nan | nan | nan | nan | 92.5 | 86.2 | 91.7 | 94.3 | 92.8 |
| dt_transf_dm | 51.3 | 52.8 | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan |
| dt_transf_rm | 100.0 | 100.0 | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan |
| dt_transf_rs | 100.0 | 100.0 | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan |
| dt_transf_se | 100.0 | 100.0 | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan |
| dt_transf_us | 100.0 | 100.0 | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan |
| dt_viral | nan | nan | nan | nan | nan | nan | nan | nan | 99.9 | 99.2 | 99.9 | 99.9 | 99.8 |
| epistaxe | nan | nan | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| evidencia | nan | nan | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| evolucao | nan | nan | nan | nan | nan | nan | nan | nan | 0.0 | 1.1 | 2.0 | 0.0 | 9.9 |
| exantema | nan | nan | 93.8 | 32.2 | 0.0 | 0.1 | 2.1 | 0.3 | 0.0 | 1.1 | 0.4 | 0.0 | 1.3 |
| febre | nan | nan | 93.8 | 32.2 | 0.0 | 0.1 | 2.1 | 0.3 | 0.0 | 1.1 | 0.4 | 0.0 | 1.3 |
| gengivo | nan | nan | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| grav_ast | nan | nan | 100.0 | 100.0 | nan | nan | 99.8 | 100.0 | 99.9 | 99.7 | 99.9 | 99.9 | 99.9 |
| grav_consc | nan | nan | 100.0 | 100.0 | nan | nan | 99.8 | 100.0 | 99.9 | 99.7 | 99.9 | 99.9 | 99.9 |
| grav_conv | nan | nan | 100.0 | 100.0 | nan | nan | 99.8 | 100.0 | 99.9 | 99.7 | 99.9 | 99.9 | 99.9 |
| grav_ench | nan | nan | 100.0 | 100.0 | nan | nan | 99.8 | 100.0 | 99.9 | 99.7 | 99.9 | 99.9 | 99.9 |
| grav_extre | nan | nan | 100.0 | 100.0 | nan | nan | 99.8 | 100.0 | 99.9 | 99.7 | 99.9 | 99.9 | 99.9 |
| grav_hemat | nan | nan | 100.0 | 100.0 | nan | nan | 99.8 | 100.0 | 99.9 | 99.7 | 99.9 | 99.9 | 99.9 |
| grav_hipot | nan | nan | 100.0 | 100.0 | nan | nan | 99.8 | 100.0 | 99.9 | 99.7 | 99.9 | 99.9 | 99.9 |
| grav_insuf | nan | nan | 100.0 | 100.0 | nan | nan | 99.8 | 100.0 | 99.9 | 99.7 | 99.9 | 99.9 | 99.9 |
| grav_melen | nan | nan | 100.0 | 100.0 | nan | nan | 99.8 | 100.0 | 99.9 | 99.7 | 99.9 | 99.9 | 99.9 |
| grav_metro | nan | nan | 100.0 | 100.0 | nan | nan | 99.8 | 100.0 | 99.9 | 99.7 | 99.9 | 99.9 | 99.9 |
| grav_mioc | nan | nan | 100.0 | 100.0 | nan | nan | 99.8 | 100.0 | 99.9 | 99.7 | 99.9 | 99.9 | 99.9 |
| grav_orgao | nan | nan | 100.0 | 100.0 | nan | nan | 99.8 | 100.0 | 99.9 | 99.7 | 99.9 | 99.9 | 99.9 |
| grav_pulso | nan | nan | 100.0 | 100.0 | nan | nan | 99.8 | 100.0 | 99.9 | 99.7 | 99.9 | 99.9 | 99.9 |
| grav_sang | nan | nan | 100.0 | 100.0 | nan | nan | 99.8 | 100.0 | 99.9 | 99.7 | 99.9 | 99.9 | 99.9 |
| grav_taqui | nan | nan | 100.0 | 100.0 | nan | nan | 99.8 | 100.0 | 99.9 | 99.7 | 99.9 | 99.9 | 99.9 |
| hematolog | nan | nan | 93.8 | 32.2 | 0.0 | 0.1 | 2.1 | 0.3 | 0.0 | 1.1 | 0.4 | 0.0 | 1.3 |
| hematura | nan | nan | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| hepatopat | nan | nan | 93.8 | 32.2 | 0.0 | 0.1 | 2.1 | 0.3 | 0.0 | 1.1 | 0.4 | 0.0 | 1.3 |
| hipertensa | nan | nan | nan | nan | nan | nan | nan | nan | 0.0 | 1.1 | 0.4 | 0.0 | 1.3 |
| hipertensao | nan | nan | 93.8 | 32.2 | 0.0 | 0.1 | 2.1 | 0.3 | nan | nan | nan | nan | nan |
| histopa_n | nan | nan | nan | nan | nan | nan | nan | nan | 81.5 | 88.3 | 86.3 | 89.0 | 90.6 |
| hospital | nan | nan | nan | nan | nan | 93.4 | nan | nan | nan | 93.3 | 95.3 | 96.7 | 93.5 |
| hospitaliz | nan | nan | nan | nan | nan | nan | nan | nan | 39.7 | 36.0 | 34.7 | 47.3 | 40.2 |
| id_agravo | nan | nan | nan | nan | nan | nan | nan | nan | 0.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| id_bairro | nan | nan | nan | nan | nan | nan | nan | nan | 0.0 | 1.1 | 0.2 | 0.0 | 0.6 |
| id_distrit | nan | nan | nan | nan | nan | nan | nan | nan | 0.0 | 1.1 | 0.1 | 0.0 | 2.2 |
| id_logrado | nan | nan | nan | nan | nan | nan | nan | nan | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| id_mn_resi | nan | nan | nan | nan | nan | nan | nan | nan | 0.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| id_municip | nan | nan | nan | nan | nan | nan | nan | nan | 0.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| id_ocupa_n | nan | nan | nan | nan | nan | nan | nan | nan | 88.8 | 93.7 | 94.5 | 93.7 | 95.1 |
| id_pais | nan | nan | nan | nan | nan | nan | nan | nan | 0.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| id_regiona | nan | nan | nan | nan | nan | nan | nan | nan | 0.0 | 1.1 | 0.2 | 0.1 | 0.0 |
| id_rg_resi | nan | nan | nan | nan | nan | nan | nan | nan | 0.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| id_unidade | nan | nan | nan | nan | nan | nan | nan | nan | 0.0 | 1.1 | 0.0 | 0.0 | 0.0 |
| imunoh_n | nan | nan | nan | nan | nan | nan | nan | nan | 81.0 | 87.5 | 85.6 | 88.8 | 90.6 |
| laco | nan | nan | 93.8 | 32.2 | 0.0 | 0.1 | 2.1 | 0.3 | 0.0 | 1.1 | 0.4 | 0.0 | 1.3 |
| laco_n | nan | nan | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| leucopenia | nan | nan | 93.8 | 32.2 | 0.0 | 0.1 | 2.1 | 0.3 | 0.0 | 1.1 | 0.4 | 0.0 | 1.3 |
| mani_hemor | nan | nan | 100.0 | 100.0 | nan | nan | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| metro | nan | nan | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| mialgia | nan | nan | 93.8 | 32.2 | 0.0 | 0.1 | 2.1 | 0.3 | 0.0 | 1.1 | 0.4 | 0.0 | 1.3 |
| municipio | nan | nan | nan | nan | nan | nan | nan | nan | nan | 93.3 | 95.1 | 96.7 | 93.4 |
| nausea | nan | nan | 93.8 | 32.2 | 0.0 | 0.1 | 2.1 | 0.3 | 0.0 | 1.1 | 0.4 | 0.0 | 1.3 |
| nm_bairro | nan | nan | nan | nan | nan | nan | nan | nan | 0.0 | 1.0 | 0.0 | 0.0 | 0.2 |
| nm_logrado | nan | nan | nan | nan | nan | nan | nan | nan | 1.7 | 2.5 | 1.5 | 0.2 | 0.4 |
| no_bairro_infeccao | 100.0 | 100.0 | 90.2 | 83.2 | 89.2 | 92.0 | 90.8 | 91.1 | nan | nan | nan | nan | nan |
| no_bairro_residencia | 0.0 | 0.0 | 0.8 | 1.8 | 0.0 | 0.3 | 1.1 | 0.3 | nan | nan | nan | nan | nan |
| nobaiinf | nan | nan | nan | nan | nan | nan | nan | nan | 88.1 | 88.3 | 96.9 | 98.7 | 97.8 |
| nome_logradouro_residencia | 0.4 | 0.7 | 2.2 | 2.2 | 1.1 | 1.6 | 2.0 | 1.8 | nan | nan | nan | nan | nan |
| nu_ano | nan | nan | nan | nan | nan | nan | nan | nan | 0.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| nu_cep | nan | nan | nan | nan | nan | nan | nan | nan | 74.1 | 55.8 | 39.1 | 49.5 | 39.9 |
| nu_cep_residencia | 75.5 | 74.9 | 80.6 | 78.1 | 60.9 | 63.2 | 63.6 | 71.3 | nan | nan | nan | nan | nan |
| nu_ddd_hospital | 99.9 | 100.0 | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan |
| nu_idade_n | nan | nan | nan | nan | nan | nan | nan | nan | 0.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| nu_lote_horizontal | 100.0 | 100.0 | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan |
| nu_lote_i | nan | nan | nan | nan | nan | nan | nan | nan | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| petequia_n | nan | nan | 93.8 | 32.2 | 0.0 | 0.1 | 2.1 | 0.3 | 0.0 | 1.1 | 0.4 | 0.0 | 1.3 |
| petequias | nan | nan | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| plaq_menor | nan | nan | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| plasmatico | nan | nan | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| renal | nan | nan | 93.8 | 32.2 | 0.0 | 0.1 | 2.1 | 0.3 | 0.0 | 1.1 | 0.4 | 0.0 | 1.3 |
| res_chiks1 | nan | nan | 100.0 | 99.3 | 96.9 | 95.6 | 98.6 | 96.9 | 93.6 | 95.6 | 95.9 | 97.7 | 98.0 |
| res_chiks2 | nan | nan | 100.0 | 99.6 | 97.8 | 96.7 | 99.2 | 97.2 | 94.0 | 97.3 | 96.1 | 97.8 | 98.0 |
| resul_ns1 | nan | nan | nan | nan | nan | nan | nan | nan | 78.5 | 85.3 | 82.1 | 85.1 | 76.7 |
| resul_pcr_ | nan | nan | nan | nan | nan | nan | nan | nan | 74.5 | 80.7 | 77.8 | 85.0 | 76.9 |
| resul_prnt | nan | nan | 100.0 | 99.6 | 97.8 | 96.6 | 99.3 | 97.3 | 94.0 | 97.1 | 95.8 | 97.8 | 98.1 |
| resul_soro | nan | nan | nan | nan | nan | nan | nan | nan | 74.9 | 68.8 | 76.2 | 84.1 | 83.8 |
| resul_vi_n | nan | nan | nan | nan | nan | nan | nan | nan | 73.5 | 82.8 | 78.8 | 86.0 | 87.2 |
| sangram | nan | nan | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| sem_not | nan | nan | nan | nan | nan | nan | nan | nan | 0.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| sem_pri | nan | nan | nan | nan | nan | nan | nan | nan | 0.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| sg_uf | nan | nan | nan | nan | nan | nan | nan | nan | 0.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| sg_uf_not | nan | nan | nan | nan | nan | nan | nan | nan | 0.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| sorotipo | nan | nan | nan | nan | nan | nan | nan | nan | 99.9 | 100.0 | 100.0 | 99.9 | 96.1 |
| st_doenca_trabalho | 64.0 | 71.5 | 61.5 | 85.0 | 100.0 | 100.0 | 100.0 | 100.0 | nan | nan | nan | nan | nan |
| st_fluxo_retorno_recebido | 100.0 | 100.0 | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan |
| st_importado | 100.0 | 100.0 | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan |
| st_ocorreu_hospitalizacao | 18.6 | 19.5 | 59.7 | 58.6 | 52.4 | 38.5 | 35.5 | 41.6 | nan | nan | nan | nan | nan |
| tel_hosp | nan | nan | nan | nan | nan | nan | nan | nan | nan | 97.3 | 97.4 | 98.3 | 95.8 |
| tel_hospital | nan | nan | nan | nan | nan | 97.2 | nan | nan | nan | nan | nan | nan | nan |
| tp_autoctone_residencia | 61.3 | 71.2 | 69.6 | 69.7 | 78.9 | 80.9 | 76.3 | 78.5 | nan | nan | nan | nan | nan |
| tp_criterio_confirmacao | 0.0 | 0.0 | 8.8 | 8.0 | 0.2 | 0.4 | 8.0 | 3.5 | nan | nan | nan | nan | nan |
| tp_duplicidade | 96.8 | 96.2 | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan |
| tp_escolaridade | 10.0 | 11.1 | 33.5 | 29.0 | 6.5 | 9.6 | 12.0 | 17.5 | nan | nan | nan | nan | nan |
| tp_evolucao_caso | 0.5 | 1.8 | 12.2 | 14.0 | 0.3 | 1.0 | 9.6 | 4.8 | nan | nan | nan | nan | nan |
| tp_fluxo_retorno | 100.0 | 100.0 | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan | nan |
| tp_not | nan | nan | nan | nan | nan | nan | nan | nan | 0.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| tp_raca_cor | 4.8 | 2.5 | 24.2 | 8.1 | 0.0 | 0.0 | 0.1 | 0.0 | nan | nan | nan | nan | nan |
| tp_result_exame | 2.6 | 7.6 | 39.1 | 69.8 | 79.3 | 59.6 | 62.0 | 70.1 | nan | nan | nan | nan | nan |
| tp_result_histopatologia | 33.2 | 39.8 | 63.0 | 78.8 | 85.0 | 75.5 | 77.2 | 78.4 | nan | nan | nan | nan | nan |
| tp_result_imunohistoquimica | 32.3 | 37.9 | 63.1 | 78.6 | 84.7 | 75.2 | 77.1 | 77.9 | nan | nan | nan | nan | nan |
| tp_result_isolamento | 32.3 | 36.0 | 52.7 | 74.3 | 79.7 | 65.4 | 65.7 | 70.1 | nan | nan | nan | nan | nan |
| tp_result_ns1 | 32.5 | 31.5 | 53.2 | 75.9 | 83.1 | 68.6 | 67.4 | 73.9 | nan | nan | nan | nan | nan |
| tp_result_rtpcr | 32.0 | 37.9 | 56.2 | 74.5 | 79.5 | 66.1 | 70.4 | 73.1 | nan | nan | nan | nan | nan |
| tp_sorotipo | 99.9 | 99.7 | 100.0 | 100.0 | 100.0 | 99.9 | 99.7 | 100.0 | nan | nan | nan | nan | nan |
| tp_zona_residencia | 1.5 | 2.7 | 9.1 | 14.3 | 5.8 | 100.0 | 4.5 | 3.0 | nan | nan | nan | nan | nan |
| tpautocto | nan | nan | nan | nan | nan | nan | nan | nan | 69.5 | 75.2 | 80.5 | 94.7 | 82.5 |
| uf | nan | nan | nan | nan | nan | nan | nan | nan | 97.5 | 92.9 | 95.1 | 96.6 | 93.3 |
| vomito | nan | nan | 93.8 | 32.2 | 0.0 | 0.1 | 2.1 | 0.3 | 0.0 | 1.1 | 0.4 | 0.0 | 1.3 |

## 5. Intervalo de datas

| ano_arquivo | campo | coluna | mínimo | máximo | datas não reconhecidas |
|---|---|---|---|---|---|
| 2013 | data_notificacao | dt_notificacao | 2013-01-03 | 2013-12-31 | 0 |
| 2013 | data_sintomas | dt_diagnostico_sintoma | 2013-01-01 | 2013-12-28 | 0 |
| 2014 | data_notificacao | dt_notificacao | 2014-01-01 | 2014-07-28 | 0 |
| 2014 | data_sintomas | dt_diagnostico_sintoma | 2013-02-25 | 2014-07-28 | 0 |
| 2015 | data_notificacao | dt_notificacao | 2015-01-04 | 2018-03-14 | 0 |
| 2015 | data_sintomas | dt_diagnostico_sintoma | 2015-01-04 | 2016-01-02 | 0 |
| 2016 | data_notificacao | dt_notificacao | 2016-01-03 | 2018-04-16 | 0 |
| 2016 | data_sintomas | dt_diagnostico_sintoma | 2016-01-03 | 2016-12-31 | 0 |
| 2017 | data_notificacao | dt_notificacao | 2017-01-02 | 2019-07-23 | 0 |
| 2017 | data_sintomas | dt_diagnostico_sintoma | 2017-01-01 | 2017-12-30 | 0 |
| 2018 | data_notificacao | dt_notificacao | 2018-01-02 | 2020-02-04 | 0 |
| 2018 | data_sintomas | dt_diagnostico_sintoma | 2017-12-31 | 2018-12-29 | 0 |
| 2019 | data_notificacao | dt_notificacao | 2019-01-02 | 2020-02-06 | 0 |
| 2019 | data_sintomas | dt_diagnostico_sintoma | 2018-12-30 | 2019-12-28 | 0 |
| 2020 | data_notificacao | dt_notificacao | 2020-01-01 | 2020-12-30 | 0 |
| 2020 | data_sintomas | dt_diagnostico_sintoma | 2019-12-29 | 2020-12-29 | 0 |
| 2021 | data_notificacao | DT_NOTIFIC | 2021-01-01 | 2021-12-31 | 0 |
| 2021 | data_sintomas | DT_SIN_PRI | 2016-07-20 | 2021-12-30 | 0 |
| 2022 | data_notificacao | DT_NOTIFIC | 2022-01-03 | 2022-12-31 | 0 |
| 2022 | data_sintomas | DT_SIN_PRI | 2020-07-17 | 2022-12-29 | 0 |
| 2023 | data_notificacao | dt_notific | 2023-01-01 | 2023-12-30 | 0 |
| 2023 | data_sintomas | dt_sin_pri | 1970-12-06 | 2023-12-28 | 0 |
| 2024 | data_notificacao | DT_NOTIFIC | 2024-01-02 | 2024-12-31 | 0 |
| 2024 | data_sintomas | DT_SIN_PRI | 1990-08-21 | 2024-12-29 | 0 |
| 2025 | data_notificacao | DT_NOTIFIC | 2025-01-01 | 2025-12-31 | 0 |
| 2025 | data_sintomas | DT_SIN_PRI | 1950-01-11 | 2025-12-31 | 0 |

## 6. Bairros (residência)

- Valores distintos (texto bruto): **168**
- Valores distintos após `strip` + maiúsculas: **165**
- Nulos: 0.7%

### 20 nomes mais frequentes

| bairro | registros |
|---|---|
| COHAB | 6817 |
| IBURA | 5730 |
| VARZEA | 4963 |
| IPUTINGA | 4107 |
| BOA VIAGEM | 4080 |
| IMBIRIBEIRA | 3800 |
| AGUA FRIA | 3418 |
| NOVA DESCOBERTA | 3359 |
| AFOGADOS | 2935 |
| CAMPO GRANDE | 2783 |
| CASA AMARELA | 2503 |
| VASCO DA GAMA | 2502 |
| AREIAS | 2433 |
| SANTO AMARO | 2432 |
| CORDEIRO | 2364 |
| DOIS UNIDOS | 2362 |
| TORROES | 2297 |
| JARDIM SAO PAULO | 2273 |
| PINA | 1967 |
| JORDAO | 1796 |

### Nomes distintos por ano

| ano | nomes distintos |
|---|---|
| 2013 | 92 |
| 2014 | 88 |
| 2015 | 125 |
| 2016 | 100 |
| 2017 | 91 |
| 2018 | 94 |
| 2019 | 108 |
| 2020 | 92 |
| 2021 | 93 |
| 2022 | 92 |
| 2023 | 92 |
| 2024 | 93 |
| 2025 | 112 |

### Comparação com a Tabela de Bairros do portal (95 localidades)

Nomes que **não** aparecem na tabela: 71 distintos, 86 registros (0.1% dos não nulos). Os 25 mais frequentes:

| nome | registros |
|---|---|
| CENTRO | 5 |
| GRAAS | 4 |
| ZONA RURAL | 3 |
| BOLA NA REDE | 2 |
| MORRO DA CONCEIO | 2 |
| AREAIS | 2 |
| BREJO | 2 |
| ALTO SANTA ISABEL | 2 |
| ALTO DA BONDADE | 2 |
| TAMA | 1 |
| PONRO DE PARADA | 1 |
| CAMPO | 1 |
| EST | 1 |
| IMB | 1 |
| VASIO  DAGAMA | 1 |
| TEJIPI | 1 |
| INBIRIBEIRA | 1 |
| JOANA  BEZERRA | 1 |
| SO JOSE | 1 |
| MANGUE | 1 |
| MUSTADINHA | 1 |
| COQUEIRO | 1 |
| CHO DE ESTRELA | 1 |
| MANGUEIRA - BAIRRO | 1 |
| VILA TAMANDARE | 1 |

## 7. Valores distintos das colunas categóricas (contagem por ano)

### agravo

| valor | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| <nulo> | 0 | 0 | 46 | 0 | 0 | 0 | 6 | 0 | 0 | 30 | 0 | 0 | 0 |
| A90 | 3229 | 1192 | 34510 | 18612 | 2454 | 2687 | 7302 | 3540 | 10898 | 2876 | 3523 | 10548 | 9187 |

### classificacao_final

| valor | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1279 | 374 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 1.0 | 0 | 0 | 352 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 10 | 0 | 0 | 0 | 12117 | 959 | 1188 | 3968 | 1485 | 7367 | 1313 | 0 | 2579 | 5002 |
| 10.0 | 0 | 0 | 23088 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1406 | 0 | 0 |
| 11 | 0 | 0 | 0 | 28 | 3 | 18 | 121 | 11 | 24 | 36 | 0 | 28 | 99 |
| 11.0 | 0 | 0 | 15 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 23 | 0 | 0 |
| 12 | 0 | 0 | 0 | 2 | 0 | 1 | 8 | 1 | 6 | 4 | 0 | 0 | 9 |
| 12.0 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| 2 | 13 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2.0 | 0 | 0 | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 3 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 5 | 1936 | 818 | 0 | 4910 | 1488 | 1468 | 2603 | 1920 | 3500 | 1522 | 0 | 7941 | 3533 |
| 5.0 | 0 | 0 | 7870 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2009 | 0 | 0 |
| 8 | 0 | 0 | 0 | 1527 | 4 | 12 | 602 | 122 | 1 | 1 | 0 | 0 | 289 |
| 8.0 | 0 | 0 | 3160 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 83 | 0 | 0 |
| <nulo> | 0 | 0 | 54 | 23 | 0 | 0 | 6 | 1 | 0 | 30 | 1 | 0 | 255 |

### criterio

| valor | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 492 | 259 | 0 | 784 | 175 | 366 | 0 | 378 | 1214 | 473 | 0 | 639 | 1958 |
| 1.0 | 0 | 0 | 2661 | 0 | 0 | 0 | 923 | 0 | 0 | 0 | 328 | 0 | 0 |
| 2 | 2737 | 933 | 0 | 15917 | 2275 | 2309 | 0 | 3004 | 9683 | 2402 | 0 | 9908 | 6196 |
| 2.0 | 0 | 0 | 28536 | 0 | 0 | 0 | 5778 | 0 | 0 | 0 | 3106 | 0 | 0 |
| 3 | 0 | 0 | 0 | 422 | 0 | 0 | 0 | 35 | 0 | 0 | 0 | 1 | 492 |
| 3.0 | 0 | 0 | 313 | 0 | 0 | 0 | 19 | 0 | 0 | 0 | 12 | 0 | 0 |
| <nulo> | 0 | 0 | 3046 | 1489 | 4 | 12 | 588 | 123 | 1 | 31 | 77 | 0 | 541 |

### evolucao

| valor | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 3148 | 1087 | 0 | 15082 | 2433 | 2649 | 0 | 3325 | 10870 | 2834 | 0 | 10523 | 7502 |
| 1.0 | 0 | 0 | 29241 | 0 | 0 | 0 | 6485 | 0 | 0 | 0 | 3354 | 0 | 0 |
| 2 | 10 | 0 | 0 | 21 | 2 | 1 | 0 | 0 | 6 | 0 | 0 | 0 | 3 |
| 2.0 | 0 | 0 | 11 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 1 | 0 | 0 |
| 3 | 9 | 2 | 0 | 90 | 11 | 9 | 0 | 8 | 6 | 10 | 0 | 20 | 26 |
| 3.0 | 0 | 0 | 20 | 0 | 0 | 0 | 29 | 0 | 0 | 0 | 9 | 0 | 0 |
| 4 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| 4.0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 |
| 9 | 46 | 81 | 0 | 819 | 0 | 2 | 0 | 38 | 15 | 30 | 0 | 3 | 743 |
| 9.0 | 0 | 0 | 1055 | 0 | 0 | 0 | 86 | 0 | 0 | 0 | 86 | 0 | 0 |
| <nulo> | 16 | 22 | 4228 | 2599 | 8 | 26 | 705 | 169 | 1 | 32 | 71 | 2 | 912 |

## 8. Exemplos (5 linhas, colunas-chave): ano mais antigo e mais recente

**2013**

| dt_notificacao | dt_diagnostico_sintoma | no_bairro_residencia | co_cid | tp_classificacao_final | tp_criterio_confirmacao | tp_evolucao_caso |
|---|---|---|---|---|---|---|
| 2013/01/04 00:00:00 | 2013/01/01 00:00:00 | SAO JOSE | A90 | 5 | 1 | 1 |
| 2013/01/07 00:00:00 | 2013/01/01 00:00:00 | BOA VIAGEM | A90 | 5 | 2 | 1 |
| 2013/02/20 00:00:00 | 2013/01/01 00:00:00 | COHAB | A90 | 5 | 2 | 1 |
| 2013/01/03 00:00:00 | 2013/01/02 00:00:00 | ENCRUZILHADA | A90 | 5 | 2 | 1 |
| 2013/01/07 00:00:00 | 2013/01/02 00:00:00 | CASA AMARELA | A90 | 5 | 2 | 1 |

**2025**

| DT_NOTIFIC | DT_SIN_PRI | NM_BAIRRO | ID_AGRAVO | CLASSI_FIN | CRITERIO | EVOLUCAO |
|---|---|---|---|---|---|---|
| 04/03/2025 | 02/03/2025 | PINA | A90 | 10 | 2 | 1 |
| 04/03/2025 | 02/03/2025 | JARDIM SAO PAULO | A90 | 5 | 2 | 1 |
| 08/03/2025 | 07/03/2025 | IPSEP | A90 | 10 | 2 | 1 |
| 27/03/2025 | 26/03/2025 | TORRE | A90 | 5 | 2 | 1 |
| 02/03/2025 | 28/02/2025 | JIQUIA | A90 | 5 | 2 | 1 |
