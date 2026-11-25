import math

import altair as alt
import pandas as pd
import streamlit as st

import consultas


st.set_page_config(page_title="Acidentes em rodovias federais", layout="wide")
st.title("Clima, condições da via e acidentes rodoviários")
st.caption(
    "Explore como as ocorrencias e suas consequencias variam entre condicoes "
    "meteorologicas e caracteristicas das rodovias federais."
)

anos = consultas.anos_disponiveis()
if not anos:
    st.error("Nao ha anos disponiveis no banco. Execute o pipeline primeiro.")
    st.stop()

with st.sidebar:
    st.header("Analise e filtros")
    ano_inicial, ano_final = st.select_slider(
        "Periodo",
        options=anos,
        value=(anos[0], anos[-1]),
    )
    dimensao_label = st.selectbox(
        "Caracteristica da via para comparar com o clima",
        list(consultas.DIMENSOES_VIA),
        index=0,
    )
    dimensao_via = consultas.DIMENSOES_VIA[dimensao_label]
    tipo_grafico = st.selectbox(
        "Tipo de gráfico",
        ["Mapa de calor", "Barras horizontais", "Pizza"],
        key="tipo_grafico",
    )
    escala_grafico = None
    if tipo_grafico != "Pizza":
        escala_grafico = st.selectbox(
            "Escala dos valores",
            ["Logarítmica", "Linear"],
            key="escala_grafico",
        )

    with st.expander("Filtros adicionais", expanded=True):
        campos = [
            ("condicao_metereologica", "Clima"),
            ("tipo_acidente", "Tipo de acidente"),
            ("classificacao_acidente", "Classificacao do acidente"),
            ("causa_acidente", "Causa registrada"),
            ("tipo_pista", "Tipo de pista"),
            ("tracado_via", "Tracado da via"),
            ("superficie", "Superficie (DNIT)"),
            ("administracao", "Administracao (DNIT)"),
            ("em_obras", "Obras no trecho (DNIT)"),
            ("tipo_de_trecho", "Tipo de trecho (DNIT)"),
            ("uf", "UF"),
            ("periodo_dia", "Periodo do dia"),
            ("dia_semana", "Dia da semana"),
            ("mes", "Mes"),
        ]
        filtros = {}
        for campo, rotulo in campos:
            opcoes = consultas.opcoes(campo)
            filtros[campo] = st.selectbox(
                rotulo,
                opcoes,
                key=f"filtro_{campo}",
            )

resumo = consultas.resumo(ano_inicial, ano_final, filtros)
cruzamento = consultas.comparativo(
    ano_inicial,
    ano_final,
    filtros,
    dimensao_via,
)
tendencia = consultas.evolucao(ano_inicial, ano_final, filtros)

acidentes = int(resumo["acidentes"])
mortes = int(resumo["mortes"])
feridos = int(resumo["feridos"])
acidentes_fatais = int(resumo["acidentes_com_mortes"])
mortes_por_100_acidentes = (mortes / acidentes * 100) if acidentes else 0
percentual_fatais = (acidentes_fatais / acidentes * 100) if acidentes else 0
percentual_com_trecho = (
    int(resumo["acidentes_com_trecho"]) / acidentes * 100 if acidentes else 0
)

colunas_kpi = st.columns(5)
colunas_kpi[0].metric("Acidentes", f"{acidentes:,}".replace(",", "."))
colunas_kpi[1].metric("Mortes registradas", f"{mortes:,}".replace(",", "."))
colunas_kpi[2].metric("Feridos", f"{feridos:,}".replace(",", "."))
colunas_kpi[3].metric(
    "Acidentes com morte",
    f"{percentual_fatais:.2f}%",
    help=f"{acidentes_fatais:,} acidentes com pelo menos uma morte.",
)
colunas_kpi[4].metric(
    "Com trecho DNIT identificado",
    f"{percentual_com_trecho:.1f}%",
)

