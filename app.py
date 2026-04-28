import os, json, re, requests, unicodedata
from urllib.parse import urlparse, parse_qs, quote
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

@st.cache_data(ttl=20)
def load_andreia() -> pd.DataFrame:
    hdrs = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Prefer": "count=none"}
    table = quote("base protetores andreia", safe="")
    rows, offset, page = [], 0, 1000
    while True:
        url = f"{SUPABASE_URL}/rest/v1/{table}?select=*&limit={page}&offset={offset}"
        r = requests.get(url, headers=hdrs, timeout=15)
        r.raise_for_status()
        batch = r.json()
        rows.extend(batch)
        if len(batch) < page: break
        offset += page
    if not rows: return pd.DataFrame()
    df = pd.DataFrame(rows)
    def _norm(c):
        c = unicodedata.normalize("NFKD", str(c)).encode("ascii","ignore").decode("ascii")
        return re.sub(r"[^\w]+", "_", c.strip()).upper().strip("_")
    df.columns = [_norm(c) for c in df.columns]
    # date col (Supabase created_at ou similar)
    date_col = next((c for c in df.columns if "CRIADO" in c or "DATA" in c or "DATE" in c or "CREATED" in c), None)
    if date_col:
        df["DATA"] = (pd.to_datetime(df[date_col], errors="coerce", utc=True)
                      .dt.tz_convert(BRASILIA).dt.tz_localize(None))
        df = df.sort_values("DATA", ascending=False, na_position="last")
    # normaliza coluna N°
    col_num = next((c for c in df.columns if c in ("N_", "N", "NUM", "NUMERO", "NUMERO_")), None)
    if col_num and col_num != "NUM": df = df.rename(columns={col_num: "NUM"})
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

@st.cache_data(ttl=20)
def load_buffo() -> pd.DataFrame:
    hdrs = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Prefer": "count=none"}
    rows, offset, page = [], 0, 1000
    while True:
        url = f"{SUPABASE_URL}/rest/v1/base_buffo?select=*&limit={page}&offset={offset}"
        r = requests.get(url, headers=hdrs, timeout=15)
        r.raise_for_status()
        batch = r.json()
        rows.extend(batch)
        if len(batch) < page: break
        offset += page
    if not rows: return pd.DataFrame()
    df = pd.DataFrame(rows)
    def _norm(c):
        c = unicodedata.normalize("NFKD", str(c)).encode("ascii","ignore").decode("ascii")
        return re.sub(r"[^\w]+", "_", c.strip()).upper().strip("_")
    df.columns = [_norm(c) for c in df.columns]
    date_col = next((c for c in df.columns if "DATA_HORA" in c or "CREATED" in c), None) \
               or next((c for c in df.columns if "DATA" in c), None)
    if date_col:
        df["DATA"] = (pd.to_datetime(df[date_col], errors="coerce", utc=True)
                      .dt.tz_convert(BRASILIA).dt.tz_localize(None))
        df = df.sort_values("DATA", ascending=False, na_position="last")
    pet_col = next((c for c in df.columns if "CACHORRO" in c or ("ANIMAL" in c and "NOME" not in c)), None)
    if pet_col:
        df = df.rename(columns={pet_col: "TIPO_ANIMAL"})
        df["TIPO_ANIMAL"] = df["TIPO_ANIMAL"].str.upper().str.strip()
    if "GENERO" in df.columns:
        df["GENERO"] = df["GENERO"].str.capitalize().str.strip()
    bairro_col = next((c for c in df.columns if "BAIRRO" in c), None)
    if bairro_col and bairro_col != "BAIRRO":
        df = df.rename(columns={bairro_col: "BAIRRO"})
    if "BAIRRO" in df.columns:
        df["BAIRRO"] = df["BAIRRO"].str.upper().str.strip()
    comp_col = next((c for c in df.columns if "COMPLEMENT" in c), None)
    if comp_col and comp_col != "COMPLEMENTO":
        df = df.rename(columns={comp_col: "COMPLEMENTO"})
    return df

@st.cache_data(ttl=20)
def load_andreia_castracao() -> pd.DataFrame:
    hdrs = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Prefer": "count=none"}
    rows, offset, page = [], 0, 1000
    while True:
        url = f"{SUPABASE_URL}/rest/v1/base_andreia_castracao?select=*&limit={page}&offset={offset}"
        r = requests.get(url, headers=hdrs, timeout=15)
        r.raise_for_status()
        batch = r.json()
        rows.extend(batch)
        if len(batch) < page: break
        offset += page
    if not rows: return pd.DataFrame()
    df = pd.DataFrame(rows)
    def _norm(c):
        c = unicodedata.normalize("NFKD", str(c)).encode("ascii","ignore").decode("ascii")
        return re.sub(r"[^\w]+", "_", c.strip()).upper().strip("_")
    df.columns = [_norm(c) for c in df.columns]
    date_col = next((c for c in df.columns if "CRIADO" in c or "DATA" in c or "DATE" in c or "CREATED" in c), None)
    if date_col:
        df["DATA"] = (pd.to_datetime(df[date_col], errors="coerce", utc=True)
                      .dt.tz_convert(BRASILIA).dt.tz_localize(None))
        df = df.sort_values("DATA", ascending=False, na_position="last")
    if "BAIRRO" in df.columns:
        df["BAIRRO"] = df["BAIRRO"].str.upper().str.strip()
    # normaliza especie
    esp_col = next((c for c in df.columns if "ESPECIE" in c or "ESPÉC" in c), None)
    if esp_col and esp_col != "ESPECIE": df = df.rename(columns={esp_col: "ESPECIE"})
    if "ESPECIE" in df.columns: df["ESPECIE"] = df["ESPECIE"].str.upper().str.strip()
    # normaliza genero
    if "GENERO" in df.columns: df["GENERO"] = df["GENERO"].str.capitalize().str.strip()
    # normaliza porte
    if "PORTE" in df.columns: df["PORTE"] = df["PORTE"].str.capitalize().str.strip()
    col_num = next((c for c in df.columns if c in ("N_", "N", "NUM", "NUMERO")), None)
    if col_num and col_num != "NUM": df = df.rename(columns={col_num: "NUM"})
    return df

