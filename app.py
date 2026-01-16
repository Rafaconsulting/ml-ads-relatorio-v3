import streamlit as st
import pandas as pd
from datetime import datetime

import ml_report as ml


# -------------------------
# Formatadores BR
# -------------------------
def fmt_money_br(x):
    if pd.isna(x):
        return ""
    return f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_percent_br(x):
    if pd.isna(x):
        return ""
    return f"{x:.2f}%".replace(".", ",")


def fmt_number_br(x, decimals=2):
    if pd.isna(x):
        return ""
    return f"{x:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_int_br(x):
    if pd.isna(x):
        return ""
    return f"{int(round(x)):,}".replace(",", ".")


# -------------------------
# Detectores de colunas
# -------------------------
def _is_money_col(col_name: str) -> bool:
    c = str(col_name).strip().lower()
    money_keys = [
        "orcamento",
        "orçamento",
        "investimento",
        "receita",
        "vendas_brutas",
        "potencial_receita",
        "potencial receita",
        "faturamento",
        "vendas (r$)",
    ]
    return any(k in c for k in money_keys)


def _is_count_col(col_name: str) -> bool:
    """
    Colunas que representam volume/contagem
    """
    c = str(col_name).strip().lower()
    count_keys = [
        "impress",
        "clique",
        "click",
        "visita",
        "qtd",
        "quant",
        "venda",
        "orders",
        "pedidos",
    ]
    return any(k in c for k in count_keys)


_PERCENT_COLS = {
    "acos real",
    "acos_real",
    "cpi_share",
    "cpi share",
    "cpi_cum",
    "cpi cum",
    "con_visitas_vendas",
    "con visitas vendas",
    "conv_visitas_vendas",
    "conv visitas vendas",
    "conv_visitas_compradores",
    "conv visitas compradores",
    "perdidas_orc",
    "perdidas_class",
    "cvr",
    "cvr\n(conversion rate)",
}


def _is_percent_col(col_name: str) -> bool:
    c = str(col_name).strip().lower().replace("__", "_")
    return c in _PERCENT_COLS


# -------------------------
# ACOS objetivo -> ROAS objetivo
# -------------------------
def _acos_value_to_roas(ac):
    if pd.isna(ac):
        return pd.NA
    try:
        v = float(ac)
    except Exception:
        return pd.NA

    if v == 0:
        return pd.NA

    acos_frac = v / 100 if v > 2 else v
    if acos_frac <= 0:
        return pd.NA

    return 1 / acos_frac


def _roas_col_name_from_acos_col(col_name: str) -> str:
    lc = str(col_name).strip().lower().replace("__", "_")
    if lc.endswith("_n") or "objetivo_n" in lc or "objetivo n" in lc:
        return "ROAS objetivo N"
    return "ROAS objetivo"