st.info(
    "Os valores mostram associacoes nos registros, nao provam causalidade nem "
    "risco por veiculo. Para estimar risco seriam necessarios dados de "
    "exposicao, como fluxo ou quilometros percorridos em cada condicao."
)

aba_cruzamento, aba_gravidade, aba_tempo, aba_dados = st.tabs(
    ["Via x clima", "Gravidade", "Evolucao temporal", "Tabela agregada"]
)

with aba_cruzamento:
    st.subheader(f"Acidentes por clima e {dimensao_label.lower()}")
    if dimensao_via == "tracado_via":
        st.caption(
            "Exibindo apenas Reta, Curva, Aclive, Declive e Interseção de Vias. "
            "Combinações entre traçados e outras categorias ficam fora desta "
            "comparação."
        )
    if tipo_grafico == "Mapa de calor":
        st.caption(
            "A cor representa o numero de ocorrencias. Passe o cursor sobre "
            "uma celula para ver o total exato; categorias sem informacao "
            "ficam visiveis."
        )
    elif tipo_grafico == "Barras horizontais":
        st.caption(
            "As barras comparam ocorrencias por categoria e clima. Passe o "
            "cursor sobre uma barra para ver o total exato."
        )
    else:
        st.caption(
            "A pizza compara o total de acidentes por categoria, somando os "
            "climas. As oito maiores categorias aparecem separadas; as demais "
            "sao agrupadas em Outras quando necessario."
        )
    if cruzamento.empty:
        st.info("Nenhum registro corresponde aos filtros selecionados.")
    else:
        totais_categoria = (
            cruzamento.groupby("categoria_via", as_index=False)["acidentes"]
            .sum()
            .sort_values("acidentes", ascending=False)
        )
        principais = totais_categoria.head(15)["categoria_via"]
        grafico = cruzamento[
            cruzamento["categoria_via"].isin(principais)
        ]
        if tipo_grafico == "Mapa de calor":
            escala_cor = (
                alt.Scale(type="log", base=10, zero=False)
                if escala_grafico == "Logarítmica"
                else alt.Scale(type="linear", zero=True)
            )
            figura = (
                alt.Chart(grafico)
                .mark_rect(stroke="white", strokeWidth=1)
                .encode(
                    x=alt.X(
                        "clima:N",
                        title="Condicao meteorologica",
                        sort=alt.EncodingSortField(
                            field="acidentes",
                            op="sum",
                            order="descending",
                        ),
                    ),
                    y=alt.Y(
                        "categoria_via:N",
                        title="Categoria da via",
                        sort=alt.EncodingSortField(
                            field="acidentes",
                            op="sum",
                            order="descending",
                        ),
                    ),
                    color=alt.Color(
                        "acidentes:Q",
                        title=f"Acidentes ({escala_grafico.lower()})",
                        scale=escala_cor,
                        legend=alt.Legend(format="~s"),
                    ),
                    tooltip=[
                        alt.Tooltip("categoria_via:N", title="Categoria"),
                        alt.Tooltip("clima:N", title="Clima"),
                        alt.Tooltip(
                            "acidentes:Q",
                            title="Acidentes",
                            format=",",
                        ),
                    ],
                )
                .properties(height=max(420, len(principais) * 32))
            )
        elif tipo_grafico == "Barras horizontais":
            dados_barras = grafico.copy()
            if escala_grafico == "Logarítmica":
                dados_barras["acidentes_log10"] = dados_barras[
                    "acidentes"
                ].map(math.log10)
                expoente_maximo = max(
                    1,
                    math.ceil(math.log10(dados_barras["acidentes"].max())),
                )
                eixo_x = alt.X(
                    "acidentes_log10:Q",
                    title="Acidentes (escala logarítmica)",
                    scale=alt.Scale(domain=[0, expoente_maximo]),
                    axis=alt.Axis(
                        values=list(range(expoente_maximo + 1)),
                        labelExpr="format(pow(10, datum.value), '~s')",
                    ),
                )
            else:
                eixo_x = alt.X(
                    "acidentes:Q",
                    title="Acidentes",
                    axis=alt.Axis(format="~s"),
                )
            figura = (
                alt.Chart(dados_barras)
                .mark_bar()
                .encode(
                    x=eixo_x,
                    y=alt.Y(
                        "categoria_via:N",
                        title="Categoria da via",
                        sort=alt.EncodingSortField(
                            field="acidentes",
                            op="sum",
                            order="descending",
                        ),
                    ),
                    yOffset=alt.YOffset("clima:N"),
                    color=alt.Color("clima:N", title="Clima"),
                    tooltip=[
                        alt.Tooltip("categoria_via:N", title="Categoria"),
                        alt.Tooltip("clima:N", title="Clima"),
                        alt.Tooltip(
                            "acidentes:Q",
                            title="Acidentes",
                            format=",",
                        ),
                    ],
                )
                .properties(height=max(480, len(principais) * 34))
            )
        else:
            dados_pizza = totais_categoria.head(8).copy()
            outras = int(totais_categoria.iloc[8:]["acidentes"].sum())
            if outras:
                dados_pizza = pd.concat(
                    [
                        dados_pizza,
                        pd.DataFrame(
                            [{"categoria_via": "Outras", "acidentes": outras}]
                        ),
                    ],
                    ignore_index=True,
                )
            dados_pizza["percentual"] = (
                dados_pizza["acidentes"] / dados_pizza["acidentes"].sum() * 100
            )
            figura = (
                alt.Chart(dados_pizza)
                .mark_arc(outerRadius=160)
                .encode(
                    theta=alt.Theta("acidentes:Q", stack=True),
                    color=alt.Color(
                        "categoria_via:N",
                        title=dimensao_label,
                    ),
                    tooltip=[
                        alt.Tooltip("categoria_via:N", title="Categoria"),
                        alt.Tooltip(
                            "acidentes:Q",
                            title="Acidentes",
                            format=",",
                        ),
                        alt.Tooltip(
                            "percentual:Q",
                            title="Percentual",
                            format=".1f",
                        ),
                    ],
                )
                .properties(height=420)
            )
        st.altair_chart(figura, width="stretch")
        st.dataframe(
            cruzamento.sort_values("acidentes", ascending=False),
            hide_index=True,
            width="stretch",
        )