@st.cache_data(ttl=20)
def load_guti_visita() -> pd.DataFrame:
    hdrs = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Prefer": "count=none"}
    rows, offset, page = [], 0, 1000
    while True:
        url = f"{SUPABASE_URL}/rest/v1/lead_guti_visita?select=*&order=data.desc&limit={page}&offset={offset}"
        r = requests.get(url, headers=hdrs, timeout=15)
        r.raise_for_status()
        batch = r.json()
        rows.extend(batch)
        if len(batch) < page: break
        offset += page
    if not rows: return pd.DataFrame()
    df = pd.DataFrame(rows)
    def _norm(c):
        c = unicodedata.normalize("NFKD", str(c)).encode("ascii","ignore").decode("ascii")
        return re.sub(r"[^\w]+", "_", c.strip()).upper().strip("_")
    df.columns = [_norm(c) for c in df.columns]
    date_col = next((c for c in df.columns if c == "DATA" or "DATA" in c or "DATE" in c), None)
    if date_col:
        df["DATA"] = (pd.to_datetime(df[date_col], errors="coerce", utc=True)
                      .dt.tz_convert(BRASILIA).dt.tz_localize(None))
        df = df.sort_values("DATA", ascending=False, na_position="last")
    # consolida nome
    if "NAME" in df.columns:
        df["NOME"] = df["NAME"].str.strip()
    elif "FIRST_NAME" in df.columns:
        df["NOME"] = (df["FIRST_NAME"].fillna("") + " " + df.get("LAST_NAME", pd.Series("", index=df.index)).fillna("")).str.strip()
    # normaliza telefone
    if "PHONE" in df.columns and "TELEFONE" not in df.columns:
        df = df.rename(columns={"PHONE": "TELEFONE"})
    return df


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

BAIRRO_COORDS = {
    "JD CUMBICA":          {"lat":-23.4183,"lon":-46.4611},
    "JARDIM CUMBICA":      {"lat":-23.4183,"lon":-46.4611},
    "RES PRQ CUMBICA":     {"lat":-23.4150,"lon":-46.4680},
    "JD PTE ALTA I":       {"lat":-23.4320,"lon":-46.4720},
    "JD PTE ALTA":         {"lat":-23.4320,"lon":-46.4720},
    "PRQ RES BAMBI":       {"lat":-23.4580,"lon":-46.5050},
    "JD STA HELENA":       {"lat":-23.4650,"lon":-46.4830},
    "JARDIM SANTA HELENA": {"lat":-23.4650,"lon":-46.4830},
    "JD ADRIANA":          {"lat":-23.4700,"lon":-46.4850},
    "JD TABATINGA":        {"lat":-23.4480,"lon":-46.5180},
    "JARDIM TABATINGA":    {"lat":-23.4480,"lon":-46.5180},
    "JD S JOÃO":           {"lat":-23.4820,"lon":-46.4960},
    "JARDIM SÃO JOÃO":     {"lat":-23.4820,"lon":-46.4960},
    "MACEDO":              {"lat":-23.4650,"lon":-46.5120},
    "A GARIBALDI":         {"lat":-23.4560,"lon":-46.5200},
    "VL UNIÃO":            {"lat":-23.4780,"lon":-46.5070},
    "VILA UNIÃO":          {"lat":-23.4780,"lon":-46.5070},
    "JD HANNA":            {"lat":-23.4730,"lon":-46.5160},
    "JD PARAVENTI":        {"lat":-23.4900,"lon":-46.5130},
    "PRQ STOS DUMONT":     {"lat":-23.4550,"lon":-46.5260},
    "JD TRANQÜILIDADE":    {"lat":-23.5030,"lon":-46.5290},
    "JD TRANQUILIDADE":    {"lat":-23.5030,"lon":-46.5290},
    "C SOBERANA":          {"lat":-23.4480,"lon":-46.5390},
    "JD STA PAULA":        {"lat":-23.4860,"lon":-46.5010},
    "JARDIM SANTA PAULA":  {"lat":-23.4860,"lon":-46.5010},
    "PRQ PIRATININGA":     {"lat":-23.4980,"lon":-46.5230},
    "PRQ CONTINENTAL II":  {"lat":-23.4440,"lon":-46.5120},
    "JD DIVINOLÂNDIA":     {"lat":-23.4760,"lon":-46.5300},
    "JD DIVOLANDIA":       {"lat":-23.4760,"lon":-46.5300},
    "JD VL GALVÃO":        {"lat":-23.4910,"lon":-46.5190},
    "JD CARDOSO":          {"lat":-23.4870,"lon":-46.5250},
    "JD ADRIANA":          {"lat":-23.4700,"lon":-46.4890},
    # SP Zona Leste
    "VILA CARRAO":         {"lat":-23.5389,"lon":-46.5417},
    "VILA CARRÃO":         {"lat":-23.5389,"lon":-46.5417},
    "VILA CARRAO":         {"lat":-23.5389,"lon":-46.5417},
    "VL CARRÃO":           {"lat":-23.5389,"lon":-46.5417},
    "VL CARRAO":           {"lat":-23.5389,"lon":-46.5417},
    "VILA FORMOSA":        {"lat":-23.5381,"lon":-46.5283},
    "VL FORMOSA":          {"lat":-23.5381,"lon":-46.5283},
    "TATUAPE":             {"lat":-23.5372,"lon":-46.5775},
    "TATUAPÉ":             {"lat":-23.5372,"lon":-46.5775},
    "VILA RICA":           {"lat":-23.5550,"lon":-46.5200},
    "VL RICA":             {"lat":-23.5550,"lon":-46.5200},
    "JARDIM SANTA MARIA":  {"lat":-23.5700,"lon":-46.5100},
    "JD SANTA MARIA":      {"lat":-23.5700,"lon":-46.5100},
    "PENHA":               {"lat":-23.5239,"lon":-46.5378},
    "VILA MATILDE":        {"lat":-23.5297,"lon":-46.5186},
    "VL MATILDE":          {"lat":-23.5297,"lon":-46.5186},
    "AGUA RASA":           {"lat":-23.5514,"lon":-46.5664},
    "ÁGUA RASA":           {"lat":-23.5514,"lon":-46.5664},
    "MOOCA":               {"lat":-23.5500,"lon":-46.5950},
    "BELENZINHO":          {"lat":-23.5444,"lon":-46.6036},
    "ANALIA FRANCO":       {"lat":-23.5442,"lon":-46.5289},
    "ANÁLIA FRANCO":       {"lat":-23.5442,"lon":-46.5289},
    "VILA PRUDENTE":       {"lat":-23.5786,"lon":-46.5550},
    "VL PRUDENTE":         {"lat":-23.5786,"lon":-46.5550},
    "SAPOPEMBA":           {"lat":-23.5900,"lon":-46.5086},
    "CIDADE LIDER":        {"lat":-23.5756,"lon":-46.4836},
    "CIDADE LÍDER":        {"lat":-23.5756,"lon":-46.4836},
    "ITAQUERA":            {"lat":-23.5386,"lon":-46.4558},
    "VILA IONE":           {"lat":-23.5550,"lon":-46.5350},
    "VL IONE":             {"lat":-23.5550,"lon":-46.5350},
    "PARQUE NOVO MUNDO":   {"lat":-23.5039,"lon":-46.5614},
    "PRQ NOVO MUNDO":      {"lat":-23.5039,"lon":-46.5614},
    "CANGAIBA":            {"lat":-23.4981,"lon":-46.5319},
    "VILA ESPERANCA":      {"lat":-23.5233,"lon":-46.5094},
    "VILA ESPERANÇA":      {"lat":-23.5233,"lon":-46.5094},
}

