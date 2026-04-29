---
name: novo-dash
description: Guia completo para criar dashboards analytics em tempo real com Streamlit + Supabase. Cobre arquitetura, componentes de UI, paginação, atualização automática e deploy no Streamlit Cloud. Use quando o usuário quiser iniciar um novo projeto de dashboard.
---

# Skill: Dashboard Analytics — Streamlit + Supabase (Real-time)

Você é especialista em criar dashboards analytics profissionais com **Streamlit + Supabase**. Quando ativado, guie o usuário do zero até o deploy, gerando código funcional desde o início.

---

## Passo 1 — Coletar informações do cliente

Pergunte antes de escrever qualquer código:

1. **Nome do projeto** (ex: "DashVendas", "DashCliente")
2. **URL e KEY do Supabase** (já existem ou precisam ser criados?)
3. **Tabelas no Supabase**: nome de cada tabela e o que representa
4. **Colunas importantes**: data, nome, telefone, cidade, status, valor — o que cada tabela tem
5. **Páginas desejadas**: visão geral, leads, relatório, mapa, grupos, etc.
6. **Paleta de cores**: usar padrão (PURPLE/ORANGE/GREEN/AMBER) ou customizar?
7. **Atualização automática**: a cada quantos segundos o dash deve buscar novos dados? (padrão: 30s)

---

## Passo 2 — Arquitetura geral

```
app.py                        ← arquivo único, toda a aplicação
.streamlit/
  secrets.toml                ← credenciais (NUNCA commitar)
  config.toml                 ← tema e configurações do Streamlit
requirements.txt
.gitignore
```

### Fluxo de dados (real-time)

```
Supabase (PostgreSQL)
        ↓  REST API com paginação
  load_*() — @st.cache_data(ttl=N)
        ↓  cache expira a cada N segundos
  st_autorefresh — dispara rerun automático
        ↓
  Dashboard atualizado
```

**Regra de ouro**: `ttl` do cache deve ser igual ao intervalo de autorefresh.  
Se o dado cai no Supabase e você quer ver em 30s → `ttl=30` + `st_autorefresh(interval=30000)`.

---

## Passo 3 — Estrutura do app.py

```
1.  Imports
2.  Constantes (cores, Supabase URL/KEY, timezone, DDD_INFO)
3.  Dados hardcoded (projetos, metas, grupos — se houver)
4.  CSS global (dark theme via st.markdown)
5.  Funções de UI (kpi_card, section, fmt_num, base_layout)
6.  Funções de dados (load_* com paginação + @st.cache_data)
7.  PAGINAS dict
8.  st_autorefresh (real-time)
9.  Sidebar (navegação + filtros)
10. Carregamento de dados (if tipo == "x": df_all = load_x())
11. Filtro de período
12. Blocos de renderização por página
```

---

## Passo 4 — Código base completo

### Imports e constantes

```python
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests, re, unicodedata
from datetime import date, timedelta
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Nome do Dash", layout="wide", page_icon="📊")

# ── Supabase ──────────────────────────────────────────────────────────────────
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

# ── Timezone ──────────────────────────────────────────────────────────────────
import pytz
BRASILIA = pytz.timezone("America/Sao_Paulo")

# ── Cores ─────────────────────────────────────────────────────────────────────
PURPLE   = "#8b5cf6"
ORANGE   = "#f97316"
GREEN    = "#10b981"
AMBER    = "#f59b0b"
MUTED    = "#94a3b8"
MUTED2   = "#cbd5e1"
GRID_CLR = "rgba(148,163,184,.08)"
BG_CARD  = "rgba(30,41,59,.6)"
```

### CSS Dark Theme

```python
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif!important;background:#0f172a!important;color:#f1f5f9}
.stApp{background:#0f172a}
section[data-testid="stSidebar"]{background:#1e293b!important;border-right:1px solid rgba(255,255,255,.06)}
.block-container{padding-top:1.5rem!important}
.chart-title{color:#f1f5f9;font-size:14px;font-weight:700;margin-bottom:2px}
.chart-sub{color:#94a3b8;font-size:12px;margin-bottom:14px}
div[data-testid="stTabs"] button{color:#94a3b8;font-weight:600}
div[data-testid="stTabs"] button[aria-selected="true"]{color:#f1f5f9;border-bottom:2px solid #8b5cf6}
div[data-testid="stMetric"]{background:rgba(30,41,59,.6);border-radius:12px;padding:16px}
</style>""", unsafe_allow_html=True)
```

### Real-time — autorefresh

```python
# Coloque ANTES do sidebar, logo após o CSS
# interval em milissegundos; limit=-1 = infinito
REFRESH_SEC = 30
st_autorefresh(interval=REFRESH_SEC * 1000, limit=None, key="autorefresh")
```

> Quando um novo lead cai no Supabase, o cache expira em até `REFRESH_SEC` segundos e o dashboard atualiza automaticamente sem o usuário precisar recarregar a página.

### Paginação Supabase (padrão para qualquer tabela)

