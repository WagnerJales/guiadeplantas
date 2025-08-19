
import streamlit as st
import pandas as pd
import requests
import unicodedata
from urllib.parse import quote

@st.cache_data
def load_data():
    df = pd.read_csv("plants_guide.csv")
    # Normalize helper
    df["planta_norm"] = df["planta"].apply(normalize)
    return df

def normalize(s: str) -> str:
    s = s or ""
    s = str(s)
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return s.lower().strip()

@st.cache_data(show_spinner=False)
def wiki_images(query: str, lang="pt", limit=4):
    # Try Wikipedia API (search -> pageimages thumbnails)
    # First try in PT, fallback to EN
    imgs = _wiki_images_lang(query, lang=lang, limit=limit)
    if not imgs and lang != "en":
        imgs = _wiki_images_lang(query, lang="en", limit=limit)
    return imgs

def _wiki_images_lang(query: str, lang="pt", limit=4):
    base = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": query,
        "gsrlimit": limit,
        "prop": "pageimages|info",
        "inprop": "url",
        "piprop": "thumbnail",
        "pithumbsize": 800,
    }
    try:
        r = requests.get(base, params=params, timeout=10)
        if r.status_code == 200:
            js = r.json()
            pages = js.get("query", {}).get("pages", {})
            out = []
            for _, p in pages.items():
                thumb = p.get("thumbnail", {}).get("source")
                url = p.get("fullurl")
                title = p.get("title")
                if thumb:
                    out.append({"src": thumb, "page": url, "title": title})
            return out
    except Exception:
        pass
    return []

st.set_page_config(page_title="Guia de Plantas • Festival de Flores", page_icon="🌿", layout="wide")

st.title("🌿 Guia de Plantas — Festival de Flores")
st.caption("Baseado no guia fornecido pela organização do festival.")

df = load_data()

# Search UI
col1, col2 = st.columns([2,1])
with col1:
    q = st.text_input("Busque pelo nome da planta", placeholder="Ex.: Alecrim, Orquídeas, Kalanchoe...")
with col2:
    st.write(" ")
    show_table = st.checkbox("Ver tabela completa", value=False)

# Suggestions
filtered = df
if q:
    qn = normalize(q)
    filtered = df[df["planta_norm"].str.contains(qn)]
    # If nothing, suggest closest by startswith
    if filtered.empty:
        filtered = df[df["planta_norm"].str.startswith(qn[:3])]

# Sidebar filters (opcional)
with st.sidebar:
    st.header("Filtros")
    ambientes = sorted([a for a in df["ambiente"].dropna().unique() if isinstance(a, str)])
    expos = sorted([a for a in df["exposicao"].dropna().unique() if isinstance(a, str)])
    ambiente_sel = st.multiselect("Ambiente contém:", ambientes, default=[])
    expos_sel = st.multiselect("Exposição contém:", expos, default=[])

def contains_any(cell, needles):
    if not needles:
        return True
    if not isinstance(cell, str):
        return False
    c = normalize(cell)
    return any(normalize(n) in c for n in needles)

if ambiente_sel:
    filtered = filtered[filtered["ambiente"].apply(lambda x: contains_any(x, ambiente_sel))]
if expos_sel:
    filtered = filtered[filtered["exposicao"].apply(lambda x: contains_any(x, expos_sel))]

if show_table:
    st.dataframe(filtered[["planta", "exposicao", "rega", "ambiente", "poda", "adubo"]], use_container_width=True)

# Detail view
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
        imgs = wiki_images(sel + " planta", limit=4)
        if imgs:
            st.markdown("**Imagens sugeridas (Wikipedia):**")
            for im in imgs:
                st.image(im["src"], caption=f"{im['title']} — fonte: Wikipedia", use_column_width=True)
                st.markdown(f"[Abrir página]({im['page']})")
        else:
            st.info("Não encontrei imagens automaticamente. Tente outro nome ou adicione imagens locais na pasta `images/`.")

else:
    st.warning("Nenhum resultado. Tente outro termo.")

st.divider()
st.markdown("ℹ️ **Fonte dos dados**: guia fornecido pelo Festival de Flores (arquivo PDF).")
