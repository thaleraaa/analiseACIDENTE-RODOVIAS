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

## Ambiente Python

Na raiz do projeto, crie o ambiente virtual uma vez, ative-o e instale as
dependências:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

O prompt do PowerShell deve passar a mostrar `(.venv)`. Execute os comandos
Python e dbt deste README nesse terminal ativado. Em um novo terminal, ative o
ambiente novamente com `.\.venv\Scripts\Activate.ps1`.

## Pipeline

O projeto possui um ponto de entrada único em `src/pipeline.py`. Os caminhos
das camadas ficam centralizados em `src/config.py`, calculados a partir da
raiz do projeto, para que os scripts não dependam da pasta de onde o comando
foi executado.

Para executar todas as etapas disponíveis:

```powershell
python .\src\pipeline.py
```

Para retomar a partir de uma etapa:

```powershell
python .\src\pipeline.py enriquecimento
```

A etapa de `carga` está implementada e a etapa de `modelagem` executa o dbt.

O pipeline registra as mensagens no terminal e em `pipeline.log`. O arquivo de
log é ignorado pelo Git. Cada etapa informa início, fim, duração e registra o
rastro completo quando ocorre uma falha.

## Modelagem e carga no DuckDB

O banco da camada Ouro é `dados/ouro/projeto.duckdb`. A carga usa DuckDB
embutido, sem servidor, usuário ou senha, e lê os Parquets da Prata
diretamente.

O grão da fato é:

> Uma linha de `ouro.fato_acidente` representa um acidente rodoviário
> registrado pela PRF.

O modelo possui:

- `prata.prf`, `prata.dnit` e `prata.prf_enriquecido`: cópias das entradas
  tratadas;
- `ouro.fato_acidente`: uma linha por acidente, com `acidente_id`;
- `ouro.dim_trecho`: uma linha por trecho/versionamento do DNIT;
- `ouro.vw_acidente_completo`: view com a fato enriquecida pelo trecho;
- `trecho_id`: chave derivada de `codigo` e `versao_snv`.

A etapa confere duplicidades de `acidente_id` e fatos órfãos sem trecho. Ambos
precisam ser zero. Acidentes sem correspondência no DNIT continuam na fato,
com `trecho_id` nulo, preservando o `left join` da etapa de enriquecimento.

## Transformação declarativa com dbt

A criação das tabelas da Ouro foi migrada para o dbt. O Python continua
responsável pela ingestão, transformação, enriquecimento e carga dos Parquets
da Prata. O dbt fica responsável apenas pelos `SELECT`s que criam os modelos
analíticos.

O projeto dbt está em `analise_dbt/` e possui:

- `models/sources.yml`: declara `prata.dnit` e
  `prata.prf_enriquecido` como fontes;
- `models/dim_trecho.sql`: cria a tabela `ouro.dim_trecho`;
- `models/fato_acidente.sql`: cria a tabela `ouro.fato_acidente`;
- `models/vw_acidente_completo.sql`: cria a view usando `ref()` nos dois
  modelos anteriores.

O perfil do dbt fica em `analise_dbt/profiles.yml` e aponta para
`dados/ouro/projeto.duckdb` por um caminho relativo, sem depender de um perfil
na pasta pessoal do usuário.

Comandos de validação:

```powershell
Push-Location analise_dbt
dbt debug --profiles-dir .
dbt run --profiles-dir .
Pop-Location
```

Ou, pelo pipeline:

```powershell
python .\src\pipeline.py modelagem
```

O pipeline agora executa `carga → modelagem`. A etapa de modelagem chama
`dbt run` com `check=True` e, depois, confirma que não há acidentes
duplicados nem fatos órfãos.

### Ideia de cada model

`prata.prf_enriquecido` é o resultado achatado do enriquecimento feito em
Python. Ele mantém os dados do acidente e as informações do trecho na mesma
linha, sendo a entrada principal da modelagem.

