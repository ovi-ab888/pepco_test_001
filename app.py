import sys
import os
sys.path.append(os.path.dirname(__file__))

import streamlit as st
import pandas as pd
import io
import zipfile

# সব লেবেল জেনারেটর মডিউল ইমপোর্ট করুন
import labels.pad_label as pad_label
import labels.inner_label as inner_label
import labels.outer_label as outer_label
import labels.two_pieces_set as pieces_label
import labels.additional_care_instruction_tag as care_tag_label
import labels.look_at_my_back_sticker as back_sticker_label
import labels.two_packs as two_packs_label
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

    st.session_state["pdf_filename_row"] = extracted_df.iloc[0].to_dict()
    st.session_state["pdf_extracted_df"] = extracted_df.drop(columns=["_temp_sku_for_filename"])
    st.session_state["pdf_uploader_names"] = [f.name for f in pdf_files]

# -------------------------------
# 3. ডেটা এডিটর
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
# 4. লেবেল টাইপ সিলেক্ট ও জেনারেশন (আপডেটেড)
# -------------------------------
st.subheader("🖨️ Select Label Types to Generate")

# লেবেল টাইপের নাম ও সংশ্লিষ্ট ফাংশনের ম্যাপিং
label_options = {
    "Inner & Outer Sticker (i/o Pad)": pad_label.generate_batch,
    "Inner": inner_label.generate_batch,
    "Outer": outer_label.generate_batch,
    "2-Pieces-Set": pieces_label.generate_batch,
    "Additional Care Instruction Tag": care_tag_label.generate_batch,
    "Look at my back Sticker": back_sticker_label.generate_batch,
    "Two Packs": two_packs_label.generate_batch,
}

# চেকবক্সের মাধ্যমে একাধিক সিলেক্ট করার অপশন
selected_labels = []
cols = st.columns(3)  # ৩ কলামে সাজানো
for i, (label_name, _) in enumerate(label_options.items()):
    with cols[i % 3]:
        if st.checkbox(label_name, key=f"chk_{i}"):
            selected_labels.append(label_name)

if not selected_labels:
    st.info("☝️ Please select at least one label type to generate.")

# জেনারেট বাটন
if selected_labels and st.button("🚀 Generate Selected Labels", type="primary"):
    rows = corrected_df.to_dict(orient="records")
    
    with st.spinner(f"⏳ Generating {len(selected_labels)} label type(s)..."):
        # জিপ ফাইল তৈরি
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for label_name in selected_labels:
                # সংশ্লিষ্ট ফাংশন খুঁজে বের করা
                generate_func = label_options[label_name]
                
                # লেবেল জেনারেট করা
                pdf_bytes = generate_func(rows)
                
                # ফাইল নাম তৈরি
                filename_row = dict(st.session_state["pdf_filename_row"])
                filename_row.update(rows[0])
                base_filename = extractor.build_filename(filename_row, extension="pdf")
                
                # লেবেল টাইপ অনুযায়ী নাম পরিবর্তন
                if label_name == "Inner & Outer Sticker (i/o Pad)":
                    final_filename = base_filename.replace(".pdf", "_Inner_Outer_Pad.pdf")
                elif label_name == "Inner":
                    final_filename = base_filename.replace(".pdf", "_Inner.pdf")
                elif label_name == "Outer":
                    final_filename = base_filename.replace(".pdf", "_Outer.pdf")
                else:
                    # স্পেস ও স্পেশাল ক্যারেক্টার প্রতিস্থাপন
                    clean_name = label_name.replace(" ", "_").replace("&", "and")
                    final_filename = base_filename.replace(".pdf", f"_{clean_name}.pdf")
                
                # জিপে যোগ করা
                zip_file.writestr(final_filename, pdf_bytes)
        
        zip_buffer.seek(0)
        
        # সফল বার্তা
        st.success(f"✅ Done! {len(selected_labels)} label type(s) generated and packaged in a ZIP file.")
        
        # জিপ ফাইল ডাউনলোড
        st.download_button(
            "⬇️ Download All Labels (ZIP)",
            data=zip_buffer,
            file_name=f"PEPCO_Labels_{extractor.build_filename(filename_row, extension='').replace('.', '_')}.zip",
            mime="application/zip",
            use_container_width=True,
        )

# -------------------------------
# 5. CSV ডাউনলোড (অপরিবর্তিত)
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

st.divider()
st.caption("💡 Tip: You can edit any field in the table above before generating the label.")
