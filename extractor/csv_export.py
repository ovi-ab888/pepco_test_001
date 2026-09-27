# ================================================================
#  csv_export.py
#  Final table dekhano (edit kora jay) + ; separator CSV download
#  app.py te use korte:
#      from csv_export import render_editor_and_download
# ================================================================
import csv as pycsv
import re
from io import StringIO

import streamlit as st

# CSV-te je column gulo, je order e jabe
FINAL_COLS = [
    "Order_ID", "Style", "Colour", "Supplier_product_code",
    "Item_classification", "Supplier_name", "today_date",
    "Collection", "Colour_SKU", "Style_Merch_Season",
    "Batch", "barcode", "washing_code", "EUR", "BGN",
    "BAM", "PLN", "RON", "CZK", "UAH", "MKD", "RSD", "HUF",
    "product_name", "Dept", "Item_name_English", "Season", "Sizes",
    "Cotton"   # 100% Cotton hole "Z", na hole khali (column shob somoy thake)
]


# ================================================================
#  Build CSV with ; separator & quoted fields
# ================================================================
def build_csv_bytes(edited_df, final_cols):
    csv_buffer = StringIO()
    writer = pycsv.writer(
        csv_buffer,
        delimiter=';',
        quoting=pycsv.QUOTE_ALL
    )
    writer.writerow(final_cols)

    for row in edited_df.itertuples(index=False):
        writer.writerow(row)

    return csv_buffer.getvalue().encode('utf-8-sig')


# ================================================================
#  Custom CSV filename
#  PEPCO_{SEASON}_{SKUs}_Swingtag {SupplierCode}_00_{Style}.csv
# ================================================================
def build_csv_filename(df):
    first_row_df = df.iloc[0]
    season_val = first_row_df.get("Season", "UNKNOWN").upper()

    all_skus = df['Colour_SKU'].apply(
        lambda x: re.sub(r".*SKU\s*", "", x)
    ).tolist()
    sku_val = "_".join(all_skus) if all_skus else "UNKNOWN"

    supplier_code = first_row_df.get("Supplier_product_code", "UNKNOWN")
    style_val = first_row_df.get("Style", "UNKNOWN")

    return (
        f"PEPCO_{season_val}_{sku_val}_Swingtag "
        f"{supplier_code}_00_{style_val}.csv"
    )


# ================================================================
#  UI: editable table + Download button
# ================================================================
def render_editor_and_download(df):
    final_cols = list(FINAL_COLS)

    # Ensure all columns exist
    for col in final_cols:
        if col not in df.columns:
            df[col] = ""

    st.success("✅ Done!")
    st.subheader("Edit Before Download")

    edited_df = st.data_editor(df[final_cols])

    st.download_button(
        "📥 Download CSV",
        build_csv_bytes(edited_df, final_cols),
        file_name=build_csv_filename(df),
        mime="text/csv"
    )
