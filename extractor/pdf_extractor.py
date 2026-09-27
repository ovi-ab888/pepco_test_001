# ================================================================
#  pdf_extractor.py
#  PEPCO PDF theke directly data extract korar sob function
#  app.py te use korte:
#      from pdf_extractor import extract_data_from_pdf, extract_order_id_only
# ================================================================
import re

import fitz  # PyMuPDF
import streamlit as st

from auto_fields import (
    make_today_date,
    make_colour_sku,
    make_style_merch_season,
    make_batch,
)


# ================================================================
#  SIZES
# ================================================================
def extract_sizes_from_pdf(pages_text):
    """Extract Sizes correctly even when split line-by-line.
    Supports:
      - 9/10, 11/12, 13/14, 15
      - S, M, L, XL, XXL
      - 3/4, 4/5, 5/6 ...
      - 6/9, 9/12, 12/18 ...
      - 92-98, 98-104, 110-116, 122-128
      - multiple sizes on one line separated by commas
    """
    size_pattern = re.compile(
        r"^(?:\d+(?:[/-]\d+)?|[A-Za-z]{1,4}(?:/[A-Za-z]{1,4})?)$",
        re.IGNORECASE
    )
    for text in pages_text:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for idx, line in enumerate(lines):
            if line.lower() == "sizes":
                sizes = []
                for next_line in lines[idx + 1:]:
                    upper = next_line.upper()
                    if upper == "TOTAL":
                        break
                    if upper == "COLOUR":
                        continue
                    candidates = re.split(r"\s*,\s*", next_line)
                    for cand in candidates:
                        cand = cand.strip()
                        if not cand:
                            continue
                        if size_pattern.fullmatch(cand) and cand.upper() not in ("COLOUR", "TOTAL"):
                            sizes.append(cand)
                if sizes:
                    return ", ".join(sizes)
    return ""


# ================================================================
#  PL SALES PRICE
# ================================================================
def extract_pl_sales_price_from_pdf(pages_text):
    """Extract PL Sales Price accurately across lines."""
    for text in pages_text:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for idx, line in enumerate(lines):
            if line == "PL" or line.startswith("PL "):
                # Single line check first
                prices = re.findall(r"\b\d+(?:[.,]\d{2})\b", line)
                if prices:
                    return prices[0].replace(",", ".")

                # Multi-line check for the next few lines
                for next_line in lines[idx + 1:idx + 5]:
                    prices = re.findall(r"\b\d+(?:[.,]\d{2})\b", next_line)
                    if prices:
                        return prices[0].replace(",", ".")
    return ""


# ================================================================
#  COLLECTION
# ================================================================
def extract_collection_value(raw_text):
    """
    Format: TYPE - NAME - SEASON - CODE
    Prothom part (TYPE) skip kore,
    baki theke SEASON (SS27) ar CODE (digit) bad diye je-ta thake sei-ta NAME.
    """
    parts = [p.strip() for p in raw_text.split("-") if p.strip()]

    if not parts:
        return "UNKNOWN"

    parts = parts[1:]   # prothom part (TYPE) skip

    for p in parts:
        if re.fullmatch(r"[A-Za-z]{2}\d{2}", p):  # SEASON skip (SS27, AW26)
            continue
        if p.isdigit():                            # CODE skip
            continue
        return p    # baki jeta thaklo sei-ta NAME

    return "UNKNOWN"


