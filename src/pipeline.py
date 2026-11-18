import logging
from pathlib import Path
import subprocess
import sys
import time

import duckdb

import carga
from config import RAIZ
import enriquecer_prf_dnit
import ingerir
import transformar_dnit
import transformar_prf
from config import configurar_log


log = logging.getLogger(__name__)


def executar(nome, funcao):
    log.info("etapa %s: inicio", nome)
    comecou = time.perf_counter()
    try:
        funcao()
    except Exception:
        log.exception("etapa %s: falhou", nome)
        raise
    duracao = time.perf_counter() - comecou
    log.info("etapa %s: fim em %.1fs", nome, duracao)


def etapa_carga():
    carga.main()


def etapa_modelagem():
    executavel = Path(sys.executable).with_name("dbt.exe")
    subprocess.run(
        [str(executavel), "run"],
        cwd=RAIZ / "analise_dbt",
        check=True,
    )
    with duckdb.connect(str(carga.BANCO), read_only=True) as con:
        carga.conferir(con)


ETAPAS = [
    ("ingestao", ingerir.main),
    ("transformacao", lambda: (transformar_prf.main(), transformar_dnit.main())),
    ("enriquecimento", enriquecer_prf_dnit.main),
    ("carga", etapa_carga),
    ("modelagem", etapa_modelagem),
]


def main(a_partir_de=None):
    configurar_log()
    comecou = a_partir_de is None

    for nome, funcao in ETAPAS:
        if nome == a_partir_de:
            comecou = True
        if not comecou or funcao is None:
            log.info("etapa %s: pulada", nome)
            continue
        executar(nome, funcao)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
