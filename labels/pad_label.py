"""
labels/pad_label.py
"Pad" (full proof sheet) — the template stays BLANK. At generation time we:
  1. Generate the Inner label (via labels.inner_label, same config used for
     the standalone Inner output).
  2. Generate the Outer label (via labels.outer_label, same config used for
     the standalone Outer output).
  3. Composite both onto a copy of the blank template at the Inner/Outer
     box positions.
  4. Fill the header fields (Order ID, Item, Style Code, Color, Designer,
     etc.) directly on the pad.

This way inner_field_mapping.json / outer_field_mapping.json stay the single
source of truth — editing them updates the Pad output automatically too.
"""
import os
import json
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import fitz
from engine.label_engine import fill_single_label, compose_pdf_into_rect
import labels.inner_label as inner_label
import labels.outer_label as outer_label

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
# NOTE: filename here also drives the download filename (build_filename uses
# each label type's own template filename) — keep this in sync with
# whatever the actual file in templates/ is named.
TEMPLATE_PATH = os.path.join(BASE_DIR, "templates", "Inner_Outer_Sticker.pdf")
CONFIG_PATH = os.path.join(BASE_DIR, "config", "pad_header_mapping.json")

# Where the Inner/Outer boxes sit on the pad page (PDF points, top-left origin)
INNER_RECT = fitz.Rect(90.027, 350.416, 288.452, 492.686)
OUTER_RECT = fitz.Rect(378.794, 257.954, 661.259, 541.419)


def load_field_config():
    """Header-only fields — Inner/Outer field editing happens on their own tabs."""
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def _generate_one_page(row: dict) -> bytes:
    """Build ONE pad page for one row (TC_Number_st / Barcode_st / Sizes)."""
    header_config = load_field_config()

    pad_bytes = fill_single_label(TEMPLATE_PATH, row, header_config)
    doc = fitz.open("pdf", pad_bytes)

    inner_bytes = inner_label.generate_single(row)
    outer_bytes = outer_label.generate_single(row)

    compose_pdf_into_rect(doc, 0, INNER_RECT, inner_bytes)
    compose_pdf_into_rect(doc, 0, OUTER_RECT, outer_bytes)

    out = doc.tobytes()
    doc.close()
    return out


def generate_single(row: dict) -> bytes:
    """row = ekta row (1 size). TC_Number_st / Barcode_st / Sizes ei row-er
    nijer value — tai 1 row = 1 page."""
    return _generate_one_page(row)


def generate_batch(rows: list) -> bytes:
    """rows = list of row dicts (1 row = 1 size). Returns one merged
    multi-page PDF, ek row = ek page."""
    merged = fitz.open()
    for row in rows:
        single_bytes = generate_single(row)
        single_doc = fitz.open("pdf", single_bytes)
        merged.insert_pdf(single_doc)
        single_doc.close()
    out = merged.tobytes()
    merged.close()
    return out
