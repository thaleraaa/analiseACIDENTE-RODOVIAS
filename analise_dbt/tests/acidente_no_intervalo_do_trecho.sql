SELECT
    f.acidente_id,
    f.trecho_id,
    f.km,
    d.km_inicial,
    d.km_final
FROM {{ ref('fato_acidente') }} AS f
JOIN {{ ref('dim_trecho') }} AS d USING (trecho_id)
WHERE f.km < d.km_inicial
   OR f.km > d.km_final
