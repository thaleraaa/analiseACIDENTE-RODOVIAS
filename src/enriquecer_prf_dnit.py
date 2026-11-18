import re
from datetime import datetime
import json
import logging

import pandas as pd

from config import PRATA


log = logging.getLogger(__name__)
PRF_PATH = PRATA / "prf.parquet"
DNIT_PATH = PRATA / "dnit.parquet"
DESTINO = PRATA / "prf_enriquecido.parquet"
SEM_CORRESPONDENCIA = PRATA / "prf_sem_correspondencia_dnit.parquet"


def ano_versao(versao):
    encontrado = re.search(r"SNV_(\d{4})", str(versao))
    if not encontrado:
        raise ValueError(f"Versão do DNIT sem ano reconhecível: {versao}")
    return int(encontrado.group(1))


def escolher_versao_por_ano(dnit):
    versoes = (
        dnit[["versao_snv", "_ano_versao"]]
        .drop_duplicates()
        .sort_values(["_ano_versao", "versao_snv"])
    )

    escolhidas = {}
    for ano in range(2017, 2026):
        anteriores = versoes.loc[versoes["_ano_versao"] <= ano]
        if anteriores.empty:
            escolhidas[ano] = versoes.iloc[0]["versao_snv"]
        else:
            escolhidas[ano] = anteriores.iloc[-1]["versao_snv"]

    return escolhidas


def preparar(df_prf, df_dnit):
    prf = df_prf.copy().reset_index(drop=True)
    dnit = df_dnit.copy()

    prf["_linha_prf"] = prf.index
    prf["uf"] = prf["uf"].astype("string").str.strip().str.upper()
    dnit["uf"] = dnit["uf"].astype("string").str.strip().str.upper()
    prf["br"] = pd.to_numeric(prf["br"], errors="coerce").astype("Int64")
    dnit["br"] = pd.to_numeric(dnit["br"], errors="coerce").astype("Int64")
    dnit["_ano_versao"] = dnit["versao_snv"].map(ano_versao)

    return prf, dnit


def juntar_por_intervalo(prf, dnit):
    versoes = escolher_versao_por_ano(dnit)
    resultados = []
    ausentes = []

    for ano, acidentes in prf.groupby("ano", sort=True):
        versao = versoes.get(int(ano), versoes[min(versoes)])
        trechos = dnit.loc[dnit["versao_snv"] == versao].copy()
        trechos_por_chave = {
            chave: grupo
            for chave, grupo in trechos.groupby(["uf", "br"], dropna=False)
        }

        for chave, grupo_acidentes in acidentes.groupby(
            ["uf", "br"], dropna=False
        ):
            grupo_trechos = trechos_por_chave.get(chave)
            if grupo_trechos is None:
                sem_par = grupo_acidentes.copy()
                sem_par["motivo"] = "uf_br_sem_trecho"
            else:
                candidatos = grupo_acidentes.merge(
                    grupo_trechos,
                    on=["uf", "br"],
                    how="inner",
                    suffixes=("", "_dnit"),
                )
                no_intervalo = (
                    candidatos["km"].ge(candidatos["km_inicial"])
                    & candidatos["km"].le(candidatos["km_final"])
                )
                encontrados = candidatos.loc[no_intervalo].copy()

                if not encontrados.empty:
                    encontrados["_tamanho_trecho"] = (
                        encontrados["km_final"] - encontrados["km_inicial"]
                    )
                    encontrados = encontrados.sort_values(
                        ["_linha_prf", "_tamanho_trecho", "codigo"],
                        kind="stable",
                    )
                    encontrados = encontrados.drop_duplicates(
                        subset="_linha_prf", keep="first"
                    )
                    resultados.append(encontrados)

                ids_encontrados = set(encontrados["_linha_prf"])
                sem_par = grupo_acidentes.loc[
                    ~grupo_acidentes["_linha_prf"].isin(ids_encontrados)
                ].copy()
                sem_par["motivo"] = "km_fora_do_intervalo"

            if not sem_par.empty:
                chaves = sem_par[
                    ["_linha_prf", "uf", "br", "km", "ano", "motivo"]
                ].copy()
                chaves["versao_snv_consultada"] = versao
                ausentes.append(chaves)

    resultado = pd.concat(resultados, ignore_index=True)
    sem_correspondencia = (
        pd.concat(ausentes, ignore_index=True)
        if ausentes
        else pd.DataFrame(
            columns=[
                "_linha_prf",
                "uf",
                "br",
                "km",
                "ano",
                "versao_snv_consultada",
                "motivo",
            ]
        )
    )

    if len(resultado) + len(sem_correspondencia) != len(prf):
        raise AssertionError(
            "A junção não classificou todos os acidentes como encontrados ou ausentes."
        )

    if resultado["_linha_prf"].duplicated().any():
        raise AssertionError("A junção gerou mais de um trecho para o mesmo acidente.")

    return resultado, sem_correspondencia, versoes


