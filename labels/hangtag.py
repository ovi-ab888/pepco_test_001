"""
labels/hangtag.py
==================
PEPCO Hangtag (Swingtag) — Front side + Back side generator.

Coordinates below were extracted PROGRAMMATICALLY (PyMuPDF text-position
scan) from the uploaded templates:
  - Hangtag_front_side.pdf  (130.89 x 326.48 pt = 46.2mm x 115.2mm)
  - Hangtag_back_side.pdf   (same page size)
  - Pad.pdf                 (8 slot rectangles: 1 Front + 7 Back, each
                              130.4 x 326.0 pt — i.e. 1:1 scale, no resize
                              needed when compositing)
So these positions are REAL, not guessed — but please sanity-check the
first generated PDF against print/preview before bulk use.

TEMPLATE FILES EXPECTED (place the cleaned, pink-removed versions here):
    templates/Hangtag/front_side.pdf
    templates/Hangtag/back_side.pdf
    templates/Hangtag/pad.pdf
FONT FILES EXPECTED:
    fonts/PEPCO_Ovi.ttf        (pictogram font — used for washing_code + Cotton "Z")

⚠️ OPEN ITEMS to confirm with Ovi before this is production-ready:
  1. The "40" wash-temperature number seen in the rasterized preview did
     NOT appear in the PDF text layer at all — it's likely baked into the
     wash-tub icon as an outlined/vector graphic, not fillable text. If a
     product ever needs a DIFFERENT temperature, that icon graphic itself
     needs a variant, not a text fill. Flagging — not solved here.
  2. Barcode bars are drawn with a self-contained standard EAN13 renderer
     in this file (`_draw_ean13`). The main system already has a proven
     `draw_ean13_vector` in engine.py (guard bars 1.15x taller, brand
     color #E6007E) — once this file sits in the real repo, swap
     `_draw_ean13()` calls for `engine.draw_ean13_vector()` so barcodes
     match Inner/Outer/Pad pixel-for-pixel. Kept local here only because
     engine.py's exact function signature wasn't available to port from.
  3. Price table currently hardcodes exactly the 8 currencies seen in the
     template (EUR, BAM, PLN, RON, CZK, MKD, RSD, HUF) at fixed stacked
     positions. If a future template needs a different currency SET or
     COUNT, the FRONT_PRICE_FIELDS list below is where to edit — it's not
     auto-derived from the row's columns on purpose (position count must
     match the template).
"""

import fitz  # PyMuPDF
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TEMPLATE_FRONT = os.path.join(BASE_DIR, "templates", "Hangtag", "front_side.pdf")
TEMPLATE_BACK = os.path.join(BASE_DIR, "templates", "Hangtag", "back_side.pdf")
TEMPLATE_PAD = os.path.join(BASE_DIR, "templates", "Hangtag", "pad.pdf")
FONT_PICTOGRAM = os.path.join(BASE_DIR, "fonts", "PEPCO_Ovi.ttf")

BRAND_PINK = (236 / 255, 0 / 255, 140 / 255)  # #EC008C — matches barcode/price pink in templates
BLACK = (35 / 255, 31 / 255, 32 / 255)        # #231F20 — matches body text black in templates


# ================================================================
#  BACK SIDE — field positions (pt, top-left origin, PyMuPDF convention)
# ================================================================
BACK_TEXT_FIELDS = [
    # column_name, bbox(x0,y0,x1,y1), fontsize, align ("l"/"c"/"r"), color
    ("Collection",          (50.6, 214.3, 80.3, 220.3), 4.5, "l", BLACK),
    ("Colour_SKU",          (49.4, 222.5, 81.6, 228.5), 4.5, "l", BLACK),
    ("Style_Merch_Season",  (43.0, 228.5, 88.0, 234.5), 4.5, "l", BLACK),
    ("Batch",               (59.4, 240.6, 71.3, 246.6), 4.5, "l", BLACK),
]

# washing_code (e.g. "gjnqt") — rendered with the PEPCO_Ovi pictogram font
BACK_WASHING_FIELD = {"bbox": (30.9, 32.5, 100.0, 44.0), "fontsize": 6.0}

# Cotton flag ("Z" -> pictogram glyph that renders as the "100% Cotton" seal).
# Column is present ONLY when the row is 100% single-material (per
# hangtag_extractor's cotton_value logic) — skip silently otherwise.
BACK_COTTON_FIELD = {"bbox": (96.5, -9.4, 119.1, 28.9), "fontsize": 20.0}

# Barcode: human-readable digits sit at this row; vector bars are drawn
# just above it (see _draw_ean13).
BACK_BARCODE_FIELD = {"digits_y": (274.5, 285.0), "x0": 21.2, "x1": 101.2, "bars_height": 34}


