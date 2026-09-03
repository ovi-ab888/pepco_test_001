"""
app.py — PEPCO Hangtag (Swingtag) Generator — STANDALONE, Hangtag-only.

Folder layout expected (same folder as this file):
    app.py
    hangtag_extractor.py
    hangtag_front.py
    templates/Hangtag/front_side.pdf   <- your cleaned template

Run:  streamlit run app.py

STATUS:
  ✅ Front Side — working (extract -> fill -> download)
  ⏳ Back Side  — not wired yet (add hangtag_back.py the same way once ready)
  ⏳ Pad        — not wired yet (add hangtag_pad.py the same way once ready)
"""

import streamlit as st
from datetime import datetime

import hangtag_extractor as hx
import hangtag_front as hf

st.set_page_config(page_title="PEPCO Hangtag Generator", page_icon="🏷️", layout="wide")
st.title("🏷️ PEPCO Hangtag Generator")
st.caption("Front Side is live. Back Side and Pad are coming in the next steps.")

# ----------------------------------------------------------------
# 1) Upload PEPCO tech-pack PDF
# ----------------------------------------------------------------
st.header("1. Upload Tech Pack PDF")
uploaded_pdf = st.file_uploader("PEPCO tech pack PDF", type=["pdf"])

if uploaded_pdf is None:
    st.info("PDF upload korle extraction shuru hobe.")
    st.stop()

results, pl_price_detected, flags = hx.extract_data_from_pdf(uploaded_pdf)

if flags.get("error"):
    st.error(f"Extraction failed: {flags['error']}")
    st.stop()

if not results:
    st.error("Kono data extract kora jayni. PDF format check koro.")
    st.stop()

st.success(f"{len(results)} ta row extract hoise.")

# ----------------------------------------------------------------
# 2) Manual fallbacks (Collection / Colour) if not auto-detected
# ----------------------------------------------------------------
st.header("2. Manual Fields (jodi lage)")

col1, col2 = st.columns(2)
with col1:
    if flags.get("collection_manual"):
        manual_collection = st.text_input("Collection (auto-detect hoyni, likho)")
        if manual_collection:
            for r in results:
                r["Collection"] = manual_collection
with col2:
    if flags.get("colour_manual"):
        manual_colour = st.text_input("Colour (auto-detect hoyni, likho)")
        if manual_colour:
            for r in results:
                r["Colour"] = manual_colour.upper()

# ----------------------------------------------------------------
# 3) Washing Code + PLN Price + Cotton (manual controls, per SS27 app)
# ----------------------------------------------------------------
st.header("3. Washing Code / Price / Material")

wc1, wc2, wc3 = st.columns(3)
with wc1:
    washing_code_key = st.selectbox(
        "Washing Code",
        options=list(hx.WASHING_CODES.keys()),
        format_func=lambda k: f"Code {k}",
    )
with wc2:
    pln_price_raw = st.text_input("PLN Sales Price", value=pl_price_detected or "")
with wc3:
    is_100_cotton = st.checkbox("100% Single Material (Cotton seal dekhabe)")

pln_price = None
if pln_price_raw.strip():
    try:
        pln_price = float(pln_price_raw.replace(",", "."))
    except ValueError:
        st.warning("PLN price ta shothik number na — khali rakhte paro.")

designer_name = st.text_input("Designer", value="")

# ----------------------------------------------------------------
# 4) Enrich rows: washing_code, prices, Cotton, product_name, Designer
# ----------------------------------------------------------------
translations_df = hx.load_product_translations()
material_df = hx.load_material_translations()

for r in results:
    r["washing_code"] = hx.WASHING_CODES.get(washing_code_key, "")
    r["Designer"] = designer_name
    r["Cotton"] = "Z" if is_100_cotton else ""

    if pln_price is not None:
        currency_values = hx.find_closest_price(pln_price)
        if currency_values:
            r.update(currency_values)
            r["PLN"] = hx.format_number(pln_price, "PLN")
        else:
            st.warning("Ei PLN price-er jonno price ladder e match paini.")

    if not translations_df.empty and "Item_name_EN" in r:
        match = translations_df[translations_df.get("EN", "") == r.get("Item_name_EN", "")]
        if not match.empty:
            row_t = match.iloc[0]
            r["product_name"] = hx.format_product_translations(r.get("Item_name_EN", ""), row_t)

# ----------------------------------------------------------------
# 5) Preview extracted data
# ----------------------------------------------------------------
st.header("4. Extracted Data (preview)")
st.dataframe(results, use_container_width=True)

# ----------------------------------------------------------------
# 6) Generate Front Side
# ----------------------------------------------------------------
st.header("5. Generate Front Side")

if st.button("🏷️ Generate Front Side PDFs", type="primary"):
    try:
        front_pdfs = hf.generate_batch(results)
        st.success(f"{len(front_pdfs)} ta Front Side PDF generate hoise.")
        for i, (row, pdf_bytes) in enumerate(zip(results, front_pdfs), start=1):
            fname = f"Hangtag_Front_{row.get('Order_ID','row')}_{i}.pdf"
            st.download_button(
                label=f"⬇️ Download {fname}",
                data=pdf_bytes,
                file_name=fname,
                mime="application/pdf",
                key=f"dl_{i}",
            )
    except FileNotFoundError:
        st.error(
            "templates/Hangtag/front_side.pdf paoa jayni. "
            "Cleaned template ta oi path-e rakho, tarpor abar try koro."
        )
    except Exception as e:
        st.error(f"Generate korte giye error: {e}")

st.divider()
st.caption(f"Generated on {datetime.today().strftime('%d-%m-%Y')} · Hangtag module v0.1 (Front only)")