def replace_acos_obj_with_roas_obj(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return df

    df2 = df.copy()
    renames = {}

    for col in list(df2.columns):
        lc = str(col).strip().lower()
        if "acos" in lc and "objetivo" in lc:
            ser = pd.to_numeric(df2[col], errors="coerce")
            df2[col] = ser.map(_acos_value_to_roas)
            renames[col] = _roas_col_name_from_acos_col(col)

    if renames:
        df2 = df2.rename(columns=renames)

    return df2


# -------------------------
# Formatação unificada (Painel, CPI, Ações)
# -------------------------
def format_table_br(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return df

    df_fmt = df.copy()

    for col in df_fmt.columns:
        lc = str(col).strip().lower()

        # preserva texto
        if (
            "nome" in lc
            or "campanha" in lc
            or "acao" in lc
            or "ação" in lc
            or "recomend" in lc
            or "estrateg" in lc
        ):
            df_fmt[col] = df_fmt[col].astype(str).replace({"nan": ""})
            continue

        serie_num = pd.to_numeric(df_fmt[col], errors="coerce")
        non_null = df_fmt[col].notna().sum()
        num_ok = serie_num.notna().sum()

        if non_null == 0 or (num_ok / max(non_null, 1)) < 0.60:
            df_fmt[col] = df_fmt[col].astype(str).replace({"nan": ""})
            continue

        # regras de formatação
        if _is_money_col(col):
            df_fmt[col] = serie_num.map(fmt_money_br)

        elif _is_count_col(col):
            df_fmt[col] = serie_num.map(fmt_int_br)

        elif _is_percent_col(col):
            vmax = serie_num.max(skipna=True)
            if pd.notna(vmax) and vmax <= 2:
                serie_num = serie_num * 100
            df_fmt[col] = serie_num.map(fmt_percent_br)

        else:
            df_fmt[col] = serie_num.map(lambda x: fmt_number_br(x, 2))

    return df_fmt


# -------------------------
# App
# -------------------------
def main():
    st.set_page_config(page_title="Mercado Livre Ads", layout="wide")
    st.title("Mercado Livre Ads - Dashboard e Relatório")

    with st.sidebar:
        st.caption(f"Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        st.divider()

        st.subheader("Arquivos")
        organico_file = st.file_uploader("Relatório de Desempenho de Vendas (Excel)", type=["xlsx"])
        patrocinados_file = st.file_uploader("Relatório Anúncios Patrocinados (Excel)", type=["xlsx"])
        campanhas_file = st.file_uploader("Relatório de Campanha (Excel)", type=["xlsx"])

        st.divider()
        st.subheader("Filtros de regra")

        enter_visitas_min = st.number_input("Entrar em Ads: visitas mín", min_value=0, value=50, step=10)
        enter_conv_min_pct = st.number_input("Entrar em Ads: conversão mín (%)", min_value=0.0, value=5.0, step=0.5)
        pause_invest_min = st.number_input("Pausar: investimento mín (R$)", min_value=0.0, value=100.0, step=50.0)
        pause_cvr_max_pct = st.number_input("Pausar: CVR máx (%)", min_value=0.0, value=1.0, step=0.5)

        enter_conv_min = enter_conv_min_pct / 100
        pause_cvr_max = pause_cvr_max_pct / 100

        st.divider()
        executar = st.button("Gerar relatório", use_container_width=True)

    if not (organico_file and patrocinados_file and campanhas_file):
        st.info("Envie os 3 arquivos na barra lateral para liberar o relatório.")
        return

    if not executar:
        st.warning("Quando estiver pronto, clique em Gerar relatório.")
        return

    org = ml.load_organico(organico_file)
    pat = ml.load_patrocinados(patrocinados_file)

    camp_raw = ml.load_campanhas_consolidado(campanhas_file)
    camp_agg = ml.build_campaign_agg(camp_raw, modo="consolidado")

    kpis, pause, enter, scale, acos, camp_strat = ml.build_tables(
        org=org,
        camp_agg=camp_agg,
        pat=pat,
        enter_visitas_min=int(enter_visitas_min),
        enter_conv_min=float(enter_conv_min),
        pause_invest_min=float(pause_invest_min),
        pause_cvr_max=float(pause_cvr_max),
    )

    st.success("Relatório gerado com sucesso.")

    # Painel Geral
    st.subheader("Painel geral")
    panel_fmt = format_table_br(replace_acos_obj_with_roas_obj(ml.build_control_panel(camp_strat)))
    st.dataframe(panel_fmt, use_container_width=True)

    # Matriz CPI
    st.subheader("Matriz CPI")
    st.dataframe(format_table_br(replace_acos_obj_with_roas_obj(camp_strat)), use_container_width=True)

    # Ações
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Pausar ou revisar")
        st.dataframe(format_table_br(replace_acos_obj_with_roas_obj(pause)), use_container_width=True)
    with c2:
        st.subheader("Entrar em Ads")
        st.dataframe(format_table_br(replace_acos_obj_with_roas_obj(enter)), use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        st.subheader("Escalar orçamento")
        st.dataframe(format_table_br(replace_acos_obj_with_roas_obj(scale)), use_container_width=True)
    with c4:
        st.subheader("Subir ROAS objetivo")
        st.dataframe(format_table_br(replace_acos_obj_with_roas_obj(acos)), use_container_width=True)


if __name__ == "__main__":
    main()
