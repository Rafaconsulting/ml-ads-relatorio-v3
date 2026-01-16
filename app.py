import streamlit as st
from datetime import datetime
import ml_report as ml


# --------------------------------------------------------------------
# Helpers de exibicao
# Padroniza colunas de dinheiro com prefixo "R$" sem alterar os dados.
# --------------------------------------------------------------------
import pandas as pd

def _is_money_col(col_name: str) -> bool:
    c = str(col_name).strip().lower()
    # casos comuns no app
    if "receita proj" in c:
        return True
    if "potencial_receita" in c or "potencial receita" in c:
        return True
    if "orcamento" in c or "orçamento" in c:
        return True
    if "investimento" in c:
        return True
    if "vendas_brutas" in c or "vendas brutas" in c:
        return True
    # evita pegar metricas que nao sao dinheiro
    if c == "receita" or c.startswith("receita "):
        return True
    return False


# Colunas que devem ser exibidas como percentual (na exibicao).
_PERCENT_COLS = {
    "acos real",
    "acos_real",
    "acos objetivo n",
    "acos_objetivo_n",
    "cpi_share",
    "cpi share",
    "cpi_cum",
    "cpi cum",
    "con_visitas_vendas",
    "con visitas vendas",
}

def _is_percent_col(col_name: str) -> bool:
    c = str(col_name).strip().lower()
    c = c.replace("__", "_")
    return c in _PERCENT_COLS


def show_df(df, **kwargs):
    """Mostra dataframe no Streamlit com padrao de exibicao:
    - Colunas de dinheiro com prefixo R$ e 2 casas.
    - Colunas percentuais (ACOS, CPI, Conversao) com % e 2 casas.
    Sem alterar os dados originais e evitando Styler em tabelas grandes.
    """
    _st_dataframe = st.dataframe

    # Se ja for um Styler, nao mexe
    try:
        from pandas.io.formats.style import Styler
        if isinstance(df, Styler):
            return _st_dataframe(df, **kwargs)
    except Exception:
        pass

    if df is None:
        return st.info("Sem dados para exibir.")

    if not isinstance(df, pd.DataFrame):
        return _st_dataframe(df, **kwargs)

    if df.empty:
        return _st_dataframe(df, **kwargs)

    _df = df.copy()

    money_cols = [c for c in _df.columns if _is_money_col(c)]
    percent_cols = [c for c in _df.columns if _is_percent_col(c)]

    # Converte percentuais so na exibicao:
    # Se vier como fracao (0 a 1.x), multiplica por 100.
    for c in percent_cols:
        ser = pd.to_numeric(_df[c], errors="coerce")
        try:
            vmax = ser.max(skipna=True)
            if pd.notna(vmax) and vmax <= 2:
                _df[c] = ser * 100
            else:
                _df[c] = ser
        except Exception:
            _df[c] = ser

    if not money_cols and not percent_cols:
        return _st_dataframe(_df, **kwargs)

    # Preferencia: column_config (mais leve e estavel)
    try:
        col_config = {}
        for c in money_cols:
            col_config[c] = st.column_config.NumberColumn(format="R$ %.2f")
        for c in percent_cols:
            col_config[c] = st.column_config.NumberColumn(format="%.2f%%")
        return _st_dataframe(_df, column_config=col_config, **kwargs)
    except Exception:
        # Fallback: Styler so para tabelas menores
        if _df.shape[0] <= 1500 and _df.shape[1] <= 40:
            fmt = {c: "R$ {:,.2f}" for c in money_cols}
            fmt.update({c: "{:.2f}%" for c in percent_cols})
            return _st_dataframe(_df.style.format(fmt), **kwargs)

        # Fallback final: converte so as colunas especiais para string (leve)
        for c in money_cols:
            _df[c] = pd.to_numeric(_df[c], errors="coerce")
            _df[c] = _df[c].map(lambda x: "" if pd.isna(x) else f"R$ {x:,.2f}")
        for c in percent_cols:
            _df[c] = pd.to_numeric(_df[c], errors="coerce")
            _df[c] = _df[c].map(lambda x: "" if pd.isna(x) else f"{x:.2f}%")
        return _st_dataframe(_df, **kwargs)