```python
@st.cache_data(ttl=30)   # igual ao REFRESH_SEC
def load_tabela() -> pd.DataFrame:
    hdrs = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Prefer": "count=none",
    }
    rows, offset, page = [], 0, 1000
    while True:
        url = (f"{SUPABASE_URL}/rest/v1/nome_da_tabela"
               f"?select=*&order=created_at.asc&limit={page}&offset={offset}")
        r = requests.get(url, headers=hdrs, timeout=15)
        r.raise_for_status()
        batch = r.json()
        rows.extend(batch)
        if len(batch) < page:
            break
        offset += page
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df.columns = [_norm_col(c) for c in df.columns]
    # parse de data — ajuste o nome da coluna conforme a tabela
    if "CREATED_AT" in df.columns:
        df["DATA"] = (pd.to_datetime(df["CREATED_AT"], errors="coerce", utc=True)
                      .dt.tz_convert(BRASILIA).dt.tz_localize(None))
    return df

def _norm_col(c: str) -> str:
    """Normaliza nome de coluna para UPPER_SNAKE_CASE sem acentos."""
    c = unicodedata.normalize("NFKD", str(c)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", "_", c.strip()).upper()
```

**Variações de parse de data:**

```python
# Coluna timestamp ISO com timezone (padrão Supabase)
df["DATA"] = pd.to_datetime(df["CREATED_AT"], errors="coerce", utc=True).dt.tz_convert(BRASILIA).dt.tz_localize(None)

# Coluna texto formato brasileiro "DD/MM/YYYY HH:MM"
df["DATA"] = pd.to_datetime(df["DATA_CADASTRO"], format="%d/%m/%Y %H:%M", errors="coerce", dayfirst=True)

# Coluna texto formato ISO sem timezone "YYYY-MM-DD HH:MM:SS"
df["DATA"] = pd.to_datetime(df["DATA"], errors="coerce")
```

### Funções de UI

```python
def kpi_card(color, label, value, badge="", badge_color="rgba(255,255,255,.06)", badge_txt=None):
    bt = badge_txt or color
    b = (f'<span style="background:{badge_color};color:{bt};padding:3px 10px;'
         f'border-radius:999px;font-size:11px;font-weight:600">{badge}</span>' if badge else "")
    return (f'<div style="background:{BG_CARD};border:1px solid rgba(255,255,255,.06);'
            f'border-radius:16px;padding:22px 24px;min-height:110px">'
            f'<p style="color:{MUTED};font-size:11px;font-weight:700;letter-spacing:.08em;margin:0 0 6px">'
            f'{label.upper()}</p>'
            f'<p style="color:#f1f5f9;font-size:32px;font-weight:800;margin:0 0 10px;line-height:1">{value}</p>'
            f'{b}</div>')

def section(title: str):
    st.markdown(
        f'<p style="color:{MUTED};font-size:11px;font-weight:700;letter-spacing:.1em;'
        f'text-transform:uppercase;margin:28px 0 12px">{title}</p>',
        unsafe_allow_html=True,
    )

def fmt_num(n) -> str:
    try: return f"{int(n):,}".replace(",", ".")
    except: return str(n)

def base_layout(**kw) -> dict:
    d = dict(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter,sans-serif", color=MUTED),
        margin=dict(l=0, r=0, t=10, b=0),
        showlegend=False,
        height=kw.pop("height", 300),
    )
    d.update(kw)
    return d
```

### Gráfico de área (evolução diária)

```python
def area_chart(df: pd.DataFrame) -> go.Figure:
    if "DATA" not in df.columns or df.empty:
        return go.Figure()
    daily = df.groupby(df["DATA"].dt.date).size().reset_index(name="n")
    daily.columns = ["data", "n"]
    fig = go.Figure(go.Scatter(
        x=daily["data"], y=daily["n"], mode="lines",
        fill="tozeroy",
        line=dict(color=PURPLE, width=2),
        fillcolor="rgba(139,92,246,.15)",
    ))
    fig.update_layout(**base_layout(height=220,
        xaxis=dict(gridcolor=GRID_CLR, showline=False, tickfont_size=11),
        yaxis=dict(gridcolor=GRID_CLR, showline=False, zeroline=False, tickfont_size=11),
    ))
    return fig
```

### PAGINAS dict e Sidebar

```python
PAGINAS = {
    "🏠  Geral":       {"tipo": "geral"},
    "📣  Leads":       {"tipo": "leads"},
    "👥  Grupos":      {"tipo": "grupos"},
    "📋  Relatório":   {"tipo": "relatorio"},
    # adicione conforme necessário
}

with st.sidebar:
    st.markdown("## 📊 Nome do Dash")
    st.markdown("---")
    pagina_nome = st.radio("", list(PAGINAS.keys()), label_visibility="collapsed")
    pagina_cfg  = PAGINAS[pagina_nome]
    tipo = pagina_cfg.get("tipo", "leads")

    st.markdown("---")
    # filtro de período (esconde em páginas sem data)
    if tipo not in ("geral", "relatorio", "grupos"):
        periodo = st.selectbox("PERÍODO", ["7 dias","15 dias","30 dias","60 dias","90 dias","Total"])
    else:
        periodo = "Total"

    # indicador de atualização automática
    st.markdown(
        f'<p style="color:{MUTED};font-size:11px;text-align:center;margin-top:20px">'
        f'🔄 Atualiza a cada {REFRESH_SEC}s</p>',
        unsafe_allow_html=True,
    )
```

