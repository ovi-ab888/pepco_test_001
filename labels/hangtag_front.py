"""
hangtag_front.py
=================
PEPCO Hangtag — FRONT SIDE only. Standalone (no other project files needed).

HOW TO USE (manual position adjustment workflow):
1. Put your cleaned template at: templates/Hangtag/front_side.pdf
   (pink placeholder text removed, blank/clean template)
2. Edit the coordinates in the "ADJUST THESE COORDINATES" section below.
3. Run:  python hangtag_front.py
   -> Creates preview_front.pdf AND preview_front.png (so you can see the
      result instantly without opening Illustrator/Acrobat).
4. Repeat step 2-3 until the position looks right.

Coordinates are in PDF points, TOP-LEFT origin (PyMuPDF convention):
  x increases -> right,  y increases -> down.
  bbox = (x0, y0, x1, y1)  i.e. (left, top, right, bottom)
Page size for this template: 130.89 x 326.48 pt (46.2mm x 115.2mm)
"""

import fitz  # PyMuPDF (pip install pymupdf)
import os

TEMPLATE_PATH = "templates/Hangtag/front_side.pdf"

BRAND_PINK = (236 / 255, 0 / 255, 140 / 255)   # #EC008C - price numbers
BLACK = (35 / 255, 31 / 255, 32 / 255)         # #231F20 - body text


# ================================================================
#  🔧 ADJUST THESE COORDINATES 🔧
# ================================================================

# --- Product description paragraph (21-language block, auto word-wraps) ---
PRODUCT_NAME_BOX = (6.9, 32.5, 124.3, 134.6)   # (x0, y0, x1, y1)
PRODUCT_NAME_FONTSIZE = 4.4

# --- Price values (right-aligned inside each bbox) ---
# column_name : (bbox, fontsize)
PRICE_FIELDS = {
    "EUR": ((73.8, 137.6, 111.0, 163.3), 21.0),
    "BAM": ((73.8, 160.3, 111.0, 186.0), 21.0),   # shown as "KM" label on template
    "PLN": ((73.8, 183.0, 111.0, 208.6), 21.0),
    "RON": ((73.8, 205.7, 111.0, 231.3), 21.0),
    "CZK": ((89.0, 228.3, 111.0, 254.0), 21.0),
    "MKD": ((78.3, 251.0, 111.0, 276.7), 21.0),   # shown as "ден" label on template
    "RSD": ((78.3, 273.7, 111.0, 299.4), 21.0),
    "HUF": ((78.3, 296.4, 111.0, 322.0), 21.0),
}

# --- Sample data to preview with (change freely while testing) ---
SAMPLE_ROW = {
    "product_name": (
        "|EN| Girls t-shirt |AL| T-shirt vajzash: 100% Pambuk |BG| Момичешка тениска "
        "|BiH| T-shirt za djevojčice. Sastav materijala na ušivenoj etiketi. "
        "|CZ| Dívčí t-shirt |DE| T-Shirt für Mädchen |EE| Tüdrukute T-särk"
    ),
    "EUR": "2,00", "BAM": "4,00", "PLN": "8,00", "RON": "9,00",
    "CZK": "50", "MKD": "120", "RSD": "250", "HUF": "750",
}

# ================================================================
#  (No need to edit below this line)
# ================================================================


def _insert_right_aligned(page, text, bbox, fontsize, color=BRAND_PINK, fontname="helv"):
    if not text:
        return
    rect = fitz.Rect(bbox)
    tw = fitz.get_text_length(str(text), fontname=fontname, fontsize=fontsize)
    x = rect.x1 - tw
    y = rect.y1 - (rect.height - fontsize) / 2 - 1
    page.insert_text((x, y), str(text), fontsize=fontsize, fontname=fontname, color=color)


def fill_front_side(row, template_path=TEMPLATE_PATH):
    """Returns a fitz.Document with the front side filled in."""
    doc = fitz.open(template_path)
    page = doc[0]

    if row.get("product_name"):
        rect = fitz.Rect(PRODUCT_NAME_BOX)
        page.insert_textbox(rect, row["product_name"], fontsize=PRODUCT_NAME_FONTSIZE,
                             fontname="helv", color=BLACK, align=0)

    for col, (bbox, fontsize) in PRICE_FIELDS.items():
        _insert_right_aligned(page, row.get(col, ""), bbox, fontsize)

    return doc


def generate_single(row, template_path=TEMPLATE_PATH):
    """Returns front-side PDF bytes for one row (use this from your app)."""
    doc = fill_front_side(row, template_path)
    data = doc.tobytes()
    doc.close()
    return data


def generate_batch(rows, template_path=TEMPLATE_PATH):
    """Returns a list of front-side PDF bytes, one per row."""
    return [generate_single(row, template_path) for row in rows]


def generate_batch_pdf(rows, template_path=TEMPLATE_PATH):
    """Returns ONE multi-page PDF (bytes), one page per row — matches the
    shared label_options["generate"](rows) -> pdf_bytes contract used by
    app.py / the main label-automation system (same as pad_label,
    inner_label, etc.)."""
    out = fitz.open()
    for row in rows:
        doc = fill_front_side(row, template_path)
        out.insert_pdf(doc)
        doc.close()
    data = out.tobytes()
    out.close()
    return data


if __name__ == "__main__":
    if not os.path.exists(TEMPLATE_PATH):
        print(f"❌ Template not found at: {TEMPLATE_PATH}")
        print("   Put your cleaned front_side.pdf there first, then rerun.")
    else:
        doc = fill_front_side(SAMPLE_ROW)
        doc.save("preview_front.pdf")
        pix = doc[0].get_pixmap(dpi=200)
        pix.save("preview_front.png")
        doc.close()
        print("✅ Done — check preview_front.png (or preview_front.pdf)")
        print("   Adjust the coordinates above and rerun to fine-tune.")
