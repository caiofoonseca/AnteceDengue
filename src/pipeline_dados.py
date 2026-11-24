"""Etapas do DAG antecedengue_dados, chamáveis pela linha de comando (python -m src.pipeline_dados <etapa>).

Etapas: ingestao, backup, clima, resumo, validar, publicar. A lógica de download e de montagem do painel continua em
scripts/download_raw.py, scripts/build_panel.py e scripts/build_clima.py; aqui só ficam a decisão de pular
o download, o resumo de cada etapa para o log e a validação de qualidade.

validar falha (código de saída 1) se houver duplicata de (bairro, week_start), semana faltando no painel,
nulos fora do esperado ou PANEL_END incoerente; nesse caso restaura as cópias de segurança de data/processed.
"""
import argparse
import hashlib
import json
import logging
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd

from src import config

log = logging.getLogger("pipeline_dados")

RAW_YEARS = range(2013, 2026)
PROCESSED_FILES = ("panel.csv", "clima_semanal.csv")
BACKUP_SUFFIX = ".bak"
MANIFEST = "manifest.json"
MAX_NULL_TEMP_HUM = 0.06


class ValidationFailed(RuntimeError):
    pass


def raw_files(raw_dir: Path = config.DATA_RAW) -> list[Path]:
    return [raw_dir / f"dengue_{ano}.csv" for ano in RAW_YEARS]


def missing_raw(raw_dir: Path = config.DATA_RAW) -> list[str]:
    return [p.name for p in raw_files(raw_dir) if not p.exists() or p.stat().st_size == 0]


def climate_raw_present(raw_dir: Path = config.DATA_RAW) -> bool:
    clima = raw_dir / "clima"
    return all((clima / nome).exists() for nome in ("infodengue_alertcity_2611606.csv",
                                                    "openmeteo_era5_daily_recife.csv"))


def ingest(refresh: bool, raw_dir: Path = config.DATA_RAW) -> str:
    """Baixa os CSVs anuais do portal, pulando o download se todos já existem (a menos que refresh)."""
    faltando = missing_raw(raw_dir)
    if not faltando and not refresh:
        resumo = f"download pulado: os {len(RAW_YEARS)} CSVs anuais já existem em {raw_dir} (use refresh=true para baixar de novo)"
        log.info(resumo)
        return resumo
    motivo = "refresh=true" if refresh else f"faltam {faltando}"
    log.info("baixando os CSVs do portal (%s); precisa de internet", motivo)
    subprocess.run([sys.executable, str(config.ROOT / "scripts" / "download_raw.py")], check=True, cwd=config.ROOT)
    return f"download feito ({motivo})"


def build_climate(refresh: bool, raw_dir: Path = config.DATA_RAW) -> list[str]:
    """Comando do passo de clima: sem download se os brutos existem e refresh é falso."""
    comando = [sys.executable, str(config.ROOT / "scripts" / "build_clima.py")]
    if climate_raw_present(raw_dir) and not refresh:
        comando.append("--sem-download")
    return comando


def summarize_panel(panel: pd.DataFrame) -> str:
    return (f"painel: {len(panel)} linhas, {panel['bairro'].nunique()} bairros, {panel['week_start'].nunique()} semanas, "
            f"{panel['week_start'].min().date()} a {panel['week_start'].max().date()}, {int(panel['casos'].sum())} casos")


def summarize_climate(clima: pd.DataFrame) -> str:
    return (f"clima: {len(clima)} linhas, {clima['week_start'].min().date()} a {clima['week_start'].max().date()}, "
            f"nulos {clima.drop(columns='week_start').isna().sum().to_dict()}")


def summarize_raw(raw_dir: Path = config.DATA_RAW) -> str:
    existentes = [p for p in raw_files(raw_dir) if p.exists()]
    linhas = sum(max(sum(1 for _ in open(p, "rb")) - 1, 0) for p in existentes)
    return f"brutos: {len(existentes)} de {len(RAW_YEARS)} arquivos anuais, cerca de {linhas} linhas no total"


def read_panel(processed: Path = config.DATA_PROCESSED) -> pd.DataFrame:
    return pd.read_csv(processed / "panel.csv", parse_dates=["week_start"])


def read_climate(processed: Path = config.DATA_PROCESSED) -> pd.DataFrame:
    return pd.read_csv(processed / "clima_semanal.csv", parse_dates=["week_start"])


