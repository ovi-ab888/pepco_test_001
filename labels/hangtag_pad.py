"""
hangtag_pad.py
===============
PEPCO Hangtag — Pad compositing: 1x Front + 7x Back (same back, repeated)
composited onto the Pad template, plus the Pad header fields (shared
8-field style: Order_ID, Item_classification, Style, Colour, Designer,
Dept, and the top-right COLOUR swatch name).

Position config lives in config/hangtag_pad_mapping.json — same pattern
as hangtag_front.py / hangtag_back.py.

Repo structure needed:
    labels/hangtag_pad.py     (this file)
    labels/hangtag_front.py
    labels/hangtag_back.py
    config/hangtag_pad_mapping.json
    fonts/ArialRegular.ttf
    templates/Hangtag/pad.pdf   <- your cleaned Pad template

Note: Tech Pack Rcvd / Last Revision Date / Final Approved Date /
Customer stay BLANK on the Pad (confirmed earlier — manual fields, not
data-driven). Buyer/Product/Measurement are fixed template text.
"""

import fitz  # PyMuPDF
import json
import os

from labels import hangtag_front as hf
from labels import hangtag_back as hb

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # repo root
TEMPLATE_PATH = os.path.join(BASE_DIR, "templates", "Hangtag", "pad.pdf")
CONFIG_PATH = os.path.join(BASE_DIR, "config", "hangtag_pad_mapping.json")

BLACK = (35 / 255, 31 / 255, 32 / 255)

fitz.TOOLS.set_aa_level(0)  # keep barcode preview scannable, same as hangtag_back.py


def load_mapping(config_path=CONFIG_PATH):
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def fill_pad_header(page, row, mapping):
    """Fill the Pad header fields directly on the (already-opened) pad page."""
    for col, cfg in mapping.get("header", {}).items():
        value = row.get(col, "")
        if value:
            page.insert_text((cfg["x"], cfg["y"]), str(value), fontsize=cfg["fontsize"],
                              fontname="helv", color=BLACK)

    swatch_cfg = mapping.get("colour_swatch_name")
    colour = row.get("Colour", "")
    if swatch_cfg and colour:
        rect = fitz.Rect(swatch_cfg["bbox"])
        text = str(colour).upper()
        fs = swatch_cfg["fontsize"]
        tw = fitz.get_text_length(text, fontname="helv", fontsize=fs)
        x = rect.x0 + (rect.width - tw) / 2 if swatch_cfg.get("align", "center") == "center" else rect.x0
        y = rect.y1 - (rect.height - fs) / 2 - 1
        page.insert_text((x, y), text, fontsize=fs, fontname="helv", color=BLACK)


def generate_pad(row, front_bytes=None, back_bytes=None, template_path=TEMPLATE_PATH,
                  config_path=CONFIG_PATH, mapping=None):
    """
    Build one Pad PDF (bytes) for a single row: 1x Front + 7x Back
    composited at the fixed slot rectangles, with the header filled in.

    If front_bytes / back_bytes are not supplied, they are generated from
    `row` using hangtag_front.generate_single / hangtag_back.generate_single
    (with each module's own default template/config/fonts).
    """
    if mapping is None:
        mapping = load_mapping(config_path)

    if front_bytes is None:
        front_bytes = hf.generate_single(row)
    if back_bytes is None:
        back_bytes = hb.generate_single(row)

    pad_doc = fitz.open(template_path)
    pad_page = pad_doc[0]

    fill_pad_header(pad_page, row, mapping)

    front_src = fitz.open("pdf", front_bytes)
    pad_page.show_pdf_page(fitz.Rect(mapping["front_rect"]), front_src, 0)
    front_src.close()

    back_src = fitz.open("pdf", back_bytes)
    for rect_coords in mapping["back_rects"]:
        pad_page.show_pdf_page(fitz.Rect(rect_coords), back_src, 0)
    back_src.close()

    data = pad_doc.tobytes()
    pad_doc.close()
    return data


def generate_batch(rows, template_path=TEMPLATE_PATH, config_path=CONFIG_PATH):
    """Returns a list of Pad PDF bytes, one per row."""
    mapping = load_mapping(config_path)
    return [generate_pad(row, template_path=template_path, mapping=mapping) for row in rows]


def generate_batch_pdf(rows, template_path=TEMPLATE_PATH, config_path=CONFIG_PATH):
    """Returns ONE multi-page PDF (bytes), one Pad page per row."""
    mapping = load_mapping(config_path)
    out = fitz.open()
    for row in rows:
        pad_bytes = generate_pad(row, template_path=template_path, mapping=mapping)
        pad_single = fitz.open("pdf", pad_bytes)
        out.insert_pdf(pad_single)
        pad_single.close()
    data = out.tobytes()
    out.close()
    return data
