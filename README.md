
# 🌿 Guia de Plantas — Streamlit App

Aplicativo em Streamlit que permite buscar plantas pelo nome e visualizar informações essenciais
(exposição ao sol, rega, ambiente, poda e adubo), além de imagens sugeridas via Wikipedia.

## 📦 Estrutura do repositório

```
.
├─ app.py
├─ plants_guide.csv
├─ requirements.txt
└─ README.md
```

> Opcional: crie uma pasta `images/` com fotos locais para cada planta e adapte o código caso prefira não usar a Wikipedia.

## ▶️ Rodar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

## ☁️ Deploy pelo GitHub (Streamlit Community Cloud)

1. Crie um repositório no GitHub e envie estes arquivos (`app.py`, `plants_guide.csv`, `requirements.txt`, `README.md`).
2. Acesse https://share.streamlit.io/ (ou https://streamlit.io/cloud) e clique em **New app**.
3. Selecione seu repositório e branch principal, e informe `app.py` como arquivo de entrada.
4. Clique em **Deploy**. Em cerca de 1–2 minutos seu app estará online.

### Variáveis e imagens

- As imagens são obtidas automaticamente via API da Wikipedia (PT e fallback EN). Se preferir **não depender de chamadas externas**, salve imagens em `images/` e troque a função `wiki_images` por carregamento local conforme o nome da planta.
- O CSV `plants_guide.csv` foi gerado a partir do PDF fornecido e pode ser atualizado conforme necessário.

## 🧩 Atualizar a base

Edite o `plants_guide.csv` com as colunas:

- `planta`
- `exposicao`
- `rega`
- `ambiente`
- `poda`
- `adubo`

## 📄 Licença

Uso livre com atribuição.