def adicionar_atributo_derivado(resultado):
    resultado["distancia_inicio_trecho_km"] = (
        resultado["km"] - resultado["km_inicial"]
    )
    return resultado


def completar_left_join(prf, encontrados, sem_correspondencia):
    colunas_dnit = [
        coluna
        for coluna in encontrados.columns
        if coluna not in prf.columns
        and coluna not in {"_merge", "_tamanho_trecho"}
    ]

    resultado = prf.copy()
    encontrados_por_id = encontrados.set_index("_linha_prf")
    for coluna in colunas_dnit:
        resultado[coluna] = encontrados_por_id[coluna].reindex(
            resultado["_linha_prf"]
        ).to_numpy()

    return resultado


def registrar(antes, depois, sem_correspondencia, versoes):
    info = {
        "origens": [PRF_PATH.name, DNIT_PATH.name],
        "arquivo_prata": DESTINO.name,
        "arquivo_sem_correspondencia": SEM_CORRESPONDENCIA.name,
        "linhas_antes_prf": antes,
        "linhas_depois": depois,
        "sem_correspondencia": sem_correspondencia,
        "versoes_dnit_por_ano": versoes,
        "transformado_em": datetime.now().isoformat(timespec="seconds"),
        "decisoes": [
            "PRF mantida como tabela da esquerda e todos os acidentes preservados",
            "junção por uf e br, com km_inicial <= km <= km_final",
            "uma versão do DNIT escolhida por ano: a mais recente disponível "
            "até o ano do acidente; para anos anteriores à primeira versão, "
            "usada a primeira versão disponível",
            "sobreposição de trechos resolvida escolhendo o menor intervalo",
            "atributo derivado distancia_inicio_trecho_km criado após a junção",
        ],
    }

    caminho = PRATA / "proveniencia.jsonl"
    with caminho.open("a", encoding="utf-8") as arquivo:
        arquivo.write(json.dumps(info, ensure_ascii=False) + "\n")


def main():
    prf = pd.read_parquet(PRF_PATH)
    dnit = pd.read_parquet(DNIT_PATH)
    prf, dnit = preparar(prf, dnit)

    encontrados, sem_correspondencia, versoes = juntar_por_intervalo(prf, dnit)
    resultado = completar_left_join(prf, encontrados, sem_correspondencia)
    resultado = adicionar_atributo_derivado(resultado)
    resultado = resultado.drop(
        columns=["_linha_prf", "_ano_versao", "_merge", "_tamanho_trecho"],
        errors="ignore",
    )
    resultado.to_parquet(DESTINO, index=False)
    sem_correspondencia.to_parquet(SEM_CORRESPONDENCIA, index=False)

    log.info("Enriquecimento: PRF antes: %s", len(prf))
    log.info("Enriquecimento: resultado: %s", len(resultado))
    log.warning(
        "Enriquecimento: sem correspondencia: %s",
        len(sem_correspondencia),
    )
    log.info(
        "Enriquecimento: motivos: %s",
        sem_correspondencia["motivo"].value_counts(dropna=False).to_dict(),
    )
    log.info("Enriquecimento: salvo em %s", DESTINO)
    log.info("Enriquecimento: ausentes em %s", SEM_CORRESPONDENCIA)

    registrar(
        len(prf),
        len(resultado),
        len(sem_correspondencia),
        versoes,
    )


if __name__ == "__main__":
    main()
