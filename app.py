import os, json, re, requests
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from ddd_coords import DDD_INFO

BRASILIA = ZoneInfo("America/Sao_Paulo")

load_dotenv()

SHEETS_CSV_URL = (
    "https://docs.google.com/spreadsheets/d/e/"
    "2PACX-1vTch090fHoZlOtOE7Q89ejnSsvfcOSqAJg5M4ZZG1ly5kYneptpVTuudvWvJkbE2l3gkAPa_lASvYlN"
    "/pub?gid=0&single=true&output=csv"
)
META_TOKEN    = os.getenv("META_ACCESS_TOKEN", "")
META_ACCOUNT  = os.getenv("META_AD_ACCOUNT_ID", "")
SUPABASE_URL  = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY  = os.getenv("SUPABASE_KEY", "")
SP_DDDS       = {"11","12","13","14","15","16","17","18","19"}

PROJETOS = {
    "Trampah": "lead_guti_trampah",
    "Latidah":  "lead_guti_latidah",
    "Vigilha":  "lead_guti_vigilha",
}

st.set_page_config(page_title="DashGuti", page_icon="📊",
                   layout="wide", initial_sidebar_state="expanded")


if "dark" not in st.session_state:
    st.session_state.dark = True

D = st.session_state.dark

# ── paleta ────────────────────────────────────────────────────────────────────
if D:
    BG, SURF, SURF2      = "#0f172a", "#1e293b", "#0f172a"
    BORDER               = "#334155"
    TXT, MUTED, MUTED2   = "#f1f5f9", "#94a3b8", "#475569"
    CHART_TPL            = "plotly_dark"
    CHART_PAPER          = "#1e293b"
    CHART_PLOT           = "#1e293b"
    MAP_STYLE            = "carto-positron"
    GRID_CLR             = "#334155"
    SHADOW               = "0 4px 24px rgba(0,0,0,.45)"
    BTN_ICON, BTN_LBL    = "☀️", "Modo claro"
else:
    BG, SURF, SURF2      = "#f8fafc", "#ffffff", "#f1f5f9"
    BORDER               = "#e2e8f0"
    TXT, MUTED, MUTED2   = "#0f172a", "#64748b", "#94a3b8"
    CHART_TPL            = "plotly_white"
    CHART_PAPER          = "#ffffff"
    CHART_PLOT           = "#ffffff"
    MAP_STYLE            = "carto-positron"
    GRID_CLR             = "#e2e8f0"
    SHADOW               = "0 2px 12px rgba(0,0,0,.08)"
    BTN_ICON, BTN_LBL    = "🌙", "Modo escuro"

ORANGE, PURPLE, GREEN, AMBER = "#f97316","#8b5cf6","#10b981","#f59e0b"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,300..900;1,14..32,300..900&display=swap');

*,html,body{{ font-family:'Inter',sans-serif !important; box-sizing:border-box; }}

/* ── app shell ── */
.stApp                            {{ background:{BG} !important; }}
.block-container                  {{ padding:2rem 2.5rem 3rem !important; max-width:100% !important; }}
section[data-testid="stSidebar"]  {{ background:{BG} !important; border-right:1px solid {BORDER}; }}
section[data-testid="stSidebar"] > div {{ padding:2rem 1.25rem; }}

/* ── tabs ── */
.stTabs                            {{ margin-top:28px !important; }}
.stTabs [data-baseweb="tab-list"] {{ background:{SURF} !important; border-radius:14px; padding:5px; border:1px solid {BORDER}; gap:3px; }}
.stTabs [data-baseweb="tab"]      {{ border-radius:10px !important; color:{MUTED} !important; font-size:13px !important; font-weight:500 !important; padding:8px 18px !important; transition:all .2s; }}
.stTabs [aria-selected="true"]    {{ background:{BG} !important; color:{TXT} !important; box-shadow:{SHADOW}; }}
.stTabs [data-baseweb="tab-panel"]{{ padding-top:28px !important; }}

/* ── sidebar icon buttons ── */
.icon-btn {{
  display:inline-flex; align-items:center; justify-content:center;
  width:32px; height:32px; border-radius:8px;
  border:1px solid {BORDER}; background:{SURF};
  color:{MUTED}; font-size:15px; cursor:pointer;
  transition:border-color .2s, color .2s; text-decoration:none;
}}
.icon-btn:hover {{ border-color:{ORANGE}; color:{ORANGE}; }}

