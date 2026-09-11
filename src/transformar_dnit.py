from pathlib import Path
from datetime import datetime
import json
import pandas as pd

# ── Caminhos ──────────────────────────────────────────────────────────────────
BRONZE = Path("dados/bronze/DNIT")
PRATA  = Path("dados/prata")

# ── Carregar e fundir ─────────────────────────────────────────────────────────

def carregar():
    arquivos = sorted(BRONZE.glob("**/*.xls") )
    if not arquivos:
        raise FileNotFoundError(f"Nenhum XLS em {BRONZE}")

    dfs = []
    for arq in arquivos:
        df = pd.read_excel(arq, header=2)
        df["versao_snv"] = arq.stem
        dfs.append(df)
        print(f"  · {arq.name} ({len(df)} linhas)")

    fundido = pd.concat(dfs, ignore_index=True)
    print(f"\nTotal fundido: {len(fundido)} linhas")
    return fundido, arquivos


# ── Transformações ─────────────────────────────────────────────────────────────

def tirar_espacos(df):
    df.columns = [str(c).strip() for c in df.columns]
    print(df.columns.tolist())  # << ver os nomes
    print(df.dtypes)            # << ver os tipos
    return df

def filtrar_federal(df):
    antes = len(df)
    df = df[df["Jurisdição"] == "Federal"].copy()
    print(f"Filtro federal: {antes} → {len(df)} linhas ({antes - len(df)} removidas)")
    return df


def converter_tipos(df):
    for col in ["km inicial", "km final"]:
        if df[col].dtype == object:
            df[col] = df[col].astype(str).str.replace(",", ".", regex=False)
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def descartar_colunas(df):
    colunas = [
        "Jurisdição", "Extensão", "Obras", "OBRAS",
        "Federal Coincidente", "Ato legal",
        "Unidade Local", "Estadual Coincidente",
        "Superfície Est. Coincidente", "Superfície Federal",
    ]
    df = df.drop(columns=[c for c in colunas if c in df.columns])
    print(f"Colunas descartadas: {colunas}")
    return df


# ── Salvar ────────────────────────────────────────────────────────────────────

def salvar(df):
    PRATA.mkdir(parents=True, exist_ok=True)
    destino = PRATA / "dnit.parquet"
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
    print(" Transformando: DNIT")
    print("="*50)

    df, arquivos = carregar()
    antes = len(df)

    df = tirar_espacos(df)
    df = filtrar_federal(df)
    df = converter_tipos(df)
    df = descartar_colunas(df)

    destino = salvar(df)
    registrar(arquivos, destino, antes, len(df), [
        "espacos removidos de colunas e texto",
        "filtrado apenas trechos com Jurisdicao Federal",
        "km inicial e km final convertidos para float (virgula -> ponto)",
        "Jurisdicao, Extensao, Obras, Federal Coincidente, Ato legal, Unidade Local, Estadual Coincidente, Superficie Est. Coincidente, Superficie Federal descartadas",
    ])

    print("\nDNIT concluído.")


if __name__ == "__main__":
    main()