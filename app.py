"""
app.py — PEPCO Hangtag Front Side Generator (CSV-driven + live position/font adjustor)

Repo structure needed:
    app.py
    labels/hangtag_front.py
    config/hangtag_front_mapping.json
    fonts/DejaVuSans.ttf               <- Unicode font (Cyrillic/Greek support)
    templates/Hangtag/front_side.pdf   <- your cleaned template
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime

import fitz  # PyMuPDF
from labels import hangtag_front as hf

st.set_page_config(page_title="PEPCO Hangtag Front Generator", page_icon="🏷️", layout="wide")
st.title("🏷️ PEPCO Hangtag — Front Side Generator")
st.caption("CSV upload → generate → preview → adjust position/font size live.")

# ----------------------------------------------------------------
# 1) Upload CSV
# ----------------------------------------------------------------
st.header("1. Upload Data CSV")
uploaded_csv = st.file_uploader("Data CSV (Order_ID, product_name, EUR, PLN, ...)", type=["csv"])

if uploaded_csv is None:
    st.info("CSV upload korle data preview + generate option ashbe.")
    st.stop()

try:
    df = pd.read_csv(uploaded_csv)
except Exception as e:
    st.error(f"CSV porte giye error: {e}")
    st.stop()

if df.empty:
    st.error("CSV file khali.")
    st.stop()

st.success(f"{len(df)} ta row load hoise.")

# ----------------------------------------------------------------
# 2) Preview / edit data
# ----------------------------------------------------------------
st.header("2. Review Data")
edited_df = st.data_editor(df, use_container_width=True, num_rows="fixed")
rows = edited_df.fillna("").to_dict(orient="records")

# ---- Diagnostic: flag rows with missing/empty product_name ----
missing_pn = [i for i, r in enumerate(rows) if not str(r.get("product_name", "")).strip()]
if missing_pn:
    st.warning(f"⚠️ {len(missing_pn)} ta row-e 'product_name' khali ache (row index: {missing_pn}). "
               f"CSV-e oi column check koro.")

# ----------------------------------------------------------------
# 3) Generate (bulk download)
# ----------------------------------------------------------------
st.header("3. Generate Front Side (bulk)")
col1, col2 = st.columns(2)
with col1:
    if st.button("📄 Generate ONE combined PDF (all rows)", type="primary"):
        try:
            pdf_bytes = hf.generate_batch_pdf(rows)
            fname = f"Hangtag_Front_{rows[0].get('Order_ID','batch')}_{datetime.today().strftime('%d%m%Y')}.pdf"
            st.download_button("⬇️ Download combined PDF", data=pdf_bytes, file_name=fname,
                                mime="application/pdf")
        except FileNotFoundError:
            st.error("templates/Hangtag/front_side.pdf paoa jayni — template file ta repo-te rakho.")
        except Exception as e:
            st.error(f"Generate korte giye error: {e}")
with col2:
    if st.button("📑 Generate SEPARATE PDF per row"):
        try:
            pdfs = hf.generate_batch(rows)
            st.success(f"{len(pdfs)} ta PDF ready.")
            for i, (row, pdf_bytes) in enumerate(zip(rows, pdfs), start=1):
                fname = f"Hangtag_Front_{row.get('Order_ID','row')}_{i}.pdf"
                st.download_button(f"⬇️ {fname}", data=pdf_bytes, file_name=fname,
                                    mime="application/pdf", key=f"dl_{i}")
        except FileNotFoundError:
            st.error("templates/Hangtag/front_side.pdf paoa jayni — template file ta repo-te rakho.")
        except Exception as e:
            st.error(f"Generate korte giye error: {e}")

# ----------------------------------------------------------------
# 4) Live Preview + Position/Font Adjustor
# ----------------------------------------------------------------
st.header("4. 🎯 Live Preview & Position/Font Adjustor")
st.caption("Ekhane change korle sathe sathe preview update hobe. Thik hoye gele niche theke JSON download kore GitHub-e config/hangtag_front_mapping.json replace koro.")

if "mapping" not in st.session_state:
    try:
        st.session_state.mapping = hf.load_mapping()
    except Exception:
        st.session_state.mapping = {"product_name": {"bbox": [6.9, 32.5, 124.3, 134.6], "fontsize": 4.4, "color": "black"}, "prices": {}}

mapping = st.session_state.mapping

preview_row_idx = st.selectbox("Preview korার jonno row select koro", options=list(range(len(rows))),
                                format_func=lambda i: f"Row {i+1} — {rows[i].get('Order_ID','')}")
preview_row = rows[preview_row_idx]

pn_debug = str(preview_row.get("product_name", ""))
st.code(f"product_name length: {len(pn_debug)} chars\nFirst 120 chars: {pn_debug[:120]!r}", language=None)

adj_col, prev_col = st.columns([1, 1])

with adj_col:
    st.subheader("Fonts (optional upload — for testing before committing to repo)")
    uploaded_product_font = st.file_uploader("Product Name font (Arial.ttf)", type=["ttf", "otf"], key="pf_upload")
    uploaded_price_font = st.file_uploader("Price font (MyriadPro-Semibold.ttf/otf)", type=["ttf", "otf"], key="prf_upload")

    if uploaded_product_font is not None:
        uploaded_product_font.seek(0)
        product_font_bytes = uploaded_product_font.read()
    else:
        product_font_bytes = None

    if uploaded_price_font is not None:
        uploaded_price_font.seek(0)
        price_font_bytes = uploaded_price_font.read()
    else:
        price_font_bytes = None

    st.subheader("Product Name box")
    pn = mapping.get("product_name", {"bbox": [6.9, 32.5, 124.3, 134.6], "fontsize": 4.4, "color": "black", "align": "justify"})
    pn_x0 = st.number_input("x0", value=float(pn["bbox"][0]), key="pn_x0")
    pn_y0 = st.number_input("y0", value=float(pn["bbox"][1]), key="pn_y0")
    pn_x1 = st.number_input("x1", value=float(pn["bbox"][2]), key="pn_x1")
    pn_y1 = st.number_input("y1", value=float(pn["bbox"][3]), key="pn_y1")
    pn_fs = st.number_input("Font size", value=float(pn["fontsize"]), step=0.1, key="pn_fs")
    pn_align = st.selectbox("Align", options=["justify", "left", "center", "right"],
                             index=["justify", "left", "center", "right"].index(pn.get("align", "justify")),
                             key="pn_align")

    mapping["product_name"] = {"bbox": [pn_x0, pn_y0, pn_x1, pn_y1], "fontsize": pn_fs,
                                "color": pn.get("color", "black"), "align": pn_align}

    st.subheader("Price fields")
    price_rows = []
    for cur, cfg in mapping.get("prices", {}).items():
        price_rows.append({"currency": cur, "x0": cfg["bbox"][0], "y0": cfg["bbox"][1],
                            "x1": cfg["bbox"][2], "y1": cfg["bbox"][3], "fontsize": cfg["fontsize"]})
    price_df = pd.DataFrame(price_rows)
    edited_price_df = st.data_editor(price_df, use_container_width=True, num_rows="fixed", key="price_editor")

    new_prices = {}
    for _, r in edited_price_df.iterrows():
        new_prices[r["currency"]] = {"bbox": [r["x0"], r["y0"], r["x1"], r["y1"]], "fontsize": r["fontsize"]}
    mapping["prices"] = new_prices

    if st.button("🔄 Render Preview", type="primary"):
        st.session_state.render_trigger = True

    st.download_button(
        "⬇️ Download Updated hangtag_front_mapping.json",
        data=json.dumps(mapping, indent=2, ensure_ascii=False),
        file_name="hangtag_front_mapping.json",
        mime="application/json",
    )
    st.caption("Download kore GitHub-e config/hangtag_front_mapping.json file ta replace koro.")

with prev_col:
    st.subheader("Preview")
    try:
        import warnings
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            doc = hf.fill_front_side(preview_row, mapping=mapping,
                                      product_font_bytes=product_font_bytes,
                                      price_font_bytes=price_font_bytes)
            for w in caught:
                st.warning(f"⚠️ {w.message}")
        pix = doc[0].get_pixmap(dpi=200)
        img_bytes = pix.tobytes("png")
        doc.close()
        st.image(img_bytes, use_container_width=True)
    except FileNotFoundError:
        st.error("templates/Hangtag/front_side.pdf paoa jayni — template file ta repo-te rakho.")
    except Exception as e:
        st.error(f"Preview generate korte giye error: {e}")

st.divider()
st.caption(f"Generated on {datetime.today().strftime('%d-%m-%Y')} · Hangtag Front v0.3 (live adjustor)")
