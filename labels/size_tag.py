"""
labels/size_tag.py
Size Tag stickers (Regular / With OEKO-TEX variants) — 6-panel size ladder
with the item's English name printed on each panel. Header (Order ID, Item,
Style Code, Color, Designer, etc.) uses the same layout as
pad_label/inner_label/outer_label, via config/size_tag_mapping.json (a copy
of pad_header_mapping.json's shape, plus Item_name_English x6).

Two template variants, selected by name:
    "Regular"   -> Size_Tag_Regular.pdf    (70mm x 46mm)
    "OEKO-TEX"  -> Size_Tag_OEKO_TEX.pdf   (86mm x 46mm, has the OEKO-TEX
                   certification badge on each panel)

NOTE: the "PRODUCT NAME" / item-name text in the source templates uses a
Poppins-SemiBold font we don't have a .ttf for yet — falls back to
Helvetica-Bold (hebo) for now. Drop Poppins-SemiBold.ttf into /fonts and
update the "font" key in config/size_tag_mapping.json to switch to it later.
"""
import os
import json
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from engine.label_engine import fill_single_label, generate_multipage_pdf

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
CONFIG_PATH = os.path.join(BASE_DIR, "config", "size_tag_mapping.json")

# ----- New: Folder-based template discovery for cascading dropdown -----
SIZETAG_BASE = os.path.join(BASE_DIR, "templates", "Sizetag")

def get_available_options():
    """
    Scans the Sizetag folder and returns a nested dict of available options.
    Returns: {
        "Regular": {
            "PB & PG": ["K. C. PRINT LTD", "Knit Concern Ltd"],
            "OG & OB": [...]
        },
        "With OEKO-TEX": {
            "PB & PG": ["K. C. PRINT LTD", ...]
        }
    }
    """
    options = {}
    if not os.path.exists(SIZETAG_BASE):
        return options

    for type_name in os.listdir(SIZETAG_BASE):
        type_path = os.path.join(SIZETAG_BASE, type_name)
        if not os.path.isdir(type_path):
            continue
        options[type_name] = {}
        for dept in os.listdir(type_path):
            dept_path = os.path.join(type_path, dept)
            if not os.path.isdir(dept_path):
                continue
            customers = []
            for cust in os.listdir(dept_path):
                cust_path = os.path.join(dept_path, cust)
                if os.path.isdir(cust_path):
                    # Check if "All" folder exists with a PDF
                    all_path = os.path.join(cust_path, "All")
                    if os.path.exists(all_path) and any(f.endswith('.pdf') for f in os.listdir(all_path)):
                        customers.append(cust)
            if customers:
                options[type_name][dept] = customers
    return options

def get_pdf_path(type_name, department, customer, base_path=SIZETAG_BASE):
    """Returns the full path to the Size Tag PDF for the selected options."""
    if not all([type_name, department, customer]):
        return None
    # Expected path: Sizetag/Type/Department/Customer/All/Size Tag.pdf
    pdf_path = os.path.join(base_path, type_name, department, customer, "All", "Size Tag.pdf")
    return pdf_path if os.path.exists(pdf_path) else None

# ----- End of new functions -----

# Original template dict (still used by the batch generation for other labels)
TEMPLATES = {
    "Regular": os.path.join(BASE_DIR, "templates", "Size_Tag_Regular.pdf"),
    "OEKO-TEX": os.path.join(BASE_DIR, "templates", "Size_Tag_OEKO_TEX.pdf"),
}

DEFAULT_TEMPLATE_KEY = "Regular"
TEMPLATE_PATH = TEMPLATES[DEFAULT_TEMPLATE_KEY]  # used for filename derivation

def load_field_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def generate_single(row: dict, variant: str = DEFAULT_TEMPLATE_KEY) -> bytes:
    """variant must be one of TEMPLATES.keys()."""
    template_path = TEMPLATES.get(variant, TEMPLATES[DEFAULT_TEMPLATE_KEY])
    field_config = load_field_config()
    return fill_single_label(template_path, row, field_config)

def generate_batch(rows: list, variant: str = DEFAULT_TEMPLATE_KEY) -> bytes:
    """rows = list of Excel row dicts. Returns one merged multi-page PDF."""
    template_path = TEMPLATES.get(variant, TEMPLATES[DEFAULT_TEMPLATE_KEY])
    field_config = load_field_config()
    return generate_multipage_pdf(template_path, rows, field_config)
