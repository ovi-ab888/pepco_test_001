# ================================================================
#  extractor package  (PEPCO SS27)
#  Usage from main app:
#      from extractor.pdf_extractor import extract_data_from_pdf, extract_order_id_only
#      from extractor.auto_fields import ...
#      from extractor.csv_export import render_editor_and_download
#      ...
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
from .data_loaders import load_product_translations, load_material_translations, load_price_data
from .price_helpers import parse_pln_price, apply_price_columns
from .translation import format_product_translations
from .material_ui import render_material_section
from .csv_export import render_editor_and_download

__all__ = [
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
