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
import re
import json
import fitz  # PyMuPDF

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "size_tag_back_mapping.json")
ARIAL_FONT_PATH = os.path.join(BASE_DIR, "fonts", "ArialRegular.ttf")
ARIAL_BOLD_PATH = os.path.join(BASE_DIR, "fonts", "ArialBold.ttf")  # optional; না থাকলে faux-bold
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


CODE_RE = re.compile(r"^\|[A-Za-z]{2,3}\|$")  # |EN| |AL| |BiH| ... => bold


def _draw_product_name(page, text, cfg):
    """Justified paragraph, country codes (|EN|, |AL| ...) bold, rest regular.
    Font shrinks (cfg.fontsize -> cfg.min_fontsize) until everything fits."""
    reg_file = ARIAL_FONT_PATH if os.path.exists(ARIAL_FONT_PATH) else None
    bold_file = ARIAL_BOLD_PATH if os.path.exists(ARIAL_BOLD_PATH) else None
    reg_name, bold_name = "helv", "helv"
    if reg_file:
        page.insert_font(fontfile=reg_file, fontname="arial_font")
        reg_name = bold_name = "arial_font"
    if bold_file:
        page.insert_font(fontfile=bold_file, fontname="arial_bold")
        bold_name = "arial_bold"
    faux_bold = bold_file is None

    f_reg = fitz.Font(fontfile=reg_file) if reg_file else fitz.Font("helv")
    f_bold = fitz.Font(fontfile=bold_file) if bold_file else f_reg

    color = COLOR_MAP.get(cfg.get("color", "black"), BLACK)
    rect = fitz.Rect(cfg["bbox"])
    justify = cfg.get("align", "justify") == "justify"
    spacing = float(cfg.get("line_spacing", 1.25))
    size = float(cfg["fontsize"])
    min_size = float(cfg.get("min_fontsize", 3.0))

    words = [(w, bool(CODE_RE.match(w))) for w in str(text).split()]

    def wlen(w, b, sz):
        return (f_bold if b else f_reg).text_length(w, fontsize=sz)

    def layout(sz):
        space = f_reg.text_length(" ", fontsize=sz)
        lines, cur, cur_w = [], [], 0.0
        for w, b in words:
            ww = wlen(w, b, sz)
            add = ww if not cur else space + ww
            if cur and cur_w + add > rect.width:
                lines.append(cur)
                cur, cur_w = [(w, b, ww)], ww
            else:
                cur.append((w, b, ww))
                cur_w += add
        if cur:
            lines.append(cur)
        return lines, space

    while True:
        lines, space = layout(size)
        height = (len(lines) - 1) * size * spacing + size
        if height <= rect.height or size <= min_size:
            break
        size -= 0.1
    if height > rect.height:
        print("⚠️ size_tag_back: product_name box এ ধরেনি (min font এও)। bbox বড় করো।")

    y = rect.y0 + size * 0.92
    for li, line in enumerate(lines):
        n = len(line)
        gap = space
        if justify and li < len(lines) - 1 and n > 1:
            gap = (rect.width - sum(ww for _, _, ww in line)) / (n - 1)
        x = rect.x0
        for w, b, ww in line:
            if b and faux_bold:
                page.insert_text((x, y), w, fontsize=size, fontname=reg_name, color=color,
                                 fill=color, render_mode=2, border_width=size * 0.01)
            else:
                page.insert_text((x, y), w, fontsize=size,
                                 fontname=bold_name if b else reg_name, color=color)
            x += ww + gap
        y += size * spacing


def _get(row, key):
    """row[key], case-insensitive (product_name / Product_name / PRODUCT_NAME)."""
    if key in row:
        return row.get(key)
    low = key.lower()
    for k, v in row.items():
        if str(k).lower() == low:
            return v
    return None


def _find_back_panel(page, mapping):
    """Back Side panel = the LOWEST panel-sized rectangle on the page
    (works for 70mm and 86mm/OEKO-TEX templates alike)."""
    best = None
    for dr in page.get_drawings():
        r = dr["rect"]
        if 125 < r.width < 136 and r.height > 150:
            if best is None or r.y0 > best.y0:
                best = r
    if best is None:  # fallback to the 70mm position stored in the JSON
        best = fitz.Rect(mapping["page_check"]["back_panel"])
    return best


def _abs_bbox(panel, cfg):
    """Panel-relative margins -> absolute bbox. (cfg['bbox'] still works.)"""
    if "bbox" in cfg:
        return cfg["bbox"]
    x0 = panel.x0 + cfg["margin_left"]
    x1 = panel.x1 - cfg["margin_right"]
    if "margin_top" in cfg:  # product_name: top & bottom margins
        y0 = panel.y0 + cfg["margin_top"]
        y1 = panel.y1 - cfg["margin_bottom"]
    else:                    # washing_code: fixed height above bottom margin
        y1 = panel.y1 - cfg["margin_bottom"]
        y0 = y1 - cfg["height"]
    return [x0, y0, x1, y1]


def fill_back(pdf_bytes, row, config_path=CONFIG_PATH):
    """Takes the already-filled Size Tag PDF bytes, writes product_name and
    washing_code on the Back Side panel, returns new PDF bytes."""
    mapping = load_mapping(config_path)
    doc = fitz.open("pdf", pdf_bytes)
    page = doc[0]
    panel = _find_back_panel(page, mapping)

    # --- product_name: justified, country codes bold (see _draw_product_name) ---
    pn = mapping.get("product_name")
    pn_text = _get(row, "product_name")
    if pn and pn_text:
        _draw_product_name(page, pn_text, {**pn, "bbox": _abs_bbox(panel, pn)})

    # --- washing_code: same as hangtag_back (pictogram font PEPCO_Ovi) ---
    wc = mapping.get("washing_code")
    if wc and _get(row, "washing_code"):
        fontname, fontfile = "helv", None
        if os.path.exists(PICTOGRAM_FONT_PATH):
            page.insert_font(fontfile=PICTOGRAM_FONT_PATH, fontname="pictogram_font")
            fontname, fontfile = "pictogram_font", PICTOGRAM_FONT_PATH
        color = COLOR_MAP.get(wc.get("color", "black"), BLACK)
        code = str(_get(row, "washing_code"))
        wc_bbox = _abs_bbox(panel, wc)
        size = float(wc["fontsize"])
        max_w = fitz.Rect(wc_bbox).width
        font_obj = fitz.Font(fontfile=fontfile) if fontfile else fitz.Font(fontname=fontname)
        while size > 3 and font_obj.text_length(code, fontsize=size) > max_w:
            size -= 0.1  # symbols panel এর বাইরে গেলে auto ছোট হবে
        _insert_text(page, code, wc_bbox, size,
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
