from pathlib import Path

import duckdb


RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / "dados" / "ouro" / "projeto.duckdb"
TABELA = "ouro.vw_acidente_completo"
TRACADOS_PRINCIPAIS = (
    "Reta",
    "Curva",
    "Aclive",
    "Declive",
    "Interseção de Vias",
)

DIMENSOES_VIA = {
    "Traçado da via": "tracado_via",
    "Tipo de pista": "tipo_pista",
    "Superfície do trecho (DNIT)": "superficie",
    "Administração (DNIT)": "administracao",
    "Trecho em obras (DNIT)": "em_obras",
    "Tipo de trecho (DNIT)": "tipo_de_trecho",
    "Unidade federativa": "uf",
}

CAMPOS_FILTRO = {
    "condicao_metereologica",
    "tipo_acidente",
    "classificacao_acidente",
    "causa_acidente",
    "tipo_pista",
    "tracado_via",
    "superficie",
    "administracao",
    "em_obras",
    "tipo_de_trecho",
    "uf",
    "periodo_dia",
    "dia_semana",
    "mes",
}


def _consultar(sql, parametros=None):
    with duckdb.connect(str(BANCO), read_only=True) as con:
        return con.execute(sql, parametros or []).fetchdf()


def anos_disponiveis():
    return _consultar(
        f"""
        SELECT DISTINCT ano
        FROM {TABELA}
        WHERE ano IS NOT NULL
        ORDER BY ano
        """
    )["ano"].tolist()


def _expressao_categoria(campo):
    if campo == "em_obras":
        return (
            "CASE WHEN em_obras IS TRUE THEN 'Sim' "
            "WHEN em_obras IS FALSE THEN 'Nao' "
            "ELSE 'Sem informacao' END"
        )
    return f"COALESCE(CAST({campo} AS VARCHAR), 'Sem informacao')"


def opcoes(campo):
    if campo not in CAMPOS_FILTRO:
        raise ValueError(f"Campo de filtro nao permitido: {campo}")

    if campo == "tracado_via":
        return ["Todos"] + list(TRACADOS_PRINCIPAIS)

    expressao = _expressao_categoria(campo)
    valores = _consultar(
        f"""
        SELECT DISTINCT {expressao} AS categoria
        FROM {TABELA}
        ORDER BY categoria
        """
    )["categoria"].tolist()
    return ["Todos"] + valores


def _where(ano_inicial, ano_final, filtros):
    condicoes = ["ano BETWEEN ? AND ?"]
    parametros = [ano_inicial, ano_final]

    for campo, valor in filtros.items():
        if campo not in CAMPOS_FILTRO:
            raise ValueError(f"Campo de filtro nao permitido: {campo}")
        if valor in (None, "Todos"):
            continue

        if campo == "em_obras":
            if valor == "Sem informacao":
                condicoes.append("em_obras IS NULL")
            else:
                condicoes.append("em_obras = ?")
                parametros.append(valor == "Sim")
        elif valor == "Sem informacao":
            condicoes.append(f"{campo} IS NULL")
        else:
            condicoes.append(f"{campo} = ?")
            parametros.append(valor)

    return " AND ".join(condicoes), parametros


def resumo(ano_inicial, ano_final, filtros):
    where, parametros = _where(ano_inicial, ano_final, filtros)
    return _consultar(
        f"""
        SELECT
            COUNT(*) AS acidentes,
            SUM(COALESCE(mortos, 0)) AS mortes,
            SUM(COALESCE(feridos_leves, 0) + COALESCE(feridos_graves, 0))
                AS feridos,
            SUM(CASE WHEN COALESCE(mortos, 0) > 0 THEN 1 ELSE 0 END)
                AS acidentes_com_mortes,
            COUNT(trecho_id) AS acidentes_com_trecho,
            COUNT(*) - COUNT(trecho_id) AS acidentes_sem_trecho
        FROM {TABELA}
        WHERE {where}
        """,
        parametros,
    ).iloc[0]


def comparativo(ano_inicial, ano_final, filtros, dimensao_via):
    if dimensao_via not in DIMENSOES_VIA.values():
        raise ValueError(f"Dimensao de via nao permitida: {dimensao_via}")

    where, parametros = _where(ano_inicial, ano_final, filtros)
    if dimensao_via == "tracado_via":
        placeholders = ", ".join("?" for _ in TRACADOS_PRINCIPAIS)
        where += f" AND tracado_via IN ({placeholders})"
        parametros.extend(TRACADOS_PRINCIPAIS)

    categoria_via = _expressao_categoria(dimensao_via)
    clima = _expressao_categoria("condicao_metereologica")
    return _consultar(
        f"""
        SELECT
            {categoria_via} AS categoria_via,
            {clima} AS clima,
            COUNT(*) AS acidentes,
            SUM(COALESCE(mortos, 0)) AS mortes,
            SUM(COALESCE(feridos_leves, 0) + COALESCE(feridos_graves, 0))
                AS feridos,
            SUM(CASE WHEN COALESCE(mortos, 0) > 0 THEN 1 ELSE 0 END)
                AS acidentes_com_mortes
        FROM {TABELA}
        WHERE {where}
        GROUP BY categoria_via, clima
        ORDER BY acidentes DESC
        """,
        parametros,
    )


def evolucao(ano_inicial, ano_final, filtros):
    where, parametros = _where(ano_inicial, ano_final, filtros)
    return _consultar(
        f"""
        SELECT
            ano,
            COUNT(*) AS acidentes,
            SUM(COALESCE(mortos, 0)) AS mortes,
            SUM(COALESCE(feridos_leves, 0) + COALESCE(feridos_graves, 0))
                AS feridos,
            SUM(CASE WHEN COALESCE(mortos, 0) > 0 THEN 1 ELSE 0 END)
                AS acidentes_com_mortes
        FROM {TABELA}
        WHERE {where}
        GROUP BY ano
        ORDER BY ano
        """,
        parametros,
    )