`dim_trecho.sql` cria `ouro.dim_trecho`. Essa dimensão guarda uma linha por
trecho/versionamento do DNIT e seus atributos descritivos, como rodovia, faixa
de quilometragem, superfície, administração e situação de obras. Esses dados
ficam separados para não serem repetidos em todas as linhas de acidentes.

`fato_acidente.sql` cria `ouro.fato_acidente`. Essa é a tabela central do
modelo: cada linha representa um acidente da PRF e contém as medidas e
características do acontecimento, como mortos, feridos, veículos, ano, tipo e
local. A coluna `trecho_id` aponta para a dimensão quando houve
correspondência com o DNIT.

`vw_acidente_completo.sql` cria `ouro.vw_acidente_completo`. A view faz um
`LEFT JOIN` entre a fato e a dimensão para oferecer uma consulta achatada,
pronta para análises, sem duplicar fisicamente os atributos do trecho. Ela
preserva também acidentes sem correspondência no DNIT.

Assim, os três models têm responsabilidades diferentes:

```text
prf_enriquecido  → entrada achatada tratada
dim_trecho       → descrição dos trechos
fato_acidente    → acontecimentos e medidas dos acidentes
vw_acidente_completo → consulta analítica reunindo fato e dimensão
```

## Testes, documentação e dashboard

Os testes de dados ficam junto dos models dbt:

- `analise_dbt/models/schema.yml` documenta modelos e colunas e declara
  `not_null`, `unique` e `relationships`;
- `analise_dbt/tests/acidente_no_intervalo_do_trecho.sql` verifica que o km
  de cada acidente associado está dentro do intervalo do trecho do DNIT.

Os testes rodam automaticamente depois de `dbt run` na etapa `modelagem` do
pipeline. Também podem ser executados manualmente:

```powershell
Push-Location analise_dbt
dbt test --profiles-dir .
dbt docs generate --profiles-dir .
dbt docs serve --profiles-dir .
Pop-Location
```

O dashboard é um consumidor separado do pipeline, feito com Streamlit. Ele lê
`ouro.vw_acidente_completo` em modo somente leitura e permite explorar o clima
em conjunto com características da via: traçado, tipo de pista, superfície,
administração, obras, tipo de trecho e UF. Também há filtros por tipo e
classificação do acidente, causa, período do dia, dia da semana e mês.

O painel apresenta:

- comparação cruzada de ocorrências por condição meteorológica e característica
  selecionada da via;
- mortes, feridos e acidentes com mortes por combinação;
- evolução anual dos acidentes e das mortes;
- filtros de período e categorias, incluindo registros sem informação;
- cobertura de correspondência com trechos do DNIT.

Os indicadores descrevem associações nos registros, não demonstram
causalidade nem risco por viagem. Para estimar risco seriam necessários dados
de exposição, como fluxo de veículos ou quilômetros percorridos em cada
condição. Os atributos do DNIT ficam sem informação para acidentes sem trecho
correspondente, que podem ser inspecionados separadamente pelos filtros.
Nas abas "Via x clima" e "Gravidade", é possível alternar entre mapa de calor,
barras horizontais e pizza. Mapa de calor e barras oferecem escala linear ou
logarítmica. Na aba "Gravidade", a pizza representa a participação dos
acidentes com morte por categoria, não a taxa de mortes. As pizzas mostram as
oito categorias mais frequentes e agrupam o restante em "Outras". Os gráficos
são renderizados com Altair pelo Streamlit; Matplotlib não é necessário.
Quando a dimensão selecionada é "Traçado da via", o painel exibe apenas Reta,
Curva, Aclive, Declive e Interseção de Vias. Valores combinados, como
"Reta;Declive", ficam fora desses gráficos e da tabela cruzada.

Para iniciar:

```powershell
python -m streamlit run .\dashboard\painel.py
```

Execute o pipeline antes para criar/atualizar o banco DuckDB. O painel não
altera nem cria tabelas.
