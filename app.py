import streamlit as st
from datetime import datetime
import inspect
import pandas as pd


# --------------------------------------------------------------------
# Helpers de exibicao
# Padroniza dinheiro com "R$" e percentuais com "%", sem alterar a fonte.
# --------------------------------------------------------------------
def _is_money_col(col_name: str) -> bool:
    c = str(col_name).strip().lower()
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
    if c == "receita" or c.startswith("receita "):
        return True
    return False


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
    c = str(col_name).strip().lower().replace("__", "_")
    return c in _PERCENT_COLS


def _dataframe_accepts_column_config() -> bool:
    try:
        sig = inspect.signature(st.dataframe)
        return "column_config" in sig.parameters
    except Exception:
        return False


def show_df(df, **kwargs):
    """
    Exibe dataframe no Streamlit com padrao:
    - Dinheiro: R$ e 2 casas
    - Percentuais: % e 2 casas (ACOS, CPI, Con_Visitas_Vendas)
    Sem alterar os dados originais e evitando travar o app.
    """
    kwargs.pop("column_config", None)
    _st_dataframe = st.dataframe

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

    # Se percentuais vierem como fracao (0 a 1.x), converte para 0 a 100 na exibicao
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

    n_rows, n_cols = _df.shape
    n_special = len(money_cols) + len(percent_cols)

    # Preferencia: column_config (quando suportado)
    if (
        _dataframe_accepts_column_config()
        and n_rows <= 5000
        and n_cols <= 60
        and n_special <= 30
    ):
        try:
            col_config = {}
            for c in money_cols:
                col_config[c] = st.column_config.NumberColumn(format="R$ %.2f")
            for c in percent_cols:
                col_config[c] = st.column_config.NumberColumn(format="%.2f%%")
            return _st_dataframe(_df, column_config=col_config, **kwargs)
        except Exception:
            pass

    # Fallback: Styler so para tabelas menores
    if n_rows <= 1500 and n_cols <= 40:
        try:
            fmt = {c: "R$ {:,.2f}" for c in money_cols}
            fmt.update({c: "{:.2f}%" for c in percent_cols})
            return _st_dataframe(_df.style.format(fmt), **kwargs)
        except Exception:
            pass

    # Fallback final: converte somente as colunas especiais para string
    for c in money_cols:
        _df[c] = pd.to_numeric(_df[c], errors="coerce")
        _df[c] = _df[c].map(lambda x: "" if pd.isna(x) else f"R$ {x:,.2f}")
    for c in percent_cols:
        _df[c] = pd.to_numeric(_df[c], errors="coerce")
        _df[c] = _df[c].map(lambda x: "" if pd.isna(x) else f"{x:.2f}%")

    return _st_dataframe(_df, **kwargs)


# --------------------------------------------------------------------
# App
# --------------------------------------------------------------------
def _call_ml_entrypoint(ml):
    """
    Tenta chamar um entrypoint do ml_report sem quebrar o app.
    Ajuda quando voce nao tem certeza do nome da funcao principal.
    """
    candidates = [
        "main",
        "run",
        "app",
        "render",
        "render_app",
        "build_app",
    ]

    for name in candidates:
        fn = getattr(ml, name, None)
        if callable(fn):
            # tenta passar show_df se a funcao aceitar
            try:
                sig = inspect.signature(fn)
                if "show_df" in sig.parameters:
                    return fn(show_df=show_df)
                return fn()
            except TypeError:
                # assinatura inesperada, tenta chamada simples
                try:
                    return fn()
                except Exception:
                    raise

    # Se nao achou nada, informa o usuario e lista o que tem no modulo
    public = [x for x in dir(ml) if not x.startswith("_")]
    st.error("Nao encontrei funcao principal no ml_report para iniciar o app.")
    st.write("Funcoes/objetos disponiveis em ml_report:")
    st.code("\n".join(public))


def main():
    st.set_page_config(page_title="MelieADs", layout="wide")
    st.title("Mercado Livre Ads - Dashboard e Relatorio")

    with st.sidebar:
        st.caption(f"Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        st.divider()
        st.write("Se o app travar ao carregar, o erro costuma estar em import circular no ml_report.")
        st.divider()

    # Import tardio para evitar import circular e travamento na inicializacao
    try:
        import ml_report as ml
    except Exception as e:
        st.error("Falha ao importar ml_report. Isso normalmente indica import circular ou erro no modulo.")
        st.exception(e)
        return

    try:
        _call_ml_entrypoint(ml)
    except Exception as e:
        st.error("O app iniciou, mas houve erro ao executar o ml_report.")
        st.exception(e)


if __name__ == "__main__":
    main()
