{{ config(materialized='table') }}

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
FROM {{ source('prata', 'dnit') }}
