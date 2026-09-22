from pathlib import Path
from datetime import datetime
import json

import pandas as pd

import limpeza


BRONZE = Path("dados/bronze/PRF")
PRATA  = Path("dados/prata")


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


def converter_tipos(df):
    horario = pd.to_datetime(
        df["horario"],
        format="%H:%M:%S",
        errors="coerce",
    )

    df["hora"] = horario.dt.hour.astype("Int64")
    df.drop(columns=["horario"], inplace=True)

    df["br"] = pd.to_numeric(df["br"], errors="coerce").astype("Int64")

    df["km"] = (
        df["km"]
        .astype("string")
        .str.strip()
        .str.replace(",", ".", regex=False)
    )
    df["km"] = pd.to_numeric(df["km"], errors="coerce")

    return df


def periodo_dia(df):
    df["periodo_dia"] = pd.cut(
        df["hora"],
        bins=[0, 6, 12, 18, 24],
        labels=["Madrugada", "Manhã", "Tarde", "Noite"],
        right=False, include_lowest=True
    )
    return df


def conferir_redundancias(df):
    colunas = ["feridos", "feridos_leves", "feridos_graves"]

    if not all(coluna in df.columns for coluna in colunas):
        return df

    valores = df[colunas].apply(pd.to_numeric, errors="coerce").fillna(0)

    divergencias = (
        valores["feridos_leves"] + valores["feridos_graves"]
        != valores["feridos"]
    ).sum()

    print(f"Divergências feridos: {divergencias}")
    return df


def partir_data(df):
    df["data_inversa"] = pd.to_datetime(df["data_inversa"], errors="coerce")
    df["mes"] = df["data_inversa"].dt.month.astype("Int64")
    df["dia"] = df["data_inversa"].dt.day.astype("Int64")
    df = df.drop(columns=["data_inversa"])
    return df


def descartar_colunas(df):
    colunas = [
        "regional", "feridos", "municipio",
        "latitude", "longitude", "delegacia", "uop",
        "uso_solo", "ignorados", "fase_dia",
    ]
    df = df.drop(columns=[c for c in colunas if c in df.columns])
    print(f"Colunas descartadas: {colunas}")
    return df


def tratar_ausentes(df):
    antes = len(df)
    df = df.dropna(subset=["classificacao_acidente"])
    print(f"Ausentes em classificacao_acidente removidos: {antes - len(df)}")
    return df


def salvar(df):
    PRATA.mkdir(parents=True, exist_ok=True)
    destino = PRATA / "prf.parquet"
    df.to_parquet(destino, index=False)
    print(f"\nSalvo em: {destino} {df.shape}")
    return destino


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


def main():
    print("=" * 50)
    print(" Transformando: PRF")
    print("=" * 50)

    df, arquivos = carregar()
    antes = len(df)

    df = limpeza.normalizar_colunas(df)
    df = limpeza.tirar_espacos(df)
    df = converter_tipos(df)
    df = partir_data(df)
    df = periodo_dia(df)
    df = conferir_redundancias(df)
    df = descartar_colunas(df)
    df = tratar_ausentes(df)

    destino = salvar(df)

    registrar(
        arquivos,
        destino,
        antes,
        len(df),
        [
            "arquivos CSV lidos com separador ';' e codificacao latin-1",
            "nomes das colunas normalizados para snake_case, sem acentos ou simbolos",
            "espacos externos removidos dos valores textuais",
            "colunas duplicadas apos normalizacao removidas mantendo a primeira",
            "ano extraido do nome de cada arquivo datatran",
            "horario convertido para a coluna numerica hora",
            "coluna horario descartada apos a extracao da hora",
            "periodo_dia criado a partir da hora: Madrugada, Manha, Tarde e Noite",
            "feridos_leves e feridos_graves comparados com o total de feridos",
            "colunas regional, feridos, municipio, latitude, longitude, "
            "delegacia e uop descartadas",
            "registros sem classificacao_acidente removidos",
            "data_inversa partida em mes e dia; data_inversa descartada apos a particao (ano ja existia extraido do nome do arquivo)",
            "uso_solo descartado: urbano/rural nao e condicao de pista nem clima",
            "fase_dia descartada: redundante com periodo_dia",
            "ignorados descartado: nao analitico",
        ],
    )

    print("\nPRF concluído.")


if __name__ == "__main__":
    main()