# ================================================================
#  FRONT SIDE — field positions
# ================================================================
# Product description block (21-language paragraph from
# hangtag_extractor.format_product_translations). Auto word-wraps.
FRONT_PRODUCT_NAME_BOX = (6.9, 32.5, 124.3, 134.6)
FRONT_PRODUCT_NAME_FONTSIZE = 4.4

# Price values — column name -> (bbox, fontsize). Currency LABELS
# (EUR/€, KM, PLN, CZK, ден, RON, RSD, HUF) are already fixed/black in the
# template; only these numeric values are filled, right-aligned in bbox.
FRONT_PRICE_FIELDS = [
    ("EUR", (73.8, 137.6, 111.0, 163.3), 21.0),
    ("BAM", (73.8, 160.3, 111.0, 186.0), 21.0),   # "KM" label = BAM currency
    ("PLN", (73.8, 183.0, 111.0, 208.6), 21.0),
    ("RON", (73.8, 205.7, 111.0, 231.3), 21.0),
    ("CZK", (89.0, 228.3, 111.0, 254.0), 21.0),
    ("MKD", (78.3, 251.0, 111.0, 276.7), 21.0),   # "ден" label = MKD currency
    ("RSD", (78.3, 273.7, 111.0, 299.4), 21.0),
    ("HUF", (78.3, 296.4, 111.0, 322.0), 21.0),
]

# ================================================================
#  PAD — 1x Front slot + 7x Back slot (from Pad.pdf, 1:1 scale)
# ================================================================
PAD_FRONT_RECT = fitz.Rect(55.2, 225.5, 185.6, 551.5)
PAD_BACK_RECTS = [
    fitz.Rect(189.2, 225.5, 319.6, 551.5),
    fitz.Rect(325.3, 225.5, 455.7, 551.5),
    fitz.Rect(461.4, 225.5, 591.7, 551.5),
    fitz.Rect(597.4, 225.5, 727.8, 551.5),
    fitz.Rect(733.5, 225.5, 863.9, 551.5),
    fitz.Rect(869.5, 225.5, 999.9, 551.5),
    fitz.Rect(1005.6, 225.5, 1136.0, 551.5),
]

# Pad header — reuses the SAME shared 8-field mapping as Inner/Outer/Pad
# (Order_ID, Style, Colour, Supplier_product_code, Item_classification,
# Supplier_name, today_date, Designer). Loaded from the existing
# config/pad_header_mapping.json — not redefined here.


# ================================================================
#  HELPERS
# ================================================================
def _insert_aligned_text(page, text, bbox, fontsize, align="l", color=BLACK, fontname="helv", fontfile=None):
    """Insert single-line text, left/center/right aligned within bbox, vertically centered."""
    if not text:
        return
    rect = fitz.Rect(bbox)
    tw = fitz.get_text_length(str(text), fontname=fontname, fontsize=fontsize) if not fontfile else None
    y = rect.y1 - (rect.height - fontsize) / 2 - 1  # baseline, roughly vertically centered
    if fontfile:
        # Pictogram / custom font glyphs — width calc not reliable via get_text_length,
        # so left-align at bbox.x0 for these (Collection/Batch/etc are already narrow).
        x = rect.x0
        page.insert_font(fontfile=fontfile, fontname="pictogram")
        page.insert_text((x, y), str(text), fontsize=fontsize, fontname="pictogram", color=color)
        return
    if align == "r":
        x = rect.x1 - tw
    elif align == "c":
        x = rect.x0 + (rect.width - tw) / 2
    else:
        x = rect.x0
    page.insert_text((x, y), str(text), fontsize=fontsize, fontname=fontname, color=color)