with aba_gravidade:
    st.subheader("Consequencias por clima e caracteristica da via")
    if dimensao_via == "tracado_via":
        st.caption(
            "Exibindo apenas Reta, Curva, Aclive, Declive e Interseção de Vias. "
            "Combinações entre traçados e outras categorias ficam fora desta "
            "comparação."
        )
    if cruzamento.empty:
        st.info("Nenhum registro corresponde aos filtros selecionados.")
    else:
        tipo_grafico_gravidade = st.selectbox(
            "Tipo de gráfico da gravidade",
            ["Mapa de calor", "Barras horizontais", "Pizza"],
            key="tipo_grafico_gravidade",
        )
        escala_gravidade = None
        if tipo_grafico_gravidade != "Pizza":
            escala_gravidade = st.selectbox(
                "Escala da gravidade",
                ["Logarítmica", "Linear"],
                key="escala_gravidade",
            )

        gravidade = cruzamento.copy()
        gravidade["mortes_por_100_acidentes"] = (
            gravidade["mortes"] / gravidade["acidentes"] * 100
        )
        gravidade["percentual_acidentes_com_morte"] = (
            gravidade["acidentes_com_mortes"] / gravidade["acidentes"] * 100
        )
        if tipo_grafico_gravidade == "Mapa de calor":
            dados_calor = gravidade.copy()
            campo_cor = "mortes_por_100_acidentes"
            legenda_gravidade = alt.Legend(format=".1f")
            if escala_gravidade == "Logarítmica":
                dados_calor["mortes_log10"] = dados_calor[
                    "mortes_por_100_acidentes"
                ].map(lambda valor: math.log10(valor + 1))
                campo_cor = "mortes_log10"
                maior_taxa = dados_calor["mortes_por_100_acidentes"].max()
                valores_taxa = [
                    valor
                    for valor in [0, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]
                    if valor <= maior_taxa
                ]
                valores_legenda = [
                    math.log10(valor + 1) for valor in valores_taxa
                ]
                legenda_gravidade = alt.Legend(
                    values=valores_legenda,
                    labelExpr="format(pow(10, datum.value) - 1, '~s')",
                )
            figura_gravidade = (
                alt.Chart(dados_calor)
                .mark_rect(stroke="white", strokeWidth=1)
                .encode(
                    x=alt.X(
                        "clima:N",
                        title="Condicao meteorologica",
                        sort=alt.EncodingSortField(
                            field="mortes",
                            op="sum",
                            order="descending",
                        ),
                    ),
                    y=alt.Y(
                        "categoria_via:N",
                        title="Categoria da via",
                        sort=alt.EncodingSortField(
                            field="mortes_por_100_acidentes",
                            op="mean",
                            order="descending",
                        ),
                    ),
                    color=alt.Color(
                        f"{campo_cor}:Q",
                        title=(
                            "Mortes por 100 acidentes"
                            if escala_gravidade == "Linear"
                            else "Mortes por 100 acidentes (log)"
                        ),
                        scale=alt.Scale(type="linear", zero=True),
                        legend=legenda_gravidade,
                    ),
                    tooltip=[
                        alt.Tooltip("categoria_via:N", title="Categoria"),
                        alt.Tooltip("clima:N", title="Clima"),
                        alt.Tooltip(
                            "mortes_por_100_acidentes:Q",
                            title="Mortes por 100 acidentes",
                            format=".2f",
                        ),
                        alt.Tooltip(
                            "percentual_acidentes_com_morte:Q",
                            title="% de acidentes com morte",
                            format=".2f",
                        ),
                    ],
                )
                .properties(height=max(420, gravidade["categoria_via"].nunique() * 32))
            )
            st.altair_chart(figura_gravidade, width="stretch")
        elif tipo_grafico_gravidade == "Barras horizontais":
            dados_barras = gravidade.copy()
            if escala_gravidade == "Logarítmica":
                dados_barras["mortes_log10"] = dados_barras[
                    "mortes_por_100_acidentes"
                ].map(lambda valor: math.log10(valor + 1))
                maior_taxa = dados_barras["mortes_por_100_acidentes"].max()
                valores_taxa = [
                    valor
                    for valor in [0, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]
                    if valor <= maior_taxa
                ]
                eixo_x = alt.X(
                    "mortes_log10:Q",
                    title="Mortes por 100 acidentes (log)",
                    scale=alt.Scale(
                        domain=[0, max(math.log10(maior_taxa + 1), 0.1)]
                    ),
                    axis=alt.Axis(
                        values=[math.log10(valor + 1) for valor in valores_taxa],
                        labelExpr="format(pow(10, datum.value) - 1, '~s')",
                    ),
                )
            else:
                eixo_x = alt.X(
                    "mortes_por_100_acidentes:Q",
                    title="Mortes por 100 acidentes",
                    axis=alt.Axis(format="~s"),
                )
            figura_gravidade = (
                alt.Chart(dados_barras)
                .mark_bar()
                .encode(
                    x=eixo_x,
                    y=alt.Y(
                        "categoria_via:N",
                        title="Categoria da via",
                        sort=alt.EncodingSortField(
                            field="mortes_por_100_acidentes",
                            op="mean",
                            order="descending",
                        ),
                    ),
                    yOffset=alt.YOffset("clima:N"),
                    color=alt.Color("clima:N", title="Clima"),
                    tooltip=[
                        alt.Tooltip("categoria_via:N", title="Categoria"),
                        alt.Tooltip("clima:N", title="Clima"),
                        alt.Tooltip(
                            "mortes_por_100_acidentes:Q",
                            title="Mortes por 100 acidentes",
                            format=".2f",
                        ),
                        alt.Tooltip(
                            "percentual_acidentes_com_morte:Q",
                            title="% de acidentes com morte",
                            format=".2f",
                        ),
                    ],
                )
                .properties(height=max(480, gravidade["categoria_via"].nunique() * 34))
            )
            st.altair_chart(figura_gravidade, width="stretch")
        else:
            dados_pizza = (
                gravidade.groupby("categoria_via", as_index=False)[
                    "acidentes_com_mortes"
                ]
                .sum()
                .sort_values("acidentes_com_mortes", ascending=False)
            )
            total_acidentes_com_morte = int(
                dados_pizza["acidentes_com_mortes"].sum()
            )
            if total_acidentes_com_morte == 0:
                st.info(
                    "Nao ha acidentes com morte neste recorte para montar a pizza."
                )
            else:
                dados_pizza = dados_pizza.head(8).copy()
                outras = total_acidentes_com_morte - int(
                    dados_pizza["acidentes_com_mortes"].sum()
                )
                if outras:
                    dados_pizza = pd.concat(
                        [
                            dados_pizza,
                            pd.DataFrame(
                                [
                                    {
                                        "categoria_via": "Outras",
                                        "acidentes_com_mortes": outras,
                                    }
                                ]
                            ),
                        ],
                        ignore_index=True,
                    )
                dados_pizza["percentual"] = (
                    dados_pizza["acidentes_com_mortes"]
                    / total_acidentes_com_morte
                    * 100
                )
                figura_gravidade = (
                    alt.Chart(dados_pizza)
                    .mark_arc(outerRadius=160)
                    .encode(
                        theta=alt.Theta("acidentes_com_mortes:Q", stack=True),
                        color=alt.Color(
                            "categoria_via:N",
                            title=dimensao_label,
                        ),
                        tooltip=[
                            alt.Tooltip("categoria_via:N", title="Categoria"),
                            alt.Tooltip(
                                "acidentes_com_mortes:Q",
                                title="Acidentes com morte",
                                format=",",
                            ),
                            alt.Tooltip(
                                "percentual:Q",
                                title="Percentual",
                                format=".1f",
                            ),
                        ],
                    )
                    .properties(height=420)
                )
                st.altair_chart(figura_gravidade, width="stretch")
        st.caption(
            "Mortes por 100 acidentes e percentual de acidentes com mortes "
            "descrevem a gravidade entre os registros; nao sao taxas de risco "
            "por viagem ou volume de trafego. A pizza mostra a participacao dos "
            "acidentes com morte por categoria, nao a taxa de mortes."
        )
        st.dataframe(
            gravidade.sort_values(
                "mortes_por_100_acidentes",
                ascending=False,
            ),
            hide_index=True,
            width="stretch",
        )