def validate(panel: pd.DataFrame, clima: pd.DataFrame, panel_end: str = config.PANEL_END) -> list[str]:
    """Devolve a lista de problemas encontrados (vazia se o painel e o clima estão coerentes)."""
    problemas = []
    duplicadas = int(panel.duplicated(["bairro", "week_start"]).sum())
    if duplicadas:
        problemas.append(f"{duplicadas} linhas duplicadas de (bairro, week_start) no painel")
    fim = pd.Timestamp(panel_end)
    if panel["week_start"].max() != fim:
        problemas.append(f"PANEL_END incoerente: última semana do painel é {panel['week_start'].max().date()}, "
                         f"config.PANEL_END é {fim.date()}")
    esperadas = pd.date_range(panel["week_start"].min(), panel["week_start"].max(), freq="7D")
    if (panel["week_start"].dt.dayofweek != 6).any():
        problemas.append("há week_start que não cai num domingo")
    por_bairro = panel.groupby("bairro")["week_start"].nunique()
    incompletos = por_bairro[por_bairro != len(esperadas)]
    if len(incompletos):
        problemas.append(f"{len(incompletos)} bairros com semanas faltando no painel (esperado {len(esperadas)} "
                         f"semanas cada), por exemplo {list(incompletos.index[:3])}")
    faltam_semanas = sorted(set(esperadas) - set(panel["week_start"]))
    if faltam_semanas:
        problemas.append(f"semanas ausentes em todo o painel: {[str(s.date()) for s in faltam_semanas[:3]]}")
    nulos_casos = int(panel["casos"].isna().sum() + panel["bairro"].isna().sum())
    if nulos_casos or (panel["casos"] < 0).any():
        problemas.append(f"casos ou bairro nulos/negativos no painel ({nulos_casos} nulos)")
    no_painel = clima[clima["week_start"].isin(esperadas)]
    if len(no_painel) != len(esperadas):
        problemas.append(f"clima sem linha para {len(esperadas) - len(no_painel)} semanas do painel")
    if int(no_painel["chuva_mm"].isna().sum()):
        problemas.append(f"chuva nula em {int(no_painel['chuva_mm'].isna().sum())} semanas do painel (esperado 0)")
    for coluna in ("temp_media", "umid_media"):
        fracao = float(no_painel[coluna].isna().mean()) if len(no_painel) else 1.0
        if fracao > MAX_NULL_TEMP_HUM:
            problemas.append(f"{coluna} com {fracao:.1%} de nulos nas semanas do painel (limite {MAX_NULL_TEMP_HUM:.0%})")
    return problemas


def backup(processed: Path = config.DATA_PROCESSED) -> list[str]:
    feitos = []
    for nome in PROCESSED_FILES:
        origem = processed / nome
        if origem.exists():
            shutil.copy2(origem, processed / (nome + BACKUP_SUFFIX))
            feitos.append(nome)
    return feitos


def restore(processed: Path = config.DATA_PROCESSED) -> list[str]:
    restaurados = []
    for nome in PROCESSED_FILES:
        copia = processed / (nome + BACKUP_SUFFIX)
        if copia.exists():
            shutil.copy2(copia, processed / nome)
            restaurados.append(nome)
    return restaurados


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def publish(processed: Path = config.DATA_PROCESSED) -> dict:
    """Grava data/processed/manifest.json com linhas, período e hash dos arquivos que a API e o modelo leem."""
    panel, clima = read_panel(processed), read_climate(processed)
    manifesto = {"panel_end": config.PANEL_END,
                 "panel.csv": {"linhas": len(panel), "inicio": str(panel["week_start"].min().date()),
                               "fim": str(panel["week_start"].max().date()), "sha256": sha256(processed / "panel.csv")},
                 "clima_semanal.csv": {"linhas": len(clima), "inicio": str(clima["week_start"].min().date()),
                                       "fim": str(clima["week_start"].max().date()),
                                       "sha256": sha256(processed / "clima_semanal.csv")}}
    (processed / MANIFEST).write_text(json.dumps(manifesto, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifesto


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Etapas do DAG antecedengue_dados")
    sub = parser.add_subparsers(dest="etapa", required=True)
    p_ing = sub.add_parser("ingestao")
    p_ing.add_argument("--refresh", action="store_true")
    sub.add_parser("backup")
    p_cli = sub.add_parser("clima")
    p_cli.add_argument("--refresh", action="store_true")
    p_res = sub.add_parser("resumo")
    p_res.add_argument("alvo", choices=["raw", "panel", "clima"])
    sub.add_parser("validar")
    sub.add_parser("publicar")
    args = parser.parse_args(argv)
    logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if args.etapa == "ingestao":
        print(ingest(args.refresh))
    elif args.etapa == "backup":
        print(f"cópias de segurança: {backup()}")
    elif args.etapa == "clima":
        comando = build_climate(args.refresh)
        print("executando: " + " ".join(comando[1:]))
        subprocess.run(comando, check=True, cwd=config.ROOT)
    elif args.etapa == "resumo":
        print({"raw": summarize_raw, "panel": lambda: summarize_panel(read_panel()),
               "clima": lambda: summarize_climate(read_climate())}[args.alvo]())
    elif args.etapa == "validar":
        problemas = validate(read_panel(), read_climate())
        if problemas:
            print(f"restaurados da cópia de segurança: {restore()}")
            for p in problemas:
                print(f"FALHA: {p}")
            raise SystemExit(1)
        print("validação de qualidade ok: sem duplicatas, sem semanas faltando, nulos dentro do esperado, "
              f"PANEL_END coerente ({config.PANEL_END})")
    elif args.etapa == "publicar":
        manifesto = publish()
        print(json.dumps(manifesto, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
