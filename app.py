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
from labels import hangtag_back as hb

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
    pn_align = st.selectbox("Align", options=["justify", "left", "center", "right"],
                             index=["justify", "left", "center", "right"].index(pn.get("align", "justify")),
                             key="pn_align")

    pn_auto_fit = st.checkbox("Auto-fit fontsize (fill the box automatically)",
                               value=pn.get("auto_fit", True), key="pn_auto_fit")

    if pn_auto_fit:
        c1, c2, c3 = st.columns(3)
        pn_max_fs = c1.number_input("Max font size", value=float(pn.get("max_fontsize", 5.5)), step=0.1, key="pn_max_fs")
        pn_min_fs = c2.number_input("Min font size", value=float(pn.get("min_fontsize", 3.5)), step=0.1, key="pn_min_fs")
        pn_step = c3.number_input("Fit step", value=float(pn.get("fit_step", 0.1)), step=0.05, key="pn_fit_step")
        mapping["product_name"] = {
            "bbox": [pn_x0, pn_y0, pn_x1, pn_y1], "fontsize": pn_max_fs, "color": pn.get("color", "black"),
            "align": pn_align, "auto_fit": True, "max_fontsize": pn_max_fs,
            "min_fontsize": pn_min_fs, "fit_step": pn_step,
        }
    else:
        pn_fs = st.number_input("Font size", value=float(pn.get("fontsize", 4.4)), step=0.1, key="pn_fs")
        mapping["product_name"] = {"bbox": [pn_x0, pn_y0, pn_x1, pn_y1], "fontsize": pn_fs,
                                    "color": pn.get("color", "black"), "align": pn_align, "auto_fit": False}

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

# ==================================================================
# BACK SIDE
# ==================================================================
st.divider()
st.header("5. Generate Back Side (bulk)")
bcol1, bcol2 = st.columns(2)
with bcol1:
    if st.button("📄 Generate ONE combined PDF (all rows) — Back", type="primary"):
        try:
            pdf_bytes = hb.generate_batch_pdf(rows)
            fname = f"Hangtag_Back_{rows[0].get('Order_ID','batch')}_{datetime.today().strftime('%d%m%Y')}.pdf"
            st.download_button("⬇️ Download combined PDF", data=pdf_bytes, file_name=fname,
                                mime="application/pdf", key="back_combined_dl")
        except FileNotFoundError:
            st.error("templates/Hangtag/back_side.pdf paoa jayni — template file ta repo-te rakho.")
        except Exception as e:
            st.error(f"Generate korte giye error: {e}")
with bcol2:
    if st.button("📑 Generate SEPARATE PDF per row — Back"):
        try:
            pdfs = hb.generate_batch(rows)
            st.success(f"{len(pdfs)} ta PDF ready.")
            for i, (row, pdf_bytes) in enumerate(zip(rows, pdfs), start=1):
                fname = f"Hangtag_Back_{row.get('Order_ID','row')}_{i}.pdf"
                st.download_button(f"⬇️ {fname}", data=pdf_bytes, file_name=fname,
                                    mime="application/pdf", key=f"back_dl_{i}")
        except FileNotFoundError:
            st.error("templates/Hangtag/back_side.pdf paoa jayni — template file ta repo-te rakho.")
        except Exception as e:
            st.error(f"Generate korte giye error: {e}")

# ----------------------------------------------------------------
# 6) Back Side — Live Preview + Position/Font Adjustor
# ----------------------------------------------------------------
st.header("6. 🎯 Live Preview & Position/Font Adjustor — Back Side")

DEFAULT_BACK_MAPPING = {
    "Collection": {"bbox": [50.6, 214.3, 90.3, 220.3], "fontsize": 4.5, "font": "arial", "color": "black"},
    "Colour_SKU": {"bbox": [49.4, 222.5, 91.6, 228.5], "fontsize": 4.5, "font": "arial", "color": "black"},
    "Style_Merch_Season": {"bbox": [43.0, 228.5, 98.0, 234.5], "fontsize": 4.5, "font": "arial", "color": "black"},
    "Batch": {"bbox": [59.4, 240.6, 90.3, 246.6], "fontsize": 4.5, "font": "arial", "color": "black"},
    "washing_code": {"bbox": [30.9, 32.5, 100.0, 44.0], "fontsize": 6.0, "font": "pictogram", "color": "pink"},
    "Cotton": {"bbox": [96.5, 6.0, 119.1, 28.9], "fontsize": 6.0, "font": "pictogram", "color": "pink"},
    "barcode": {"x0": 21.2, "x1": 101.2, "digits_y0": 274.5, "digits_y1": 285.0,
                "digits_fontsize": 8.8, "bars_height": 34, "color": "pink"},
}

if "back_mapping" not in st.session_state:
    try:
        st.session_state.back_mapping = hb.load_mapping()
    except Exception:
        st.session_state.back_mapping = DEFAULT_BACK_MAPPING

back_mapping = st.session_state.back_mapping

back_preview_idx = st.selectbox("Preview korার jonno row select koro (Back)", options=list(range(len(rows))),
                                 format_func=lambda i: f"Row {i+1} — {rows[i].get('Order_ID','')}",
                                 key="back_preview_idx")
back_preview_row = rows[back_preview_idx]

back_adj_col, back_prev_col = st.columns([1, 1])

