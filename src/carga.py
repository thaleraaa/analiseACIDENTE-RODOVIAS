import logging

import duckdb

from config import OURO, PRATA


log = logging.getLogger(__name__)
BANCO = OURO / "projeto.duckdb"


def caminho_sql(caminho):
    return caminho.as_posix().replace("'", "''")


def carregar_prata(con):
    arquivos = {
        "prf": PRATA / "prf.parquet",
        "dnit": PRATA / "dnit.parquet",
        "prf_enriquecido": PRATA / "prf_enriquecido.parquet",
    }

    for nome, caminho in arquivos.items():
        if not caminho.exists():
            raise FileNotFoundError(f"Arquivo da Prata não encontrado: {caminho}")

        con.execute(
            f"""
            CREATE OR REPLACE TABLE prata.{nome} AS
            SELECT * FROM read_parquet('{caminho_sql(caminho)}')
            """
        )
        total = con.execute(f"SELECT COUNT(*) FROM prata.{nome}").fetchone()[0]
        log.info("Prata: %s carregada com %s registros", nome, total)


def construir_ouro(con):
    con.execute(
        """
        CREATE OR REPLACE TABLE ouro.dim_trecho AS
        SELECT DISTINCT
            md5(
                concat_ws(
                    '|',
                    coalesce(CAST(codigo AS VARCHAR), ''),
                    coalesce(versao_snv, '')
                )
            ) AS trecho_id,
            codigo,
            uf,
            br,
            km_inicial,
            km_final,
            tipo_de_trecho,
            administracao,
            superficie,
            em_obras,
            versao_snv
        FROM prata.dnit
        """
    )

    con.execute(
        """
        CREATE OR REPLACE TABLE ouro.fato_acidente AS
        SELECT
            id AS acidente_id,
            ano,
            mes,
            dia,
            hora,
            periodo_dia,
            dia_semana,
            uf,
            br,
            km,
            tipo_acidente,
            classificacao_acidente,
            causa_acidente,
            sentido_via,
            condicao_metereologica,
            tipo_pista,
            tracado_via,
            pessoas,
            mortos,
            feridos_leves,
            feridos_graves,
            ilesos,
            veiculos,
            CASE
                WHEN codigo IS NULL THEN NULL
                ELSE md5(
                    concat_ws(
                        '|',
                        coalesce(CAST(codigo AS VARCHAR), ''),
                        coalesce(versao_snv, '')
                    )
                )
            END AS trecho_id
        FROM prata.prf_enriquecido
        """
    )

    con.execute(
        """
        CREATE OR REPLACE VIEW ouro.vw_acidente_completo AS
        SELECT
            f.*,
            d.codigo,
            d.km_inicial,
            d.km_final,
            d.tipo_de_trecho,
            d.administracao,
            d.superficie,
            d.em_obras,
            d.versao_snv
        FROM ouro.fato_acidente f
        LEFT JOIN ouro.dim_trecho d USING (trecho_id)
        """
    )


def conferir(con):
    duplicados = con.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT acidente_id
            FROM ouro.fato_acidente
            GROUP BY acidente_id
            HAVING COUNT(*) > 1
        )
        """
    ).fetchone()[0]

    orfaos = con.execute(
        """
        SELECT COUNT(*)
        FROM ouro.fato_acidente f
        LEFT JOIN ouro.dim_trecho d USING (trecho_id)
        WHERE f.trecho_id IS NOT NULL AND d.trecho_id IS NULL
        """
    ).fetchone()[0]

    fatos = con.execute("SELECT COUNT(*) FROM ouro.fato_acidente").fetchone()[0]
    dimensoes = con.execute("SELECT COUNT(*) FROM ouro.dim_trecho").fetchone()[0]

    log.info(
        "Ouro: %s fatos, %s dimensoes, %s grupos duplicados, %s orfaos",
        fatos,
        dimensoes,
        duplicados,
        orfaos,
    )

    if duplicados or orfaos:
        raise AssertionError(
            f"Modelo invalido: {duplicados} duplicidades e {orfaos} orfaos."
        )

    return {
        "fatos": fatos,
        "dimensoes": dimensoes,
        "duplicados": duplicados,
        "orfaos": orfaos,
    }


def main():
    OURO.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(BANCO)) as con:
        con.execute("CREATE SCHEMA IF NOT EXISTS prata")
        con.execute("CREATE SCHEMA IF NOT EXISTS ouro")
        carregar_prata(con)

    log.info("Carga concluida: %s", BANCO)


if __name__ == "__main__":
    from config import configurar_log

    configurar_log()
    main()
