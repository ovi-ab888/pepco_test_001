"""
app.py — PEPCO Hangtag Front Side Generator (CSV-driven, no PDF extractor)

Upload a CSV with these columns (matches the SS27 app's export format):
    Order_ID, Style, Colour, Supplier_product_code, Item_classification,
    Supplier_name, today_date, Collection, Colour_SKU, Style_Merch_Season,
    Batch, barcode, washing_code, EUR, BGN, BAM, PLN, RON, CZK, UAH, MKD,
    RSD, HUF, product_name, Dept, Item_name_English, Season, Sizes, Cotton

Only these are actually used by the Front Side template right now:
    product_name, EUR, BAM, PLN, RON, CZK, MKD, RSD, HUF
(the rest ride along for when Back Side / Pad are wired in later)

Repo structure needed:
    app.py
    labels/hangtag_front.py
    templates/Hangtag/front_side.pdf   <- your cleaned template
"""

import streamlit as st
import pandas as pd
from datetime import datetime

from labels import hangtag_front as hf

st.set_page_config(page_title="PEPCO Hangtag Front Generator", page_icon="🏷️", layout="wide")
st.title("🏷️ PEPCO Hangtag — Front Side Generator")
st.caption("CSV upload → generate. No PDF extraction step.")

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
st.caption("Kono field change lagle direct table-e edit koro.")
edited_df = st.data_editor(df, use_container_width=True, num_rows="fixed")

rows = edited_df.fillna("").to_dict(orient="records")

# ----------------------------------------------------------------
# 3) Generate
# ----------------------------------------------------------------
st.header("3. Generate Front Side")

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

st.divider()
st.caption(f"Generated on {datetime.today().strftime('%d-%m-%Y')} · Hangtag Front (CSV-driven) v0.2")
