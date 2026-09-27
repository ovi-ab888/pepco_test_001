# ================================================================
#  app.py  —  PEPCO SS27 (main file)
#  Ekhane shudhu page config + pipeline + UI wiring ache.
#  Baki shob logic alada file e:
#     constants.py       WASHING_CODES, COLLECTION_MAPPING
#     pdf_extractor.py   PDF theke directly data extract
#     auto_fields.py     code-generated field (date, Batch, Dept ...)
#     data_loaders.py    Google Sheet loaders
#     classification.py  classification / collection helper
#     translation.py     multi-language product name
#     price_helpers.py   PLN parse + price ladder
#     material_ui.py     Material Composition UI
#     csv_export.py      editable table + CSV download
# ================================================================

# ---------- PAGE CONFIG (must be at top) ----------
import streamlit as st
st.set_page_config(
    page_title="PEPCO SS27",
    page_icon="🧾",
    layout="wide"
)

# ---------- Imports ----------
import re
import pandas as pd

# ---------- Local modules (same folder) ----------
from constants import WASHING_CODES
from pdf_extractor import extract_data_from_pdf, extract_order_id_only
from auto_fields import get_dept_value, clean_item_name_english
from data_loaders import load_product_translations, load_material_translations
from classification import (
    map_item_class_to_dept_label,
    modify_collection,
    map_collection_name,
)
from translation import format_product_translations
from price_helpers import parse_pln_price, apply_price_columns
from material_ui import render_material_section
from csv_export import render_editor_and_download


# ================================================================
#  MAIN WORKFLOW: PDF → DataFrame → UI → CSV
# ================================================================
def process_pepco_pdf(uploaded_pdf, extra_order_ids: str | None = None):
    """Main pipeline: parse PDF, build DF, apply UI choices, export CSV."""
    # ----- Load reference data -----
    translations_df = load_product_translations()
    material_translations_df = load_material_translations()

    if not (uploaded_pdf and not translations_df.empty):
        return

    # ----- Parse PDF to structured data -----
    result_data, detected_pl = extract_data_from_pdf(uploaded_pdf)
    if not result_data:
        return

    df = pd.DataFrame(result_data)

    # ----- Collection mapping -----
    df["Collection"] = df.apply(
        lambda r: map_collection_name(r["Collection"], r["Item_classification"]),
        axis=1
    )

    # ----- Base values from first row -----
    first_row = result_data[0] if len(result_data) > 0 else {}
    pdf_item_class = first_row.get("Item_classification", "")
    pdf_item_name_en = (first_row.get("Item_name_EN") or "").strip()
    pdf_item_name_en = re.sub(r'^\d+\.\s*', '', pdf_item_name_en).strip()

    # ----- Merge extra Order IDs from other PDFs -----
    if extra_order_ids:
        try:
            df['Order_ID'] = df['Order_ID'].astype(str) + "+" + extra_order_ids
        except Exception:
            pass

    # ============================================================
    #  UI Controls (Department, Product, Washing, PLN)
    # ============================================================
    c1, c2, c3, c4 = st.columns(4)

    # -- Department select (default from item_class) --
    depts = translations_df['DEPARTMENT'].dropna().unique().tolist()
    default_dept_label = map_item_class_to_dept_label(pdf_item_class)
    default_dept_index = 0

    if default_dept_label:
        for i, d in enumerate(depts):
            if str(d).strip().lower() == str(default_dept_label).strip().lower():
                default_dept_index = i
                break

    with c1:
        selected_dept = st.selectbox(
            "Select Department",
            options=depts,
            index=default_dept_index,
            key="ui_dept"
        )

    # -- Product list filtered by Department --
    filtered = translations_df[translations_df['DEPARTMENT'] == selected_dept]
    products = filtered['PRODUCT_NAME'].dropna().unique().tolist()

    default_product_index = 0
    if pdf_item_name_en:
        for i, p in enumerate(products):
            if str(p).strip().lower() == pdf_item_name_en.strip().lower():
                default_product_index = i
                break

    with c2:
        product_type = st.selectbox(
            "Select Product Type",
            options=products,
            index=default_product_index,
            key="ui_product"
        )

    # -- Washing code --
    washing_options = list(WASHING_CODES.keys())
    washing_default_index = washing_options.index('9') if '9' in washing_options else 0

    with c3:
        washing_code_key = st.selectbox(
            "Select Washing Code",
            options=washing_options,
            index=washing_default_index,
            key="ui_wash"
        )

    # -- PLN price manual input --
    with c4:
        default_pln = str(detected_pl) if detected_pl else ""
        pln_price_raw = st.text_input(
            "Enter PLN Price",
            value=default_pln,
            key="ui_pln_price"
        )

    pln_price = parse_pln_price(pln_price_raw)

    # ============================================================
    #  MATERIAL COMPOSITION UI  (material_ui.py)
    # ============================================================
    (
        selected_materials,
        cotton_value,
        material_trans_dict,
        material_compositions,
    ) = render_material_section(material_translations_df)

    # ============================================================
    #  DataFrame enrichment (Dept, Cotton, Collection, Product, Washing)
    # ============================================================
    df['Dept'] = df['Item_classification'].apply(get_dept_value)

    # Cotton column shob somoy thakbe: 100% Cotton hole "Z", na hole khali
    df['Cotton'] = cotton_value

    df['Collection'] = df.apply(
        lambda r: modify_collection(r['Collection'], r['Item_classification']),
        axis=1
    )

    product_row = filtered[filtered['PRODUCT_NAME'] == product_type]
    if not product_row.empty:
        df['product_name'] = format_product_translations(
            product_type,
            product_row.iloc[0],
            selected_materials,
            material_trans_dict,
            material_compositions
        )
    else:
        df['product_name'] = ""

    df['washing_code'] = WASHING_CODES[washing_code_key]

    # ============================================================
    #  PRICE LADDER + CSV EXPORT
    # ============================================================
    if pln_price is not None:
        if apply_price_columns(df, pln_price):
            # Item name English (cleaned & CAPITAL)
            df["Item_name_English"] = df["Item_name_EN"].apply(clean_item_name_english)

            render_editor_and_download(df)
        else:
            st.warning("⚠️ Processing stopped - valid PLN price not found")


