import os
import json
import requests
import pandas as pd
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
SP_DDDS      = {"11","12","13","14","15","16","17","18","19"}

# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="DashGuti", page_icon="📊", layout="wide",
                   initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* ── layout ── */
.stApp                          { background: #09090b; }
.block-container                { padding: 1.5rem 2rem 2rem 2rem; max-width: 100%; }
section[data-testid="stSidebar"]{ background: #09090b; border-right: 1px solid #1c1c1e; }

/* ── KPI card ── */
.kpi {
  background: #111113;
  border: 1px solid #1c1c1e;
  border-radius: 16px;
  padding: 24px 20px;
  height: 130px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  transition: border-color .25s, box-shadow .25s;
}
.kpi:hover { border-color: #f97316; box-shadow: 0 0 0 1px #f9731622; }
.kpi-top   { display: flex; align-items: center; gap: 8px; }
.kpi-dot   { width: 8px; height: 8px; border-radius: 50%; background: #f97316; flex-shrink: 0; }
.kpi-label { color: #71717a; font-size: 11px; font-weight: 500;
             letter-spacing: .08em; text-transform: uppercase; }
.kpi-value { color: #fafafa; font-size: 30px; font-weight: 700;
             font-variant-numeric: tabular-nums; letter-spacing: -.02em; }
.kpi-sub   { color: #f97316; font-size: 11px; font-weight: 500; }
.kpi-sub-gray { color: #52525b; font-size: 11px; }

/* ── section header ── */
.sec {
  display: flex; align-items: center; gap: 10px;
  margin: 28px 0 14px 0;
}
.sec-line { width: 3px; height: 16px; background: #f97316; border-radius: 2px; flex-shrink:0; }
.sec-text { color: #a1a1aa; font-size: 11px; font-weight: 600; letter-spacing: .1em; text-transform: uppercase; }

/* ── chart wrap ── */
[data-testid="stPlotlyChart"] {
  border-radius: 14px !important;
  overflow: hidden;
}

/* ── dataframe ── */
[data-testid="stDataFrame"] > div { border-radius: 12px !important; overflow: hidden; }
[data-testid="stDataFrame"] thead th { background: #111113 !important; color: #71717a !important;
  font-size: 11px !important; letter-spacing: .06em !important; text-transform: uppercase !important; }
[data-testid="stDataFrame"] tbody tr:hover td { background: #1c1c1e !important; }

/* ── tabs ── */
.stTabs [data-baseweb="tab-list"]  { background: #111113; border-radius: 12px; padding: 4px; gap: 2px; }
.stTabs [data-baseweb="tab"]       { border-radius: 8px; color: #71717a !important; font-size: 13px; font-weight: 500; }
.stTabs [aria-selected="true"]     { background: #1c1c1e !important; color: #fafafa !important; }
.stTabs [data-baseweb="tab-panel"] { padding-top: 0 !important; }

/* ── sidebar ── */
.stRadio [data-testid="stMarkdownContainer"] p { color: #a1a1aa; font-size: 13px; }
div[data-testid="stRadio"] label { font-size: 13px !important; color: #d4d4d8 !important; }
div[data-testid="stRadio"] label:hover { color: #fafafa !important; }

/* ── button ── */
.stButton > button {
  background: #111113; color: #d4d4d8; border: 1px solid #27272a;
  border-radius: 10px; width: 100%; font-size: 13px; padding: 8px 0;
  transition: all .2s;
}
.stButton > button:hover { border-color: #f97316; color: #f97316; background: #18100a; }

/* ── text input ── */
.stTextInput > div > div { background: #111113 !important; border-color: #27272a !important; border-radius: 10px !important; }
.stTextInput input { color: #fafafa !important; font-size: 13px !important; }

/* ── scrollbar ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #09090b; }
::-webkit-scrollbar-thumb { background: #27272a; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)


# ── helpers ───────────────────────────────────────────────────────────────────
def fmt_brl(v): return f"R$ {v:,.2f}".replace(",","X").replace(".",",").replace("X",".")
def fmt_num(v): return f"{v:,}".replace(",",".")

def kpi(dot_color, label, value, sub="", sub_gray=False):
    sub_cls  = "kpi-sub-gray" if sub_gray else "kpi-sub"
    sub_html = f'<div class="{sub_cls}">{sub}</div>' if sub else '<div style="height:14px"></div>'
    dot_style = f'background:{dot_color}' if dot_color != "#f97316" else ""
    dot_html  = f'<div class="kpi-dot" style="{dot_style}"></div>' if dot_style else '<div class="kpi-dot"></div>'
    return f"""<div class="kpi">
      <div class="kpi-top">{dot_html}<span class="kpi-label">{label}</span></div>
      <div class="kpi-value">{value}</div>
      {sub_html}
    </div>"""

def sec(title):
    st.markdown(f'<div class="sec"><div class="sec-line"></div>'
                f'<span class="sec-text">{title}</span></div>', unsafe_allow_html=True)


# ── dados ─────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_all_leads():
    df = pd.read_csv(SHEETS_CSV_URL)
    df.columns = [c.strip().upper() for c in df.columns]
    if "DATA" in df.columns:
        s = df["DATA"].astype(str).str.extract(r"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})")[0]
        df["DATA"] = pd.to_datetime(s, errors="coerce")
        if getattr(df["DATA"].dtype, "tz", None):
            df["DATA"] = df["DATA"].dt.tz_localize(None)
    if "TELEFONE" in df.columns:
        tel = df["TELEFONE"].fillna("").astype(str).str.replace(r"\.0$","",regex=True).str.strip()
        df["DDD"] = tel.apply(lambda t: t[2:4] if isinstance(t,str) and t.startswith("55") and len(t)>=4 else None)
    return df

@st.cache_data(ttl=300)
def get_meta_spend(since, until):
    if not META_TOKEN or not META_ACCOUNT: return None
    try:
        r = requests.get(
            f"https://graph.facebook.com/v19.0/act_{META_ACCOUNT}/insights",
            params={"fields":"spend","time_range":json.dumps({"since":since,"until":until}),
                    "access_token":META_TOKEN,"level":"account"}, timeout=10)
        d = r.json()
        if "data" in d and d["data"]: return float(d["data"][0].get("spend",0))
    except Exception: pass
    return None


# ── charts ────────────────────────────────────────────────────────────────────
CHART_BG    = "#0d0d0f"
GRID_COLOR  = "#1c1c1e"
FONT_COLOR  = "#a1a1aa"

def build_map(df):
    if "DDD" not in df.columns or df.empty: return go.Figure()
    df_sp = df[df["DDD"].isin(SP_DDDS)]
    if df_sp.empty: return go.Figure()
    counts = df_sp["DDD"].astype(str).value_counts().reset_index()
    counts.columns = ["DDD","leads"]
    rows = []
    for _, r in counts.iterrows():
        info = DDD_INFO.get(r["DDD"])
        if info:
            rows.append({"DDD":r["DDD"],"leads":int(r["leads"]),
                         "lat":info["lat"],"lon":info["lon"],"cidade":info["cidade"]})
    if not rows: return go.Figure()
    mdf = pd.DataFrame(rows)
    mx  = mdf["leads"].max()

    fig = go.Figure()
    fig.add_trace(go.Scattermapbox(
        lat=mdf["lat"], lon=mdf["lon"], mode="markers",
        marker=dict(size=mdf["leads"]/mx*60+16, color=mdf["leads"],
                    colorscale=[[0,"#6366f1"],[.5,"#f97316"],[1,"#ef4444"]],
                    opacity=.82, showscale=False),
        text=mdf.apply(lambda r: f"<b>DDD {r['DDD']} — {r['cidade']}</b><br>{r['leads']:,} leads",axis=1),
        hoverinfo="text", name="",
    ))
    fig.add_trace(go.Scattermapbox(
        lat=mdf["lat"], lon=mdf["lon"], mode="text",
        text=mdf["DDD"], textfont=dict(size=10,color="#ffffff",family="Inter"),
        hoverinfo="skip", name="",
    ))
    fig.update_layout(
        mapbox=dict(style="carto-positron", center={"lat":-22.2,"lon":-48.8}, zoom=5.8),
        margin=dict(r=0,t=0,l=0,b=0), paper_bgcolor=CHART_BG,
        showlegend=False, height=400,
    )
    return fig


def build_bar(df, top_n=15):
    if "DDD" not in df.columns or df.empty: return go.Figure()
    counts = df["DDD"].dropna().astype(str).str.zfill(2).value_counts().head(top_n).reset_index()
    counts.columns = ["DDD","leads"]
    counts["label"] = counts["DDD"].map(lambda d: f"DDD {d} · {DDD_INFO[d]['cidade']}" if d in DDD_INFO else f"DDD {d}")
    counts = counts.sort_values("leads")
    fig = go.Figure(go.Bar(
        x=counts["leads"], y=counts["label"], orientation="h",
        marker=dict(color=counts["leads"], colorscale=[[0,"#6366f1"],[1,"#f97316"]], showscale=False,
                    line=dict(width=0)),
        text=counts["leads"].apply(lambda v: fmt_num(int(v))),
        textposition="outside", textfont=dict(color="#52525b",size=10),
    ))
    fig.update_layout(
        margin=dict(r=50,t=0,l=0,b=0), paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
        font_color=FONT_COLOR, font_size=11, height=400,
        xaxis=dict(gridcolor=GRID_COLOR,zeroline=False,showline=False,tickfont_size=10),
        yaxis=dict(gridcolor="rgba(0,0,0,0)",showline=False,tickfont_size=11),
    )
    return fig


def build_area(df):
    if "DATA" not in df.columns or df.empty: return go.Figure()
    daily = df.dropna(subset=["DATA"]).copy()
    daily["dia"] = daily["DATA"].dt.date
    daily = daily.groupby("dia").size().reset_index(name="leads")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily["dia"], y=daily["leads"], mode="lines", fill="tozeroy",
        line=dict(color="#f97316",width=2.5),
        fillcolor="rgba(249,115,22,0.08)",
        hovertemplate="<b>%{y} leads</b><br>%{x}<extra></extra>",
    ))
    fig.update_layout(
        margin=dict(r=10,t=10,l=0,b=0), paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
        font_color=FONT_COLOR, height=200, hovermode="x unified",
        xaxis=dict(gridcolor=GRID_COLOR,showline=False,tickformat="%d/%m",tickfont_size=11),
        yaxis=dict(gridcolor=GRID_COLOR,showline=False,tickfont_size=11),
    )
    return fig


# ── sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:8px 0 20px 0">
      <div style="font-size:18px;font-weight:700;color:#fafafa;letter-spacing:-.02em">DashGuti</div>
      <div style="font-size:12px;color:#52525b;margin-top:2px">Trampah · Analytics</div>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div style="height:1px;background:#1c1c1e;margin-bottom:20px"></div>', unsafe_allow_html=True)
    st.markdown('<div style="color:#71717a;font-size:11px;letter-spacing:.08em;text-transform:uppercase;margin-bottom:10px">Período</div>', unsafe_allow_html=True)

    hoje   = date.today()
    periodo = st.radio("", ["Hoje","7 dias","30 dias","Total","Personalizado"],
                       index=2, label_visibility="collapsed")

    if periodo == "Hoje":            data_ini, data_fim = hoje, hoje
    elif periodo == "7 dias":        data_ini, data_fim = hoje-timedelta(7), hoje
    elif periodo == "30 dias":       data_ini, data_fim = hoje-timedelta(30), hoje
    elif periodo == "Total":         data_ini, data_fim = date(2020,1,1), hoje
    else:
        ca, cb = st.columns(2)
        data_ini = ca.date_input("De",  value=hoje-timedelta(30), label_visibility="collapsed")
        data_fim = cb.date_input("Até", value=hoje,               label_visibility="collapsed")

    st.markdown('<div style="height:1px;background:#1c1c1e;margin:20px 0"></div>', unsafe_allow_html=True)
    if st.button("⟳  Atualizar dados"):
        st.cache_data.clear(); st.rerun()
    st.markdown(f'<div style="color:#3f3f46;font-size:11px;margin-top:8px;text-align:center">auto-refresh · 60s</div>', unsafe_allow_html=True)


# ── load & filter ─────────────────────────────────────────────────────────────
since_str = data_ini.strftime("%Y-%m-%d")
until_str = data_fim.strftime("%Y-%m-%d")

with st.spinner(""):
    try:    df_all = load_all_leads(); erro = None
    except Exception as e: df_all = pd.DataFrame(); erro = str(e)

if erro:
    st.error(f"Erro ao carregar planilha: {erro}"); st.stop()

if "DATA" in df_all.columns and not df_all.empty:
    df = df_all[(df_all["DATA"].dt.date >= data_ini) & (df_all["DATA"].dt.date <= data_fim)].copy()
else:
    df = df_all.copy()


# ── tabs ──────────────────────────────────────────────────────────────────────
tab_geral, tab_leads = st.tabs(["  🗺️  Geral  ","  📋  Leads  "])

# ─────────────────────────────────────────────────────────────────────────────
with tab_geral:
    total   = len(df)
    leads_sp= int(df["DDD"].isin(SP_DDDS).sum()) if "DDD" in df.columns else 0
    gasto   = get_meta_spend(since_str, until_str)
    cpl     = (gasto/total) if gasto and total else None
    pct_sp  = f"{leads_sp/total*100:.0f}% do total" if total else ""

    # ── KPIs ──────────────────────────────────────────────────────────────────
    k1,k2,k3,k4 = st.columns(4, gap="small")
    k1.markdown(kpi("#6366f1","Total de Leads",   fmt_num(total)), unsafe_allow_html=True)
    k2.markdown(kpi("#10b981","Valor Gasto",      fmt_brl(gasto) if gasto else "—",
                    sub="" if gasto else "Configure o token Meta", sub_gray=not gasto), unsafe_allow_html=True)
    k3.markdown(kpi("#f59e0b","Custo por Lead",   fmt_brl(cpl) if cpl else "—"), unsafe_allow_html=True)
    k4.markdown(kpi("#f97316","Leads em SP",      fmt_num(leads_sp), pct_sp), unsafe_allow_html=True)

    if df.empty:
        st.info("Nenhum lead no período."); st.stop()

    # ── Mapa + Barra ───────────────────────────────────────────────────────────
    sec("Distribuição Geográfica")
    cm, cb_ = st.columns([3,2], gap="medium")
    with cm:
        st.markdown('<p style="color:#71717a;font-size:12px;margin:0 0 8px 4px">Estado de São Paulo · por DDD</p>', unsafe_allow_html=True)
        st.plotly_chart(build_map(df), use_container_width=True, config={"displayModeBar":False})
    with cb_:
        st.markdown('<p style="color:#71717a;font-size:12px;margin:0 0 8px 4px">Top DDDs · todos os estados</p>', unsafe_allow_html=True)
        st.plotly_chart(build_bar(df), use_container_width=True, config={"displayModeBar":False})

    # ── Evolução ──────────────────────────────────────────────────────────────
    sec("Evolução Diária de Leads")
    st.plotly_chart(build_area(df), use_container_width=True, config={"displayModeBar":False})

    # ── Tabelas ───────────────────────────────────────────────────────────────
    sec("Métricas Detalhadas")
    td, tf = st.columns(2, gap="medium")

    with td:
        st.markdown('<p style="color:#71717a;font-size:12px;margin:0 0 8px 4px">Por DDD</p>', unsafe_allow_html=True)
        if "DDD" in df.columns:
            r = df["DDD"].dropna().astype(str).str.zfill(2).value_counts().reset_index()
            r.columns = ["DDD","Leads"]
            r["Cidade"] = r["DDD"].map(lambda d: DDD_INFO.get(d,{}).get("cidade","—"))
            r["Estado"] = r["DDD"].map(lambda d: DDD_INFO.get(d,{}).get("estado","—"))
            r["% Total"] = (r["Leads"]/total*100).round(1).astype(str)+"%"
            st.dataframe(r[["DDD","Cidade","Estado","Leads","% Total"]],
                         use_container_width=True, hide_index=True, height=320)

    with tf:
        st.markdown('<p style="color:#71717a;font-size:12px;margin:0 0 8px 4px">Por Fonte</p>', unsafe_allow_html=True)
        if "FONTE" in df.columns:
            rf = df["FONTE"].fillna("Não informado").value_counts().reset_index()
            rf.columns = ["Fonte","Leads"]
            rf["% Total"] = (rf["Leads"]/total*100).round(1).astype(str)+"%"
            if cpl:
                rf["CPL Est."] = fmt_brl(cpl)
            st.dataframe(rf[["Fonte","Leads","% Total"] + (["CPL Est."] if cpl else [])],
                         use_container_width=True, hide_index=True, height=320)


# ─────────────────────────────────────────────────────────────────────────────
with tab_leads:
    if df.empty:
        st.info("Nenhum lead no período.")
    else:
        c_search, c_count = st.columns([3,1])
        with c_search:
            search = st.text_input("", placeholder="🔍  Buscar por nome ou e-mail...",
                                   label_visibility="collapsed")
        with c_count:
            st.markdown(f'<div style="color:#52525b;font-size:12px;padding:10px 0;text-align:right">'
                        f'{fmt_num(len(df))} leads</div>', unsafe_allow_html=True)

        df_show = df.copy()
        if search:
            m = (df_show.get("NOME",  pd.Series(dtype=str)).str.contains(search,case=False,na=False)
               | df_show.get("EMAIL", pd.Series(dtype=str)).str.contains(search,case=False,na=False))
            df_show = df_show[m]

        cols = [c for c in ["DATA","NOME","EMAIL","TELEFONE","DDD","FONTE"] if c in df_show.columns]
        st.dataframe(df_show[cols], use_container_width=True, hide_index=True, height=520)