def bairro_key(nome):
    n = unicodedata.normalize("NFKD", str(nome)).encode("ascii","ignore").decode("ascii").upper().strip()
    return BAIRRO_COORDS.get(n) or BAIRRO_COORDS.get(nome.upper().strip())

def map_bairro(df, col="BAIRRO", label="leads", height=440):
    if col not in df.columns or df.empty: return None
    cnt = df[col].value_counts().reset_index()
    cnt.columns = [col, label]
    rows = []
    for _, r in cnt.iterrows():
        coords = bairro_key(str(r[col]))
        if coords:
            rows.append({"bairro": r[col], label: int(r[label]),
                         "lat": coords["lat"], "lon": coords["lon"]})
    if not rows: return None
    mdf = pd.DataFrame(rows); mx = mdf[label].max()
    fig = go.Figure()
    fig.add_trace(go.Scattermapbox(
        lat=mdf["lat"], lon=mdf["lon"],
        mode="markers",
        marker=dict(
            size=mdf[label].apply(lambda v: 14 + 32*(v/mx)**0.5),
            color=mdf[label], colorscale=[[0,PURPLE],[0.5,ORANGE],[1,"#ef4444"]],
            showscale=False, opacity=0.85,
        ),
        text=mdf.apply(lambda r: f"<b>{r['bairro']}</b><br>{fmt_num(r[label])} {label}", axis=1),
        hoverinfo="text",
    ))
    fig.update_layout(
        mapbox=dict(style=MAP_STYLE, center=dict(lat=-23.460, lon=-46.510), zoom=11.5,
                    layers=_sp_layer()),
        **base_layout(height=height),
    )
    return fig

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
    "🏘️  Latidah Andreia": {
        "tipo": "andreia",
        "tabela": "base protetores andreia",
    },
    "🐾  Latidah Buffo": {
        "tipo": "buffo",
        "tabela": "base_buffo",
    },
    "📍  Guti Visita": {
        "tipo": "visita",
        "tabela": "lead_guti_visita",
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

    # Filtro de base — aba Andreia tem duas bases distintas
    andreia_proj = None
    if pagina_cfg.get("tipo") == "andreia":
        andreia_proj = st.selectbox("PROJETO", ["Base Protetores", "Base Castração"], index=0)
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
elif tipo == "andreia":
    with st.spinner(""):
        try:
            df_all = load_andreia_castracao() if andreia_proj == "Base Castração" else load_andreia()
            erro = None
        except Exception as e: df_all = pd.DataFrame(); erro = str(e)
elif tipo == "buffo":
    with st.spinner(""):
        try:    df_all = load_buffo(); erro = None
        except Exception as e: df_all = pd.DataFrame(); erro = str(e)
elif tipo == "visita":
    with st.spinner(""):
        try:    df_all = load_guti_visita(); erro = None
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
elif tipo == "andreia":
    tab_an_vis, tab_an_cont = st.tabs(["  📊  Visão Geral  ","  📋  Contatos  "])
elif tipo == "buffo":
    tab_bf_vis, tab_bf_cad = st.tabs(["  📊  Visão Geral  ","  📋  Cadastros  "])
elif tipo == "visita":
    tab_vs_vis, tab_vs_lista = st.tabs(["  📊  Visão Geral  ","  📋  Contatos  "])
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
                st.markdown('<div class="chart-title">Campanhas (UTM) — ranking por zona</div>'
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
                    rts = df["UTM_SOURCE"].fillna("(direto)").value_counts().reset_index()
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

# ══════════════════════════ LATIDAH ANDREIA ═══════════════════════════════════
if tipo == "andreia":
    is_castracao = (andreia_proj == "Base Castração")
    BAIRRO_COL = next((c for c in df.columns if "BAIRRO"    in c), "BAIRRO")
    CEP_COL    = next((c for c in df.columns if "CEP"       in c), "CEP")
    TIPO_COL   = next((c for c in df.columns if c == "TIPO"), "TIPO")
    LOG_COL    = next((c for c in df.columns if "LOGRADOURO" in c or "LOGRADO" in c), "LOGRADOURO")
    # colunas exclusivas da base castração
    ESP_COL    = "ESPECIE"   if "ESPECIE"   in df.columns else None
    GEN_AN_COL = "GENERO"    if "GENERO"    in df.columns else None
    PRT_COL    = "PORTE"     if "PORTE"     in df.columns else None
    NOME_AN_COL= next((c for c in df.columns if "NOME" in c and "ANIMAL" in c), None)
    PEL_COL    = next((c for c in df.columns if "PELAGEM" in c or "COR" in c), None)

    total_an  = len(df)
    n_bairros = df[BAIRRO_COL].nunique() if BAIRRO_COL in df.columns else 0
    n_ceps    = df[CEP_COL].nunique()    if CEP_COL    in df.columns else 0
    n_especies= df[ESP_COL].nunique()    if ESP_COL                  else 0

    with tab_an_vis:
        # ── KPIs ──────────────────────────────────────────────────────────────
        k1, k2, k3, k4 = st.columns(4, gap="medium")
        k1.markdown(kpi_card(PURPLE, "Total de Leads", fmt_num(total_an),
                             badge="contatos cadastrados", badge_color="rgba(139,92,246,.12)", badge_txt=PURPLE),
                    unsafe_allow_html=True)
        k2.markdown(kpi_card(ORANGE, "Bairros", fmt_num(n_bairros),
                             badge="bairros alcançados", badge_color="rgba(249,115,22,.12)", badge_txt=ORANGE),
                    unsafe_allow_html=True)
        k3.markdown(kpi_card(GREEN, "CEPs", fmt_num(n_ceps),
                             badge="regiões distintas", badge_color="rgba(16,185,129,.12)", badge_txt=GREEN),
                    unsafe_allow_html=True)
        if is_castracao and ESP_COL:
            k4.markdown(kpi_card(AMBER, "Espécies", fmt_num(n_especies),
                                 badge="felina / canina", badge_color="rgba(245,158,11,.12)", badge_txt=AMBER),
                        unsafe_allow_html=True)
        else:
            n_tipos = df[TIPO_COL].nunique() if TIPO_COL in df.columns else 0
            k4.markdown(kpi_card(AMBER, "Tipos", fmt_num(n_tipos),
                                 badge="tipos de logradouro", badge_color="rgba(245,158,11,.12)", badge_txt=AMBER),
                        unsafe_allow_html=True)

        if df.empty:
            st.info("Nenhum contato encontrado."); st.stop()

        # ── Engajamento no Bot ────────────────────────────────────────────────
        section("Engajamento no Bot")
        b1, b2, b3 = st.columns(3, gap="medium")
        b1.markdown(kpi_card(PURPLE, "Taxa de Resposta", "56%",
                             badge="leads que responderam ao bot", badge_color="rgba(139,92,246,.12)", badge_txt=PURPLE),
                    unsafe_allow_html=True)
        b2.markdown(kpi_card(ORANGE, "2+ Interações", "40%",
                             badge="interagiram mais de 2x com o bot", badge_color="rgba(249,115,22,.12)", badge_txt=ORANGE),
                    unsafe_allow_html=True)
        b3.markdown(kpi_card(GREEN, "3+ Respostas", "30%",
                             badge="responderam 3 ou mais vezes", badge_color="rgba(16,185,129,.12)", badge_txt=GREEN),
                    unsafe_allow_html=True)

        # ── Mapa por Bairro ───────────────────────────────────────────────────
        section("Distribuição Geográfica")
        mfig_an = map_bairro(df, col=BAIRRO_COL, label="leads", height=460)
        if mfig_an:
            st.plotly_chart(mfig_an, use_container_width=True,
                            config={"displayModeBar": False, "scrollZoom": True})
        else:
            with st.container(border=True):
                st.markdown('<div class="chart-title">Ranking de Bairros</div>'
                            '<div class="chart-sub">Volume de leads por bairro</div>',
                            unsafe_allow_html=True)
                rb = df[BAIRRO_COL].fillna("Não informado").value_counts().head(20).reset_index()
                rb.columns = ["Bairro", "Qtd"]; rb = rb.sort_values("Qtd")
                fig = go.Figure(go.Bar(
                    x=rb["Qtd"], y=rb["Bairro"], orientation="h",
                    marker=dict(color=rb["Qtd"], colorscale=[[0, PURPLE],[1, ORANGE]],
                                showscale=False, line=dict(width=0)),
                    text=rb["Qtd"], textposition="outside",
                    textfont=dict(color=MUTED2, size=11),
                ))
                fig.update_layout(**base_layout(height=520,
                    xaxis=dict(gridcolor=GRID_CLR, showline=False, zeroline=False),
                    yaxis=dict(gridcolor="rgba(0,0,0,0)", showline=False, tickfont_size=11),
                    bargap=0.3))
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        # ── Análise de Localização ─────────────────────────────────────────────
        section("Análise de Localização")
        col_a, col_b = st.columns(2, gap="medium")

        with col_a:
            with st.container(border=True):
                st.markdown('<div class="chart-title">Top Bairros</div>'
                            '<div class="chart-sub">Bairros com maior concentração de leads</div>',
                            unsafe_allow_html=True)
                if BAIRRO_COL in df.columns:
                    rb2 = df[BAIRRO_COL].fillna("Não informado").value_counts().head(15).reset_index()
                    rb2.columns = ["Bairro", "Qtd"]; rb2 = rb2.sort_values("Qtd")
                    fig = go.Figure(go.Bar(
                        x=rb2["Qtd"], y=rb2["Bairro"], orientation="h",
                        marker=dict(color=rb2["Qtd"], colorscale=[[0, PURPLE],[1, ORANGE]],
                                    showscale=False, line=dict(width=0)),
                        text=rb2["Qtd"], textposition="outside",
                        textfont=dict(color=MUTED2, size=11),
                    ))
                    fig.update_layout(**base_layout(height=380,
                        xaxis=dict(gridcolor=GRID_CLR, showline=False, zeroline=False, tickfont_size=10),
                        yaxis=dict(gridcolor="rgba(0,0,0,0)", showline=False, tickfont_size=11),
                        bargap=0.3))
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        with col_b:
            with st.container(border=True):
                st.markdown('<div class="chart-title">Tipo de Logradouro</div>'
                            '<div class="chart-sub">Distribuição por RUA / AVENIDA / ESTRADA</div>',
                            unsafe_allow_html=True)
                if TIPO_COL in df.columns:
                    rt = df[TIPO_COL].fillna("Não informado").value_counts().reset_index()
                    rt.columns = ["Tipo", "Qtd"]; rt = rt.sort_values("Qtd")
                    fig = go.Figure(go.Bar(
                        x=rt["Qtd"], y=rt["Tipo"], orientation="h",
                        marker=dict(color=rt["Qtd"], colorscale=[[0, GREEN],[1, AMBER]],
                                    showscale=False, line=dict(width=0)),
                        text=rt["Qtd"], textposition="outside",
                        textfont=dict(color=MUTED2, size=11),
                    ))
                    fig.update_layout(**base_layout(height=380,
                        xaxis=dict(gridcolor=GRID_CLR, showline=False, zeroline=False, tickfont_size=10),
                        yaxis=dict(gridcolor="rgba(0,0,0,0)", showline=False, tickfont_size=12),
                        bargap=0.35))
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        # ── Perfil dos Pets (exclusivo Base Castração) ─────────────────────────
        if is_castracao:
            section("Perfil dos Pets")
            pa, pb, pc = st.columns(3, gap="medium")

            with pa:
                with st.container(border=True):
                    st.markdown('<div class="chart-title">Espécie</div>'
                                '<div class="chart-sub">Felina vs Canina</div>',
                                unsafe_allow_html=True)
                    if ESP_COL:
                        te = df[ESP_COL].fillna("Não informado").value_counts().reset_index()
                        te.columns = ["Espécie", "Qtd"]; te = te.sort_values("Qtd")
                        fig = go.Figure(go.Bar(
                            x=te["Qtd"], y=te["Espécie"], orientation="h",
                            marker=dict(color=[ORANGE if "CAN" in str(v) else PURPLE
                                               for v in te["Espécie"]], line=dict(width=0)),
                            text=te["Qtd"], textposition="outside",
                            textfont=dict(color=MUTED2, size=11),
                        ))
                        fig.update_layout(**base_layout(height=240,
                            xaxis=dict(gridcolor=GRID_CLR, showline=False, zeroline=False, tickfont_size=10),
                            yaxis=dict(gridcolor="rgba(0,0,0,0)", showline=False, tickfont_size=12),
                            bargap=0.4))
                        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

            with pb:
                with st.container(border=True):
                    st.markdown('<div class="chart-title">Gênero</div>'
                                '<div class="chart-sub">Macho vs Fêmea</div>',
                                unsafe_allow_html=True)
                    if GEN_AN_COL:
                        tg = df[GEN_AN_COL].fillna("Não informado").value_counts().reset_index()
                        tg.columns = ["Gênero", "Qtd"]; tg = tg.sort_values("Qtd")
                        fig = go.Figure(go.Bar(
                            x=tg["Qtd"], y=tg["Gênero"], orientation="h",
                            marker=dict(color=tg["Qtd"], colorscale=[[0, GREEN],[1, AMBER]],
                                        showscale=False, line=dict(width=0)),
                            text=tg["Qtd"], textposition="outside",
                            textfont=dict(color=MUTED2, size=11),
                        ))
                        fig.update_layout(**base_layout(height=240,
                            xaxis=dict(gridcolor=GRID_CLR, showline=False, zeroline=False, tickfont_size=10),
                            yaxis=dict(gridcolor="rgba(0,0,0,0)", showline=False, tickfont_size=12),
                            bargap=0.4))
                        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

            with pc:
                with st.container(border=True):
                    st.markdown('<div class="chart-title">Porte</div>'
                                '<div class="chart-sub">Pequeno / Médio / Grande</div>',
                                unsafe_allow_html=True)
                    if PRT_COL:
                        tp = df[PRT_COL].fillna("Não informado").value_counts().reset_index()
                        tp.columns = ["Porte", "Qtd"]; tp = tp.sort_values("Qtd")
                        fig = go.Figure(go.Bar(
                            x=tp["Qtd"], y=tp["Porte"], orientation="h",
                            marker=dict(color=tp["Qtd"], colorscale=[[0, PURPLE],[1, ORANGE]],
                                        showscale=False, line=dict(width=0)),
                            text=tp["Qtd"], textposition="outside",
                            textfont=dict(color=MUTED2, size=11),
                        ))
                        fig.update_layout(**base_layout(height=240,
                            xaxis=dict(gridcolor=GRID_CLR, showline=False, zeroline=False, tickfont_size=10),
                            yaxis=dict(gridcolor="rgba(0,0,0,0)", showline=False, tickfont_size=12),
                            bargap=0.4))
                        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        # ── Top Logradouros ────────────────────────────────────────────────────
        section("Top Logradouros")
        with st.container(border=True):
            st.markdown('<div class="chart-title">Ruas e Avenidas com mais leads</div>'
                        '<div class="chart-sub">Top 15 logradouros por volume</div>',
                        unsafe_allow_html=True)
            if LOG_COL in df.columns:
                rl = df[LOG_COL].fillna("Não informado").value_counts().head(15).reset_index()
                rl.columns = ["Logradouro", "Qtd"]; rl = rl.sort_values("Qtd")
                fig = go.Figure(go.Bar(
                    x=rl["Qtd"], y=rl["Logradouro"], orientation="h",
                    marker=dict(color=rl["Qtd"], colorscale=[[0, PURPLE],[0.5, ORANGE],[1, "#ef4444"]],
                                showscale=False, line=dict(width=0)),
                    text=rl["Qtd"], textposition="outside",
                    textfont=dict(color=MUTED2, size=11),
                ))
                fig.update_layout(**base_layout(height=420,
                    xaxis=dict(gridcolor=GRID_CLR, showline=False, zeroline=False, tickfont_size=10),
                    yaxis=dict(gridcolor="rgba(0,0,0,0)", showline=False, tickfont_size=11),
                    bargap=0.3))
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        # ── Métricas detalhadas ────────────────────────────────────────────────
        section("Métricas Detalhadas")
        dt1, dt2 = st.columns(2, gap="medium")

        with dt1:
            with st.container(border=True):
                st.markdown('<div class="chart-title" style="margin-bottom:12px">Por Bairro</div>',
                            unsafe_allow_html=True)
                if BAIRRO_COL in df.columns:
                    tb = df[BAIRRO_COL].fillna("Não informado").value_counts().reset_index()
                    tb.columns = ["Bairro", "Leads"]
                    tb["% Total"] = (tb["Leads"] / total_an * 100).round(1).astype(str) + "%"
                    st.dataframe(tb, use_container_width=True, hide_index=True, height=340)

        with dt2:
            with st.container(border=True):
                st.markdown('<div class="chart-title" style="margin-bottom:12px">Por CEP</div>',
                            unsafe_allow_html=True)
                if CEP_COL in df.columns:
                    tc = df[CEP_COL].fillna("Não informado").value_counts().reset_index()
                    tc.columns = ["CEP", "Leads"]
                    tc["% Total"] = (tc["Leads"] / total_an * 100).round(1).astype(str) + "%"
                    st.dataframe(tc, use_container_width=True, hide_index=True, height=340)

    with tab_an_cont:
        sc, cc = st.columns([4, 1])
        an_search = sc.text_input("", placeholder="🔍  Buscar por nome, bairro, CEP, logradouro...",
                                  label_visibility="collapsed")
        cc.markdown(f'<p style="color:{MUTED2};font-size:12px;text-align:right;padding-top:10px">'
                    f'{fmt_num(total_an)} registros</p>', unsafe_allow_html=True)
        df_an = df.copy()
        if an_search:
            an_cols = ["NOME", BAIRRO_COL, CEP_COL, LOG_COL, "TELEFONE", "CELULAR",
                       ESP_COL, NOME_AN_COL]
            an_mask = pd.Series(False, index=df_an.index)
            for c in an_cols:
                if c and c in df_an.columns:
                    an_mask |= df_an[c].astype(str).str.contains(an_search, case=False, na=False)
            df_an = df_an[an_mask]
        base_cols = ["NOME", "TELEFONE", "CELULAR", BAIRRO_COL, CEP_COL, TIPO_COL, LOG_COL, "NUM", "RG", "CPF"]
        pet_cols  = [NOME_AN_COL, ESP_COL, GEN_AN_COL, PRT_COL, PEL_COL] if is_castracao else []
        an_show = [c for c in base_cols + pet_cols if c and c in df_an.columns]
        st.dataframe(df_an[an_show], use_container_width=True, hide_index=True, height=560)

    st.stop()   # andreia complete

# ══════════════════════════════ LATIDAH BUFFO ════════════════════════════════
if tipo == "buffo":
    # detecta colunas
    PET_COL    = "TIPO_ANIMAL" if "TIPO_ANIMAL" in df.columns else None
    GEN_COL    = "GENERO"      if "GENERO"      in df.columns else None
    NOME_PET   = next((c for c in df.columns if "NOME" in c and "ANIMAL" in c), None) \
                 or next((c for c in df.columns if "NOME" in c and "COMPLETO" not in c and "ASSE" not in c), None)
    EQUIPE_COL = next((c for c in df.columns if "EQUIPE" in c), None)
    COMP_COL   = "COMPLEMENTO" if "COMPLEMENTO" in df.columns else None
    IDADE_COL  = next((c for c in df.columns if "IDADE" in c), None)
    ASSE_COL   = next((c for c in df.columns if "ASSE" in c or "ASSESSOR" in c), None)

    total_bf   = len(df)
    n_bairros  = df["BAIRRO"].nunique()         if "BAIRRO"    in df.columns else 0
    n_equipes  = df[EQUIPE_COL].nunique()       if EQUIPE_COL  else 0
    n_ceps     = df["CEP"].nunique()            if "CEP"       in df.columns else 0

    # contagem cachorros vs gatos
    cachorros = gatos = 0
    if PET_COL:
        cachorros = df[PET_COL].str.contains("CACHORRO", na=False).sum()
        gatos     = df[PET_COL].str.contains("GATO", na=False).sum()

    with tab_bf_vis:
        # ── KPIs ──────────────────────────────────────────────────────────────
        k1, k2, k3, k4 = st.columns(4, gap="medium")
        k1.markdown(kpi_card(PURPLE, "Total de Leads", fmt_num(total_bf),
                             badge=f"Período: {periodo}", badge_color="rgba(139,92,246,.12)", badge_txt=PURPLE),
                    unsafe_allow_html=True)
        k2.markdown(kpi_card(ORANGE, "Bairros", fmt_num(n_bairros),
                             badge="regiões alcançadas", badge_color="rgba(249,115,22,.12)", badge_txt=ORANGE),
                    unsafe_allow_html=True)
        k3.markdown(kpi_card(GREEN, "Cachorros", fmt_num(cachorros),
                             badge=f"{int(cachorros/total_bf*100) if total_bf else 0}% dos pets",
                             badge_color="rgba(16,185,129,.12)", badge_txt=GREEN),
                    unsafe_allow_html=True)
        k4.markdown(kpi_card(AMBER, "Gatos", fmt_num(gatos),
                             badge=f"{int(gatos/total_bf*100) if total_bf else 0}% dos pets",
                             badge_color="rgba(245,158,11,.12)", badge_txt=AMBER),
                    unsafe_allow_html=True)

        if df.empty:
            st.info("Nenhum cadastro no período selecionado."); st.stop()

        # ── Engajamento no Bot ────────────────────────────────────────────────
        section("Engajamento no Bot")
        b1, b2, b3 = st.columns(3, gap="medium")
        b1.markdown(kpi_card(PURPLE, "Taxa de Resposta", "56%",
                             badge="leads que responderam ao bot", badge_color="rgba(139,92,246,.12)", badge_txt=PURPLE),
                    unsafe_allow_html=True)
        b2.markdown(kpi_card(ORANGE, "2+ Interações", "40%",
                             badge="interagiram mais de 2x com o bot", badge_color="rgba(249,115,22,.12)", badge_txt=ORANGE),
                    unsafe_allow_html=True)
        b3.markdown(kpi_card(GREEN, "3+ Respostas", "30%",
                             badge="responderam 3 ou mais vezes", badge_color="rgba(16,185,129,.12)", badge_txt=GREEN),
                    unsafe_allow_html=True)

        # ── Crescimento ────────────────────────────────────────────────────────
        if "DATA" in df.columns:
            section("Crescimento")
            with st.container(border=True):
                st.markdown('<div class="chart-title">Cadastros por dia</div>'
                            '<div class="chart-sub">Evolução no período selecionado</div>',
                            unsafe_allow_html=True)
                st.plotly_chart(area_chart(df), use_container_width=True, config={"displayModeBar": False})

        # ── Mapa por Bairro ────────────────────────────────────────────────────
        section("Distribuição Geográfica")
        mfig_bf = map_bairro(df, col="BAIRRO", label="leads", height=460) if "BAIRRO" in df.columns else None
        if mfig_bf:
            st.plotly_chart(mfig_bf, use_container_width=True,
                            config={"displayModeBar": False, "scrollZoom": True})
        elif "BAIRRO" in df.columns:
            with st.container(border=True):
                rb = df["BAIRRO"].fillna("Não informado").value_counts().head(20).reset_index()
                rb.columns = ["Bairro", "Qtd"]; rb = rb.sort_values("Qtd")
                fig = go.Figure(go.Bar(
                    x=rb["Qtd"], y=rb["Bairro"], orientation="h",
                    marker=dict(color=rb["Qtd"], colorscale=[[0, PURPLE],[1, ORANGE]],
                                showscale=False, line=dict(width=0)),
                    text=rb["Qtd"], textposition="outside",
                    textfont=dict(color=MUTED2, size=11),
                ))
                fig.update_layout(**base_layout(height=520,
                    xaxis=dict(gridcolor=GRID_CLR, showline=False, zeroline=False),
                    yaxis=dict(gridcolor="rgba(0,0,0,0)", showline=False, tickfont_size=11),
                    bargap=0.3))
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        # ── Pets ──────────────────────────────────────────────────────────────
        section("Perfil dos Pets")
        p1, p2, p3 = st.columns(3, gap="medium")

        with p1:
            with st.container(border=True):
                st.markdown('<div class="chart-title">Cachorro ou Gato</div>'
                            '<div class="chart-sub">Distribuição por tipo de animal</div>',
                            unsafe_allow_html=True)
                if PET_COL:
                    tp = df[PET_COL].fillna("Não informado").value_counts().reset_index()
                    tp.columns = ["Tipo", "Qtd"]; tp = tp.sort_values("Qtd")
                    fig = go.Figure(go.Bar(
                        x=tp["Qtd"], y=tp["Tipo"], orientation="h",
                        marker=dict(color=[GREEN if "CACHORRO" in str(t) else AMBER if "GATO" in str(t) else MUTED
                                           for t in tp["Tipo"]],
                                    line=dict(width=0)),
                        text=tp["Qtd"], textposition="outside",
                        textfont=dict(color=MUTED2, size=11),
                    ))
                    fig.update_layout(**base_layout(height=260,
                        xaxis=dict(gridcolor=GRID_CLR, showline=False, zeroline=False, tickfont_size=10),
                        yaxis=dict(gridcolor="rgba(0,0,0,0)", showline=False, tickfont_size=12),
                        bargap=0.4))
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        with p2:
            with st.container(border=True):
                st.markdown('<div class="chart-title">Gênero do Pet</div>'
                            '<div class="chart-sub">Distribuição por sexo</div>',
                            unsafe_allow_html=True)
                if GEN_COL:
                    tg = df[GEN_COL].fillna("Não informado").value_counts().reset_index()
                    tg.columns = ["Gênero", "Qtd"]; tg = tg.sort_values("Qtd")
                    fig = go.Figure(go.Bar(
                        x=tg["Qtd"], y=tg["Gênero"], orientation="h",
                        marker=dict(color=tg["Qtd"], colorscale=[[0, PURPLE],[1, ORANGE]],
                                    showscale=False, line=dict(width=0)),
                        text=tg["Qtd"], textposition="outside",
                        textfont=dict(color=MUTED2, size=11),
                    ))
                    fig.update_layout(**base_layout(height=260,
                        xaxis=dict(gridcolor=GRID_CLR, showline=False, zeroline=False, tickfont_size=10),
                        yaxis=dict(gridcolor="rgba(0,0,0,0)", showline=False, tickfont_size=12),
                        bargap=0.4))
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        with p3:
            with st.container(border=True):
                st.markdown('<div class="chart-title">Tipo de Moradia</div>'
                            '<div class="chart-sub">Casa vs Apartamento</div>',
                            unsafe_allow_html=True)
                if COMP_COL:
                    def _moradia(v):
                        v = str(v).upper()
                        if "APAR" in v or "APT" in v: return "Apartamento"
                        if "CASA" in v: return "Casa"
                        return "Outro"
                    tm = df[COMP_COL].apply(_moradia).value_counts().reset_index()
                    tm.columns = ["Moradia", "Qtd"]; tm = tm.sort_values("Qtd")
                    fig = go.Figure(go.Bar(
                        x=tm["Qtd"], y=tm["Moradia"], orientation="h",
                        marker=dict(color=tm["Qtd"], colorscale=[[0, GREEN],[1, AMBER]],
                                    showscale=False, line=dict(width=0)),
                        text=tm["Qtd"], textposition="outside",
                        textfont=dict(color=MUTED2, size=11),
                    ))
                    fig.update_layout(**base_layout(height=260,
                        xaxis=dict(gridcolor=GRID_CLR, showline=False, zeroline=False, tickfont_size=10),
                        yaxis=dict(gridcolor="rgba(0,0,0,0)", showline=False, tickfont_size=12),
                        bargap=0.4))
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        # ── Bairros + Equipes ──────────────────────────────────────────────────
        section("Análise de Localização e Equipes")
        la1, la2 = st.columns(2, gap="medium")

        with la1:
            with st.container(border=True):
                st.markdown('<div class="chart-title">Top Bairros</div>'
                            '<div class="chart-sub">Bairros com maior volume de cadastros</div>',
                            unsafe_allow_html=True)
                if "BAIRRO" in df.columns:
                    rb2 = df["BAIRRO"].fillna("Não informado").value_counts().head(15).reset_index()
                    rb2.columns = ["Bairro", "Qtd"]; rb2 = rb2.sort_values("Qtd")
                    fig = go.Figure(go.Bar(
                        x=rb2["Qtd"], y=rb2["Bairro"], orientation="h",
                        marker=dict(color=rb2["Qtd"], colorscale=[[0, PURPLE],[1, ORANGE]],
                                    showscale=False, line=dict(width=0)),
                        text=rb2["Qtd"], textposition="outside",
                        textfont=dict(color=MUTED2, size=11),
                    ))
                    fig.update_layout(**base_layout(height=400,
                        xaxis=dict(gridcolor=GRID_CLR, showline=False, zeroline=False, tickfont_size=10),
                        yaxis=dict(gridcolor="rgba(0,0,0,0)", showline=False, tickfont_size=11),
                        bargap=0.3))
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        with la2:
            with st.container(border=True):
                st.markdown('<div class="chart-title">Performance por Equipe</div>'
                            '<div class="chart-sub">Cadastros por equipe de campo</div>',
                            unsafe_allow_html=True)
                if EQUIPE_COL:
                    re2 = df[EQUIPE_COL].fillna("Não informado").value_counts().head(15).reset_index()
                    re2.columns = ["Equipe", "Qtd"]; re2 = re2.sort_values("Qtd")
                    fig = go.Figure(go.Bar(
                        x=re2["Qtd"], y=re2["Equipe"], orientation="h",
                        marker=dict(color=re2["Qtd"], colorscale=[[0, GREEN],[1, AMBER]],
                                    showscale=False, line=dict(width=0)),
                        text=re2["Qtd"], textposition="outside",
                        textfont=dict(color=MUTED2, size=11),
                    ))
                    fig.update_layout(**base_layout(height=400,
                        xaxis=dict(gridcolor=GRID_CLR, showline=False, zeroline=False, tickfont_size=10),
                        yaxis=dict(gridcolor="rgba(0,0,0,0)", showline=False, tickfont_size=12),
                        bargap=0.35))
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        # ── Métricas detalhadas ────────────────────────────────────────────────
        section("Métricas Detalhadas")
        md1, md2 = st.columns(2, gap="medium")

        with md1:
            with st.container(border=True):
                st.markdown('<div class="chart-title" style="margin-bottom:12px">Por Bairro</div>',
                            unsafe_allow_html=True)
                if "BAIRRO" in df.columns:
                    tb = df["BAIRRO"].fillna("Não informado").value_counts().reset_index()
                    tb.columns = ["Bairro", "Leads"]
                    tb["% Total"] = (tb["Leads"] / total_bf * 100).round(1).astype(str) + "%"
                    st.dataframe(tb, use_container_width=True, hide_index=True, height=340)

        with md2:
            with st.container(border=True):
                st.markdown('<div class="chart-title" style="margin-bottom:12px">Por Equipe</div>',
                            unsafe_allow_html=True)
                if EQUIPE_COL:
                    te = df[EQUIPE_COL].fillna("Não informado").value_counts().reset_index()
                    te.columns = ["Equipe", "Leads"]
                    te["% Total"] = (te["Leads"] / total_bf * 100).round(1).astype(str) + "%"
                    st.dataframe(te, use_container_width=True, hide_index=True, height=340)

    with tab_bf_cad:
        sc, cc = st.columns([4, 1])
        bf_search = sc.text_input("", placeholder="🔍  Buscar por nome, bairro, pet, equipe...",
                                  label_visibility="collapsed")
        cc.markdown(f'<p style="color:{MUTED2};font-size:12px;text-align:right;padding-top:10px">'
                    f'{fmt_num(total_bf)} registros</p>', unsafe_allow_html=True)
        df_bf = df.copy()
        if bf_search:
            bf_cols = ["NOME_COMPLETO", "BAIRRO", PET_COL, NOME_PET, EQUIPE_COL, ASSE_COL, "CEP"]
            bf_mask = pd.Series(False, index=df_bf.index)
            for c in bf_cols:
                if c and c in df_bf.columns:
                    bf_mask |= df_bf[c].astype(str).str.contains(bf_search, case=False, na=False)
            df_bf = df_bf[bf_mask]
        pref = ["DATA","NOME_COMPLETO","WHATSAPP",PET_COL,NOME_PET,GEN_COL,IDADE_COL,
                "BAIRRO","CEP","ENDERECO","COMPLEMENTO",EQUIPE_COL,ASSE_COL]
        bf_show = [c for c in pref if c and c in df_bf.columns]
        st.dataframe(df_bf[bf_show], use_container_width=True, hide_index=True, height=580)

    st.stop()   # buffo complete

# ══════════════════════════════ GUTI VISITA ═══════════════════════════════════
if tipo == "visita":
    total_vs = len(df)
    hoje_vs  = len(df[df["DATA"].dt.date == datetime.now(tz=BRASILIA).date()]) if "DATA" in df.columns else 0
    ultimos7 = len(df[df["DATA"].dt.date >= (datetime.now(tz=BRASILIA).date() - timedelta(7))]) if "DATA" in df.columns else 0
    com_tel  = df["TELEFONE"].notna().sum() if "TELEFONE" in df.columns else 0

    with tab_vs_vis:
        # ── KPIs ──────────────────────────────────────────────────────────────
        k1, k2, k3, k4 = st.columns(4, gap="medium")
        k1.markdown(kpi_card(PURPLE, "Total de Visitas", fmt_num(total_vs),
                             badge=f"Período: {periodo}", badge_color="rgba(139,92,246,.12)", badge_txt=PURPLE),
                    unsafe_allow_html=True)
        k2.markdown(kpi_card(ORANGE, "Hoje", fmt_num(hoje_vs),
                             badge="novos hoje", badge_color="rgba(249,115,22,.12)", badge_txt=ORANGE),
                    unsafe_allow_html=True)
        k3.markdown(kpi_card(GREEN, "Últimos 7 dias", fmt_num(ultimos7),
                             badge="visitas recentes", badge_color="rgba(16,185,129,.12)", badge_txt=GREEN),
                    unsafe_allow_html=True)
        k4.markdown(kpi_card(AMBER, "Com Telefone", fmt_num(com_tel),
                             badge=f"{int(com_tel/total_vs*100) if total_vs else 0}% dos contatos",
                             badge_color="rgba(245,158,11,.12)", badge_txt=AMBER),
                    unsafe_allow_html=True)

        if df.empty:
            st.info("Nenhuma visita no período selecionado."); st.stop()

        # ── Crescimento ────────────────────────────────────────────────────────
        section("Crescimento")
        with st.container(border=True):
            st.markdown('<div class="chart-title">Visitas por dia</div>'
                        '<div class="chart-sub">Evolução no período selecionado</div>',
                        unsafe_allow_html=True)
            st.plotly_chart(area_chart(df), use_container_width=True, config={"displayModeBar": False})

        # ── Distribuição por hora e dia da semana ─────────────────────────────
        section("Padrão de Visitas")
        h1, h2 = st.columns(2, gap="medium")

        with h1:
            with st.container(border=True):
                st.markdown('<div class="chart-title">Visitas por Hora do Dia</div>'
                            '<div class="chart-sub">Em que horário as pessoas se cadastram</div>',
                            unsafe_allow_html=True)
                if "DATA" in df.columns:
                    hora_df = df.dropna(subset=["DATA"]).copy()
                    hora_df["hora"] = hora_df["DATA"].dt.hour
                    hc = hora_df.groupby("hora").size().reset_index(name="Qtd")
                    hc["label"] = hc["hora"].apply(lambda h: f"{h:02d}h")
                    fig = go.Figure(go.Bar(
                        x=hc["label"], y=hc["Qtd"],
                        marker=dict(color=hc["Qtd"], colorscale=[[0, PURPLE],[1, ORANGE]],
                                    showscale=False, line=dict(width=0)),
                        text=hc["Qtd"], textposition="outside",
                        textfont=dict(color=MUTED2, size=10),
                    ))
                    fig.update_layout(**base_layout(height=300,
                        xaxis=dict(gridcolor=GRID_CLR, showline=False, zeroline=False, tickfont_size=10),
                        yaxis=dict(gridcolor=GRID_CLR, showline=False, zeroline=False, tickfont_size=10),
                        bargap=0.2))
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        with h2:
            with st.container(border=True):
                st.markdown('<div class="chart-title">Visitas por Dia da Semana</div>'
                            '<div class="chart-sub">Dias com mais cadastros</div>',
                            unsafe_allow_html=True)
                if "DATA" in df.columns:
                    dias_pt = ["Segunda","Terça","Quarta","Quinta","Sexta","Sábado","Domingo"]
                    sem_df  = df.dropna(subset=["DATA"]).copy()
                    sem_df["dia_num"] = sem_df["DATA"].dt.dayofweek
                    sem_df["dia"]     = sem_df["dia_num"].apply(lambda d: dias_pt[d])
                    sc2 = sem_df.groupby(["dia_num","dia"]).size().reset_index(name="Qtd")
                    sc2 = sc2.sort_values("dia_num")
                    fig = go.Figure(go.Bar(
                        x=sc2["dia"], y=sc2["Qtd"],
                        marker=dict(color=sc2["Qtd"], colorscale=[[0, GREEN],[1, AMBER]],
                                    showscale=False, line=dict(width=0)),
                        text=sc2["Qtd"], textposition="outside",
                        textfont=dict(color=MUTED2, size=10),
                    ))
                    fig.update_layout(**base_layout(height=300,
                        xaxis=dict(gridcolor=GRID_CLR, showline=False, zeroline=False, tickfont_size=11),
                        yaxis=dict(gridcolor=GRID_CLR, showline=False, zeroline=False, tickfont_size=10),
                        bargap=0.3))
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        # ── Tabela resumo por data ─────────────────────────────────────────────
        section("Resumo Diário")
        with st.container(border=True):
            st.markdown('<div class="chart-title" style="margin-bottom:12px">Visitas por Data</div>',
                        unsafe_allow_html=True)
            if "DATA" in df.columns:
                rd = df.dropna(subset=["DATA"]).copy()
                rd["Data"] = rd["DATA"].dt.date
                rd = rd.groupby("Data").size().reset_index(name="Visitas")
                rd = rd.sort_values("Data", ascending=False)
                rd["Data"] = rd["Data"].astype(str)
                rd["% Total"] = (rd["Visitas"] / total_vs * 100).round(1).astype(str) + "%"
                st.dataframe(rd, use_container_width=True, hide_index=True, height=360)

    with tab_vs_lista:
        sc, cc = st.columns([4, 1])
        vs_search = sc.text_input("", placeholder="🔍  Buscar por nome ou telefone...",
                                  label_visibility="collapsed")
        cc.markdown(f'<p style="color:{MUTED2};font-size:12px;text-align:right;padding-top:10px">'
                    f'{fmt_num(total_vs)} registros</p>', unsafe_allow_html=True)
        df_vs = df.copy()
        if vs_search:
            vs_mask = pd.Series(False, index=df_vs.index)
            for c in ["NOME", "TELEFONE", "FIRST_NAME", "LAST_NAME", "NAME"]:
                if c in df_vs.columns:
                    vs_mask |= df_vs[c].astype(str).str.contains(vs_search, case=False, na=False)
            df_vs = df_vs[vs_mask]
        vs_show = [c for c in ["DATA", "NOME", "TELEFONE", "FIRST_NAME", "LAST_NAME"]
                   if c in df_vs.columns]
        st.dataframe(df_vs[vs_show], use_container_width=True, hide_index=True, height=580)

    st.stop()   # visita complete

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
