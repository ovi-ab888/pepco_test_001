"""
hangtag_front.py
=================
PEPCO Hangtag — FRONT SIDE only.

AW27: `product_name` was REMOVED from the Hangtag front (it now lives on the
Size Tag back — see labels/size_tag_back.py). The front now only carries the
8 currency prices. Positions were re-measured from the new AW27 template.

Position/font-size config lives in a JSON file (same pattern as
config/pad_header_mapping.json elsewhere in this project) — NOT
hardcoded in this file. Edit the JSON to adjust positions, no code
change needed.

HOW TO USE (manual position adjustment workflow):
1. Put your cleaned template at: templates/Hangtag/front_side.pdf
   (pink placeholder text removed, blank/clean template)
2. Edit config/hangtag_front_mapping.json (bbox / fontsize values).
3. Run:  python labels/hangtag_front.py   (from the repo root)
   -> Creates preview_front.pdf AND preview_front.png.
4. Repeat step 2-3 until the position looks right.

Coordinates are in PDF points, TOP-LEFT origin (PyMuPDF convention):
  x increases -> right,  y increases -> down.
  bbox = [x0, y0, x1, y1]  i.e. (left, top, right, bottom)
Page size for this template: 130.89 x 326.48 pt (46.2mm x 115.2mm)
"""

import fitz  # PyMuPDF (pip install pymupdf)
import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # repo root
TEMPLATE_PATH = os.path.join(BASE_DIR, "templates", "Hangtag", "front_side.pdf")
CONFIG_PATH = os.path.join(BASE_DIR, "config", "hangtag_front_mapping.json")

# Font is bundled in the repo's fonts/ folder — no upload needed.
MYRIADPRO_FONT_PATH = os.path.join(BASE_DIR, "fonts", "MyriadProSemibold.otf")

BRAND_PINK = (236 / 255, 0 / 255, 140 / 255)   # #EC008C - price numbers
BLACK = (0, 0, 0, 1)                           # CMYK C0 M0 Y0 K100 - print-safe pure black

COLOR_MAP = {"black": BLACK, "pink": BRAND_PINK}


def load_mapping(config_path=CONFIG_PATH):
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


# --- Sample data to preview with (change freely while testing) ---
SAMPLE_ROW = {
    "EUR": "3,00", "BAM": "6,00", "PLN": "12,00", "RON": "14,00",
    "CZK": "70", "MKD": "170", "RSD": "350", "HUF": "1200",
}


def _insert_right_aligned(page, text, bbox, fontsize, color=BRAND_PINK, fontname="helv", fontfile=None, fontbuffer=None):
    if not text:
        return
    rect = fitz.Rect(bbox)
    font_obj = fitz.Font(fontname=None if (fontfile or fontbuffer) else fontname,
                          fontfile=fontfile, fontbuffer=fontbuffer)
    tw = font_obj.text_length(str(text), fontsize=fontsize)
    x = rect.x1 - tw
    y = rect.y1 - (rect.height - fontsize) / 2 - 1
    page.insert_text((x, y), str(text), fontsize=fontsize, fontname=fontname, color=color)


def fill_front_side(row, template_path=TEMPLATE_PATH, config_path=CONFIG_PATH, mapping=None,
                     product_font_bytes=None, price_font_bytes=None, product_bold_font_bytes=None):
    """Returns a fitz.Document with the front side filled in.
    Pass `mapping` directly (a dict, same shape as the JSON) to skip
    reading from disk — used by the in-app live preview/adjustor.
    `price_font_bytes`: raw OTF bytes to use instead of the default price
    font (live-testing). `product_font_bytes` / `product_bold_font_bytes`
    are kept ONLY so older callers don't break — they are ignored (AW27 has
    no product_name on the Hangtag)."""
    if mapping is None:
        mapping = load_mapping(config_path)
    doc = fitz.open(template_path)
    page = doc[0]

    # (AW27) product_name removed from the Hangtag — nothing to draw here.

    price_fontname = "helv"
    price_fontfile = None
    price_fontbuffer = None
    if price_font_bytes:
        page.insert_font(fontbuffer=price_font_bytes, fontname="price_font")
        price_fontname = "price_font"
        price_fontbuffer = price_font_bytes
    elif os.path.exists(MYRIADPRO_FONT_PATH):
        page.insert_font(fontfile=MYRIADPRO_FONT_PATH, fontname="price_font")
        price_fontname = "price_font"
        price_fontfile = MYRIADPRO_FONT_PATH

    for col, field_cfg in mapping.get("prices", {}).items():
        value = row.get(col, "")
        if value:
            price_color = COLOR_MAP.get(field_cfg.get("color", "black"), BLACK)
            _insert_right_aligned(page, value, field_cfg["bbox"], field_cfg["fontsize"], color=price_color,
                                   fontname=price_fontname, fontfile=price_fontfile, fontbuffer=price_fontbuffer)

    return doc


def generate_single(row, template_path=TEMPLATE_PATH, config_path=CONFIG_PATH):
    """Returns front-side PDF bytes for one row (use this from your app)."""
    doc = fill_front_side(row, template_path, config_path)
    data = doc.tobytes()
    doc.close()
    return data


def generate_batch(rows, template_path=TEMPLATE_PATH, config_path=CONFIG_PATH):
    """Returns a list of front-side PDF bytes, one per row."""
    return [generate_single(row, template_path, config_path) for row in rows]


def generate_batch_pdf(rows, template_path=TEMPLATE_PATH, config_path=CONFIG_PATH):
    """Returns ONE multi-page PDF (bytes), one page per row — matches the
    shared label_options["generate"](rows) -> pdf_bytes contract used by
    app.py / the main label-automation system (same as pad_label,
    inner_label, etc.)."""
    out = fitz.open()
    for row in rows:
        doc = fill_front_side(row, template_path, config_path)
        out.insert_pdf(doc)
        doc.close()
    # same final save as hangtag_back: merge the duplicate per-page copies of
    # the price font into ONE (smaller file). No font subsetting (Illustrator).
    data = out.tobytes(garbage=4, deflate=True, clean=True)
    out.close()
    return data


if __name__ == "__main__":
    if not os.path.exists(TEMPLATE_PATH):
        print(f"❌ Template not found at: {TEMPLATE_PATH}")
        print("   Put your cleaned front_side.pdf there first, then rerun.")
    elif not os.path.exists(CONFIG_PATH):
        print(f"❌ Config not found at: {CONFIG_PATH}")
    else:
        doc = fill_front_side(SAMPLE_ROW)
        doc.save("preview_front.pdf")
        pix = doc[0].get_pixmap(dpi=200)
        pix.save("preview_front.png")
        doc.close()
        print("✅ Done — check preview_front.png (or preview_front.pdf)")
        print("   Adjust config/hangtag_front_mapping.json and rerun to fine-tune.")