# ================================================================
#  COLOUR
# ================================================================
def extract_colour_from_pdf_pages(pages_text):
    """
    Ultra-robust PEPCO Colour Detection
    Supports:
        - Old 6-page PDF format
        - New 5-page PDF format
        - Broken layout (Colour row + size row merged)
        - Missing pantone
    """
    # -------- 1) Standard Colour Table --------
    for txt in pages_text:
        m = re.search(
            r"Colour.*?\n.*?\n\s*([A-Za-z ]+)\s+[0-9]{2}-[0-9]{4}",
            txt,
            re.IGNORECASE | re.DOTALL
        )
        if m:
            return m.group(1).strip().upper()

    # -------- 2) Purchase Price block --------
    for txt in pages_text:
        m2 = re.search(
            r"Purchase price.*?\n\s*([A-Za-z ]+)\s+[0-9]{2}-[0-9]{4}",
            txt,
            re.IGNORECASE | re.DOTALL
        )
        if m2:
            return m2.group(1).strip().upper()

    # -------- 3) Generic fallback using "colour" keyword --------
    for txt in pages_text:
        if "colour" in txt.lower():
            for line in txt.splitlines():
                if re.search(r"[A-Za-z ]+\s+[0-9]{2}-[0-9]{4}", line):
                    name = line.split()[0:-1]
                    if name:
                        return " ".join(name).upper()

    # -------- 4) Manual input fallback --------
    st.warning("⚠️ Colour not found in PDF. Enter colour manually:")
    manual = st.text_input("Colour (e.g. WHITE):", key="manual_colour_fix")
    return manual.strip().upper() if manual else "UNKNOWN"


# ================================================================
#  ORDER ID ONLY (extra PDF upload-er jonno)
# ================================================================
def extract_order_id_only(file):
    """Extract only Order ID from a PDF file."""
    pos = None
    try:
        pos = file.tell()
    except Exception:
        pass

    try:
        file.seek(0)
    except Exception:
        pass

    try:
        with fitz.open(stream=file.read(), filetype="pdf") as doc:
            page1_text = doc[0].get_text() if len(doc) > 0 else ""
    except Exception:
        try:
            file.seek(0 if pos is None else pos)
        except Exception:
            pass
        return None

    try:
        file.seek(0 if pos is None else pos)
    except Exception:
        pass

    m = re.search(
        r"Order\s*-\s*ID\s*\.{2,}\s*([A-Z0-9_+-]+)",
        page1_text,
        re.IGNORECASE
    )
    return m.group(1).strip() if m else None