/* ── KPI cards ── */
.kpi-wrap {{ display:grid; grid-template-columns:repeat(4,1fr); gap:16px; margin-bottom:24px; }}
.kpi {{
  background:{SURF};
  border:1px solid {BORDER};
  border-radius:20px;
  padding:22px 24px;
  position:relative;
  overflow:hidden;
  height:140px;
  display:flex;
  flex-direction:column;
  justify-content:flex-start;
  transition:transform .2s, box-shadow .2s;
  box-shadow:{SHADOW};
}}
.kpi:hover {{ transform:translateY(-2px); box-shadow:0 8px 32px rgba(0,0,0,.3); }}
.kpi-glow {{
  position:absolute; top:-30px; right:-30px;
  width:100px; height:100px; border-radius:50%;
  opacity:.12; filter:blur(25px);
}}
.kpi-label {{ color:{MUTED}; font-size:11px; font-weight:600; letter-spacing:.09em; text-transform:uppercase; margin-bottom:8px; }}
.kpi-value {{ color:{TXT}; font-size:32px; font-weight:800; letter-spacing:-.03em; line-height:1; margin-bottom:10px; font-variant-numeric:tabular-nums; flex:1; }}
.kpi-badge {{ display:inline-flex; align-self:flex-start; align-items:center; padding:3px 10px; border-radius:999px; font-size:11px; font-weight:600; width:fit-content; }}


/* ── content cards (chart/table containers) ── */
[data-testid="stVerticalBlockBorderWrapper"] {{
  background:{SURF} !important;
  border:1px solid {BORDER} !important;
  border-radius:20px !important;
  padding:4px 4px !important;
  box-shadow:{SHADOW} !important;
}}