def _draw_ean13(page, code, x0, x1, y_bars_bottom, bars_height, color=BRAND_PINK):
    """
    Self-contained standard EAN13 vector bar renderer (guard/L/G/R pattern).
    ⚠️ See module docstring item #2 — swap for engine.draw_ean13_vector
    once available, so barcodes match the rest of the system exactly.
    """
    L_CODES = {
        '0': '0001101', '1': '0011001', '2': '0010011', '3': '0111101', '4': '0100011',
        '5': '0110001', '6': '0101111', '7': '0111011', '8': '0110111', '9': '0001011',
    }
    G_CODES = {k: v[::-1] for k, v in L_CODES.items()}
    R_CODES = {k: ''.join('1' if c == '0' else '0' for c in v) for k, v in L_CODES.items()}
    PARITY = {
        '0': 'LLLLLL', '1': 'LLGLGG', '2': 'LLGGLG', '3': 'LLGGGL', '4': 'LGLLGG',
        '5': 'LGGLLG', '6': 'LGGGLL', '7': 'LGLGLG', '8': 'LGLGGL', '9': 'LGGLGL',
    }
    code = str(code).zfill(13)
    first, rest = code[0], code[1:]
    left, right = rest[:6], rest[6:]
    parity = PARITY[first]

    bits = "101"  # start guard
    for i, d in enumerate(left):
        bits += L_CODES[d] if parity[i] == 'L' else G_CODES[d]
    bits += "01010"  # center guard
    for d in right:
        bits += R_CODES[d]
    bits += "101"  # end guard

    total_width = x1 - x0
    module_w = total_width / len(bits)
    x = x0
    for i, bit in enumerate(bits):
        is_guard = i < 3 or (45 <= i < 50) or i >= len(bits) - 3
        h = bars_height * (1.15 if is_guard else 1.0)
        if bit == "1":
            rect = fitz.Rect(x, y_bars_bottom - h, x + module_w, y_bars_bottom)
            page.draw_rect(rect, color=color, fill=color, width=0)
        x += module_w


def _fill_back_side(row, template_path=TEMPLATE_BACK):
    doc = fitz.open(template_path)
    page = doc[0]

    for col, bbox, fontsize, align, color in BACK_TEXT_FIELDS:
        _insert_aligned_text(page, row.get(col, ""), bbox, fontsize, align, color)

    washing_code = row.get("washing_code", "")
    if washing_code:
        b = BACK_WASHING_FIELD["bbox"]
        _insert_aligned_text(page, washing_code, b, BACK_WASHING_FIELD["fontsize"],
                              color=BRAND_PINK, fontfile=FONT_PICTOGRAM)

    if row.get("Cotton"):
        b = BACK_COTTON_FIELD["bbox"]
        _insert_aligned_text(page, row["Cotton"], b, BACK_COTTON_FIELD["fontsize"],
                              color=BRAND_PINK, fontfile=FONT_PICTOGRAM)

    barcode = row.get("barcode", "")
    if barcode:
        bf = BACK_BARCODE_FIELD
        _draw_ean13(page, barcode, bf["x0"], bf["x1"], bf["digits_y"][0] - 2, bf["bars_height"])
        _insert_aligned_text(page, " ".join([barcode[0], barcode[1:7], barcode[7:]]),
                              (bf["x0"], bf["digits_y"][0], bf["x1"], bf["digits_y"][1]),
                              8.8, align="c", color=BRAND_PINK)

    return doc


def _fill_front_side(row, template_path=TEMPLATE_FRONT):
    doc = fitz.open(template_path)
    page = doc[0]

    if row.get("product_name"):
        rect = fitz.Rect(FRONT_PRODUCT_NAME_BOX)
        page.insert_textbox(rect, row["product_name"], fontsize=FRONT_PRODUCT_NAME_FONTSIZE,
                             fontname="helv", color=BLACK, align=0)

    for col, bbox, fontsize in FRONT_PRICE_FIELDS:
        value = row.get(col, "")
        if value:
            _insert_aligned_text(page, value, bbox, fontsize, align="r", color=BRAND_PINK,
                                  fontname="helv")

    return doc


# ================================================================
#  PUBLIC API — matches inner_label.py / outer_label.py pattern
# ================================================================
def generate_single(row):
    """Returns (front_pdf_bytes, back_pdf_bytes) for one row."""
    front_doc = _fill_front_side(row)
    back_doc = _fill_back_side(row)
    front_bytes = front_doc.tobytes()
    back_bytes = back_doc.tobytes()
    front_doc.close()
    back_doc.close()
    return front_bytes, back_bytes


def generate_batch(rows):
    """Returns a list of (front_pdf_bytes, back_pdf_bytes) tuples, one per row."""
    return [generate_single(row) for row in rows]


def generate_pad(front_bytes, back_bytes, template_path=TEMPLATE_PAD):
    """
    Composite 1x Front + 7x Back (same back, repeated) onto the Pad
    template at the 8 slot rectangles found in Pad.pdf.
    Pad header (Order ID/Style/Colour/etc, 8-field shared mapping) should
    be filled separately using the existing pad_header_mapping.json flow
    BEFORE calling this, same as Inner+Outer -> Pad.
    """
    pad_doc = fitz.open(template_path)
    pad_page = pad_doc[0]

    front_src = fitz.open("pdf", front_bytes)
    pad_page.show_pdf_page(PAD_FRONT_RECT, front_src, 0)
    front_src.close()

    back_src = fitz.open("pdf", back_bytes)
    for rect in PAD_BACK_RECTS:
        pad_page.show_pdf_page(rect, back_src, 0)
    back_src.close()

    return pad_doc.tobytes()