# ================================================================
#  MAIN PDF EXTRACTION ENGINE
#  NOTE: Collection mapping (COLLECTION_MAPPING) ei file-e nai.
#        Sheta ekhon app.py-er process_pepco_pdf() e apply hoy.
# ================================================================
def extract_data_from_pdf(file):
    """Robust PEPCO extractor (5-page + 6-page).
    Returns: (list_of_row_dicts, detected_pl_price)  ba  (None, None)
    """
    try:
        raw = file.read()
        if not raw:
            st.error("Empty PDF uploaded.")
            return None, None

        doc = fitz.open(stream=raw, filetype="pdf")

        if len(doc) < 1:
            st.error("PDF must have at least 1 page.")
            return None, None

        pages_text = [doc[i].get_text() for i in range(len(doc))]
        full_text = "\n".join(pages_text)
        page1 = pages_text[0]

        # ---------------- Item Name EN ----------------
        item_name_en = None

        m_item = re.search(
            r"Item\s*name\s*English\s*[:\.]{1,}\s*(.+)",
            full_text,
            re.IGNORECASE
        )
        if not m_item:
            m_item = re.search(
                r"Item\s*name\s*[:\.]{1,}\s*(.+?)\n",
                full_text,
                re.IGNORECASE
            )
        if m_item:
            item_name_en = m_item.group(1).strip()

        # ---------------- SIZES + PL PRICE ----------------
        sizes = extract_sizes_from_pdf(pages_text)
        pl_price_detected = extract_pl_sales_price_from_pdf(pages_text)

        # ---------------- Identifiers ----------------
        merch_code = re.search(r"Merch\s*code\s*\.{2,}\s*([\w/]+)", page1)
        season = re.search(r"Season\s*\.{2,}\s*(\w+)?\s*(\d{2})", page1)
        style_code = re.search(r"\b\d{6}\b", page1)

        style_suffix = ""
        if merch_code and season:
            style_suffix = f"{merch_code.group(1).strip()}{season.group(2)}"
        elif merch_code:
            style_suffix = merch_code.group(1).strip()

        collection = re.search(r"Collection\s*\.{2,}\s*(.+)", page1)

        if collection:
            collection_value = extract_collection_value(collection.group(1))
        else:
            collection_value = "UNKNOWN"

        # ---------------- Collection Manual Fallback ----------------
        if not collection_value or collection_value == "UNKNOWN":
            st.warning("⚠️ Collection not found in PDF. Enter Collection manually:")
            manual_collection = st.text_input(
                "Collection (e.g. MODERN 1):",
                key="manual_collection_input"
            )
            if manual_collection and manual_collection.strip():
                collection_value = manual_collection.strip().upper()

        date_match = re.search(
            r"Handover\s*date\s*\.{2,}\s*(\d{2}/\d{2}/\d{4})",
            page1
        )

        batch_text = make_batch(date_match.group(1) if date_match else None)

        order_id = re.search(r"Order\s*-\s*ID\s*\.{2,}\s*(.+)", page1)
        item_class = re.search(r"Item classification\s*\.{2,}\s*(.+)", page1)
        supplier_code = re.search(r"Supplier product code\s*\.{2,}\s*(.+)", page1)
        supplier_name = re.search(r"Supplier name\s*\.{2,}\s*(.+)", page1)

        item_class_value = item_class.group(1).strip() if item_class else "UNKNOWN"

        # ---------------- AUTO COLOUR EXTRACTION ----------------
        colour = extract_colour_from_pdf_pages(pages_text)

        # ---------------- SKU + BARCODE ----------------
        skus = []
        barcodes = []
        excluded = set()

        for txt in pages_text:
            skus.extend(re.findall(r"\b\d{8}\b", txt))
            barcodes.extend(re.findall(r"\b\d{13}\b", txt))
            excluded.update(re.findall(r"barcode:\s*(\d{13})", txt))

        # Dedupe
        def _dedupe(seq):
            seen = set()
            out = []
            for x in seq:
                if x not in seen:
                    seen.add(x)
                    out.append(x)
            return out

        skus = _dedupe(skus)
        barcodes = _dedupe(barcodes)

        valid_barcodes = [b for b in barcodes if b not in excluded]

        if not skus or not valid_barcodes:
            st.error("SKU or Barcode missing.")
            return None, None

        # Align count mismatch
        if len(skus) != len(valid_barcodes):
            min_len = min(len(skus), len(valid_barcodes))
            st.warning(
                f"SKU ({len(skus)}) and Barcode ({len(valid_barcodes)}) differ. Using first {min_len}."
            )
            skus = skus[:min_len]
            valid_barcodes = valid_barcodes[:min_len]

        season_value = (
            f"{season.group(1)}{season.group(2)}"
            if season else "UNKNOWN"
        )

        # ---------------- BUILD RESULT ----------------
        results = []

        # Sizes ke list-e bhag koro
        sizes_list = [s.strip() for s in sizes.split(",")] if sizes else [""]

        # SKU + Barcode + Size ekshathe jora (zip = shobcheye chhoto list porjonto)
        for sku, barcode, size in zip(skus, valid_barcodes, sizes_list):
            results.append({
                "Order_ID": order_id.group(1).strip() if order_id else "UNKNOWN",
                "Style": style_code.group() if style_code else "UNKNOWN",
                "Colour": colour.title(),
                "Supplier_product_code": supplier_code.group(1).strip() if supplier_code else "UNKNOWN",
                "Item_classification": item_class_value,
                "Supplier_name": supplier_name.group(1).strip() if supplier_name else "UNKNOWN",
                "today_date": make_today_date(),
                "Collection": collection_value,
                "Colour_SKU": make_colour_sku(colour, sku),
                "Style_Merch_Season": make_style_merch_season(
                    style_code.group() if style_code else None, style_suffix
                ),
                "Batch": batch_text,
                "barcode": barcode,
                "Item_name_EN": item_name_en or "",
                "Season": season_value,
                "Sizes": size,
            })

        return results, pl_price_detected

    except Exception as e:
        st.error(f"PDF error: {str(e)}")
        return None, None