/* ── section header ── */
.sec {{ display:flex; align-items:center; gap:12px; margin:28px 0 14px; }}
.sec-pill {{ background:linear-gradient(135deg,{ORANGE},{AMBER}); border-radius:999px; padding:3px 12px; font-size:10px; font-weight:700; color:#fff; letter-spacing:.1em; text-transform:uppercase; }}
.sec-line {{ flex:1; height:1px; background:{BORDER}; }}

/* ── chart cards ── */
.chart-card {{ background:{SURF}; border:1px solid {BORDER}; border-radius:20px; padding:24px; box-shadow:{SHADOW}; }}
.chart-title {{ color:{TXT}; font-size:14px; font-weight:600; margin-bottom:4px; }}
.chart-sub   {{ color:{MUTED}; font-size:12px; margin-bottom:16px; }}

/* ── selectbox ── */
div[data-testid="stSelectbox"] > label  {{ color:{MUTED} !important; font-size:11px !important; font-weight:600 !important; letter-spacing:.08em !important; text-transform:uppercase !important; }}
div[data-testid="stSelectbox"] > div > div {{ background:{SURF} !important; border:1px solid {BORDER} !important; border-radius:12px !important; color:{TXT} !important; box-shadow:{SHADOW}; }}

/* ── sidebar icon buttons ── */
section[data-testid="stSidebar"] .stButton>button {{
  background:{SURF} !important; color:{MUTED} !important;
  border:1px solid {BORDER} !important; border-radius:10px !important;
  height:34px !important; min-height:0 !important; max-height:34px !important;
  font-size:17px !important; padding:0 4px !important; line-height:1 !important;
  display:flex !important; align-items:center !important; justify-content:center !important;
  transition:border-color .2s,color .2s; box-shadow:none !important;
}}
section[data-testid="stSidebar"] .stButton>button:hover {{
  border-color:{ORANGE} !important; color:{ORANGE} !important;
}}
section[data-testid="stSidebar"] .stButton       {{ margin:0 !important; padding:0 !important; }}
section[data-testid="stSidebar"] [data-testid="column"] {{ padding:0 2px !important; }}
section[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] {{ gap:4px !important; align-items:center !important; }}

/* ── text input ── */
.stTextInput>div>div {{ background:{SURF} !important; border:1px solid {BORDER} !important; border-radius:12px !important; box-shadow:{SHADOW}; }}
.stTextInput input   {{ color:{TXT} !important; font-size:13px !important; }}

/* ── dataframe ── */
[data-testid="stDataFrame"]           {{ border-radius:16px; overflow:hidden; box-shadow:{SHADOW}; }}
[data-testid="stDataFrame"] thead th  {{ background:{SURF2} !important; color:{MUTED} !important; font-size:11px !important; font-weight:600 !important; letter-spacing:.06em !important; text-transform:uppercase !important; border-bottom:1px solid {BORDER} !important; }}
[data-testid="stDataFrame"] tbody td  {{ color:{TXT} !important; font-size:13px !important; border-bottom:1px solid {BORDER} !important; }}
[data-testid="stDataFrame"] tbody tr:hover td {{ background:{SURF2} !important; }}

/* ── scrollbar ── */
::-webkit-scrollbar            {{ width:4px; height:4px; }}
::-webkit-scrollbar-track      {{ background:{BG}; }}
::-webkit-scrollbar-thumb      {{ background:{BORDER}; border-radius:4px; }}
::-webkit-scrollbar-thumb:hover{{ background:{MUTED2}; }}
</style>
""", unsafe_allow_html=True)


# ── helpers ───────────────────────────────────────────────────────────────────
def fmt_brl(v): return f"R$ {v:,.2f}".replace(",","X").replace(".",",").replace("X",".")
def fmt_num(v): return f"{int(v):,}".replace(",",".")

def kpi_card(color, label, value, badge="", badge_color="rgba(249,115,22,.15)", badge_txt="#f97316"):
    badge_html = (f'<span class="kpi-badge" style="background:{badge_color};color:{badge_txt}">'
                  f'{badge}</span>') if badge else ""
    return f"""
    <div class="kpi">
      <div class="kpi-glow" style="background:{color}"></div>
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{value}</div>
      {badge_html}
    </div>"""

def section(label):
    st.markdown(f'<div class="sec"><span class="sec-pill">{label}</span>'
                f'<div class="sec-line"></div></div>', unsafe_allow_html=True)


# ── dados ─────────────────────────────────────────────────────────────────────
def _process_df(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [c.strip().upper() for c in df.columns]
    if "DATA" in df.columns:
        df["DATA"] = (
            pd.to_datetime(df["DATA"], errors="coerce", utc=True)
            .dt.tz_convert(BRASILIA)
            .dt.tz_localize(None)
        )
    if "TELEFONE" in df.columns:
        tel = df["TELEFONE"].fillna("").astype(str).str.strip()
        def _ddd(t):
            digits = re.sub(r"\D", "", t)
            if len(digits) < 2: return None
            candidate = digits[2:4] if digits.startswith("55") and len(digits) >= 12 else digits[:2]
            return candidate if candidate in DDD_INFO else None
        df["DDD"] = tel.apply(_ddd)
    return df

@st.cache_data(ttl=20)
def _fetch_table(table: str) -> pd.DataFrame:
    """Busca todos os registros de uma tabela Supabase com paginação."""
    hdrs = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Prefer": "count=none",
    }
    rows, offset, page = [], 0, 1000
    while True:
        url = (f"{SUPABASE_URL}/rest/v1/{table}"
               f"?select=DATA,NOME,EMAIL,TELEFONE,FONTE"
               f"&order=DATA.desc&limit={page}&offset={offset}")
        r = requests.get(url, headers=hdrs, timeout=15)
        r.raise_for_status()
        batch = r.json()
        rows.extend(batch)
        if len(batch) < page:
            break
        offset += page
    return pd.DataFrame(rows)

def load_leads(projetos: tuple) -> pd.DataFrame:
    """Combina leads dos projetos selecionados, cada um cacheado individualmente."""
    frames = []
    for nome, table in PROJETOS.items():
        if nome in projetos:
            df = _fetch_table(table)
            df["PROJETO"] = nome
            frames.append(df)
    if not frames:
        return pd.DataFrame()
    return _process_df(pd.concat(frames, ignore_index=True))

@st.cache_data(ttl=300)
def get_spend(since, until):
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
def base_layout(**kw):
    return dict(template=CHART_TPL, paper_bgcolor=CHART_PAPER, plot_bgcolor=CHART_PLOT,
                font=dict(family="Inter",color=MUTED), margin=dict(l=0,r=0,t=0,b=0),
                **kw)

def map_chart(df):
    if "DDD" not in df.columns or df.empty: return go.Figure()
    sp = df[df["DDD"].isin(SP_DDDS)]
    if sp.empty: return go.Figure()
    cnt = sp["DDD"].astype(str).value_counts().reset_index()
    cnt.columns = ["DDD","leads"]
    rows = [{"DDD":r.DDD,"leads":int(r.leads),
             "lat":DDD_INFO[r.DDD]["lat"],"lon":DDD_INFO[r.DDD]["lon"],
             "cidade":DDD_INFO[r.DDD]["cidade"]}
            for _,r in cnt.iterrows() if r.DDD in DDD_INFO]
    if not rows: return go.Figure()
    mdf = pd.DataFrame(rows); mx = mdf["leads"].max()
    fig = go.Figure()
    fig.add_trace(go.Scattermapbox(
        lat=mdf["lat"], lon=mdf["lon"], mode="markers",
        marker=dict(size=mdf["leads"]/mx*70+14,
                    color=mdf["leads"],
                    colorscale=[[0,PURPLE],[.4,ORANGE],[1,"#ef4444"]],
                    opacity=.88, showscale=False,
                    sizemode="diameter"),
        customdata=mdf[["cidade","leads"]].values,
        hovertemplate="<b>DDD %{text}</b><br>%{customdata[0]}<br><b>%{customdata[1]:,} leads</b><extra></extra>",
        text=mdf["DDD"], name="",
    ))
    fig.add_trace(go.Scattermapbox(
        lat=mdf["lat"], lon=mdf["lon"], mode="text",
        text=mdf["DDD"], textfont=dict(size=11, color="#fff", family="Inter"),
        hoverinfo="skip", name="",
    ))
    fig.update_layout(
        mapbox=dict(style=MAP_STYLE, center={"lat":-22.2,"lon":-48.8}, zoom=5.8),
        margin=dict(r=0,t=0,l=0,b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False, height=480,
    )
    return fig

def area_chart(df):
    if "DATA" not in df.columns or df.empty: return go.Figure()
    d = df.dropna(subset=["DATA"]).copy()
    d["dia"] = d["DATA"].dt.date
    d = d.groupby("dia").size().reset_index(name="leads")
    fig = go.Figure(go.Scatter(
        x=d["dia"], y=d["leads"], mode="lines", fill="tozeroy",
        line=dict(color=ORANGE, width=2.5, shape="spline", smoothing=0.8),
        fillcolor=f"rgba(249,115,22,{'0.15' if D else '0.08'})",
        hovertemplate="<b>%{y} leads</b> em %{x}<extra></extra>",
    ))
    fig.update_layout(**base_layout(height=240,
        xaxis=dict(gridcolor=GRID_CLR, showline=False, tickformat="%d/%m", tickfont_size=11, zeroline=False),
        yaxis=dict(gridcolor=GRID_CLR, showline=False, tickfont_size=11, zeroline=False),
        hovermode="x unified",
    ))
    return fig

def bar_fonte(df):
    if "FONTE" not in df.columns or df.empty: return go.Figure()
    rf = df["FONTE"].fillna("Não informado").value_counts().reset_index()
    rf.columns = ["Fonte","Leads"]
    rf = rf.sort_values("Leads")
    rf["Fonte"] = rf["Fonte"].str.replace("_"," ").str.title()
    fig = go.Figure(go.Bar(
        x=rf["Leads"], y=rf["Fonte"], orientation="h",
        marker=dict(color=rf["Leads"],
                    colorscale=[[0,PURPLE],[1,ORANGE]],
                    showscale=False,
                    line=dict(width=0)),
        text=rf["Leads"].apply(lambda v: fmt_num(int(v))),
        textposition="outside",
        textfont=dict(color=MUTED2, size=11),
    ))
    fig.update_layout(**base_layout(height=240,
        xaxis=dict(gridcolor=GRID_CLR, showline=False, zeroline=False, tickfont_size=10),
        yaxis=dict(gridcolor="rgba(0,0,0,0)", showline=False, tickfont_size=12),
        bargap=0.35,
    ))
    return fig


# ── sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    # header: título + ícones lado a lado
    c_title, c_theme, c_refresh = st.columns([5, 1, 1])
    with c_title:
        st.markdown(f"""
        <div style="font-size:19px;font-weight:800;color:{TXT};letter-spacing:-.03em;line-height:1.1">DashGuti</div>
        <div style="font-size:11px;color:{MUTED2};margin-top:3px;font-weight:500">Multi-projeto · Analytics</div>
        """, unsafe_allow_html=True)
    if c_theme.button(BTN_ICON, use_container_width=True):
        st.session_state.dark = not D; st.rerun()
    if c_refresh.button("⟳", use_container_width=True):
        st.cache_data.clear(); st.rerun()

    st.markdown(f'<div style="height:1px;background:{BORDER};margin:20px 0 20px"></div>', unsafe_allow_html=True)

    projeto_sel = st.selectbox("PROJETO", ["Todos"] + list(PROJETOS.keys()), index=0)
    projetos_ativos = tuple(PROJETOS.keys()) if projeto_sel == "Todos" else (projeto_sel,)

    st.markdown(f'<div style="height:1px;background:{BORDER};margin:16px 0 16px"></div>', unsafe_allow_html=True)

    hoje    = datetime.now(tz=BRASILIA).date()
    periodo = st.selectbox("PERÍODO", ["Hoje","7 dias","30 dias","Total","Personalizado"], index=2)

    if periodo == "Hoje":      data_ini, data_fim = hoje, hoje
    elif periodo == "7 dias":  data_ini, data_fim = hoje-timedelta(7), hoje
    elif periodo == "30 dias": data_ini, data_fim = hoje-timedelta(30), hoje
    elif periodo == "Total":   data_ini, data_fim = date(2020,1,1), hoje
    else:
        ca, cb = st.columns(2)
        data_ini = ca.date_input("De",  hoje-timedelta(30), label_visibility="collapsed")
        data_fim = cb.date_input("Até", hoje,               label_visibility="collapsed")



# ── dados ─────────────────────────────────────────────────────────────────────
since_str = data_ini.strftime("%Y-%m-%d")
until_str = data_fim.strftime("%Y-%m-%d")

with st.spinner(""):
    try:    df_all = load_leads(projetos_ativos); erro = None
    except Exception as e: df_all = pd.DataFrame(); erro = str(e)

if erro:
    st.error(f"Erro ao carregar planilha: {erro}"); st.stop()

if "DATA" in df_all.columns and not df_all.empty and periodo != "Total":
    mask = (df_all["DATA"].dt.date >= data_ini) & (df_all["DATA"].dt.date <= data_fim)
    df = df_all[mask].copy()
else:
    df = df_all.copy()

total    = len(df)
leads_sp = int(df["DDD"].isin(SP_DDDS).sum()) if "DDD" in df.columns else 0
gasto    = get_spend(since_str, until_str)
cpl      = (gasto/total) if gasto and total else None
pct_sp   = f"{leads_sp/total*100:.0f}% do total" if total else ""


# ── tabs ──────────────────────────────────────────────────────────────────────
tab_geral, tab_leads = st.tabs(["  🗺️  Geral  ","  📋  Leads  "])

# ─────────────────────────────────────────────────────────────────────────────
with tab_geral:

    # KPIs — linha 1
    k1,k2,k3,k4 = st.columns(4, gap="medium")
    k1.markdown(kpi_card(PURPLE,"Total de Leads",fmt_num(total),
                         badge=f"Período: {periodo}",badge_color="rgba(139,92,246,.12)",badge_txt=PURPLE),
                unsafe_allow_html=True)
    k2.markdown(kpi_card(GREEN,"Valor Gasto",
                         fmt_brl(gasto) if gasto else "—",
                         badge="Token Meta pendente" if not gasto else "",
                         badge_color="rgba(16,185,129,.12)",badge_txt=GREEN),
                unsafe_allow_html=True)
    k3.markdown(kpi_card(AMBER,"Custo por Lead",
                         fmt_brl(cpl) if cpl else "—"),
                unsafe_allow_html=True)
    k4.markdown(kpi_card(ORANGE,"Leads em SP",fmt_num(leads_sp),
                         badge=pct_sp,badge_color="rgba(249,115,22,.12)",badge_txt=ORANGE),
                unsafe_allow_html=True)

    if df.empty:
        st.info("Nenhum lead encontrado no período."); st.stop()

    # KPIs — linha 2: breakdown por projeto (mesmo estilo da linha 1)
    if projeto_sel == "Todos" and "PROJETO" in df.columns:
        proj_colors = {"Trampah": PURPLE, "Latidah": GREEN, "Vigilha": AMBER}
        st.markdown('<div style="margin-top:16px"></div>', unsafe_allow_html=True)
        p1, p2, p3, _ = st.columns(4, gap="medium")
        for col, (nome, _tbl) in zip([p1, p2, p3], PROJETOS.items()):
            n = int((df["PROJETO"] == nome).sum())
            pct = f"{n/total*100:.0f}% do total" if total else ""
            c = proj_colors.get(nome, ORANGE)
            r, g, b = int(c[1:3],16), int(c[3:5],16), int(c[5:7],16)
            col.markdown(kpi_card(c, nome, fmt_num(n),
                                  badge=pct,
                                  badge_color=f"rgba({r},{g},{b},.12)",
                                  badge_txt=c),
                         unsafe_allow_html=True)

    # Mapa
    section("Distribuição Geográfica")
    st.markdown(f'<p style="color:{MUTED};font-size:13px;margin:-8px 0 16px">Estado de São Paulo · bolhas proporcionais ao volume de leads por DDD</p>',
                unsafe_allow_html=True)
    st.plotly_chart(map_chart(df), use_container_width=True, config={"displayModeBar":False})

    # Evolução + Fonte
    section("Evolução & Origem")
    ca, cb = st.columns([3,2], gap="medium")
    with ca:
        with st.container(border=True):
            st.markdown(f'<div class="chart-title">Leads por dia</div>'
                        f'<div class="chart-sub">Volume diário no período selecionado</div>',
                        unsafe_allow_html=True)
            st.plotly_chart(area_chart(df), use_container_width=True, config={"displayModeBar":False})
    with cb:
        with st.container(border=True):
            st.markdown(f'<div class="chart-title">Leads por fonte</div>'
                        f'<div class="chart-sub">Distribuição por canal de aquisição</div>',
                        unsafe_allow_html=True)
            st.plotly_chart(bar_fonte(df), use_container_width=True, config={"displayModeBar":False})

    # Tabelas
    section("Métricas Detalhadas")
    td, tf = st.columns(2, gap="medium")

    with td:
        with st.container(border=True):
            st.markdown(f'<div class="chart-title" style="margin-bottom:12px">Por DDD</div>',
                        unsafe_allow_html=True)
            if "DDD" in df.columns:
                r = df["DDD"].dropna().astype(str).str.zfill(2).value_counts().reset_index()
                r.columns = ["DDD","Leads"]
                r["Cidade"]  = r["DDD"].map(lambda d: DDD_INFO.get(d,{}).get("cidade","—"))
                r["Estado"]  = r["DDD"].map(lambda d: DDD_INFO.get(d,{}).get("estado","—"))
                r["% Total"] = (r["Leads"]/total*100).round(1).astype(str)+"%"
                st.dataframe(r[["DDD","Cidade","Estado","Leads","% Total"]],
                             use_container_width=True, hide_index=True, height=320)

    with tf:
        with st.container(border=True):
            st.markdown(f'<div class="chart-title" style="margin-bottom:12px">Por Fonte</div>',
                        unsafe_allow_html=True)
            if "FONTE" in df.columns:
                rf = df["FONTE"].fillna("Não informado").value_counts().reset_index()
                rf.columns = ["Fonte","Leads"]
                rf["Fonte"]   = rf["Fonte"].str.replace("_"," ").str.title()
                rf["% Total"] = (rf["Leads"]/total*100).round(1).astype(str)+"%"
                if cpl: rf["CPL Est."] = fmt_brl(cpl)
                st.dataframe(rf[["Fonte","Leads","% Total"]+(["CPL Est."] if cpl else [])],
                             use_container_width=True, hide_index=True, height=320)


# ─────────────────────────────────────────────────────────────────────────────
with tab_leads:
    if df.empty:
        st.info("Nenhum lead no período.")
    else:
        cs, cc = st.columns([4,1])
        search = cs.text_input("", placeholder="🔍  Buscar por nome, e-mail...",
                               label_visibility="collapsed")
        cc.markdown(f'<p style="color:{MUTED2};font-size:12px;text-align:right;padding-top:10px">'
                    f'{fmt_num(len(df))} leads</p>', unsafe_allow_html=True)

        df_show = df.copy()
        if search:
            m = (df_show.get("NOME",  pd.Series(dtype=str)).str.contains(search,case=False,na=False)
               | df_show.get("EMAIL", pd.Series(dtype=str)).str.contains(search,case=False,na=False))
            df_show = df_show[m]

        cols = [c for c in ["PROJETO","DATA","NOME","EMAIL","TELEFONE","DDD","FONTE"] if c in df_show.columns]
        st.dataframe(df_show[cols], use_container_width=True, hide_index=True, height=540)
