import os, json, re, requests, unicodedata
from urllib.parse import urlparse, parse_qs
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

/* ── sidebar nav ── */
section[data-testid="stSidebar"] .stRadio {{ margin:0; }}
section[data-testid="stSidebar"] .stRadio > label {{ display:none; }}
section[data-testid="stSidebar"] .stRadio [role="radiogroup"] {{
  display:flex; flex-direction:column; gap:2px;
}}
section[data-testid="stSidebar"] .stRadio [role="radiogroup"] label {{
  display:flex; align-items:center; padding:9px 12px;
  border-radius:12px; cursor:pointer;
  color:{MUTED}; font-size:13px; font-weight:500;
  transition:background .15s, color .15s;
  border:1px solid transparent;
}}
section[data-testid="stSidebar"] .stRadio [role="radiogroup"] label:has(input:checked) {{
  background:{SURF}; color:{TXT}; font-weight:600;
  border-color:{BORDER};
}}
section[data-testid="stSidebar"] .stRadio [role="radiogroup"] label:hover:not(:has(input:checked)) {{
  background:{SURF}; color:{TXT}; opacity:.7;
}}
section[data-testid="stSidebar"] .stRadio [role="radiogroup"] input[type="radio"] {{
  display:none;
}}


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
    if "FONTE" in df.columns:
        df["FONTE"] = (df["FONTE"].astype(str)
                       .str.replace(r"[_\-]?kilorias[_\-]?", "", regex=True, case=False)
                       .str.strip("_- ").str.strip()
                       .replace({"": None, "nan": None, "none": None}))
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

def load_leads(projetos: tuple, proj_map: tuple) -> pd.DataFrame:
    """Combina leads dos projetos da página, cada tabela cacheada individualmente."""
    frames = []
    for nome, table in proj_map:
        df = _fetch_table(table)
        df["PROJETO"] = nome
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    return _process_df(pd.concat(frames, ignore_index=True))

@st.cache_data(ttl=20)
def load_reinoh() -> pd.DataFrame:
    hdrs = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Prefer": "count=none"}
    rows, offset, page = [], 0, 1000
    while True:
        url = (f"{SUPABASE_URL}/rest/v1/reinoh_val"
               f"?select=*&limit={page}&offset={offset}")
        r = requests.get(url, headers=hdrs, timeout=15)
        r.raise_for_status()
        batch = r.json()
        rows.extend(batch)
        if len(batch) < page: break
        offset += page
    if not rows: return pd.DataFrame()
    df = pd.DataFrame(rows)
    def _norm_col(c):
        c = unicodedata.normalize("NFKD", str(c)).encode("ascii", "ignore").decode("ascii")
        return re.sub(r"\s+", "_", c.strip()).upper()
    df.columns = [_norm_col(c) for c in df.columns]
    # detecta coluna de data (pode ter nomes diferentes dependendo de como foi criada no Supabase)
    date_col = next((c for c in df.columns if "DATA" in c or "DATE" in c or "CADASTRO" in c), None)
    if date_col:
        df["DATA"] = (pd.to_datetime(df[date_col], errors="coerce", utc=True)
                      .dt.tz_convert(BRASILIA).dt.tz_localize(None))
        df = df.sort_values("DATA", ascending=False, na_position="last")
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
def load_zona_eleitoral() -> pd.DataFrame:
    hdrs = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Prefer": "count=none"}
    rows, offset, page = [], 0, 1000
    while True:
        url = f"{SUPABASE_URL}/rest/v1/Guti_zona_eleitoral?select=*&limit={page}&offset={offset}"
        r = requests.get(url, headers=hdrs, timeout=15)
        r.raise_for_status()
        batch = r.json()
        rows.extend(batch)
        if len(batch) < page: break
        offset += page
    if not rows: return pd.DataFrame()
    df = pd.DataFrame(rows)
    def _norm_col(c):
        c = unicodedata.normalize("NFKD", str(c)).encode("ascii","ignore").decode("ascii")
        return re.sub(r"\s+", "_", c.strip()).upper()
    df.columns = [_norm_col(c) for c in df.columns]
    # data
    date_col = next((c for c in df.columns if "CRIADO" in c or "DATA" in c or "DATE" in c), None)
    if date_col:
        df["DATA"] = (pd.to_datetime(df[date_col], errors="coerce", utc=True)
                      .dt.tz_convert(BRASILIA).dt.tz_localize(None))
        df = df.sort_values("DATA", ascending=False, na_position="last")
    # padroniza colunas-chave
    renames = {
        next((c for c in df.columns if "NOME" in c and "DO" not in c), None): "NOME",
        next((c for c in df.columns if "MAIL" in c), None):                    "EMAIL",
        next((c for c in df.columns if "TELEFONE" in c or "FONE" in c), None): "TELEFONE",
        next((c for c in df.columns if c == "CIDADE" or "CIDAD" in c), None):  "CIDADE",
        next((c for c in df.columns if "FORM" in c or "NOME_DO" in c or "FONTE" in c), None): "FONTE",
        next((c for c in df.columns if "REFER" in c or "UTM" in c), None):     "REF",
    }
    df = df.rename(columns={orig: std for orig, std in renames.items() if orig and orig != std})
    # parse UTM da coluna Referência
    if "REF" in df.columns:
        def _parse_utm(url):
            try:
                q = parse_qs(urlparse(str(url)).query)
                return pd.Series({
                    "UTM_SOURCE":   q.get("utm_source",   [None])[0],
                    "UTM_CAMPAIGN": q.get("utm_campaign", [None])[0],
                    "UTM_MEDIUM":   q.get("utm_medium",   [None])[0],
                })
            except Exception:
                return pd.Series({"UTM_SOURCE": None, "UTM_CAMPAIGN": None, "UTM_MEDIUM": None})
        df[["UTM_SOURCE","UTM_CAMPAIGN","UTM_MEDIUM"]] = df["REF"].apply(_parse_utm)
    return df