with aba_tempo:
    st.subheader("Evolucao anual no periodo filtrado")
    if tendencia.empty:
        st.info("Nenhum registro corresponde aos filtros selecionados.")
    else:
        col_acidentes, col_mortes = st.columns(2)
        with col_acidentes:
            st.caption("Acidentes registrados por ano")
            st.line_chart(tendencia, x="ano", y="acidentes")
        with col_mortes:
            st.caption("Mortes registradas por ano")
            st.line_chart(tendencia, x="ano", y="mortes")
        st.dataframe(tendencia, hide_index=True, width="stretch")

with aba_dados:
    st.subheader("Resumo cruzado usado nos graficos")
    if dimensao_via == "tracado_via":
        st.caption(
            "A tabela inclui somente Reta, Curva, Aclive, Declive e "
            "Interseção de Vias; combinações de traçados foram excluídas."
        )
    st.dataframe(
        cruzamento.sort_values("acidentes", ascending=False),
        hide_index=True,
        width="stretch",
    )

st.caption(
    "Fontes: registros de acidentes da PRF e cadastro de trechos do DNIT. "
    f"Mortes por 100 acidentes no recorte atual: "
    f"{mortes_por_100_acidentes:.2f}. "
    f"Acidentes sem correspondencia com trecho DNIT: "
    f"{int(resumo['acidentes_sem_trecho']):,}."
)
