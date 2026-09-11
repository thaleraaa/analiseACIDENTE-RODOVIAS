# analiseACIDENTE-RODOVIAS

### PRF (dados abertos gov.br)
> Arquivo analisado: `datatran2025.csv` (ano de 2025).

- `feridos` = `feridos_leves` + `feridos_graves`, confirmado com 0 divergências nos 851191 registros.
- `pessoas` mantida, pois apresentou 33077 divergências em relação à soma `ilesos + mortos + feridos + ignorados`, critério de preenchimento pode variar entre anos.
- `regional` é derivada de `uf`, mesma informação em granularidade diferente.
- `horario` foi interpretado como data completa (2026-09-11 HH:MM), é só hora, precisa corrigir o tipo na prata.
- `latitude`, `longitude` e `km` estão como texto com vírgula decimal em vez de ponto, não são numéricas ainda.
- `classificacao_acidente` tem 1 valor ausente, removida na prata por ser coluna analítica central.
- `regional` tem 2 valores ausentes, `delegacia` tem 22, `uop` tem 38.
- `mortos` tem 92.8% de zeros, que é o esperado, pois a maioria dos acidentes não é fatal.
- `municipio`, `latitude`, `longitude`, `delegacia`, `uop` e `regional` descartadas por não serem necessárias para a análise.

### DNIT (SNV - Sistema Nacional de Viação, dnit.gov.br)
> Arquivo analisado: `SNV_202511A.xls` (versão novembro de 2025).

- `Ato legal` tem 99,9% de valores ausentes e o único valor presente é `Decisão Judicial` (constante), descartar na prata.
- `Obras` tem 98,0% de valores ausentes, descartar na prata.
- `Jurisdição` será usada como filtro na prata para manter apenas trechos federais, descartada após o filtro.
- `Estadual Coincidente` e `Superfície Est. Coincidente` têm ~79% de ausentes e só fazem sentido para trechos estaduais coincidentes, descartar junto com o filtro federal.
- `Unidade Local` tem 30,9% de ausentes, descartada pois a análise usará apenas o cruzamento por `BR` e `UF` com a PRF.
- `Extensão` descartada pois é derivada de `km final` - `km inicial`.
- `Federal Coincidente` descartada por não ser necessária para a análise.
- `km inicial`, `km final` estão como texto com vírgula decimal em vez de ponto, precisam de conversão para numérico na prata.
- `Tipo de trecho` tem 79,6% como `Eixo Principal`, desequilíbrio esperado, reflete a realidade da malha rodoviária.
- `Jurisdição` tem 79,1% como `Federal`, desequilíbrio esperado dado que é o SNV do DNIT (federal).
- `Administração` após filtro federal restará `Federal` e `Concessão Federal`, útil para identificar trechos concessionados.
- `Superfície Federal` e `Superfície` são altamente correlacionadas, como a análise se restringe a rodovias federais as duas coincidem, manter apenas `Superfície`.
- `Código` é único por registro, candidato a chave primária.

## Integração prevista

### PRF
- Fundir todos os `datatran<ano>.csv` em um único `prf.parquet` na prata.
- Anos disponíveis: 2015 a 2025.

### DNIT
- Fundir todos os `SNV_<versão>.xls` em um único `dnit.parquet` na prata.
- Versões disponíveis: 2015 a 2025.
- Cada versão representa um snapshot da malha rodoviária, adicionar coluna 

## Decisões de tratamento

### PRF
- Espaços removidos de nomes de coluna e texto.
- `km` convertido para float (vírgula → ponto).
- `horario` convertido para time.
- `feridos` confirmado como soma exata de `feridos_leves` + `feridos_graves` (0 divergências em 851.191 registros), descartado.
- `regional`, `municipio`, `latitude`, `longitude`, `delegacia`, `uop` descartadas por não serem necessárias para a análise.
- 11 linhas removidas por ausente em `classificacao_acidente`.
- Anos fundidos: 2015 a 2025. Total: 851.180 linhas.

### DNIT
- Espaços removidos de nomes de coluna e texto.
- Filtrado apenas trechos com `Jurisdição == Federal`: 262.668 → 134.376 linhas.
- `km inicial` e `km final` convertidos para float (vírgula → ponto).
- `Jurisdição`, `Extensão`, `Obras`, `Federal Coincidente`, `Ato legal`, `Unidade Local`, `Estadual Coincidente`, `Superfície Est. Coincidente`, `Superfície Federal` descartadas.
- Versões fundidas: 2016 a 2025. Total: 134.376 linhas.
- Coluna `versao_snv` adicionada para rastrear a origem de cada linha.