{{ config(materialized='view') }}

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
FROM {{ ref('fato_acidente') }} AS f
LEFT JOIN {{ ref('dim_trecho') }} AS d USING (trecho_id)
