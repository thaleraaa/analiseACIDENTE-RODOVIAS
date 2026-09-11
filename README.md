# analiseACIDENTE-RODOVIAS

### PRF (dados abertos gov.br)
> Arquivo analisado: `datatran2025.csv` (ano de 2025).

- `feridos` = `feridos_leves` + `feridos_graves`
- `pessoas` = `ilesos` + `mortos` + `feridos` + `ignorados`
- `regional` é derivada de `uf` é a mesma informação em granularidade diferente.
- `horario` foi interpretado como data completa (2026-09-11 HH:MM), é só hora, precisa corrigir o tipo na prata.
- `latitude` e `longitude` estão como texto com vírgula decimal em vez de ponto, não são numéricas ainda.
- `km` está como texto por conter vírgula decimal (ex: `546,2`).
- `classificacao_acidente` tem 1 valor ausente.
- `regional` tem 2 valores ausentes, `delegacia` tem 22, `uop` tem 38.
- `mortos` tem 92.8% de zeros, que é o esperado, pois a maioria dos acidentes não é fatal.

### DNIT (SNV - Sistema Nacional de Viação, dnit.gov.br)
> Arquivo analisado: `SNV_202511A.xls` (versão novembro de 2025).

- `Ato legal` tem 99,9% de valores ausentes e o único valor presente é `Decisão Judicial` (constante), descartar na prata.
- `Obras` tem 98,0% de valores ausentes, descartar na prata.
- `Jurisdição` será usada como filtro na prata para manter apenas trechos federais, descartada após o filtro.
- `Estadual Coincidente` e `Superfície Est. Coincidente` têm ~79% de ausentes e só fazem sentido para trechos estaduais coincidentes, descartar junto com o filtro federal.
- `Unidade Local` tem 30,9% de ausentes, descartada pois a análise usará apenas o cruzamento por `BR`, `UF` e `KM` com a PRF.
- `km inicial`, `km final` e `Extensão` estão como texto com vírgula decimal em vez de ponto, precisam de conversão para numérico na prata.
- `Tipo de trecho` tem 79,6% como `Eixo Principal`, desequilíbrio esperado, reflete a realidade da malha rodoviária.
- `Administração` após filtro federal restará `Federal` e `Concessão Federal`, útil para identificar trechos concessionados.
- `Superfície Federal` e `Superfície` são altamente correlacionadas, como a análise se restringe a rodovias federais as duas coincidem, manter apenas `Superfície`.
- `Código` é único por registro, candidato a chave primária.