### Filtro de período

```python
hoje = date.today()
_mapa = {"7 dias": 7, "15 dias": 15, "30 dias": 30, "60 dias": 60, "90 dias": 90}

if periodo == "Total":
    data_ini, data_fim = date(2020, 1, 1), hoje
else:
    data_ini = hoje - timedelta(days=_mapa[periodo])
    data_fim = hoje

# aplicar após df_all estar carregado
if "DATA" in df_all.columns and not df_all.empty and periodo != "Total":
    mask = (df_all["DATA"].dt.date >= data_ini) & (df_all["DATA"].dt.date <= data_fim)
    df = df_all[mask].copy()
else:
    df = df_all.copy()
```

---

## Passo 5 — Configuração Supabase

### Permissões da tabela (Row Level Security)

No Supabase, para o dashboard conseguir ler sem autenticação de usuário:

```sql
-- Habilita leitura pública (somente leitura, sem RLS bloqueando)
ALTER TABLE nome_tabela ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Leitura pública" ON nome_tabela
  FOR SELECT USING (true);
```

Ou simplesmente **desabilite RLS** na tabela se for uso interno:
```sql
ALTER TABLE nome_tabela DISABLE ROW LEVEL SECURITY;
```

### ORDER BY estável para paginação

Sempre use uma coluna estável no ORDER BY para evitar registros duplicados ou faltando entre páginas:

```
✅ &order=created_at.asc   (timestamp, padrão Supabase)
✅ &order=id.asc           (se a tabela tiver id numérico)
✅ &order=ID.asc           (se a coluna se chama ID — case sensitive na URL)
❌ sem order               (PostgreSQL pode retornar ordem diferente entre páginas)
```

---

## Passo 6 — Deploy no Streamlit Cloud

### 1. Prepare o repositório

```bash
# Estrutura mínima
├── app.py
├── requirements.txt
└── .gitignore

# .gitignore deve conter:
.streamlit/secrets.toml
__pycache__/
*.pyc
.env
```

### 2. requirements.txt

```
streamlit>=1.32
plotly>=5.20
pandas>=2.0
requests>=2.31
pytz>=2024.1
streamlit-autorefresh>=1.0
```

### 3. Deploy

1. Acesse **share.streamlit.io** e conecte o GitHub
2. Selecione o repositório e o arquivo `app.py`
3. Em **"Advanced settings"** → **"Secrets"**, cole:

```toml
SUPABASE_URL = "https://xxxx.supabase.co"
SUPABASE_KEY = "eyJhbGci..."
```

4. Clique **Deploy** — URL pública gerada automaticamente

### 4. Atualização automática do deploy

Qualquer `git push` na branch configurada redeploya automaticamente em ~30 segundos.

---

## Passo 7 — Checklist antes de ir ao ar

- [ ] `secrets.toml` **não** está no git (verificar `.gitignore`)
- [ ] Todas as tabelas Supabase têm ORDER BY estável na paginação
- [ ] `ttl` do `@st.cache_data` igual ao intervalo do `st_autorefresh`
- [ ] RLS do Supabase configurado corretamente (leitura permitida)
- [ ] `requirements.txt` com todas as dependências
- [ ] Testou em modo incógnito (sem cache do browser)
- [ ] Deploy no Streamlit Cloud configurado com secrets

---

## Passo 8 — Armadilhas comuns

| Problema | Causa | Solução |
|---|---|---|
| Dashboard não atualiza | `ttl` muito alto | Reduza `ttl` = `REFRESH_SEC` |
| Registros faltando | Paginação sem ORDER BY | Adicione `&order=created_at.asc` |
| 400 Bad Request no ORDER | Coluna não existe | Verifique nome exato da coluna no Supabase |
| Datas erradas | Formato de data diferente | Use `format="%d/%m/%Y %H:%M"` para texto BR |
| Erro de autenticação | KEY inválida ou RLS bloqueando | Verifique secrets e política RLS |
| Deploy lento | Cache muito grande | Reduza colunas no `select=*` → `select=col1,col2` |

---

## Como usar esta skill

Ao ser ativado com `/novo-dash`:

1. **Pergunte** as informações do Passo 1 antes de gerar código
2. **Gere** o `app.py` completo já com tabelas, páginas e cores do cliente
3. **Inclua** autorefresh configurado desde o início
4. **Oriente** o deploy passo a passo ao final
5. **Itere** conforme o cliente pedir ajustes

Gere sempre código funcional e completo — nunca esqueletos com `# TODO`.
