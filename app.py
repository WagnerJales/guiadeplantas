# app.py — Guia de Plantas (com correção da busca de imagens via Wikipédia/Commons)

import streamlit as st
import pandas as pd
import requests
import unicodedata
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

# ======= CORREÇÃO DA BUSCA DE IMAGENS =======
def _wiki_search_title(query: str, lang: str = "pt") -> str | None:
    """Busca o melhor título de página usando a API 'list=search' da Wikipédia."""
    try:
        r = requests.get(
            f"https://{lang}.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "format": "json",
                "list": "search",
                "srsearch": query,
                "srlimit": 1,
            },
            timeout=10,
        )
        r.raise_for_status()
        js = r.json()
        items = js.get("query", {}).get("search", [])
        if items:
            return items[0].get("title")
    except Exception:
        pass
    return None

def _wiki_summary_image_by_title(title: str, lang: str = "pt") -> dict | None:
    """Usa a API REST 'page/summary' para obter thumbnail/original e URL da página."""
    try:
        summary = requests.get(
            f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote(title)}",
            timeout=10,
            headers={"Accept": "application/json"},
        )
        summary.raise_for_status()
        js = summary.json()
        src = (js.get("originalimage") or {}).get("source") or (js.get("thumbnail") or {}).get("source")
        page = js.get("content_urls", {}).get("desktop", {}).get("page")
        if src:
            return {"src": src, "page": page, "title": js.get("title", title)}
    except Exception:
        pass
    return None

def wiki_first_image(query: str, lang: str = "pt") -> dict | None:
    """Pipeline robusto: busca o título e puxa imagem via REST Summary."""
    title = _wiki_search_title(query, lang=lang)
    if not title:
        return None
    return _wiki_summary_image_by_title(title, lang=lang)

def commons_first_image(query: str) -> dict | None:
    """Fallback: busca direto por arquivos (namespace 6) no Wikimedia Commons."""
    try:
        r = requests.get(
            "https://commons.wikimedia.org/w/api.php",
            params={
                "action": "query",
                "format": "json",
                "generator": "search",
                "gsrsearch": query,
                "gsrlimit": 1,
                "gsrnamespace": 6,  # somente arquivos
                "prop": "imageinfo|info",
                "inprop": "url",
                "iiprop": "url",
                "iiurlwidth": 1024,
            },
            timeout=10,
        )
        r.raise_for_status()
        js = r.json()
        pages = js.get("query", {}).get("pages", {})
        if not pages:
            return None
        p = next(iter(pages.values()))
        infos = p.get("imageinfo") or []
        if infos:
            ii = infos[0]
            src = ii.get("thumburl") or ii.get("url")
            if src:
                return {
                    "src": src,
                    "page": p.get("fullurl") or f"https://commons.wikimedia.org/wiki/{quote(p.get('title',''))}",
                    "title": p.get("title", query),
                }
    except Exception:
        pass
    return None

def one_image_any_site(plant_name: str) -> dict | None:
    """
    Prioriza Wikipédia em PT; depois EN; por fim Commons.
    Mantém contexto botânico para evitar homônimos.
    """
    q_pt  = f"{plant_name} (planta)"
    q_pt2 = f"{plant_name} botânica"
    q_en  = f"{plant_name} (plant)"

    im = wiki_first_image(q_pt,  lang="pt") or wiki_first_image(q_pt2, lang="pt")
    if im:
        return im

    im = wiki_first_image(q_en,  lang="en")
    if im:
        return im

    im = commons_first_image(f"{plant_name} flower") or commons_first_image(f"{plant_name} plant")
    if im:
        return im

    return None
# ======= FIM DA CORREÇÃO =======

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
st.markdown("📸 Acompanhe também no Instagram: [Festival de Flores de Holambra SLZ](https://www.instagram.com/floresdeholambraslz/)")
