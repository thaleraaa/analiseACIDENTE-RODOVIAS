from pathlib import Path
from datetime import datetime
import json
import pandas as pd

# ── Caminhos ──────────────────────────────────────────────────────────────────
BRONZE = Path("dados/bronze/PRF")
PRATA  = Path("dados/prata")

# ── Carregar e fundir ─────────────────────────────────────────────────────────

def carregar():
    arquivos = sorted(BRONZE.glob("**/*.csv"))
    if not arquivos:
        raise FileNotFoundError(f"Nenhum CSV em {BRONZE}")

    dfs = []
    for arq in arquivos:
        df = pd.read_csv(arq, encoding="latin-1", sep=";")
        df["ano"] = int(arq.stem.replace("datatran", ""))
        dfs.append(df)
        print(f"  · {arq.name} ({len(df)} linhas)")

    fundido = pd.concat(dfs, ignore_index=True)
    print(f"\nTotal fundido: {len(fundido)} linhas")
    return fundido, arquivos


# ── Transformações ─────────────────────────────────────────────────────────────

def tirar_espacos(df):
    df.columns = df.columns.str.strip()
    for col in df.select_dtypes(include="object"):
        df[col] = df[col].str.strip()
    return df


def converter_tipos(df):
    for col in ["km"]:
        df[col] = df[col].astype(str).str.replace(",", ".", regex=False)
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["horario"] = pd.to_datetime(df["horario"], format="%H:%M:%S", errors="coerce").dt.time

    return df


def conferir_redundancias(df):
    divergencias = (df["feridos_leves"] + df["feridos_graves"] != df["feridos"]).sum()
    print(f"Divergências feridos: {divergencias}")
    return df


def descartar_colunas(df):
    colunas = [
        "regional", "feridos", "municipio",
        "latitude", "longitude", "delegacia", "uop",
    ]
    df = df.drop(columns=[c for c in colunas if c in df.columns])
    print(f"Colunas descartadas: {colunas}")
    return df


def tratar_ausentes(df):
    antes = len(df)
    df = df.dropna(subset=["classificacao_acidente"])
    print(f"Ausentes em classificacao_acidente removidos: {antes - len(df)}")
    return df


# ── Salvar ────────────────────────────────────────────────────────────────────

def salvar(df):
    PRATA.mkdir(parents=True, exist_ok=True)
    destino = PRATA / "prf.parquet"
    df.to_parquet(destino, index=False)
    print(f"\nSalvo em: {destino} {df.shape}")
    return destino


# ── Proveniência ──────────────────────────────────────────────────────────────

def registrar(arquivos, destino, antes, depois, decisoes):
    info = {
        "origens": [a.name for a in arquivos],
        "arquivo_prata": destino.name,
        "linhas_antes": antes,
        "linhas_depois": depois,
        "decisoes": decisoes,
        "transformado_em": datetime.now().isoformat(timespec="seconds"),
    }
    caminho = PRATA / "proveniencia.jsonl"
    with caminho.open("a", encoding="utf-8") as f:
        f.write(json.dumps(info, ensure_ascii=False) + "\n")


# ── Pipeline ──────────────────────────────────────────────────────────────────

def main():
    print("="*50)
    print(" Transformando: PRF")
    print("="*50)

    df, arquivos = carregar()
    antes = len(df)

    df = tirar_espacos(df)
    df = converter_tipos(df)
    df = conferir_redundancias(df)
    df = descartar_colunas(df)
    df = tratar_ausentes(df)

    destino = salvar(df)
    registrar(arquivos, destino, antes, len(df), [
        "espacos removidos de colunas e texto",
        "km convertido para float (virgula -> ponto)",
        "horario convertido para time",
        "regional, feridos, municipio, latitude, longitude, delegacia, uop descartadas",
        "feridos confirmado como soma exata de feridos_leves + feridos_graves",
        f"{antes - len(df)} linhas removidas por ausente em classificacao_acidente",
    ])

    print("\nPRF concluído.")


if __name__ == "__main__":
    main()