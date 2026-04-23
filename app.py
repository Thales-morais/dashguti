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

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
META_TOKEN = os.getenv("META_ACCESS_TOKEN", "")
META_ACCOUNT = os.getenv("META_AD_ACCOUNT_ID", "")

st.set_page_config(
    page_title="Dashboard Guti",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── estilos ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .kpi-card {
        background: #1e1e2e;
        border-radius: 12px;
        padding: 20px 24px;
        text-align: center;
        border: 1px solid #2e2e3e;
    }
    .kpi-label { color: #aaa; font-size: 13px; margin-bottom: 4px; }
    .kpi-value { color: #fff; font-size: 32px; font-weight: 700; }
    .kpi-sub   { color: #666; font-size: 11px; margin-top: 2px; }
    [data-testid="stMetricValue"] { font-size: 28px !important; }
</style>
""", unsafe_allow_html=True)


# ── helpers de dados ──────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_leads(table: str, since: str, until: str) -> pd.DataFrame:
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    url = (
        f"{SUPABASE_URL}/rest/v1/{table}"
        f'?select=*&"DATA"=gte.{since}T00:00:00&"DATA"=lte.{until}T23:59:59'
        f"&order=DATA.desc&limit=50000"
    )
    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    df = pd.DataFrame(r.json())
    if df.empty:
        return df
    if "DATA" in df.columns:
        df["DATA"] = pd.to_datetime(df["DATA"], errors="coerce")
    return df


@st.cache_data(ttl=300)
def get_meta_spend(since: str, until: str) -> float:
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


def build_map(df: pd.DataFrame) -> go.Figure:
    if "DDD" not in df.columns or df.empty:
        return go.Figure()

    ddd_counts = df["DDD"].value_counts().reset_index()
    ddd_counts.columns = ["DDD", "leads"]
    ddd_counts["DDD"] = ddd_counts["DDD"].astype(str).str.zfill(2)

    rows = []
    for _, row in ddd_counts.iterrows():
        info = DDD_INFO.get(row["DDD"])
        if info:
            rows.append({
                "DDD": row["DDD"],
                "leads": row["leads"],
                "lat": info["lat"],
                "lon": info["lon"],
                "cidade": info["cidade"],
                "estado": info["estado"],
                "label": f"DDD {row['DDD']} — {info['cidade']}<br>{row['leads']:,} leads",
            })

    if not rows:
        return go.Figure()

    map_df = pd.DataFrame(rows)

    fig = px.scatter_mapbox(
        map_df,
        lat="lat",
        lon="lon",
        size="leads",
        color="leads",
        hover_name="label",
        hover_data={"lat": False, "lon": False, "leads": True, "estado": True},
        color_continuous_scale="Oranges",
        size_max=60,
        zoom=4,
        center={"lat": -15.0, "lon": -50.0},
        mapbox_style="carto-darkmatter",
        labels={"leads": "Leads", "estado": "Estado"},
    )
    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        coloraxis_showscale=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def build_bar_ddd(df: pd.DataFrame, top_n: int = 20) -> go.Figure:
    if "DDD" not in df.columns or df.empty:
        return go.Figure()
    counts = (
        df["DDD"].astype(str).str.zfill(2).value_counts()
        .head(top_n).reset_index()
    )
    counts.columns = ["DDD", "leads"]
    counts["label"] = counts["DDD"].map(
        lambda d: f"{d} · {DDD_INFO[d]['cidade']}" if d in DDD_INFO else d
    )
    counts = counts.sort_values("leads", ascending=True)

    fig = px.bar(
        counts,
        x="leads",
        y="label",
        orientation="h",
        color="leads",
        color_continuous_scale="Oranges",
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
        daily,
        x="dia",
        y="leads",
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
    st.image("https://via.placeholder.com/160x40/1e1e2e/f97316?text=DASHGUTI", width=160)
    st.markdown("---")
    st.markdown("### Filtros")

    hoje = date.today()
    ini_default = hoje.replace(day=1)

    col_a, col_b = st.columns(2)
    with col_a:
        data_ini = st.date_input("De", value=ini_default, key="d_ini")
    with col_b:
        data_fim = st.date_input("Até", value=hoje, key="d_fim")

    st.markdown("---")
    st.caption("Atualiza automaticamente a cada 60s")
    if st.button("Atualizar agora"):
        st.cache_data.clear()
        st.rerun()


# ── tabs ──────────────────────────────────────────────────────────────────────
tab_geral, tab_leads = st.tabs(["🗺️  Geral", "📋  Leads"])

since_str = data_ini.strftime("%Y-%m-%d")
until_str = data_fim.strftime("%Y-%m-%d")

# ──────────────────────────────────────────────────────────────────────────────
# TAB GERAL
# ──────────────────────────────────────────────────────────────────────────────
with tab_geral:
    st.markdown("## Visão Geral — Trampah")

    with st.spinner("Carregando dados..."):
        try:
            df = load_leads("lead_guti_trampah", since_str, until_str)
            erro_dados = None
        except Exception as e:
            df = pd.DataFrame()
            erro_dados = str(e)

    if erro_dados:
        st.error(f"Erro ao conectar no Supabase: {erro_dados}")
        st.stop()

    total_leads = len(df)
    valor_gasto = get_meta_spend(since_str, until_str)
    cpl = (valor_gasto / total_leads) if (valor_gasto and total_leads > 0) else None

    # ── KPIs ──────────────────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)

    with k1:
        st.metric("Total de Leads", f"{total_leads:,}".replace(",", "."))

    with k2:
        if valor_gasto is not None:
            st.metric("Valor Gasto (Meta)", fmt_brl(valor_gasto))
        else:
            st.metric("Valor Gasto (Meta)", "—")
            st.caption("Configure META_ACCESS_TOKEN no .env")

    with k3:
        if cpl is not None:
            st.metric("Custo por Lead (CPL)", fmt_brl(cpl))
        else:
            st.metric("Custo por Lead (CPL)", "—")

    with k4:
        fontes = df["FONTE"].nunique() if "FONTE" in df.columns else 0
        st.metric("Fontes ativas", fontes)

    st.markdown("---")

    if df.empty:
        st.info("Nenhum lead encontrado no período selecionado.")
        st.stop()

    # ── mapa + barra ──────────────────────────────────────────────────────────
    col_map, col_bar = st.columns([3, 2])

    with col_map:
        st.markdown("#### Distribuição por DDD")
        fig_map = build_map(df)
        st.plotly_chart(fig_map, use_container_width=True, config={"displayModeBar": False})

    with col_bar:
        st.markdown("#### Top DDDs")
        fig_bar = build_bar_ddd(df)
        st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})

    # ── linha diária ──────────────────────────────────────────────────────────
    st.markdown("#### Leads por dia")
    fig_line = build_line_daily(df)
    st.plotly_chart(fig_line, use_container_width=True, config={"displayModeBar": False})

    # ── tabela de DDDs ────────────────────────────────────────────────────────
    if "DDD" in df.columns:
        st.markdown("#### Resumo por DDD")
        resumo = (
            df["DDD"].astype(str).str.zfill(2).value_counts()
            .reset_index()
            .rename(columns={"DDD": "DDD", "count": "Leads"})
        )
        resumo["Cidade"] = resumo["DDD"].map(
            lambda d: DDD_INFO[d]["cidade"] if d in DDD_INFO else "—"
        )
        resumo["Estado"] = resumo["DDD"].map(
            lambda d: DDD_INFO[d]["estado"] if d in DDD_INFO else "—"
        )
        resumo["% do total"] = (resumo["Leads"] / total_leads * 100).round(1).astype(str) + "%"
        st.dataframe(
            resumo[["DDD", "Cidade", "Estado", "Leads", "% do total"]],
            use_container_width=True,
            hide_index=True,
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
