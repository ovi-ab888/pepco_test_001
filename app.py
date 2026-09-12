"""
app.py — PEPCO Hangtag Generator (production, clean)

Upload a data CSV (Order_ID, Style, Colour, product_name, prices,
Collection, Colour_SKU, Batch, barcode, washing_code, Cotton, etc.) and
download the final Pad layout PDF(s) — Front + Back(s) + header, ready
to print.

Repo structure needed:
    app.py
    labels/hangtag_front.py
    labels/hangtag_back.py
    labels/hangtag_pad.py
    config/hangtag_front_mapping.json
    config/hangtag_back_mapping.json
    config/hangtag_pad_mapping.json
    fonts/ArialRegular.ttf, ArialBold.ttf, MyriadProSemibold.otf, PEPCO_Ovi.ttf, Tahoma.ttf
    templates/Hangtag/front_side.pdf, back_side.pdf, pad.pdf
"""

import streamlit as st
import pandas as pd
from datetime import datetime

from labels import hangtag_pad as hp

st.set_page_config(page_title="PEPCO Hangtag Generator", page_icon="🏷️", layout="wide")
st.title("🏷️ PEPCO Hangtag Generator")

# ----------------------------------------------------------------
# 1) Upload Data CSV
# ----------------------------------------------------------------
st.header("1. Upload Data CSV")
uploaded_csv = st.file_uploader("Data CSV", type=["csv"])

if uploaded_csv is None:
    st.info("CSV upload korle data preview + download option ashbe.")
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
# 2) Review / edit data
# ----------------------------------------------------------------
st.header("2. Review Data")
st.caption("Kono field change lagle direct table-e edit koro.")
edited_df = st.data_editor(df, use_container_width=True, num_rows="fixed")
rows = edited_df.fillna("").to_dict(orient="records")

# ----------------------------------------------------------------
# 3) Generate & Download Pad Layout
# ----------------------------------------------------------------
st.header("3. Download Pad Layout")

groups = hp.group_rows_for_pads(rows)
st.caption(f"{len(rows)} ta row → {len(groups)} ta Pad-e group hoise "
           f"(same product/price -> ekshathe, protita Pad-e max "
           f"{len(hp.load_mapping()['back_rects'])} ta unit).")

col1, col2 = st.columns(2)

with col1:
    if st.button("📄 Download combined PDF (all Pads)", type="primary"):
        try:
            pdf_bytes = hp.generate_batch_pdf(rows)
            fname = f"Hangtag_Pad_{rows[0].get('Order_ID','batch')}_{datetime.today().strftime('%d%m%Y')}.pdf"
            st.download_button("⬇️ Download PDF", data=pdf_bytes, file_name=fname,
                                mime="application/pdf", key="combined_dl")
        except FileNotFoundError as e:
            st.error(f"Template/font file paoa jayni: {e}")
        except Exception as e:
            st.error(f"Generate korte giye error: {e}")

with col2:
    if st.button("📑 Download SEPARATE PDF per Pad"):
        try:
            pdfs = hp.generate_batch(rows)
            st.success(f"{len(pdfs)} ta Pad PDF ready.")
            for i, pdf_bytes in enumerate(pdfs, start=1):
                fname = f"Hangtag_Pad_{i}_{datetime.today().strftime('%d%m%Y')}.pdf"
                st.download_button(f"⬇️ {fname}", data=pdf_bytes, file_name=fname,
                                    mime="application/pdf", key=f"dl_{i}")
        except FileNotFoundError as e:
            st.error(f"Template/font file paoa jayni: {e}")
        except Exception as e:
            st.error(f"Generate korte giye error: {e}")

st.divider()
st.caption(f"Generated on {datetime.today().strftime('%d-%m-%Y')} · Hangtag Generator v1.0")