with back_adj_col:
    st.subheader("Fonts (optional upload — for testing before committing to repo)")
    uploaded_arial_font = st.file_uploader("Arial font", type=["ttf", "otf"], key="back_arial_upload")
    uploaded_pictogram_font = st.file_uploader("Pictogram font (PEPCO_Ovi.ttf)", type=["ttf", "otf"], key="back_pictogram_upload")

    arial_font_bytes = None
    if uploaded_arial_font is not None:
        uploaded_arial_font.seek(0)
        arial_font_bytes = uploaded_arial_font.read()

    pictogram_font_bytes = None
    if uploaded_pictogram_font is not None:
        uploaded_pictogram_font.seek(0)
        pictogram_font_bytes = uploaded_pictogram_font.read()

    st.subheader("Text fields (Collection / Colour_SKU / Style_Merch_Season / Batch)")
    tf_rows = []
    for col in ["Collection", "Colour_SKU", "Style_Merch_Season", "Batch"]:
        cfg = back_mapping.get(col, DEFAULT_BACK_MAPPING[col])
        tf_rows.append({"field": col, "x0": cfg["bbox"][0], "y0": cfg["bbox"][1],
                         "x1": cfg["bbox"][2], "y1": cfg["bbox"][3], "fontsize": cfg["fontsize"]})
    tf_df = pd.DataFrame(tf_rows)
    edited_tf_df = st.data_editor(tf_df, use_container_width=True, num_rows="fixed", key="back_tf_editor")

    for _, r in edited_tf_df.iterrows():
        back_mapping[r["field"]] = {"bbox": [r["x0"], r["y0"], r["x1"], r["y1"]], "fontsize": r["fontsize"],
                                     "font": "arial", "color": "black"}

    st.subheader("Washing Code (pictogram)")
    wc = back_mapping.get("washing_code", DEFAULT_BACK_MAPPING["washing_code"])
    wc_x0 = st.number_input("wc x0", value=float(wc["bbox"][0]), key="wc_x0")
    wc_y0 = st.number_input("wc y0", value=float(wc["bbox"][1]), key="wc_y0")
    wc_x1 = st.number_input("wc x1", value=float(wc["bbox"][2]), key="wc_x1")
    wc_y1 = st.number_input("wc y1", value=float(wc["bbox"][3]), key="wc_y1")
    wc_fs = st.number_input("wc fontsize", value=float(wc["fontsize"]), step=0.1, key="wc_fs")
    back_mapping["washing_code"] = {"bbox": [wc_x0, wc_y0, wc_x1, wc_y1], "fontsize": wc_fs,
                                     "font": "pictogram", "color": "pink"}

    st.subheader("Cotton (pictogram)")
    ct = back_mapping.get("Cotton", DEFAULT_BACK_MAPPING["Cotton"])
    ct_x0 = st.number_input("cotton x0", value=float(ct["bbox"][0]), key="ct_x0")
    ct_y0 = st.number_input("cotton y0", value=float(ct["bbox"][1]), key="ct_y0")
    ct_x1 = st.number_input("cotton x1", value=float(ct["bbox"][2]), key="ct_x1")
    ct_y1 = st.number_input("cotton y1", value=float(ct["bbox"][3]), key="ct_y1")
    ct_fs = st.number_input("cotton fontsize", value=float(ct["fontsize"]), step=0.1, key="ct_fs")
    back_mapping["Cotton"] = {"bbox": [ct_x0, ct_y0, ct_x1, ct_y1], "fontsize": ct_fs,
                               "font": "pictogram", "color": "pink"}

    st.subheader("Barcode")
    bc = back_mapping.get("barcode", DEFAULT_BACK_MAPPING["barcode"])
    bc_x0 = st.number_input("barcode x0", value=float(bc["x0"]), key="bc_x0")
    bc_x1 = st.number_input("barcode x1", value=float(bc["x1"]), key="bc_x1")
    bc_dy0 = st.number_input("digits y0", value=float(bc["digits_y0"]), key="bc_dy0")
    bc_dy1 = st.number_input("digits y1", value=float(bc["digits_y1"]), key="bc_dy1")
    bc_height = st.number_input("bars height", value=float(bc["bars_height"]), key="bc_height")
    bc_dfs = st.number_input("digits fontsize", value=float(bc["digits_fontsize"]), step=0.1, key="bc_dfs")
    back_mapping["barcode"] = {"x0": bc_x0, "x1": bc_x1, "digits_y0": bc_dy0, "digits_y1": bc_dy1,
                                "bars_height": bc_height, "digits_fontsize": bc_dfs, "color": "pink"}

    st.download_button(
        "⬇️ Download Updated hangtag_back_mapping.json",
        data=json.dumps(back_mapping, indent=2, ensure_ascii=False),
        file_name="hangtag_back_mapping.json",
        mime="application/json",
        key="back_json_dl",
    )
    st.caption("Download kore GitHub-e config/hangtag_back_mapping.json file ta replace koro.")

with back_prev_col:
    st.subheader("Preview")
    try:
        doc = hb.fill_back_side(back_preview_row, mapping=back_mapping,
                                 arial_font_bytes=arial_font_bytes,
                                 pictogram_font_bytes=pictogram_font_bytes)
        pix = doc[0].get_pixmap(dpi=200)
        img_bytes = pix.tobytes("png")
        doc.close()
        st.image(img_bytes, use_container_width=True)
    except FileNotFoundError:
        st.error("templates/Hangtag/back_side.pdf paoa jayni — template file ta repo-te rakho.")
    except Exception as e:
        st.error(f"Preview generate korte giye error: {e}")

st.divider()
st.caption(f"Generated on {datetime.today().strftime('%d-%m-%Y')} · Hangtag Front+Back v0.4 (live adjustor)")
