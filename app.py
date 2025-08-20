import streamlit as st
import pandas as pd
import requests
import unicodedata
import re
from urllib.parse import quote
from PIL import Image

# ---- CONFIGURAÇÃO GERAL ----
st.set_page_config(page_title="Guia de Plantas", layout="wide")

# ---- CSS personalizado (mobile-friendly) ----
st.markdown("""
<style>
/* Fundo e container */
.stApp { background: #F4C300 !important; }
.main .block-container {
  background: #ffffff;
  padding: 1.25rem 1rem 2rem 1rem;
  border-radius: 16px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.08);
}

/* Título em uma linha + responsivo */
.app-title {
  white-space: nowrap;
  margin: .25rem 0 .5rem 0;
  line-height: 1.1;
  font-weight: 800;
  font-size: clamp(1.6rem, 6vw, 2.8rem);
}

/* Texto do input: preto; placeholder mais escuro para contraste */
.stTextInput input {
  color: #000 !important;
  background: #fff !important;
}
.stTextInput input::placeholder {
  color: #222 !important;
  opacity: .7;
}

/* Rótulos (Exposição, Rega, etc.) um pouco maiores */
.plant-details strong, .plant-details b {
  font-size: clamp(1.00rem, 3.5vw, 1.25rem);
  color: #1f2937;
}
</style>
""", unsafe_allow_html=True)

# ---- Cabeçalho com logo ----
# use "logo_ffh.png" conforme seu arquivo; se tiver versão transparente, pode trocar pelo PNG transparente
logo = Image.open("logo_ffh.png")
col_logo, col_title = st.columns([1,3])
with col_logo:
    st.image(logo, use_container_width=True)
with col_title:
    st.markdown('<h1 class="app-title">Guia de Plantas</h1>', unsafe_allow_html=True)

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

def one_image_any_site(plant_name: str):
    """
    Força contexto botânico para reduzir falsos positivos de homônimos.
    """
    q_pt  = f"{plant_name} planta botânica"
    q_pt2 = f"{plant_name} planta horticultura"
    q_en  = f"{plant_name} plant botany"

    im = wiki_first_image(q_pt,  lang="pt") or wiki_first_image(q_pt2, lang="pt")
    if im: return im
    im = wiki_first_image(q_en,  lang="en")
    if im: return im
    im = duckduckgo_first_image(q_pt) or duckduckgo_first_image(q_en)
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

    # Container com classe para aumentar os rótulos
    st.markdown('<div class="plant-details">', unsafe_allow_html=True)
    c1, c2 = st.columns([1,1])
    with c1:
        st.markdown(f"<strong>Exposição ao Sol:</strong> {row['exposicao'] if isinstance(row['exposicao'], str) else '-'}", unsafe_allow_html=True)
        st.markdown(f"<strong>Rega:</strong> {row['rega'] if isinstance(row['rega'], str) else '-'}", unsafe_allow_html=True)
        st.markdown(f"<strong>Ambiente:</strong> {row['ambiente'] if isinstance(row['ambiente'], str) else '-'}", unsafe_allow_html=True)
        st.markdown(f"<strong>Poda:</strong> {row['poda'] if isinstance(row['poda'], str) else '-'}", unsafe_allow_html=True)
        st.markdown(f"<strong>Adubo:</strong> {row['adubo'] if isinstance(row['adubo'], str) else '-'}", unsafe_allow_html=True)
    with c2:
        im = one_image_any_site(sel)
        if im:
            st.image(im["src"], caption=f"{im['title']} — fonte externa", use_container_width=True)
            if im.get("page"):
                st.markdown(f"[Abrir página de origem]({im['page']})")
        else:
            st.info("Não encontrei imagem automática. Você pode adicionar uma foto local na pasta `images/`.")
    st.markdown('</div>', unsafe_allow_html=True)

else:
    st.warning("Nenhum resultado. Tente outro termo.")

# ---- Rodapé ----
st.divider()
st.caption("Fonte dos dados: Guia de Plantas (PDF convertido). O app busca apenas **1** imagem (Wikipedia → DuckDuckGo) com viés botânico.")
st.markdown("📸 Acompanhe também no Instagram: [Festival de Flores de Holambra SLZ](https://www.instagram.com/floresdeholambraslz/)")


