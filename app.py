import streamlit as st
import pandas as pd
import requests
import unicodedata
import re
from urllib.parse import quote
from PIL import Image

# ---- CONFIGURAÇÃO GERAL ----
st.set_page_config(page_title="Guia de Plantas - Festival de Flores de Holambra 2025", page_icon="🌱", layout="wide")

# ---- CSS personalizado (tema amarelo + cartões brancos) ----
st.markdown("""
<style>
.stApp {
  background: #F4C300 !important; /* amarelo festival */
}
.main .block-container {
  background: #ffffff;
  padding: 2rem 2rem 3rem 2rem;
  border-radius: 16px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.08);
}
.css-10trblm, .stTextInput>div>div>input { 
  background: #fff !important; 
}
</style>
""", unsafe_allow_html=True)

# ---- Cabeçalho com logo ----
logo = Image.open("logo_ffh.jpg")
col_logo, col_title = st.columns([1,3])
with col_logo:
    st.image(logo, use_column_width=True)
with col_title:
    st.title("🌱 Guia de Plantas — 1 imagem")
    st.caption("Festival de Flores de Holambra")

# ---- Funções utilitárias ----
def normalize(s: str) -> str:
    s = s or ""
    s = str(s)
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return s.lower().strip()

@st.cache_data
def load_data():
    df = pd.read_csv("plants_guide.csv")
    df["planta_norm"] = df["planta"].apply(normalize)
    return df

def wiki_first_image(query: str, lang="pt"):
    base = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": query,
        "gsrlimit": 1,
        "prop": "pageimages|info",
        "inprop": "url",
        "piprop": "thumbnail",
        "pithumbsize": 1024,
    }
    try:
        r = requests.get(base, params=params, timeout=10)
        if r.status_code == 200:
            js = r.json()
            pages = js.get("query", {}).get("pages", {})
            if pages:
                p = next(iter(pages.values()))
                thumb = p.get("thumbnail", {}).get("source")
                if thumb:
                    return {"src": thumb, "page": p.get("fullurl"), "title": p.get("title")}
    except Exception:
        pass
    return None

def duckduckgo_first_image(query: str):
    try:
        html = requests.get(
            "https://duckduckgo.com/", 
            params={"q": query, "iax":"images","ia":"images"}, 
            timeout=10, 
            headers={"User-Agent":"Mozilla/5.0"}
        ).text
        m = re.search(r'"image":"(https:[^"]+)"', html)
        if m:
            url = m.group(1).encode("utf-8").decode("unicode_escape")
            return {"src": url, "page": f"https://duckduckgo.com/?q={quote(query)}&iax=images&ia=images", "title": query}
    except Exception:
        return None
    return None

def one_image_any_site(query: str):
    im = wiki_first_image(query + " planta", lang="pt")
    if im: return im
    im = wiki_first_image(query + " plant", lang="en")
    if im: return im
    im = duckduckgo_first_image(query + " plant")
    if im: return im
    return None

# ---- Carregar base ----
df = load_data()

# ---- Barra de busca ----
col1, col2 = st.columns([2,1])
with col1:
    q = st.text_input("Busque pelo nome da planta", placeholder="Ex.: Alecrim, Orquídea, Kalanchoe...")
with col2:
    show_table = st.checkbox("Ver tabela", value=False)

filtered = df
if q:
    qn = normalize(q)
    filtered = df[df["planta_norm"].str.contains(qn)]
    if filtered.empty and len(qn) >= 3:
        filtered = df[df["planta_norm"].str.startswith(qn[:3])]

# ---- Filtros opcionais ----
with st.sidebar:
    st.header("Filtros (opcional)")
    ambientes = sorted([a for a in df["ambiente"].dropna().unique() if isinstance(a, str)])
    expos = sorted([a for a in df["exposicao"].dropna().unique() if isinstance(a, str)])
    ambiente_sel = st.multiselect("Ambiente contém:", ambientes, default=[])
    expos_sel = st.multiselect("Exposição contém:", expos, default=[])

def contains_any(cell, needles):
    if not needles: return True
    if not isinstance(cell, str): return False
    c = normalize(cell)
    return any(normalize(n) in c for n in needles)

if ambiente_sel:
    filtered = filtered[filtered["ambiente"].apply(lambda x: contains_any(x, ambiente_sel))]
if expos_sel:
    filtered = filtered[filtered["exposicao"].apply(lambda x: contains_any(x, expos_sel))]

if show_table:
    st.dataframe(filtered[["planta","exposicao","rega","ambiente","poda","adubo"]], use_container_width=True)

# ---- Detalhes da planta ----
if not filtered.empty:
    options = filtered["planta"].tolist()
    sel = st.selectbox("Selecione uma planta", options, index=0)
    row = df[df["planta"] == sel].iloc[0]

    st.subheader(sel)
    c1, c2 = st.columns([1,1])
    with c1:
        st.markdown(f"**Exposição ao Sol:** {row['exposicao'] if isinstance(row['exposicao'], str) else '-'}")
        st.markdown(f"**Rega:** {row['rega'] if isinstance(row['rega'], str) else '-'}")
        st.markdown(f"**Ambiente:** {row['ambiente'] if isinstance(row['ambiente'], str) else '-'}")
        st.markdown(f"**Poda:** {row['poda'] if isinstance(row['poda'], str) else '-'}")
        st.markdown(f"**Adubo:** {row['adubo'] if isinstance(row['adubo'], str) else '-'}")
    with c2:
        im = one_image_any_site(sel)
        if im:
            st.image(im["src"], caption=f"{im['title']} — fonte externa", use_column_width=True)
            if im.get("page"):
                st.markdown(f"[Abrir página de origem]({im['page']})")
        else:
            st.info("Não encontrei imagem automática. Você pode adicionar uma foto local na pasta `images/`.")

else:
    st.warning("Nenhum resultado. Tente outro termo.")

st.divider()
st.caption("Fonte dos dados: Guia de Plantas (PDF convertido). O app busca apenas **1** imagem em site externo (Wikipedia → DuckDuckGo).")

