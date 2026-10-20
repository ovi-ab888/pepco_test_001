"""
labels/size_tag_back.py
=======================
AW27 Size Tag — BACK SIDE (product_name + washing_code).

Logic is copied as-is from Hangtag (hangtag_front.py -> product_name,
hangtag_back.py -> washing_code). Positions come from
config/size_tag_back_mapping.json (PDF points, TOP-LEFT origin).

Preview:  python labels/size_tag_back.py   (needs a template PDF path below)
"""
import os
import json
import fitz  # PyMuPDF

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "size_tag_back_mapping.json")
ARIAL_FONT_PATH = os.path.join(BASE_DIR, "fonts", "ArialRegular.ttf")
PICTOGRAM_FONT_PATH = os.path.join(BASE_DIR, "fonts", "PEPCO_Ovi.ttf")

BRAND_PINK = (236 / 255, 0 / 255, 140 / 255)
BLACK = (0, 0, 0, 1)  # CMYK K100 - print-safe black (same as hangtag_back)
COLOR_MAP = {"black": BLACK, "pink": BRAND_PINK}


def load_mapping(config_path=CONFIG_PATH):
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _insert_text(page, text, bbox, fontsize, color=BLACK, fontname="helv",
                 align="left", fontfile=None):
    """Same helper as hangtag_back._insert_text."""
    if not text:
        return
    rect = fitz.Rect(bbox)
    text = str(text)
    font_obj = fitz.Font(fontfile=fontfile) if fontfile else fitz.Font(fontname=fontname)
    tw = font_obj.text_length(text, fontsize=fontsize)
    if align == "center":
        x = rect.x0 + (rect.width - tw) / 2
    elif align == "right":
        x = rect.x1 - tw
    else:
        x = rect.x0
    y = rect.y1 - (rect.height - fontsize) / 2 - 1
    page.insert_text((x, y), text, fontsize=fontsize, fontname=fontname, color=color)


def _get(row, key):
    """row[key], case-insensitive (product_name / Product_name / PRODUCT_NAME)."""
    if key in row:
        return row.get(key)
    low = key.lower()
    for k, v in row.items():
        if str(k).lower() == low:
            return v
    return None


def fill_back(pdf_bytes, row, config_path=CONFIG_PATH):
    """Takes the already-filled Size Tag PDF bytes, writes product_name and
    washing_code on the Back Side panel, returns new PDF bytes."""
    mapping = load_mapping(config_path)
    doc = fitz.open("pdf", pdf_bytes)
    page = doc[0]

    # --- product_name: same textbox logic as hangtag_front, but Arial font
    #     (built-in helv cannot draw Cyrillic / ž č ć etc.).
    #     insert_textbox draws NOTHING when text does not fit, so we shrink
    #     the font step by step until it fits. ---
    pn = mapping.get("product_name")
    pn_text = _get(row, "product_name")
    if pn and pn_text:
        pn_font = "helv"
        if os.path.exists(ARIAL_FONT_PATH):
            page.insert_font(fontfile=ARIAL_FONT_PATH, fontname="arial_font")
            pn_font = "arial_font"
        color = COLOR_MAP.get(pn.get("color", "black"), BLACK)
        rect = fitz.Rect(pn["bbox"])
        size = float(pn["fontsize"])
        min_size = float(pn.get("min_fontsize", 3.0))
        while True:
            rc = page.insert_textbox(rect, pn_text, fontsize=size,
                                     fontname=pn_font, color=color, align=0)
            if rc >= 0:
                break
            size -= 0.1
            if size < min_size:
                print("⚠️ size_tag_back: product_name box এ ধরেনি (min font এও)। "
                      "bbox বড় করো বা text ছোট করো।")
                break

    # --- washing_code: same as hangtag_back (pictogram font PEPCO_Ovi) ---
    wc = mapping.get("washing_code")
    if wc and _get(row, "washing_code"):
        fontname, fontfile = "helv", None
        if os.path.exists(PICTOGRAM_FONT_PATH):
            page.insert_font(fontfile=PICTOGRAM_FONT_PATH, fontname="pictogram_font")
            fontname, fontfile = "pictogram_font", PICTOGRAM_FONT_PATH
        color = COLOR_MAP.get(wc.get("color", "black"), BLACK)
        code = str(_get(row, "washing_code"))
        size = float(wc["fontsize"])
        max_w = fitz.Rect(wc["bbox"]).width
        font_obj = fitz.Font(fontfile=fontfile) if fontfile else fitz.Font(fontname=fontname)
        while size > 3 and font_obj.text_length(code, fontsize=size) > max_w:
            size -= 0.1  # symbols panel এর বাইরে গেলে auto ছোট হবে
        _insert_text(page, code, wc["bbox"], size,
                     color=color, fontname=fontname,
                     align=wc.get("align", "center"), fontfile=fontfile)

    out = doc.tobytes()
    doc.close()
    return out


if __name__ == "__main__":
    import sys
    tpl = sys.argv[1] if len(sys.argv) > 1 else "AW27_Size_Tag.pdf"
    sample = {
        "product_name": (
            "|EN| Boys t-shirt |AL| T-shirt djemsh: 100% Pambuk |BG| Момчешка тениска "
            "|BiH| T-shirt za dječake. Sastav materijala na ušivenoj etiketi. "
            "|CZ| Chlapecké tričko |DE| T-Shirt für Jungen |EE| Poiste T-särk "
            "|ES| Camiseta de niño / Samarreta nen |GR| T-shirt για αγόρια "
            "|HR| T-shirt za dječake |HU| Fiú póló |IT| Maglietta per ragazzi "
            "|LT| Marškinėliai berniukui |LV| T-krekls zēniem |MK| Детски машки t-shirt: 100% Памук "
            "|PL| T-shirt chłopięcy |PT| T-shirt para rapaz |RO| T-shirt băieți "
            "|RS| Majica za dečake. Sastav materijala nalazi se na ušivenoj etiketi. "
            "|SI| Fantovska majica, kratki rokav |SK| Chlapčenské tričko |UA| Футболка для хлопчиків."
        ),
        "washing_code": "gjnqt",
    }
    with open(tpl, "rb") as f:
        out = fill_back(f.read(), sample)
    d = fitz.open("pdf", out)
    d.save("preview_size_tag_back.pdf")
    d[0].get_pixmap(dpi=150).save("preview_size_tag_back.png")
    print("✅ preview_size_tag_back.png / .pdf তৈরি হয়েছে")
