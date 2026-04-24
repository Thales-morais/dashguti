import os
import json
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import date, timedelta
from dotenv import load_dotenv
from ddd_coords import DDD_INFO

load_dotenv()

SHEETS_CSV_URL = (
    "https://docs.google.com/spreadsheets/d/e/"
    "2PACX-1vTch090fHoZlOtOE7Q89ejnSsvfcOSqAJg5M4ZZG1ly5kYneptpVTuudvWvJkbE2l3gkAPa_lASvYlN"
    "/pub?gid=0&single=true&output=csv"
)

META_TOKEN   = os.getenv("META_ACCESS_TOKEN", "")
META_ACCOUNT = os.getenv("META_AD_ACCOUNT_ID", "")

SP_DDDS = {"11", "12", "13", "14", "15", "16", "17", "18", "19"}

st.set_page_config(
    page_title="Dashboard Guti",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 28px !important; }
    [data-testid="stMetricLabel"] { font-size: 13px !important; color: #aaa; }
</style>
""", unsafe_allow_html=True)


# ── dados ─────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_all_leads() -> pd.DataFrame:
    df = pd.read_csv(SHEETS_CSV_URL)
    df.columns = [c.strip().upper() for c in df.columns]

    if "DATA" in df.columns:
        df["DATA"] = pd.to_datetime(df["DATA"], errors="coerce", utc=True)
        df["DATA"] = df["DATA"].dt.tz_localize(None)

    if "TELEFONE" in df.columns:
        tel = df["TELEFONE"].fillna("").astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
        df["DDD"] = tel.apply(
            lambda t: t[2:4] if isinstance(t, str) and t.startswith("55") and len(t) >= 4 else None
        )

    return df


@st.cache_data(ttl=300)
def get_meta_spend(since: str, until: str) -> float | None:
    if not META_TOKEN or not META_ACCOUNT:
        return None
    url = f"https://graph.facebook.com/v19.0/act_{META_ACCOUNT}/insights"
    params = {
        "fields": "spend",
        "time_range": json.dumps({"since": since, "until": until}),
        "access_token": META_TOKEN,
        "level": "account",
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        if "data" in data and data["data"]:
            return float(data["data"][0].get("spend", 0))
    except Exception:
        pass
    return None


def fmt_brl(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ── gráficos ──────────────────────────────────────────────────────────────────
def build_map_sp(df: pd.DataFrame) -> go.Figure:
    """Mapa do estado de SP com bolhas por DDD."""
    if "DDD" not in df.columns or df.empty:
        return go.Figure()

    df_sp = df[df["DDD"].isin(SP_DDDS)]
    if df_sp.empty:
        return go.Figure()

    counts = df_sp["DDD"].astype(str).value_counts().reset_index()
    counts.columns = ["DDD", "leads"]

    rows = []
    for _, row in counts.iterrows():
        info = DDD_INFO.get(row["DDD"])
        if info:
            rows.append({
                "DDD": row["DDD"],
                "leads": row["leads"],
                "lat": info["lat"],
                "lon": info["lon"],
                "label": f"DDD {row['DDD']} — {info['cidade']}<br>{row['leads']:,} leads",
            })

    if not rows:
        return go.Figure()

    map_df = pd.DataFrame(rows)
    fig = px.scatter_mapbox(
        map_df,
        lat="lat", lon="lon",
        size="leads", color="leads",
        hover_name="label",
        hover_data={"lat": False, "lon": False, "leads": True},
        color_continuous_scale="Oranges",
        size_max=70,
        zoom=5.8,
        center={"lat": -22.2, "lon": -48.8},
        mapbox_style="carto-darkmatter",
        labels={"leads": "Leads"},
    )
    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        coloraxis_showscale=False,
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def build_bar_ddd(df: pd.DataFrame, top_n: int = 20) -> go.Figure:
    if "DDD" not in df.columns or df.empty:
        return go.Figure()

    counts = (
        df["DDD"].dropna().astype(str).str.zfill(2)
        .value_counts().head(top_n).reset_index()
    )
    counts.columns = ["DDD", "leads"]
    counts["label"] = counts["DDD"].map(
        lambda d: f"{d} · {DDD_INFO[d]['cidade']}" if d in DDD_INFO else d
    )
    counts = counts.sort_values("leads", ascending=True)

    fig = px.bar(
        counts, x="leads", y="label", orientation="h",
        color="leads", color_continuous_scale="Oranges",
        labels={"leads": "Leads", "label": "DDD"},
    )
    fig.update_layout(
        margin={"r": 10, "t": 10, "l": 10, "b": 10},
        coloraxis_showscale=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#ccc",
        yaxis=dict(tickfont=dict(size=11)),
        xaxis=dict(gridcolor="#2e2e3e"),
    )
    return fig


def build_line_daily(df: pd.DataFrame) -> go.Figure:
    if "DATA" not in df.columns or df.empty:
        return go.Figure()

    daily = df.dropna(subset=["DATA"]).copy()
    daily["dia"] = daily["DATA"].dt.date
    daily = daily.groupby("dia").size().reset_index(name="leads")

    fig = px.area(
        daily, x="dia", y="leads",
        labels={"dia": "Data", "leads": "Leads"},
        color_discrete_sequence=["#f97316"],
    )
    fig.update_traces(fillcolor="rgba(249,115,22,0.15)", line_color="#f97316")
    fig.update_layout(
        margin={"r": 10, "t": 10, "l": 10, "b": 10},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#ccc",
        xaxis=dict(gridcolor="#2e2e3e"),
        yaxis=dict(gridcolor="#2e2e3e"),
    )
    return fig


# ── sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 DashGuti")
    st.markdown("---")
    st.markdown("### Período")

    hoje = date.today()

    periodo = st.radio(
        "Selecione",
        ["Hoje", "7 dias", "30 dias", "Total", "Personalizado"],
        index=2,
        label_visibility="collapsed",
    )

    if periodo == "Hoje":
        data_ini, data_fim = hoje, hoje
    elif periodo == "7 dias":
        data_ini, data_fim = hoje - timedelta(days=7), hoje
    elif periodo == "30 dias":
        data_ini, data_fim = hoje - timedelta(days=30), hoje
    elif periodo == "Total":
        data_ini, data_fim = date(2020, 1, 1), hoje
    else:
        st.markdown("**De / Até**")
        col_a, col_b = st.columns(2)
        with col_a:
            data_ini = st.date_input("De", value=hoje - timedelta(days=30), label_visibility="collapsed")
        with col_b:
            data_fim = st.date_input("Até", value=hoje, label_visibility="collapsed")

    st.markdown("---")
    st.caption("Dados atualizados a cada 60s")
    if st.button("🔄 Atualizar agora"):
        st.cache_data.clear()
        st.rerun()


# ── carrega dados ─────────────────────────────────────────────────────────────
since_str = data_ini.strftime("%Y-%m-%d")
until_str = data_fim.strftime("%Y-%m-%d")

with st.spinner("Carregando dados..."):
    try:
        df_all = load_all_leads()
        erro = None
    except Exception as e:
        df_all = pd.DataFrame()
        erro = str(e)

if erro:
    st.error(f"Erro ao carregar planilha: {erro}")
    st.stop()

# filtra por período
if "DATA" in df_all.columns and not df_all.empty:
    mask = (df_all["DATA"].dt.date >= data_ini) & (df_all["DATA"].dt.date <= data_fim)
    df = df_all[mask].copy()
else:
    df = df_all.copy()


# ── tabs ──────────────────────────────────────────────────────────────────────
tab_geral, tab_leads = st.tabs(["🗺️  Geral", "📋  Leads"])


# ──────────────────────────────────────────────────────────────────────────────
# TAB GERAL
# ──────────────────────────────────────────────────────────────────────────────
with tab_geral:
    st.markdown("## Visão Geral — Trampah")

    total_leads  = len(df)
    leads_sp     = df["DDD"].isin(SP_DDDS).sum() if "DDD" in df.columns else 0
    valor_gasto  = get_meta_spend(since_str, until_str)
    cpl = (valor_gasto / total_leads) if (valor_gasto and total_leads > 0) else None

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("Total de Leads", f"{total_leads:,}".replace(",", "."))
    with k2:
        if valor_gasto is not None:
            st.metric("Valor Gasto (Meta)", fmt_brl(valor_gasto))
        else:
            st.metric("Valor Gasto (Meta)", "—")
    with k3:
        if cpl is not None:
            st.metric("Custo por Lead (CPL)", fmt_brl(cpl))
        else:
            st.metric("Custo por Lead (CPL)", "—")
    with k4:
        st.metric("Leads em SP", f"{leads_sp:,}".replace(",", "."))

    st.markdown("---")

    if df.empty:
        st.info("Nenhum lead encontrado no período selecionado.")
        st.stop()

    # Mapa SP + Barra DDDs
    col_map, col_bar = st.columns([3, 2])
    with col_map:
        st.markdown("#### Mapa — Estado de São Paulo por DDD")
        st.plotly_chart(build_map_sp(df), use_container_width=True, config={"displayModeBar": False})
    with col_bar:
        st.markdown("#### Top DDDs (todos os estados)")
        st.plotly_chart(build_bar_ddd(df), use_container_width=True, config={"displayModeBar": False})

    # Linha diária
    st.markdown("#### Leads por dia")
    st.plotly_chart(build_line_daily(df), use_container_width=True, config={"displayModeBar": False})

    # Tabela resumo
    if "DDD" in df.columns:
        st.markdown("#### Resumo por DDD")
        resumo = (
            df["DDD"].dropna().astype(str).str.zfill(2)
            .value_counts().reset_index()
            .rename(columns={"DDD": "DDD", "count": "Leads"})
        )
        resumo["Cidade"] = resumo["DDD"].map(lambda d: DDD_INFO.get(d, {}).get("cidade", "—"))
        resumo["Estado"] = resumo["DDD"].map(lambda d: DDD_INFO.get(d, {}).get("estado", "—"))
        resumo["% do total"] = (resumo["Leads"] / total_leads * 100).round(1).astype(str) + "%"
        st.dataframe(
            resumo[["DDD", "Cidade", "Estado", "Leads", "% do total"]],
            use_container_width=True, hide_index=True,
        )


# ──────────────────────────────────────────────────────────────────────────────
# TAB LEADS
# ──────────────────────────────────────────────────────────────────────────────
with tab_leads:
    st.markdown("## Lista de Leads — Trampah")

    if df.empty:
        st.info("Nenhum lead no período.")
    else:
        search = st.text_input("Buscar por nome ou e-mail", placeholder="Digite para filtrar...")
        df_show = df.copy()
        if search:
            mask = (
                df_show.get("NOME", pd.Series(dtype=str)).str.contains(search, case=False, na=False)
                | df_show.get("EMAIL", pd.Series(dtype=str)).str.contains(search, case=False, na=False)
            )
            df_show = df_show[mask]

        cols_show = [c for c in ["DATA", "NOME", "EMAIL", "TELEFONE", "DDD", "FONTE"] if c in df_show.columns]
        st.dataframe(df_show[cols_show], use_container_width=True, hide_index=True)
        st.caption(f"{len(df_show):,} registros exibidos")
