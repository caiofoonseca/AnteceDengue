"""Gera reports/dados_inspecao.md com um retrato dos CSVs brutos de dengue.

Uso: python scripts/inspect_raw.py
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import config  # noqa: E402
from src import data_recife as dr  # noqa: E402

# Nomes lógicos -> candidatos de coluna (comparação sem diferenciar maiúsculas)
ALIASES = {
    "data_notificacao": ["dt_notificacao", "dt_notific"],
    "data_sintomas": ["dt_diagnostico_sintoma", "dt_sin_pri"],
    "bairro_residencia": ["no_bairro_residencia", "nm_bairro"],
    "agravo": ["co_cid", "id_agravo"],
    "classificacao_final": ["tp_classificacao_final", "classi_fin"],
    "criterio": ["tp_criterio_confirmacao", "criterio"],
    "evolucao": ["tp_evolucao_caso", "evolucao"],
}
CATEGORICAL = ["agravo", "classificacao_final", "criterio", "evolucao"]


def find_col(df: pd.DataFrame, key: str) -> str | None:
    lower = {c.lower(): c for c in df.columns}
    for cand in ALIASES[key]:
        if cand in lower:
            return lower[cand]
    return None


def infer_type(s: pd.Series) -> str:
    v = s.dropna().head(2000)
    if v.empty:
        return "vazio"
    if pd.to_numeric(v, errors="coerce").notna().all():
        return "numérico"
    if dr.parse_date_series(v).notna().mean() > 0.95:
        return "data"
    return "texto"


def md_table(df: pd.DataFrame) -> str:
    cols = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for row in df.itertuples(index=False):
        lines.append("| " + " | ".join(str(x).replace("|", "\\|") for x in row) + " |")
    return "\n".join(lines)


def main() -> None:
    files = dr.list_raw_csvs()
    if not files:
        sys.exit("Nenhum CSV em data/raw/. Rode scripts/download_raw.py primeiro.")
    data = {dr.year_from_filename(p): dr.read_csv_tolerant(p) for p in files}
    anos = sorted(data)
    out: list[str] = ["# Inspeção dos dados brutos de dengue (Recife)", ""]

    # 1. Arquivos
    out += ["## 1. Arquivos lidos", ""]
    rows = [(p.name, y, data[y].attrs["encoding"], repr(data[y].attrs["sep"]), len(data[y]), data[y].shape[1])
            for p, y in zip(files, anos)]
    out += [md_table(pd.DataFrame(rows, columns=["arquivo", "ano", "encoding", "separador", "linhas", "colunas"])), ""]
    faltando = [a for a in range(2013, 2026) if a not in data]
    out += [f"Anos presentes: {anos[0]}–{anos[-1]} ({len(anos)} arquivos). "
            f"Anos faltando em 2013–2025: {faltando or 'nenhum'}.", ""]

    # 2. Colunas e mudanças entre anos
    out += ["## 2. Colunas e mudanças entre anos", ""]
    grupos: dict[tuple, list[int]] = {}
    for y in anos:
        grupos.setdefault(tuple(data[y].columns), []).append(y)
    out += [f"Conjuntos distintos de colunas (nomes exatos): **{len(grupos)}**.", ""]
    for i, (cols, ys) in enumerate(grupos.items(), 1):
        out += [f"### Esquema {i} — anos {ys} ({len(cols)} colunas)", "", "`" + "`, `".join(cols) + "`", ""]
    out += ["### Colunas-chave por ano (nome real no arquivo)", ""]
    chave = [{"ano": y, **{k: find_col(data[y], k) or "—" for k in ALIASES}} for y in anos]
    out += [md_table(pd.DataFrame(chave)), ""]

    # 3. Linhas por ano
    out += ["## 3. Linhas por ano", "",
            md_table(pd.DataFrame([(y, len(data[y])) for y in anos], columns=["ano", "linhas"])), ""]

    # 4. Tipos e nulos
    out += ["## 4. Tipos inferidos e % de nulos", ""]
    for key in ALIASES:
        linhas = []
        for y in anos:
            c = find_col(data[y], key)
            if c is None:
                linhas.append((y, "—", "—", "—"))
            else:
                linhas.append((y, c, infer_type(data[y][c]), f"{data[y][c].isna().mean() * 100:.1f}%"))
        out += [f"**{key}**", "", md_table(pd.DataFrame(linhas, columns=["ano", "coluna", "tipo", "% nulos"])), ""]
    out += ["### % de nulos de todas as colunas (nomes em minúsculas; só colunas com ≥ 1% de nulos em algum ano)", ""]
    nulos = pd.DataFrame({y: data[y].isna().mean() * 100 for y in anos})
    nulos.index = [i.lower() for i in nulos.index]
    nulos = nulos.groupby(level=0).first()
    nulos = nulos[nulos.max(axis=1) >= 1].round(1)
    nulos.insert(0, "coluna", nulos.index)
    out += [md_table(nulos.reset_index(drop=True)), ""]

    # 5. Datas
    out += ["## 5. Intervalo de datas", ""]
    linhas = []
    for y in anos:
        for key in ("data_notificacao", "data_sintomas"):
            c = find_col(data[y], key)
            if c is None:
                continue
            d = dr.parse_date_series(data[y][c])
            falhas = int(data[y][c].notna().sum() - d.notna().sum())
            linhas.append((y, key, c, d.min().date() if d.notna().any() else "—",
                           d.max().date() if d.notna().any() else "—", falhas))
    out += [md_table(pd.DataFrame(linhas, columns=["ano_arquivo", "campo", "coluna", "mínimo", "máximo",
                                                   "datas não reconhecidas"])), ""]

    # 6. Bairros
    out += ["## 6. Bairros (residência)", ""]
    series = {y: data[y][find_col(data[y], "bairro_residencia")] for y in anos}
    todos = pd.concat(series.values(), ignore_index=True)
    norm = todos.dropna().str.strip().str.upper()
    out += [f"- Valores distintos (texto bruto): **{todos.nunique()}**",
            f"- Valores distintos após `strip` + maiúsculas: **{norm.nunique()}**",
            f"- Nulos: {todos.isna().mean() * 100:.1f}%", ""]
    top = norm.value_counts().head(20).rename_axis("bairro").reset_index(name="registros")
    out += ["### 20 nomes mais frequentes", "", md_table(top), ""]
    por_ano = pd.DataFrame([(y, s.str.strip().str.upper().nunique()) for y, s in series.items()],
                           columns=["ano", "nomes distintos"])
    out += ["### Nomes distintos por ano", "", md_table(por_ano), ""]
    aux = config.DATA_RAW / "auxiliares" / "tabela_de_bairros.csv"
    if aux.exists():
        tb = dr.read_csv_tolerant(aux)
        oficiais = set(tb["Nome Localidade"].str.strip().str.upper())
        fora = norm[~norm.isin(oficiais)].value_counts()
        out += [f"### Comparação com a Tabela de Bairros do portal ({len(oficiais)} localidades)", "",
                f"Nomes que **não** aparecem na tabela: {fora.shape[0]} distintos, {fora.sum()} registros "
                f"({fora.sum() / len(norm) * 100:.1f}% dos não nulos). Os 25 mais frequentes:", "",
                md_table(fora.head(25).rename_axis("nome").reset_index(name="registros")), ""]

    # 7. Categóricas
    out += ["## 7. Valores distintos das colunas categóricas (contagem por ano)", ""]
    for key in CATEGORICAL:
        tabela = {}
        for y in anos:
            c = find_col(data[y], key)
            if c is not None:
                tabela[y] = data[y][c].fillna("<nulo>").str.strip().value_counts()
        tab = pd.DataFrame(tabela).fillna(0).astype(int).rename_axis("valor").reset_index()
        out += [f"### {key}", "", md_table(tab), ""]

    # 8. Exemplos
    out += ["## 8. Exemplos (5 linhas, colunas-chave): ano mais antigo e mais recente", ""]
    for y in (anos[0], anos[-1]):
        cols = [c for c in (find_col(data[y], k) for k in ALIASES) if c]
        out += [f"**{y}**", "", md_table(data[y][cols].head(5).fillna("<nulo>")), ""]

    config.REPORTS_DIR.mkdir(exist_ok=True)
    destino = config.REPORTS_DIR / "dados_inspecao.md"
    destino.write_text("\n".join(out), encoding="utf-8")
    print(f"Relatório gravado em {destino}")


if __name__ == "__main__":
    main()
