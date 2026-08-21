import sys
import os
sys.path.append(os.path.dirname(__file__))

import streamlit as st
import pandas as pd
import io
import zipfile

import theme
import auth

# পেজ কনফিগারেশন
st.set_page_config(page_title="PEPCO Label Automation", layout="wide")
theme.load_css()  # login page-ও এই style পাবে

# -------------------------------
# 0. লগইন চেক (সবার আগে)
# -------------------------------
if not auth.check_login():
    st.stop()

auth.logout_button()

# সব লেবেল জেনারেটর মডিউল ইমপোর্ট করুন
import labels.pad_label as pad_label
import labels.inner_label as inner_label
import labels.outer_label as outer_label
import labels.two_pieces_set as pieces_label
import labels.additional_care_instruction_tag as care_tag_label
import labels.look_at_my_back_sticker as back_sticker_label
import labels.two_packs as two_packs_label
import extractor

theme.main_header("PEPCO Label Automation", "Automated Label Data Extraction & Generation System")


# -------------------------------
# 1. ফাইল আপলোড সেকশন
# -------------------------------
pdf_files = st.file_uploader(
    "Upload PEPCO PDF",
    type=["pdf"],
    accept_multiple_files=True,
    key="pdf_uploader",
)
if not pdf_files:
    st.info("Upload and process your PEPCO PO's.")
    st.stop()

# -------------------------------
# 2. ডেটা এক্সট্রাকশন
# -------------------------------
if (
    "pdf_extracted_df" not in st.session_state
    or st.session_state.get("pdf_uploader_names") != [f.name for f in pdf_files]
):
    with st.spinner("🔄 Extracting data from PDF..."):
        extracted_df = extractor.extract_rows_from_pdfs(pdf_files)
    if extracted_df.empty:
        st.error("❌ Couldn't extract data from this PDF — check it's the right file type.")
        st.stop()
    extracted_df["Designer"] = auth.get_display_name()  # from the logged-in user, editable below
    st.session_state["pdf_filename_row"] = extracted_df.iloc[0].to_dict()
    st.session_state["pdf_extracted_df"] = extracted_df.drop(columns=["_temp_sku_for_filename"])
    st.session_state["pdf_uploader_names"] = [f.name for f in pdf_files]

# -------------------------------
# 3. ডেটা এডিটর
# -------------------------------
st.subheader("Review Data")
st.caption("Every field is editable — fix anything the extractor got wrong.")
corrected_df = st.data_editor(
    st.session_state["pdf_extracted_df"],
    use_container_width=True,
    num_rows="fixed",
    key="pdf_data_editor",
)

# -------------------------------
# 4. লেবেল টাইপ সিলেক্ট ও জেনারেশন
# -------------------------------
st.subheader("Select the required label")

label_options = {
    "Inner & Outer Sticker": pad_label,
    "2-Pieces-Set": pieces_label,
    "Additional Care Instruction Tag": care_tag_label,
    "Look at my back Sticker": back_sticker_label,
    "Two Packs Sticker": two_packs_label,
}


def _template_name_for(module) -> str:
    """The actual template PDF filename (no extension) this label module uses
    — e.g. 'pad' for templates/pad.pdf. Falls back to 'Sticker' if the module
    doesn't expose TEMPLATE_PATH yet."""
    path = getattr(module, "TEMPLATE_PATH", None)
    if not path:
        return "Sticker"
    return os.path.splitext(os.path.basename(path))[0]

# ---- Section 1: Benefite Tag and Sticker (LIVE — works today) ----
selected_labels = []
with st.expander("Benefite Tag and Sticker", expanded=True):
    cols = st.columns(4)
    for i, (label_name, _) in enumerate(label_options.items()):
        with cols[i % 4]:
            if st.checkbox(label_name, key=f"chk_{i}"):
                selected_labels.append(label_name)

# ---- Section 2: Size Tag (UI ONLY — not wired up yet) ----
with st.expander("Size Tag", expanded=False):
    c1, c2, c3, c4 = st.columns(4)
    c1.selectbox("Select Type", [""], key="size_type", disabled=True)
    c2.selectbox("Select Department", [""], key="size_dept", disabled=True)
    c3.selectbox("Select Costomer", [""], key="size_customer", disabled=True)
    c4.selectbox("Select Size", [""], key="size_size", disabled=True)

# ---- Section 3: Hangtag (UI ONLY — not wired up yet) ----
with st.expander("Hangtag", expanded=False):
    c1, c2, c3, c4 = st.columns(4)
    c1.text_input("Enter Composition", key="hangtag_composition", disabled=True)
    c2.text_input("Enter Price", key="hangtag_price", disabled=True)
    c3.selectbox("Select Washing Code", [""], key="hangtag_washing", disabled=True)
    c4.selectbox("Select Product Type", [""], key="hangtag_product_type", disabled=True)

# ---- Section 4: Care Label (UI ONLY — not wired up yet) ----
with st.expander("Care Label", expanded=False):
    c1, c2 = st.columns(2)
    c1.text_input("Enter Composition", key="care_composition", disabled=True)
    c2.selectbox("Select Washing Code", [""], key="care_washing", disabled=True)

st.caption("🚧 Size Tag / Hangtag / Care Label sections are UI placeholders for now — "
           "not yet wired up to generation.")

if not selected_labels:
    st.info("☝️ Please select at least one label type from **Benefite Tag and Sticker** to generate.")

if selected_labels and st.button("Generate Labels", type="primary"):
    rows = corrected_df.to_dict(orient="records")
    filename_row = dict(st.session_state.get("pdf_filename_row", {}))
    filename_row.update(rows[0])

    with st.spinner(f"⏳ Generating {len(selected_labels)} label type(s)..."):
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for label_name in selected_labels:
                module = label_options[label_name]
                pdf_bytes = module.generate_batch(rows)

                template_name = _template_name_for(module)
                final_filename = extractor.build_filename(
                    filename_row, extension="pdf", template_name=template_name
                )

                zip_file.writestr(final_filename, pdf_bytes)
        zip_buffer.seek(0)

    st.success(f"✅ Done! {len(selected_labels)} label type(s) generated and packaged in a ZIP file.")

    # ZIP filename = Supplier_product_code value
    supplier_code = str(filename_row.get("Supplier_product_code", "UNKNOWN")).strip() or "UNKNOWN"
    zip_name = f"{supplier_code}.zip"

    st.download_button(
        "⬇️ Download All Labels (ZIP)",
        data=zip_buffer,
        file_name=zip_name,
        mime="application/zip",
        use_container_width=True,
    )

# -------------------------------
# 5. CSV ডাউনলোড
# -------------------------------
with st.expander("💾 Also download the extracted data as CSV (optional)"):
    csv_bytes = corrected_df.to_csv(index=False, sep=";").encode("utf-8-sig")
    csv_filename_row = dict(st.session_state.get("pdf_filename_row", {}))
    csv_filename_row.update(corrected_df.iloc[0].to_dict())
    csv_download_name = extractor.build_filename(csv_filename_row, extension="csv")
    st.download_button(
        "⬇️ Download CSV",
        data=csv_bytes,
        file_name=csv_download_name,
        mime="text/csv",
        use_container_width=True,
    )

st.divider()
st.caption("💡 Tip: You can edit any field in the table above before generating the label.")