@st.cache_data(ttl=86400)
def _sp_geojson():
    try:
        r = requests.get(
            "https://servicodados.ibge.gov.br/api/v3/malhas/estados/35"
            "?formato=application/vnd.geo+json&resolucao=5",
            timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

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

def _sp_layer(color=ORANGE, width=2.5):
    gj = _sp_geojson()
    if not gj: return []
    return [dict(sourcetype="geojson", source=gj, type="line",
                 color=color, line=dict(width=width))]

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
        mapbox=dict(style=MAP_STYLE, center={"lat":-22.5,"lon":-48.5}, zoom=5.8,
                    layers=_sp_layer()),
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


CIDADE_COORDS = {
    "GUARULHOS":{"lat":-23.4543,"lon":-46.5333},"CAMPINAS":{"lat":-22.9056,"lon":-47.0608},
    "HORTOLANDIA":{"lat":-22.8608,"lon":-47.2200},"HORTOLÂNDIA":{"lat":-22.8608,"lon":-47.2200},
    "SUMARE":{"lat":-22.8219,"lon":-47.2669},"SUMARÉ":{"lat":-22.8219,"lon":-47.2669},
    "PAULINIA":{"lat":-22.7614,"lon":-47.1536},"PAULÍNIA":{"lat":-22.7614,"lon":-47.1536},
    "ATIBAIA":{"lat":-23.1175,"lon":-46.5503},
    "PRAIA GRANDE":{"lat":-24.0058,"lon":-46.4022},
    "SAO PAULO":{"lat":-23.5505,"lon":-46.6333},"SÃO PAULO":{"lat":-23.5505,"lon":-46.6333},
    "SANTO ANDRE":{"lat":-23.6639,"lon":-46.5383},"SANTO ANDRÉ":{"lat":-23.6639,"lon":-46.5383},
    "MOGI DAS CRUZES":{"lat":-23.5228,"lon":-46.1869},
    "JUNDIAI":{"lat":-23.1864,"lon":-46.8981},"JUNDIAÍ":{"lat":-23.1864,"lon":-46.8981},
    "SOROCABA":{"lat":-23.5015,"lon":-47.4526},
    "BARUERI":{"lat":-23.5114,"lon":-46.8758},
    "OSASCO":{"lat":-23.5325,"lon":-46.7919},
    "SAO BERNARDO DO CAMPO":{"lat":-23.6914,"lon":-46.5646},
    "RIBEIRAO PRETO":{"lat":-21.1775,"lon":-47.8103},"RIBEIRÃO PRETO":{"lat":-21.1775,"lon":-47.8103},
    "SAO JOSE DOS CAMPOS":{"lat":-23.1794,"lon":-45.8869},"SÃO JOSÉ DOS CAMPOS":{"lat":-23.1794,"lon":-45.8869},
    "SANTOS":{"lat":-23.9608,"lon":-46.3336},
    "PIRACICABA":{"lat":-22.7253,"lon":-47.6492},
    "LIMEIRA":{"lat":-22.5647,"lon":-47.4008},
    "AMERICANA":{"lat":-22.7394,"lon":-47.3319},
    "SANTA BARBARA D'OESTE":{"lat":-22.7539,"lon":-47.4136},
    "INDAIATUBA":{"lat":-23.0897,"lon":-47.2189},
    "VALINHOS":{"lat":-22.9706,"lon":-46.9961},
    "VINHEDO":{"lat":-23.0297,"lon":-46.9747},"VINHEDO":{"lat":-23.0297,"lon":-46.9747},
    "ITATIBA":{"lat":-23.0039,"lon":-46.8381},
    "PERUIBE":{"lat":-24.3189,"lon":-47.0044},"PERUÍBE":{"lat":-24.3189,"lon":-47.0044},
    "BARUERI":{"lat":-23.5114,"lon":-46.8758},
    "ITAPEVI":{"lat":-23.5489,"lon":-46.9342},
    "COTIA":{"lat":-23.6039,"lon":-46.9192},
    "EMBU_DAS_ARTES":{"lat":-23.6489,"lon":-46.8511},"EMBU DAS ARTES":{"lat":-23.6489,"lon":-46.8511},
    "DIADEMA":{"lat":-23.6861,"lon":-46.6228},
    "MAUA":{"lat":-23.6678,"lon":-46.4619},"MAUÁ":{"lat":-23.6678,"lon":-46.4619},
    "SUZANO":{"lat":-23.5422,"lon":-46.3119},
    "ITAQUAQUECETUBA":{"lat":-23.4861,"lon":-46.3486},
    "FERRAZ_DE_VASCONCELOS":{"lat":-23.5408,"lon":-46.3689},"FERRAZ DE VASCONCELOS":{"lat":-23.5408,"lon":-46.3689},
    "CARAPICUIBA":{"lat":-23.5228,"lon":-46.8353},
    "ITAPETININGA":{"lat":-23.5917,"lon":-48.0531},
    "SAO_CAETANO_DO_SUL":{"lat":-23.6189,"lon":-46.5500},"SÃO CAETANO DO SUL":{"lat":-23.6189,"lon":-46.5500},
    "RIBEIRAO_PIRES":{"lat":-23.7108,"lon":-46.4131},"RIBEIRÃO PIRES":{"lat":-23.7108,"lon":-46.4131},
    "TAUBATE":{"lat":-23.0261,"lon":-45.5558},"TAUBATÉ":{"lat":-23.0261,"lon":-45.5558},
    "SAO_JOSE_DO_RIO_PRETO":{"lat":-20.8197,"lon":-49.3794},"SÃO JOSÉ DO RIO PRETO":{"lat":-20.8197,"lon":-49.3794},
    "ARARAS":{"lat":-22.3572,"lon":-47.3839},
    "BOTUCATU":{"lat":-22.8858,"lon":-48.4428},
    "MARILIA":{"lat":-22.2139,"lon":-49.9458},"MARÍLIA":{"lat":-22.2139,"lon":-49.9458},
    "PRESIDENTE_PRUDENTE":{"lat":-22.1208,"lon":-51.3886},"PRESIDENTE PRUDENTE":{"lat":-22.1208,"lon":-51.3886},
    "FRANCA":{"lat":-20.5386,"lon":-47.4008},
    "BRAGANCA_PAULISTA":{"lat":-22.9519,"lon":-46.5425},"BRAGANÇA PAULISTA":{"lat":-22.9519,"lon":-46.5425},
    "GUARA_SP":{"lat":-20.4347,"lon":-47.8258},"GUARA":{"lat":-20.4347,"lon":-47.8258},
}

def municipio_key(nome):
    n = unicodedata.normalize("NFKD", str(nome)).encode("ascii","ignore").decode("ascii").upper().strip()
    return CIDADE_COORDS.get(n)

def map_municipio(df, col="MUNICIPIO", label="cadastros", height=380):
    if col not in df.columns or df.empty: return None
    cnt = df[col].value_counts().reset_index()
    cnt.columns = [col, label]
    rows = []
    for _, r in cnt.iterrows():
        coords = municipio_key(str(r[col]))
        if coords:
            rows.append({"cidade": r[col], label: int(r[label]),
                         "lat": coords["lat"], "lon": coords["lon"]})
    if not rows: return None
    mdf = pd.DataFrame(rows); mx = mdf[label].max()
    fig = go.Figure()
    fig.add_trace(go.Scattermapbox(
        lat=mdf["lat"], lon=mdf["lon"], mode="markers",
        marker=dict(size=mdf[label]/mx*60+14,
                    color=mdf[label],
                    colorscale=[[0,GREEN],[.5,ORANGE],[1,"#ef4444"]],
                    opacity=.85, showscale=False, sizemode="diameter"),
        customdata=mdf[["cidade", label]].values,
        hovertemplate=f"<b>%{{customdata[0]}}</b><br><b>%{{customdata[1]:,}} {label}</b><extra></extra>",
        text=mdf["cidade"], name="",
    ))
    fig.update_layout(
        mapbox=dict(style="carto-positron", center={"lat":-22.5,"lon":-48.5}, zoom=5.8,
                    layers=_sp_layer(color=ORANGE)),
        margin=dict(r=0,t=0,l=0,b=0), paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False, height=height,
    )
    return fig

# ── sidebar ───────────────────────────────────────────────────────────────────

# Páginas disponíveis — adicione novas entradas aqui conforme criar tabelas no Supabase
# formato: "Label no menu": {"tabelas": [...], "descricao": "..."}
PAGINAS = {
    "🏠  Geral": {
        "tipo": "leads",
        "projetos": PROJETOS,
    },
    "🏛️  Reinoh": {
        "tipo": "reinoh",
        "tabela": "reinoh_val",
    },
    "🗳️  Zona Eleitoral": {
        "tipo": "zona_eleitoral",
        "tabela": "Guti_zona_eleitoral",
    },
}

with st.sidebar:
    c_title, c_theme, c_refresh = st.columns([5, 1, 1])
    with c_title:
        st.markdown(f"""
        <div style="font-size:19px;font-weight:800;color:{TXT};letter-spacing:-.03em;line-height:1.1">DashGuti</div>
        <div style="font-size:11px;color:{MUTED2};margin-top:3px;font-weight:500">Analytics</div>
        """, unsafe_allow_html=True)
    if c_theme.button(BTN_ICON, use_container_width=True):
        st.session_state.dark = not D; st.rerun()
    if c_refresh.button("⟳", use_container_width=True):
        st.cache_data.clear(); st.rerun()

    st.markdown(f'<div style="height:1px;background:{BORDER};margin:20px 0 12px"></div>', unsafe_allow_html=True)

    pagina_sel = st.radio("", list(PAGINAS.keys()), label_visibility="collapsed")
    pagina_cfg = PAGINAS[pagina_sel]

    st.markdown(f'<div style="height:1px;background:{BORDER};margin:12px 0 16px"></div>', unsafe_allow_html=True)

    # Filtro de projeto — só na aba Geral (tipo leads com múltiplos projetos)
    if pagina_cfg.get("tipo") == "leads":
        projs = pagina_cfg["projetos"]
        if len(projs) > 1:
            projeto_sel = st.selectbox("PROJETO", ["Todos"] + list(projs.keys()), index=0)
            proj_map = list(projs.items()) if projeto_sel == "Todos" \
                       else [(projeto_sel, projs[projeto_sel])]
            st.markdown(f'<div style="height:1px;background:{BORDER};margin:12px 0 16px"></div>', unsafe_allow_html=True)
        else:
            projeto_sel = list(projs.keys())[0]
            proj_map    = list(projs.items())
        projetos_ativos = tuple(n for n, _ in proj_map)

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



# ── roteador de páginas ───────────────────────────────────────────────────────
since_str = data_ini.strftime("%Y-%m-%d")
until_str = data_fim.strftime("%Y-%m-%d")
tipo = pagina_cfg.get("tipo", "leads")

if tipo == "reinoh":
    with st.spinner(""):
        try:    df_all = load_reinoh(); erro = None
        except Exception as e: df_all = pd.DataFrame(); erro = str(e)
elif tipo == "zona_eleitoral":
    with st.spinner(""):
        try:    df_all = load_zona_eleitoral(); erro = None
        except Exception as e: df_all = pd.DataFrame(); erro = str(e)
else:
    with st.spinner(""):
        try:    df_all = load_leads(projetos_ativos, tuple(proj_map)); erro = None
        except Exception as e: df_all = pd.DataFrame(); erro = str(e)

if erro:
    st.error(f"Erro ao carregar dados: {erro}"); st.stop()

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


# ── renderização por tipo de página ───────────────────────────────────────────
if tipo == "reinoh":
    tab_vis, tab_cad = st.tabs(["  📊  Visão Geral  ","  📋  Cadastros  "])
elif tipo == "zona_eleitoral":
    tab_ze_vis, tab_ze_leads = st.tabs(["  📊  Visão Geral  ","  📋  Leads  "])
else:
    tab_geral, tab_leads = st.tabs(["  🗺️  Geral  ","  📋  Leads  "])

# ═══════════════════════════════ REINOH ══════════════════════════════════════
if tipo == "reinoh":
    total_r  = len(df)
    # coluna de município pode vir como MUNICIPIO ou MUNICIPIO (após normalização)
    MUN_COL = next((c for c in df.columns if "MUNICIPIO" in c or "MUNIC" in c), None)
    IND_COL = next((c for c in df.columns if "INDICADO" in c), None)
    IGR_COL = next((c for c in df.columns if "IGREJA" in c), None)
    STS_COL = next((c for c in df.columns if "STATUS" in c), None)
    # normaliza nomes para facilitar acesso
    if MUN_COL and MUN_COL != "MUNICIPIO": df = df.rename(columns={MUN_COL: "MUNICIPIO"})
    if IND_COL and IND_COL != "INDICADO_POR": df = df.rename(columns={IND_COL: "INDICADO_POR"})
    if IGR_COL and IGR_COL != "IGREJA": df = df.rename(columns={IGR_COL: "IGREJA"})
    if STS_COL and STS_COL != "STATUS": df = df.rename(columns={STS_COL: "STATUS"})
    n_mun = df["MUNICIPIO"].nunique()    if "MUNICIPIO"    in df.columns else 0
    n_igr = df["IGREJA"].nunique()       if "IGREJA"       in df.columns else 0
    n_ind = df["INDICADO_POR"].nunique() if "INDICADO_POR" in df.columns else 0

    with tab_vis:
        # KPIs
        k1,k2,k3,k4 = st.columns(4, gap="medium")
        k1.markdown(kpi_card(PURPLE,"Total de Cadastros",fmt_num(total_r),
                             badge=f"Período: {periodo}",badge_color="rgba(139,92,246,.12)",badge_txt=PURPLE),
                    unsafe_allow_html=True)
        k2.markdown(kpi_card(ORANGE,"Municípios",fmt_num(n_mun),
                             badge="cidades alcançadas",badge_color="rgba(249,115,22,.12)",badge_txt=ORANGE),
                    unsafe_allow_html=True)
        k3.markdown(kpi_card(GREEN,"Igrejas",fmt_num(n_igr),
                             badge="denominações",badge_color="rgba(16,185,129,.12)",badge_txt=GREEN),
                    unsafe_allow_html=True)
        k4.markdown(kpi_card(AMBER,"Indicadores",fmt_num(n_ind),
                             badge="pessoas indicando",badge_color="rgba(245,158,11,.12)",badge_txt=AMBER),
                    unsafe_allow_html=True)

        if df.empty:
            st.info("Nenhum cadastro no período."); st.stop()

        # Crescimento diário
        section("Crescimento")
        cc1, cc2 = st.columns([3,2], gap="medium")
        with cc1:
            with st.container(border=True):
                st.markdown('<div class="chart-title">Cadastros por dia</div>'
                            '<div class="chart-sub">Evolução no período selecionado</div>',
                            unsafe_allow_html=True)
                st.plotly_chart(area_chart(df), use_container_width=True, config={"displayModeBar":False})
        with cc2:
            with st.container(border=True):
                st.markdown('<div class="chart-title">Top Indicadores</div>'
                            '<div class="chart-sub">Quem mais está trazendo cadastros</div>',
                            unsafe_allow_html=True)
                if "INDICADO_POR" in df.columns:
                    ri = (df["INDICADO_POR"].fillna("Não informado").value_counts().head(8).reset_index())
                    ri.columns = ["Indicador","Qtd"]
                    ri = ri.sort_values("Qtd")
                    fig = go.Figure(go.Bar(
                        x=ri["Qtd"], y=ri["Indicador"], orientation="h",
                        marker=dict(color=ri["Qtd"], colorscale=[[0,PURPLE],[1,ORANGE]],
                                    showscale=False, line=dict(width=0)),
                        text=ri["Qtd"], textposition="outside",
                        textfont=dict(color=MUTED2, size=11),
                    ))
                    fig.update_layout(**base_layout(height=240,
                        xaxis=dict(gridcolor=GRID_CLR, showline=False, zeroline=False, tickfont_size=10),
                        yaxis=dict(gridcolor="rgba(0,0,0,0)", showline=False, tickfont_size=11),
                        bargap=0.3,
                    ))
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

        # Mapa por município
        section("Distribuição Geográfica")
        mfig = map_municipio(df)
        if mfig:
            st.plotly_chart(mfig, use_container_width=True, config={"displayModeBar":False, "scrollZoom":True})
        elif "MUNICIPIO" in df.columns:
            # fallback: bar chart se cidades não estiverem no lookup
            with st.container(border=True):
                rm = df["MUNICIPIO"].fillna("Não informado").value_counts().head(15).reset_index()
                rm.columns = ["Município","Qtd"]
                rm = rm.sort_values("Qtd")
                fig = go.Figure(go.Bar(
                    x=rm["Qtd"], y=rm["Município"], orientation="h",
                    marker=dict(color=rm["Qtd"], colorscale=[[0,GREEN],[1,AMBER]],
                                showscale=False, line=dict(width=0)),
                    text=rm["Qtd"], textposition="outside",
                    textfont=dict(color=MUTED2, size=11),
                ))
                fig.update_layout(**base_layout(height=400,
                    xaxis=dict(gridcolor=GRID_CLR, showline=False, zeroline=False),
                    yaxis=dict(gridcolor="rgba(0,0,0,0)", showline=False),
                    bargap=0.3,
                ))
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

        # Tabelas detalhadas
        section("Métricas Detalhadas")
        t1, t2 = st.columns(2, gap="medium")

        with t1:
            with st.container(border=True):
                st.markdown('<div class="chart-title" style="margin-bottom:12px">Ranking de Indicadores</div>',
                            unsafe_allow_html=True)
                if "INDICADO_POR" in df.columns:
                    ri2 = df["INDICADO_POR"].fillna("Não informado").value_counts().reset_index()
                    ri2.columns = ["Indicador","Cadastros"]
                    ri2["% Total"] = (ri2["Cadastros"]/total_r*100).round(1).astype(str)+"%"
                    st.dataframe(ri2, use_container_width=True, hide_index=True, height=300)

        with t2:
            with st.container(border=True):
                st.markdown('<div class="chart-title" style="margin-bottom:12px">Por Igreja</div>',
                            unsafe_allow_html=True)
                if "IGREJA" in df.columns:
                    rig = df["IGREJA"].fillna("Não informada").value_counts().reset_index()
                    rig.columns = ["Igreja","Cadastros"]
                    rig["% Total"] = (rig["Cadastros"]/total_r*100).round(1).astype(str)+"%"
                    st.dataframe(rig, use_container_width=True, hide_index=True, height=300)

    with tab_cad:
        cs, cc = st.columns([4,1])
        search = cs.text_input("", placeholder="🔍  Buscar por nome, cidade, indicador...",
                               label_visibility="collapsed")
        cc.markdown(f'<p style="color:{MUTED2};font-size:12px;text-align:right;padding-top:10px">'
                    f'{fmt_num(len(df))} registros</p>', unsafe_allow_html=True)
        df_show = df.copy()
        if search:
            cols_busca = ["NOME","MUNICIPIO","IGREJA","INDICADO_POR","EMAIL"]
            mask_s = pd.Series(False, index=df_show.index)
            for c in cols_busca:
                if c in df_show.columns:
                    mask_s |= df_show[c].astype(str).str.contains(search, case=False, na=False)
            df_show = df_show[mask_s]
        show_cols = [c for c in ["DATA","NOME","MUNICIPIO","IGREJA","INDICADO_POR","STATUS","TELEFONE","EMAIL"]
                     if c in df_show.columns]
        st.dataframe(df_show[show_cols], use_container_width=True, hide_index=True, height=560)

    st.stop()   # reinoh page complete — don't render leads tabs below

# ══════════════════════════ ZONA ELEITORAL ═══════════════════════════════════
if tipo == "zona_eleitoral":
    total_ze = len(df)
    n_cidades    = df["CIDADE"].nunique()        if "CIDADE"       in df.columns else 0
    n_campanhas  = df["UTM_CAMPAIGN"].nunique()  if "UTM_CAMPAIGN" in df.columns else 0
    n_fontes     = df["UTM_SOURCE"].nunique()    if "UTM_SOURCE"   in df.columns else 0

    with tab_ze_vis:
        # KPIs
        k1,k2,k3,k4 = st.columns(4, gap="medium")
        k1.markdown(kpi_card(PURPLE,"Total de Leads",fmt_num(total_ze),
                             badge=f"Período: {periodo}",badge_color="rgba(139,92,246,.12)",badge_txt=PURPLE),
                    unsafe_allow_html=True)
        k2.markdown(kpi_card(ORANGE,"Cidades",fmt_num(n_cidades),
                             badge="municípios alcançados",badge_color="rgba(249,115,22,.12)",badge_txt=ORANGE),
                    unsafe_allow_html=True)
        k3.markdown(kpi_card(GREEN,"Campanhas",fmt_num(n_campanhas),
                             badge="utm_campaign distintas",badge_color="rgba(16,185,129,.12)",badge_txt=GREEN),
                    unsafe_allow_html=True)
        k4.markdown(kpi_card(AMBER,"Fontes",fmt_num(n_fontes),
                             badge="utm_source distintas",badge_color="rgba(245,158,11,.12)",badge_txt=AMBER),
                    unsafe_allow_html=True)

        if df.empty:
            st.info("Nenhum lead no período selecionado."); st.stop()

        # Crescimento
        section("Crescimento")
        with st.container(border=True):
            st.markdown('<div class="chart-title">Leads por dia</div>'
                        '<div class="chart-sub">Evolução no período selecionado</div>',
                        unsafe_allow_html=True)
            st.plotly_chart(area_chart(df), use_container_width=True, config={"displayModeBar":False})

        # Mapa
        section("Distribuição Geográfica")
        mfig_ze = map_municipio(df, col="CIDADE", label="leads", height=440)
        if mfig_ze:
            st.plotly_chart(mfig_ze, use_container_width=True,
                            config={"displayModeBar":False, "scrollZoom":True})
        elif "CIDADE" in df.columns:
            with st.container(border=True):
                rc = df["CIDADE"].fillna("Não informada").value_counts().head(20).reset_index()
                rc.columns = ["Cidade","Qtd"]
                rc = rc.sort_values("Qtd")
                fig = go.Figure(go.Bar(
                    x=rc["Qtd"], y=rc["Cidade"], orientation="h",
                    marker=dict(color=rc["Qtd"], colorscale=[[0,PURPLE],[1,ORANGE]],
                                showscale=False, line=dict(width=0)),
                    text=rc["Qtd"], textposition="outside",
                    textfont=dict(color=MUTED2, size=11),
                ))
                fig.update_layout(**base_layout(height=480,
                    xaxis=dict(gridcolor=GRID_CLR, showline=False, zeroline=False),
                    yaxis=dict(gridcolor="rgba(0,0,0,0)", showline=False),
                    bargap=0.3))
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

        # Origem
        section("Origem dos Leads")
        oc1, oc2 = st.columns(2, gap="medium")

        with oc1:
            with st.container(border=True):
                st.markdown('<div class="chart-title">Top Cidades</div>'
                            '<div class="chart-sub">Volume de leads por município</div>',
                            unsafe_allow_html=True)
                if "CIDADE" in df.columns:
                    rci = df["CIDADE"].fillna("Não informada").value_counts().head(10).reset_index()
                    rci.columns = ["Cidade","Qtd"]; rci = rci.sort_values("Qtd")
                    fig = go.Figure(go.Bar(
                        x=rci["Qtd"], y=rci["Cidade"], orientation="h",
                        marker=dict(color=rci["Qtd"], colorscale=[[0,PURPLE],[1,ORANGE]],
                                    showscale=False, line=dict(width=0)),
                        text=rci["Qtd"], textposition="outside",
                        textfont=dict(color=MUTED2, size=11),
                    ))
                    fig.update_layout(**base_layout(height=320,
                        xaxis=dict(gridcolor=GRID_CLR, showline=False, zeroline=False, tickfont_size=10),
                        yaxis=dict(gridcolor="rgba(0,0,0,0)", showline=False, tickfont_size=11),
                        bargap=0.3))
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

        with oc2:
            with st.container(border=True):
                st.markdown('<div class="chart-title">Campanhas (UTM)</div>'
                            '<div class="chart-sub">Leads por utm_campaign</div>',
                            unsafe_allow_html=True)
                if "UTM_CAMPAIGN" in df.columns:
                    rc2 = (df["UTM_CAMPAIGN"].dropna()
                           .value_counts().head(10).reset_index())
                    rc2.columns = ["Campanha","Qtd"]; rc2 = rc2.sort_values("Qtd")
                    fig = go.Figure(go.Bar(
                        x=rc2["Qtd"], y=rc2["Campanha"], orientation="h",
                        marker=dict(color=rc2["Qtd"], colorscale=[[0,GREEN],[1,AMBER]],
                                    showscale=False, line=dict(width=0)),
                        text=rc2["Qtd"], textposition="outside",
                        textfont=dict(color=MUTED2, size=11),
                    ))
                    fig.update_layout(**base_layout(height=320,
                        xaxis=dict(gridcolor=GRID_CLR, showline=False, zeroline=False, tickfont_size=10),
                        yaxis=dict(gridcolor="rgba(0,0,0,0)", showline=False, tickfont_size=11),
                        bargap=0.3))
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

        # Métricas detalhadas
        section("Métricas Detalhadas")
        dt1, dt2 = st.columns(2, gap="medium")

        with dt1:
            with st.container(border=True):
                st.markdown('<div class="chart-title" style="margin-bottom:12px">Por Cidade</div>',
                            unsafe_allow_html=True)
                if "CIDADE" in df.columns:
                    rtc = df["CIDADE"].fillna("Não informada").value_counts().reset_index()
                    rtc.columns = ["Cidade","Leads"]
                    rtc["% Total"] = (rtc["Leads"]/total_ze*100).round(1).astype(str)+"%"
                    st.dataframe(rtc, use_container_width=True, hide_index=True, height=320)

        with dt2:
            with st.container(border=True):
                st.markdown('<div class="chart-title" style="margin-bottom:12px">Por Fonte (UTM Source)</div>',
                            unsafe_allow_html=True)
                if "UTM_SOURCE" in df.columns:
                    rts = df["UTM_SOURCE"].dropna().value_counts().reset_index()
                    rts.columns = ["Fonte","Leads"]
                    rts["% Total"] = (rts["Leads"]/total_ze*100).round(1).astype(str)+"%"
                    st.dataframe(rts, use_container_width=True, hide_index=True, height=320)

    with tab_ze_leads:
        ls, lc = st.columns([4,1])
        ze_search = ls.text_input("", placeholder="🔍  Buscar por nome, cidade, campanha...",
                                  label_visibility="collapsed")
        lc.markdown(f'<p style="color:{MUTED2};font-size:12px;text-align:right;padding-top:10px">'
                    f'{fmt_num(len(df))} registros</p>', unsafe_allow_html=True)
        df_ze = df.copy()
        if ze_search:
            ze_cols = ["NOME","EMAIL","CIDADE","FONTE","UTM_SOURCE","UTM_CAMPAIGN"]
            ze_mask = pd.Series(False, index=df_ze.index)
            for c in ze_cols:
                if c in df_ze.columns:
                    ze_mask |= df_ze[c].astype(str).str.contains(ze_search, case=False, na=False)
            df_ze = df_ze[ze_mask]
        ze_show = [c for c in ["DATA","NOME","CIDADE","FONTE","UTM_CAMPAIGN","UTM_SOURCE",
                                "UTM_MEDIUM","TELEFONE","EMAIL","REF"]
                   if c in df_ze.columns]
        st.dataframe(df_ze[ze_show], use_container_width=True, hide_index=True, height=560)

    st.stop()   # zona_eleitoral complete

# ══════════════════════════════ GERAL / LEADS ════════════════════════════════
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
    proj_colors = {"Trampah": PURPLE, "Latidah": GREEN, "Vigilha": AMBER}
    projs = pagina_cfg["projetos"]
    if len(projs) > 1 and "PROJETO" in df.columns:
        st.markdown('<div style="margin-top:16px"></div>', unsafe_allow_html=True)
        proj_cols = st.columns(4, gap="medium")
        for col, (nome, _tbl) in zip(proj_cols, projs.items()):
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
    st.plotly_chart(map_chart(df), use_container_width=True, config={"displayModeBar":False, "scrollZoom":True})

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
