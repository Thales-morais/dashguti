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
SP_DDDS      = {"11", "12", "13", "14", "15", "16", "17", "18", "19"}

st.set_page_config(
    page_title="DashGuti",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  /* fundo geral */
  .stApp { background-color: #0d1117; }
  section[data-testid="stSidebar"] { background-color: #0d1117; border-right: 1px solid #21262d; }

  /* remove padding padrão do main */
  .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }

  /* KPI card */
  .kpi-card {
    background: linear-gradient(135deg, #161b22 0%, #1c2333 100%);
    border: 1px solid #30363d;
    border-radius: 14px;
    padding: 22px 24px 18px 24px;
    text-align: center;
    transition: border-color .2s;
  }
  .kpi-card:hover { border-color: #f97316; }
  .kpi-icon  { font-size: 22px; margin-bottom: 6px; }
  .kpi-label { color: #8b949e; font-size: 12px; font-weight: 500;
               letter-spacing: .06em; text-transform: uppercase; margin-bottom: 6px; }
  .kpi-value { color: #f0f6fc; font-size: 34px; font-weight: 700; line-height: 1.1; }
  .kpi-sub   { color: #f97316; font-size: 12px; margin-top: 4px; }

  /* section title */
  .section-title {
    color: #8b949e; font-size: 11px; font-weight: 600;
    letter-spacing: .1em; text-transform: uppercase;
    border-left: 3px solid #f97316; padding-left: 10px;
    margin: 24px 0 12px 0;
  }

  /* chart card */
  .chart-card {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 14px;
    padding: 20px;
  }

  /* sidebar radio */
  .stRadio label { color: #c9d1d9 !important; font-size: 14px !important; }
  div[data-testid="stRadio"] > label { color: #8b949e !important; }

  /* tabs */
  .stTabs [data-baseweb="tab-list"] { background: #161b22; border-radius: 10px; padding: 4px; }
  .stTabs [data-baseweb="tab"] { color: #8b949e !important; border-radius: 8px; }
  .stTabs [aria-selected="true"] { background: #21262d !important; color: #f0f6fc !important; }

  /* dataframe */
  .stDataFrame { border-radius: 10px; overflow: hidden; }

  /* botão */
  .stButton > button {
    background: #21262d; color: #c9d1d9; border: 1px solid #30363d;
    border-radius: 8px; width: 100%; font-size: 13px;
  }
  .stButton > button:hover { border-color: #f97316; color: #f97316; }
</style>
""", unsafe_allow_html=True)


# ── dados ─────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_all_leads() -> pd.DataFrame:
    df = pd.read_csv(SHEETS_CSV_URL)
    df.columns = [c.strip().upper() for c in df.columns]

    if "DATA" in df.columns:
        data_str = df["DATA"].astype(str).str.extract(
            r"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})"
        )[0]
        df["DATA"] = pd.to_datetime(data_str, errors="coerce")
        if hasattr(df["DATA"].dtype, "tz") and df["DATA"].dt.tz is not None:
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

def fmt_num(v: int) -> str:
    return f"{v:,}".replace(",", ".")

def kpi_card(icon: str, label: str, value: str, sub: str = "") -> str:
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    return f"""
    <div class="kpi-card">
      <div class="kpi-icon">{icon}</div>
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{value}</div>
      {sub_html}
    </div>"""


# ── gráficos ──────────────────────────────────────────────────────────────────
def build_map_sp(df: pd.DataFrame) -> go.Figure:
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
                "leads": int(row["leads"]),
                "lat": info["lat"],
                "lon": info["lon"],
                "cidade": info["cidade"],
            })

    if not rows:
        return go.Figure()

    map_df = pd.DataFrame(rows)
    max_leads = map_df["leads"].max()

    fig = go.Figure()

    # bolhas
    fig.add_trace(go.Scattermapbox(
        lat=map_df["lat"],
        lon=map_df["lon"],
        mode="markers",
        marker=dict(
            size=map_df["leads"] / max_leads * 55 + 18,
            color=map_df["leads"],
            colorscale=[[0, "#7c3aed"], [0.5, "#f97316"], [1, "#ef4444"]],
            opacity=0.85,
            showscale=False,
        ),
        text=map_df.apply(
            lambda r: f"<b>DDD {r['DDD']} — {r['cidade']}</b><br>{r['leads']:,} leads", axis=1
        ),
        hoverinfo="text",
        name="",
    ))

    # labels DDD
    fig.add_trace(go.Scattermapbox(
        lat=map_df["lat"],
        lon=map_df["lon"],
        mode="text",
        text=map_df["DDD"],
        textfont=dict(size=11, color="#ffffff"),
        hoverinfo="skip",
        name="",
    ))

    fig.update_layout(
        mapbox=dict(
            style="carto-darkmatter",
            center={"lat": -22.2, "lon": -48.8},
            zoom=5.8,
        ),
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        height=420,
    )
    return fig


def build_bar_ddd(df: pd.DataFrame, top_n: int = 15) -> go.Figure:
    if "DDD" not in df.columns or df.empty:
        return go.Figure()

    counts = (
        df["DDD"].dropna().astype(str).str.zfill(2)
        .value_counts().head(top_n).reset_index()
    )
    counts.columns = ["DDD", "leads"]
    counts["label"] = counts["DDD"].map(
        lambda d: f"DDD {d} · {DDD_INFO[d]['cidade']}" if d in DDD_INFO else f"DDD {d}"
    )
    counts = counts.sort_values("leads", ascending=True)

    fig = go.Figure(go.Bar(
        x=counts["leads"],
        y=counts["label"],
        orientation="h",
        marker=dict(
            color=counts["leads"],
            colorscale=[[0, "#7c3aed"], [1, "#f97316"]],
            showscale=False,
        ),
        text=counts["leads"].apply(lambda v: f"{v:,}".replace(",", ".")),
        textposition="outside",
        textfont=dict(color="#8b949e", size=11),
    ))
    fig.update_layout(
        margin={"r": 40, "t": 10, "l": 10, "b": 10},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#c9d1d9",
        height=420,
        yaxis=dict(tickfont=dict(size=11), gridcolor="#21262d"),
        xaxis=dict(gridcolor="#21262d", zeroline=False),
    )
    return fig


def build_line_daily(df: pd.DataFrame) -> go.Figure:
    if "DATA" not in df.columns or df.empty:
        return go.Figure()

    daily = df.dropna(subset=["DATA"]).copy()
    daily["dia"] = daily["DATA"].dt.date
    daily = daily.groupby("dia").size().reset_index(name="leads")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily["dia"],
        y=daily["leads"],
        mode="lines",
        fill="tozeroy",
        line=dict(color="#f97316", width=2),
        fillcolor="rgba(249,115,22,0.12)",
        hovertemplate="%{x}<br><b>%{y} leads</b><extra></extra>",
    ))
    fig.update_layout(
        margin={"r": 10, "t": 10, "l": 10, "b": 10},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#c9d1d9",
        height=220,
        xaxis=dict(gridcolor="#21262d", showline=False, tickformat="%d/%m"),
        yaxis=dict(gridcolor="#21262d", showline=False),
        hovermode="x unified",
    )
    return fig


# ── sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<h2 style="color:#f0f6fc;margin:0 0 4px 0;">📊 DashGuti</h2>'
        '<p style="color:#8b949e;font-size:12px;margin:0 0 20px 0;">Trampah · Leads</p>',
        unsafe_allow_html=True,
    )
    st.markdown("---")

    hoje = date.today()
    periodo = st.radio(
        "Período",
        ["Hoje", "7 dias", "30 dias", "Total", "Personalizado"],
        index=2,
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
        col_a, col_b = st.columns(2)
        with col_a:
            data_ini = st.date_input("De", value=hoje - timedelta(days=30))
        with col_b:
            data_fim = st.date_input("Até", value=hoje)

    st.markdown("---")
    if st.button("🔄 Atualizar dados"):
        st.cache_data.clear()
        st.rerun()
    st.caption(f"Auto-refresh a cada 60s")


# ── carrega e filtra ──────────────────────────────────────────────────────────
since_str = data_ini.strftime("%Y-%m-%d")
until_str = data_fim.strftime("%Y-%m-%d")

with st.spinner(""):
    try:
        df_all = load_all_leads()
        erro = None
    except Exception as e:
        df_all = pd.DataFrame()
        erro = str(e)

if erro:
    st.error(f"Erro ao carregar planilha: {erro}")
    st.stop()

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

    total_leads = len(df)
    leads_sp    = int(df["DDD"].isin(SP_DDDS).sum()) if "DDD" in df.columns else 0
    valor_gasto = get_meta_spend(since_str, until_str)
    cpl = (valor_gasto / total_leads) if (valor_gasto and total_leads > 0) else None

    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(kpi_card("🎯", "Total de Leads", fmt_num(total_leads)), unsafe_allow_html=True)
    with c2:
        v = fmt_brl(valor_gasto) if valor_gasto is not None else "—"
        sub = "" if valor_gasto else "Configure o token Meta"
        st.markdown(kpi_card("💰", "Valor Gasto", v, sub), unsafe_allow_html=True)
    with c3:
        v = fmt_brl(cpl) if cpl is not None else "—"
        st.markdown(kpi_card("📉", "Custo por Lead (CPL)", v), unsafe_allow_html=True)
    with c4:
        pct = f"{leads_sp/total_leads*100:.0f}% do total" if total_leads else ""
        st.markdown(kpi_card("📍", "Leads em SP", fmt_num(leads_sp), pct), unsafe_allow_html=True)

    if df.empty:
        st.info("Nenhum lead encontrado no período selecionado.")
        st.stop()

    # Mapa + Barra
    st.markdown('<div class="section-title">Distribuição Geográfica</div>', unsafe_allow_html=True)
    col_map, col_bar = st.columns([3, 2], gap="medium")

    with col_map:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.markdown("**Mapa — Estado de São Paulo por DDD**")
        st.plotly_chart(build_map_sp(df), use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    with col_bar:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.markdown("**Top DDDs**")
        st.plotly_chart(build_bar_ddd(df), use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    # Linha diária
    st.markdown('<div class="section-title">Evolução Diária</div>', unsafe_allow_html=True)
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.plotly_chart(build_line_daily(df), use_container_width=True, config={"displayModeBar": False})
    st.markdown('</div>', unsafe_allow_html=True)

    # Tabela resumo
    st.markdown('<div class="section-title">Resumo por DDD</div>', unsafe_allow_html=True)
    if "DDD" in df.columns:
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
    st.markdown(
        f'<p style="color:#8b949e;font-size:13px;margin-bottom:16px;">'
        f'{fmt_num(len(df))} leads encontrados no período</p>',
        unsafe_allow_html=True,
    )

    if df.empty:
        st.info("Nenhum lead no período.")
    else:
        search = st.text_input("🔍  Buscar por nome ou e-mail", placeholder="Digite para filtrar...", label_visibility="collapsed")
        df_show = df.copy()
        if search:
            mask = (
                df_show.get("NOME",  pd.Series(dtype=str)).str.contains(search, case=False, na=False)
                | df_show.get("EMAIL", pd.Series(dtype=str)).str.contains(search, case=False, na=False)
            )
            df_show = df_show[mask]

        cols_show = [c for c in ["DATA", "NOME", "EMAIL", "TELEFONE", "DDD", "FONTE"] if c in df_show.columns]
        st.dataframe(df_show[cols_show], use_container_width=True, hide_index=True, height=500)
