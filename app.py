import sys
import os
sys.path.append(os.path.dirname(__file__))

import streamlit as st
import pandas as pd

# লেবেল জেনারেটর মডিউলগুলো ইমপোর্ট করুন
import labels.pad_label as pad_label
import labels.inner_label as inner_label
import labels.outer_label as outer_label
import labels._2_pieces_set as pieces_label  # নতুন টেমপ্লেট
import extractor

# পেজ কনফিগারেশন
st.set_page_config(page_title="PEPCO Label Automation", layout="wide")
st.title("📦 PEPCO Label Automation")
st.caption("Upload PEPCO order/PO PDF and generate labels effortlessly.")

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
    st.info("📄 Please upload a PDF to continue.")
    st.stop()

# -------------------------------
# 2. ডেটা এক্সট্রাকশন (শুধুমাত্র নতুন ফাইল আপলোড করলে)
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

    # ফাইল নামের জন্য আলাদা করে রাখা (ইউজারকে দেখানো হবে না)
    st.session_state["pdf_filename_row"] = extracted_df.iloc[0].to_dict()
    st.session_state["pdf_extracted_df"] = extracted_df.drop(columns=["_temp_sku_for_filename"])
    st.session_state["pdf_uploader_names"] = [f.name for f in pdf_files]

# -------------------------------
# 3. ডেটা এডিটর (ইউজার সংশোধন করতে পারবে)
# -------------------------------
st.subheader("✏️ Review & correct extracted data")
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
st.subheader("🖨️ Generate Layout")

# লেবেল টাইপ নির্বাচন
label_type = st.radio(
    "Select Label Type",
    ["Pad", "Inner", "Outer", "2-Pieces-Set"],
    horizontal=True,
    index=0,
)

if st.button("🚀 Generate PDF", type="primary"):
    rows = corrected_df.to_dict(orient="records")

    with st.spinner(f"⏳ Generating {label_type} label(s)..."):
        # টাইপ অনুযায়ী সঠিক ফাংশন কল
        if label_type == "Pad":
            final_pdf = pad_label.generate_batch(rows)
        elif label_type == "Inner":
            final_pdf = inner_label.generate_batch(rows)
        elif label_type == "Outer":
            final_pdf = outer_label.generate_batch(rows)
        else:  # 2-Pieces-Set
            final_pdf = pieces_label.generate_batch(rows)

    st.success("✅ Done! Your PDF is ready for download.")

    # ফাইল নাম তৈরি
    filename_row = dict(st.session_state["pdf_filename_row"])
    filename_row.update(rows[0])  # যেকোনো করেকশন ফাইলনেমে আপডেট করবে
    download_name = extractor.build_filename(filename_row, extension="pdf")

    # ডাউনলোড বাটন
    st.download_button(
        "⬇️ Download PDF",
        data=final_pdf,
        file_name=download_name,
        mime="application/pdf",
        use_container_width=True,
    )

# -------------------------------
# 5. (অপশনাল) CSV ডাউনলোড
# -------------------------------
with st.expander("💾 Also download the extracted data as CSV (optional)"):
    csv_bytes = corrected_df.to_csv(index=False, sep=";").encode("utf-8-sig")
    csv_filename_row = dict(st.session_state["pdf_filename_row"])
    csv_filename_row.update(corrected_df.iloc[0].to_dict())
    csv_download_name = extractor.build_filename(csv_filename_row, extension="csv")

    st.download_button(
        "⬇️ Download CSV",
        data=csv_bytes,
        file_name=csv_download_name,
        mime="text/csv",
        use_container_width=True,
    )

# -------------------------------
# 6. ফুটার/ইনফো
# -------------------------------
st.divider()
st.caption("💡 Tip: You can edit any field in the table above before generating the label.")
