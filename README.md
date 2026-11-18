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
- `Obras` tem 98,0% de valores ausentes, convertida para flag booleana `em_obras` (True = trecho com intervenção ativa); ausente interpretado como sem obra, confirmado pelo manual SNV DNIT seção 3.5.
- `Jurisdição` será usada como filtro na prata para manter apenas trechos Federal, Concessão Federal e Convênio de Administração, descartada após o filtro.
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


## Decisões de tratamento

### PRF
- Espaços removidos de nomes de coluna e texto.
- `km` convertido para float (vírgula → ponto).
- `horario` convertido para a coluna numérica `hora`; `horario` descartada após a extração.
- `feridos` confirmado como soma exata de `feridos_leves` + `feridos_graves` (0 divergências em 851.191 registros), descartado.
- `data_inversa` partida em `mes` e `dia`; `data_inversa` descartada após a partição (`ano` já existia extraído do nome do arquivo).
- `periodo_dia` criado a partir de `hora`: Madrugada (0–6), Manhã (6–12), Tarde (12–18), Noite (18–24).
- `pessoas` mantida apesar de 33.064 divergências em relação à soma das categorias de vítimas — critério de preenchimento pode variar entre anos.
- `regional`, `municipio`, `latitude`, `longitude`, `delegacia`, `uop` descartadas por não serem necessárias para a análise.
- `uso_solo`, `ignorados` e `fase_dia` descartados por não responderem à pergunta norteadora.
- 11 linhas removidas por ausente em `classificacao_acidente`.
- Anos fundidos: 2017 a 2025. Total: 632.657 linhas.


### DNIT
- Espaços removidos de nomes de coluna e texto.
- Filtrado apenas trechos federais: `Federal`, `Concessão Federal`,
  `Convênio de Administração` e os códigos históricos
  `FEDERAL-PAV`, `FEDERAL-PLA` e `FEDERAL-N_PAV`.
- `obras` convertida para flag booleana `em_obras`, coluna `obras` descartada após a conversão.
- `Jurisdição`, `Extensão`, `Federal Coincidente`, `Ato legal`, `Unidade Local`, `Estadual Coincidente`, `Superfície Est. Coincidente`, `Superfície Federal`, `local_de_inicio`, `local_de_fim`, `desc_coinc` descartadas.
- `km inicial` e `km final` convertidos para float (vírgula → ponto).
- Versões fundidas: 2017 a 2025. Total: 200.773 linhas.
- Coluna `versao_snv` adicionada para rastrear a origem de cada linha.

## Enriquecimento PRF + DNIT

O enriquecimento mantém a PRF como tabela principal, com uma linha por
acidente. A tabela do DNIT possui uma linha por trecho, por isso a chave não é
um valor único de quilômetro: o acidente casa quando `uf` e `br` são iguais e
`km_inicial <= km <= km_final`.

O script `src/enriquecer_prf_dnit.py` escolhe, para cada ano do acidente, a
versão do DNIT mais recente disponível até aquele ano. Como há versões
históricas desde 2017, os acidentes de 2017 a 2025 são comparados com a
versão correspondente disponível no período. Caso algum ano não tenha versão
anterior, o script usa a primeira versão disponível e registra essa limitação
na proveniência.

A junção é `left`, portanto nenhum acidente da PRF é removido. Quando mais de
um trecho contém o mesmo quilômetro, é escolhido o trecho de menor intervalo,
evitando duplicar o acidente. O resultado deve manter exatamente as 632.657
linhas da PRF.


O atributo derivado `distancia_inicio_trecho_km` também é criado após a
junção. Ele representa a distância do acidente em relação ao início do trecho
do DNIT.