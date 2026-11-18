{{ config(materialized='table') }}

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
FROM {{ source('prata', 'prf_enriquecido') }}
