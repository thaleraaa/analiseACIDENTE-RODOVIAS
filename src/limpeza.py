"""Funções de limpeza que servem a qualquer fonte."""
import re
import unicodedata

import pandas as pd


def tirar_espacos(df):
    for coluna in df.select_dtypes(include=["object", "string"]).columns:
        df[coluna] = df[coluna].astype("string").str.strip()
    return df


def nome_snake_case(nome):
    nome = str(nome).strip().lower()
    nome = unicodedata.normalize("NFKD", nome)
    nome = "".join(
        caractere
        for caractere in nome
        if not unicodedata.combining(caractere)
    )
    return re.sub(r"[^a-z0-9]+", "_", nome).strip("_")


def normalizar_colunas(df):
    df.columns = [nome_snake_case(coluna) for coluna in df.columns]

    if df.columns.duplicated().any():
        duplicadas = df.columns[df.columns.duplicated()].tolist()
        print(f"Colunas duplicadas removidas: {duplicadas}")
        df = df.loc[:, ~df.columns.duplicated()].copy()

    return df


def chave_texto(serie):
    """Versão comparável: sem acento, sem espaço sobrando, tudo minúsculo.
    Serve para comparar e juntar, não para exibir."""
    s = serie.astype("string").str.strip().str.lower()
    s = s.str.normalize("NFKD")
    s = s.str.encode("ascii", errors="ignore")
    return s.str.decode("utf-8")


def aplicar_mapa(serie, mapa):
    """Troca variantes pelo valor canônico. O que não estiver no mapa fica como está."""
    return serie.replace(mapa)


_JURISDICOES_FEDERAIS = {"federal", "concessao federal", "convenio de administracao"}


def filtrar_federal(df):
    if "jurisdicao" not in df.columns:
        raise KeyError(
            "A coluna 'jurisdicao' não foi encontrada. "
            f"Colunas disponíveis: {df.columns.tolist()}"
        )

    antes = len(df)
    df = df.loc[chave_texto(df["jurisdicao"]).isin(_JURISDICOES_FEDERAIS)].copy()

    print(
        f"Filtro federal: {antes} → {len(df)} linhas "
        f"({antes - len(df)} removidas)"
    )

    return df