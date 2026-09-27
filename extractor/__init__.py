# ================================================================
#  extractor/__init__.py
#  Label App compatibility + SS27 modules
# ================================================================

from .pdf_extractor import extract_data_from_pdf, extract_order_id_only
from .auto_fields import (
    make_today_date,
    make_colour_sku,
    make_style_merch_season,
    make_batch,
    get_dept_value,
    clean_item_name_english,
)
from .classification import (
    map_item_class_to_dept_label,
    modify_collection,
    map_collection_name,
)
from .constants import WASHING_CODES, COLLECTION_MAPPING
from .data_loaders import (
    load_product_translations,
    load_material_translations,
    load_price_data,
)
from .price_helpers import parse_pln_price, apply_price_columns
from .translation import format_product_translations
from .material_ui import render_material_section
from .csv_export import render_editor_and_download

# ------------------------------------------------
#  Label App compatibility functions
# ------------------------------------------------
import pandas as pd
from datetime import datetime
import re
import fitz


def extract_rows_from_pdfs(pdf_files) -> pd.DataFrame:
    """
    Label App যেভাবে কল করে:
        extracted_df = extractor.extract_rows_from_pdfs(pdf_files)
    এখানে SS27 extractor ব্যবহার করে পুরনো ফরম্যাটে DataFrame রিটার্ন করে।
    """
    if not pdf_files:
        return pd.DataFrame()

    primary = pdf_files[0]
    others = pdf_files[1:]

    # Extra Order IDs
    extra_ids = []
    for f in others:
        oid = extract_order_id_only(f)
        if oid:
            extra_ids.append(oid)
    extra_order_ids = "+".join(extra_ids) if extra_ids else ""

    # SS27 extractor চালাও
    result_data, _ = extract_data_from_pdf(primary)
    if not result_data:
        return pd.DataFrame()

    # Extra Order ID জোড়া
    if extra_order_ids:
        for row in result_data:
            row["Order_ID"] = str(row.get("Order_ID", "")) + "+" + extra_order_ids

    # Label App যে কলামগুলো আশা করে সেগুলো ম্যাপ করি
    rows = []
    for r in result_data:
        # SKU বের করি Colour_SKU থেকে
        colour_sku = r.get("Colour_SKU", "")
        sku_match = re.search(r"SKU\s*(\d+)", str(colour_sku))
        sku = sku_match.group(1) if sku_match else "UNKNOWN"

        row = {
            "Order_ID": r.get("Order_ID", ""),
            "Style": r.get("Style", ""),
            "Colour": r.get("Colour", ""),
            "Supplier_product_code": r.get("Supplier_product_code", ""),
            "Item_classification": r.get("Item_classification", ""),
            "Supplier_name": r.get("Supplier_name", ""),
            "today_date": r.get("today_date", datetime.today().strftime("%d-%m-%Y")),
            "Item_name_English": clean_item_name_english(r.get("Item_name_EN", "")),
            "Season": r.get("Season", ""),
            "Pictogram": "",                    # SS27-এ নেই → খালি
            "Promotional": "",                  # SS27-এ নেই → খালি
            "Product_name": r.get("Item_name_EN", ""),
            "Inner_kg": "",
            "Season_st": r.get("Season", ""),
            "Inner_qty": "",
            "Outer_qty": "",
            "Sizes": r.get("Sizes", ""),
            "_temp_sku_for_filename": sku,
            # Extra useful fields (Label App ignore করবে)
            "Collection": r.get("Collection", ""),
            "Colour_SKU": colour_sku,
            "Batch": r.get("Batch", ""),
            "barcode": r.get("barcode", ""),
        }

        # TC & Barcode slots (পুরনো ফরম্যাট)
        for i in range(7):
            row[f"TC_Number_st{i+1}"] = ""
            row[f"Barcode_st{i+1}"] = r.get("barcode", "") if i == 0 else ""

        rows.append(row)

    return pd.DataFrame(rows)


def build_filename(row: dict, extension: str = "pdf", template_name: str = "Sticker") -> str:
    """
    Label App-এর পুরনো filename প্যাটার্ন:
    PEPCO_{SEASON}_{SKU}_{TEMPLATE} {SUPPLIER_CODE}_00_{STYLE}.{ext}
    """
    season_val = str(row.get("Season", "UNKNOWN")).upper() or "UNKNOWN"
    sku = row.get("_temp_sku_for_filename", "UNKNOWN")
    supplier_code = row.get("Supplier_product_code", "UNKNOWN")
    style_val = row.get("Style", "UNKNOWN")
    return f"PEPCO_{season_val}_{sku}_{template_name} {supplier_code}_00_{style_val}.{extension}"


__all__ = [
    # Label App compatibility
    "extract_rows_from_pdfs",
    "build_filename",
    # SS27 modules
    "extract_data_from_pdf",
    "extract_order_id_only",
    "make_today_date",
    "make_colour_sku",
    "make_style_merch_season",
    "make_batch",
    "get_dept_value",
    "clean_item_name_english",
    "map_item_class_to_dept_label",
    "modify_collection",
    "map_collection_name",
    "WASHING_CODES",
    "COLLECTION_MAPPING",
    "load_product_translations",
    "load_material_translations",
    "load_price_data",
    "parse_pln_price",
    "apply_price_columns",
    "format_product_translations",
    "render_material_section",
    "render_editor_and_download",
]
