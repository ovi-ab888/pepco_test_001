import sys
import os
sys.path.append(os.path.dirname(__file__))

import streamlit as st

import labels.pad_label as pad_label
import extractor

st.set_page_config(page_title="PEPCO Label Automation", layout="wide")
st.title("🏷️ PEPCO Label Automation")

st.caption("Upload the PEPCO order/tech-pack PDF — data is pulled out automatically. "
           "Fix anything wrong in the table, then generate.")

pdf_files = st.file_uploader(
    "Upload PEPCO PDF (add more files after the first just to pull in extra Order IDs)",
    type=["pdf"], accept_multiple_files=True, key="pdf_uploader",
)
if not pdf_files:
    st.info("Upload a PDF to continue.")
    st.stop()

if "pdf_extracted_df" not in st.session_state or st.session_state.get("pdf_uploader_names") != [f.name for f in pdf_files]:
    with st.spinner("Extracting data from PDF..."):
        extracted_df = extractor.extract_rows_from_pdfs(pdf_files)
    if extracted_df.empty:
        st.error("Couldn't extract data from this PDF — check it's the right file type.")
        st.stop()
    st.session_state["pdf_extracted_df"] = extracted_df
    st.session_state["pdf_uploader_names"] = [f.name for f in pdf_files]

st.subheader("Review & correct extracted data")
st.caption("Every field is editable — fix anything the extractor got wrong or left blank before generating.")
corrected_df = st.data_editor(
    st.session_state["pdf_extracted_df"],
    use_container_width=True,
    num_rows="fixed",
    key="pdf_data_editor",
)

st.subheader("Generate Labels")
if st.button("Generate PDF", type="primary"):
    rows = corrected_df.to_dict(orient="records")
    with st.spinner("Generating..."):
        final_pdf = pad_label.generate_batch(rows)
    st.success("Done!")
    st.download_button(
        "Download PDF", data=final_pdf,
        file_name="pad_labels.pdf", mime="application/pdf",
    )

with st.expander("💾 Also download the extracted data as CSV (optional)"):
    csv_bytes = corrected_df.to_csv(index=False, sep=";").encode("utf-8-sig")
    st.download_button("Download CSV", data=csv_bytes, file_name="extracted_data.csv", mime="text/csv")
