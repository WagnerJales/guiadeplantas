
# -*- coding: utf-8 -*-
import re
import sys
import pandas as pd

def parse_pdf_to_df(pdf_path: str) -> pd.DataFrame:
    try:
        import PyPDF2
    except ImportError:
        raise SystemExit("PyPDF2 não encontrado. Instale com: pip install PyPDF2")

    text_pages = []
    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text = page.extract_text() or ""
            text = text.replace("\r", "\n")
            text_pages.append(re.sub(r"\n{3,}", "\n\n", text))

    def capture(label, text):
        pattern = rf"{label}:\s*(.*?)(?:(?:\n\n|\n)(?:Exposição ao Sol|Rega|Ambiente|Poda|Adubo):|$)"
        m = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if m:
            val = m.group(1).strip()
            val = re.sub(r"\s*\n\s*", " ", val)
            return val.strip(" .")
        return ""

    records = []
    for raw in text_pages:
        if not raw.strip():
            continue
        if not re.search(r"Exposição ao Sol:", raw, flags=re.IGNORECASE):
            continue

        # header (plant name)
        pre = raw[: re.search(r"Exposição ao Sol:", raw, flags=re.IGNORECASE).start()]
        header_lines = [ln.strip() for ln in pre.split("\n") if ln.strip()]
        header_lines = [ln for ln in header_lines if ln not in ("Nature Farm Presentation", "Guia de Plantas", "Festival de Flores para", "Vendedores e Colaboradores")]
        header_lines = [ln for ln in header_lines if not re.fullmatch(r"\d+", ln)]

        plant_name = " ".join(header_lines[-2:]) if len(header_lines) > 1 else (header_lines[-1] if header_lines else "").strip()
        if not plant_name or len(plant_name) < 3:
            for ln in reversed(header_lines):
                if len(ln) > 2 and "Nature" not in ln and "Guia" not in ln:
                    plant_name = ln
                    break
        plant_name = re.sub(r"\s{2,}", " ", plant_name).strip(" .:;-")
        plant_name = re.sub(r"^(?:\d+\s+)+", "", plant_name).strip()

        exposicao = capture("Exposição ao Sol", raw)
        rega = capture("Rega", raw)
        ambiente = capture("Ambiente", raw)
        poda = capture("Poda", raw)
        adubo = capture("Adubo", raw)

        filled = sum(1 for v in [exposicao, rega, ambiente, poda, adubo] if v)
        if plant_name and filled >= 2:
            records.append({
                "planta": plant_name,
                "exposicao": exposicao,
                "rega": rega,
                "ambiente": ambiente,
                "poda": poda,
                "adubo": adubo,
            })

    # Dedup + sort
    by_name = {}
    for r in records:
        key = r["planta"].strip().lower()
        if key not in by_name:
            by_name[key] = r
        else:
            prev = by_name[key]
            if sum(1 for v in prev.values() if v) < sum(1 for v in r.values() if v):
                by_name[key] = r
    df = pd.DataFrame(list(by_name.values()), columns=["planta","exposicao","rega","ambiente","poda","adubo"])
    # clean name
    df["planta"] = df["planta"].str.replace(r"^(?:\d+\s+)+", "", regex=True).str.strip(" .:-")
    df = df.sort_values("planta").reset_index(drop=True)
    return df

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python build_csv_from_pdf.py <Guia de Plantas.pdf> <saida.csv>")
        sys.exit(1)
    pdf_in = sys.argv[1]
    csv_out = sys.argv[2]
    df = parse_pdf_to_df(pdf_in)
    df.to_csv(csv_out, index=False, encoding="utf-8")
    print(f"Gerado: {csv_out} com {len(df)} registros")