# ================================================================
#  PEPCO SECTION (Uploader + Reset)
# ================================================================
def pepco_section():
    """Main PEPCO UI section (upload + reset + extra order IDs merge)."""
    st.subheader("PEPCO Data Processing")

    # One-time init for uploader key
    if "uploader_key" not in st.session_state:
        st.session_state.uploader_key = 0

    cols = st.columns([1, 6])

    # Reset / new upload button
    with cols[0]:
        def _reset_all():
            # Clear only app-related session keys
            for k in list(st.session_state.keys()):
                if k.startswith((
                    "ui_", "mat_", "pepco_",
                    "colour_", "colour_manual_", "colour_missing_"
                )):
                    st.session_state.pop(k, None)

            # Force uploader refresh
            st.session_state.uploader_key += 1
            # st.rerun() REMOVED (callback auto reruns)

        st.button("🆕 Upload New File", on_click=_reset_all)

    # File uploader (multi PDF)
    uploaded_pdfs = st.file_uploader(
        "Upload PEPCO Data file",
        type=["pdf"],
        key=f"pepco_uploader_{st.session_state.uploader_key}",
        accept_multiple_files=True
    )

    if uploaded_pdfs:
        if not isinstance(uploaded_pdfs, list):
            uploaded_pdfs = [uploaded_pdfs]

        primary_pdf = uploaded_pdfs[0]
        others = uploaded_pdfs[1:]

        # Collect Order_ID from additional PDFs
        other_ids = []
        for f in others:
            try:
                f.seek(0)
            except Exception:
                pass

            oid = extract_order_id_only(f)
            if oid:
                other_ids.append(oid)

            try:
                f.seek(0)
            except Exception:
                pass

        concatenated_ids = "+".join(other_ids) if other_ids else ""
        process_pepco_pdf(primary_pdf, extra_order_ids=concatenated_ids)


# ================================================================
#  MAIN APP
# ================================================================
def main():
    # Title
    st.title("PEPCO Automation App")

    # Main content
    pepco_section()

    st.markdown("---")
    st.caption("This app developed by Ovi")


# ================================================================
#  ENTRY POINT
# ================================================================
if __name__ == "__main__":
    main()
