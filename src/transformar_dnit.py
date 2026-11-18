from datetime import datetime
import json
import logging

import pandas as pd

from config import BRONZE, PRATA
import limpeza


log = logging.getLogger(__name__)
BRONZE = BRONZE / "DNIT"


def carregar():
    arquivos = sorted(
        list(BRONZE.glob("**/*.xls"))
        + list(BRONZE.glob("**/*.xlsx"))
    )

    if not arquivos:
        raise FileNotFoundError(f"Nenhum XLS encontrado em {BRONZE}")

    dfs = []

    for arquivo in arquivos:
        df = pd.read_excel(arquivo, header=2)
        df["versao_snv"] = arquivo.stem
        df = limpeza.normalizar_colunas(df)

        dfs.append(df)
        log.info("DNIT: %s (%s linhas)", arquivo.name, len(df))

    fundido = pd.concat(dfs, ignore_index=True)
    log.info("DNIT: total fundido %s linhas", len(fundido))

    return fundido, arquivos


def converter_tipos(df):
    for coluna in ["km_inicial", "km_final"]:
        if coluna not in df.columns:
            continue

        serie = (
            df[coluna]
            .astype("string")
            .str.strip()
            .str.replace(",", ".", regex=False)
        )

        df[coluna] = pd.to_numeric(serie, errors="coerce")

    return df


def flag_obras(df):
    if "obras" in df.columns:
        df["em_obras"] = df["obras"].notna().astype("boolean")
        df = df.drop(columns=["obras"])

    return df


def descartar_colunas(df):
    colunas = [
        "jurisdicao",
        "extensao",
        "federal_coincidente",
        "ato_legal",
        "unidade_local",
        "estadual_coincidente",
        "superficie_est_coincidente",
        "superficie_federal",
        "local_de_inicio",
        "local_de_fim",
        "desc_coinc",
    ]

    return df.drop(
        columns=[coluna for coluna in colunas if coluna in df.columns]
    )


def salvar(df):
    PRATA.mkdir(parents=True, exist_ok=True)

    destino = PRATA / "dnit.parquet"
    df.to_parquet(destino, index=False)

    log.info("DNIT: salvo em %s com dimensao %s", destino, df.shape)
    log.debug("DNIT: colunas finais: %s", df.columns.tolist())

    return destino


def registrar(arquivos, destino, antes, depois, decisoes):
    info = {
        "origens": [arquivo.name for arquivo in arquivos],
        "arquivo_prata": destino.name,
        "linhas_antes": antes,
        "linhas_depois": depois,
        "decisoes": decisoes,
        "transformado_em": datetime.now().isoformat(timespec="seconds"),
    }

    caminho = PRATA / "proveniencia.jsonl"

    with caminho.open("a", encoding="utf-8") as arquivo:
        arquivo.write(json.dumps(info, ensure_ascii=False) + "\n")


def main():
    df, arquivos = carregar()
    antes = len(df)

    df = limpeza.tirar_espacos(df)
    df = limpeza.filtrar_federal(df)
    df = converter_tipos(df)
    df = flag_obras(df)
    df = descartar_colunas(df)

    destino = salvar(df)

    registrar(
        arquivos,
        destino,
        antes,
        len(df),
        [
            "nomes das colunas normalizados para snake_case sem acentos ou simbolos",
            "espacos externos removidos dos valores textuais",
            "colunas duplicadas apos normalizacao removidas mantendo a primeira (obras aparecia como Obras e OBRAS)",
            "filtrado apenas trechos com jurisdicao Federal, Concessao Federal ou Convenio de Administracao",
            "km_inicial e km_final convertidos para float (virgula -> ponto)",
            "obras convertida para flag booleana em_obras (True = trecho com intervencao ativa); "
            "ausente = sem obra, confirmado pelo manual SNV DNIT secao 3.5 — "
            "EOD: duplicacao, EOP: pavimentacao, EOI: implantacao",
            "jurisdicao, extensao, federal_coincidente, ato_legal, unidade_local, "
            "estadual_coincidente, superficie_est_coincidente, superficie_federal descartadas",
            "local_de_inicio e local_de_fim descartados: join com PRF sera por br, uf e km, "
            "descricao textual nao entra em nenhuma chave",
            "desc_coinc descartada: nao relacionada a condicao de pista ou clima; "
            "trechos coincidentes poderiam gerar duplicatas no join por br+uf+km",
        ],
    )

    log.info("DNIT: transformacao concluida")


if __name__ == "__main__":
    main()